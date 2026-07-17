# Quickstart: Relatórios Mensais

Guia de validação ponta a ponta desta feature. Assume o app já rodando
localmente (`python -m src.api.app` ou equivalente já usado no projeto) com
`data/financiall.db` populado por pelo menos uma nota com itens classificados
(feature 008).

## Pré-requisitos

- Pelo menos uma nota de um mês `M1` com itens classificados em categorias
  diferentes (ex.: um item "Alimentação", outro "Higiene pessoal e
  perfumaria").
- Pelo menos uma nota de outro mês `M2` sem nenhum item classificado (todos
  pendentes, ou nota sem itens).
- Pelo menos duas notas de meses diferentes atribuídas a tipos de
  estabelecimento diferentes (ex.: uma "Supermercado", outra "Restaurante").
- Seed de taxonomia de estabelecimento já rodado
  (`python -m src.scripts.seed_taxonomia_estabelecimento`).

## Cenário 1 — Resumo por categoria do item com fallback (US1, FR-001/002/003)

1. Abrir `/ver/resumo?mes=M1&dimensao=item`.
2. Confirmar que os valores aparecem separados pelas categorias dos itens
   (não uma fatia única para a nota inteira).
3. Abrir `/ver/resumo?mes=M2&dimensao=item`.
4. Confirmar que o valor total da nota sem itens classificados aparece sob a
   categoria da própria nota (ou "Sem categoria").
5. Alternar para `nivel=2` em `M1` e confirmar que a fatia muda de categoria
   de topo para subcategoria.

**Resultado esperado**: contrato de `GET /notas/resumo/categorias?mes=M1&dimensao=item&nivel=1|2`
bate com o que a tela mostra.

## Cenário 2 — Navegação por mês (US2, FR-004/005)

1. Abrir `/ver/resumo` sem `mes` (default: mês corrente).
2. Clicar em "mês anterior" repetidamente até chegar em `M1`.
3. Confirmar que cada clique atualiza o total e o gráfico, e que o mês ativo
   fica visível o tempo todo.
4. A partir de `M1`, usar a ação de "mês mais recente" e confirmar retorno
   direto ao mês corrente.

**Resultado esperado**: nenhum mês sem nota aparece como destino de
navegação (Assumptions do spec).

## Cenário 3 — Drill-down para notas (US3, FR-006)

1. Em `/ver/resumo?mes=M1&dimensao=item`, clicar numa fatia de categoria.
2. Confirmar que a navegação leva a `/ver/notas?mes=M1` com exatamente as
   notas de `M1`.
3. Em `/ver/resumo?mes=M1&dimensao=estabelecimento`, clicar numa fatia de
   tipo de estabelecimento (ex.: "Restaurante").
4. Confirmar que a navegação leva a `/ver/notas?mes=M1&estabelecimento=<id>`
   com só as notas daquele mês E daquele tipo de estabelecimento.

## Cenário 4 — Notas agrupadas por mês (US4, FR-007/008)

1. Abrir `/ver/notas` sem nenhum filtro.
2. Confirmar que as notas aparecem organizadas em seções por mês, mês mais
   recente primeiro.
3. Aplicar o filtro `?titular=marcelo` e confirmar que o agrupamento por mês
   se mantém, agora só com as notas desse titular.

## Cenário 5 — Visão por tipo de estabelecimento (US5, FR-010/011)

1. Abrir `/ver/resumo?mes=M1&dimensao=estabelecimento`.
2. Confirmar que os valores são agrupados pelo tipo de estabelecimento da
   nota, não pela categoria dos itens dentro dela.
3. Selecionar a visão "os dois" e confirmar que os dois gráficos aparecem
   juntos na mesma tela, sem perder o mês selecionado.

## Cenário 6 — Revisão da taxonomia de estabelecimento (US6, FR-012)

1. Rodar `python -m src.scripts.seed_taxonomia_estabelecimento` contra o banco
   de dev do Pi.
2. Confirmar via `/categorias` que Supermercado, Mercearia, Restaurante, Bar,
   Farmácia, Pet Shop e Saúde (com Dentista/Plano de Saúde) existem.
3. Reclassificar uma nota real de teste via `/ver/notas/<id>` (campo "Tipo de
   estabelecimento") e confirmar que a mudança reflete imediatamente no
   resumo do mês correspondente.

## Validação com dado real (segunda barreira, Princípio V)

Rodar os cenários 1, 3 e 5 contra o banco de dev do Pi (dado real já
existente, não sintético) antes de promover a feature — sem isso, a suíte
automatizada sozinha não é suficiente para promover (Princípio V, mesmo
padrão da feature 008).

## Verificação visual (Princípio VIII)

Captura de tela headless de `/ver/resumo` (mês com dado nas duas dimensões,
mês vazio, visão "os dois") e de `/ver/notas` (agrupada por mês) — mais
checagem de ausência de erro de console JS — antes de promover.
