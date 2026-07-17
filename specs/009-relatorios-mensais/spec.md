# Feature Specification: Relatórios Mensais (Resumo por Item + Estabelecimento + Navegação por Mês)

**Feature Branch**: `009-relatorios-mensais`

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "Evoluir a página de resumo/relatórios (/ver/resumo) e sua integração
com a listagem de notas (/ver/notas), agora que a feature 008 trouxe classificação por item.
Resumo deve preferir a soma por categoria dos itens quando existirem itens classificados na
nota; só cair para a categoria da nota quando não houver nenhum item classificado. Página de
resumo precisa de redesign profissional: filtros por mês, navegação intuitiva, acesso à
listagem das notas daquele mês, notas agrupadas por mês de forma mais intuitiva. Além disso, a
categoria da NOTA deve passar a representar o tipo de estabelecimento (Supermercado,
Mercearia, Restaurante, Bar, Saúde > Dentista, Saúde > Plano de Saúde, etc.) — um eixo
independente de 'o que foi comprado' (categoria do item), já que o mesmo tipo de item pode ser
comprado em estabelecimentos diferentes. O resumo deve permitir visualizar o gasto por tipo de
estabelecimento, por categoria do item (nível 1 ou nível 2, alternável), ou os dois ao mesmo
tempo."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver o gasto mensal refletindo a classificação real dos itens (Priority: P1)

Hoje o resumo agrupa gasto por categoria usando só o rótulo único que o usuário atribuiu à
nota inteira (feature 003). Isso esconde a mistura real de categorias que uma única nota pode
conter (ex.: uma compra de supermercado com itens de Alimentação, Higiene e Pet), já que a
feature 008 classifica cada item individualmente com muito mais precisão. O usuário quer que
o resumo mensal reflita essa granularidade: somar o gasto por categoria a partir dos itens
classificados, e só usar a categoria da nota como respaldo quando a nota não tiver nenhum item
classificado (ex.: nota registrada com falha de extração de itens). O usuário também quer
poder alternar entre ver essa quebra pela categoria de topo do item (ex.: Alimentação,
Bebidas, Pets) ou pela subcategoria (ex.: Alimentos pré-processados, Biscoitos, Lanche,
Rotisserie, Sucos e isotônicos, Itens diversos).

**Why this priority**: é a mudança que corrige a informação que o resumo mostra — sem ela, o
relatório continua desatualizado em relação ao que o sistema já sabe sobre cada compra, mesmo
com toda a navegação/redesign das outras histórias.

**Independent Test**: importar/ter uma nota com itens classificados em categorias diferentes
entre si (e diferentes da categoria da própria nota, se houver), abrir o resumo do mês
correspondente, e confirmar que os valores aparecem separados pelas categorias dos itens (não
agrupados sob uma única categoria de nota), e que alternar entre nível 1 e nível 2 muda o
detalhamento exibido.

**Acceptance Scenarios**:

1. **Given** uma nota com itens classificados em "Alimentação" e "Higiene pessoal e
   perfumaria", **When** o usuário abre o resumo do mês dessa nota, **Then** o valor de cada
   item aparece somado na categoria daquele item, não sob uma categoria única para a nota
   inteira.
2. **Given** uma nota sem nenhum item classificado (todos pendentes, ou nota sem itens
   extraídos), **When** o usuário abre o resumo do mês dessa nota, **Then** o valor total da
   nota aparece somado sob a categoria atribuída à própria nota (ou "Sem categoria", se a nota
   também não tiver categoria).
3. **Given** uma nota com alguns itens classificados e outros ainda pendentes, **When** o
   usuário abre o resumo, **Then** o valor dos itens classificados aparece nas categorias
   correspondentes, e o valor dos itens pendentes aparece separadamente sob "Sem categoria"
   (não é atribuído à categoria da nota, já que a nota tem pelo menos um item classificado).
4. **Given** o usuário está vendo o resumo por categoria de item no nível 1 (topo), **When**
   ele alterna para o nível 2, **Then** o gráfico passa a exibir as subcategorias (ex.:
   "Alimentos pré-processados", "Biscoitos") em vez das categorias de topo.

