# Feature Specification: Revisão Visual do Layout

**Feature Branch**: `006-revisao-visual-layout`

**Created**: 2026-07-16

**Status**: Draft

**Input**: User description: "Revisão visual do layout: o front do financiALL hoje é HTML puro sem framework de estilo, funcional mas visualmente pobre. Adotar a 'pele' do template Argon Dashboard Flask (assets visuais vendorizados localmente + estrutura HTML como partials Jinja), mantendo 100% do Flask/blueprints/rotas/sqlite atuais intactos. Todas as páginas existentes ganham o novo visual e viram responsivas. Não é escopo mudar nenhuma lógica de negócio, rota, ou comportamento funcional já existente."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver um visual mais profissional nas páginas principais (Priority: P1)

Como usuário, quero que as páginas do financiALL (Importar, Notas, Categorias, Resumo) tenham uma aparência mais profissional e organizada, para ter uma experiência mais agradável de usar no dia a dia — sem que isso afete nenhuma funcionalidade que já uso.

**Why this priority**: é o pedido central da feature — a aparência atual é funcional mas pobre, e é o motivo direto de abrir esta feature.

**Independent Test**: abrir cada página existente e verificar que ela usa o novo visual (navegação clara, cards, tabelas estilizadas) e que toda ação que já funcionava antes (importar, listar, editar, excluir) continua funcionando exatamente igual.

**Acceptance Scenarios**:

1. **Given** o usuário abre qualquer página já existente (Importar, Notas, detalhe de Nota, Categorias, Resumo), **When** a página carrega, **Then** ela usa o novo visual, com a mesma navegação principal reconhecível em todas.
2. **Given** o usuário realiza qualquer ação que já existia antes desta feature (ex.: importar nota, excluir nota, criar categoria, atribuir categoria), **When** ele completa a ação, **Then** o resultado é exatamente o mesmo de antes — só a aparência mudou.

---

### User Story 2 - Usar a aplicação a partir do celular (Priority: P1)

Como usuário, quero conseguir usar o financiALL confortavelmente pelo celular — principalmente para enviar foto de cupom fiscal, que já faço direto do celular — sem precisar dar zoom ou lidar com um layout quebrado.

**Why this priority**: mesmo peso do pedido original ("garantir a responsividade") — parte real do fluxo de uso já acontece no celular, então um visual bonito só no desktop não resolveria o problema todo.

**Independent Test**: abrir cada página existente numa tela estreita (celular) e verificar que o conteúdo se ajusta, sem exigir zoom nem gerar rolagem horizontal da página inteira.

**Acceptance Scenarios**:

1. **Given** o usuário acessa qualquer página do financiALL por um celular, **When** a página carrega, **Then** todo o conteúdo é legível e utilizável sem precisar dar zoom.
2. **Given** uma tabela com muitas colunas (ex.: listagem de notas), **When** exibida numa tela estreita, **Then** a tabela permite rolagem horizontal dentro dela mesma, sem que o restante da página vaze ou quebre.
3. **Given** o usuário está na tela de importar por foto, **When** ele acessa pelo celular, **Then** consegue enviar a foto do cupom sem dificuldade adicional causada pelo novo layout.

---

### User Story 3 - Gráficos continuam corretos dentro do novo visual (Priority: P2)

Como usuário, quero que os gráficos de pizza e barras do resumo (feature 005) continuem mostrando as informações certas, com as mesmas cores, depois da mudança visual — para não perder a clareza que acabei de ganhar.

**Why this priority**: é um risco de regressão concreto (gráficos são sensíveis a CSS externo, largura de container, etc.), mas o valor central da feature (US1/US2) já se sustenta mesmo que este ponto precise de um ajuste fino depois.

**Independent Test**: abrir a página de resumo antes e depois da mudança visual e conferir que os mesmos valores, cores e legendas aparecem, sem sobreposição ou corte.

**Acceptance Scenarios**:

