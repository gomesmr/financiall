# Contrato: API HTTP — Gráficos no Resumo (feature 005)

Adiciona ao contrato existente. Mesmas convenções: JSON, mensagens em
português, `2xx` para sucesso (inclusive "sem dados", que não é erro).

## `GET /notas/resumo/categorias`

Retorna o gasto agrupado por categoria para um mês.

**Query string**: `?mes=AAAA-MM` (opcional — default é o mês corrente,
mesmo default implícito do resto do resumo).

**Resposta** (`200`): `{"mes": "AAAA-MM", "categorias": [{"categoria_id":
<id>|null, "nome": "<nome>"|"Sem categoria", "total_gasto": <centavos>},
...], "parcial": true}` — mesma semântica `"parcial": true` já usada em
`/notas/resumo/mes-atual`/`/notas/resumo/historico` (reflete só notas
fiscais importadas). Lista vazia (`{"categorias": []}`) quando o mês não
tem nenhuma nota com valor — nunca um erro.

Ordenado do maior para o menor `total_gasto`.

## `GET /notas/resumo/historico` — reaproveitado sem alteração de contrato

Já existente (feature 001) — o gráfico de barras consome exatamente essa
rota, sem parâmetro novo. Nenhuma mudança de formato de resposta.

## `GET /ver/resumo` — comportamento novo (view HTML)

Página existente ganha os dois gráficos (pizza + barras) e um seletor de
mês para a pizza. O seletor lista os meses que já aparecem na tabela
"Meses anteriores" mais o mês corrente — nenhum mês novo é inventado
além do que a página já mostrava em texto.
