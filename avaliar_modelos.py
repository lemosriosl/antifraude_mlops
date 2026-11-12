"""Compara modelos nas semanas 11–12 e salva evidências de validação."""

import argparse
import hashlib
import json
import platform
import sys
from importlib.metadata import version
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier
from threadpoolctl import threadpool_limits

import config
from app.contrato import validar
from features import carregar_contrato, criar_preprocessador
from monitoramento import custo_decisao

TRANSACOES = config.RAIZ / "dados/transacoes_semanas_01_12.csv"
ROTULOS = config.RAIZ / "dados/rotulos_semanas_01_12.csv"
CONTRATO = config.CONTRATO
TREINO = list(range(1, 11))
VALIDACAO = [11, 12]
SEMENTE = 42


def carregar_historico(contrato):
    transacoes = pd.read_csv(TRANSACOES, dtype={"id_transacao": str, "id_cliente": str})
    rotulos = pd.read_csv(ROTULOS, usecols=["id_transacao", "fraude"], dtype={"id_transacao": str})
    transacoes, erros = validar(transacoes, contrato, exigir_uma_semana=False)
    if erros:
        raise ValueError(f"Histórico fora do contrato: {erros}")
    if rotulos["id_transacao"].isna().any() or not rotulos["fraude"].isin([0, 1]).all():
        raise ValueError("Histórico com rótulos ausentes ou inválidos")
    historico = transacoes.merge(rotulos, on="id_transacao", validate="one_to_one")
    if len(historico) != len(transacoes) or len(historico) != len(rotulos):
        raise ValueError("A junção de transações e rótulos perdeu linhas")
    if set(historico["semana"]) != set(TREINO + VALIDACAO):
        raise ValueError("O histórico deve conter as semanas 1 a 12")
    return historico


def estimadores():
    """Inclui as configurações originais e alternativas de regularização e custo."""
    boosting = dict(max_iter=200, max_leaf_nodes=23, min_samples_leaf=30,
                    learning_rate=0.08, l2_regularization=1.0, random_state=SEMENTE)
    return [
        ("logistica_balanceada", LogisticRegression(max_iter=1000, class_weight="balanced",
                                                     random_state=SEMENTE), False),
        ("floresta_original", RandomForestClassifier(n_estimators=300, min_samples_leaf=5,
                                                      class_weight="balanced", random_state=SEMENTE,
                                                      n_jobs=4), False),
        ("arvore_regularizada", DecisionTreeClassifier(max_depth=9, min_samples_leaf=40,
                                                        random_state=SEMENTE), False),
        ("floresta_regularizada", RandomForestClassifier(n_estimators=180, max_depth=14,
                                                           min_samples_leaf=15,
                                                           random_state=SEMENTE, n_jobs=4), False),
        ("boosting", HistGradientBoostingClassifier(**boosting), False),
        ("boosting_ponderado_por_custo", HistGradientBoostingClassifier(**boosting), True),
    ]


def medir(decisoes, dados, scores=None):
    fraude = dados["fraude"].to_numpy() == 1
    perdidas = fraude & ~decisoes
    legitimas = ~fraude & decisoes
    acertos = int((fraude & decisoes).sum())
    return {
        "custo": round(custo_decisao(fraude, dados["valor_transacao"], decisoes, 0.5,
                                     config.CUSTO_FALSO_POSITIVO), 2),
        "valor_fraudes_aprovadas": round(float(dados.loc[perdidas, "valor_transacao"].sum()), 2),
        "fraudes_aprovadas": int(perdidas.sum()),
        "legitimas_bloqueadas": int(legitimas.sum()),
        "clientes_legitimos_afetados": int(dados.loc[legitimas, "id_cliente"].nunique()),
        "taxa_bloqueio": float(decisoes.mean()),
        "recall": acertos / int(fraude.sum()) if fraude.any() else None,
        "precision": acertos / int(decisoes.sum()) if decisoes.any() else None,
        "pr_auc": float(average_precision_score(fraude, scores))
        if scores is not None and np.unique(fraude).size == 2 else None,
    }


