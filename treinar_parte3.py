"""Compara ações para o Pix e registra um candidato validado, sem promovê-lo."""

import argparse
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
from mlflow.models import infer_signature
from mlflow.tracking import MlflowClient
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.pipeline import Pipeline

import config
from app import contrato
from features import EspecialistaPix, criar_preprocessador, pix_dispositivo_conhecido
from monitoramento import carregar_semana, custo_decisao
from operar_parte3 import EVIDENCIAS, api, modelo_vigente, perfil_pix


CORTE_TEMPO = pd.Timestamp("2026-10-03 03:00:00")  # sábado, 00h em Brasília
PASTA = EVIDENCIAS / "validacao"


def dados_originais(semana):
    pasta_lote = Path("dados") / ("parte2" if semana <= 16 else "parte3")
    pasta_rotulos = Path("dados") / ("parte2" if semana < 16 else "parte3")
    lote = pd.read_csv(pasta_lote / f"transacoes_semana_{semana:02d}.csv", parse_dates=["data_transacao"])
    rotulos = pd.read_csv(pasta_rotulos / f"rotulos_semana_{semana:02d}.csv", usecols=["id_transacao", "fraude"])
    dados = lote.merge(rotulos, on="id_transacao", how="left", validate="one_to_one")
    if not dados["fraude"].isin([0, 1]).all():
        raise ValueError(f"Rótulos incompletos para a semana {semana}.")
    if semana == 13:
        # Antes da migração, o arquivo original já vinha em horário de Brasília.
        dados["data_transacao"] += pd.Timedelta(hours=3)
        dados["hora_transacao"] = dados["data_transacao"].dt.hour
        dados["dia_semana"] = dados["data_transacao"].dt.dayofweek
    return dados


def corte_menor_custo(dados, scores):
    """Testa cada corte distinto e preserva o maior corte em caso de empate."""
    y = dados["fraude"].eq(1).to_numpy()
    valores = dados["valor_transacao"].to_numpy()
    indices = np.argsort(scores)
    ordenados = scores[indices]
    ganhos = np.where(y, valores, -config.CUSTO_FALSO_POSITIVO)
    acumulado = np.r_[0, np.cumsum(ganhos[indices])]
    limites = np.unique(np.clip(np.r_[ordenados, 0, 1], 1e-12, 1 - 1e-12))
    inicio = np.searchsorted(ordenados, limites, side="left")
    economia = acumulado[-1] - acumulado[inicio]
    return float(limites[np.flatnonzero(np.isclose(economia, economia.max(), rtol=0, atol=1e-8))[-1]])


def medir(dados, scores, corte, nome):
    perfis = perfil_pix(dados)
    grupos = {"global": np.ones(len(dados), dtype=bool),
              "grupo_pix": pix_dispositivo_conhecido(dados).to_numpy(),
              "outros_pix": perfis == "outros_pix", "outros_canais": perfis == "outros_canais"}
    grupos["restante"] = ~grupos["grupo_pix"]
    linhas = []
    for segmento, mascara in grupos.items():
        parte = dados.loc[mascara]
        y = parte["fraude"].to_numpy()
        s = scores[mascara]
        bloqueadas = s >= corte
        fraudes = y == 1
        tp = int((fraudes & bloqueadas).sum())
        fp = int((~fraudes & bloqueadas).sum())
        linhas.append({
            "modelo": nome, "segmento": segmento, "transacoes": len(parte),
            "fraudes": int(fraudes.sum()), "fraudes_detectadas": tp, "legitimas_bloqueadas": fp,
            "fraude_perdida": parte.loc[fraudes & ~bloqueadas, "valor_transacao"].sum(),
            "recall": tp / fraudes.sum() if fraudes.any() else np.nan,
            "precisao": tp / bloqueadas.sum() if bloqueadas.any() else np.nan,
            "taxa_bloqueio": bloqueadas.mean(),
            "valor_bloqueado": parte.loc[bloqueadas, "valor_transacao"].sum(),
            "custo": custo_decisao(y, parte["valor_transacao"], s, corte),
        })
    return pd.DataFrame(linhas)


def cortes_por_grupo(X, scores, corte_grupo, corte_atual):
    corte = np.where(pix_dispositivo_conhecido(X), corte_grupo, corte_atual)
    return (scores >= corte).astype(float)


