# Research: Relatórios Mensais (Resumo por Item + Estabelecimento + Navegação por Mês)

## 1. Estratégia de agregação (SQL vs. Python)

**Decision**: buscar as linhas cruas (nota × item, via `LEFT JOIN`) com uma única
query por dimensão e fazer o agrupamento/soma em Python.

**Rationale**: o volume de dados é de uso pessoal (dezenas de notas e itens por
mês, não milhares) — a query complexa em SQL (CASE para decidir fallback por
nota, agregação em dois níveis de categoria) ficaria mais difícil de ler e
testar do que a mesma lógica em Python puro, sem ganho de performance
perceptível (Princípio I).

**Alternatives considered**: `CASE WHEN` + subquery correlacionada em SQL
para decidir por nota se ela "tem item classificado" — rejeitado por
complexidade desproporcional ao volume de dados e por dificultar teste
unitário isolado da regra de negócio.

## 2. Visão por tipo de estabelecimento reaproveita a função existente

**Decision**: renomear `gasto_por_categoria` (hoje soma `nota_fiscal.categoria_id`
por mês) para `gasto_por_estabelecimento`, adicionando um parâmetro `nivel`
(1 ou 2).

**Rationale**: a função já implementa exatamente a agregação necessária para
o eixo "tipo de estabelecimento" (soma por `nota_fiscal.categoria_id`) — o
único ajuste é o parâmetro de nível. Criar uma função nova duplicaria lógica
já testada (Princípio I).

**Alternatives considered**: manter o nome antigo e criar uma segunda função
para o eixo "estabelecimento" — rejeitado, geraria duas funções fazendo a
mesma coisa sob nomes diferentes.

## 3. Toggle nível 1 / nível 2

**Decision**: resolver subcategoria → categoria-pai em Python, usando um
dicionário `{categoria_id: Categoria}` pré-carregado (`listar_categorias`).
Nível 1 agrupa pelo topo (categoria-pai, ou a própria categoria se ela já for
de topo); nível 2 agrupa pela categoria tal como está atribuída ao item/nota.

**Rationale**: a taxonomia é de 2 níveis fixos (Princípio I / feature 008) —
resolver o pai é um lookup O(1) em memória, não precisa de self-join em SQL.

**Alternatives considered**: `SELECT` com self-join em `categoria` para
resolver o pai diretamente no SQL — rejeitado, complexidade desnecessária
para uma tabela de dezenas de linhas.

## 4. Modelo de navegação entre meses

**Decision**: `meses_navegaveis` = união ordenada (desc) de `{mes_atual()}` com
todos os meses que têm nota (`listar_meses_com_notas`). Mês anterior/seguinte
é calculado pela posição do mês selecionado nessa lista (não por aritmética de
calendário), então meses sem nenhuma nota nunca aparecem como destino de
navegação — consistente com a seção Assumptions do spec.

**Rationale**: navegação por posição na lista garante que "mês anterior"
sempre leva a um mês com conteúdo (ou ao mês corrente, que é sempre incluído
mesmo vazio).

**Alternatives considered**: navegação por aritmética de calendário
(mês - 1 / mês + 1 sempre), tratando meses vazios com uma tela "sem notas" —
rejeitado explicitamente pela Assumption do spec (evita construir uma tela
vazia sem necessidade).

## 5. Navegação da visualização para a listagem de notas (drill-down)

**Decision**: cliques nas fatias dos gráficos (evento nativo `plotly_click` do
Plotly, já vendorizado) constroem a URL `/ver/notas?mes=<mes>` (visão por
item) ou `/ver/notas?mes=<mes>&estabelecimento=<categoria_id>` (visão por
estabelecimento) e navegam via `window.location`.

**Rationale**: Plotly já expõe esse evento nativamente, sem precisar de
biblioteca nova; a URL com query string reaproveita o padrão de filtro já
usado em `/ver/notas?titular=...`.

