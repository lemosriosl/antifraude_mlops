"""
Sistema de Prevenção a Fraudes — Banco Aurora.

    uvicorn app.main:app --reload --port 8000     (a partir da raiz do projeto)

O back é só API (JSON e CSV). O front são páginas HTML/CSS/JS puras, em
app/static/, que chamam estas rotas com fetch.

Páginas            Rotas da API que cada uma usa
------             -----------------------------
/        painel    GET  /api/painel
/lotes             GET  /api/lotes        POST /api/lotes   POST /api/lotes/{semana}/repontuar
/rotulos           GET  /api/lotes        POST /api/rotulos
/modelo            GET  /api/modelo
/decisoes          GET  /api/decisoes     POST /api/decisoes
(todas)            GET  /api/saude        (selo do modelo no topo)

Outras rotas
------------
POST /predict                         pontua transações avulsas (lista de JSON com as 13 features)
GET  /api/semanas/{semana}/dados.csv  transações + predição vigente + rótulo (o que o monitoramento lê)
GET  /api/painel.csv                  o painel em CSV
GET  /api/decisoes/exportar.csv       suas decisões, para a entrega
GET  /saude                           atalho para /api/saude
"""
import io
import json
from typing import Any

import pandas as pd
from fastapi import FastAPI, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from app import banco, contrato
from app.modelo import SemModeloEmProducao, producao

STATIC = config.RAIZ / "app" / "static"
app = FastAPI(title="Banco Aurora — Prevenção a Fraudes")


def _json(df):
    """DataFrame -> JSON (datas em ISO, NaN vira null)."""
    return Response(df.to_json(orient="records", date_format="iso", force_ascii=False),
                    media_type="application/json")


def _csv(df, nome=None):
    headers = {"Content-Disposition": f"attachment; filename={nome}"} if nome else None
    return Response(df.to_csv(index=False), media_type="text/csv", headers=headers)


def _erro(status, erro, detalhes=None):
    return JSONResponse({"erro": erro, "detalhes": detalhes or []}, status_code=status)


def _status_modelo():
    try:
        p = producao.atualizar()
        return {"ok": True, "versao": p.versao, "threshold": p.threshold, "run_id": p.run_id, "descricao": p.descricao}
    except SemModeloEmProducao as e:
        return {"ok": False, "erro": str(e)}
    except Exception as e:  # MLflow fora do ar, por exemplo
        return {"ok": False, "erro": f"Não consegui falar com o MLflow: {e}"}


def _pontuar_semana(semana):
    df = banco.transacoes_da_semana(semana)
    scores = producao.pontuar(df)
    banco.inserir_predicoes(semana, df["id_transacao"], scores, producao.threshold, producao.versao)
    return len(df), float((scores >= producao.threshold).mean())


# ------------------------------------------------------------- saúde -------
@app.get("/api/saude")
def saude():
    return {"sistema": "ok", "contrato": contrato.carregar()["versao"], "modelo": _status_modelo()}


app.get("/saude", include_in_schema=False)(saude)


# ------------------------------------------------------------- painel ------
@app.get("/api/painel")
def painel():
    return _json(banco.painel())


@app.get("/api/painel.csv")
def painel_csv():
    return _csv(banco.painel(), "painel.csv")


# ------------------------------------------------------------- lotes -------
@app.get("/api/lotes")
def lotes():
    return _json(banco.lotes())


@app.post("/api/lotes")
async def receber_lote(arquivo: UploadFile):
    try:
        bruto = pd.read_csv(io.BytesIO(await arquivo.read()), dtype={"id_transacao": str, "id_cliente": str})
    except Exception as e:
        return _erro(400, f"Não consegui ler '{arquivo.filename}' como CSV: {e}")
    c = contrato.carregar()
    df, erros = contrato.validar(bruto, c)
    if erros:
        return _erro(422, f"Lote '{arquivo.filename}' REJEITADO pelo contrato v{c['versao']}.", erros)
    semana = int(df["semana"].iloc[0])
    if banco.semana_existe(semana):
        return _erro(409, f"A semana {semana} já foi recebida. Para pontuar de novo com o modelo atual, use 'Repontuar'.")
    banco.inserir_lote(semana, arquivo.filename, df, c["versao"])
    try:
        n, pct = _pontuar_semana(semana)
    except SemModeloEmProducao as e:
        return {"semana": semana, "pontuada": False, "msg": f"Semana {semana} recebida, mas NÃO pontuada: {e}"}
    return {"semana": semana, "pontuada": True, "transacoes": n, "pct_bloqueado": pct, "versao_modelo": producao.versao,
            "msg": f"Semana {semana}: {n} transações recebidas e pontuadas pelo modelo v{producao.versao}."}


