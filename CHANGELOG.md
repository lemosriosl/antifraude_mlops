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

## v1.0.0 — 07/11/2026

- **Tipo:** modelo
- **Versão no MLflow:** `antifraude v3` (`@champion`)
- **O que mudou:** primeira versão em produção. O Random Forest usa as 13 features do contrato v1.0 e bloqueia para verificação quando o score é maior ou igual a 0,29.
- **Por quê:** o corte de 0,29 minimizou o custo na validação. O Random Forest ficou abaixo da regressão logística (R$ 35.477,50), de aprovar tudo (R$ 376.035,53) e do próprio Random Forest com corte de 0,50 (R$ 35.381,44).
- **Evidência:** run `7260ffdde12740b38a547f1a41c50a98`, com a referência em `referencia/`. Treino nas semanas 1 a 10 e validação nas semanas 11 e 12, com PR-AUC de 0,8229 e precisão de 44,18%. A maior estatística KS no relatório zero foi D = 0,0594 para `idade_conta_dias`, abaixo do limite de 0,10.
- **Impacto:** nas semanas 11 e 12, em relação à regra de bloquear Pix acima de R$ 1.000, o custo caiu de R$ 225.349,79 para R$ 24.023,14 (economia de R$ 201.326,65 no período). A taxa de bloqueio passou de 0,63% para 2,96% e o recall de 9,83% para 86,00%. O modelo bloqueou 652 transações legítimas e aprovou 84 fraudes. O custo médio foi de R$ 12.011,57 por semana.
- **Retreinou?** Não. Esta versão veio do primeiro treinamento.
