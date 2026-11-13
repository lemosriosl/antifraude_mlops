"""
Acesso ao banco DO SISTEMA (antifraude). Encanamento — vem pronto.
O banco do MLflow é outro, e quem fala com ele é o próprio MLflow.
"""
from contextlib import contextmanager

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

import config

COLS_TRANSACAO = [
    "id_transacao", "id_cliente", "semana", "data_transacao",
    "valor_transacao", "hora_transacao", "dia_semana", "canal",
    "dispositivo_novo", "qtd_transacoes_1h", "valor_medio_30d",
    "razao_valor_media", "distancia_ultima_transacao_km", "idade_conta_dias",
    "destinatario_novo", "categoria_estabelecimento", "uf_cliente",
]


@contextmanager
def conexao():
    con = psycopg2.connect(config.URI_BANCO_APP)
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def consulta(sql, params=None):
    with conexao() as con:
        return pd.read_sql_query(sql, con, params=params)


def _py(v):
    """numpy/pandas -> tipo nativo, para o psycopg2."""
    if pd.isna(v):
        return None
    return v.item() if hasattr(v, "item") else v


# ------------------------------------------------------------- lotes -------
def semana_existe(semana):
    return not consulta("SELECT 1 FROM lotes WHERE semana = %s", (semana,)).empty


def inserir_lote(semana, arquivo, df, versao_contrato):
    linhas = [tuple(_py(v) for v in row) for row in df[COLS_TRANSACAO].itertuples(index=False)]
    with conexao() as con, con.cursor() as cur:
        cur.execute(
            "INSERT INTO lotes (semana, arquivo, qtd_linhas, versao_contrato) VALUES (%s, %s, %s, %s)",
            (semana, arquivo, len(df), versao_contrato))
        execute_values(cur, f"INSERT INTO transacoes ({', '.join(COLS_TRANSACAO)}) VALUES %s",
                       linhas, page_size=5000)


def transacoes_da_semana(semana):
    return consulta(f"SELECT {', '.join(COLS_TRANSACAO)} FROM transacoes WHERE semana = %s ORDER BY id_transacao",
                    (semana,))


def inserir_predicoes(semana, ids, scores, threshold, versao):
    linhas = [(i, semana, float(s), bool(s >= threshold), float(threshold), str(versao))
              for i, s in zip(ids, scores)]
    with conexao() as con, con.cursor() as cur:
        execute_values(cur, "INSERT INTO predicoes (id_transacao, semana, score, bloqueada, threshold, versao_modelo) VALUES %s",
                       linhas, page_size=5000)


# ------------------------------------------------------------ rótulos ------
def inserir_rotulos(df):
    """Insere só os rótulos de transações que o sistema conhece.
    Devolve (inseridos, desconhecidos, repetidos)."""
    conhecidos = set(consulta("SELECT id_transacao FROM transacoes WHERE id_transacao = ANY(%s)",
                              (list(df["id_transacao"]),))["id_transacao"])
    ok = df[df["id_transacao"].isin(conhecidos)]
    desconhecidos = len(df) - len(ok)
    linhas = [(r.id_transacao, int(r.fraude), _py(r.data_contestacao) or None) for r in ok.itertuples(index=False)]
    with conexao() as con, con.cursor() as cur:
        novos = execute_values(cur, """INSERT INTO rotulos (id_transacao, fraude, data_contestacao) VALUES %s
                                       ON CONFLICT (id_transacao) DO NOTHING RETURNING id_transacao""",
                               linhas, page_size=5000, fetch=True)
        inseridos = len(novos)
    return inseridos, desconhecidos, len(ok) - inseridos


# ------------------------------------------------------------- modelo ------
def ultima_troca():
    df = consulta("SELECT versao_nova, threshold FROM trocas_modelo ORDER BY id DESC LIMIT 1")
    return None if df.empty else df.iloc[0]


def registrar_troca(anterior, nova, threshold, motivo):
    with conexao() as con, con.cursor() as cur:
        cur.execute("INSERT INTO trocas_modelo (versao_anterior, versao_nova, threshold, motivo) VALUES (%s, %s, %s, %s)",
                    (anterior, nova, threshold, motivo))


