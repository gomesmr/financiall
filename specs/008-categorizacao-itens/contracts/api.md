# Contrato: API (feature 008)

Todos os endpoints novos seguem o mesmo padrão já usado em
`routes_categorias.py` (JSON, blueprint por domínio, mensagens de erro em
português — Princípio VI).

> **Nota sobre categoria/subcategoria**: em toda a API, "atribuir
> categoria e subcategoria" é sempre um único campo `categoria_id` —
> subcategoria é apenas uma linha de `categoria` mais funda na
> hierarquia (data-model.md), nunca um campo separado. No cliente, o
> campo de seleção é um autocomplete único sobre a lista já carregada de
> categorias/subcategorias (`GET /categorias`, sem endpoint de busca
> novo — a taxonomia é pequena o suficiente para filtrar no navegador);
> ao escolher uma subcategoria, a categoria-pai é exibida automaticamente
> a partir do `parent_id` do item escolhido, sem seleção separada.
> Escolher diretamente uma categoria de topo (sem entrar numa
> subcategoria) é a classificação parcial do FR-011.

## Fila de pendentes

### `GET /itens/pendentes`

Lista os itens ainda sem categoria (`categoria_id IS NULL`), agrupados
por descrição normalizada (FR-009). Inclui um resumo agregado
(pendentes vs. total de itens) para dar visibilidade contínua a SC-002
(research.md #21), sem exigir endpoint separado. O gráfico de evolução
(burndown, research.md #22) **não** passa por este endpoint — é
renderizado do lado do servidor direto na página `/ver/pendentes`, mesmo
padrão de `resumo.html` (feature 005).

**Response**:
```json
200 OK
{
  "resumo": {"total_pendente": 42, "total_itens": 310},
  "grupos": [
    {
      "descricao_normalizada": "REFRIGERANTE COCA COLA 2L",
      "quantidade_itens": 3,
      "exemplo_item_id": 42
    }
  ]
}
```

### `GET /itens/pendentes?nota_id=<id>`

Mesma listagem, sem agrupamento — todos os itens pendentes de uma nota
específica (visão "por nota" do FR-009).

**Response**:
```json
200 OK
{
  "itens": [
    {"id": 42, "descricao": "REFRIG COCA 2L", "quantidade": 1, "valor_total_item": 850}
  ]
}
```

## Classificar / corrigir item

### `POST /itens/pendentes/classificar-grupo`

Atribui categoria a todos os itens pendentes de uma mesma descrição
normalizada em uma ação (US1 cenário 2, FR-010) — conveniência de UI
para a fila agrupada; a mesma operação de fundo de `PUT
/itens/<id>/categoria` abaixo, entrando pela descrição em vez de por um
item específico.

**Request**:
```json
{"descricao_normalizada": "REFRIGERANTE COCA COLA 2L", "categoria_id": 7}
```

**Response — sucesso**:
```json
200 OK
{"mensagem": "3 itens classificados.", "quantidade_itens_afetados": 3}
```

**Response — categoria não existe**:
```json
422 Unprocessable Entity
{"erro": "Categoria não encontrada."}
```

### `PUT /itens/<id>/categoria`

Atribui ou corrige a categoria de um único item (US1 cenários 1/4, US4
cenário 1). Se o item estava pendente, resolve automaticamente todos os
demais itens pendentes com a mesma descrição normalizada, sem precisar
do endpoint em lote acima (US1 cenário 2) — se o item já estava
classificado (correção, US4), afeta só ele. Corrigir a fonte é uma ação
**separada e explícita** (endpoint seguinte), nunca o comportamento
padrão desta rota.

**Request**:
```json
{"categoria_id": 12}
```

**Response — sucesso**: `200 OK`, mesmo formato de
`PUT /notas/<id>/categoria` já existente.
**Response — item ou categoria não encontrados**: `404`/`422`, mesmo
padrão já usado em `routes_categorias.py`.

### `GET /itens/<id>/impacto-correcao-fonte`

Prévia antes de "corrigir a fonte e reclassificar o passado" (FR-013,
SC-006) — chamada pelo cliente antes de habilitar o botão de confirmação.

**Response**:
```json
200 OK
{"descricao_normalizada": "REFRIG COCA 2L", "quantidade_itens_afetados": 4}
```

### `POST /itens/<id>/corrigir-fonte`

Aplica a correção em massa descrita no `impacto-correcao-fonte` acima
(data-model.md — `corrigir_fonte_e_reclassificar`). Ação explícita e
separada de `PUT /itens/<id>/categoria` (FR-013).

**Request**:
```json
{"categoria_id": 7}
```

**Response**:
```json
200 OK
{"mensagem": "4 itens reclassificados.", "quantidade_itens_afetados": 4}
```

## Taxonomia (extensão de `routes_categorias.py`)

### `POST /categorias` — corpo ganha `parent_id` opcional

**Request** (subcategoria):
```json
{"nome": "Mercearia seca", "parent_id": 3}
```

**Response — quase-duplicata detectada** (aviso, não bloqueio — FR-002):
```json
409 Conflict
{"aviso": "Já existe uma categoria parecida.", "sugestao": {"id": 3, "nome": "Mercearia Seca"}}
```
O cliente decide: usar a sugestão, ou reenviar com `"forcar": true` no
corpo para criar mesmo assim.

### `GET /categorias/<id>/impacto-exclusao`

Prévia antes de excluir (FR-004, FR-017, SC-006).

**Response — bloqueado por subcategorias**:
```json
200 OK
{"tem_subcategorias": true, "quantidade_itens": 0, "quantidade_cache": 0, "quantidade_regras": 0}
```

**Response — em uso, sem subcategorias**:
```json
200 OK
{"tem_subcategorias": false, "quantidade_itens": 18, "quantidade_cache": 5, "quantidade_regras": 1}
```

### `DELETE /categorias/<id>` — corpo passa a ser obrigatório quando em uso

**Request**:
```json
{"destino": "substituta", "categoria_substituta_id": 9}
```
ou
```json
{"destino": "pendente"}
```

**Response — bloqueado por subcategorias**:
```json
422 Unprocessable Entity
{"erro": "Exclua ou mova as subcategorias antes de excluir esta categoria."}
```

**Response — destino ausente quando há referências em uso**:
```json
422 Unprocessable Entity
{"erro": "Informe o destino dos itens/cache/regras afetados antes de excluir."}
```

**Response — sucesso**: `200 OK`, mesmo formato do `DELETE
/categorias/<id>` já existente.

## Endpoints existentes — sem mudança de contrato

`POST /notas`, `POST /notas/<id>/categoria`, `GET /categorias`, `PUT
/categorias/<id>` continuam exatamente como documentados nas features
001/003 — a classificação de item roda como uma etapa adicional interna
após a inserção de itens (research.md #8), sem mudar request/response
desses endpoints.