def avaliar_candidato(nome, modelo, validacao, scores, ponderado, curva):
    y = validacao["fraude"]
    valores = validacao["valor_transacao"]
    for centesimos in range(1, 100):
        corte = centesimos / 100
        custo = custo_decisao(y, valores, scores, corte, config.CUSTO_FALSO_POSITIVO)
        curva.append({"modelo": nome, "threshold": corte, "custo": round(custo, 2)})
    otimo = min(curva, key=lambda linha: linha["custo"])
    corte = otimo["threshold"]
    bloqueadas = scores >= corte
    por_semana = {}
    for semana in VALIDACAO:
        mask = validacao["semana"].eq(semana).to_numpy()
        por_semana[str(semana)] = medir(bloqueadas[mask], validacao.loc[mask], scores[mask])
    return {
        "modelo": nome,
        "algoritmo": type(modelo).__name__,
        "parametros": modelo.get_params(),
        "peso_de_treino": (f"valor da fraude / {config.CUSTO_FALSO_POSITIVO:g}; legítimas = 1"
                           if ponderado else "uniforme"),
        "threshold": corte,
        **medir(bloqueadas, validacao, scores),
        "custo_threshold_0_5": medir(scores >= 0.5, validacao)["custo"],
        "por_semana": por_semana,
    }


def registrar_run(mlflow, pipeline, exemplo, resultado, curva, contrato):
    with mlflow.start_run(run_name=resultado["modelo"]) as run:
        mlflow.log_params({
            "algoritmo": resultado["algoritmo"],
            "semanas_treino": "1-10",
            "semanas_validacao": "11-12",
            "versao_contrato": contrato["versao"],
            "peso_de_treino": resultado["peso_de_treino"],
            **resultado["parametros"],
        })
        mlflow.log_metrics({
            chave: resultado[chave] for chave in
            ("custo", "threshold", "pr_auc", "recall", "precision", "custo_threshold_0_5")
            if resultado[chave] is not None
        })
        mlflow.log_dict({"curva": curva, "por_semana": resultado["por_semana"]}, "validacao.json")
        info = mlflow.sklearn.log_model(
            pipeline, artifact_path="modelo", serialization_format="pickle",
            signature=mlflow.models.infer_signature(exemplo, pipeline.predict_proba(exemplo)),
            input_example=exemplo, code_paths=[str(config.RAIZ / "features.py")],
        )
        return {"run_id": run.info.run_id, "model_uri": info.model_uri}


def abrir_experimento(tracking_uri):
    import mlflow
    import mlflow.sklearn

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("antifraude-parte1-comparacao")
    return mlflow


def hashes_historico():
    return {p.relative_to(config.RAIZ).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (TRANSACOES, ROTULOS, CONTRATO)}


def salvar_comparacao(caminho, relatorio):
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=caminho.parent,
                            suffix=".json", delete=False) as arquivo:
        json.dump(relatorio, arquivo, ensure_ascii=False, indent=2)
        arquivo.write("\n")
    temporario = Path(arquivo.name)
    try:
        temporario.replace(caminho)
    finally:
        temporario.unlink(missing_ok=True)


def registrar_candidato(destino, tracking_uri):
    """Confere o candidato da comparação e registra apenas o seu pipeline no MLflow."""
    caminho = destino / "comparacao.json"
    relatorio = json.loads(caminho.read_text(encoding="utf-8"))
    candidato = next((r for r in relatorio["resultados"] if r["modelo"] == relatorio["candidato"]), None)
    if candidato is None or not candidato["atende_pisos"]:
        raise ValueError("A comparação não possui um candidato que superou as referências de custo.")
    if relatorio["sha256"] != hashes_historico():
        raise ValueError("Os dados ou o contrato mudaram. Refaça a comparação antes de registrar o candidato.")

    mlflow = abrir_experimento(tracking_uri)
    contrato = carregar_contrato(CONTRATO)
    historico = carregar_historico(contrato)
    colunas = relatorio["features"]
    validacao = historico.loc[historico["semana"].isin(VALIDACAO)]
    x_validacao = validacao[colunas]
    pasta_modelo = destino / "modelo_candidato"
    ponderado = candidato["peso_de_treino"] != "uniforme"
    with threadpool_limits(limits=4):
        if (pasta_modelo / "MLmodel").is_file():
            pipeline = mlflow.sklearn.load_model(str(pasta_modelo))
        else:
            modelo = next(est for nome, est, _ in estimadores() if nome == candidato["modelo"])
            modelo.set_params(**candidato["parametros"])
            pipeline = Pipeline([("preprocessamento", criar_preprocessador(contrato)), ("modelo", modelo)])
            treino = historico.loc[historico["semana"].isin(TREINO)]
            y_treino = treino["fraude"]
            pesos = np.where(y_treino == 1, treino["valor_transacao"] / config.CUSTO_FALSO_POSITIVO, 1.0)
            ajuste = {"modelo__sample_weight": pesos} if ponderado else {}
            pipeline.fit(treino[colunas], y_treino, **ajuste)
        if list(pipeline.feature_names_in_) != colunas:
            raise ValueError("As features do candidato divergem da comparação.")
        curva = []
        recalculado = avaliar_candidato(
            candidato["modelo"], pipeline.named_steps["modelo"], validacao,
            pipeline.predict_proba(x_validacao)[:, 1], ponderado, curva,
        )
    for chave in ("algoritmo", "parametros", "threshold", "custo",
                  "fraudes_aprovadas", "legitimas_bloqueadas"):
        if recalculado[chave] != candidato[chave]:
            raise ValueError(f"O candidato carregado diverge da comparação em {chave}.")
    for semana in map(str, VALIDACAO):
        if recalculado["por_semana"][semana]["custo"] != candidato["por_semana"][semana]["custo"]:
            raise ValueError(f"O custo do candidato diverge da comparação na semana {semana}.")
    candidato.update(registrar_run(mlflow, pipeline, x_validacao.head(5), candidato, curva, contrato))
    salvar_comparacao(caminho, relatorio)
    return candidato


