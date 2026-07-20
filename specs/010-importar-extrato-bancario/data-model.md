# Data Model: Importar Extrato Bancário

## Novas tabelas

```sql
CREATE TABLE IF NOT EXISTS estabelecimento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    documento TEXT,
    descricao_normalizada TEXT,
    nome_fantasia TEXT,
    tipo_categoria_id INTEGER REFERENCES categoria(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_estabelecimento_documento
    ON estabelecimento(documento) WHERE documento IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_estabelecimento_descricao
    ON estabelecimento(descricao_normalizada) WHERE documento IS NULL AND descricao_normalizada IS NOT NULL;

CREATE TABLE IF NOT EXISTS transacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT NOT NULL,
    data TEXT NOT NULL,
    descricao TEXT NOT NULL,
    descricao_normalizada TEXT,
    valor INTEGER NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('entrada', 'saida')),
    natureza TEXT CHECK (natureza IN ('gasto', 'renda', 'transferencia_interna', 'pagamento_fatura', 'estorno_credito')),
    metodo_classificacao_natureza TEXT CHECK (metodo_classificacao_natureza IN ('cache', 'regra', 'manual')),
    categoria_id INTEGER REFERENCES categoria(id),
    conta TEXT NOT NULL,
    titular TEXT,
    fonte TEXT,
    nota_fiscal_id INTEGER REFERENCES nota_fiscal(id),
    estabelecimento_id INTEGER REFERENCES estabelecimento(id),
    data_importacao TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_transacao_fingerprint ON transacao(fingerprint);

CREATE UNIQUE INDEX IF NOT EXISTS idx_transacao_nota_fiscal
    ON transacao(nota_fiscal_id) WHERE nota_fiscal_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS cache_descricao_natureza (
    descricao_normalizada TEXT PRIMARY KEY,
    natureza TEXT NOT NULL,
    categoria_id INTEGER REFERENCES categoria(id)
);

CREATE TABLE IF NOT EXISTS regra_natureza (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    padrao TEXT NOT NULL,
    natureza TEXT NOT NULL,
    categoria_id INTEGER REFERENCES categoria(id),
    prioridade INTEGER NOT NULL DEFAULT 0,
    ativa INTEGER NOT NULL DEFAULT 1
);
```

Como as demais tabelas do projeto (`db.py::SCHEMA`), estas entram via
`CREATE TABLE IF NOT EXISTS` executado em todo `init_db()` — seguro tanto
para banco novo quanto para o banco real já em produção/dev no Pi.

Não há coluna `titular` com `CHECK` (mesmo racional de `nota_fiscal.titular`,
validação em `TITULARES_VALIDOS` na camada de serviço). `estabelecimento_id`
e `categoria_id` ficam `NULL` até serem resolvidos — nunca bloqueiam a
importação (FR-002, FR-008, edge cases do spec.md).

## `Estabelecimento`

| Campo | Tipo | Regras |
|---|---|---|
| `documento` | TEXT, nullable | CNPJ (14 dígitos) ou CPF (11 dígitos), sem formatação. Único quando presente. |
| `descricao_normalizada` | TEXT, nullable | Fallback de identidade quando `documento` é nulo. Único apenas entre linhas sem documento. |
| `nome_fantasia` | TEXT, nullable | Definido pelo usuário na fila de gerenciamento (US5); `NULL` até ser resolvido. |
| `tipo_categoria_id` | FK `categoria`, nullable | Reaproveita a taxonomia de tipo de estabelecimento já usada por `nota_fiscal.categoria_id` (feature 003/009) — **não** a taxonomia de categoria de gasto por item (feature 008); são o mesmo namespace de tabela, mas atribuições distintas, mesmo padrão que já existe hoje entre `nota_fiscal.categoria_id` e `item_nota.categoria_id`. |

## `Transacao`

