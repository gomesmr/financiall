# Feature Specification: CRUD de Categorias

**Feature Branch**: `003-categorias-crud`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: "CRUD de categorias para o financiALL: permitir criar, listar, editar e excluir categorias de gasto, e atribuir uma categoria a cada nota fiscal já importada. Granularidade por nota inteira neste ciclo (não por item — item fica como horizonte futuro). Atribuição de categoria é manual pela UI neste ciclo (sem motor de regras/IA automático). Esta spec é só o CRUD de categorias e a atribuição manual — a importação do histórico financeiro antigo é uma feature separada."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Criar uma categoria nova (Priority: P1)

Como usuário, quero criar uma categoria de gasto (ex.: "Alimentação", "Transporte") para poder organizar minhas notas fiscais por tipo de despesa.

**Why this priority**: sem categorias existentes, nenhuma outra parte da feature funciona — é o alicerce de tudo.

**Independent Test**: criar uma categoria pela UI e verificar que ela aparece imediatamente na lista de categorias disponíveis.

**Acceptance Scenarios**:

1. **Given** nenhuma categoria com aquele nome existe, **When** o usuário informa um nome e confirma a criação, **Then** a categoria passa a existir e aparece na lista de categorias.
2. **Given** já existe uma categoria com o mesmo nome (ignorando maiúsculas/minúsculas e espaços nas pontas), **When** o usuário tenta criar outra com o mesmo nome, **Then** o sistema recusa e explica que o nome já está em uso.
3. **Given** o usuário não informa nenhum nome (ou só espaços), **When** ele confirma a criação, **Then** o sistema recusa e pede um nome válido.

---

### User Story 2 - Atribuir categoria a uma nota fiscal (Priority: P1)

Como usuário, na tela de detalhe de uma nota fiscal já importada, quero escolher a categoria que melhor representa aquele gasto, para poder acompanhar meus gastos por categoria.

**Why this priority**: é o valor central pedido — categorizar os gastos já registrados. Depende de já existir ao menos uma categoria (US1), mas é o motivo de toda a feature existir.

**Independent Test**: com ao menos uma categoria criada, abrir o detalhe de uma nota, escolher uma categoria, salvar, e verificar que a nota passa a exibir aquela categoria.

**Acceptance Scenarios**:

1. **Given** uma nota sem categoria atribuída e ao menos uma categoria existente, **When** o usuário escolhe uma categoria e confirma, **Then** a nota passa a exibir essa categoria.
2. **Given** uma nota que já tem uma categoria atribuída, **When** o usuário escolhe uma categoria diferente e confirma, **Then** a categoria da nota é substituída pela nova escolha (nunca duplica).
3. **Given** uma nota com categoria atribuída, **When** o usuário escolhe a opção "sem categoria" e confirma, **Then** a nota volta a não ter categoria.

---

### User Story 3 - Ver todas as categorias existentes (Priority: P2)

Como usuário, quero ver a lista de todas as categorias que já criei, para saber quais já existem antes de criar uma nova e ter uma visão geral.

**Why this priority**: apoia US1/US2, mas o sistema já entrega valor sem uma tela dedicada (o seletor de categoria já mostra as opções). Sem ela, o usuário só perde visibilidade e corre mais risco de criar duplicatas por engano.

**Independent Test**: com duas ou mais categorias criadas, acessar a tela de categorias e verificar que todas aparecem.

**Acceptance Scenarios**:

1. **Given** existem categorias criadas, **When** o usuário acessa a tela de categorias, **Then** vê todas elas listadas.
2. **Given** nenhuma categoria foi criada ainda, **When** o usuário acessa a tela de categorias, **Then** vê uma mensagem indicando que não há categorias, com um caminho claro para criar a primeira.

---

### User Story 4 - Editar o nome de uma categoria (Priority: P2)

Como usuário, quero corrigir ou renomear uma categoria já criada (ex.: corrigir um erro de digitação), sem perder as notas já atribuídas a ela.

**Why this priority**: melhora a qualidade dos dados ao longo do tempo, mas não bloqueia o uso básico — na pior hipótese o usuário convive com um nome errado por mais tempo.

**Independent Test**: editar o nome de uma categoria que já tem notas atribuídas e verificar que o novo nome aparece tanto na lista de categorias quanto nas notas que a usavam.

**Acceptance Scenarios**:

1. **Given** uma categoria existente, **When** o usuário edita o nome para um valor novo e válido, **Then** a categoria passa a ter o novo nome em todos os lugares onde aparece, incluindo notas já atribuídas a ela.
2. **Given** uma categoria existente, **When** o usuário tenta editar o nome para um nome já usado por outra categoria, **Then** o sistema recusa e explica o motivo.

---

### User Story 5 - Excluir uma categoria (Priority: P3)

Como usuário, quero excluir uma categoria que criei por engano ou que não faz mais sentido, sem que isso quebre as notas que já usavam essa categoria.

