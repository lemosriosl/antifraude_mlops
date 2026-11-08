"""
Configuração do sistema. Tudo que muda de máquina para máquina vem do .env.

    python config.py      mostra as conexões e o comando para subir o MLflow
"""
import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent
load_dotenv(RAIZ / ".env")

# ------------------------------------------------------------- Postgres ----
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_USER = os.getenv("PG_USER", "postgres")
PG_SENHA = os.getenv("PG_SENHA", "postgres")
PG_DB_APP = os.getenv("PG_DB_APP", "antifraude")
PG_DB_MLFLOW = os.getenv("PG_DB_MLFLOW", "mlflow")


def uri_postgres(banco):
    return f"postgresql://{PG_USER}:{PG_SENHA}@{PG_HOST}:{PG_PORT}/{banco}"


URI_BANCO_APP = uri_postgres(PG_DB_APP)        # banco do sistema
URI_BANCO_MLFLOW = uri_postgres(PG_DB_MLFLOW)  # backend do MLflow

# --------------------------------------------------------------- MLflow ----
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
NOME_MODELO = os.getenv("NOME_MODELO", "antifraude")
ALIAS_PRODUCAO = "champion"
TAG_THRESHOLD = "threshold"   # tag da VERSÃO do modelo com o corte de bloqueio
TAG_MOTIVO = "motivo"         # tag da VERSÃO do modelo com o motivo da troca

# -------------------------------------------------------------- Sistema ----
SISTEMA_URL = os.getenv("SISTEMA_URL", "http://127.0.0.1:8000")

# --------------------------------------------------------------- Negócio ---
CUSTO_FALSO_POSITIVO = 15.0   # R$ por transação legítima bloqueada
# Falso negativo custa o próprio valor da transação (fraude aprovada).

# -------------------------------------------------------------- Arquivos ---
CONTRATO = RAIZ / "contrato" / "contrato_features.yaml"


if __name__ == "__main__":
    print("Banco do sistema :", URI_BANCO_APP)
    print("Banco do MLflow  :", URI_BANCO_MLFLOW)
    print("MLflow tracking  :", MLFLOW_TRACKING_URI)
    print()
    print("Para subir o MLflow (o servidor NÃO lê o .env, a conexão vai na linha de comando):")
    print(f"python -m mlflow server --host 127.0.0.1 --port 5000 "
          f"--backend-store-uri {URI_BANCO_MLFLOW} --default-artifact-root ./mlruns")