def comparar(versao_base=None):
    lotes = {int(l["semana"]): l for l in api("/api/lotes")}
    if any(lotes[s]["rotulos"] != lotes[s]["qtd_linhas"] for s in range(13, 20)):
        raise RuntimeError("A comparação requer os lotes e rótulos completos das semanas 13 a 19.")
    PASTA.mkdir(parents=True, exist_ok=True)
    if versao_base is None:
        versao, atual = modelo_vigente()
    else:
        mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
        versao = MlflowClient().get_model_version(config.NOME_MODELO, versao_base)
        atual = mlflow.sklearn.load_model(f"models:/{config.NOME_MODELO}/{versao.version}")
    corte_atual = float(versao.tags[config.TAG_THRESHOLD])
    utc = atual.named_steps["utc"]
    campos = contrato.nomes_features()
    historico = pd.concat([dados_originais(s) for s in range(13, 19)], ignore_index=True)
    treino = historico.loc[historico["data_transacao"].lt(CORTE_TEMPO)]
    calibracao = historico.loc[historico["data_transacao"].ge(CORTE_TEMPO)]
    calib_bruto = contrato.tipar(calibracao[campos])
    calib_local = utc.transform(calib_bruto)
    grupo_treino = treino.loc[pix_dispositivo_conhecido(treino)]
    grupo_calib = pix_dispositivo_conhecido(calib_local)
    treino_local = utc.transform(contrato.tipar(grupo_treino[campos]))
    s_calib = atual.predict_proba(calib_bruto)[:, 1]
    corte_global = corte_menor_custo(calibracao, s_calib)
    corte_grupo = corte_menor_custo(calibracao.loc[grupo_calib], s_calib[grupo_calib])
    resumo = [
        medir(calibracao, s_calib, corte_atual, "champion").assign(corte=corte_atual),
        medir(calibracao, s_calib, corte_global, "corte_global").assign(corte=corte_global),
        medir(calibracao, cortes_por_grupo(calib_local, s_calib, corte_grupo, corte_atual), 0.5,
              "corte_por_grupo").assign(corte=corte_grupo),
    ]
    candidatos = []
    for nome, estimador in [
        ("floresta_pix", RandomForestClassifier(n_estimators=200, min_samples_leaf=8, random_state=42, n_jobs=4)),
        ("boosting_pix", HistGradientBoostingClassifier(max_iter=100, max_leaf_nodes=12, min_samples_leaf=14, random_state=42)),
    ]:
        especialista = Pipeline([("pre", criar_preprocessador()), ("modelo", estimador)])
        especialista.fit(treino_local, grupo_treino["fraude"])
        score_grupo = especialista.predict_proba(calib_local.loc[grupo_calib])[:, 1]
        corte = corte_menor_custo(calibracao.loc[grupo_calib], score_grupo)
        combinado = Pipeline([("utc", utc), ("modelo", EspecialistaPix(atual[1:], especialista, corte_atual, corte))])
        scores = combinado.predict_proba(calib_bruto)[:, 1]
        medidas = medir(calibracao, scores, corte_atual, nome).assign(corte=corte)
        resumo.append(medidas)
        candidatos.append((medidas.loc[medidas["segmento"].eq("global"), "custo"].iat[0], nome, corte, combinado))
    _, nome, corte, candidato = min(candidatos, key=lambda item: item[0])
    pd.concat(resumo, ignore_index=True).to_csv(PASTA / "calibracao_semana_18.csv", index=False)
    pd.concat([
        treino.assign(uso="treino"),
        calibracao.assign(uso="calibracao"),
    ]).assign(grupo=lambda d: pix_dispositivo_conhecido(d)).groupby(
        ["uso", "semana", "grupo"]
    )["fraude"].agg(["count", "sum"]).to_csv(PASTA / "amostras.csv")

    # A semana 19 só é aberta depois de congelar algoritmo e cortes.
    semana19 = carregar_semana(19)
    X19 = contrato.tipar(semana19[campos])
    s19 = atual.predict_proba(X19)[:, 1]
    s_candidato = candidato.predict_proba(X19)[:, 1]
    np.testing.assert_allclose(s19, semana19["score"], atol=1e-10, rtol=0)
    grupo19 = pix_dispositivo_conhecido(X19).to_numpy()
    np.testing.assert_array_equal(s_candidato[~grupo19], s19[~grupo19])
    validacao = pd.concat([
        medir(semana19, s19, corte_atual, "champion").assign(corte=corte_atual),
        medir(semana19, s19, corte_global, "corte_global").assign(corte=corte_global),
        medir(semana19, cortes_por_grupo(X19, s19, corte_grupo, corte_atual), 0.5,
              "corte_por_grupo").assign(corte=corte_grupo),
        medir(semana19, s_candidato, corte_atual, nome).assign(corte=corte),
    ], ignore_index=True)
    validacao.to_csv(PASTA / "validacao_semana_19.csv", index=False)
    print(validacao.to_string(index=False))
    custo = validacao.loc[validacao["segmento"].eq("global")].set_index("modelo")["custo"]
    elegivel = custo[nome] < custo[["champion", "corte_global", "corte_por_grupo"]].min()
    return versao, candidato, nome, corte_atual, corte, X19, elegivel