def trocas():
    return consulta("SELECT trocado_em, versao_anterior, versao_nova, threshold, motivo FROM trocas_modelo ORDER BY id DESC")


# ------------------------------------------------------------- painel ------
SQL_VIGENTE = """
    SELECT DISTINCT ON (id_transacao) id_transacao, score, bloqueada, threshold, versao_modelo
    FROM predicoes ORDER BY id_transacao, id DESC
"""


def painel():
    df = consulta(f"""
        WITH vig AS ({SQL_VIGENTE})
        SELECT t.semana,
               count(*)                                                    AS volume,
               count(v.id_transacao)                                       AS pontuadas,
               count(*) FILTER (WHERE v.bloqueada)                         AS bloqueadas,
               coalesce(sum(t.valor_transacao) FILTER (WHERE v.bloqueada), 0)::float8 AS valor_bloqueado,
               count(r.id_transacao)                                       AS rotuladas,
               count(*) FILTER (WHERE r.fraude = 1)                        AS fraudes,
               coalesce(sum(t.valor_transacao) FILTER (WHERE r.fraude = 1 AND v.bloqueada), 0)::float8     AS fraude_evitada,
               coalesce(sum(t.valor_transacao) FILTER (WHERE r.fraude = 1 AND NOT v.bloqueada), 0)::float8 AS fraude_perdida,
               count(*) FILTER (WHERE r.fraude = 0 AND v.bloqueada)        AS legitimas_bloqueadas,
               string_agg(DISTINCT v.versao_modelo, ', ')                  AS versoes
        FROM transacoes t
        LEFT JOIN vig v USING (id_transacao)
        LEFT JOIN rotulos r USING (id_transacao)
        GROUP BY t.semana ORDER BY t.semana
    """)
    if df.empty:
        return df
    df["pct_bloqueado"] = df["bloqueadas"] / df["volume"]
    df["custo_total"] = df["fraude_perdida"].astype(float) + config.CUSTO_FALSO_POSITIVO * df["legitimas_bloqueadas"]
    sem_rotulo = df["rotuladas"] == 0
    df[["fraude_evitada", "fraude_perdida", "legitimas_bloqueadas", "custo_total"]] = (
        df[["fraude_evitada", "fraude_perdida", "legitimas_bloqueadas", "custo_total"]].astype(float))
    df.loc[sem_rotulo, ["fraude_evitada", "fraude_perdida", "legitimas_bloqueadas", "custo_total"]] = float("nan")
    return df


def dados_da_semana(semana):
    """Transações + predição vigente + rótulo (se já chegou). É o que o
    notebook baixa para monitorar."""
    return consulta(f"""
        WITH vig AS ({SQL_VIGENTE})
        SELECT t.*, v.score, v.bloqueada, v.threshold, v.versao_modelo, r.fraude
        FROM transacoes t
        LEFT JOIN vig v USING (id_transacao)
        LEFT JOIN rotulos r USING (id_transacao)
        WHERE t.semana = %s ORDER BY t.id_transacao
    """, (semana,))


def lotes():
    return consulta("""
        SELECT l.semana, l.arquivo, l.recebido_em, l.qtd_linhas, l.versao_contrato,
               (SELECT count(*) FROM rotulos r JOIN transacoes t USING (id_transacao) WHERE t.semana = l.semana) AS rotulos
        FROM lotes l ORDER BY l.semana
    """)


# ------------------------------------------------------------ decisões -----
def inserir_decisao(d):
    with conexao() as con, con.cursor() as cur:
        cur.execute("""INSERT INTO decisoes (semana, diagnostico, acao, retreinou, versao_modelo, versao_contrato, observacoes)
                       VALUES (%(semana)s, %(diagnostico)s, %(acao)s, %(retreinou)s, %(versao_modelo)s, %(versao_contrato)s, %(observacoes)s)""", d)


def decisoes():
    return consulta("SELECT * FROM decisoes ORDER BY semana, id")
