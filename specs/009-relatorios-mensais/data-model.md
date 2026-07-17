# Data Model: Relatórios Mensais

Nenhuma tabela ou coluna nova é criada por esta feature — `categoria.parent_id`
(feature 008) e `nota_fiscal.categoria_id` (feature 003) já existem e cobrem
os dois eixos de classificação. Esta feature apenas recombina dados já
existentes em novas leituras/agregações e adiciona linhas-semente à tabela
`categoria` já existente (research.md #7).

## Entidades existentes reaproveitadas

### `categoria` (sem alteração de schema)

Mesmo mecanismo de dois níveis já usado pela feature 008
(`id`, `nome`, `parent_id`). Passa a ser reconhecida explicitamente como
servindo **dois eixos independentes**:

- **Categoria do item** — via `item_nota.categoria_id` (feature 008): o que
  foi comprado (ex.: Alimentação › Biscoitos).
- **Tipo de estabelecimento** — via `nota_fiscal.categoria_id` (feature 003,
  reinterpretado nesta feature): onde a compra foi feita (ex.: Supermercado,
  Saúde › Dentista).

Os dois eixos podem compartilhar a mesma tabela sem colisão, pois cada um é
referenciado por uma coluna distinta em tabelas distintas
(`item_nota.categoria_id` vs. `nota_fiscal.categoria_id`) — nada exige que os
nomes de categoria de um eixo sejam distintos dos do outro eixo.

**Novas linhas-semente** (idempotentes, via
`src/scripts/seed_taxonomia_estabelecimento.py`): Supermercado, Mercearia,
Restaurante, Bar, Farmácia, Pet Shop, Saúde (com subcategorias Dentista e
Plano de Saúde) — só inseridas se ainda não existirem (mesma checagem de
nome_normalizado já usada por `criar_categoria`).

### `nota_fiscal.categoria_id` (sem alteração de schema, reinterpretação)

Continua sendo a mesma coluna/mecanismo (`atribuir_categoria_a_nota`, feature
003), agora documentada como representando o **tipo de estabelecimento**
da compra, não mais uma "categoria de gasto" genérica.

### `item_nota.categoria_id` (sem alteração, feature 008)

Continua representando a categoria do item comprado, sem mudança.

## Modelos de leitura (agregados calculados sob demanda, não persistidos)

### `ResumoMes` (existente, `src/services/resumo.py`, sem alteração de forma)

```python
mes: str            # AAAA-MM
total_gasto: int | None   # centavos, soma de nota_fiscal.valor_total
quantidade_notas: int
```

### `GastoCategoria` (existente, sem alteração de forma — reaproveitado pelas
duas dimensões)

```python
categoria_id: int | None  # None = "Sem categoria" / "Sem tipo de estabelecimento"
nome: str
total_gasto: int  # centavos
```

Usado tanto pela agregação por categoria do item quanto pela agregação por
tipo de estabelecimento — a dimensão é determinada por qual função de serviço
produziu a lista, não por um campo extra na dataclass.

## Regra de negócio: fallback item → nota (FR-001/002/003)

Para uma nota do mês selecionado:

1. Se **algum** item da nota tem `categoria_id` preenchido → a nota entra em
   "modo item": cada item classificado soma na sua própria categoria (nível 1
   resolve para a categoria-pai; nível 2 usa a categoria tal como está); itens
   da mesma nota ainda sem categoria somam em "Sem categoria" (nunca caem na
   categoria da nota).
2. Se **nenhum** item da nota tem `categoria_id` preenchido (incluindo notas
   sem nenhum item extraído) → o valor total da nota (`nota_fiscal.valor_total`)
   soma inteiro na categoria da própria nota (`nota_fiscal.categoria_id`), ou em
   "Sem categoria" se a nota também não tiver categoria própria.
3. Itens com `valor_total_item` nulo nunca contribuem para nenhuma soma (mesma
   regra já usada para `nota_fiscal.valor_total` nulo).

## Regra de negócio: resolução de nível (FR-009)

Dado um `categoria_id` e um dicionário `{id: Categoria}` pré-carregado:

- **Nível 2**: usa a própria categoria (`categoria_id`, `nome`).
- **Nível 1**: se `categoria.parent_id` é `None`, usa a própria categoria;
  senão, usa a categoria apontada por `parent_id` (o topo).

## Regra de negócio: navegação por mês (FR-004/005)

`meses_navegaveis` = união ordenada (desc) de `{mes_atual()}` com os meses
retornados por `listar_meses_com_notas()` (mesma query de
`_query_resumo_por_mes`, já ordenada). Mês anterior/seguinte = vizinho na
lista pelo índice do mês selecionado — nunca aritmética de calendário
(research.md #4).

## Relação com a listagem de notas (FR-006/007/008)

`storage_db.listar_notas` ganha um parâmetro opcional `categoria_id` (filtro
por tipo de estabelecimento), somando-se aos já existentes `mes` e `titular`.
O agrupamento visual por mês na página `/ver/notas` é feito em Python sobre o
resultado já ordenado (`itertools.groupby`), sem mudança na query em si além
do novo filtro opcional.
