# Data Model: Excluir Nota Fiscal

Não há tabela nem campo novo — esta feature opera sobre as entidades já
definidas na feature 001 (`nota_fiscal`, `item_nota`, `envio_ocr`, ver
`specs/001-importar-nfce/data-model.md` e `src/storage/db.py`). O que
muda é o comportamento: uma nova operação de exclusão em cascata sobre
essas três tabelas.

## Entidades afetadas

### `nota_fiscal`

- **Operação nova**: `DELETE FROM nota_fiscal WHERE id = ?`.
- **Efeito colateral estrutural**: os índices únicos parciais
  `idx_nota_fiscal_chave_acesso` (`WHERE chave_acesso IS NOT NULL`) e
  `idx_nota_fiscal_hash_conteudo` (`WHERE hash_conteudo IS NOT NULL`) só
  indexam linhas existentes — ao excluir a linha, a chave/hash deixa de
  estar "ocupada" automaticamente. Isso é o que garante FR-004/US2
  (reimportação liberada) sem lógica adicional.

### `item_nota`

- **Operação nova**: `DELETE FROM item_nota WHERE nota_fiscal_id = ?`,
  executado **antes** do delete de `nota_fiscal` na mesma transação (FK
  `nota_fiscal_id` referencia `nota_fiscal(id)`).
- Nenhum item pode existir sem a nota correspondente após a operação —
  invariante de cascata (FR-003).

### `envio_ocr`

- **Operação nova**: `DELETE FROM envio_ocr WHERE nota_fiscal_id = ?`,
  executado na mesma transação. Pode remover zero, um ou múltiplos
  registros (edge case: uploads repetidos que resolveram para a mesma
  nota — ver research.md #3).
- **Campo relevante**: `caminho_arquivo` de cada linha selecionada é lido
  **antes** do delete e retornado ao chamador, para a remoção do arquivo
  físico em disco (fora da transação SQL — ver research.md #2).
- Envios com `nota_fiscal_id IS NULL` (ainda pendentes/processando, sem
  nota resultante) não são afetados por esta operação — não têm nota para
  disparar a exclusão.

## Operação: `excluir_nota`

**Entrada**: `nota_id: int`, `db_path: str`.

**Saída**: `list[str] | None` — lista dos `caminho_arquivo` a remover do
disco (pode ser vazia, se não havia envio associado), ou `None` se a nota
não existia (permite à camada de serviço/rota responder 404).

**Transação** (tudo dentro de um único `BEGIN`/`COMMIT`):

1. Verifica se `nota_fiscal` com o `id` existe; se não, `ROLLBACK`/aborta e
   retorna `None`.
2. `SELECT caminho_arquivo FROM envio_ocr WHERE nota_fiscal_id = ?` —
   guarda a lista de caminhos.
3. `DELETE FROM envio_ocr WHERE nota_fiscal_id = ?`.
4. `DELETE FROM item_nota WHERE nota_fiscal_id = ?`.
5. `DELETE FROM nota_fiscal WHERE id = ?`.
6. `COMMIT`.
7. Retorna a lista de caminhos coletada no passo 2.

Nenhuma etapa grava nada fora dessas três tabelas; a remoção de arquivo em
disco é responsabilidade do chamador (`services/exclusao.py`), não desta
função.

## Estados

Não há novo estado para `nota_fiscal`/`item_nota`/`envio_ocr` (sem
soft-delete, ver Assumptions da spec) — a transição é sempre "existe" →
"não existe". Não há campo de status "excluída" a introduzir.
