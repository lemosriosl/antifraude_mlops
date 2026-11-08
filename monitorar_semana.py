"""Monitora uma semana pontuada. Uso: python monitorar_semana.py 13"""

import argparse
from pathlib import Path

from monitoramento import carregar_referencia_champion, carregar_semana, monitorar


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("semana", type=int)
    args = parser.parse_args()
    referencia, threshold, versao = carregar_referencia_champion()
    lote = carregar_semana(args.semana)
    if lote["versao_modelo"].astype(str).ne(versao).any():
        raise ValueError(f"Semana {args.semana} não está totalmente pontuada pelo champion v{versao}; repontue em Lotes")
    tabelas = monitorar(referencia, lote, threshold)
    pasta = Path("monitoramento") / f"semana_{args.semana:02d}"
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, tabela in tabelas.items():
        if tabela is not None:
            tabela.to_csv(pasta / f"{nome}.csv", index=False)
        print(f"\n{nome}\n{tabela.to_string(index=False) if tabela is not None else 'Aguardando rótulos completos'}")
    print(f"\nChampion v{versao} | threshold {threshold} | tabelas em {pasta}")


if __name__ == "__main__":
    main()
