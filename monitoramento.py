"""Tabelas de monitoramento semanal do modelo antifraude."""

from io import BytesIO
from urllib.request import urlopen

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, ks_2samp
from sklearn.metrics import average_precision_score, precision_score, recall_score

from features import carregar_contrato

LIMITE_KS_D = 0.10
LIMITE_PROPORCAO_PP = 5.0
LIMITE_TAXA_BLOQUEIO_PP = 1.0
LIMITE_PCT_VALOR_BLOQUEADO_PP = 3.0
LIMITE_QUEDA_GLOBAL_PP = 5.0
LIMITE_QUEDA_SEGMENTO_PP = 10.0
MIN_FRAUDES_SEGMENTO = 100
LIMITE_AUMENTO_CUSTO_POR_MIL = 0.50


def custo_decisao(y_true, valores, scores, threshold, custo_legitima_bloqueada=15.0):
    """Fraudes aprovadas + custo fixo por transação legítima bloqueada."""
    y_true = np.asarray(y_true)
    valores = np.asarray(valores, dtype=float)
    bloqueada = np.asarray(scores, dtype=float) >= threshold
    return float(valores[(y_true == 1) & ~bloqueada].sum()
                 + custo_legitima_bloqueada * ((y_true == 0) & bloqueada).sum())


def colunas_monitoradas(contrato=None):
    """Features contínuas e discretas conforme o contrato, mais score."""
    contrato = contrato or carregar_contrato()
    continuas = [f["nome"] for f in contrato["features"]
                 if f["tipo"] == "float" or (f["tipo"] == "int" and f["nome"] not in {"hora_transacao", "dia_semana"})]
    discretas = [f["nome"] for f in contrato["features"] if f["nome"] not in continuas]
    return continuas + ["score"], discretas


def _exigir_colunas(df, colunas, nome):
    faltantes = set(colunas) - set(df.columns)
    if faltantes:
        raise ValueError(f"{nome}: faltam colunas {sorted(faltantes)}")


def drift_continuas(referencia, lote, colunas=None):
    """KS de duas amostras: estatística D e p-valor."""
    colunas = colunas if colunas is not None else colunas_monitoradas()[0]
    _exigir_colunas(referencia, colunas, "referência")
    _exigir_colunas(lote, colunas, "lote")
    linhas = []
    for coluna in colunas:
        a = pd.to_numeric(referencia[coluna], errors="coerce").dropna().to_numpy()
        b = pd.to_numeric(lote[coluna], errors="coerce").dropna().to_numpy()
        teste = ks_2samp(a, b) if len(a) and len(b) else None
        linhas.append({
            "variavel": coluna, "n_referencia": len(a), "n_lote": len(b),
            "media_referencia": float(a.mean()) if len(a) else np.nan,
            "media_lote": float(b.mean()) if len(b) else np.nan,
            "D": float(teste.statistic) if teste else np.nan,
            "p_valor": float(teste.pvalue) if teste else np.nan,
        })
    tabela = pd.DataFrame(linhas)
    tabela["alerta"] = tabela["D"] > LIMITE_KS_D
    return tabela


def drift_discretas(referencia, lote, colunas=None):
    """Qui-quadrado e maior mudança de proporção (pontos percentuais)."""
    colunas = colunas if colunas is not None else colunas_monitoradas()[1]
    _exigir_colunas(referencia, colunas, "referência")
    _exigir_colunas(lote, colunas, "lote")
    linhas = []
    for coluna in colunas:
        a = referencia[coluna].astype("string").fillna("<ausente>")
        b = lote[coluna].astype("string").fillna("<ausente>")
        categorias = list(pd.concat([a, b]).unique())
        n_a, n_b = len(a), len(b)
        cont_a = a.value_counts().reindex(categorias, fill_value=0).to_numpy()
        cont_b = b.value_counts().reindex(categorias, fill_value=0).to_numpy()
        if n_a and n_b:
            dif = np.abs(cont_a / n_a - cont_b / n_b)
            maior = int(np.argmax(dif))
            p = float(chi2_contingency(np.vstack([cont_a, cont_b]))[1]) if len(categorias) > 1 else 1.0
            mudanca = float(100 * dif[maior])
            categoria = str(categorias[maior])
        else:
            p, mudanca, categoria = np.nan, np.nan, None
        linhas.append({
            "variavel": coluna, "n_referencia": n_a, "n_lote": n_b,
            "categorias": len(categorias), "categoria_maior_mudanca": categoria,
            "maior_mudanca_pp": mudanca, "p_valor": p,
        })
    tabela = pd.DataFrame(linhas)
    tabela["alerta"] = tabela["maior_mudanca_pp"] > LIMITE_PROPORCAO_PP
    return tabela