def registrar_candidato(versao, candidato, nome, corte_atual, corte, X19):
    mlflow.set_experiment("antifraude-parte3")
    referencia = dados_originais(19)
    X_ref = contrato.tipar(referencia[contrato.nomes_features()])
    dados_ref = candidato.named_steps["utc"].transform(X_ref).assign(
        semana=19, fraude=referencia["fraude"], score=candidato.predict_proba(X_ref)[:, 1],
    )
    caminho_ref = PASTA / "referencia_semana_19.csv"
    dados_ref.to_csv(caminho_ref, index=False)
    with mlflow.start_run(run_name=nome) as run:
        mlflow.log_params({
            "champion_anterior": versao.version, "treino": "Pix do grupo nas semanas 13 a 17 e 18 até sexta",
            "calibracao": "semana 18, sábado e domingo (Brasília)", "validacao": "semana 19 inteira",
            "corte_especialista": corte, "corte_publicado": corte_atual, "versao_contrato": "1.1",
        })
        validacao = pd.read_csv(PASTA / "validacao_semana_19.csv")
        for linha in validacao[validacao["modelo"].eq(nome)].itertuples():
            mlflow.log_metrics({f"custo_{linha.segmento}": linha.custo, f"recall_{linha.segmento}": linha.recall,
                                f"taxa_bloqueio_{linha.segmento}": linha.taxa_bloqueio})
        mlflow.log_artifact(str(caminho_ref), "referencia")
        for arquivo in ("amostras.csv", "calibracao_semana_18.csv", "validacao_semana_19.csv"):
            mlflow.log_artifact(str(PASTA / arquivo), "validacao")
        exemplo = X19.iloc[:5]
        info = mlflow.sklearn.log_model(
            candidato, "modelo", input_example=exemplo,
            signature=infer_signature(exemplo, candidato.predict_proba(exemplo)),
            pyfunc_predict_fn="predict_proba",
            code_paths=["features.py", "estado_oficial_parte2/conversao_utc.py"],
        )
    nova = mlflow.register_model(info.model_uri, config.NOME_MODELO)
    cliente = MlflowClient()
    descricao = (f"Especialista {nome} para Pix em aparelho conhecido com 2+ transações na hora anterior. "
                 f"Corte calibrado por custo: {corte:.8g}. Fora do grupo, mantém scores e decisões da v{versao.version}. "
                 "Validação temporal na semana 19; contrato v1.1.")
    cliente.update_model_version(config.NOME_MODELO, nova.version, descricao)
    for chave, valor in {
        config.TAG_THRESHOLD: corte_atual, config.TAG_MOTIVO: "Mitigar deterioração de detecção no Pix",
        "referencia_vigente": caminho_ref.name, "versao_contrato": "1.1", "rollback": versao.version,
    }.items():
        cliente.set_model_version_tag(config.NOME_MODELO, nova.version, chave, str(valor))
    print(f"Candidato v{nova.version}, run {run.info.run_id}, corte publicado {corte_atual}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--versao-base", help="versão incumbente na semana 19, para reproduzir a comparação")
    parser.add_argument("--registrar", action="store_true")
    args = parser.parse_args()
    *resultado, elegivel = comparar(args.versao_base)
    print("Candidato supera as alternativas na validação:", elegivel)
    if args.registrar and elegivel:
        registrar_candidato(*resultado)


if __name__ == "__main__":
    main()
