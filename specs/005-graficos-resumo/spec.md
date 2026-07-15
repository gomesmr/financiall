# Feature Specification: Gráficos no Resumo de Gastos

**Feature Branch**: `005-graficos-resumo`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: "Gráficos no resumo de gastos: adicionar visualizações gráficas (pizza e barras) à página de resumo já existente, que hoje só mostra números em tabela. Gráfico de pizza mostrando a distribuição do gasto por categoria (do mês corrente, e possivelmente de um mês selecionado do histórico); gráfico de barras mostrando a evolução do gasto mês a mês. Notas sem categoria atribuída devem aparecer como fatia própria 'Sem categoria', não ser omitidas. Sem filtro por titular nesta feature."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver a distribuição do gasto do mês por categoria (Priority: P1)

Como usuário, ao abrir o resumo, quero ver um gráfico de pizza mostrando quanto gastei em cada categoria no mês corrente, para entender de forma visual e imediata onde meu dinheiro está indo, sem precisar somar números manualmente.

**Why this priority**: é o pedido central que motivou a feature — visualizar o gasto por categoria é o valor que os números em tabela sozinhos não entregam.

**Independent Test**: com notas categorizadas no mês corrente, abrir `/ver/resumo` e verificar que o gráfico de pizza mostra uma fatia por categoria, proporcional ao gasto de cada uma.

**Acceptance Scenarios**:

1. **Given** o mês corrente tem notas em duas ou mais categorias diferentes, **When** o usuário abre o resumo, **Then** o gráfico de pizza mostra uma fatia por categoria, com tamanho proporcional ao valor gasto nela.
2. **Given** existem notas do mês corrente sem categoria atribuída, **When** o usuário abre o resumo, **Then** essas notas aparecem juntas numa fatia própria chamada "Sem categoria", nunca ficam de fora do gráfico.
3. **Given** o usuário passa o mouse (ou toca) numa fatia do gráfico, **When** ele interage com ela, **Then** vê o nome da categoria e o valor exato gasto nela.

---

### User Story 2 - Ver a evolução do gasto mês a mês (Priority: P1)

Como usuário, quero ver um gráfico de barras com o total gasto em cada mês do meu histórico, para comparar visualmente períodos diferentes sem precisar ler uma tabela de números.

**Why this priority**: mesmo peso do pedido original do usuário — é a segunda visualização central pedida, complementar à primeira (uma mostra "onde", a outra mostra "quando").

**Independent Test**: com notas em pelo menos três meses diferentes, abrir `/ver/resumo` e verificar que o gráfico de barras mostra uma barra por mês, com altura proporcional ao total gasto.

**Acceptance Scenarios**:

1. **Given** existem notas em vários meses do histórico, **When** o usuário abre o resumo, **Then** o gráfico de barras mostra uma barra por mês, na mesma cobertura de período já exibida na tabela de "Meses anteriores".
2. **Given** o usuário passa o mouse (ou toca) numa barra, **When** ele interage com ela, **Then** vê o mês e o valor total exato gasto naquele mês.

---

### User Story 3 - Ver a distribuição por categoria de um mês específico do histórico (Priority: P2)

Como usuário, quero escolher um mês passado (não só o corrente) e ver o gráfico de pizza da distribuição por categoria daquele mês, para entender como meus gastos por categoria mudaram ao longo do tempo.

**Why this priority**: estende o valor da US1 para o histórico, mas o sistema já entrega valor real só com o mês corrente (US1) — esta história é um refinamento, não um bloqueio.

**Independent Test**: escolher um mês do histórico (diferente do corrente) e verificar que o gráfico de pizza passa a refletir a distribuição por categoria daquele mês escolhido.

**Acceptance Scenarios**:

1. **Given** o usuário está vendo o gráfico de pizza do mês corrente, **When** ele escolhe um mês diferente do histórico, **Then** o gráfico de pizza passa a mostrar a distribuição por categoria daquele mês escolhido.
2. **Given** o mês escolhido não tem nenhuma nota com valor gasto, **When** o gráfico de pizza tenta ser exibido, **Then** o usuário vê uma mensagem clara ("nenhum gasto neste mês") em vez de um gráfico vazio ou quebrado.

