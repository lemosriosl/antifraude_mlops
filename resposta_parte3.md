**De:** Levy Guilherme Lemos Rios — Time de Dados
**Para:** Helena Prado
**Assunto:** RE: Última etapa — semanas 17 a 20

Helena,

### Semanas 17 a 20

| Semana das transações | Custo confirmado | Fraudes detectadas | O que observamos |
|---|---:|---:|---|
| 17 | R$ 16.786,97 | 82,14% | O volume de retenções ficou dentro do esperado. |
| 18 | R$ 44.205,70 | 59,75% | A queda na detecção se concentrou em Pix feitos no aparelho habitual do cliente, após duas ou mais transações na última hora. |
| 19 | R$ 43.639,74 | 56,07% | Com o modelo em uso naquele lote, o mesmo grupo concentrou R$ 31.843,32 do custo da semana. |
| 20 | Aguardando contestações | Aguardando contestações | Com a nova versão, as transações retidas para verificação passaram de 491 para 815. As 324 retenções adicionais ficaram no grupo investigado. |

O padrão é compatível com o golpe da mão fantasma. Na semana 18, o modelo detectou apenas **14 de 168** fraudes no grupo investigado. Entre as fraudes aprovadas nesse grupo, o valor mediano era de R$ 126,10. O dado disponível identifica o aparelho habitual e a sequência de operações. A confirmação de acesso remoto depende da investigação dos relatos dos clientes.

Os volumes gerais e a proporção de transações retidas continuaram perto do esperado. O relatório só conseguiu medir a queda de detecção com a chegada das contestações, uma semana depois. O relatório já mostrou o problema com os rótulos da semana 18. Faltou transformar esse alerta em uma comunicação para Prevenção a Fraudes e Ouvidoria. Vamos abrir uma investigação quando esses relatos aumentarem, mesmo antes do fechamento das contestações.

Colocamos em produção um modelo específico para esse perfil. Aplicado em teste às mesmas transações da semana 19, ele teria detectado **168 das 176** fraudes do grupo, ante 14 com a versão anterior. O custo total teria caído em **R$ 27.370,33**, com 172 verificações adicionais de transações legítimas. As decisões fora do grupo ficaram iguais. Essa economia é uma estimativa de validação. As contestações da semana 20 vão mostrar o resultado do novo modelo na operação.

### Balanço da operação

Na semana 14, a troca de plataforma mudou o fuso dos arquivos. Corrigimos os lotes 15 e 16 e, a partir da 17, a conversão passou a fazer parte do sistema de pontuação. Nos lotes 15 e 16, as contestações confirmam **R$ 9.545,41** a menos de custo em relação às pontuações originais. A partir da semana 18, passamos a lidar também com a mudança no padrão de fraude em Pix.

Nas semanas **13 a 19**, as transações retidas somaram **R$ 1.154.812,33 em fraudes confirmadas**. Descontando R$ 33.015,00 pelas 2.201 retenções legítimas, a economia líquida foi de **R$ 1.121.797,33** frente ao cenário de aprovar tudo. O custo observado no período foi de **R$ 154.356,73**, dos quais **R$ 104.632,41** nas semanas 17 a 19. O balanço financeiro da semana 20 será fechado com as contestações.

### O que acompanhar

- **Ao receber o lote**, conferir o fuso e a qualidade dos campos, a distribuição de risco e as retenções por canal. Uma variação acima de 1 ponto percentual na taxa global de retenção abre uma investigação de dados e capacidade de atendimento.
- **Ao receber as contestações**, comparar o custo por mil transações e a proporção de fraudes detectadas, tanto no total quanto por canal. Investigar queda global superior a 5 pontos percentuais ou custo por mil 50% acima da referência. Acompanhar separadamente o Pix em aparelho conhecido com operações em sequência. Com pelo menos 30 fraudes confirmadas nesse grupo, uma detecção abaixo de 80% abre revisão imediata.
- **Com a Ouvidoria e o Atendimento**, consolidar os relatos de Pix não reconhecido e abrir investigação se o volume dobrar frente à média das quatro semanas anteriores ou se houver relatos convergentes do mesmo padrão. Se a nova versão custar mais do que a anterior nas mesmas transações já contestadas, voltar à versão anterior e revisar o grupo e o corte.
