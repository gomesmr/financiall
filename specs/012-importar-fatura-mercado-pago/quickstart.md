# Quickstart: Importar fatura do cartão Mercado Pago

Guia de validação ponta a ponta. Assume o app rodando localmente
(`python -m src.api.app`) com um `data/financiall.db` de teste.

## Pré-requisitos

```bash
pip install -e .   # instala pdfplumber (nova dependência, research.md #9)
python -m src.storage.db  # ou qualquer entrypoint que chame init_db()
python -m src.scripts.seed_regras_natureza   # inclui as novas regras de encargos (data-model.md)
```

## Cenário 1 — Importar a fatura real de junho/2026 sem duplicar (US1)

1. Rodar `python -m src.scripts.importar_fatura_mercado_pago "assets/novos-extratos/mercado-pago-2026-06.pdf"`.
2. Conferir na saída que as ~25 transações reais da fatura foram
   importadas (compras dos dois cartões + os 4 encargos), e que o
   lançamento "Pagamento da fatura de junho/2026" não aparece contado.
3. `SELECT COUNT(*) FROM transacao WHERE conta LIKE 'mercado_pago%'` deve
   bater com "importadas" da saída do script.
4. Rodar o mesmo comando de novo (mesmo arquivo); confirmar que a
   contagem de "já existente" bate com o total da execução anterior
   (idempotência, FR-007).

## Cenário 2 — Encargos da fatura contam como gasto, pagamento não conta (US1)

1. Após a importação, verificar que as 4 transações da conta `mercado_pago`
   (Juros de mora, Multa por atraso, Juros do rotativo, IOF do rotativo)
   estão classificadas como `natureza = 'gasto'`.
2. Confirmar que não existe nenhuma transação com descrição contendo
   "Pagamento da fatura" na conta `mercado_pago` — esse lançamento deve
   ter sido excluído na importação (FR-004).

## Cenário 3 — Reconciliação com nota fiscal também funciona (US1)

1. Escolher uma transação da fatura Mercado Pago cujo valor e data batam
   com alguma nota fiscal já importada.
2. Confirmar via `GET /transacoes/reconciliacao/pendentes` que ela
   reconciliou automaticamente (ou resolver manualmente se ambígua) —
   mesmo comportamento já validado para o Itaú na feature 010.

## Cenário 4 — Importação recorrente sem perder parcela nova (US2)

1. Simular uma "fatura de julho/2026" com a mesma compra parcelada
   presente na fatura de junho (ex.: `CLARICELL`, mesma data original,
   mesmo valor, "Parcela 15 de 21" em vez de "Parcela 14 de 21").
2. Rodar a importação contra essa segunda fatura.
3. Confirmar que a parcela 15 entra como transação nova ("importada"), não
   como "já existente" — evidência de que o fingerprint distingue
   parcelas consecutivas da mesma compra (research.md #4, FR-007).
4. Confirmar que uma compra não-parcelada repetida entre as duas faturas
   (mesma data, descrição e valor — não deveria existir na prática, mas
   serve de teste de regressão) continua sendo tratada como "já
   existente".

## Validação com dado real (Princípio V — obrigatória antes de promover)

Testes automatizados (sintéticos) cobrem os casos de borda conhecidos, mas
não substituem rodar contra o dado real do usuário. Antes de promover
dev → main:

1. Rodar a importação contra o arquivo real
   `assets/novos-extratos/mercado-pago-2026-06.pdf` sobre uma cópia do
   banco real do Pi (ambiente dev).
2. Conferir manualmente que o total importado bate com o "Total a pagar"
   da fatura, decompondo: soma das compras de cada cartão + encargos −
   pagamento excluído deve corresponder ao raciocínio do "Resumo da
   fatura" impresso na própria fatura (consumos + tarifas/encargos +
   multas, descontando pagamentos já contados em outra conta).
3. Conferir a taxa de classificação automática (cache/regra vs.
   pendente) das transações importadas — se ficar muito abaixo da taxa
   alcançada para o Itaú, revisar o seed de regras antes de promover.
4. Quando a próxima fatura real do Mercado Pago for baixada (mês
   seguinte), repetir a importação contra ela e confirmar que nenhuma
   parcela recorrente já vista foi perdida nem duplicada (Cenário 4)
   antes de considerar a importação recorrente validada de fato.