def comparar(destino, tracking_uri=None):
    contrato = carregar_contrato(CONTRATO)
    historico = carregar_historico(contrato)
    colunas = [f["nome"] for f in contrato["features"]]
    treino = historico.loc[historico["semana"].isin(TREINO)]
    validacao = historico.loc[historico["semana"].isin(VALIDACAO)]
    x_treino, x_validacao = treino[colunas], validacao[colunas]
    y_treino = treino["fraude"]
    pesos = np.where(y_treino == 1, treino["valor_transacao"] / config.CUSTO_FALSO_POSITIVO, 1.0)
    aprovar_tudo = medir(np.zeros(len(validacao), dtype=bool), validacao)
    regra_pix = medir((validacao["canal"].eq("pix") & validacao["valor_transacao"].gt(1000)).to_numpy(),
                     validacao)
    mlflow = abrir_experimento(tracking_uri) if tracking_uri else None

    resultados, curvas = [], []
    with threadpool_limits(limits=4):
        for nome, modelo, ponderado in estimadores():
            pipeline = Pipeline([("preprocessamento", criar_preprocessador(contrato)), ("modelo", modelo)])
            ajuste = {"modelo__sample_weight": pesos} if ponderado else {}
            pipeline.fit(x_treino, y_treino, **ajuste)
            scores = pipeline.predict_proba(x_validacao)[:, 1]
            curva = []
            resultado = avaliar_candidato(nome, modelo, validacao, scores, ponderado, curva)
            resultado["atende_pisos"] = resultado["custo"] < min(
                aprovar_tudo["custo"], regra_pix["custo"], resultado["custo_threshold_0_5"]
            )
            if mlflow:
                resultado.update(registrar_run(mlflow, pipeline, x_treino.head(5), resultado, curva, contrato))
            resultados.append(resultado)
            curvas.extend(curva)
            print(f'{nome}: custo R$ {resultado["custo"]:.2f} | corte {resultado["threshold"]:.2f}', flush=True)

    resultados.sort(key=lambda candidato: (not candidato["atende_pisos"], candidato["custo"]))
    elegiveis = [r for r in resultados if r["atende_pisos"]]
    relatorio = {
        "avaliacao": "Validação usada para escolher modelo e corte nas semanas 11–12",
        "contrato": contrato["versao"],
        "features": colunas,
        "semanas_treino": TREINO,
        "semanas_validacao": VALIDACAO,
        "linhas_treino": len(treino),
        "linhas_validacao": len(validacao),
        "sha256": hashes_historico(),
        "ambiente": {"python": platform.python_version(),
                     **{p: version(p) for p in ("numpy", "pandas", "scipy", "scikit-learn")}},
        "baselines": {"aprovar_tudo": aprovar_tudo, "pix_acima_1000": regra_pix},
        "candidato": elegiveis[0]["modelo"] if elegiveis else None,
        "resultados": resultados,
    }
    destino.mkdir(parents=True, exist_ok=True)
    salvar_comparacao(destino / "comparacao.json", relatorio)
    pd.DataFrame(curvas).to_csv(destino / "curvas_custo.csv", index=False)
    return relatorio


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=config.RAIZ / "resultados_validacao")
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--mlflow", action="store_true", help="Registra todas as runs no MLflow configurado")
    modo.add_argument("--candidato", action="store_true", help="Registra o candidato da comparação existente")
    args = parser.parse_args()
    if args.candidato:
        candidato = registrar_candidato(args.saida, config.MLFLOW_TRACKING_URI)
        print(f'Candidato {candidato["modelo"]} registrado na run {candidato["run_id"]}.')
    else:
        comparar(args.saida, config.MLFLOW_TRACKING_URI if args.mlflow else None)


if __name__ == "__main__":
    main()
