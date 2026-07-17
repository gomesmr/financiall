# API Contract: Relatórios Mensais

## `GET /ver/resumo` (HTML)

Página de navegação do resumo mensal (redesign desta feature).

**Query string**:
- `mes` (opcional, `AAAA-MM`) — mês selecionado; default: mês corrente.
- `dimensao` (opcional, `item` | `estabelecimento`) — dimensão inicial exibida
  no carregamento da página; default: `item`. A troca para "os dois" é
  puramente client-side (dispara as duas chamadas a `/notas/resumo/categorias`).
- `nivel` (opcional, `1` | `2`) — nível de detalhe da dimensão "item"; default:
  `1`. Ignorado (mas aceito sem erro) quando a dimensão é `estabelecimento`,
  já que tipo de estabelecimento também tem 2 níveis (ex.: Saúde › Dentista) —
  `nivel` se aplica às duas dimensões igualmente.

Sempre 200 — mês sem nenhuma nota mostra estado vazio, nunca erro.

## `GET /notas/resumo/categorias` (JSON) — **contrato estendido**

Retorna o gasto agrupado por categoria para um mês, numa das duas dimensões.

**Query string**:
- `mes` (opcional, `AAAA-MM`) — default: mês corrente (mantido da feature 005).
- `dimensao` (opcional, `item` | `estabelecimento`) — **novo**; default: `item`
  (mudança de comportamento em relação à feature 005, que só tinha a dimensão
  hoje chamada "estabelecimento" — endpoint de uso interno da própria página,
  sem consumidor externo documentado).
- `nivel` (opcional, `1` | `2`) — **novo**; default: `1`.

**Resposta** (`200`): `{"mes": "AAAA-MM", "dimensao": "item"|"estabelecimento",
"nivel": 1|2, "categorias": [{"categoria_id": <id>|null, "nome": "<nome>"|"Sem
categoria", "total_gasto": <centavos>}, ...], "parcial": true}` — mesma
semântica `"parcial": true` já usada em `/notas/resumo/mes-atual`. Lista vazia
quando o mês não tem nenhuma nota com valor — nunca um erro.

Ordenado do maior para o menor `total_gasto`, mesmo comportamento da feature
005.

Valor inválido de `dimensao` ou `nivel` é ignorado silenciosamente, caindo no
default (`item`/`1`) — mesmo espírito de tolerância a parâmetro opcional já
usado no resto do projeto, evita erro 400 por um typo de query string numa
página de uso pessoal.

## `GET /ver/notas` (HTML) — **contrato estendido**

**Query string**:
- `mes` (opcional, `AAAA-MM`) — **novo nesta feature**; filtra a listagem para
  um único mês (usado pelo drill-down vindo do resumo, FR-006). Quando
  ausente, a página mostra todas as notas agrupadas visualmente por mês
  (FR-007), mês mais recente primeiro.
- `titular` (opcional, `marcelo` | `cristine`) — mantido da feature 004, sem
  mudança.
- `estabelecimento` (opcional, `<categoria_id>`) — **novo**; filtra a listagem
  pelo tipo de estabelecimento da nota (`nota_fiscal.categoria_id`), usado
  pelo drill-down a partir de uma fatia da visão por estabelecimento no
  resumo (FR-006, US3 cenário 2).

Todos os filtros são combináveis (AND) — ex.:
`/ver/notas?mes=2026-06&estabelecimento=12`.

## `GET /notas` (JSON) — sem alteração de contrato

Mantido exatamente como na feature 004 — esta feature não estende o filtro
`estabelecimento` para o endpoint JSON puro, apenas para a página HTML
(`/ver/notas`), já que nenhum consumidor externo/teste depende do filtro novo
neste endpoint.

## Sem alteração

- `GET /notas/resumo/mes-atual`
- `GET /notas/resumo/historico`

Ambos mantidos exatamente como na feature 005 — esta feature não altera a
forma de resposta nem o comportamento default desses dois endpoints.
