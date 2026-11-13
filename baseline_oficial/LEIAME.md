# Baseline oficial

Um modelo de referência, treinado com as mesmas regras da parte 1 (contrato v1.0, treino nas semanas 1–10, validação nas semanas 11 e 12, threshold pelo custo). Ele existe para que **ninguém fique travado nas partes 2 e 3 por causa da parte 1**.

| Arquivo | O que é |
|---|---|
| `modelo/` | O pipeline (pré-processamento + HistGradientBoosting) no formato do MLflow |
| `referencia/referencia_validacao.csv` | A referência do monitoramento: features, `semana`, `fraude` e `score` das semanas 11–12 |
| `metricas.json` | Algoritmo, divisão e métricas na validação (threshold, recall, precision, PR-AUC, custo) |
| `registrar_baseline.py` | Registra o baseline como nova versão do `antifraude` no seu MLflow |
| `features.py`, `monitoramento.py` | O pré-processamento e um monitoramento de referência |

## Usar ou não usar?

A escolha é sua, e as duas valem:

- **Não conseguiu chegar a um bom modelo na parte 1?** Por exemplo: o custo ficou acima do piso, o pipeline não roda no sistema, faltou a referência ou o threshold está errado. Nesse caso, **use o baseline**. Você não perde ponto por isso nesta parte.
- **O seu modelo está funcionando?** Ele está como `@champion`, tem o threshold, tem a referência e o sistema pontua com ele. Então **pode continuar com ele**.

Em qualquer caso, registre a escolha e o motivo na decisão da semana 13. Se ficar em dúvida, registre o baseline sem promover e compare os dois na validação antes de decidir.

## Como registrar

A partir da raiz do projeto, com o MLflow no ar:

```bash
python baseline_oficial/registrar_baseline.py              # só registra uma nova versão
python baseline_oficial/registrar_baseline.py --promover   # registra e aponta o @champion para ela
```

O script cria a run `baseline_oficial` no experimento `antifraude-baseline-oficial` e grava a referência como artefato da run, em `referencia/`. A versão registrada recebe as tags `threshold` e `motivo` e uma descrição.

Se você promover o baseline, ele passa a ser o seu modelo em produção e precisa de uma entrada no `CHANGELOG.md`, como qualquer troca.

## E o monitoramento?

Se o seu `monitoramento.py` não ficou pronto na parte 1, pode partir do `baseline_oficial/monitoramento.py`. Copie-o para a raiz e adapte. O que for seu, registre no changelog.
