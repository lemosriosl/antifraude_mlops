# Changelog — modelo antifraude

Uma entrada por versão que chegou (ou quase chegou) à produção, da mais nova para a mais antiga.
A versão aqui precisa bater com a descrição da versão no MLflow e, quando o contrato mudar, com o `contrato_features.yaml`.

Modelo de entrada:

```markdown
## vX.Y.Z — DD/MM/AAAA
- **Tipo:** modelo | pipeline | contrato
- **Versão no MLflow:** antifraude v<n>
- **O que mudou:**
- **Por quê:**
- **Evidência:** (run do MLflow, métrica, teste de drift)
- **Impacto:** (custo, taxa de bloqueio, recall — antes e depois)
- **Retreinou?** sim | não
```

---

<!-- Escreva a sua primeira entrada (v1.0.0) abaixo desta linha. -->

## Parte 3 — especialista para Pix — 14/11/2026

- **Tipo:** modelo e referência.
- **Versão no MLflow:** **antifraude v9**, run `d81b7759854042a0a939e3f2832af1d6`, corte publicado 0,05 e contrato v1.1.
- **O que mudou:** um classificador de árvores por boosting pontua Pix em aparelho conhecido com duas ou mais transações na hora anterior. Seu corte interno de 0,0042658561 foi escolhido pelo custo e remapeado para 0,05. A v8 continua pontuando todas as outras transações. O pipeline mantém a conversão de UTC para Brasília.
- **Por quê:** nos rótulos da semana 18, o grupo concentrou 154 fraudes que passaram e R$ 29.544,12 em custo. O desempenho baixo se repetiu na semana 19.
- **Evidência:** o especialista foi ajustado com o grupo nas semanas 13 a 17 e nos cinco primeiros dias da 18. O fim de semana da 18 serviu para escolher o estimador e os cortes. Na semana 19, com o modelo e o corte já definidos, o custo passou de R$ 43.639,74 para R$ 16.269,41, com recall de 56,07% para 88,28%. O corte por grupo sem retreino custaria R$ 17.158,67. A referência vigente é `referencia/referencia_semana_19.csv`, com scores da v9 e atributos em Brasília.
- **Impacto:** repontuamos o lote 20, único sem contestações. As retenções passaram de 491 (2,47%) para 815 (4,10%) e as 324 retenções adicionais ficaram dentro do grupo. Conferimos 12 previsões na API, sendo seis no grupo, e os scores do lote inteiro após repontuar. Os lotes anteriores preservam a decisão que estava em produção.
- **Retreinou?** Sim, apenas para o segmento afetado. Para voltar, restaure `@champion` na v8 e confirme a versão na API.

## Parte 3 — adoção do estado oficial — 14/11/2026

- **Tipo:** pipeline, modelo e contrato.
- **Versão no MLflow:** **antifraude v8**, run `a296fb0a32b04d2c8f07d50d6b5aad06`, corte 0,05 e contrato v1.1.
- **O que mudou:** adotamos o modelo oficial fornecido para o fim da Parte 2. O pipeline recebe a hora e o dia da Vértice em UTC e os converte para Brasília antes da pontuação, inclusive na virada do dia. A referência em Brasília está na run, em `referencia/referencia_validacao.csv`.
- **Por quê:** a correção da Parte 2 alterou os dados armazenados dos lotes 15 e 16. O pipeline publicado até então dependia dessa correção externa. A versão oficial aplica a conversão aos novos lotes e à rota de previsão.
- **Impacto operacional:** o champion v8 começa no lote 17. Preservamos as pontuações históricas das semanas 13 a 16. Os lotes 15 e 16 já têm hora corrigida no banco e sofreriam outra conversão se repontuados diretamente com a v8.
- **Retreinou?** Não. A v8 contém os pesos do baseline oficial e o pipeline de fuso.

## v1.1.1 — 12/11/2026

- **Tipo:** correção dos dados dos lotes 15 e 16.
- **Versão no MLflow:** `antifraude v7` (`@champion`), corte 0,09, contrato v1.0 e referência das semanas 11–12.
- **O que mudou:** o reprocessamento explícito das semanas 15 e 16 converteu os timestamps da Vértice de UTC para Brasília, derivou a hora e o dia da semana e gravou novas predições. O CSV de origem e os scores originais foram preservados.
- **Por quê:** o deslocamento de três horas apareceu nas semanas 14 a 16. No teste retrospectivo da semana 14, a conversão reduziu o custo estimado de R$ 15.065,62 para R$ 10.525,93. A operação registrada da semana 14 foi preservada.
- **Evidência:** runs de operação `8b3dff66abf04f80896908490dc00f8d` (semana 15) e `b34d20d45413499e82cb14af7cfd5a83` (semana 16) no experimento `antifraude-operacao`, com os hashes dos arquivos, os intervalos das predições e o relatório após a correção. Cinco scores e decisões da API foram conferidos por lote.
- **Impacto:** na semana 15, 750 → 506 retenções (3,74% → 2,52%) e 741 → 501 clientes com retenção. Com as contestações da 15, o custo foi de R$ 9.759,94 após a correção, ante R$ 14.503,03 com a pontuação original. A proporção de fraudes detectadas (recall) subiu de 78,14% para 81,38%. Na semana 16, 803 → 546 retenções (4,02% → 2,74%) e 789 → 538 clientes com retenção. Custo e recall da 16 aguardam as contestações.
- **Retreinou?** Não.

