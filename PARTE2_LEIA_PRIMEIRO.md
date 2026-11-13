# Parte 2 — como instalar este pacote

Este pacote **completa** a pasta `antifraude_mlops/` que você já tem. Ele não substitui nada seu: o único arquivo que já existia é o `app/modelo.py`, do sistema.

1. Extraia o `.zip` **no mesmo lugar onde está a sua pasta `antifraude_mlops/`**, para que as duas se juntem. Se o sistema operacional perguntar, escolha "mesclar" e aceite substituir o `app/modelo.py`.
2. Confira que apareceram, dentro de `antifraude_mlops/`:

   | Arquivo ou pasta | O que é |
   |---|---|
   | `demanda_parte2.md` | O pedido do negócio. Leia o e-mail principal primeiro; os anexos têm hora para serem lidos |
   | `parte2.ipynb` | O roteiro técnico |
   | `dados/parte2/` | Lotes das semanas 13 a 16 e rótulos das semanas 13 a 15 |
   | `baseline_oficial/` | Um modelo pronto. Use-o se não conseguiu um bom modelo na parte 1; senão, continue com o seu (veja o `LEIAME.md` dele) |
   | `resposta_parte2.md` | Onde você escreve a resposta para a Helena |
   | `app/modelo.py` | Correção do sistema (veja abaixo) |

3. **Reinicie o sistema** (o `uvicorn`) se ele estiver no ar, para carregar o `app/modelo.py` novo. Depois suba o resto do ambiente como na parte 1: Postgres, MLflow (terminal 1), sistema (terminal 2) e Jupyter (terminal 3). Os passos estão no `README.md`.
4. Abra o `parte2.ipynb` e rode a célula da seção 0.

Não é preciso instalar nada novo: o `requirements.txt` não mudou.

## A correção do `app/modelo.py`

Quando uma versão do modelo é registrada com `code_paths=["features.py"]`, o sistema carrega o `features.py` que foi registrado junto com ela.

Na versão anterior do sistema, havia um problema ao trocar o `@champion` para uma versão com um `features.py` diferente. O sistema podia reaproveitar o `features.py` da versão antiga, que tinha ficado na memória. Com isso, o carregamento falhava ou, pior, usava código desatualizado, até alguém reiniciar o sistema.

A correção descarrega o código da versão anterior antes de carregar a nova. Nada muda no que você faz.
