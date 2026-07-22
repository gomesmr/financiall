# Quickstart: Importar extrato BB (Cristine) e visão por titular

Guia de validação ponta a ponta. Assume o app rodando localmente
(`python -m src.api.app`) com um `data/financiall.db` de teste.

## Pré-requisitos

```bash
python -m src.storage.db  # ou qualquer entrypoint que chame init_db()
python -m src.scripts.seed_regras_natureza   # inclui as novas regras da Cristine (research.md #9)
```

## Cenário 1 — Importar o histórico real da Cristine sem duplicar (US1)

1. Rodar `python -m src.scripts.importar_extrato_bb assets/finalcial/Financeiro/extrato/cristine/`
   (pasta com os 5 arquivos reais, jan–mai/2026).
2. Conferir na saída que a maior parte caiu em "cache/regra" (evidência de
   que o seed cobre o vocabulário real dela), e não em "pendente de
   revisão".
3. `SELECT COUNT(*) FROM transacao WHERE titular = 'cristine'` deve bater
   com "importadas" da saída do script.
4. Rodar o mesmo comando de novo (mesma pasta); confirmar que a contagem de
   "já existente" bate com o total da execução anterior (idempotência,
   FR-004).

## Cenário 2 — Reconciliação com nota fiscal também funciona para a Cristine (US1)

1. Escolher uma transação do extrato BB cujo valor e data batam com alguma
   nota fiscal já importada com `titular='cristine'`.
2. Confirmar via `GET /transacoes/reconciliacao/pendentes` que ela reconciliou
   automaticamente (ou resolver manualmente se ambígua) — mesmo
   comportamento já validado para o Marcelo na feature 010.

## Cenário 3 — Resumo mensal quebrado por titular (US2)

1. Com transações de Marcelo e Cristine no mesmo mês, abrir
   `GET /ver/resumo?mes=<AAAA-MM>` (sem filtro) — total deve ser o
   consolidado do casal.
2. Abrir `GET /ver/resumo?mes=<AAAA-MM>&titular=cristine` — total deve
   refletir só as transações/notas dela.
3. Repetir com `titular=marcelo` e conferir que os dois totais somados
   batem com o consolidado do passo 1 (menos qualquer transferência
   interna entre os dois — Cenário 4).
4. Abrir `GET /ver/transacoes?titular=cristine` e confirmar que só
   transações dela aparecem.

## Cenário 4 — Transferência entre o casal não distorce o saldo (US2)

1. Identificar no extrato da Cristine uma transferência para o Marcelo
   (ex.: descrição contendo "MARCELO RENATO GOMES") e a entrada
   correspondente no extrato do Itaú dele.
2. Confirmar que ambas as transações foram classificadas com
   `natureza = 'transferencia_interna'` (não `gasto` nem `renda`).
3. Comparar `saldo_do_mes` do casal antes e depois de classificar essas
   duas transações: o saldo não deve mudar ao reclassificar uma
   transferência que já estava marcada como gasto/renda por engano —
   evidência de que a exclusão funciona (FR-010/SC-003).

## Cenário 5 — Importação recorrente de um extrato novo (US3)

1. Simular um novo extrato do BB com um período que se sobrepõe
   parcialmente ao já importado (mesmas transações de maio + transações
   novas de junho).
2. Rodar `python -m src.scripts.importar_extrato_bb <novo-arquivo>`.
3. Confirmar que só as transações de junho (fora da sobreposição) somam à
   contagem de "importadas"; as de maio contam como "já existente".
4. Repetir o mesmo teste de sobreposição com um novo arquivo de fatura
   Itaú (`python -m src.scripts.importar_extrato_itau_cartao`), confirmando
   que o fluxo recorrente já validado na feature 010 continua funcionando
   sem regressão.

## Validação com dado real (Princípio V — obrigatória antes de promover)

Testes automatizados (sintéticos) cobrem os casos de borda conhecidos, mas
não substituem rodar contra o dado real do usuário. Antes de promover
dev → main:

1. Rodar a importação histórica completa contra os 5 arquivos reais de
   `assets/finalcial/Financeiro/extrato/cristine/*.xlsx` sobre uma cópia do
   banco real do Pi (ambiente dev).
2. Conferir manualmente uma amostra de transações classificadas
   automaticamente — natureza e categoria fazem sentido comparado ao
   gabarito manual em `Cristine.xlsx` (aba do mês correspondente, tabela
   "LANÇAMENTOS REAIS").
3. Conferir a taxa de classificação automática (cache/regra vs. pendente)
   — se ficar muito abaixo da taxa alcançada para o Marcelo (78%, feature
   010), revisar o seed de regras (research.md #9) antes de promover.
4. Comparar o saldo mensal do casal (jan–mai/2026) calculado pelo
   financiALL após a importação com o `Consolidado.xlsx` legado (linha
   "SALDO CONJUNTO") — divergência esperada só onde o legado usava
   orçamento estimado (colunas marcadas com `*`), nunca nos meses com dado
   real.
5. Verificação visual real (Princípio VIII) do seletor de titular em
   `/ver/resumo` e `/ver/transacoes`: captura de tela via navegador
   headless + checagem de ausência de erro de console, antes de promover
   para produção.
