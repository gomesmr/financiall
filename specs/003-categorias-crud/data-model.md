# Data Model: CRUD de Categorias

## Entidade nova: `categoria`

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | — |
| `nome` | TEXT NOT NULL | valor exibido ao usuário, exatamente como digitado (após `strip()`) |
| `nome_normalizado` | TEXT NOT NULL, **UNIQUE** | `nome.strip().casefold()` — calculado em Python, nunca exposto na UI (research.md #2) |

```sql
CREATE TABLE IF NOT EXISTS categoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    nome_normalizado TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_categoria_nome_normalizado
    ON categoria(nome_normalizado);
```

**Validação (FR-001, FR-002, FR-010)**: nome vazio ou só espaços é
recusado antes de qualquer escrita (camada de serviço). Nome cujo
`nome_normalizado` já existe é recusado com base no índice único —
capturado como erro de aplicação (`IntegrityError`) e traduzido para
mensagem em português.

## Alteração em entidade existente: `nota_fiscal`

Nova coluna, adicionada via `ALTER TABLE` idempotente (research.md #1),
não via recriação da tabela:

| Coluna | Tipo | Regras |
|---|---|---|
| `categoria_id` | INTEGER, nullable | `REFERENCES categoria(id)`; `NULL` = "sem categoria" (estado padrão e válido) |

```sql
-- Em init_db(), apos o CREATE TABLE/ALTER de nota_fiscal existente:
-- 1. PRAGMA table_info(nota_fiscal) -> verifica se 'categoria_id' ja existe
-- 2. Se ausente:
ALTER TABLE nota_fiscal ADD COLUMN categoria_id INTEGER REFERENCES categoria(id);
```

Nenhuma constraint `NOT NULL` nem `ON DELETE` declarada na FK — a
integridade referencial na exclusão é garantida por SQL explícito em
transação (ver Operação `excluir_categoria` abaixo e research.md #3), não
pela FK.

## Operações de repositório (`src/storage/db.py`)

### `criar_categoria(nome, db_path) -> int | None`

Calcula `nome_normalizado`. Insere `categoria`. Retorna o `id` novo, ou
`None` se `nome` (após `strip()`) for vazio ou já existir (índice único
violado) — o chamador (camada de serviço) distingue os dois casos para dar
a mensagem certa (FR-002 vs FR-010).

### `listar_categorias(db_path) -> list[Categoria]`

Todas as categorias, ordenadas por `nome`.

### `buscar_categoria_por_id(categoria_id, db_path) -> Categoria | None`

### `editar_categoria(categoria_id, novo_nome, db_path) -> bool | None`

Mesma validação de `criar_categoria`. Retorna `None` se `categoria_id` não
existe, `False` se o novo nome é inválido/duplicado, `True` em sucesso.

### `excluir_categoria(categoria_id, db_path) -> bool`

Transação única (research.md #3): `UPDATE nota_fiscal SET categoria_id =
NULL WHERE categoria_id = ?` seguido de `DELETE FROM categoria WHERE id =
?`. Retorna `False` se a categoria não existia (nenhuma linha afetada no
delete), `True` em sucesso — idempotente na forma (não lança exceção se
já não existir).

### `atribuir_categoria_a_nota(nota_id, categoria_id, db_path) -> bool | None`

`UPDATE nota_fiscal SET categoria_id = ? WHERE id = ?`. `categoria_id`
pode ser `None` (remover atribuição, US2 cenário 3). Retorna `None` se a
nota não existe; `False` se `categoria_id` foi informado mas não existe
como categoria; `True` em sucesso.

## Estados

- **Categoria**: sem estados — existe ou não existe (exclusão é
  definitiva, sem soft-delete, mesma decisão da feature 002).
- **Nota Fiscal**: ganha um novo atributo derivado do relacionamento —
  "com categoria" (`categoria_id` preenchido, aponta para uma categoria
  existente) ou "sem categoria" (`categoria_id IS NULL`). Transição para
  "sem categoria" acontece tanto por ação direta do usuário (US2 cenário
  3) quanto como efeito colateral de excluir a categoria que a nota usava
  (US5 cenário 2) — os dois casos resultam no mesmo estado, sem
  distinção visual entre eles.
