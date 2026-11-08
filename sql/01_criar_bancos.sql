-- Rode conectado ao banco padrão (postgres):
--   psql -h localhost -U postgres -f sql/01_criar_bancos.sql
--
-- Um servidor, dois bancos — igual nas aulas:
--   antifraude  o banco DO SISTEMA (lotes, predições, rótulos, decisões)
--   mlflow      o backend do MLflow (runs, métricas, Model Registry)
--
-- Se algum dos dois já existir, o psql avisa e segue para o próximo.

CREATE DATABASE antifraude;
CREATE DATABASE mlflow;
