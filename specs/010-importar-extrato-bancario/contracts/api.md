# API Contract: Importar Extrato Bancário

## `GET /transacoes/pendentes` (JSON)

Fila de transações com `natureza IS NULL`, agrupadas por
`descricao_normalizada` — mesmo formato de `GET /itens/pendentes` (feature
008).

**Resposta** (`200`): `{"resumo": {"total_pendente": <n>, "total_transacoes": <n>},
"grupos": [{"descricao_normalizada": "<desc>", "quantidade_transacoes": <n>,
"exemplo_transacao_id": <id>}, ...]}`.

## `POST /transacoes/pendentes/classificar-grupo` (JSON)

**Corpo**: `{"descricao_normalizada": "<desc>", "natureza": "gasto"|"renda"|
"transferencia_interna"|"pagamento_fatura"|"estorno_credito", "categoria_id":
<id>|null}`. `categoria_id` é ignorado quando `natureza != "gasto"`;
obrigatório (`422` se ausente) quando `natureza == "gasto"`.

**Resposta** (`200`): `{"mensagem": "<N> transação(ões) classificada(s).",
"quantidade_afetada": <n>}`. Classifica toda transação pendente com aquela
`descricao_normalizada` numa única ação e grava em `cache_descricao_natureza`
(FR-006).

## `PUT /transacoes/<id>/natureza` (JSON)

Correção manual de uma transação específica (FR-007). **Corpo**:
`{"natureza": "...", "categoria_id": <id>|null}` (mesma regra de
`categoria_id` acima).

**Resposta**: `200` em sucesso; `404` se a transação não existe; `422` se
`natureza` for inválida ou `categoria_id` for exigido e ausente/inexistente.
A correção manual prevalece e passa a valer para futuras transações da
mesma descrição normalizada (upsert em `cache_descricao_natureza`).

## `GET /transacoes/reconciliacao/pendentes` (JSON)

Fila de casos ambíguos (mais de uma transação candidata para a mesma nota
fiscal, research.md #7). **Resposta** (`200`): `{"casos": [{"nota_fiscal_id":
<id>, "candidatos": [{"transacao_id": <id>, "data": "...", "descricao": "...",
"valor": <centavos>}, ...]}, ...]}`.

## `PUT /transacoes/<id>/nota` (JSON)

Resolve manualmente um caso ambíguo, ou cria uma reconciliação manual onde a
automática não encontrou nada. **Corpo**: `{"nota_fiscal_id": <id>}`.

**Resposta**: `200` em sucesso; `404` se a transação ou a nota não existem;
`422` se a nota já está reconciliada com outra transação (índice único).

## `DELETE /transacoes/<id>/nota`

Desfaz uma reconciliação (FR-014, "desfazer"), automática ou manual — zera
`transacao.nota_fiscal_id`. **Resposta**: `200` em sucesso; `404` se a
transação não existe ou não tem nota vinculada. Exposto na UI a partir de
`nota_detalhe.html` (extensão — ver abaixo).

## `GET /estabelecimentos/pendentes` (JSON)

Fila de transações sem `estabelecimento_id` resolvido, agrupadas por
`documento` (quando presente) ou `descricao_normalizada` (fallback).
**Resposta** (`200`): `{"grupos": [{"chave": "<documento_ou_descricao>",
"tipo_chave": "documento"|"descricao", "quantidade_transacoes": <n>,
"exemplo_transacao_id": <id>}, ...]}`.

## `PUT /estabelecimentos/<id>` (JSON)

Atribui/corrige `nome_fantasia` e `tipo_categoria_id` de um estabelecimento
— aplica automaticamente a todas as transações já vinculadas a ele (FR-018).
**Corpo**: `{"nome_fantasia": "<nome>", "tipo_categoria_id": <id>|null}`.
**Resposta**: `200` em sucesso; `404` se o estabelecimento não existe.

## `GET /ver/transacoes/pendentes` (HTML)

Página de revisão combinando a fila de natureza pendente e a fila de
reconciliação ambígua (mesmo espírito de `/ver/pendentes` da feature 008) —
uma central de revisão de transações, sem duplicar layout para cada fila
separadamente.

## `GET /ver/estabelecimentos/pendentes` (HTML)

Página de gerenciamento de estabelecimento (US5), mesmo padrão visual de
`/ver/transacoes/pendentes`.

## `GET /notas/resumo/categorias` (JSON) — **contrato estendido**

`dimensao=estabelecimento` passa a incluir transações sem nota fiscal
correspondente, agrupadas por `estabelecimento.tipo_categoria_id` (FR-020),
somadas junto com as notas já contempladas hoje. `dimensao=item` passa a
somar `transacao` (natureza=gasto) mais `nota_fiscal` não reconciliada
(research.md #8) — sem mudança na forma do contrato, só na composição da
soma.

## `GET /notas/resumo/mes-atual` / `GET /notas/resumo/historico` — **contrato estendido**

Mesma forma de resposta; `total_gasto` passa a refletir a soma combinada
(transação + nota não reconciliada) em vez de só nota fiscal.

## Extensão em `GET /ver/notas/<id>` (HTML)

Quando a nota tem uma transação reconciliada (`transacao.nota_fiscal_id =
<id>`), a página passa a exibir os dados da transação (conta, data do
lançamento) e um botão "Desvincular" (aciona `DELETE
/transacoes/<id>/nota`, FR-014).
