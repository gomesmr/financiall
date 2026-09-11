# Data Model: Log de classificação manual de natureza

## Entidade: LogClassificacaoManual

Representa uma única ação de classificação manual de natureza já
concluída com sucesso (em grupo ou individual). Não se relaciona
diretamente a uma linha de `Transacao` — é um registro por ação,
podendo representar várias transações afetadas de uma vez (research.md
#1).

| Campo                       | Tipo   | Obrigatório | Descrição |
|------------------------------|--------|:-----------:|-----------|
| `id`                          | int    | sim (auto)  | Chave primária. |
| `data_hora`                   | texto (ISO datetime) | sim | Momento da classificação (`datetime.now().isoformat()`). |
| `metodo`                      | texto  | sim         | `"grupo"` (via fila de pendentes) ou `"individual"` (edição de uma transação específica). |
| `alvo_descricao_normalizada`  | texto  | não         | Descrição normalizada do grupo classificado; também preenchida na classificação individual, quando disponível (research.md #2). |
| `alvo_transacao_id`           | int    | não         | Id da transação, só preenchido no método `"individual"`. |
| `natureza`                    | texto  | sim         | Natureza atribuída (`gasto`, `renda`, `transferencia_interna`, `pagamento_fatura`, `estorno_credito`). |
| `categoria_id`                | int    | não         | Categoria atribuída; presente só quando `natureza == "gasto"`. |
| `quantidade_afetada`          | int    | sim         | Quantidade de transações efetivamente alteradas por esta ação (`>= 1`, nunca `0` — research.md #3). |

### Regras de validação / integridade

- `metodo == "grupo"` ⇒ `alvo_descricao_normalizada` preenchida,
  `alvo_transacao_id` nulo.
- `metodo == "individual"` ⇒ `alvo_transacao_id` preenchido; `alvo_descricao_normalizada`
  preenchida quando a transação tinha uma descrição normalizada conhecida.
- `categoria_id` preenchida se e somente se `natureza == "gasto"` (mesma
  regra já validada pelas rotas existentes antes de chegar aqui).
- `quantidade_afetada >= 1` sempre — um evento com `0` nunca é gravado
  (FR-005, research.md #3).
- Nenhum índice único: uma reclassificação do mesmo alvo gera uma nova
  linha, de propósito (FR-004 — o histórico acumula, não sobrescreve).

### Ordenação padrão de listagem

`ORDER BY data_hora DESC, id DESC` — mesmo padrão de `log_importacao`
(feature 014): ação mais recente primeiro, `id DESC` como desempate.

## Sem alteração em entidades existentes

`Transacao`, `classificar_grupo_pendente_natureza()` e
`atribuir_natureza_manual()` mantêm seu comportamento e retorno atuais —
esta feature só acrescenta uma tabela nova e uma escrita a mais dentro
dessas duas funções, sem mudar nenhum contrato existente (Assumptions da
spec).
