# Data Model: Importar fatura do cartão Mercado Pago

Nenhuma migração de schema — reaproveita as entidades já existentes
(`Transacao`, tabela `transacao`). Esta feature só adiciona novos valores
possíveis para o atributo `conta` e novos registros que passam pelo
mesmo pipeline de persistência já existente.

## Transação (existente, sem mudança de schema)

Atributos relevantes já existentes, preenchidos pelo parser novo do mesmo
jeito que os parsers Itaú/BB já preenchem:

| Campo | Origem no parser Mercado Pago |
|---|---|
| `data` | dia/mês da linha de lançamento + ano inferido da data de emissão da fatura (research.md #3) |
| `descricao` | texto do lançamento, incluindo o sufixo "Parcela X de Y" quando presente (research.md #4) |
| `valor` | valor em R$ da linha, convertido para centavos; sinal conforme research.md #6 |
| `tipo` | derivado do sinal (entrada/saída), mesma lógica de `_interpretar_valor_e_tipo` |
| `conta` | `MercadoPago_NNNN` (por cartão) ou `MercadoPago` (encargos gerais da fatura) — canonicalizado para `mercado_pago_NNNN` / `mercado_pago` |
| `titular` | sempre `"marcelo"` (Assumption da spec — fatura emitida em nome dele, mesmo quando há cartão adicional) |
| `fonte` | nome do arquivo PDF importado |
| `fingerprint` | `sha1(data | descrição_normalizada | valor_absoluto | conta)`, mesma fórmula já existente — nenhuma mudança |

## Registro intermediário do parser (`list[dict]`)

Mesmo contrato já usado pelos demais parsers recorrentes (`importar_extrato_itau_cartao.parsear`,
`importar_extrato_bb.parsear`) — dict de entrada para `processar_transacoes()`:

```python
{
    "data": "2026-06-15",        # ISO, ano já inferido
    "descricao": "MERCADOLIVRE*MERCADOLIVRE Parcela 1 de 4",
    "valor_raw": 13.30,          # float, sinal conforme lançamento (positivo = compra/encargo)
    "conta": "MercadoPago_3258", # ou "MercadoPago" para a seção de encargos gerais
    "fonte": "mercado-pago-2026-06.pdf",
    "titular": "marcelo",
}
```

## Conta canônica (extensão de `conta_canonica.py`)

| Grafia de origem | Canônico | Observação |
|---|---|---|
| `MercadoPago` | `mercado_pago` | encargos gerais da fatura (juros, multa, IOF, pagamento excluído) |
| `MercadoPago_<4 dígitos>` | `mercado_pago_<4 dígitos>` | por cartão vinculado à fatura; regex genérico cobre cartões futuros, mesmo padrão de `Itaú_<4 dígitos>` |

`_eh_conta_cartao()` (em `importar_historico_extrato.py`) passa a
reconhecer qualquer conta canônica iniciada por `mercado_pago` como
cartão de crédito (research.md #6) — sem isso os encargos da conta
genérica `mercado_pago` cairiam na convenção de sinal errada.

## Seed de regras de natureza (extensão de `regras_semente_natureza.json`)

Novas entradas (research.md #8), mesma categoria/subcategoria já usada
para os encargos equivalentes do rotativo do BB:

| Padrão | Natureza | Categoria / Subcategoria |
|---|---|---|
| `JUROS DE MORA` | gasto | Finanças / Tarifas e juros |
| `MULTA POR ATRASO` | gasto | Finanças / Tarifas e juros |
| `JUROS DO ROTATIVO` | gasto | Finanças / Tarifas e juros |
| `IOF DO ROTATIVO` | gasto | Finanças / Tarifas e juros |
