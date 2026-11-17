# Parte 3 — como instalar este pacote

Este pacote **completa** a pasta `antifraude_mlops/`. Ele não substitui nenhum arquivo seu.

1. Extraia o `.zip` **no mesmo lugar onde está a sua pasta `antifraude_mlops/`**, para que as duas se juntem. Se o sistema operacional perguntar, escolha "mesclar".
2. Confira que apareceram, dentro de `antifraude_mlops/`:

   | Arquivo ou pasta | O que é |
   |---|---|
   | `demanda_parte3.md` | O pedido do negócio. Leia o e-mail principal primeiro; os anexos têm hora para serem lidos |
   | `parte3.ipynb` | O roteiro técnico |
   | `dados/parte3/` | Lotes das semanas 17 a 20 e rótulos das semanas 16 a 19 |
   | `estado_oficial_parte2/` | O ponto de partida oficial. Use-o se a sua parte 2 ficou errada ou incompleta; senão, continue com o seu (veja o `LEIAME.md` dele) |
   | `resposta_parte3.md` | Onde você escreve a resposta final para a Helena |

3. Suba o ambiente como sempre: Postgres, MLflow (terminal 1), sistema (terminal 2) e Jupyter (terminal 3).
4. Abra o `parte3.ipynb` e rode a célula da seção 0.

Os rótulos da semana 16 precisam do lote 16 no sistema. Se você não chegou a enviar as semanas 13 a 16 na parte 2, envie antes, usando os arquivos de `dados/parte2/`.