---

### Edge Cases

- Mês (corrente ou selecionado) sem nenhuma nota com valor: gráfico de pizza exibe mensagem clara em vez de tentar desenhar um gráfico vazio.
- Todas as notas do mês selecionado estão sem categoria: o gráfico de pizza mostra uma única fatia "Sem categoria" (100%), não um gráfico vazio.
- Nota com valor total ausente (dado incompleto, "pendente de revisão"): não entra na soma de nenhum gráfico, mesma regra já aplicada ao resumo em texto hoje.
- Muitos meses no histórico: o gráfico de barras cobre a mesma janela de tempo já mostrada na tabela existente, sem paginação nova.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST exibir, na página de resumo, um gráfico de pizza com a distribuição do gasto do mês corrente por categoria.
- **FR-002**: Notas sem categoria atribuída MUST aparecer como uma fatia própria chamada "Sem categoria" no gráfico de pizza, nunca omitidas do total.
- **FR-003**: O sistema MUST exibir, na página de resumo, um gráfico de barras com o total gasto em cada mês do histórico já disponível (mesma cobertura da tabela "Meses anteriores" existente).
- **FR-004**: O usuário MUST poder escolher um mês do histórico (além do corrente) para ver a distribuição por categoria daquele mês no gráfico de pizza.
- **FR-005**: Quando não há nenhuma nota com valor gasto no mês exibido no gráfico de pizza, o sistema MUST mostrar uma mensagem clara em vez de um gráfico vazio ou quebrado.
- **FR-006**: Os valores exibidos nos gráficos MUST corresponder exatamente aos valores já exibidos em texto na página de resumo (nunca divergir do total).
- **FR-007**: Interagir com uma fatia do gráfico de pizza ou uma barra do gráfico de barras (mouse ou toque) MUST exibir o valor exato correspondente (categoria+valor, ou mês+valor).

### Key Entities

- **Gasto por Categoria** (agregação derivada, não uma tabela nova): soma do valor das notas de um mês, agrupada por categoria (incluindo o agrupamento "Sem categoria"). Calculada a partir das notas e categorias já existentes (features 001/003).
- **Gasto Mensal** (já existente no resumo em texto): total gasto por mês — os gráficos de barras visualizam esse dado já calculado, sem alterar como ele é apurado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O usuário identifica visualmente a categoria de maior gasto do mês em poucos segundos, sem precisar somar números manualmente.
- **SC-002**: O usuário compara visualmente o gasto de dois meses diferentes olhando o gráfico de barras, sem fazer nenhum cálculo.
- **SC-003**: A soma das fatias do gráfico de pizza de qualquer mês bate exatamente com o total daquele mês já exibido em texto.
- **SC-004**: O usuário consegue ver a distribuição por categoria de qualquer mês do histórico disponível, não só do mês corrente.

## Assumptions

- Os gráficos usam a categoria já atribuída à nota inteira (granularidade de nota, mesma da feature 003) — categorização por item está fora de escopo aqui, como já decidido antes.
- Sem filtro por titular nesta feature (decisão já tomada) — os gráficos sempre mostram o total agregado de todos os titulares, mesmo comportamento do resumo em texto atual.
- Categorias com fatia muito pequena não são agrupadas automaticamente em "outros" neste ciclo — aparecem individualmente; pode ser revisitado se a quantidade de categorias tornar o gráfico poluído na prática.
- O gráfico de barras cobre a mesma janela de meses já calculada pela funcionalidade de histórico existente — não introduz um período diferente nem paginação nova.
- "Bonito" é interpretado como: cores distintas e legíveis por categoria, legendas claras e um layout que cabe bem na tela — não exige um redesenho visual completo da aplicação (isso é escopo de uma feature futura separada, revisão visual).
