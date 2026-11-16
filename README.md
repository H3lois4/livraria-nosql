# Livraria – Cliente-Servidor com Cosmos DB for MongoDB (Exercício 10.1)

MVP da livraria na arquitetura **cliente-servidor** do exercício 8.1, agora com o
**catálogo de livros em um banco NoSQL: Azure Cosmos DB for MongoDB**.

```
Cliente (navegador)  ──HTTP/JSON──▶  Servidor Flask (API)  ──▶  Cosmos DB for MongoDB (catálogo)
                                                            └─▶  TXT (lojas e preferências)
```

## Banco NoSQL

- Banco `livraria`, coleção `livros`.
- Cada livro é um **documento**, com o estoque por loja embutido:

```json
{
  "_id": "9788535902775",
  "isbn": "9788535902775",
  "titulo": "Dom Casmurro",
  "autor": "Machado de Assis",
  "preco": 29.9,
  "estoque": { "paulista": 3, "pinheiros": 0 },
  "busca": "dom casmurro machado de assis"
}
```

- Na primeira execução, se a coleção estiver vazia, o servidor cadastra **12 livros**
  (`servidor/catalogo_mongo.py`). Novos livros podem ser cadastrados com `POST /api/livros`.
- A string de conexão **não fica no código**: vem da variável de ambiente `MONGODB_URI`
  (configurada no App Service). Sem ela, o app usa um MongoDB em memória (testes e uso local).

## API

| Método | Rota | O que faz |
|---|---|---|
| GET | `/api` | Informações da API e quantos livros há no catálogo |
| GET | `/api/livros?q=termo` | Busca livros por título ou autor (no banco) |
| GET | `/api/livros/<isbn>` | Livro + estoque por loja (favorita primeiro) |
| POST | `/api/livros` | Cadastra um livro no Cosmos DB |
| GET | `/api/lojas` e `/api/lojas/<id>` | Lojas com endereço e horário |
| GET/PUT | `/api/clientes/me/loja-favorita` | Loja favorita do cliente |

Exemplo de cadastro:

```json
POST /api/livros
{ "isbn": "9788535930105", "titulo": "Torto Arado", "autor": "Itamar Vieira Junior",
  "preco": 59.9, "estoque": { "paulista": 2 } }
```

## Deploy

Pipeline em `.github/workflows/deploy.yml`: a cada push na `main`, roda os testes e publica
no Azure App Service. Configurações do App Service:

| Configuração | Valor |
|---|---|
| Comando de inicialização | `gunicorn --bind=0.0.0.0 --timeout 600 wsgi:app` |
| `MONGODB_URI` | string de conexão do Cosmos DB for MongoDB |
| `PASTA_DADOS` | `/home/data` |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` |

## Rodar localmente

```bash
pip install -r requirements.txt
pytest -q
python app.py    # http://localhost:5000
```
