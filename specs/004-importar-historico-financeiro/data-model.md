# Data Model: Importar Histórico Financeiro

## Alteração em entidade existente: `nota_fiscal`

Nova coluna, adicionada via `ALTER TABLE` idempotente (research.md #1):

| Coluna | Tipo | Regras |
|---|---|---|
| `titular` | TEXT, nullable | Validado em Python: `"marcelo"`, `"cristine"` ou `"nao_identificado"`. `NULL` só ocorre em notas gravadas antes desta feature (outros canais) — tratada como "não identificado" na exibição. |

```sql
-- Em init_db(), apos garantir categoria_id:
ALTER TABLE nota_fiscal ADD COLUMN titular TEXT;
```

## Mapeamento: registro do histórico → `NotaFiscal` + `ItemNota`

| Campo no histórico | Campo no financiALL | Conversão |
|---|---|---|
| `chave` | `chave_acesso` | direto (usado também como chave de dedupe) |
| `cnpj` | `cnpj_emitente` | direto |
| `emitente` | `emitente_nome` | direto |
| `uf` | `uf` | direto |
| `data_emissao` | `data_emissao` | `DD/MM/YYYY` → `YYYY-MM-DD` (research.md #3) |
| — | `ano_mes_emissao` | derivado de `data_emissao` já convertida (`AAMM`) |
| `total` | `valor_total` | reais → centavos, `round(valor * 100)` (research.md #2) |
| `fonte` | `canal_origem` | `pdf` → `foto_pdf`; `qr`/ausente → `url_chave` (research.md #5) |
| `conta` | `titular` | `"marcelo"`/`"cristine"` direto; qualquer outro valor ou ausente → `"nao_identificado"` |
| — | `status` | sempre `"completa"` (FR-008) |
| — | `categoria_id` | sempre `NULL` (FR-009) |
| item: `codigo` | `codigo_item` | direto |
| item: `descricao` | `descricao` | direto |
| item: `qtd` | `quantidade` | direto (já é numérico) |
| item: `vl_unit` | `valor_unitario` | reais → centavos |
| item: `vl_liquido` (ou `vl_total` se ausente) | `valor_total_item` | reais → centavos (research.md #4) |
| item: `un`, `desconto` | — | não importados (sem coluna correspondente) |

Um registro sem `chave` reconhecível (ausente, vazio, ou que não seja uma
sequência de 44 dígitos) é **pulado** — não vira `NotaFiscal` (research.md
#7). Os demais campos ausentes degradam para `None`/valor padrão, nunca
abortam o registro individual.

## Operação de repositório nova: `inserir_nota_com_itens`

**Entrada**: `nota: NotaFiscal`, `itens: list[ItemNota]`, `db_path: str`.

**Comportamento**: numa única transação (`BEGIN`/`COMMIT` implícito do
`sqlite3`), insere a nota em `nota_fiscal` e, com o `id` gerado, insere
todos os itens em `item_nota`. Se qualquer etapa falhar, nada é
persistido (research.md #6).

**Saída**: `id` da nota inserida.

## Operação de serviço: `importar_historico(caminho_arquivo, db_path)`

1. Lê e faz `json.load` do arquivo — falha aqui (arquivo ausente, JSON
   inválido) aborta a execução inteira com erro claro (FR-007).
2. Para cada registro do histórico:
   a. Extrai a chave; se ausente/inválida, conta como "pulado" e segue
      para o próximo (research.md #7).
   b. Se `buscar_por_chave_acesso` já encontra a nota, conta como "já
      existia" e segue para o próximo (FR-002/idempotência).
   c. Mapeia para `NotaFiscal` + `list[ItemNota]` (tabela acima) e grava
      via `inserir_nota_com_itens`; conta como "importada".
3. Retorna um resumo: quantidade importada, quantidade já existente,
   quantidade pulada por registro malformado (FR-010).

Nenhum passo imprime chave, CNPJ, emitente ou valor — só contagens
(Princípio IV).

## Estados

`titular` não tem transição própria — é definido uma vez na criação da
nota (import) e nunca editado pela UI nesta feature (a spec não pede
edição de titular, só exibição e filtro).
