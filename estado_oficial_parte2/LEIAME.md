# Estado oficial pós-parte 2 (turma A)

Este é o ponto de partida "correto" ao fim da parte 2, para que **ninguém fique travado na parte 3 por causa da parte 2**.

**O que aconteceu na parte 2.** Desde a semana 14, a nova plataforma de processamento (Vértice) passou a mandar a hora e o dia em **UTC**: 3 horas adiantados em relação a Brasília. O modelo, treinado em horário de Brasília, passou a ver o jantar das 21h como uma transação da meia-noite e a reter muito cliente bom.

**A ação oficial foi:**
- converter UTC → Brasília **dentro do pipeline**, mantendo os mesmos pesos, sem retreinar;
- publicar o contrato v1.1, que documenta o UTC;
- repontuar só as semanas a partir da 14.

| Arquivo | O que é |
|---|---|
| `modelo/` | Pipeline: conversão UTC → Brasília + o baseline oficial (mesmos pesos) |
| `conversao_utc.py` | O código da conversão (vai junto com o modelo, via `code_paths`) |
| `referencia/referencia_validacao.csv` | Referência do monitoramento, em horário de Brasília, que é o que o modelo vê depois da conversão |
| `contrato_features.yaml` | O contrato v1.1 |
| `registrar_estado_oficial.py` | Registra no seu MLflow como nova versão do `antifraude` |

> **Monitoramento:** compare com a referência o que o **modelo vê**, ou seja, as features depois da conversão. Se comparar a hora crua, que está em UTC, o alarme de `hora_transacao` fica aceso para sempre.

## Usar ou não usar?

A escolha é sua, e as duas valem:

- **A sua parte 2 ficou boa?** O seu modelo em produção trata corretamente o que mudou nas semanas 13 a 16, e o contrato e a referência estão em dia. Então **continue com o seu**.
- **A sua parte 2 ficou errada ou incompleta?** Por exemplo: o diagnóstico ficou errado, faltou alguma ação ou o modelo não carrega no sistema. Nesse caso, **use o estado oficial**. Você não perde ponto por isso na parte 3.

Registre a escolha e o motivo na decisão da semana 17. Se adotar o estado oficial, isso entra também no `CHANGELOG.md`.

## Como adotar

A partir da raiz do projeto, com o MLflow e o sistema no ar:

1. **Você não enviou ao sistema as semanas 13 a 16 na parte 2?** Envie agora, antes de tudo, na ordem, com os rótulos de 13 a 15. Use os arquivos do pacote da parte 2. Os rótulos da semana 16, que chegam neste pacote, precisam do lote 16 no sistema.
2. Registre o estado oficial e promova-o:
   ```bash
   python estado_oficial_parte2/registrar_estado_oficial.py --promover
   ```
3. Copie `estado_oficial_parte2/contrato_features.yaml` para `contrato/contrato_features.yaml`. O sistema relê o contrato a cada lote.
4. A referência do monitoramento fica na run do novo champion, em `referencia/`. A tag `referencia_vigente`, na versão, diz qual arquivo usar.
