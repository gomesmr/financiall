# Data Model: Log de importações

## Entidade: LogImportacao

Representa uma única execução de `processar_transacoes()` já concluída
(uma linha por chamada, independente de ter trazido transação nova ou
não). Não se relaciona a `Transacao` individual — é um registro agregado
por execução (ver research.md #4).

| Campo                          | Tipo   | Obrigatório | Descrição |
|---------------------------------|--------|:-----------:|-----------|
| `id`                             | int    | sim (auto)  | Chave primária. |
| `data_hora`                      | texto (ISO datetime) | sim | Momento em que a importação foi executada (`datetime.now().isoformat()`). |
| `fonte`                          | texto  | não         | Nome do arquivo ou dump importado (derivado do primeiro registro processado — research.md #2); `NULL` quando a lista de registros vier vazia. |
| `periodo_inicio`                 | texto (ISO `AAAA-MM-DD`) | não | Menor data entre os registros processados nesta execução (research.md #3); `NULL` quando nenhum registro tiver data válida. |
| `periodo_fim`                    | texto (ISO `AAAA-MM-DD`) | não | Maior data entre os registros processados nesta execução; `NULL` nas mesmas condições de `periodo_inicio`. |
| `importadas`                     | int    | sim         | `resumo.importadas`. |
| `ja_existentes`                  | int    | sim         | `resumo.ja_existentes`. |
| `puladas`                        | int    | sim         | `resumo.puladas`. |
| `classificadas_automaticamente`  | int    | sim         | `resumo.classificadas_automaticamente`. |
| `pendentes_natureza`             | int    | sim         | `resumo.pendentes_natureza`. |
| `reconciliadas`                  | int    | sim         | `resumo.reconciliadas`. |
| `ambiguas`                       | int    | sim         | `resumo.ambiguas`. |

### Regras de validação / integridade

- Todo campo de contagem (`importadas`, `ja_existentes`, ...) é `>= 0` —
  já garantido por construção, pois vem direto de `ImportarExtratoResumo`
  (nunca calculado de novo a partir de dado externo não confiável).
- `periodo_inicio`/`periodo_fim` são ambos `NULL` ou ambos preenchidos —
  nunca um preenchido e o outro não (research.md #3: calculados juntos, a
  partir do mesmo conjunto de datas).
- Nenhum índice único: duas execuções da mesma fonte em datas próximas
  geram duas linhas distintas, de propósito (edge case da spec — o
  histórico é de execuções, não um resumo por fonte).

### Ordenação padrão de listagem

`ORDER BY data_hora DESC, id DESC` — execução mais recente primeiro
(FR-003); `id DESC` como desempate para duas execuções com o mesmo
timestamp (mesma resolução de segundo, no caso de scripts que processam
vários arquivos em sequência rápida).

## Sem alteração em entidades existentes

`Transacao`, `ImportarExtratoResumo` e todos os parsers permanecem
inalterados — esta feature só acrescenta uma tabela nova e uma leitura a
mais dentro de `processar_transacoes()`, sem mudar nenhum contrato
existente (Assumptions da spec).
