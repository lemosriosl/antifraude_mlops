"""
BASELINE OFICIAL — monitoramento reutilizável nas partes 2 e 3.

KS (estatística D) nas contínuas e no score; qui-quadrado (V de Cramér) nas
categóricas, booleanas e na hora. Com ~20 mil linhas por lote o p-valor
acusa qualquer diferença: o alerta usa o TAMANHO do efeito, não o p-valor.
"""
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import average_precision_score, precision_score, recall_score

CONTINUAS = ["valor_transacao", "valor_medio_30d", "razao_valor_media",
             "distancia_ultima_transacao_km", "idade_conta_dias", "qtd_transacoes_1h"]
CATEGORICAS = ["hora_transacao", "dia_semana", "canal", "dispositivo_novo",
               "destinatario_novo", "categoria_estabelecimento", "uf_cliente"]
LIMITE_KS = 0.10
LIMITE_CRAMER = 0.10
CUSTO_FP = 15.0


def ks(ref, atual):
    d, p = stats.ks_2samp(ref, atual)
    return d, p


def cramer(ref, atual):
    cats = sorted(set(ref.astype(str)) | set(atual.astype(str)))
    tab = np.array([[np.sum(ref.astype(str) == c) for c in cats],
                    [np.sum(atual.astype(str) == c) for c in cats]])
    tab = tab[:, tab.sum(0) > 0]
    chi2, p, _, _ = stats.chi2_contingency(tab)
    v = np.sqrt(chi2 / (tab.sum() * (min(tab.shape) - 1)))
    return v, p


def drift(ref, atual, score_col="score"):
    linhas = []
    for c in CONTINUAS + [score_col]:
        if c in ref and c in atual:
            d, p = ks(ref[c], atual[c])
            linhas.append({"coluna": c, "teste": "KS (D)", "estatistica": d, "p_valor": p, "alerta": d > LIMITE_KS})
    for c in CATEGORICAS:
        v, p = cramer(ref[c], atual[c])
        linhas.append({"coluna": c, "teste": "qui² (V)", "estatistica": v, "p_valor": p, "alerta": v > LIMITE_CRAMER})
    return pd.DataFrame(linhas).sort_values("estatistica", ascending=False)


def saida(df, threshold, score_col="score"):
    b = df[score_col] >= threshold
    return {"taxa_bloqueio": b.mean(), "valor_bloqueado": df.loc[b, "valor_transacao"].sum()}


def custo(y, bloqueada, valor):
    y, b, v = np.asarray(y), np.asarray(bloqueada), np.asarray(valor, dtype=float)
    return v[(y == 1) & ~b].sum() + CUSTO_FP * ((y == 0) & b).sum()


def performance(df, threshold, score_col="score", y_col="fraude", segmento=None):
    def _m(g):
        y, s = g[y_col], g[score_col]
        b = s >= threshold
        return pd.Series({"n": len(g), "fraudes": int(y.sum()),
                          "recall": recall_score(y, b, zero_division=0),
                          "precision": precision_score(y, b, zero_division=0),
                          "pr_auc": average_precision_score(y, s) if y.sum() else np.nan,
                          "custo": custo(y, b, g["valor_transacao"])})
    if segmento is None:
        return _m(df).to_frame("global").T
    return df.groupby(segmento).apply(_m, include_groups=False)