---

### User Story 2 - Navegar o resumo mês a mês de forma fluida (Priority: P1)

Hoje a navegação entre meses no resumo é limitada (um seletor solto para o gráfico de
categorias, uma lista separada de "meses anteriores" para o gráfico de barras). O usuário quer
uma navegação única e intuitiva entre meses, com o mês corrente como ponto de partida natural.

**Why this priority**: sem uma forma clara de navegar entre meses, o resto do relatório
(inclusive as novas quebras por item e por estabelecimento) fica difícil de explorar — é a
espinha dorsal de usabilidade da página.

**Independent Test**: com notas em pelo menos 3 meses diferentes, abrir o resumo, navegar para
um mês anterior e depois para outro, confirmando que a página sempre deixa claro qual mês está
sendo exibido e como voltar/avançar.

**Acceptance Scenarios**:

1. **Given** o usuário está no resumo do mês corrente, **When** ele navega para o mês
   anterior, **Then** a página atualiza o gasto por categoria e o total para refletir o mês
   selecionado, com indicação visual clara de qual mês está ativo.
2. **Given** o usuário está em um mês qualquer com dado, **When** ele quer voltar ao mês mais
   recente com nota, **Then** existe uma ação direta para isso (não precisa navegar mês a mês
   manualmente até chegar lá).

---

### User Story 3 - Ver as notas por trás de um número do resumo (Priority: P1)

O usuário quer, a partir do resumo de um mês — seja de uma fatia de categoria do item ou de
uma fatia de tipo de estabelecimento — acessar diretamente a lista das notas daquele mês (e
daquele recorte), para entender quais compras compõem aquele total.

**Why this priority**: um resumo que não permite "abrir" o número pra ver as notas por trás
dele tem valor limitado para decisão financeira — é o elo que faltava entre o relatório
agregado e o detalhe já existente (`/ver/notas`, `/ver/notas/<id>`).

**Independent Test**: no resumo de um mês com notas, clicar na ação de ver as notas daquele
mês (e opcionalmente de um tipo de estabelecimento específico), e confirmar que a lista
exibida corresponde exatamente ao recorte escolhido.

**Acceptance Scenarios**:

1. **Given** o usuário está vendo o resumo de um mês específico, **When** ele aciona "ver
   notas deste mês", **Then** ele chega a uma lista contendo exatamente as notas emitidas
   naquele mês, sem precisar reconfigurar filtro manualmente.
2. **Given** o usuário está vendo o resumo por tipo de estabelecimento e clica numa fatia
   específica (ex.: "Restaurante"), **When** a navegação para notas acontece, **Then** a lista
   exibida é filtrada pelo mês E pelo tipo de estabelecimento selecionado.

---

### User Story 4 - Encontrar notas antigas por mês sem esforço (Priority: P2)

Hoje `/ver/notas` é uma tabela plana com um filtro de mês solto (dropdown). O usuário quer que
a listagem de notas apresente os meses de forma visualmente organizada (agrupada), tornando a
navegação por histórico mais natural — sem precisar já saber qual mês procurar antes de abrir
o filtro.

**Why this priority**: complementa a US3 (chegar a um mês específico vindo do resumo) com a
outra direção de uso — o usuário que já está na lista de notas e quer se orientar pelo
histórico sem sair da página.

**Independent Test**: com notas em vários meses, abrir `/ver/notas` sem filtro nenhum e
confirmar que dá para identificar visualmente a que mês cada nota pertence e navegar entre
meses sem precisar já saber o mês exato de antemão.

**Acceptance Scenarios**:

1. **Given** notas em múltiplos meses, **When** o usuário abre a listagem de notas sem
   filtro, **Then** as notas aparecem organizadas por mês (mês mais recente primeiro), com
   indicação clara de qual mês cada grupo representa.

---

### User Story 5 - Ver o gasto por tipo de estabelecimento, independente do item comprado (Priority: P2)

