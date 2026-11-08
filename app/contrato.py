"""
Validação de dados contra o contrato de features (contrato/contrato_features.yaml).

O contrato é relido a cada chamada: se você publicar uma versão nova do YAML,
o próximo lote já é validado por ela, sem reiniciar o sistema.
"""
import pandas as pd
import yaml

import config


def carregar():
    with open(config.CONTRATO, encoding="utf-8") as f:
        return yaml.safe_load(f)


def nomes_features(contrato=None):
    contrato = contrato or carregar()
    return [f["nome"] for f in contrato["features"]]


def tipar(df, contrato=None):
    """Converte as colunas de features para tipos simples (int64, float64, str).
    O modelo recebe sempre o mesmo tipo, venha o dado do CSV ou do banco."""
    contrato = contrato or carregar()
    df = df.copy()
    for f in contrato["features"]:
        col = f["nome"]
        if col not in df.columns:
            continue
        if f["tipo"] in ("int", "bool"):
            df[col] = pd.to_numeric(df[col]).astype("int64")
        elif f["tipo"] == "float":
            df[col] = pd.to_numeric(df[col]).astype("float64")
        else:
            df[col] = df[col].astype(str)
    return df


def validar(df, contrato=None, exigir_metadados=True, exigir_uma_semana=True):
    """Devolve (df_tipado, erros). df_tipado vem com as colunas na ordem do
    contrato (metadados primeiro, se exigidos). Se `erros` não estiver vazio,
    o lote deve ser rejeitado."""
    contrato = contrato or carregar()
    erros = []
    feats = contrato["features"]
    meta = contrato.get("metadados", []) if exigir_metadados else []
    esperadas = meta + [f["nome"] for f in feats]

    faltando = [c for c in esperadas if c not in df.columns]
    if faltando:
        return df, [f"Colunas obrigatórias ausentes: {', '.join(faltando)}"]
    extras = [c for c in df.columns if c not in esperadas]
    if extras:
        erros.append(f"Colunas não previstas no contrato: {', '.join(extras)}")
    df = df[esperadas].copy()

    if len(df) == 0:
        return df, ["O arquivo não tem linhas."]

    nulos = df.isna().sum()
    for col, n in nulos[nulos > 0].items():
        erros.append(f"{col}: {n} valores vazios")

    for f in feats:
        col, tipo = f["nome"], f["tipo"]
        s = df[col]
        if tipo in ("int", "float", "bool"):
            num = pd.to_numeric(s, errors="coerce")
            ruins = num.isna() & s.notna()
            if ruins.any():
                erros.append(f"{col}: {ruins.sum()} valores não numéricos (ex.: {s[ruins].iloc[0]!r})")
                continue
            if tipo in ("int", "bool") and ((num.dropna() % 1) != 0).any():
                erros.append(f"{col}: esperado inteiro, vieram valores com casas decimais")
                continue
            if tipo == "bool":
                fora = ~num.dropna().isin([0, 1])
                if fora.any():
                    erros.append(f"{col}: esperado 0 ou 1, vieram {sorted(num.dropna()[fora].unique()[:5])}")
                df[col] = num.astype("Int64")
                continue
            if "min" in f and (num < f["min"]).any():
                erros.append(f"{col}: {(num < f['min']).sum()} valores abaixo do mínimo {f['min']}")
            if "max" in f and (num > f["max"]).any():
                erros.append(f"{col}: {(num > f['max']).sum()} valores acima do máximo {f['max']}")
            df[col] = num.astype("Int64") if tipo == "int" else num.astype(float)
        elif tipo == "categoria":
            permitidos = set(map(str, f["valores"]))
            fora = ~s.astype(str).isin(permitidos) & s.notna()
            if fora.any():
                novos = sorted(s[fora].astype(str).unique())[:5]
                erros.append(f"{col}: {fora.sum()} valores fora da lista do contrato (ex.: {novos})")
            df[col] = s.astype(str)

    if exigir_metadados:
        if df["id_transacao"].duplicated().any():
            erros.append(f"id_transacao: {df['id_transacao'].duplicated().sum()} ids duplicados no arquivo")
        semanas = pd.to_numeric(df["semana"], errors="coerce").dropna().unique()
        if exigir_uma_semana and len(semanas) != 1:
            erros.append(f"semana: o arquivo deve ter uma única semana, veio {sorted(semanas)[:5]}")
        datas = pd.to_datetime(df["data_transacao"], errors="coerce")
        if datas.isna().any():
            erros.append(f"data_transacao: {datas.isna().sum()} datas inválidas")

    if not erros:
        for r in contrato.get("regras") or []:
            try:
                alvo = df.query(r["quando"]) if r.get("quando") else df
                quebram = len(alvo) - len(alvo.query(r["exigir"]))
            except Exception as e:  # regra mal escrita no YAML
                erros.append(f"regra '{r.get('nome')}': não foi possível avaliar ({e})")
                continue
            if quebram:
                erros.append(f"regra '{r['nome']}': {quebram} linhas não cumprem '{r['exigir']}'")
    return df, erros
