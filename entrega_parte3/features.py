"""Pré-processamento das 13 features cruas do modelo antifraude.

O contrato é a fonte das colunas, da ordem e das categorias permitidas. As
categorias são passadas explicitamente ao ``OneHotEncoder``: assim, uma
categoria que não apareceu no conjunto de treino não altera o número de
colunas do modelo. ``handle_unknown='ignore'`` também torna a inferência
robusta caso um lote de produção contenha uma categoria desconhecida.

O retorno de :func:`criar_preprocessador` deve ser a primeira etapa de um
``sklearn.pipeline.Pipeline`` junto com o estimador. Ao registrar um pipeline
que use este módulo, inclua ``code_paths=["features.py"]``.
"""

from pathlib import Path

import numpy as np
import yaml
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


_CAMINHO_CONTRATO = Path(__file__).resolve().parent / "contrato" / "contrato_features.yaml"


def carregar_contrato(caminho=None):
    """Carrega o contrato de features usado para montar o pré-processador."""
    if caminho is None:
        caminho = _CAMINHO_CONTRATO
        if not caminho.is_file():
            # A célula de entrega exporta o YAML ao lado de features.py.
            caminho = Path(__file__).with_name("contrato_features.yaml")
    caminho = Path(caminho)
    with caminho.open(encoding="utf-8") as arquivo:
        return yaml.safe_load(arquivo)


def criar_preprocessador(contrato=None):
    """Cria o pré-processador a partir do contrato, não dos dados de treino.

    O ``DataFrame`` de entrada deve conter somente as 13 features cruas, com
    os nomes definidos pelo contrato. Colunas extras são descartadas.
    """
    contrato = contrato or carregar_contrato()
    definicoes = contrato["features"]

    colunas_numericas = [
        feature["nome"]
        for feature in definicoes
        if feature["tipo"] in {"int", "float", "bool"}
    ]
    definicoes_categoricas = [
        feature for feature in definicoes if feature["tipo"] == "categoria"
    ]
    colunas_categoricas = [feature["nome"] for feature in definicoes_categoricas]
    categorias = [
        [str(valor) for valor in feature["valores"]]
        for feature in definicoes_categoricas
    ]

    numericas = Pipeline([
        ("imputacao", SimpleImputer(strategy="median")),
        ("escala", StandardScaler()),
    ])
    categoricas = Pipeline([
        ("imputacao", SimpleImputer(strategy="most_frequent")),
        (
            "onehot",
            OneHotEncoder(
                categories=categorias,
                handle_unknown="ignore",
                sparse_output=False,
            ),
        ),
    ])

    return ColumnTransformer(
        transformers=[
            ("numericas", numericas, colunas_numericas),
            ("categoricas", categoricas, colunas_categoricas),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def pix_dispositivo_conhecido(df):
    """Pix em aparelho já usado, com duas ou mais transações na hora anterior."""
    return df["canal"].eq("pix") & df["dispositivo_novo"].eq(0) & df["qtd_transacoes_1h"].ge(2)


class EspecialistaPix(ClassifierMixin, BaseEstimator):
    """Mantém o score anterior fora do grupo e aplica um modelo treinado no grupo."""

    def __init__(self, modelo_atual, especialista, corte_atual, corte_especialista):
        self.modelo_atual = modelo_atual
        self.especialista = especialista
        self.corte_atual = corte_atual
        self.corte_especialista = corte_especialista

    def __sklearn_is_fitted__(self):
        return hasattr(self.especialista, "classes_")

    @property
    def classes_(self):
        return self.especialista.classes_

    def fit(self, X, y):
        grupo = pix_dispositivo_conhecido(X)
        self.especialista.fit(X.loc[grupo], np.asarray(y)[grupo.to_numpy()])
        return self

    def predict_proba(self, X):
        grupo = pix_dispositivo_conhecido(X)
        score = self.modelo_atual.predict_proba(X)[:, 1]
        if grupo.any():
            risco = self.especialista.predict_proba(X.loc[grupo])[:, 1]
            # A API usa um corte único. O remapeamento preserva a ordem no grupo.
            score[grupo.to_numpy()] = np.interp(
                risco, [0, self.corte_especialista, 1], [0, self.corte_atual, 1],
            )
        return np.column_stack((1 - score, score))

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= self.corte_atual).astype(int)
