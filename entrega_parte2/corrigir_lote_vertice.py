"""Reprocessa um lote da Vértice cujo horário de origem foi declarado como UTC."""

import argparse
import hashlib
import json
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen

import mlflow.sklearn
import numpy as np
import pandas as pd
import yaml
from psycopg2.extras import Json, execute_values

import config
from app import banco, contrato


VERSAO_CORRECAO = "1.1.1"
PRIMEIRA_SEMANA_VERTICE = 14
INICIO_SEMANA_14 = pd.Timestamp("2026-08-31")


def normalizar_lote_utc(lote, semana):
    """Converte o timestamp da origem e deriva hora e dia no fuso do contrato."""
    if semana < PRIMEIRA_SEMANA_VERTICE or not pd.to_numeric(lote["semana"]).eq(semana).all():
        raise ValueError("O arquivo deve conter apenas a semana selecionada da Vértice")
    utc = pd.to_datetime(lote["data_transacao"], utc=True)
    if not (lote["hora_transacao"].eq(utc.dt.hour) & lote["dia_semana"].eq(utc.dt.dayofweek)).all():
        raise ValueError("Hora e dia do arquivo divergem do timestamp declarado em UTC")
    local = utc.dt.tz_convert("America/Sao_Paulo").dt.tz_localize(None)
    inicio = INICIO_SEMANA_14 + pd.Timedelta(weeks=semana - PRIMEIRA_SEMANA_VERTICE)
    if not (local.ge(inicio) & local.lt(inicio + pd.Timedelta(weeks=1))).all():
        raise ValueError("Ainda há timestamps fora da janela semanal depois da conversão")
    return lote.assign(data_transacao=local, hora_transacao=local.dt.hour, dia_semana=local.dt.dayofweek)


def validar_dados(lote):
    dados, erros = contrato.validar(lote)
    if erros:
        raise ValueError("; ".join(erros))
    return dados.sort_values("id_transacao").reset_index(drop=True)


def resumo(lote, scores, corte):
    retidas = scores >= corte
    return {
        "transacoes": len(lote),
        "retidas": int(retidas.sum()),
        "taxa_retencao": float(retidas.mean()),
        "valor_retido": round(float(lote.loc[retidas, "valor_transacao"].sum()), 2),
        "clientes_retidos": int(lote.loc[retidas, "id_cliente"].nunique()),
    }