## v1.1.0 — 10/11/2026

- **Tipo:** modelo
- **Versão no MLflow:** `antifraude v7` (`@champion`)
- **O que mudou:** Random Forest com 180 árvores, profundidade máxima 14 e mínimo de 15 transações por folha. O contrato v1.0 continua com 13 features. O sistema encaminha para verificação scores a partir de 0,09.
- **Por quê:** foi a configuração de menor custo entre as seis avaliadas. Custou R$ 18.866,83 nas semanas 11 e 12, diante de R$ 93.756,32 com corte 0,50, R$ 225.349,79 com a regra de Pix acima de R$ 1.000 e R$ 376.035,53 ao aprovar tudo.
- **Evidência:** run `98e2f8417abf497ebb1132c0a39f5258`, com 39.497 transações na referência. Os cinco scores e decisões da API bateram com o notebook. O modelo foi treinado nas semanas 1 a 10 e escolhido nas semanas 11 e 12.
- **Impacto:** economia de R$ 5.156,31 (21,46%) frente à v3 na validação. A taxa de bloqueio passou de 2,96% para 2,77%, o recall de 86,00% para 85,17% e a precisão de 44,18% para 46,67%. Foram bloqueadas 584 transações legítimas e aprovadas 89 fraudes.
- **Retreinou?** Sim. A v7 veio da comparação ampliada, usando as mesmas semanas de treino.

### Histórico de trocas antes da semana 13

O histórico do sistema e do MLflow, incluído na entrega em `evidencias_mlflow.json`, registra a sequência `v3 → v4 → v5 → v6 → v7`.

- **v3 → v4:** a run `b8e2bf42e82e40258dc55cb151c91d6d` republicou o mesmo modelo serializado da v3, com corte de 0,29. O `features.py` passou a procurar o YAML do contrato também ao lado do código exportado. As decisões das 39.497 transações de validação ficaram iguais.
- **v4 → v5:** a run `98e2f8417abf497ebb1132c0a39f5258` colocou em uso a floresta regularizada, com corte de 0,09. O motivo registrado foi o menor custo na validação das semanas 11 e 12 (R$ 18.866,83, ante R$ 24.023,14).
- **v5 → v6 → v7:** os três registros apontam para a mesma run e registram o mesmo corte de 0,09 e a mesma justificativa de menor custo. O histórico exportado contém apenas essa justificativa para as duas trocas. A v7 é a versão `@champion` usada nas quatro semanas da Parte 2 e identificada nos metadados da referência.

## v1.0.0 — 07/11/2026

- **Tipo:** modelo
- **Versão no MLflow:** `antifraude v3` (promovida na rodada inicial)
- **O que mudou:** primeira versão em produção. O Random Forest usa as 13 features do contrato v1.0 e bloqueia para verificação quando o score é maior ou igual a 0,29.
- **Por quê:** o corte de 0,29 minimizou o custo na validação. O Random Forest ficou abaixo da regressão logística (R$ 35.477,50), de aprovar tudo (R$ 376.035,53) e do próprio Random Forest com corte de 0,50 (R$ 35.381,44).
- **Evidência:** run `7260ffdde12740b38a547f1a41c50a98`, com a referência em `referencia/`. Treino nas semanas 1 a 10 e validação nas semanas 11 e 12, com PR-AUC de 0,8229 e precisão de 44,18%. A maior estatística KS no relatório zero foi D = 0,0594 para `idade_conta_dias`, abaixo do limite de 0,10.
- **Impacto:** nas semanas 11 e 12, em relação à regra de bloquear Pix acima de R$ 1.000, o custo caiu de R$ 225.349,79 para R$ 24.023,14 (economia de R$ 201.326,65 no período). A taxa de bloqueio passou de 0,63% para 2,96% e o recall de 9,83% para 86,00%. O modelo bloqueou 652 transações legítimas e aprovou 84 fraudes. O custo médio foi de R$ 12.011,57 por semana.
- **Retreinou?** Não. Esta versão veio do primeiro treinamento.