O usuário quer visualizar o gasto mensal agrupado pelo tipo de estabelecimento onde a compra
foi feita (Supermercado, Mercearia, Restaurante, Bar, Farmácia, Pet Shop, etc.) — um eixo
independente da categoria do item, já que o mesmo tipo de produto (ex.: cerveja, embutidos,
vassoura) pode ser comprado em estabelecimentos bem diferentes. Essa visão usa a categoria já
atribuída à nota (feature 003), agora entendida explicitamente como "tipo de estabelecimento"
em vez de "categoria de gasto".

**Why this priority**: entrega uma segunda lente de análise financeira (onde eu gasto, não só
o que eu compro), complementar à US1 — não bloqueia o valor já entregue por US1-US3, mas é o
outro pilar explícito do pedido do usuário.

**Independent Test**: com notas atribuídas a diferentes tipos de estabelecimento num mesmo
mês, abrir o resumo, selecionar a visão "por tipo de estabelecimento", e confirmar que os
valores aparecem agrupados por esse eixo (não pela categoria dos itens).

**Acceptance Scenarios**:

1. **Given** notas de um mês atribuídas a "Supermercado", "Restaurante" e "Bar", **When** o
   usuário seleciona a visão por tipo de estabelecimento no resumo, **Then** o gráfico mostra
   o total gasto em cada um desses tipos, independentemente da categoria dos itens dentro de
   cada nota.
2. **Given** o usuário está no resumo de um mês, **When** ele alterna entre "por tipo de
   estabelecimento", "por categoria do item" e "os dois juntos", **Then** a página exibe a
   combinação escolhida sem precisar recarregar manualmente outros filtros (mês continua o
   mesmo).

---

### User Story 6 - Revisar a taxonomia de tipo de estabelecimento das notas existentes (Priority: P3)

As categorias de nota já existentes hoje (Supermercado, Saúde, Pets, etc., da feature 003)
foram pensadas soltas, sem o conceito explícito de "tipo de estabelecimento" e sem
subcategorias. O usuário quer revisar/expandir essa taxonomia (ex.: "Saúde" ganhar
subcategorias como "Dentista" e "Plano de Saúde"; adicionar tipos como "Mercearia",
"Restaurante", "Bar"; ajustar rótulos que hoje descrevem mais uma "área de gasto" do que um
tipo de estabelecimento) e reclassificar as notas reais existentes de acordo.

**Why this priority**: é o que torna a US5 (visão por estabelecimento) precisa — sem essa
revisão, a visão por estabelecimento ainda funciona, mas reflete uma taxonomia
grosseira/desatualizada. Não bloqueia o lançamento das demais histórias, por isso fica em P3.

**Independent Test**: revisar a lista de categorias de nota existentes, criar/ajustar as que
fazem sentido como tipo de estabelecimento (com subcategoria quando aplicável), reclassificar
as notas reais afetadas, e confirmar que cada nota passa a ter um tipo de estabelecimento
coerente com onde a compra realmente ocorreu.

**Acceptance Scenarios**:

1. **Given** a categoria de nota "Saúde" hoje sem subcategoria, **When** o usuário revisa a
   taxonomia, **Then** ele consegue criar subcategorias como "Dentista" e "Plano de Saúde" sob
   "Saúde", reaproveitando o mesmo mecanismo de categoria de dois níveis já usado para itens
   (feature 008).
2. **Given** uma nota real hoje classificada com um rótulo que não representa bem um tipo de
   estabelecimento, **When** o usuário a reclassifica com a taxonomia revisada, **Then** o
   sistema atualiza a categoria da nota mantendo o histórico de auditoria já existente.

---

### Edge Cases

- Nota com item cujo valor está ausente/nulo (extração incompleta): o item não contribui para
  nenhuma soma de categoria (mesmo comportamento de hoje para valores nulos).
- Mês sem nenhuma nota registrada: a navegação do resumo não oferece esse mês como destino
  navegável (não existe conteúdo para exibir) — ver Assumptions.
- Nota sem categoria própria e sem nenhum item classificado: cai em "Sem categoria" no resumo
  de item, mesmo comportamento herdado da feature 005; na visão por estabelecimento, cai em
  "Sem tipo de estabelecimento".