**Why this priority**: é um caso de limpeza — útil, mas o usuário consegue conviver com uma categoria "sobrando" sem perda funcional por um bom tempo.

**Independent Test**: excluir uma categoria que tem notas atribuídas, confirmar a exclusão, e verificar que essas notas passam a aparecer como "sem categoria", sem erro.

**Acceptance Scenarios**:

1. **Given** uma categoria sem nenhuma nota atribuída, **When** o usuário a exclui e confirma, **Then** ela deixa de existir na lista de categorias.
2. **Given** uma categoria com notas atribuídas, **When** o usuário a exclui e confirma, **Then** ela deixa de existir e as notas que a usavam passam a aparecer como "sem categoria", sem erro.
3. **Given** o usuário aciona a exclusão, **When** ele cancela a confirmação, **Then** nada muda.

---

### Edge Cases

- Nome de categoria duplicado (comparação insensível a maiúsculas/minúsculas e espaços nas pontas) é recusado tanto na criação quanto na edição.
- Nota fiscal sem categoria atribuída — seja porque nunca recebeu uma, seja porque a categoria que usava foi excluída — é um estado válido e esperado, exibido como "sem categoria", nunca um erro.
- Categoria com nome vazio ou só espaços é recusada, tanto ao criar quanto ao editar.
- Excluir uma categoria enquanto ela está selecionada em outra tela/aba não deve travar a navegação do usuário nessa outra tela.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir criar uma categoria nova informando um nome.
- **FR-002**: O sistema MUST impedir a criação de duas categorias com o mesmo nome (comparação insensível a maiúsculas/minúsculas e espaços nas pontas), explicando o motivo da recusa.
- **FR-003**: O sistema MUST exibir a lista de todas as categorias existentes.
- **FR-004**: O sistema MUST permitir editar o nome de uma categoria existente, aplicando a mesma regra de nome único do FR-002.
- **FR-005**: O sistema MUST permitir excluir uma categoria existente, mediante confirmação explícita do usuário.
- **FR-006**: Ao excluir uma categoria que tinha notas atribuídas, o sistema MUST desassociar essas notas (elas passam a "sem categoria") em vez de bloquear a exclusão ou deixar referência quebrada.
- **FR-007**: O sistema MUST permitir que o usuário atribua, a partir da tela de detalhe da nota, uma categoria dentre as existentes a qualquer nota fiscal já importada.
- **FR-008**: O sistema MUST permitir trocar a categoria atribuída a uma nota por outra, ou remover a atribuição (voltar a "sem categoria").
- **FR-009**: O sistema MUST exibir a categoria atribuída (ou "sem categoria") tanto na listagem de notas quanto na tela de detalhe da nota.
- **FR-010**: O sistema MUST recusar a criação ou edição de uma categoria com nome vazio ou composto só por espaços.

### Key Entities

- **Categoria**: representa um tipo de gasto (ex.: Alimentação, Transporte, Saúde). Tem um nome único. É criada, listada, editada e excluída nesta feature.
- **Nota Fiscal** (já existente, feature 001): ganha uma associação opcional a uma Categoria — no máximo uma categoria por nota neste ciclo (granularidade de nota inteira, não por item).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O usuário consegue criar uma categoria nova em menos de 15 segundos.
- **SC-002**: O usuário consegue atribuir uma categoria a uma nota em até 3 interações (abrir a nota, escolher a categoria, confirmar).
- **SC-003**: 100% das notas exibem corretamente sua categoria (ou "sem categoria") em qualquer tela que mostre notas.
- **SC-004**: Excluir uma categoria em uso nunca resulta em erro ou navegação quebrada para o usuário.
- **SC-005**: Tentar criar (ou renomear para) um nome de categoria já existente é recusado em 100% dos casos, com mensagem clara.

## Assumptions

- Granularidade da categoria é por nota inteira neste ciclo; categorização por item fica para uma evolução futura — o modelo de dados desta feature não deve impedir essa evolução, mas implementá-la está fora de escopo.
- Atribuição de categoria é sempre manual nesta feature; um motor de sugestão automática (regra/IA) fica para um ciclo futuro.
- Excluir uma categoria em uso desassocia as notas (elas voltam a "sem categoria") em vez de bloquear a exclusão — prioriza simplicidade e evita que o usuário fique impedido de limpar categorias antigas.
- Nome de categoria é único no sistema (sem duplicatas, comparação insensível a maiúsculas/minúsculas e espaços nas pontas).
- Cor/ícone de categoria fica fora deste ciclo — uma futura feature de gráficos pode atribuir cor visualmente sem exigir esse dado persistido agora.
- Importação do histórico financeiro anterior (categorias herdadas de outro sistema) é uma feature separada, fora deste escopo.
- Não há limite de quantidade de categorias nem hierarquia entre elas (sem categorias "pai/filho") neste ciclo.
- Não há diferenciação de permissões entre usuários (Marcelo/Cristine) para gerenciar categorias — consistente com a decisão de não ter autenticação no sistema (mesma suposição da feature 002).
