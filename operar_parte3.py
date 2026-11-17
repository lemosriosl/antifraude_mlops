"""Operação semanal e evidências da Parte 3 pelo sistema do Banco Aurora."""

import argparse
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import requests
from mlflow.tracking import MlflowClient

import config
from app import contrato
from features import pix_dispositivo_conhecido
from monitoramento import carregar_referencia_champion, carregar_semana, performance, relatorio_semana


DADOS = Path("dados/parte3")
EVIDENCIAS = Path("monitoramento/parte3")


def api(rota, metodo="get", **dados):
    resposta = requests.request(metodo, f"{config.SISTEMA_URL.rstrip('/')}{rota}", timeout=180, **dados)
    if not resposta.ok:
        raise RuntimeError(f"{metodo.upper()} {rota}: {resposta.status_code} {resposta.text[:1000]}")
    return resposta.json()


def enviar(rota, caminho):
    with caminho.open("rb") as arquivo:
        return api(rota, "post", files={"arquivo": (caminho.name, arquivo, "text/csv")})


def receber_semana(semana):
    lotes = {int(lote["semana"]): lote for lote in api("/api/lotes")}
    decisoes = {int(d["semana"]) for d in api("/api/decisoes")}
    if semana > 17 and semana - 1 not in decisoes:
        raise RuntimeError(f"Registre a decisão da semana {semana - 1} primeiro.")
    anterior = lotes[semana - 1]
    if semana not in lotes:
        recebimento = enviar("/api/lotes", DADOS / f"transacoes_semana_{semana:02d}.csv")
        print(recebimento)
        if not recebimento["pontuada"]:
            raise RuntimeError(recebimento["msg"])
    if anterior["rotulos"] != anterior["qtd_linhas"]:
        resultado = enviar("/api/rotulos", DADOS / f"rotulos_semana_{semana - 1:02d}.csv")
        print(resultado)
        if resultado["desconhecidos"] or resultado["inseridos"] + resultado["repetidos"] != anterior["qtd_linhas"]:
            raise RuntimeError("Os rótulos não cobrem o lote anterior.")


def modelo_vigente():
    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
    versao = MlflowClient().get_model_version_by_alias(config.NOME_MODELO, config.ALIAS_PRODUCAO)
    modelo = mlflow.sklearn.load_model(f"models:/{config.NOME_MODELO}/{versao.version}")
    return versao, modelo


def conferir_predict(lote, versao, modelo):
    colunas = contrato.nomes_features()
    grupo = pix_dispositivo_conhecido(lote)
    amostra = pd.concat([lote.loc[~grupo].head(6), lote.loc[grupo].head(6)])
    exemplo = contrato.tipar(amostra[colunas])
    scores = modelo.predict_proba(exemplo)[:, 1]
    retorno = pd.DataFrame(api("/predict", "post", json=exemplo.to_dict("records")))
    corte = float(versao.tags[config.TAG_THRESHOLD])
    np.testing.assert_allclose(retorno["score"], scores, rtol=0, atol=0.0000005)
    np.testing.assert_array_equal(retorno["bloquear"], scores >= corte)
    if not retorno["versao_modelo"].astype(str).eq(str(versao.version)).all():
        raise RuntimeError("A API diverge do champion.")
    return retorno.assign(id_transacao=amostra["id_transacao"].to_numpy(), score_mlflow=scores, grupo_pix=pix_dispositivo_conhecido(amostra).to_numpy())


def perfil_pix(df):
    """Hipótese operacional após o Anexo 1, com sinais disponíveis no contrato."""
    pix = df["canal"].eq("pix")
    padrao = pix_dispositivo_conhecido(df)
    return np.select([padrao, pix], ["pix_dispositivo_conhecido_2mais_1h", "outros_pix"], default="outros_canais")


def relatorio(semana):
    versao, modelo = modelo_vigente()
    conversao = modelo.named_steps["utc"]
    tabelas = relatorio_semana(semana, preparar_features=conversao.transform)
    tabelas["teste_predict"] = conferir_predict(carregar_semana(semana), versao, modelo)
    if semana >= 19:
        referencia, corte, _ = carregar_referencia_champion()
        referencia = referencia.assign(perfil=perfil_pix(referencia))
        perfis = []
        for numero in range(13, semana):
            lote = carregar_semana(numero)
            lote = lote.assign(perfil=perfil_pix(lote))
            medidas = performance(referencia, lote, corte, "perfil", threshold_lote=lote["threshold"].iat[0])
            medidas["semana"] = numero
            perfis.append(medidas if numero == 13 else medidas.query("conjunto == 'lote'"))
        tabelas["perfil_pix"] = pd.concat(perfis, ignore_index=True)
    pasta = EVIDENCIAS / f"semana_{semana}"
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, tabela in tabelas.items():
        tabela.to_csv(pasta / f"{nome}.csv", index=False)
    return tabelas


def registrar(semana, diagnostico, acao, observacoes="", *, retreinou=False):
    if any(int(d["semana"]) == semana for d in api("/api/decisoes")):
        raise RuntimeError(f"Já existe uma decisão para a semana {semana}.")
    return api("/api/decisoes", "post", json={
        "semana": semana, "diagnostico": diagnostico, "acao": acao,
        "observacoes": observacoes, "retreinou": retreinou,
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("semana", type=int, choices=range(17, 21))
    args = parser.parse_args()
    if any(int(d["semana"]) == args.semana for d in api("/api/decisoes")):
        pasta = EVIDENCIAS / f"semana_{args.semana}"
        tabelas = {arquivo.stem: pd.read_csv(arquivo) for arquivo in pasta.glob("*.csv")}
        if not {"continuas", "discretas", "saida", "performance"}.issubset(tabelas):
            raise RuntimeError(f"Evidências originais indisponíveis em {pasta}.")
    else:
        receber_semana(args.semana)
        tabelas = relatorio(args.semana)
    for nome in ("continuas", "discretas"):
        tabela = tabelas[nome]
        print(nome, tabela[tabela["alerta"]].to_string(index=False))
    print(tabelas["saida"].tail(3).to_string(index=False))
    print(tabelas["performance"].query("semana == @args.semana - 1").to_string(index=False))
    if "perfil_pix" in tabelas:
        print(tabelas["perfil_pix"].query("semana >= 16 and segmento == 'perfil'").to_string(index=False))


if __name__ == "__main__":
    main()
