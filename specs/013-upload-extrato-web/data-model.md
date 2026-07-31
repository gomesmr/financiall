# Data Model: Upload de extrato/fatura bancária pela web

Nenhuma migração de schema — reaproveita `Transacao`/tabela `transacao`
sem nenhum atributo novo. Esta feature adiciona só uma camada de
detecção de formato + rota HTTP por cima do pipeline já existente.

## Formato detectado (conceito novo, não persistido)

Não é uma entidade de banco — é o resultado interno da função de
detecção, usado só para decidir qual `parsear()` chamar:

| Valor | Extensão | Parser despachado |
|---|---|---|
| `itau_fatura_cartao` | `.xls` | `src.services.importar_extrato_itau_cartao.parsear` |
| `itau_extrato_cc` | `.xls` | `src.services.importar_extrato_itau_cc.parsear` |
| `itau_fatura_cartao` (formato novo) | `.xlsx` | `src.services.importar_extrato_itau_cartao.parsear` (já despacha `.xls` vs `.xlsx` internamente) |
| `bb_extrato_cc` | `.xlsx` | `src.services.importar_extrato_bb.parsear` |
| `mercado_pago_fatura` | `.pdf` | `src.services.importar_fatura_mercado_pago.parsear` |

Ver research.md #1 para a assinatura de conteúdo usada para desempatar
`.xls` (fatura vs conta corrente) e `.xlsx` (fatura vs BB).

## Transação (existente, sem mudança de schema)

Nenhum atributo novo. As transações originadas por upload web têm
exatamente os mesmos campos (`data`, `descricao`, `valor`, `tipo`,
`natureza`, `categoria_id`, `conta`, `titular`, `fonte`, `fingerprint`)
que as originadas pelo script CLI ou pela migração histórica — o caminho
de entrada não é um atributo da transação.

## Resposta da rota de upload (contrato HTTP, não persistido)

Mesmo formato de resumo já usado pelos scripts CLI
(`ImportarExtratoResumo` de `processar_transacoes`), serializado como
JSON:

```json
{
  "formato_detectado": "mercado_pago_fatura",
  "importadas": 25,
  "ja_existentes": 0,
  "puladas": 0,
  "classificadas_automaticamente": 22,
  "pendentes_natureza": 3,
  "reconciliadas": 0,
  "ambiguas": 0
}
```
