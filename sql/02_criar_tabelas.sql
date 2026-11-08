-- Rode no banco do sistema:
--   psql -h localhost -U postgres -d antifraude -f sql/02_criar_tabelas.sql
--
-- O script é idempotente (IF NOT EXISTS): rodar duas vezes não quebra nada.
-- Nenhuma destas tabelas é do MLflow — ele cria as dele sozinho no banco mlflow.

-- Cada CSV de transações recebido é um lote (uma semana).
CREATE TABLE IF NOT EXISTS lotes (
    id               SERIAL PRIMARY KEY,
    semana           INTEGER     NOT NULL UNIQUE,
    arquivo          TEXT        NOT NULL,
    recebido_em      TIMESTAMP   NOT NULL DEFAULT now(),
    qtd_linhas       INTEGER     NOT NULL,
    versao_contrato  TEXT        NOT NULL
);

-- As transações exatamente como chegaram (metadados + 13 features do contrato).
CREATE TABLE IF NOT EXISTS transacoes (
    id_transacao                   TEXT PRIMARY KEY,
    id_cliente                     TEXT        NOT NULL,
    semana                         INTEGER     NOT NULL REFERENCES lotes (semana),
    data_transacao                 TIMESTAMP   NOT NULL,
    valor_transacao                NUMERIC(14,2) NOT NULL,
    hora_transacao                 SMALLINT    NOT NULL,
    dia_semana                     SMALLINT    NOT NULL,
    canal                          TEXT        NOT NULL,
    dispositivo_novo               SMALLINT    NOT NULL,
    qtd_transacoes_1h              INTEGER     NOT NULL,
    valor_medio_30d                NUMERIC(14,2) NOT NULL,
    razao_valor_media              DOUBLE PRECISION NOT NULL,
    distancia_ultima_transacao_km  DOUBLE PRECISION NOT NULL,
    idade_conta_dias               INTEGER     NOT NULL,
    destinatario_novo              SMALLINT    NOT NULL,
    categoria_estabelecimento      TEXT        NOT NULL,
    uf_cliente                     TEXT        NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_transacoes_semana ON transacoes (semana);

-- Toda vez que um modelo pontua uma transação, uma linha nova.
-- Repontuar um lote NÃO apaga a predição anterior: o histórico fica.
-- A predição "vigente" de uma transação é a de maior id.
CREATE TABLE IF NOT EXISTS predicoes (
    id               BIGSERIAL PRIMARY KEY,
    id_transacao     TEXT        NOT NULL REFERENCES transacoes (id_transacao),
    semana           INTEGER     NOT NULL,
    score            DOUBLE PRECISION NOT NULL,
    bloqueada        BOOLEAN     NOT NULL,
    threshold        DOUBLE PRECISION NOT NULL,
    versao_modelo    TEXT        NOT NULL,
    pontuado_em      TIMESTAMP   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_predicoes_transacao ON predicoes (id_transacao, id DESC);
CREATE INDEX IF NOT EXISTS ix_predicoes_semana ON predicoes (semana);

-- Contestações dos clientes: chegam com uma semana de atraso.
CREATE TABLE IF NOT EXISTS rotulos (
    id_transacao      TEXT PRIMARY KEY REFERENCES transacoes (id_transacao),
    fraude            SMALLINT    NOT NULL CHECK (fraude IN (0, 1)),
    data_contestacao  DATE,
    recebido_em       TIMESTAMP   NOT NULL DEFAULT now()
);

-- O sistema anota sozinho cada vez que o @champion muda de versão.
CREATE TABLE IF NOT EXISTS trocas_modelo (
    id                SERIAL PRIMARY KEY,
    trocado_em        TIMESTAMP   NOT NULL DEFAULT now(),
    versao_anterior   TEXT,
    versao_nova       TEXT        NOT NULL,
    threshold         DOUBLE PRECISION NOT NULL,
    motivo            TEXT
);

-- O seu registro de decisões, uma ou mais por semana.
CREATE TABLE IF NOT EXISTS decisoes (
    id                SERIAL PRIMARY KEY,
    registrado_em     TIMESTAMP   NOT NULL DEFAULT now(),
    semana            INTEGER     NOT NULL,
    diagnostico       TEXT        NOT NULL,
    acao              TEXT        NOT NULL,
    retreinou         BOOLEAN     NOT NULL,
    versao_modelo     TEXT,
    versao_contrato   TEXT,
    observacoes       TEXT
);
