# Relatório zero — semanas 11 e 12

Modelo: `antifraude@champion` v3, Random Forest, run `7260ffdde12740b38a547f1a41c50a98`, threshold 0,29. A referência completa reúne 39.497 transações rotuladas das duas semanas e está em `referencia/validacao_11_12.csv`, também registrada em `referencia/` na run do MLflow. Para o controle zero, a semana 11 (20.399 transações) é comparada somente com a 12 (19.098). As tabelas completas estão nos CSVs desta pasta.

## Leitura do controle zero

| Medida | Semana 11 | Semana 12 |
|---|---:|---:|
| Taxa de bloqueio | 3,000% | 2,911% |
| Valor bloqueado | R$ 282.599,52 | R$ 275.084,52 |
| Recall global | 86,41% | 85,57% |
| Precision global | 43,63% | 44,78% |
| PR-AUC global | 0,8217 | 0,8243 |
| Custo global | R$ 10.551,35 | R$ 13.471,79 |

O KS do **score** deu D = 0,0074 e p = 0,653; `valor_transacao` deu D = 0,0051 e p = 0,960. As maiores mudanças de proporção nas discretas ficaram abaixo de 0,81 ponto percentual. Não há evidência de mudança operacional relevante nessas medidas.

`idade_conta_dias` é a exceção estatística: **D = 0,0594 e p ≈ 1,13 × 10⁻³⁰**. As contas envelhecem entre semanas e a amostra tem quase 20 mil transações em cada uma. Com tantos registros, o KS detecta até deslocamentos modestos. A média permaneceu próxima (816,60 vs. 815,87 dias), mostrando que o p-valor sozinho não mede gravidade prática. Ele também não é uma garantia de independência entre transações do mesmo cliente. Interpretamos D, proporções e impacto do modelo em conjunto. Há vários testes simultâneos, o que reforça o cuidado com p-valores isolados.

## Limites de alerta para as próximas semanas

| Medida | Alerta | Justificativa |
|---|---|---|
| Feature contínua ou score | KS **D > 0,10** | Acima do maior D observado no controle zero (0,0594), com margem para o envelhecimento natural das contas. O p-valor fica como evidência auxiliar. |
| Categórica, booleana, hora ou dia | Maior mudança absoluta de proporção **> 5 pontos percentuais** | O controle zero chegou a 0,81 pp; 5 pp sinalizam mudança operacional clara, mesmo com grande volume. |
| Taxa de bloqueio | Diferença absoluta **> 1 ponto percentual** frente à referência | A taxa base é ~3%; 1 pp representa alteração operacional grande. |
| Parcela do valor bloqueado | Diferença absoluta **> 3 pontos percentuais** frente à referência | Evita confundir valor total maior por simples variação no número ou valor das transações. |
| Recall, precision ou PR-AUC global | Queda **> 5 pontos percentuais** após chegada de todos os rótulos | As diferenças globais observadas no controle zero são menores que 1,2 pp. |
| Custo global | Custo por 1.000 transações **> 50% acima** do da referência, após rotulagem | O custo é sensível a poucas fraudes de alto valor; no controle zero a variação do custo por 1.000 transações foi ~36%. |
| Performance por `canal` | Queda **> 10 pontos percentuais** em recall, precision ou PR-AUC, com pelo menos 100 fraudes no segmento | Segmentos têm amostras menores e maior oscilação. Reportar todos os canais, mas só alertar automaticamente quando há base suficiente. |

Os limites são regras operacionais iniciais, não testes de significância. Um alerta pede investigação das categorias ou faixas responsáveis, do volume e do impacto financeiro. Sem rótulos completos, só se avaliam drift e saída do modelo. Ao chegar o CSV de rótulos da semana anterior, roda-se novamente o monitoramento daquela semana para preencher a performance.

## Uso semanal

Após enviar o lote em **Lotes**, rode `python monitorar_semana.py 13` (troque o número da semana). O script lê `GET /api/semanas/{n}/dados.csv`, baixa a referência da run apontada por `@champion` e salva as tabelas em `monitoramento/semana_13/`. Após enviar os rótulos em **Rótulos**, rode o mesmo comando novamente. Se o champion mudar, crie e registre a nova referência com `python preparar_monitoramento.py` antes de monitorar o próximo lote.
