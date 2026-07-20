# Quickstart: Importar Extrato Bancário

Guia de validação ponta a ponta. Assume o app rodando localmente
(`python -m src.api.app`) com `data/financiall.db` de teste.

## Pré-requisitos

```bash
python -m src.storage.db  # ou qualquer entrypoint que chame init_db()
python -m src.scripts.seed_taxonomia_categorizacao   # já existente — garante TAXONOMIA_RESERVADA_EXTRATO
python -m src.scripts.seed_regras_natureza
```

## Cenário 1 — Classificação automática de natureza (US1)

1. Rodar `python -m src.scripts.importar_historico_extrato assets/finalcial/Financeiro/extrato/registro.json`.
2. Conferir na saída que a maioria das transações caiu em "cache/regra"
   (não em "pendente de revisão") — evidência de que o seed de
   `regra_natureza` (research.md #5) cobre o grosso do histórico real.
3. Rodar o mesmo comando de novo; confirmar que a contagem de "já
   existente" bate com o total da primeira execução (idempotência, FR-009).

## Cenário 2 — Migração histórica sem duplicar nem perder (US2)

1. Antes da migração, contar linhas de `registro.json` (418 na amostra
   real conhecida).
2. Depois da migração, `SELECT COUNT(*) FROM transacao` deve bater com
   "importadas" da saída do script.
3. Conferir que as duas grafias de conta do legado (`2486` e `Itaú_2486`)
   aparecem consolidadas: `SELECT DISTINCT conta FROM transacao` não deve
   ter as duas.

## Cenário 3 — Gasto do mês sem dupla contagem (US3)

1. Escolher uma nota fiscal já importada (feature 001/004) cujo `valor_total`
   e `data_emissao` batam com alguma transação de cartão do histórico
   migrado.
2. Confirmar via `GET /transacoes/reconciliacao/pendentes` que não há
   ambiguidade para ela, ou resolver manualmente se houver.
3. Comparar `GET /notas/resumo/mes-atual` (ou `/historico`) antes e depois
   da reconciliação: o total do mês daquela nota **não muda** quando ela
   reconcilia (a transação já contava; a nota só deixa de contar
   separadamente).
4. Testar o desfazer: `DELETE /transacoes/<id>/nota`, confirmar que o total
   do mês passa a contar a nota **e** a transação separadamente (o valor
   sobe de volta à soma das duas) — reflete que o sistema não presume mais
   que elas são a mesma compra.

## Cenário 4 — Fila de pendentes de natureza (US4)

1. Achar uma transação com `natureza IS NULL` (`GET /transacoes/pendentes`).
2. Classificar o grupo via `POST /transacoes/pendentes/classificar-grupo`.
3. Confirmar que uma transação **futura** com a mesma `descricao_normalizada`
   (nova execução de importação com um registro sintético) já chega
   classificada (cache).

## Cenário 5 — Gestão de estabelecimento (US5)

1. Achar um grupo em `GET /estabelecimentos/pendentes`.
2. Atribuir nome fantasia e tipo via `PUT /estabelecimentos/<id>`.
3. Confirmar em `GET /notas/resumo/categorias?dimensao=estabelecimento` que
   o gasto daquele estabelecimento aparece, mesmo sem nenhuma nota fiscal
   associada a essas transações.

## Cenário 6 — Parser recorrente (US6)

1. Rodar `python -m src.scripts.importar_extrato_itau_cartao <fatura.xls>`
   sobre um arquivo real de `assets/finalcial/Financeiro/extrato/` (ex.:
   `marcelo/cartao-2486-Fatura-Excel.xls`).
2. Confirmar que nenhuma transação já trazida pela migração histórica
   (Cenário 2) é duplicada — mesmas contas, mesmo fingerprint.

## Validação com dado real (Princípio V — obrigatória antes de promover)

Testes automatizados (sintéticos) cobrem os casos de borda conhecidos, mas
não substituem rodar contra o dado real do usuário. Antes de promover
dev → main:

1. Rodar a migração histórica completa contra uma cópia do banco real do
   Pi (ambiente dev), usando o `registro.json` real (418 transações reais,
   6 contas).
2. Conferir manualmente uma amostra de transações de cada conta (cartão
   9073, cartão 2486, conta corrente, Flash) — natureza e categoria fazem
   sentido para quem conhece os próprios gastos.
3. Rodar o parser Itaú cartão XLS contra pelo menos 2 arquivos reais de
   fatura diferentes (`assets/finalcial/Financeiro/extrato/marcelo/*.xls`),
   confirmando que a contagem de transações lidas bate com o número de
   linhas de compra real da fatura.
4. Verificação visual real (Princípio VIII) das duas filas novas
   (`/ver/transacoes/pendentes`, `/ver/estabelecimentos/pendentes`):
   captura de tela via navegador headless + checagem de ausência de erro
   de console, antes de promover para produção.
