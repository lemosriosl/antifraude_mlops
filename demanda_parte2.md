**De:** Helena Prado — Gerente de Prevenção a Fraudes, Banco Aurora
**Para:** Time de Dados
**Data:** quarta-feira, 11/11/2026
**Assunto:** Agora é operação — semanas 13 a 16

Pessoal,

O modelo está aprovado. A partir de agora, vocês **operam** o modelo, além de mantê-lo.

**Como vai funcionar**

Enquanto vocês construíam o modelo, quatro semanas de transações ficaram represadas: as **semanas 13 a 16**, de 24/08 a 20/09. Vamos reproduzir a operação dessas semanas agora, **uma por vez, como se fosse ao vivo**. Cada semana tem o lote de transações e as contestações da semana anterior, que só fecham uma semana depois.

Junto vão os e-mails que circularam nessas semanas. Cada um está marcado com a data em que chegou. Leia cada e-mail **no ponto do roteiro em que ele chegou**, não antes.

**Roteiro**

| Passo | O que chega | O que fazer |
|---|---|---|
| 1 | Lote da semana 13 | Enviar ao sistema, monitorar, registrar a decisão da semana 13 |
| 2 | E-mail **Anexo 1** (sex 28/08) | Ler |
| 3 | Lote da semana 14 + contestações da 13 | Enviar, monitorar, registrar a decisão da semana 14 |
| 4 | Lote da semana 15 + contestações da 14 | Enviar, monitorar, registrar a decisão da semana 15 |
| 5 | E-mail **Anexo 2** (qui 10/09) | Ler |
| 6 | Lote da semana 16 + contestações da 15 | Enviar, monitorar, registrar a decisão da semana 16 |

Os arquivos estão em `dados/parte2/`. As contestações da semana 16 só chegam no próximo pacote.

**Regras**

1. **Uma decisão por semana, na ordem.** Vale mesmo quando a decisão é "nada a fazer". A decisão de uma semana usa só o que vocês tinham naquele momento.
2. **Mudou algo em produção** (modelo, pipeline, threshold ou contrato)? Então é uma versão nova, rastreável, com entrada no changelog.
3. **Retreinar não é de graça.** Exige validação e aprovação, e pode piorar o que estava bom. Quero ver retreino só quando as evidências pedirem, e quero saber por quê.
4. O **contrato de features continua valendo**. Se ele precisar mudar, a mudança é uma versão nova do contrato, combinada com a Plataforma, e não um remendo no modelo.

**Baseline oficial**

Mando também o **baseline oficial**, na pasta `baseline_oficial/`: um modelo de referência construído com as mesmas regras da parte 1. Vocês escolhem com qual modelo vão operar:

- se **não conseguiram chegar a um bom modelo** na parte 1, ou se algo ficou quebrado, **podem usar o baseline**;
- se o modelo de vocês está funcionando, **podem continuar com ele**.

As duas escolhas valem. O que eu quero é a escolha registrada, com o motivo, na decisão da semana 13.

O sistema continua sendo operado pelas telas: lotes, rótulos, decisões, modelo e painel.

**O que eu preciso até sexta-feira, 13/11, 23h59**

1. As quatro semanas operadas no sistema, com **uma decisão registrada por semana**.
2. Uma **resposta para mim**, no arquivo `resposta_parte2.md`. Quero saber o que aconteceu nessas semanas, quanto isso custou, o que vocês fizeram e o que eu devo esperar daqui para frente.

   Escrevam para uma gerente, não para um cientista de dados. "Houve drift na feature X" não me diz nada. Me digam o que mudou no mundo ou no dado, e o que isso significa em reais e em clientes.
3. Tudo rastreável: quem olhar o MLflow, o contrato e o changelog precisa entender o que está em produção e por quê.

O roteiro técnico está no `parte2.ipynb`.

Obrigada,
Helena
---

## Anexo 1

**De:** Marcos Teixeira — Plataforma de Pagamentos
**Para:** Time de Dados; Prevenção a Fraudes
**Data:** sexta-feira, 28/08/2026, 18h40
**Assunto:** Migração do processamento concluída neste fim de semana

Pessoal,

Neste fim de semana concluímos a migração do processamento de transações (cartão e Pix) para a nova plataforma da **Vértice Pagamentos**. A partir de segunda, 31/08 (semana 14), todas as transações passam por ela.

Do lado de vocês **nada muda**. O arquivo semanal tem o mesmo layout, as mesmas colunas e os mesmos tipos, e o contrato de features continua o mesmo. Testamos o arquivo contra o validador do sistema e ele passou.

Qualquer coisa, me chamem.

Abs,
Marcos

---

## Anexo 2

**De:** Helena Prado
**Para:** Time de Dados
**Data:** quinta-feira, 10/09/2026, 09h12
**Assunto:** ENC: Aumento de ligações por transação bloqueada

Pessoal, vejam abaixo. Isso é o modelo? Mudamos alguma coisa? Preciso de uma resposta antes de levar para a diretoria.

Helena

> **De:** Carla Menezes — Central de Atendimento
> **Para:** Helena Prado
> **Data:** quarta-feira, 09/09/2026, 17h55
>
> Helena, desde o começo do mês o volume de ligações de clientes com transação retida para confirmação disparou. Os atendentes dizem que é tudo muito comum: jantar, aplicativo de entrega, mercado no fim do dia, Pix para conhecido. Os clientes estão irritados porque "nunca tinha acontecido".
>
> Tivemos que remanejar gente de outras filas. Consegue ver o que está acontecendo?
>
> Carla