def aplicar(semana, original, corrigido, scores_originais, scores_corrigidos, evidencia):
    """Grava o lote reemitido e as novas predições na mesma transação."""
    modelo = evidencia["modelo"]
    with banco.conexao() as con, con.cursor() as cur:
        cur.execute("SELECT arquivo, qtd_linhas, versao_contrato FROM lotes WHERE semana = %s FOR UPDATE", (semana,))
        if cur.fetchone() != (evidencia["arquivo"], len(original), evidencia["contrato"]):
            raise ValueError("O arquivo não corresponde ao lote registrado no sistema")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS correcoes_horario_lote (
                semana INTEGER PRIMARY KEY REFERENCES lotes (semana),
                aplicado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
                evidencia JSONB NOT NULL
            )
        """)
        cur.execute("SELECT evidencia FROM correcoes_horario_lote WHERE semana = %s", (semana,))
        anterior = cur.fetchone()
        if anterior is not None:
            gravado = anterior[0]
            if any(gravado[chave] != evidencia[chave] for chave in ("sha256_original", "sha256_corrigido", "modelo")):
                raise ValueError("A semana já tem uma correção com outro arquivo ou modelo")
            return gravado

        cur.execute("""
            SELECT t.id_transacao, t.data_transacao, t.hora_transacao, t.dia_semana,
                   p.score, p.threshold, p.versao_modelo, p.id
            FROM transacoes t
            JOIN LATERAL (
                SELECT id, score, threshold, versao_modelo FROM predicoes
                WHERE id_transacao = t.id_transacao ORDER BY id DESC LIMIT 1
            ) p ON true
            WHERE t.semana = %s ORDER BY t.id_transacao
            FOR UPDATE OF t
        """, (semana,))
        vigente = pd.DataFrame(cur.fetchall(), columns=[
            "id_transacao", "data_transacao", "hora_transacao", "dia_semana",
            "score", "threshold", "versao_modelo", "predicao_id",
        ])
        campos = ["id_transacao", "data_transacao", "hora_transacao", "dia_semana"]
        esperado = original[campos].assign(data_transacao=pd.to_datetime(original["data_transacao"]))
        pd.testing.assert_frame_equal(vigente[campos], esperado, check_dtype=False)
        if not (vigente["versao_modelo"].eq(modelo["versao"]).all()
                and vigente["threshold"].eq(modelo["threshold"]).all()
                and np.allclose(vigente["score"], scores_originais, atol=1e-12, rtol=0)):
            raise ValueError("A exportação do modelo não reproduziu as predições originais")

        linhas = [(i, d.to_pydatetime(), int(h), int(dia)) for i, d, h, dia in
                  corrigido[campos].itertuples(index=False, name=None)]
        atualizadas = execute_values(cur, """
            UPDATE transacoes t
            SET data_transacao = v.data_transacao, hora_transacao = v.hora, dia_semana = v.dia
            FROM (VALUES %s) AS v(id_transacao, data_transacao, hora, dia)
            WHERE t.id_transacao = v.id_transacao RETURNING t.id_transacao
        """, linhas, page_size=5000, fetch=True)
        if len(atualizadas) != len(corrigido):
            raise ValueError("A atualização de horários não cobriu todo o lote")
        corte = modelo["threshold"]
        predicoes = execute_values(cur, """
            INSERT INTO predicoes (id_transacao, semana, score, bloqueada, threshold, versao_modelo)
            VALUES %s RETURNING id
        """, [(i, semana, float(s), bool(s >= corte), corte, modelo["versao"])
              for i, s in zip(corrigido["id_transacao"], scores_corrigidos)], page_size=5000, fetch=True)
        auditoria = {**evidencia, "predicoes_originais": [int(vigente["predicao_id"].min()), int(vigente["predicao_id"].max())],
                     "predicoes_corrigidas": [predicoes[0][0], predicoes[-1][0]]}
        cur.execute("INSERT INTO correcoes_horario_lote (semana, evidencia) VALUES (%s, %s)", (semana, Json(auditoria)))
        return auditoria


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("semana", type=int)
    parser.add_argument("--origem", required=True, choices=["vertice-utc"])
    parser.add_argument("--modelo", type=Path, default=Path("entrega/modelo_exportado"))
    parser.add_argument("--aplicar", action="store_true", help="grava a correção no lote já recebido")
    args = parser.parse_args()

    caminho = config.RAIZ / "dados" / "parte2" / f"transacoes_semana_{args.semana}.csv"
    bruto = caminho.read_bytes()
    original = validar_dados(pd.read_csv(BytesIO(bruto), dtype={"id_transacao": str, "id_cliente": str}))
    corrigido = validar_dados(normalizar_lote_utc(original, args.semana))
    csv_corrigido = corrigido.to_csv(index=False, lineterminator="\n").encode("utf-8")

    registro = yaml.safe_load((args.modelo / "registered_model_meta").read_text(encoding="utf-8"))
    artefato = yaml.safe_load((args.modelo / "MLmodel").read_text(encoding="utf-8"))
    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
    versao = mlflow.MlflowClient().get_model_version_by_alias(config.NOME_MODELO, config.ALIAS_PRODUCAO)
    corte = float(versao.tags[config.TAG_THRESHOLD])
    if (registro["model_name"], str(registro["model_version"]), artefato["run_id"]) != (
            config.NOME_MODELO, str(versao.version), versao.run_id):
        raise ValueError("A exportação informada não corresponde ao champion no MLflow")
    modelo = mlflow.sklearn.load_model(str(args.modelo))
    colunas = contrato.nomes_features()
    scores_originais = modelo.predict_proba(contrato.tipar(original[colunas]))[:, 1]
    scores_corrigidos = modelo.predict_proba(contrato.tipar(corrigido[colunas]))[:, 1]
    evidencia = {
        "semana": args.semana, "arquivo": caminho.name, "versao_correcao": VERSAO_CORRECAO,
        "origem": args.origem, "destino": "America/Sao_Paulo", "contrato": str(contrato.carregar()["versao"]),
        "sha256_original": hashlib.sha256(bruto).hexdigest(),
        "sha256_corrigido": hashlib.sha256(csv_corrigido).hexdigest(),
        "modelo": {"versao": str(versao.version), "run_id": versao.run_id, "threshold": corte},
        "antes": resumo(original, scores_originais, corte), "depois": resumo(corrigido, scores_corrigidos, corte),
    }
    if args.aplicar:
        with urlopen(f"{config.SISTEMA_URL.rstrip('/')}/api/saude", timeout=30) as resposta:
            status = json.load(resposta)["modelo"]
        if not (status["ok"] and str(status["versao"]) == str(versao.version) and status["threshold"] == corte):
            raise ValueError("O champion da API não corresponde ao champion do MLflow")
        evidencia = aplicar(args.semana, original, corrigido, scores_originais, scores_corrigidos, evidencia)
        pasta = config.RAIZ / "monitoramento" / f"semana_{args.semana:02d}" / "apos_correcao"
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / f"transacoes_semana_{args.semana:02d}_corrigidas.csv").write_bytes(csv_corrigido)
        (pasta / "correcao_horario.json").write_text(json.dumps(evidencia, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidencia, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