def saida_modelo(referencia, lote, threshold):
    """Taxa, contagem e valor bloqueado do modelo em cada conjunto."""
    linhas = []
    for nome, df in (("referencia", referencia), ("lote", lote)):
        _exigir_colunas(df, ["score", "valor_transacao"], nome)
        score = pd.to_numeric(df["score"], errors="coerce")
        valor = pd.to_numeric(df["valor_transacao"], errors="coerce")
        if score.isna().any() or valor.isna().any():
            raise ValueError(f"{nome}: score ou valor_transacao ausente/inválido")
        bloqueada = score >= threshold
        linhas.append({
            "conjunto": nome, "transacoes": len(df), "bloqueios": int(bloqueada.sum()),
            "taxa_bloqueio": float(bloqueada.mean()) if len(df) else np.nan,
            "valor_bloqueado": float(valor.loc[bloqueada].sum()),
            "valor_total": float(valor.sum()),
            "pct_valor_bloqueado": float(valor.loc[bloqueada].sum() / valor.sum()) if valor.sum() else np.nan,
        })
    tabela = pd.DataFrame(linhas)
    tabela["delta_taxa_bloqueio_pp"] = (tabela["taxa_bloqueio"] - tabela.loc[0, "taxa_bloqueio"]) * 100
    tabela["delta_pct_valor_bloqueado_pp"] = (tabela["pct_valor_bloqueado"] - tabela.loc[0, "pct_valor_bloqueado"]) * 100
    tabela["alerta"] = (tabela["delta_taxa_bloqueio_pp"].abs() > LIMITE_TAXA_BLOQUEIO_PP) | (
        tabela["delta_pct_valor_bloqueado_pp"].abs() > LIMITE_PCT_VALOR_BLOQUEADO_PP)
    return tabela


def performance(referencia, lote, threshold, segmento="canal", custo_legitima_bloqueada=15.0):
    """Recall, precision, PR-AUC (average precision) e custo, globais e por segmento.

    Rótulos parciais geram erro. Recall sem fraudes e PR-AUC de grupos com
    uma única classe são indefinidos (NaN).
    """
    linhas = []
    for nome, df in (("referencia", referencia), ("lote", lote)):
        _exigir_colunas(df, ["fraude", "score", "valor_transacao", segmento], nome)
        if df["fraude"].isna().any():
            raise ValueError(f"{nome}: rótulos incompletos")
        if not df["fraude"].isin([0, 1]).all():
            raise ValueError(f"{nome}: fraude deve conter apenas 0 e 1")
        if df[["score", "valor_transacao"]].isna().any().any():
            raise ValueError(f"{nome}: score ou valor_transacao ausente")
        grupos = [("global", "todos", df)]
        grupos += [(segmento, str(valor), grupo) for valor, grupo in df.groupby(segmento, dropna=False)]
        for tipo, valor, grupo in grupos:
            y = grupo["fraude"].to_numpy(dtype=int)
            score = grupo["score"].to_numpy(dtype=float)
            bloqueada = score >= threshold
            linhas.append({
                "conjunto": nome, "segmento": tipo, "valor_segmento": valor,
                "transacoes": len(grupo), "fraudes": int(y.sum()),
                "recall": float(recall_score(y, bloqueada, zero_division=0)) if y.sum() else np.nan,
                "precision": float(precision_score(y, bloqueada, zero_division=0)) if bloqueada.sum() else np.nan,
                "pr_auc": float(average_precision_score(y, score)) if len(np.unique(y)) == 2 else np.nan,
                "custo": custo_decisao(y, grupo["valor_transacao"], score, threshold, custo_legitima_bloqueada),
            })
    tabela = pd.DataFrame(linhas)
    tabela["custo_por_mil"] = 1000 * tabela["custo"] / tabela["transacoes"]
    referencia = tabela.loc[tabela["conjunto"] == "referencia"].set_index(["segmento", "valor_segmento"])
    motivos = []
    for linha in tabela.itertuples():
        if linha.conjunto == "referencia":
            motivos.append("")
            continue
        base = referencia.loc[(linha.segmento, linha.valor_segmento)]
        minimo = LIMITE_QUEDA_GLOBAL_PP if linha.segmento == "global" else LIMITE_QUEDA_SEGMENTO_PP
        elegivel = linha.segmento == "global" or (
            linha.fraudes >= MIN_FRAUDES_SEGMENTO and base["fraudes"] >= MIN_FRAUDES_SEGMENTO)
        quedas = [metrica for metrica in ("recall", "precision", "pr_auc")
                  if pd.notna(getattr(linha, metrica)) and pd.notna(base[metrica])
                  and (base[metrica] - getattr(linha, metrica)) * 100 > minimo]
        motivo = ", ".join(f"queda_{m}" for m in quedas) if elegivel else ""
        if linha.segmento == "global" and base["custo_por_mil"] > 0 and (
            linha.custo_por_mil / base["custo_por_mil"] - 1 > LIMITE_AUMENTO_CUSTO_POR_MIL
        ):
            motivo = ", ".join(filter(None, (motivo, "aumento_custo_por_mil")))
        motivos.append(motivo)
    tabela["motivos_alerta"] = motivos
    tabela["alerta"] = tabela["motivos_alerta"].ne("")
    return tabela