1. **Given** a página de resumo com o novo visual, **When** o usuário a abre, **Then** o gráfico de pizza e o gráfico de barras aparecem completos, com os mesmos valores e cores de antes, sem sobreposição entre eles ou com outros elementos da página.
2. **Given** o usuário muda entre modo claro e escuro do sistema, **When** a página de resumo é exibida, **Then** o restante da página permanece legível (sem elemento invisível ou ilegível), ainda que o tema escuro completo do novo visual não seja o foco desta feature.

---

### Edge Cases

- Tela muito estreita (celular pequeno) não pode ter menu/navegação cobrindo o conteúdo principal.
- Nenhum formulário existente (importar por URL/chave, upload de foto, criar/editar categoria) pode perder um campo ou botão por causa do novo layout.
- Ações destrutivas (excluir nota, excluir categoria) continuam exigindo confirmação explícita antes de executar, como já garantido nas features anteriores — o novo visual não pode remover nem esconder essa confirmação.
- A aplicação continua carregando por completo (visual e funcionalmente) mesmo sem acesso à internet, já que roda num Raspberry Pi que pode ficar offline.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Todas as páginas já existentes (Importar, Notas, detalhe de Nota, Categorias, Resumo, status de envio) MUST usar o novo visual, sem exceção.
- **FR-002**: Nenhuma funcionalidade já existente MUST deixar de funcionar por causa da mudança visual — inclui importar (URL/chave e foto/PDF), listar e filtrar notas, excluir nota, criar/editar/excluir categoria, atribuir categoria a nota, e ver os gráficos de resumo.
- **FR-003**: Todas as páginas MUST ser usáveis numa tela de celular, sem exigir zoom nem gerar rolagem horizontal da página inteira.
- **FR-004**: Tabelas com muitas colunas MUST permitir rolagem horizontal dentro delas mesmas em telas estreitas, em vez de vazar ou quebrar o layout da página.
- **FR-005**: Os gráficos de pizza e barras (feature 005) MUST continuar exibindo os mesmos valores e a mesma paleta de cores validada, sem sobreposição, dentro do novo layout.
- **FR-006**: Ações destrutivas (excluir nota, excluir categoria) MUST continuar exigindo confirmação explícita do usuário antes de executar.
- **FR-007**: A aplicação MUST continuar carregando e funcionando por completo sem depender de acesso à internet.

### Key Entities

Nenhuma — feature puramente de apresentação, sem entidade de dado nova nem alteração em entidade existente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O usuário completa o fluxo de enviar uma foto de cupom fiscal pelo celular sem precisar dar zoom ou rolar a tela na horizontal.
- **SC-002**: 100% das páginas existentes carregam com o novo visual e nenhuma ação que já funcionava antes passa a falhar (checklist de regressão completo).
- **SC-003**: Os gráficos do resumo exibem exatamente os mesmos valores e cores de antes da mudança visual, em qualquer tela testada (desktop e celular).
- **SC-004**: A aplicação carrega e funciona por completo mesmo com o Raspberry Pi sem acesso à internet no momento do acesso.

## Assumptions

- "Pele" Argon Dashboard Flask significa vendorizar localmente os assets visuais já compilados (CSS/JS/fontes prontos) e a estrutura HTML (navegação, cards, tabelas estilizadas) como partials Jinja — não inclui o esqueleto de aplicação Flask do template original (autenticação, models próprios), só a camada visual, decisão já alinhada com o usuário antes desta spec.
- Nenhuma rota, campo de banco ou regra de negócio muda nesta feature — é puramente visual/estrutural de apresentação, reaproveitando 100% do backend já existente.
- Modo escuro: os gráficos já respeitam a preferência do sistema (feature 005); esta feature garante que o restante da página não fica ilegível ou quebrado em modo escuro, mas um tema escuro completo e refinado do novo visual não é garantia deste ciclo — pode ser evolução futura.
- A navegação principal (Importar / Notas / Categorias / Resumo) continua com as mesmas quatro seções de hoje, só reorganizada visualmente (ex.: como menu lateral em vez de barra horizontal).
- Sem identidade visual de marca própria definida ainda — o visual desta feature usa as cores/estilo padrão do template escolhido, sem customização de marca própria neste ciclo.
- Licença do template (versão gratuita) permite uso e vendorização local sem custo — confirmado durante o planejamento técnico, antes de baixar qualquer asset.
