**De:** Helena Prado — Gerente de Prevenção a Fraudes, Banco Aurora
**Para:** Time de Dados
**Data:** sexta-feira, 13/11/2026
**Assunto:** Última etapa — semanas 17 a 20

Pessoal,

Obrigada pela resposta sobre as semanas 13 a 16. Agora vamos fechar a operação represada: as **semanas 17 a 20**, de 21/09 a 18/10. O formato é o mesmo de antes: uma semana por vez, como se fosse ao vivo. Leia cada e-mail anexo **no ponto do roteiro em que ele chegou**.

**Roteiro**

| Passo | O que chega | O que fazer |
|---|---|---|
| 1 | Lote da semana 17 + contestações da 16 | Enviar, monitorar, registrar a decisão da semana 17 |
| 2 | Lote da semana 18 + contestações da 17 | Enviar, monitorar, registrar a decisão da semana 18 |
| 3 | E-mail **Anexo 1** | Ler |
| 4 | Lote da semana 19 + contestações da 18 | Enviar, monitorar, registrar a decisão da semana 19 |
| 5 | E-mail **Anexo 2** | Ler |
| 6 | Lote da semana 20 + contestações da 19 | Enviar, monitorar, registrar a decisão da semana 20 |

Os arquivos estão em `dados/parte3/`. As contestações da semana 20 eu guardo comigo: é com elas que vou conferir o modelo que vocês deixarem em produção.

**Regras:** as mesmas da etapa anterior, com duas novidades sobre retreino.

1. Uma decisão por semana, na ordem, só com o que vocês tinham naquele momento.
2. Mudou algo em produção? Então é uma versão nova, rastreável e com changelog.
3. O contrato de features continua valendo.
4. **Se retreinarem**, quero ver três coisas:
   - que o modelo novo é melhor que o atual **em dados que ele não viu**, pelo mesmo critério de custo;
   - com quais semanas ele foi treinado, e por quê;
   - como voltamos atrás se ele se comportar mal.
5. **Retreinar sem necessidade continua sendo um erro.** Deixar de retreinar quando é necessário também é.

**Ponto de partida**

Junto vai a pasta `estado_oficial_parte2/`: o modelo, o contrato e a referência como deveriam estar ao fim das semanas 13 a 16. Vocês escolhem com o que vão operar:

- se a parte 2 de vocês ficou certa, **continuem com o que vocês têm**;
- se ficou errada ou incompleta, **podem adotar o estado oficial**.

As duas escolhas valem. Registrem a escolha e o motivo na decisão da semana 17.

**O que eu preciso até segunda-feira, 16/11, 23h59**

1. As quatro semanas operadas no sistema, com **uma decisão registrada por semana**.
2. A **resposta final para mim**, no arquivo `resposta_parte3.md`. Ela vai para a diretoria e tem que responder a três perguntas:
   - **O que aconteceu nas semanas 17 a 20**, quanto isso custou e o que vocês fizeram.
   - **O balanço da operação inteira**, das semanas 13 a 20: o que mudou, o que foi feito e quanto isso evitou de prejuízo.
   - **O que acompanhar daqui para frente**: o que vocês vão olhar toda semana, o que faz vocês agirem e por que essas escolhas.

   Escrevam para uma gerente, não para um cientista de dados.
3. Tudo rastreável: MLflow, contrato e changelog contando a mesma história.

O roteiro técnico está no `parte3.ipynb`.

Obrigada,
Helena
---

## Anexo 1

**De:** Bruno Siqueira — Segurança da Informação
**Para:** Prevenção a Fraudes; Time de Dados; Atendimento
**Data:** sexta-feira, 02/10/2026, 16h30
**Assunto:** Alerta setorial: golpe da "mão fantasma"

Pessoal,

A federação dos bancos emitiu um alerta sobre um golpe que cresceu muito nas últimas semanas em todo o setor. Ele funciona assim:

1. O cliente recebe uma ligação de alguém que se apresenta como da "central de segurança" do banco e diz que a conta dele está sendo atacada.
2. Para "proteger" a conta, pedem que ele instale um aplicativo no celular. O aplicativo dá ao golpista **acesso remoto** ao aparelho.
3. Com o cliente ainda na linha, o golpista movimenta a conta **pelo próprio celular do cliente**. Ele faz várias transferências seguidas, de valores que não chamam atenção, para contas que recebem e repassam o dinheiro.

O cliente costuma perceber só horas depois.

Estamos reforçando a comunicação aos clientes. Vocês conseguem avaliar se o antifraude está pegando isso?

Bruno

---

## Anexo 2

**De:** Helena Prado
**Para:** Time de Dados
**Data:** quinta-feira, 15/10/2026, 08h50
**Assunto:** ENC: Pix não reconhecido — Ouvidoria

Pessoal, vejam abaixo. O painel mostra a fraude perdida subindo, e eu não recebi nenhum alerta de vocês. O monitoramento não viu nada? Como isso é possível? E o que vamos fazer?

Helena

> **De:** Patrícia Ramos — Ouvidoria
> **Para:** Helena Prado
> **Data:** quarta-feira, 14/10/2026, 18h10
>
> Helena, as reclamações de "Pix que eu não fiz" quase triplicaram nas últimas duas semanas. O padrão é parecido: o cliente jura que estava com o celular na mão, que nada foi feito de outro aparelho, e que saíram várias transferências pequenas, uma atrás da outra.
>
> Muitos estão pedindo ressarcimento. Precisamos de uma posição.
>
> Patrícia