- Categoria excluída depois que um item já foi somado num resumo de mês passado: como a soma é
  recalculada sob demanda a partir do estado atual de itens/notas/categoria (não é um valor
  congelado), o resumo de um mês passado reflete o estado atual da taxonomia, não um "retrato"
  histórico da categoria como ela era quando a nota foi importada.
- Uma categoria usada como tipo de estabelecimento (nota) e uma categoria usada como categoria
  de item (item) podem coexistir no mesmo mecanismo de taxonomia sem conflito, pois
  `nota_fiscal.categoria_id` e `item_nota.categoria_id` são colunas/atribuições
  independentes — nada impede reaproveitar valores de nome parecido nos dois eixos, mas os
  dois eixos nunca se misturam num mesmo gráfico.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST calcular o gasto por categoria de item de um mês somando o valor
  dos itens classificados (com categoria preenchida) das notas emitidas naquele mês, agrupado
  pela categoria do item.
- **FR-002**: O sistema MUST, para uma nota que não tenha nenhum item com categoria
  preenchida, atribuir o valor total dessa nota à categoria da própria nota
  (`nota_fiscal.categoria_id`) no resumo mensal — mantendo o comportamento já existente da
  feature 005 como respaldo.
- **FR-003**: O sistema MUST, para uma nota que tenha ao menos um item classificado, tratar os
  itens ainda sem categoria (pendentes) dessa mesma nota como "Sem categoria" no resumo — sem
  atribuí-los à categoria da nota.
- **FR-004**: O sistema MUST permitir navegação entre meses com notas registradas a partir do
  resumo, incluindo uma forma direta de retornar ao mês mais recente com nota.
- **FR-005**: O sistema MUST indicar visualmente, a qualquer momento no resumo, qual mês está
  sendo exibido.
- **FR-006**: O sistema MUST oferecer, a partir do resumo de um mês, uma ação que leve à
  página de listagem de notas (`/ver/notas`) já filtrada por aquele mês (e pelo tipo de
  estabelecimento, quando a fatia clicada for de uma visão por estabelecimento), sem exigir
  que o usuário reconfigure o filtro manualmente.
- **FR-007**: O sistema MUST apresentar a listagem de notas (`/ver/notas`) agrupada
  visualmente por mês como modo de exibição padrão (sem exigir seleção prévia de um filtro de
  mês), com o mês mais recente primeiro.
- **FR-008**: O sistema MUST continuar permitindo filtrar a listagem de notas por mês e por
  titular, preservando o comportamento já existente das features 001/004, em conjunto com o
  agrupamento por mês da FR-007 (ao aplicar um filtro de mês específico, a página passa a
  mostrar apenas aquele grupo).
- **FR-009**: O sistema MUST permitir alternar, na visão por categoria do item, entre nível 1
  (categoria de topo, ex.: Alimentação, Bebidas, Pets) e nível 2 (subcategoria, ex.: Alimentos
  pré-processados, Biscoitos, Lanche, Rotisserie, Sucos e isotônicos, Itens diversos).
- **FR-010**: O sistema MUST tratar a categoria já atribuída à nota (`nota_fiscal.categoria_id`)
  como representando o **tipo de estabelecimento** onde a compra foi feita (ex.: Supermercado,
  Mercearia, Restaurante, Bar, Farmácia, Pet Shop, Saúde), um eixo independente da categoria do
  item — reaproveitando o mesmo mecanismo de categoria de dois níveis já usado pelos itens
  (feature 008), incluindo subcategorias (ex.: Saúde › Dentista, Saúde › Plano de Saúde).
- **FR-011**: O sistema MUST permitir, no resumo mensal, selecionar a visão por tipo de
  estabelecimento, por categoria do item, ou ambas simultaneamente, sem exigir reconfigurar o
  mês selecionado ao trocar de visão.
- **FR-012**: O sistema MUST permitir revisar/expandir a taxonomia de tipo de estabelecimento
  (criar novas categorias e subcategorias de estabelecimento) e reclassificar notas
  existentes, reaproveitando o mecanismo de gestão de categorias e o histórico de auditoria já
  existentes (features 003/008) — sem exigir uma ferramenta nova dedicada a esse fim.

