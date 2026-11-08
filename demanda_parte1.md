**De:** Helena Prado — Gerente de Prevenção a Fraudes, Banco Aurora
**Para:** Time de Dados
**Cc:** Plataforma de Dados
**Data:** sexta-feira, 06/11/2026
**Assunto:** Modelo de bloqueio de transações — o que precisamos até quarta

Pessoal, bom dia.

Hoje a nossa defesa contra fraude é um conjunto de regras fixas, e elas estão perdendo a corrida: a cada golpe novo, a gente escreve mais uma regra, e ela já nasce atrasada. A diretoria aprovou trocarmos isso por um modelo. Vocês ficam com a construção **e com a operação** dele.

**O que o modelo precisa fazer**

Para cada transação (Pix, cartão presencial e cartão online), decidir entre **aprovar** ou **bloquear para verificação**. Bloquear não é cancelar: o cliente recebe uma notificação e confirma a transação no app.

**Quanto custa errar**

As duas formas de errar têm custos bem diferentes, e é por elas que eu vou julgar o modelo:

- **Fraude aprovada:** o banco ressarce o cliente. O prejuízo é **o valor da transação**.
- **Cliente legítimo bloqueado:** atendimento, atrito e, muitas vezes, a compra perdida. Nas nossas contas, **R$ 15 por transação**.

Não me tragam "acurácia". Fraude é cerca de 1,5% das transações: um modelo que aprova tudo acerta 98,5% e me custa uma fortuna. Quero saber **quanto o modelo custa por semana** e quanto ele economiza em relação ao que temos.

**Como a fraude é confirmada**

Só sabemos que uma transação era fraude quando o cliente contesta. As contestações de uma semana fecham **uma semana depois**. Ou seja: o que o modelo decidir hoje, só vamos saber se acertou na semana que vem.

**O que estou mandando**

- O histórico de **12 semanas** de transações (cerca de 240 mil), já com o resultado das contestações.
- O **contrato de features** do time de Plataforma, com as 13 informações que o sistema de produção entrega para cada transação. É isso e só isso que o modelo vai receber em produção.
- O **sistema de produção**, que vocês vão rodar e operar.

**Regras do jogo** (combinadas com a Plataforma)

1. O modelo consome **exatamente** as 13 features do contrato, com as regras de cálculo dele. Nem uma a mais, nem uma a menos.
2. O algoritmo é escolha de vocês, mas quero ver **pelo menos duas alternativas comparadas** e a escolha justificada pelo custo.
3. Para que os números de todos sejam comparáveis: **treino nas semanas 1 a 10, validação nas semanas 11 e 12**. Nada de misturar semanas.
4. O modelo precisa, no mínimo, custar menos do que (a) aprovar tudo, (b) a regra que mais usamos hoje — **bloquear todo Pix acima de R$ 1.000** — e (c) ele mesmo com o corte padrão de 0,5.

**O que eu preciso até quarta-feira, 11/11, 23h59**

- O modelo **em produção** no sistema, com o ponto de corte (a partir de que score bloquear) escolhido pelo custo.
- Tudo registrado de forma que qualquer pessoa do time consiga saber **qual modelo está em produção, de onde ele veio e por que foi escolhido**.
- O **monitoramento pronto**. A partir de quarta, vocês passam a receber as transações semana a semana, e eu quero que vocês percebam qualquer problema **antes** de eu reclamar.

Os detalhes técnicos estão no notebook que acompanha este e-mail.

Obrigada,
Helena
