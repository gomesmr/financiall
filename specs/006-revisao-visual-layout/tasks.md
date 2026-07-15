---

description: "Task list for feature 006 — Revisão Visual do Layout"
---

# Tasks: Revisão Visual do Layout

**Input**: Design documents from `/specs/006-revisao-visual-layout/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui.md, quickstart.md

**Tests**: Nenhum teste automatizado novo é esperado (FR-002, contracts/ui.md — nenhum
contrato de API muda). A suíte já existente (`tests/unit`, `tests/integration`,
`tests/contract`) serve de rede de segurança de regressão; rodá-la é uma tarefa de
validação (Fase final), não uma tarefa de escrita de teste.

**Real-Data Validation**: Não se aplica (Constitution Check da plan.md, Princípio V) —
feature puramente de apresentação, sem processamento de dado de origem externa.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: US1, US2 ou US3 conforme spec.md

## Path Conventions

Projeto único: `src/api/templates/`, `src/api/static/`, `tests/` na raiz do repo.

---

## Phase 1: Setup

**Purpose**: Obter e vendorizar localmente os assets do Argon Dashboard antes de
qualquer adaptação de template.

- [X] T001 Pedir aprovação explícita do usuário sobre a URL exata de download dos
      assets do Argon Dashboard (`creativetimofficial/argon-dashboard`, produto HTML
      puro, MIT — research.md #1/#3), seguindo o mesmo processo já usado para o
      Plotly.js na feature 005 (classificador de segurança bloqueia download de código
      de fonte não nomeada explicitamente pelo usuário)
- [X] T002 Baixar e vendorizar os assets pré-compilados em
      `src/api/static/argon/`: `css/argon-dashboard.min.css`,
      `js/argon-dashboard.min.js`, `fonts/` (ícones Nucleo + webfonts), `img/`
      (imagens do template, se usadas), e `ARGON.LICENSE` (cópia da licença MIT do
      repositório de origem) — sem `assets/scss/` (fonte, exigiria build)
- [X] T003 [P] Verificar a integridade dos assets baixados: confirmar que vieram do
      produto HTML puro (não da edição "Flask" com esqueleto de app), que
      `ARGON.LICENSE` está presente, e remover qualquer scaffolding de build
      (Node/Gulp/`package.json`) que não seja necessário (Princípio I — mesmo cuidado
      já exigido na feature 005 com o `node_modules/` acidental do Plotly)

**Checkpoint**: Assets do Argon disponíveis localmente em `src/api/static/argon/`,
sem dependência de CDN nem de build step.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Reestruturar o layout base (menu lateral + navbar) do qual todas as
páginas herdam, antes de adaptar qualquer página individual.

**⚠️ CRITICAL**: Nenhuma adaptação de página (Fase 3+) pode começar antes desta fase
estar completa.

- [X] T004 Reestruturar `src/api/templates/base.html` para o layout padrão do Argon
      Dashboard (menu lateral fixo/recolhível + navbar superior — research.md #4),
      referenciando os assets vendorizados via `url_for('static', ...)`, mantendo as
      mesmas 4 seções de navegação (Importar, Notas, Categorias, Resumo) e uma marcação
      de página ativa equivalente à classe `.ativo` já usada hoje (contracts/ui.md)
- [X] T005 Garantir meta tag de viewport (`<meta name="viewport" ...>`) em
      `src/api/templates/base.html` como base para a responsividade exigida em US2
- [X] T006 Rodar a suíte de testes existente
      (`pytest tests/unit tests/integration tests/contract`) para confirmar que a
      reestruturação de `base.html` não quebrou nenhuma rota ou contrato antes de
      seguir para a adaptação página a página

**Checkpoint**: Layout base pronto — adaptação individual das páginas pode começar.

---

## Phase 3: User Story 1 - Ver um visual mais profissional nas páginas principais (Priority: P1) 🎯 MVP

**Goal**: Todas as páginas existentes usam o novo visual (cards, tabelas estilizadas,
navegação clara), sem perder nenhuma funcionalidade já existente.

**Independent Test**: Abrir cada página existente e verificar que usa o novo visual e
que toda ação que já funcionava antes continua funcionando exatamente igual.

### Implementation for User Story 1

- [X] T007 [P] [US1] Adaptar `src/api/templates/upload.html` para card de formulário
      do Argon (data-model.md), preservando todos os campos/botões e o JS já
      existente
- [X] T008 [P] [US1] Adaptar `src/api/templates/notas.html` para card com tabela
      estilizada do Argon, preservando as variáveis `notas`, `categorias_por_id`,
      `titular_filtro` e o JS de `fetch`/`confirm()` já existente
- [X] T009 [P] [US1] Adaptar `src/api/templates/nota_detalhe.html` para card de
      detalhe + tabela de itens do Argon, preservando as variáveis `nota`, `itens`,
      `categorias` e o JS já existente
- [X] T010 [P] [US1] Adaptar `src/api/templates/categorias.html` para card com
      tabela + formulário inline do Argon, preservando a variável `categorias` e o
      JS de CRUD já existente
- [X] T011 [P] [US1] Adaptar `src/api/templates/resumo.html` para cards de estatística
      do Argon (mês corrente, histórico), preservando as variáveis `mes_corrente`,
      `historico`, `historico_json`, `meses_disponiveis` e sem alterar o JS/script de
      montagem dos gráficos Plotly (isso é tratado especificamente em US3)
- [X] T012 [P] [US1] Adaptar `src/api/templates/envio.html` para card de status
      simples do Argon, preservando as variáveis `envio`, `nota`, `itens`
- [X] T013 [US1] Checklist de regressão manual (quickstart.md §2) nas 6 páginas:
      navegação principal reconhecível com marcador de página ativa, e toda ação já
      existente (importar por URL/chave, importar por foto, excluir nota,
      criar/editar/excluir categoria, atribuir categoria, filtrar por mês/titular)
      continua funcionando — depende de T007-T012

**Checkpoint**: Todas as páginas usam o novo visual; toda funcionalidade já existente
validada manualmente sem regressão.

---

## Phase 4: User Story 2 - Usar a aplicação a partir do celular (Priority: P1)

**Goal**: Todas as páginas são usáveis confortavelmente numa tela de celular, sem
zoom nem rolagem horizontal da página inteira.

**Independent Test**: Abrir cada página numa tela estreita (celular) e verificar que
o conteúdo se ajusta, sem exigir zoom nem gerar rolagem horizontal da página inteira.

### Implementation for User Story 2

- [X] T014 [US2] Envolver as tabelas largas de `src/api/templates/notas.html` e
      `src/api/templates/nota_detalhe.html` num container de rolagem horizontal
      própria (ex.: `.table-responsive` do Bootstrap 5/Argon — FR-004), para que a
      tabela role dentro de si mesma em telas estreitas em vez de vazar o layout da
      página — depende de T008, T009
- [X] T015 [US2] Verificar/ajustar em `src/api/templates/upload.html` o tamanho do
      campo de escolha de foto/arquivo para uso confortável ao toque em celular
      (quickstart.md §3.3) — depende de T007
- [ ] T016 [US2] Checklist de responsividade manual (quickstart.md §3) em largura
      ~360-390px nas 6 páginas: nenhuma exige zoom nem gera rolagem horizontal da
      página inteira, tabelas rolam dentro de si mesmas, formulário de foto é
      utilizável — depende de T004 (colapso do menu lateral), T014, T015

**Checkpoint**: Todas as páginas confirmadas usáveis em tela de celular estreita.

---

## Phase 5: User Story 3 - Gráficos continuam corretos dentro do novo visual (Priority: P2)

**Goal**: Os gráficos de pizza e barras do resumo (feature 005) continuam mostrando
os mesmos valores e cores, sem sobreposição, dentro do novo layout.

**Independent Test**: Abrir a página de resumo antes e depois da mudança visual e
conferir que os mesmos valores, cores e legendas aparecem, sem sobreposição ou corte.

### Implementation for User Story 3

- [X] T017 [US3] Envolver os containers `#grafico-pizza`/`#grafico-barras` em
      `src/api/templates/resumo.html` dentro de um card do Argon com largura
      previsível, sem alterar a altura explícita nem o JS de montagem dos gráficos já
      corrigido na feature 005 (research.md #5 — risco conhecido de reintroduzir o
      bug de sobreposição) — depende de T011
