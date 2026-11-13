"""Tabelas de monitoramento semanal do modelo antifraude."""

from io import BytesIO
from pathlib import Path
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
    if contrato is None:
        raiz = Path(__file__).resolve().parent
        caminho = raiz / "contrato" / "contrato_features.yaml"
        if not caminho.is_file():
            caminho = raiz / "contrato_features.yaml"
        contrato = carregar_contrato(caminho)
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
        a = pd.to_numeric(referencia[coluna], errors="coerce").to_numpy(dtype=float, na_value=np.nan)
        b = pd.to_numeric(lote[coluna], errors="coerce").to_numpy(dtype=float, na_value=np.nan)
        a = a[np.isfinite(a)]
        b = b[np.isfinite(b)]
        teste = ks_2samp(a, b) if len(a) and len(b) else None
        linhas.append({
            "variavel": coluna, "n_referencia": len(a), "n_lote": len(b),
            "invalidos_referencia": len(referencia) - len(a),
            "invalidos_lote": len(lote) - len(b),
            "status": "calculado" if teste else "sem_amostra_valida",
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


def saida_modelo(referencia, lote, threshold, *, threshold_lote=None):
    """Taxa, contagem e valor bloqueado do modelo em cada conjunto."""
    linhas = []
    corte_lote = threshold if threshold_lote is None else threshold_lote
    for nome, df, corte in (("referencia", referencia, threshold), ("lote", lote, corte_lote)):
        _exigir_colunas(df, ["score", "valor_transacao"], nome)
        score = pd.to_numeric(df["score"], errors="coerce").to_numpy(dtype=float, na_value=np.nan)
        valor = pd.to_numeric(df["valor_transacao"], errors="coerce").to_numpy(dtype=float, na_value=np.nan)
        if not ((0 <= score) & (score <= 1)).all() or not np.isfinite(valor).all():
            raise ValueError(f"{nome}: score ou valor_transacao ausente/inválido")
        bloqueada = score >= corte
        linhas.append({
            "conjunto": nome, "transacoes": len(df), "bloqueios": int(bloqueada.sum()),
            "taxa_bloqueio": float(bloqueada.mean()) if len(df) else np.nan,
            "valor_bloqueado": float(valor[bloqueada].sum()),
            "valor_total": float(valor.sum()),
            "pct_valor_bloqueado": float(valor[bloqueada].sum() / valor.sum()) if valor.sum() else np.nan,
        })
    tabela = pd.DataFrame(linhas)
    tabela["delta_taxa_bloqueio_pp"] = (tabela["taxa_bloqueio"] - tabela.loc[0, "taxa_bloqueio"]) * 100
    tabela["delta_pct_valor_bloqueado_pp"] = (tabela["pct_valor_bloqueado"] - tabela.loc[0, "pct_valor_bloqueado"]) * 100
    tabela["alerta"] = (tabela["delta_taxa_bloqueio_pp"].abs() > LIMITE_TAXA_BLOQUEIO_PP) | (
        tabela["delta_pct_valor_bloqueado_pp"].abs() > LIMITE_PCT_VALOR_BLOQUEADO_PP)
    return tabela


def performance(referencia, lote, threshold, segmento="canal", custo_legitima_bloqueada=15.0, *, threshold_lote=None):
    """Recall, precision, PR-AUC (average precision) e custo, globais e por segmento.

    Com rótulos parciais, as métricas descrevem apenas as transações rotuladas.
    O custo final e os alertas de performance exigem cobertura completa.
    """
    linhas = []
    cobertura_completa = {}
    corte_lote = threshold if threshold_lote is None else threshold_lote
    for nome, df, corte in (("referencia", referencia, threshold), ("lote", lote, corte_lote)):
        _exigir_colunas(df, ["fraude", "score", "valor_transacao", segmento], nome)
        if not df["fraude"].dropna().isin([0, 1]).all():
            raise ValueError(f"{nome}: fraude deve conter apenas 0 e 1")
        cobertura_completa[nome] = not df.empty and df["fraude"].notna().all()
        grupos = [("global", "todos", df)]
        grupos += [(segmento, str(valor), grupo)
                   for valor, grupo in df.groupby(segmento, dropna=False, observed=True)]
        for tipo, valor, grupo in grupos:
            rotuladas = grupo.loc[grupo["fraude"].notna()]
            y = rotuladas["fraude"].to_numpy(dtype=int)
            score = rotuladas["score"].to_numpy(dtype=float)
            valores = rotuladas["valor_transacao"].to_numpy(dtype=float)
            if not np.isfinite(valores).all() or not ((0 <= score) & (score <= 1)).all():
                raise ValueError(f"{nome}: score ou valor_transacao ausente/inválido")
            bloqueada = score >= corte
            custo_observado = (
                custo_decisao(y, valores, score, corte, custo_legitima_bloqueada) if len(y) else np.nan
            )
            linhas.append({
                "conjunto": nome, "segmento": tipo, "valor_segmento": valor,
                "transacoes": len(grupo), "fraudes": int(y.sum()),
                "rotuladas": len(y), "cobertura_rotulos": len(y) / len(grupo) if len(grupo) else np.nan,
                "recall": float(recall_score(y, bloqueada, zero_division=0)) if y.sum() else np.nan,
                "precision": float(precision_score(y, bloqueada, zero_division=0)) if bloqueada.sum() else np.nan,
                "pr_auc": float(average_precision_score(y, score)) if len(np.unique(y)) == 2 else np.nan,
                "custo_observado": custo_observado,
                "custo": custo_observado if cobertura_completa[nome] else np.nan,
            })
    tabela = pd.DataFrame(linhas)
    tabela["custo_por_mil"] = 1000 * tabela["custo"] / tabela["transacoes"].replace(0, np.nan)
    base_segmentos = tabela.loc[tabela["conjunto"] == "referencia"].set_index(["segmento", "valor_segmento"])
    comparar = all(cobertura_completa.values())
    motivos, status = [], []
    for linha in tabela.itertuples():
        if linha.conjunto == "referencia":
            status.append("referencia")
            motivos.append("")
            continue
        chave = (linha.segmento, linha.valor_segmento)
        if not comparar or chave not in base_segmentos.index:
            status.append("rotulos_pendentes" if not comparar else "segmento_sem_referencia")
            motivos.append("")
            continue
        base = base_segmentos.loc[chave]
        status.append("comparado")
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
    tabela["status_comparacao"] = status
    return tabela


def monitorar(referencia, lote, threshold, segmento="canal"):
    """Quatro tabelas; performance é None enquanto não houver nenhum rótulo."""
    tabelas = {
        "continuas": drift_continuas(referencia, lote),
        "discretas": drift_discretas(referencia, lote),
        "saida": saida_modelo(referencia, lote, threshold),
        "performance": None,
    }
    if "fraude" in lote and lote["fraude"].notna().any():
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
    if not df["score"].between(0, 1).all():
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


def relatorio_semana(semana, segmento="canal"):
    """Compara a semana corrente e o histórico da operação com a referência do champion.

    Cada semana usa o corte gravado com seus scores. A performance só considera
    semanas anteriores, porque os rótulos chegam com uma semana de atraso.
    """
    if semana < 13:
        raise ValueError("O relatório de operação começa na semana 13")
    referencia, threshold, versao = carregar_referencia_champion()
    saidas, desempenhos = [], []
    for numero in range(13, semana + 1):
        lote = carregar_semana(numero)
        versoes = lote["versao_modelo"].astype("string").unique()
        cortes = lote["threshold"].unique()
        if len(versoes) != 1 or pd.isna(versoes[0]) or len(cortes) != 1 or not 0 <= cortes[0] <= 1:
            raise ValueError(f"Semana {numero}: versão ou threshold ausente ou misturado")
        versao_lote, corte = versoes[0], cortes[0]
        if numero == semana and (versao_lote != versao or corte != threshold):
            raise ValueError(f"Semana {numero}: pontuação não corresponde ao champion v{versao} e seu threshold")

        saida = saida_modelo(referencia, lote, threshold, threshold_lote=corte)
        ref = saida["conjunto"].eq("referencia")
        saida["semana"] = pd.Series(numero, index=saida.index, dtype="Int64").mask(ref)
        saida["versao_modelo"] = saida["conjunto"].map({"referencia": versao, "lote": versao_lote})
        saida["threshold"] = saida["conjunto"].map({"referencia": threshold, "lote": corte})
        saidas.append(saida if numero == 13 else saida.loc[~ref])

        if numero < semana:
            tabela = performance(referencia, lote, threshold, segmento, threshold_lote=corte)
            ref = tabela["conjunto"].eq("referencia")
            tabela["semana"] = pd.Series(numero, index=tabela.index, dtype="Int64").mask(ref)
            tabela["versao_modelo"] = tabela["conjunto"].map({"referencia": versao, "lote": versao_lote})
            tabela["threshold"] = tabela["conjunto"].map({"referencia": threshold, "lote": corte})
            desempenhos.append(tabela if numero == 13 else tabela.loc[~ref])

    return {
        "continuas": drift_continuas(referencia, lote),
        "discretas": drift_discretas(referencia, lote),
        "saida": pd.concat(saidas, ignore_index=True),
        "performance": pd.concat(desempenhos, ignore_index=True) if desempenhos else None,
    }
