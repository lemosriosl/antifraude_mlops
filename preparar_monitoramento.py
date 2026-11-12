"""Cria a referência do champion e o relatório zero (semanas 11 e 12).

Execute na raiz do projeto com o MLflow ligado: python preparar_monitoramento.py
"""

import importlib
import json
from pathlib import Path

import mlflow
import mlflow.sklearn
import pandas as pd
from mlflow.tracking import MlflowClient

import config
import monitoramento
from app.contrato import carregar


def preparar(pasta=Path("referencia"), pasta_relatorio=Path("relatorio_zero")):
    pasta, pasta_relatorio = Path(pasta), Path(pasta_relatorio)
    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
    cliente = MlflowClient()
    versao = cliente.get_model_version_by_alias(config.NOME_MODELO, config.ALIAS_PRODUCAO)
    threshold = float(versao.tags[config.TAG_THRESHOLD])
    contrato = carregar()
    features = [f["nome"] for f in contrato["features"]]

    transacoes = pd.read_csv(config.RAIZ / "dados/transacoes_semanas_01_12.csv",
                             dtype={"id_transacao": str, "id_cliente": str})
    rotulos = pd.read_csv(config.RAIZ / "dados/rotulos_semanas_01_12.csv",
                          dtype={"id_transacao": str})
    validacao = transacoes.loc[transacoes["semana"].isin([11, 12])].merge(
        rotulos[["id_transacao", "fraude"]], on="id_transacao", how="left", validate="one_to_one")
    if validacao.empty or validacao["fraude"].isna().any() or validacao["id_transacao"].duplicated().any():
        raise ValueError("Validação das semanas 11 e 12 vazia, incompleta ou duplicada")

    modelo = mlflow.sklearn.load_model(f"models:/{config.NOME_MODELO}/{versao.version}")
    validacao["score"] = modelo.predict_proba(validacao[features])[:, 1]
    validacao = validacao[["id_transacao", "semana", *features, "score", "fraude"]]
    pasta.mkdir(parents=True, exist_ok=True)
    caminho_ref = pasta / "validacao_11_12.csv"
    validacao.to_csv(caminho_ref, index=False)
    (pasta / "metadados.json").write_text(json.dumps({
        "modelo": config.NOME_MODELO, "versao": str(versao.version),
        "run_id": versao.run_id, "threshold": threshold,
        "semanas": [11, 12], "linhas": len(validacao),
        "versao_contrato": str(contrato["versao"]),
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    mlflow.log_artifacts(str(pasta), artifact_path="referencia", run_id=versao.run_id)

    semana11 = validacao.loc[validacao["semana"] == 11].copy()
    semana12 = validacao.loc[validacao["semana"] == 12].copy()
    # O notebook pode ter importado monitoramento.py antes de ele ser editado.
    tabelas = importlib.reload(monitoramento).monitorar(semana11, semana12, threshold)
    pasta_relatorio.mkdir(parents=True, exist_ok=True)
    for nome, tabela in tabelas.items():
        if tabela is not None:
            tabela.to_csv(pasta_relatorio / f"{nome}.csv", index=False)
    return versao, tabelas


if __name__ == "__main__":
    versao, tabelas = preparar()
    print(f"Champion v{versao.version} | run {versao.run_id}")
    for nome, tabela in tabelas.items():
        print(f"\n{nome}\n{tabela.to_string(index=False) if tabela is not None else 'Rótulos pendentes'}")