- [ ] T018 [US3] Verificação manual (quickstart.md §4): pizza e barras aparecem
      completos, sem sobreposição, com as mesmas cores validadas em
      `specs/005-graficos-resumo/research.md` #2, em modo claro e escuro do sistema —
      depende de T017

**Checkpoint**: Gráficos do resumo validados dentro do novo layout, em ambos os
temas do sistema.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validação final cruzando todas as user stories.

- [X] T019 Rodar a suíte completa (`pytest tests/unit tests/integration
      tests/contract -v`) e confirmar 100% passando, sem nenhum teste novo esperado
      (FR-002) — depende de T013, T016, T018
- [ ] T020 Validação completa do `quickstart.md` (§1-§5), incluindo o teste de
      funcionamento sem internet (SC-004): desconectar a máquina/Pi da internet e
      recarregar cada página, confirmando visual e funcionalidade completos com
      assets vendorizados localmente — depende de T019
- [X] T021 [P] Revisar todos os templates adaptados e remover/substituir qualquer
      texto de interface em inglês herdado do scaffolding do Argon (placeholders de
      exemplo, textos padrão do template) por português ou remoção (Princípio VI) —
      depende de T007-T012, T017

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1)**: sem dependências — pode começar imediatamente, mas T001
  (aprovação explícita da fonte) bloqueia T002 (download)
