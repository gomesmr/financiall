# Contrato: API HTTP — CRUD de Categorias (feature 003)

Adiciona ao contrato existente (`specs/001-importar-nfce/contracts/api.md`,
`specs/002-excluir-nota-fiscal/contracts/api.md`). Mesmas convenções:
JSON, mensagens em português (Princípio VI), erro de entrada usa `4xx`,
sucesso usa `2xx`.

## `GET /categorias`

Lista todas as categorias existentes, ordenadas por nome.

**Resposta** (`200`): `{"categorias": [{"id": <id>, "nome": "Alimentação"},
...]}`. Lista vazia (`{"categorias": []}`) quando não há categorias —
nunca um erro.

## `POST /categorias`

Cria uma categoria nova.

**Corpo** (JSON): `{"nome": "<nome>"}`.

| Cenário | Status HTTP | Corpo |
|---|---|---|
| Nome válido e ainda não usado | `201` | `{"mensagem": "Categoria criada com sucesso.", "categoria": {"id": <id>, "nome": "<nome>"}}` |
| Nome vazio ou só espaços | `422` | `{"erro": "Informe um nome para a categoria."}` |
| Nome já usado por outra categoria (comparação insensível a maiúsculas/minúsculas e espaços) | `422` | `{"erro": "Já existe uma categoria com esse nome."}` |

## `PUT /categorias/<id>`

Edita o nome de uma categoria existente.

**Corpo** (JSON): `{"nome": "<novo nome>"}`.

| Cenário | Status HTTP | Corpo |
|---|---|---|
| Categoria existe, nome válido e livre | `200` | `{"mensagem": "Categoria atualizada com sucesso.", "categoria": {"id": <id>, "nome": "<novo nome>"}}` |
| Categoria não existe | `404` | `{"erro": "Categoria não encontrada."}` |
| Nome vazio ou só espaços | `422` | `{"erro": "Informe um nome para a categoria."}` |
| Nome já usado por outra categoria | `422` | `{"erro": "Já existe uma categoria com esse nome."}` |

## `DELETE /categorias/<id>`

Exclui uma categoria. Notas que a usavam passam a "sem categoria"
(FR-006) — nunca ficam com referência quebrada.

| Cenário | Status HTTP | Corpo |
|---|---|---|
| Categoria existe (com ou sem notas associadas) | `200` | `{"mensagem": "Categoria excluída com sucesso."}` |
| Categoria não existe | `404` | `{"erro": "Categoria não encontrada."}` |

## `PUT /notas/<id>/categoria`

Atribui, troca ou remove a categoria de uma nota fiscal já importada.

**Corpo** (JSON): `{"categoria_id": <id> | null}`. `null` remove a
atribuição (nota volta a "sem categoria").

| Cenário | Status HTTP | Corpo |
|---|---|---|
| Nota e categoria existem (ou `categoria_id` é `null`) | `200` | `{"mensagem": "Categoria da nota atualizada com sucesso."}` |
| Nota não existe | `404` | `{"erro": "Nota não encontrada."}` |
| `categoria_id` informado não existe | `422` | `{"erro": "Categoria não encontrada."}` |

## `GET /notas` e `GET /ver/notas/<id>` — campo novo

Ambas as respostas/páginas já existentes (feature 001) passam a incluir a
categoria da nota (FR-009): campo `categoria` no JSON de
`GET /notas` — `{"id": <id>, "nome": "<nome>"} | null` — e a categoria (ou
"sem categoria") exibida na página HTML de detalhe. Nenhuma mudança de
status HTTP ou estrutura fora da adição desse campo.