| Campo | Tipo | Regras |
|---|---|---|
| `fingerprint` | TEXT, UNIQUE | `sha1(data|descricao_normalizada|abs(valor)|conta_canonica)[:16]` — research.md #1/#2. Chave de dedupe entre migração histórica e parser recorrente. |
| `data` | TEXT (`YYYY-MM-DD`) | |
| `descricao` | TEXT | Descrição crua do extrato, nunca alterada. |
| `descricao_normalizada` | TEXT, nullable | Via `src/services/normalizacao.py` (já existente), usada por cache/regra de natureza e pela fila de pendentes. |
| `valor` | INTEGER (centavos) | Sempre positivo — `tipo` indica a direção. |
| `tipo` | TEXT | `entrada` \| `saida` — cru do extrato (FR-001), nunca inferido. |
| `natureza` | TEXT, nullable | `NULL` = pendente de revisão (FR-002). Um dos 5 valores fechados quando resolvida. |
| `metodo_classificacao_natureza` | TEXT, nullable | `cache` \| `regra` \| `manual` — auditoria de como `natureza` foi decidida. |
| `categoria_id` | FK `categoria`, nullable | Só populado quando `natureza = gasto` (FR-003); reaproveita `TAXONOMIA_RESERVADA_EXTRATO` já semeada pela feature 008 (research.md #4). |
| `conta` | TEXT | Já canonicalizada (research.md #2) antes de gravar. |
| `titular` | TEXT, nullable | `TITULARES_VALIDOS` (mesmo enum de `nota_fiscal`, feature 004). |
| `fonte` | TEXT, nullable | Nome do arquivo de origem (auditoria). |
| `nota_fiscal_id` | FK `nota_fiscal`, nullable, único quando presente | Reconciliação (research.md #7). |
| `estabelecimento_id` | FK `estabelecimento`, nullable | Resolução em cascata (research.md #9). |
| `data_importacao` | TEXT (ISO) | |

## `cache_descricao_natureza` / `regra_natureza`

Espelham exatamente `cache_descricao_categoria`/`regra_categoria` (feature
008), só que classificando `natureza` (+ `categoria_id` opcional, quando a
natureza resolvida é `gasto`) em vez de só `categoria_id`. Mesma cascata:
cache (correspondência exata por descrição normalizada) → regra ativa mais
específica (por prioridade) → sem correspondência (pendente).

## Alteração em entidade existente: `nota_fiscal`

Nenhuma coluna nova. Ganha, por associação reversa, uma referência opcional
vinda de `transacao.nota_fiscal_id` — a "reconciliação" é modelada inteira
do lado da transação (índice único garante que uma nota nunca reconcilia
com mais de uma transação).

## Operações de repositório novas (`src/storage/db.py`)

- **`inserir_transacao(transacao, db_path)`**: insere; se o `fingerprint`
  já existe (`sqlite3.IntegrityError`), retorna o `id` já existente em vez
  de levantar erro — mesma semântica de idempotência silenciosa que
  `importar_historico` já usa para nota fiscal (FR-009).
- **`buscar_transacao_por_fingerprint(fingerprint, db_path)`**.
- **`classificar_natureza_transacao(transacao_id, natureza, categoria_id, metodo, descricao_normalizada, db_path)`**:
  grava a transação e faz upsert em `cache_descricao_natureza` — mesmo
  padrão de `classificar_item_automaticamente` (feature 008), sem tabela de
  histórico dedicada (não há requisito de auditoria de mudança de natureza
  na spec, ao contrário do item de nota — FR-007 só exige que a correção
  manual prevaleça, o que o upsert de cache já garante).
- **`listar_transacoes_pendentes_natureza(db_path)`**: agrupado por
  `descricao_normalizada`, mesmo formato de `listar_itens_pendentes`
  (US4, FR-006).
- **`reconciliar_transacao(transacao_id, db_path)`**: aplica research.md #7;
  retorna `"reconciliada"` (link único encontrado e aplicado),
  `"ambigua"` (mais de um candidato — nenhum link aplicado), ou `"sem_candidato"`.
- **`listar_reconciliacoes_pendentes(db_path)`**: transações com múltiplos
  candidatos de nota — fila de revisão manual (FR-013).
- **`desvincular_reconciliacao(transacao_id, db_path)`**: zera
  `transacao.nota_fiscal_id` (FR-014, "desfazer").
- **`resolver_estabelecimento(transacao_id, db_path)`**: aplica a cascata
  de research.md #9 no momento em que a transação é classificada como
  `gasto` ou reconciliada (o que muda `estabelecimento_id`).
- **`listar_estabelecimentos_pendentes(db_path)`**: agrupado por
  `documento` (quando presente) ou `descricao_normalizada` (fallback) —
  fila de gerenciamento (US5, FR-018).
- **`atribuir_estabelecimento(estabelecimento_id, nome_fantasia, tipo_categoria_id, db_path)`**.

## Operações de serviço novas

- **`src/services/classificacao_natureza.py::classificar_natureza(descricao, db_path)`**:
  cascata cache → regra → `(None, None, None)`, espelhando
  `classificacao_itens.classificar_item` (research.md #6).
- **`src/services/importar_historico_extrato.py::importar_historico_extrato(caminho_registro_json, db_path)`**:
  lê `registro.json` (formato legado), mapeia cada registro para
  `Transacao` (conta canonicalizada, `tipo` a partir do sinal de `valor`,
  `natureza`/`categoria_id` via cascata — que já resolve a maioria pelas
  regras-semente migradas, research.md #5), grava via `inserir_transacao`
  (idempotente por fingerprint) e tenta `reconciliar_transacao` para cada
  uma classificada como `gasto`. Retorna um resumo (importadas, já
  existentes, puladas) — mesmo formato de `importar_historico` (feature
  004).
- **`src/services/importar_extrato_itau_cartao.py::parsear(caminho_arquivo)`**:
  parser do formato Itaú cartão XLS (research.md #10/#11 — via `xlrd`),
  retorna `list[Transacao]` não persistidas; a persistência (fingerprint,
  classificação, reconciliação) é a mesma função reaproveitada da migração
  histórica, para não duplicar a lógica de idempotência/classificação entre
  os dois pipelines.

## Extensão em `src/services/resumo.py`

`gasto_mes_corrente`, `historico_meses_anteriores` e
`gasto_por_categoria_item` passam a somar, para cada mês: `SUM(transacao.valor)
WHERE natureza = 'gasto'` **mais** `SUM(nota_fiscal.valor_total) WHERE
nota_fiscal.id NOT IN (SELECT nota_fiscal_id FROM transacao WHERE
nota_fiscal_id IS NOT NULL)` — calculado a cada consulta, nunca persistido
(research.md #8). `gasto_por_categoria_item` usa os itens da nota quando a
transação está reconciliada e a nota tem item classificado; senão usa
`transacao.categoria_id`; nota não reconciliada segue exatamente como hoje.
`gasto_por_estabelecimento` passa a incluir transações sem nota, agrupadas
por `estabelecimento.tipo_categoria_id` (FR-020).

## Estados

- `Transacao.natureza`: `NULL` (pendente) → um dos 5 valores, por cache,
  regra ou atribuição manual (FR-007) — nunca volta a `NULL` depois de
  resolvida.
- `Transacao.nota_fiscal_id`: `NULL` → preenchido (reconciliação automática
  ou manual) → pode voltar a `NULL` (desfazer, FR-014).
- `Estabelecimento.nome_fantasia`/`tipo_categoria_id`: `NULL` até
  atribuição manual (US5) — não há classificação automática de
  nome_fantasia (é sempre um dado que só o usuário sabe).