**Alternatives considered**: botão "ver notas" separado por fatia — rejeitado,
menos direto do que clicar na própria fatia.

## 6. Notas agrupadas por mês

**Decision**: agrupar em Python (`itertools.groupby`) sobre o resultado já
ordenado de `storage_db.listar_notas()` (já ordenado por `mes_ordenacao DESC,
id DESC` desde a feature 001/004).

**Rationale**: zero SQL novo — a ordenação necessária para agrupar
corretamente já existe.

**Alternatives considered**: `GROUP BY` em SQL retornando uma estrutura
aninhada — SQLite não modela bem resultado aninhado nativamente; o
agrupamento em Python sobre uma lista já ordenada é direto e testável.

## 7. Taxonomia de tipo de estabelecimento (seed idempotente)

**Decision**: novo script `src/scripts/seed_taxonomia_estabelecimento.py`,
mesmo padrão do `seed_taxonomia_categorizacao.py` (feature 008) — insere
apenas as categorias/subcategorias de estabelecimento que ainda não existem
(reaproveita a validação de duplicata já existente em `criar_categoria`).
Categorias-semente: Supermercado, Mercearia, Restaurante, Bar, Farmácia, Pet
Shop, Saúde (com subcategorias Dentista e Plano de Saúde) — mantém qualquer
categoria de estabelecimento que o usuário já tenha criado, sem renomear
nada automaticamente.

**Rationale**: mesmo padrão já validado na feature 008; idempotência
(Princípio II) garante que rodar em dev e depois em produção não duplica
nem quebra categorias já em uso por notas reais.

**Alternatives considered**: criar as categorias manualmente via UI antes do
deploy — rejeitado, não repetível/auditável entre dev e produção.

## 8. Reclassificação das notas reais existentes

**Decision**: aplicada diretamente nos ambientes do Pi (dev primeiro) usando
a função já existente `atribuir_categoria_a_nota`, com a revisão de cada nota
feita diretamente na conversa (sem gerar um documento de revisão em lote como
`assets/proposta-classificacao.md` da feature 008).

**Rationale**: a feature 008 tratava ~300 itens reais, o que justificava um
documento dedicado com múltiplas rodadas de revisão; aqui o volume é a
quantidade de notas (uma ordem de grandeza menor), o que não justifica a
mesma cerimônia (Princípio I).

**Alternatives considered**: repetir o processo de documento de revisão em
lote da feature 008 — rejeitado, desproporcional ao volume de dados deste
caso.

## 9. Extensão do contrato `GET /notas/resumo/categorias`

**Decision**: estender o endpoint existente com `dimensao` (`item` default |
`estabelecimento`) e `nivel` (`1` default | `2`), em vez de criar um endpoint
paralelo.

**Rationale**: é um endpoint de uso interno da própria página de resumo (sem
consumidor externo documentado) — mudar o comportamento default é seguro e
evita duplicar documentação/rota para o mesmo conceito de "gasto agrupado".

**Alternatives considered**: `GET /notas/resumo/estabelecimentos` como rota
nova e paralela — rejeitado, duplicaria a mesma forma de resposta
(`{mes, categorias, parcial}`) sob nomes diferentes.

## 10. Verificação visual (Princípio VIII)

**Decision**: captura de tela via navegador headless local
(`chrome.exe --headless=new --screenshot=...`) das páginas `/ver/resumo` e
`/ver/notas`, cobrindo pelo menos: mês com dado nas duas dimensões, mês sem
nenhuma nota, visão "os dois" simultânea, e a listagem de notas agrupada por
mês — mais checagem de ausência de erro de console JS na mesma execução.

**Rationale**: exigência constitucional direta (Princípio VIII) — nenhum
asset de terceiro novo é vendorizado nesta feature, então a cláusula de
integridade de asset não se aplica, só a verificação visual em si.

**Alternatives considered**: nenhuma — verificação obrigatória, sem
alternativa aceitável.