- **Foundational (Fase 2)**: depende da Fase 1 completa — BLOQUEIA todas as user
  stories
- **User Story 1 (Fase 3)**: depende da Fase 2 completa
- **User Story 2 (Fase 4)**: depende da Fase 2 completa; T014/T015 dependem
  especificamente dos arquivos já adaptados em US1 (T007-T009), já que editam os
  mesmos templates
- **User Story 3 (Fase 5)**: depende da Fase 2 completa; T017 depende
  especificamente de T011 (mesmo arquivo `resumo.html`)
- **Polish (Fase 6)**: depende de todas as user stories completas

### Parallel Opportunities

- T007-T012 (US1) são `[P]` — arquivos diferentes, sem dependência entre si
- T003 (Setup) pode rodar em paralelo com o restante da Fase 1 depois do download
- T021 (Polish) pode rodar em paralelo com T019/T020 já que revisa arquivos já
  fechados nas fases anteriores

---

## Parallel Example: User Story 1

```bash
# Lançar as adaptações de página da US1 em paralelo (arquivos diferentes):
Task: "Adaptar src/api/templates/upload.html para card de formulário do Argon"
Task: "Adaptar src/api/templates/notas.html para card com tabela estilizada do Argon"
Task: "Adaptar src/api/templates/nota_detalhe.html para card de detalhe do Argon"
Task: "Adaptar src/api/templates/categorias.html para card com tabela do Argon"
Task: "Adaptar src/api/templates/resumo.html para cards de estatística do Argon"
Task: "Adaptar src/api/templates/envio.html para card de status simples do Argon"
```

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Fase 1: Setup (vendorizar assets do Argon)
2. Completar Fase 2: Foundational (base.html reestruturado — CRÍTICO, bloqueia tudo)
3. Completar Fase 3: User Story 1 (todas as páginas com o novo visual)
4. **PARAR e VALIDAR**: checklist de regressão da US1 (T013)
5. Deploy/demo em dev se pronto — já entrega o valor central da feature

### Incremental Delivery

1. Setup + Foundational → fundação pronta
2. US1 → validar independentemente → deploy/demo em dev (MVP visual)
3. US2 → validar independentemente → deploy/demo (responsividade confirmada)
4. US3 → validar independentemente → deploy/demo (gráficos confirmados)
5. Polish → suíte completa + quickstart completo → promover dev → main

---

## Notes

- [P] = arquivos diferentes, sem dependência
- US1 e US2 tocam os mesmos arquivos de página em momentos diferentes (US1 adapta a
  estrutura visual geral; US2 adiciona o tratamento específico de rolagem
  horizontal/toque) — respeitar a ordem indicada nas dependências acima para evitar
  conflito de edição
- Nenhuma tarefa desta feature altera `src/storage/db.py`, models, services ou rotas
  — escopo é exclusivamente `src/api/templates/` e `src/api/static/argon/`