@app.post("/api/lotes/{semana}/repontuar")
def repontuar(semana: int):
    if not banco.semana_existe(semana):
        return _erro(404, f"A semana {semana} não foi recebida.")
    try:
        n, pct = _pontuar_semana(semana)
    except SemModeloEmProducao as e:
        return _erro(503, str(e))
    return {"semana": semana, "transacoes": n, "pct_bloqueado": pct, "versao_modelo": producao.versao,
            "msg": f"Semana {semana} repontuada pelo modelo v{producao.versao}. "
                   "A predição anterior continua no banco; o painel passa a usar esta."}


@app.get("/api/semanas/{semana}/dados.csv")
def dados_semana(semana: int):
    return _csv(banco.dados_da_semana(semana), f"semana_{semana:02d}.csv")


# ------------------------------------------------------------ rótulos ------
@app.post("/api/rotulos")
async def receber_rotulos(arquivo: UploadFile):
    try:
        df = pd.read_csv(io.BytesIO(await arquivo.read()), dtype={"id_transacao": str})
    except Exception as e:
        return _erro(400, f"Não consegui ler '{arquivo.filename}' como CSV: {e}")
    faltando = {"id_transacao", "fraude", "data_contestacao"} - set(df.columns)
    if faltando:
        return _erro(422, f"Colunas ausentes: {', '.join(sorted(faltando))}")
    if not df["fraude"].isin([0, 1]).all():
        return _erro(422, "A coluna fraude só aceita 0 ou 1.")
    inseridos, desconhecidos, repetidos = banco.inserir_rotulos(df)
    msg = f"{arquivo.filename}: {inseridos} rótulos gravados"
    if repetidos:
        msg += f", {repetidos} já existiam (ignorados)"
    if desconhecidos:
        msg += f", {desconhecidos} de transações que o sistema não recebeu (ignorados)"
    return {"inseridos": inseridos, "repetidos": repetidos, "desconhecidos": desconhecidos, "msg": msg + "."}


# ------------------------------------------------------------- modelo ------
@app.get("/api/modelo")
def modelo():
    trocas = json.loads(banco.trocas().to_json(orient="records", date_format="iso", force_ascii=False))
    return {"modelo": _status_modelo(), "contrato": contrato.carregar()["versao"], "trocas": trocas}


@app.post("/predict")
def predict(transacoes: list[dict[str, Any]]):
    """Recebe uma lista de transações (só as 13 features) e devolve score e decisão."""
    df, erros = contrato.validar(pd.DataFrame(transacoes), exigir_metadados=False)
    if erros:
        return _erro(422, "Transações fora do contrato.", erros)
    try:
        scores = producao.pontuar(df)
    except SemModeloEmProducao as e:
        return _erro(503, str(e))
    return [{"score": round(float(s), 6), "bloquear": bool(s >= producao.threshold),
             "threshold": producao.threshold, "versao_modelo": producao.versao} for s in scores]


# ------------------------------------------------------------ decisões -----
class Decisao(BaseModel):
    semana: int
    diagnostico: str
    acao: str
    retreinou: bool = False
    observacoes: str = ""


@app.get("/api/decisoes")
def decisoes():
    return _json(banco.decisoes())


@app.post("/api/decisoes")
def registrar_decisao(d: Decisao):
    if not d.diagnostico.strip() or not d.acao.strip():
        return _erro(422, "Diagnóstico e ação são obrigatórios.")
    if not banco.semana_existe(d.semana):
        return _erro(422, f"A semana {d.semana} não foi recebida.")
    st = _status_modelo()
    banco.inserir_decisao({
        "semana": d.semana, "diagnostico": d.diagnostico.strip(), "acao": d.acao.strip(),
        "retreinou": d.retreinou, "observacoes": d.observacoes.strip() or None,
        "versao_modelo": str(st["versao"]) if st["ok"] else None,
        "versao_contrato": contrato.carregar()["versao"],
    })
    return {"msg": f"Decisão da semana {d.semana} registrada."}


@app.get("/api/decisoes/exportar.csv")
def exportar_decisoes():
    return _csv(banco.decisoes(), "decisoes.csv")


# ------------------------------------------------------------- páginas -----
# Endereços limpos para as páginas. O resto (css, js) sai do StaticFiles.
def _pagina(arquivo):
    def servir():
        return FileResponse(STATIC / arquivo)
    return servir


for _rota, _arquivo in {"/": "index.html", "/lotes": "lotes.html", "/rotulos": "rotulos.html",
                        "/modelo": "modelo.html", "/decisoes": "decisoes.html"}.items():
    app.get(_rota, include_in_schema=False)(_pagina(_arquivo))

app.mount("/static", StaticFiles(directory=STATIC), name="static")
