# Banco Aurora — Prevenção a Fraudes · Prática de MLOps

Este é o sistema de produção da prática. Ele recebe os lotes semanais de transações, valida cada lote contra o contrato de features, pontua com o modelo que está no MLflow como `@champion` e mostra ao negócio quanto a fraude está custando.

O **modelo é seu**. O sistema só sabe usar o que você registrar no MLflow.

## O que você precisa

- **Python 3.10 a 3.13**
- **O seu Postgres** (o container que você já usa nas aulas), com um usuário que possa criar bancos
- `psql` para rodar os scripts `.sql` (pode ser o do próprio container: `docker exec -i <container> psql ...`)

Ambiente virtual é **recomendado, não obrigatório**: organize a pasta como preferir. As versões do `requirements.txt` são as testadas. Se você instalar no Python global e houver conflito com outro projeto, o ajuste é seu.

## Passo a passo

### 1. Bancos e tabelas

Um servidor Postgres, dois bancos, como nas aulas: `antifraude` (o sistema) e `mlflow` (o MLflow).

```bash
psql -h localhost -U postgres -f sql/01_criar_bancos.sql
psql -h localhost -U postgres -d antifraude -f sql/02_criar_tabelas.sql
psql -h localhost -U postgres -d antifraude -c "\dt"     # tem que listar 6 tabelas
```

Se o Postgres estiver só dentro do container, sem a porta exposta:

```bash
docker exec -i <container> psql -U postgres < sql/01_criar_bancos.sql
docker exec -i <container> psql -U postgres -d antifraude < sql/02_criar_tabelas.sql
```

O `02_criar_tabelas.sql` é idempotente: rodar duas vezes não quebra nada.

### 2. Configuração

```bash
cp .env.exemplo .env          # ajuste usuário, senha, host e porta do SEU Postgres
pip install -r requirements.txt
python config.py              # confere as conexões e imprime o comando do MLflow
```

### 3. MLflow (terminal 1)

O servidor do MLflow **não lê o `.env`**: a conexão vai na linha de comando. Use exatamente o comando que o `python config.py` imprimiu. Com os valores padrão:

```bash
python -m mlflow server --host 127.0.0.1 --port 5000 --backend-store-uri postgresql://postgres:postgres@localhost:5432/mlflow --default-artifact-root ./mlruns
```

Abra http://127.0.0.1:5000.

Se aparecer `ImportError: cannot import name 'FallbackAsyncAdaptedQueuePool'`, rode `pip install "sqlalchemy<2.1"`.

### 4. Sistema (terminal 2)

Sempre a partir desta pasta (a raiz do projeto):

```bash
uvicorn app.main:app --reload --port 8000
```

Abra http://127.0.0.1:8000. Antes do seu primeiro modelo, o topo da tela mostra **"sem modelo em produção"** — é o esperado.

### 5. Notebook (terminal 3)

```bash
jupyter notebook parte1.ipynb
```

Rode o notebook **a partir desta pasta**, com o MLflow e o sistema no ar.

## Como o modelo entra em produção

O sistema usa sempre `models:/antifraude@champion`. Para isso, a versão registrada precisa:

1. **Receber as 13 features do contrato, cruas, na ordem do contrato.** Todo o pré-processamento mora dentro do modelo (um `Pipeline`). O sistema não transforma nada.
2. **Ter `predict_proba`.** Registre com `mlflow.sklearn.log_model`. Se o seu pipeline usa código seu (uma classe ou função do `features.py`), passe `code_paths=["features.py"]`, senão o sistema não consegue carregar o modelo.
3. **Ter a tag `threshold` na VERSÃO** (não na run), com o corte de bloqueio: `score >= threshold` bloqueia.
4. Opcional, mas cobrado na rastreabilidade: tag `motivo` na versão e uma descrição. O sistema anota o motivo em **Modelo → Histórico de trocas**.

