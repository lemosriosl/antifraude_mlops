# Relatório zero — semanas 11 e 12

O modelo `antifraude@champion` é a Random Forest v7, com corte 0,09 e run `98e2f8417abf497ebb1132c0a39f5258`. A referência completa reúne 39.497 transações rotuladas das duas semanas e está em `referencia/validacao_11_12.csv`, também registrada em `referencia/` na run do MLflow. Para o controle zero, a semana 11 (20.399 transações) é comparada com a 12 (19.098). As tabelas completas estão nos CSVs desta pasta.

## Leitura do controle zero

| Medida | Semana 11 | Semana 12 |
|---|---:|---:|
| Taxa de bloqueio | 2,819% | 2,723% |
| Valor bloqueado | R$ 293.779,50 | R$ 309.489,31 |
| Recall global | 85,44% | 84,88% |
| Precision global | 45,91% | 47,50% |
| PR-AUC global | 0,8197 | 0,8182 |
| Custo global | R$ 10.335,28 | R$ 8.531,55 |

O KS do **score** deu D = 0,0076 e p = 0,620. Para `valor_transacao`, D = 0,0051 e p = 0,960. A maior mudança de proporção nas discretas foi de aproximadamente 0,81 ponto percentual. Essas medidas ficaram abaixo dos limites de alerta.

`idade_conta_dias` é a exceção estatística: **D = 0,0594 e p ≈ 1,13 × 10⁻³⁰**. As contas envelhecem entre semanas e a amostra tem quase 20 mil transações em cada uma. Com tantos registros, o KS detecta até deslocamentos modestos. A média permaneceu próxima (816,60 vs. 815,87 dias), mostrando que o p-valor sozinho não mede gravidade prática. Ele também não é uma garantia de independência entre transações do mesmo cliente. Interpretamos D, proporções e impacto do modelo em conjunto. Há vários testes simultâneos, o que reforça o cuidado com p-valores isolados.

## Limites de alerta para as próximas semanas

| Medida | Alerta | Justificativa |
|---|---|---|
| Feature contínua ou score | KS **D > 0,10** | Acima do maior D observado no controle zero (0,0594), com margem para o envelhecimento natural das contas. O p-valor fica como evidência auxiliar. |
| Categórica, booleana, hora ou dia | Maior mudança absoluta de proporção **> 5 pontos percentuais** | O controle zero chegou a 0,81 pp; 5 pp sinalizam mudança operacional clara, mesmo com grande volume. |
| Taxa de bloqueio | Diferença absoluta **> 1 ponto percentual** frente à referência | A taxa base é ~3%; 1 pp representa alteração operacional grande. |
| Parcela do valor bloqueado | Diferença absoluta **> 3 pontos percentuais** frente à referência | Evita confundir valor total maior por simples variação no número ou valor das transações. |
| Recall, precision ou PR-AUC global | Queda **> 5 pontos percentuais** após chegada de todos os rótulos | A maior diferença global observada no controle zero foi de aproximadamente 1,6 pp. |
| Custo global | Custo por 1.000 transações **> 50% acima** do da referência, após rotulagem | O custo é sensível a poucas fraudes de alto valor. No controle zero, o custo por 1.000 transações caiu aproximadamente 12%. |
| Performance por `canal` | Queda **> 10 pontos percentuais** em recall, precision ou PR-AUC, com pelo menos 100 fraudes no segmento | Segmentos têm amostras menores e maior oscilação. Reportar todos os canais, mas só alertar automaticamente quando há base suficiente. |

Os limites são regras operacionais iniciais. Um alerta pede investigação das categorias ou faixas responsáveis, do volume e do impacto financeiro. Quando chega parte dos rótulos, a tabela mostra a cobertura e as métricas nas transações já rotuladas. Custo final e alertas de performance exigem cobertura completa. Um segmento ausente na referência fica com status `segmento_sem_referencia` e mantém suas métricas locais.

## Uso semanal

Após enviar o lote em **Lotes**, rode `python monitorar_semana.py 13` (troque o número da semana). O script lê `GET /api/semanas/{n}/dados.csv`, baixa a referência da run apontada por `@champion` e salva as tabelas em `monitoramento/semana_13/`. Após enviar os rótulos em **Rótulos**, rode o mesmo comando novamente. Se o champion mudar, crie e registre a nova referência com `python preparar_monitoramento.py` antes de monitorar o próximo lote.
