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

import yaml
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


_CAMINHO_CONTRATO = Path(__file__).resolve().parent / "contrato" / "contrato_features.yaml"


def carregar_contrato(caminho=None):
    """Carrega o contrato de features usado para montar o pré-processador."""
    caminho = Path(caminho) if caminho is not None else _CAMINHO_CONTRATO
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
