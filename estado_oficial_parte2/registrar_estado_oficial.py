"""
Registra o ESTADO OFICIAL PÓS-PARTE 2 no seu MLflow, como uma nova versão do
modelo `antifraude`. Rode a partir da raiz do projeto, com o MLflow no ar:

    python estado_oficial_parte2/registrar_estado_oficial.py              # só registra
    python estado_oficial_parte2/registrar_estado_oficial.py --promover   # registra e aponta o @champion para ele

O contrato NÃO é trocado pelo script: copie estado_oficial_parte2/contrato_features.yaml
para contrato/contrato_features.yaml (veja o LEIAME.md).
"""
import argparse
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))

import mlflow  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402
from mlflow.models import Model  # noqa: E402
from mlflow.tracking import MlflowClient  # noqa: E402

import config  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--promover", action="store_true", help="aponta o alias champion para a versão registrada")
args = ap.parse_args()

info = json.loads((AQUI / "estado.json").read_text(encoding="utf-8"))
mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
mlflow.set_experiment("antifraude-estado-oficial")

modelo = mlflow.sklearn.load_model(str(AQUI / "modelo"))
assinatura = Model.load(str(AQUI / "modelo")).signature
exemplo = pd.read_csv(AQUI / "referencia" / "referencia_validacao.csv", nrows=3)[[c.name for c in assinatura.inputs.inputs]]
codigo = [str(AQUI / "conversao_utc.py")] if (AQUI / "conversao_utc.py").exists() else None

with mlflow.start_run(run_name="estado_oficial_pos_parte2") as run:
    mlflow.log_params({"origem": "estado oficial do instrutor (pós-parte 2)", "turma": info["turma"],
                       "versao_contrato": "1.1", "retreino": "não"})
    mlflow.sklearn.log_model(modelo, "modelo", signature=assinatura, input_example=exemplo, code_paths=codigo)
    mlflow.log_artifacts(str(AQUI / "referencia"), "referencia")

cli = MlflowClient()
mv = mlflow.register_model(f"runs:/{run.info.run_id}/modelo", config.NOME_MODELO)
for chave, valor in {config.TAG_THRESHOLD: str(info["threshold"]), config.TAG_MOTIVO: f"estado oficial pós-parte 2 ({info['versao']})",
                     "versao_contrato": "1.1", "referencia_vigente": info["referencia_vigente"]}.items():
    cli.set_model_version_tag(config.NOME_MODELO, mv.version, chave, valor)
cli.update_model_version(config.NOME_MODELO, mv.version, info["descricao"])
print(f"registrado: {config.NOME_MODELO} v{mv.version} (run {run.info.run_id})")
print(f"referência vigente: referencia/{info['referencia_vigente']}")
if args.promover:
    cli.set_registered_model_alias(config.NOME_MODELO, config.ALIAS_PRODUCAO, mv.version)
    print(f"@{config.ALIAS_PRODUCAO} -> v{mv.version}. O sistema passa a usá-lo na próxima chamada.")
else:
    print(f"@{config.ALIAS_PRODUCAO} NÃO foi alterado. Para promover depois: rode de novo com --promover.")

atual = yaml.safe_load(Path(config.CONTRATO).read_text(encoding="utf-8"))
oficial = yaml.safe_load((AQUI / "contrato_features.yaml").read_text(encoding="utf-8"))
if atual != oficial:
    print("\nATENÇÃO: o seu contrato/contrato_features.yaml é diferente do contrato oficial v1.1. Se for adotar o estado "
          "oficial, copie estado_oficial_parte2/contrato_features.yaml para contrato/contrato_features.yaml.")
