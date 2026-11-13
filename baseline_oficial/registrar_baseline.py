"""
Registra o BASELINE OFICIAL no seu MLflow, como uma nova versão do modelo
`antifraude`. Rode a partir da raiz do projeto (pasta antifraude_mlops/), com
o MLflow no ar:

    python baseline_oficial/registrar_baseline.py              # só registra
    python baseline_oficial/registrar_baseline.py --promover   # registra e aponta o @champion para ele

Sem --promover, o seu champion atual continua em produção: você pode comparar
os dois antes de decidir. O script não apaga nem altera nenhuma versão sua.
"""
import argparse
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))  # para achar o config.py da raiz

import mlflow  # noqa: E402
from mlflow.models import Model  # noqa: E402
from mlflow.tracking import MlflowClient  # noqa: E402

import config  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--promover", action="store_true", help="aponta o alias champion para a versão registrada")
args = ap.parse_args()

info = json.loads((AQUI / "metricas.json").read_text(encoding="utf-8"))
m = info["metricas_validacao"]
mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
mlflow.set_experiment("antifraude-baseline-oficial")

modelo = mlflow.sklearn.load_model(str(AQUI / "modelo"))
assinatura = Model.load(str(AQUI / "modelo")).signature
exemplo = __import__("pandas").read_csv(AQUI / "referencia" / "referencia_validacao.csv", nrows=3)
exemplo = exemplo[[c.name for c in assinatura.inputs.inputs]]

with mlflow.start_run(run_name="baseline_oficial") as run:
    mlflow.log_params({"algoritmo": info["algoritmo"], "treino": info["treino"],
                       "validacao": info["validacao"], "versao_contrato": info["versao_contrato"],
                       "origem": "baseline oficial do instrutor"})
    mlflow.log_metrics(m)
    mlflow.sklearn.log_model(modelo, "modelo", signature=assinatura, input_example=exemplo)
    mlflow.log_artifacts(str(AQUI / "referencia"), "referencia")

cli = MlflowClient()
mv = mlflow.register_model(f"runs:/{run.info.run_id}/modelo", config.NOME_MODELO)
cli.set_model_version_tag(config.NOME_MODELO, mv.version, config.TAG_THRESHOLD, str(m["threshold"]))
cli.set_model_version_tag(config.NOME_MODELO, mv.version, config.TAG_MOTIVO, "baseline oficial (liberado na parte 2)")
cli.set_model_version_tag(config.NOME_MODELO, mv.version, "versao_contrato", info["versao_contrato"])
cli.update_model_version(config.NOME_MODELO, mv.version,
                         f"Baseline oficial | {info['algoritmo']} | treino {info['treino']}, validação {info['validacao']} | "
                         f"threshold {m['threshold']} pelo menor custo na validação (R$ {m['custo_validacao']:,.0f})")
print(f"registrado: {config.NOME_MODELO} v{mv.version} (run {run.info.run_id})")
print(f"validação: PR-AUC {m['pr_auc']} | threshold {m['threshold']} | recall {m['recall']} | custo R$ {m['custo_validacao']:,.2f}")
if args.promover:
    cli.set_registered_model_alias(config.NOME_MODELO, config.ALIAS_PRODUCAO, mv.version)
    print(f"@{config.ALIAS_PRODUCAO} -> v{mv.version}. O sistema passa a usá-lo na próxima chamada.")
else:
    print(f"@{config.ALIAS_PRODUCAO} NÃO foi alterado. Para promover depois: rode de novo com --promover "
          f"ou mova o alias na interface do MLflow.")