Trocar o modelo em produção = mover o alias `champion` no MLflow. O sistema percebe na próxima chamada; não precisa reiniciar. Para aplicar o modelo novo a semanas já recebidas, use **Repontuar** na tela de Lotes.

## O que tem na pasta

| Arquivo | O que é |
|---|---|
| `contrato/contrato_features.yaml` | O contrato de features v1.0. O sistema valida todo lote contra ele |
| `dados/` | Os dados da parte 1 (histórico rotulado, semanas 1 a 12) |
| `demanda_parte1.md` | O que o negócio pediu |
| `parte1.ipynb` | O roteiro técnico da parte 1: instruções, o código é seu |
| `features.py`, `monitoramento.py` | Vazios: você escreve. Serão reutilizados nas partes 2 e 3 |
| `CHANGELOG.md` | O histórico de versões do seu modelo, mantido por você |
| `app/` | O sistema: API em FastAPI e front em HTML/CSS/JS puro (`app/static/`). Encanamento: vem pronto, não precisa mexer |
| `sql/` | Criação dos bancos e das tabelas do sistema |
| `config.py`, `.env.exemplo` | Configuração das conexões |

## Como o sistema é montado

- **Back:** FastAPI (`app/main.py`), só API — devolve JSON e CSV.
- **Front:** HTML, CSS e JavaScript puros (`app/static/`), sem biblioteca. Cada página chama a API com `fetch`.
- O próprio FastAPI serve as páginas. A documentação automática das rotas fica em http://127.0.0.1:8000/docs.

| Página | O que faz | Rotas que ela chama |
|---|---|---|
| `/` | Painel do negócio, por semana: volume, % bloqueado e, quando há rótulo, fraude evitada, fraude perdida e custo | `GET /api/painel` |
| `/lotes` | Recebe o CSV de transações de uma semana; valida, grava e pontua. Também **Repontuar** e **baixar dados** | `GET/POST /api/lotes`, `POST /api/lotes/{n}/repontuar` |
| `/rotulos` | Recebe o CSV de contestações (rótulos) | `POST /api/rotulos` |
| `/modelo` | Quem está em produção, threshold e histórico de trocas | `GET /api/modelo` |
| `/decisoes` | Seu registro de decisões, por semana, e exportação | `GET/POST /api/decisoes` |
| todas | O selo do modelo no topo | `GET /api/saude` |

Outras rotas úteis:

| Rota | O que faz |
|---|---|
| `POST /predict` | Pontua transações avulsas (lista de JSON com as 13 features) |
| `GET /api/semanas/{n}/dados.csv` | Transações da semana + score vigente + rótulo (quando houver). É o que o seu monitoramento lê |
| `GET /api/painel.csv` | O painel em CSV |
| `GET /api/decisoes/exportar.csv` | Suas decisões, para a entrega das partes 2 e 3 |

O painel mostra **a visão do negócio**. Drift e análise de performance por segmento são seus, nos notebooks.

## Monitoramento semanal

Com o MLflow e o champion ativos, rode `python preparar_monitoramento.py` uma vez para pontuar as semanas 11 e 12, salvar `referencia/validacao_11_12.csv`, registrar a referência na run campeã e gerar `relatorio_zero/`. O [relatório zero](relatorio_zero/README.md) explica os limites de alerta.

Depois de enviar uma semana na tela **Lotes**, rode `python monitorar_semana.py 13` (ajuste o número). O comando lê o CSV já pontuado da API, usa a referência da run apontada por `@champion` e salva drift e saída em `monitoramento/semana_13/`. Quando os rótulos da semana chegarem em **Rótulos**, rode o mesmo comando para obter também a performance global e por canal. Em caso de troca do champion, execute `python preparar_monitoramento.py` para registrar a referência da nova run.

## Recomeçar do zero

```bash
psql -h localhost -U postgres -c "DROP DATABASE antifraude" -c "DROP DATABASE mlflow"
```

Depois apague a pasta `mlruns/` e refaça o passo 1.
