"""
BASELINE OFICIAL — pré-processamento conforme o contrato v1.0.
"""
from pathlib import Path

import yaml
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

CONTRATO = Path(__file__).resolve().parent / "contrato" / "contrato_features.yaml"


def carregar_contrato(caminho=CONTRATO):
    with open(caminho, encoding="utf-8") as f:
        return yaml.safe_load(f)


def colunas(contrato):
    feats = [f["nome"] for f in contrato["features"]]
    cat = [f["nome"] for f in contrato["features"] if f["tipo"] == "categoria"]
    num = [c for c in feats if c not in cat]
    return feats, cat, num


def preprocessador(contrato):
    """Categóricas com as categorias FIXADAS pelo contrato (não pelas que
    apareceram no treino). Numéricas passam direto (árvore não precisa de escala)."""
    feats, cat, num = colunas(contrato)
    categorias = [next(f["valores"] for f in contrato["features"] if f["nome"] == c) for c in cat]
    return ColumnTransformer(
        [("cat", OneHotEncoder(categories=categorias, handle_unknown="ignore", sparse_output=False), cat),
         ("num", "passthrough", num)],
        verbose_feature_names_out=False,
    )