def monitorar(referencia, lote, threshold, segmento="canal"):
    """Quatro tabelas; performance é None enquanto faltar algum rótulo."""
    tabelas = {
        "continuas": drift_continuas(referencia, lote),
        "discretas": drift_discretas(referencia, lote),
        "saida": saida_modelo(referencia, lote, threshold),
        "performance": None,
    }
    if "fraude" in lote and lote["fraude"].notna().all():
        tabelas["performance"] = performance(referencia, lote, threshold, segmento)
    return tabelas


def carregar_semana(semana, url_base=None):
    """Lê GET /api/semanas/{n}/dados.csv, já pontuado pelo sistema."""
    if url_base is None:
        import config
        url_base = config.SISTEMA_URL
    with urlopen(f"{url_base.rstrip('/')}/api/semanas/{int(semana)}/dados.csv", timeout=30) as resposta:
        df = pd.read_csv(BytesIO(resposta.read()), dtype={"id_transacao": str, "id_cliente": str})
    if df.empty:
        raise ValueError(f"Semana {semana} vazia na API; envie o lote em Lotes primeiro")
    if df["score"].isna().any():
        raise ValueError(f"Semana {semana} ainda não foi pontuada")
    return df


def carregar_referencia_champion():
    """Baixa a referência da run apontada pelo alias champion no MLflow.

    Retorna (DataFrame, threshold, versão); assim a troca do alias troca
    automaticamente a referência utilizada nas próximas análises.
    """
    import json
    from pathlib import Path

    import mlflow
    from mlflow.tracking import MlflowClient

    import config

    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
    versao = MlflowClient().get_model_version_by_alias(config.NOME_MODELO, config.ALIAS_PRODUCAO)
    caminho = Path(mlflow.artifacts.download_artifacts(
        run_id=versao.run_id, artifact_path="referencia/validacao_11_12.csv"))
    metadados = json.loads(Path(mlflow.artifacts.download_artifacts(
        run_id=versao.run_id, artifact_path="referencia/metadados.json")).read_text(encoding="utf-8"))
    if str(metadados["versao"]) != str(versao.version) or metadados["run_id"] != versao.run_id:
        raise ValueError("Metadados da referência não correspondem ao champion")
    threshold = float(versao.tags[config.TAG_THRESHOLD])
    if threshold != float(metadados["threshold"]):
        raise ValueError("Threshold do champion difere da referência; atualize a referência")
    referencia = pd.read_csv(caminho, dtype={"id_transacao": str})
    return referencia, threshold, str(versao.version)
