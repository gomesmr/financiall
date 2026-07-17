# Data Model: Categorização de Itens de Nota Fiscal

## Alteração em entidade existente: `categoria` (feature 003)

Nova coluna, via `ALTER TABLE` idempotente (research.md #3):

| Coluna | Tipo | Regras |
|---|---|---|
| `parent_id` | INTEGER, nullable | `REFERENCES categoria(id)`; `NULL` = categoria de topo; preenchido = subcategoria. Validado na camada de serviço: uma categoria com `parent_id` preenchido MUST NOT ser, por sua vez, `parent_id` de outra (só 2 níveis). |

```sql
-- Em init_db(), apos o CREATE TABLE/ALTER de categoria ja existente:
ALTER TABLE categoria ADD COLUMN parent_id INTEGER REFERENCES categoria(id);
```

Categorias já existentes hoje (todas sem `parent_id`) permanecem
automaticamente como categorias de topo — nenhuma migração de dado.

**Índice único escopado por nível** (research.md #19): o índice único
global de `categoria.nome_normalizado` (feature 003) é substituído por
dois índices parciais — nome único entre categorias de topo, nome único
só dentro do mesmo `parent_id` para subcategorias. Mesmo padrão de índice
parcial já usado no projeto (`idx_nota_fiscal_chave_acesso`).

```sql
-- Em init_db(), no lugar do indice unico global antigo:
DROP INDEX IF EXISTS idx_categoria_nome_normalizado;

CREATE UNIQUE INDEX IF NOT EXISTS idx_categoria_topo_nome_normalizado
    ON categoria(nome_normalizado) WHERE parent_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_categoria_subcategoria_nome_normalizado
    ON categoria(parent_id, nome_normalizado) WHERE parent_id IS NOT NULL;
```

Seguro para o dado de produção existente: hoje toda categoria tem
`parent_id IS NULL`, então a troca é comportamentalmente equivalente ao
índice antigo até a primeira subcategoria ser criada. A camada de
serviço (`criar_categoria`/`editar_categoria`) continua capturando
`sqlite3.IntegrityError` do jeito que já captura hoje — nenhuma mudança
de código além do schema.

## Alteração em entidade existente: `item_nota` (feature 001)

Três colunas novas, via `ALTER TABLE` idempotente:

| Coluna | Tipo | Regras |
|---|---|---|
| `categoria_id` | INTEGER, nullable | `REFERENCES categoria(id)`; `NULL` = pendente de revisão (estado padrão). Pode apontar para uma categoria de topo (classificação parcial, subcategoria pendente) ou uma subcategoria (classificação completa). |
| `descricao_normalizada` | TEXT, nullable | Calculada uma vez no momento da classificação (research.md #1/#2); `NULL` enquanto o item nunca passou pela cascata. |
| `metodo_classificacao` | TEXT, nullable, `CHECK (metodo_classificacao IN ('cache','regra','manual'))` | Método que originou a classificação atual do item — usado por "corrigir a fonte" (FR-013) e pela auditoria. |

```sql
ALTER TABLE item_nota ADD COLUMN categoria_id INTEGER REFERENCES categoria(id);
ALTER TABLE item_nota ADD COLUMN descricao_normalizada TEXT;
ALTER TABLE item_nota ADD COLUMN metodo_classificacao TEXT
    CHECK (metodo_classificacao IN ('cache', 'regra', 'manual'));
```

Nenhuma constraint `NOT NULL` nem `ON DELETE` na FK de `categoria_id` —
mesma decisão já tomada para `nota_fiscal.categoria_id` (feature 003):
integridade referencial na exclusão é garantida por SQL explícito em
transação, não pela FK.

## Entidade nova: `cache_descricao_categoria`

| Coluna | Tipo | Regras |
|---|---|---|
| `descricao_normalizada` | TEXT PRIMARY KEY | Chave de reaproveitamento — uma linha por descrição normalizada única já vista. |
| `categoria_id` | INTEGER NOT NULL | `REFERENCES categoria(id)`. Sempre a classificação mais recente confirmada para essa descrição (upsert, research.md #10). |

```sql
CREATE TABLE IF NOT EXISTS cache_descricao_categoria (
    descricao_normalizada TEXT PRIMARY KEY,
    categoria_id INTEGER NOT NULL REFERENCES categoria(id)
);
```

## Entidade nova: `regra_categoria`

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | — |
| `padrao` | TEXT NOT NULL | Token casado com fronteira de palavra sobre a descrição normalizada (research.md #5). |
| `categoria_id` | INTEGER NOT NULL | `REFERENCES categoria(id)`. |
| `prioridade` | INTEGER NOT NULL DEFAULT 0 | Maior vence em caso de duas regras casarem (research.md #6). |
| `ativa` | INTEGER NOT NULL DEFAULT 1 | `0` desativa a regra sem excluí-la (research.md #7 — equivale a "aprovada" do spec). |

```sql
CREATE TABLE IF NOT EXISTS regra_categoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    padrao TEXT NOT NULL,
    categoria_id INTEGER NOT NULL REFERENCES categoria(id),
    prioridade INTEGER NOT NULL DEFAULT 0,
    ativa INTEGER NOT NULL DEFAULT 1
);
```

Carregada por fixture/script de seed (Tarefa 1 — validar taxonomia e
regras-semente), não por uma tela de CRUD nesta versão.

## Entidade nova: `historico_classificacao_item`

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | — |
| `item_nota_id` | INTEGER NOT NULL | `REFERENCES item_nota(id)`. |
| `categoria_id_anterior` | INTEGER, nullable | `NULL` se o item estava pendente antes desta mudança. |
| `categoria_id_nova` | INTEGER, nullable | `NULL` se a mudança removeu a categoria (voltou a pendente — ex.: exclusão de categoria com destino "pendente"). |
| `metodo` | TEXT NOT NULL | Método que gerou esta entrada (`cache`, `regra`, `manual`). |
| `timestamp` | TEXT NOT NULL | ISO 8601, mesmo padrão de `data_importacao`/`data_envio` já usado no projeto. |

```sql
CREATE TABLE IF NOT EXISTS historico_classificacao_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_nota_id INTEGER NOT NULL REFERENCES item_nota(id),
    categoria_id_anterior INTEGER,
    categoria_id_nova INTEGER,
    metodo TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
```

Append-only — nunca editada nem excluída (trilha de auditoria, FR-014).

## Operações de repositório (`src/storage/db.py`)

### `classificar_item_automaticamente(item_id, categoria_id, metodo, db_path) -> None`

Usada pela cascata (research.md #8). `UPDATE item_nota SET categoria_id
= ?, metodo_classificacao = ? WHERE id = ?` + upsert em
`cache_descricao_categoria` (research.md #10) + `INSERT` em
`historico_classificacao_item` (`categoria_id_anterior = NULL`, já que só
roda sobre itens pendentes) — uma transação.

### `atribuir_categoria_manual(item_id, categoria_id, db_path) -> bool | None`

Usada pela fila de pendentes (US1) e pela correção simples (US4 cenário
1). `None` se o item não existe; `False` se `categoria_id` informado não
existe; `True` em sucesso. Em sucesso: grava `item_nota.categoria_id`
(`metodo_classificacao = 'manual'`), upsert do cache, `INSERT` no
histórico com a categoria anterior real do item (pode ser `NULL`, se
estava pendente) — **e, se o item de origem estava pendente
(`categoria_id_anterior IS NULL`), aplica a mesma atribuição a todos os
demais `item_nota` com a mesma `descricao_normalizada` e `categoria_id
IS NULL`** (US1 cenário 2), cada um com sua própria linha de histórico.
Correção de item já classificado (US4) nunca dispara esse efeito
colateral — só a resolução de um pendente dispara.

### `classificar_grupo_pendente(descricao_normalizada, categoria_id, db_path) -> int`

Mesma operação de `atribuir_categoria_manual` acima, só que entrando
pela descrição em vez de por um item específico — conveniência de UI
para quando o usuário já está olhando o grupo agrupado da fila (US1
cenário 1), não um mecanismo de resolução de pendentes separado. Retorna
a quantidade de itens afetados.

### `calcular_impacto_correcao_fonte(item_id, db_path) -> dict | None`

Usada pela prévia de "corrigir a fonte" (FR-013, SC-006). Retorna
`None` se o item não existe; senão `{"descricao_normalizada": ...,
"categoria_id_atual": ..., "quantidade_itens_afetados": N}` — a contagem
de `item_nota` com a mesma `descricao_normalizada` e a mesma
`categoria_id` atual do item.

### `corrigir_fonte_e_reclassificar(item_id, nova_categoria_id, db_path) -> int | None`

Aplica a correção descrita em research.md #11: upsert do cache para a
`descricao_normalizada` do item, `UPDATE` em lote de todos os `item_nota`
com a mesma `descricao_normalizada` e a categoria antiga para a nova, e
uma linha de histórico por item afetado. Retorna a quantidade de itens
atualizados, ou `None` se o item de origem não existe.

### `calcular_impacto_exclusao(categoria_id, db_path) -> dict | None`

Usada pela prévia de exclusão (FR-004, FR-017). Retorna `None` se a
categoria não existe; senão `{"tem_subcategorias": bool,
"quantidade_itens": N, "quantidade_cache": N, "quantidade_regras": N}`.
Se `tem_subcategorias` for `True`, a exclusão MUST ser recusada antes de
qualquer outro cálculo (FR-017).

### `excluir_categoria_com_destino(categoria_id, destino, categoria_substituta_id, db_path) -> bool | None`

`destino` é `"substituta"` ou `"pendente"`. Transação única: se
`"substituta"`, `UPDATE item_nota/cache_descricao_categoria/regra_categoria
SET categoria_id = <substituta> WHERE categoria_id = <categoria_id>`; se
`"pendente"`, os itens voltam a `categoria_id = NULL` (e
`metodo_classificacao = NULL`), as entradas de cache e regra que
apontavam para a categoria excluída são removidas (`DELETE`, não fazem
sentido apontando para `NULL`). Em seguida `DELETE FROM categoria WHERE
id = ?`. Retorna `None` se a categoria não existe; `False` se
`tem_subcategorias` (bloqueado, FR-017) ou se `categoria_substituta_id`
for inválido/de nível diferente; `True` em sucesso.

### `listar_itens_pendentes(nota_fiscal_id=None, db_path) -> list[...]`

Usada pela fila de revisão (FR-009). Sem `nota_fiscal_id`: agrupado por
`descricao_normalizada` (`GROUP BY`, com contagem e uma nota de exemplo
por grupo). Com `nota_fiscal_id`: todos os itens pendentes daquela nota,
sem agrupamento — a visão "por nota" do FR-009.

## Estados

- **Item de nota**: `pendente` (`categoria_id IS NULL`) →
  `classificado` (`categoria_id` preenchido, aponta para categoria de
  topo — classificação parcial — ou subcategoria — completa). Transição
  de volta a `pendente` só acontece como efeito de excluir a categoria
  que o item usava com destino `"pendente"` (FR-004). Nunca há um terceiro
  estado — SC-001.
- **Categoria/Subcategoria**: sem estados — existe ou não existe
  (exclusão definitiva, sem soft-delete, mesma decisão da feature 002/003
  — mas agora com prévia de impacto e destino explícito obrigatórios
  quando em uso, e bloqueio enquanto tiver subcategorias).
- **Regra**: `ativa` ou inativa (`ativa = 0`) — nunca excluída via UI
  nesta versão (gestão de regra é seed/fixture, research.md #7).