### Key Entities

- **Categoria (existente)**: mesmo mecanismo de dois níveis (categoria-pai/subcategoria) já
  usado pela feature 008, agora reconhecido explicitamente como servindo dois eixos
  independentes de classificação: **categoria do item** (o que foi comprado, via
  `item_nota.categoria_id`) e **tipo de estabelecimento** (onde a compra foi feita, via
  `nota_fiscal.categoria_id`). Os dois eixos podem usar a mesma tabela/mecanismo de categoria
  sem risco de mistura, pois cada um é referenciado por uma coluna distinta.
- **Resumo mensal (conceito de leitura, não uma tabela nova)**: um agregado calculado sob
  demanda a partir dos itens e notas do mês selecionado, com três recortes possíveis
  (categoria do item nível 1, categoria do item nível 2, tipo de estabelecimento) — não é um
  dado persistido/congelado (ver Edge Cases sobre categoria excluída depois).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O gasto mensal exibido no resumo reflete a categoria real dos itens para 100%
  das notas com pelo menos um item classificado (não fica mais preso à categoria única da
  nota nesses casos).
- **SC-002**: O usuário consegue navegar de um mês para outro (adjacente ou para o mês mais
  recente) em uma única ação, sem precisar reconfigurar filtros manualmente.
- **SC-003**: O usuário consegue sair de um número do resumo de um mês (categoria do item ou
  tipo de estabelecimento) e chegar à lista das notas correspondentes em uma única ação.
- **SC-004**: O usuário consegue identificar visualmente a que mês uma nota pertence na
  listagem de notas sem precisar abrir/ler a data de cada linha individualmente.
- **SC-005**: A página de resumo passa por verificação visual real (captura de tela +
  ausência de erro de console) e é aprovada pelo usuário como tendo aparência profissional de
  relatório financeiro, substituindo o layout atual.
- **SC-006**: O usuário consegue alternar entre visão por categoria do item (nível 1 ou 2) e
  visão por tipo de estabelecimento — ou ver ambas juntas — sem perder o mês selecionado.

## Assumptions

- Meses sem nenhuma nota registrada não são oferecidos como destino navegável no resumo (não
  há necessidade de "criar" uma tela vazia para um mês sem dado) — se o usuário precisar
  confirmar a ausência de notas num mês específico, isso continua acessível pela listagem de
  notas com filtro manual de mês, mesmo que esse mês não apareça na navegação rápida do
  resumo.
- O redesign visual do resumo reaproveita a mesma stack já usada no projeto (Jinja2
  renderizado no servidor, Plotly para gráficos, tema Argon já vendorizado) — não introduz
  nenhuma biblioteca de frontend nova nem asset de terceiro novo (Princípio I, Princípio VIII).
- A navegação por mês (FR-004) cobre os meses que têm pelo menos uma nota — o "mês corrente"
  continua sendo sempre acessível mesmo sem nota (comportamento parcial já existente da
  feature 005), para o usuário confirmar que ainda não há gasto registrado no mês em curso.
- "Sem categoria" (item) e "Sem tipo de estabelecimento" (nota) continuam sendo fatias
  próprias e sempre visíveis nos respectivos gráficos (nunca escondidas), consistente com a
  decisão já tomada na feature 005.
- O agrupamento por mês da listagem de notas (FR-007) substitui a tabela plana atual como
  modo de exibição padrão — não é um modo alternativo opcional — mantendo os filtros
  existentes (mês, titular) como forma de restringir a visão dentro desse novo agrupamento.
- A revisão da taxonomia de tipo de estabelecimento (US6/FR-012) reaproveita a tela/mecanismo
  de gestão de categorias já existente (feature 008, `/categorias`) — não é necessário um
  documento de revisão em lote como o usado na feature 008 para itens, dado que o volume de
  notas a reclassificar é muito menor que o volume de itens.
- A visão "ambas simultaneamente" (FR-011) exibe os dois gráficos (por item e por
  estabelecimento) lado a lado ou empilhados na mesma tela de resumo do mês, sem necessidade
  de rolagem horizontal (respeitando a diretriz de responsividade já seguida no projeto).
