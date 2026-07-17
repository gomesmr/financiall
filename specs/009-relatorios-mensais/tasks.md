# Tasks: Relatórios Mensais (Resumo por Item + Estabelecimento + Navegação por Mês)

**Input**: Design documents from `/specs/009-relatorios-mensais/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: incluídos (mesmo padrão de cobertura já usado nas features 001-008).

**Organization**: tarefas agrupadas por história de usuário (spec.md), na mesma
ordem de prioridade.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: US1..US6, mapeando para spec.md
- Caminho de arquivo exato em cada descrição

---

## Phase 1: Setup

**Purpose**: confirmar baseline antes de qualquer mudança.

- [X] T001 Rodar a suíte de testes atual como baseline (`python -m pytest -q`) — 244
      passed, 1 skipped, confirmado antes de qualquer alteração desta feature.

Nenhuma dependência nova (plan.md "Primary Dependencies"), nenhum arquivo de
lint/config no projeto — fase de setup não tem mais nada a fazer.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: infraestrutura usada por 2+ histórias — bloqueia início das
histórias de usuário.

**⚠️ CRITICAL**: nenhuma história começa antes desta fase estar completa.

- [X] T002 [P] Implementar helper `_bucket_por_nivel(categoria_id, nivel, categorias_por_id)`
      em `src/services/resumo.py` (research.md #3/#3, data-model.md "Regra de
      negócio: resolução de nível") — resolve subcategoria → categoria-pai
      quando `nivel=1`, usa a própria categoria quando `nivel=2`.
- [X] T003 [P] Implementar `listar_meses_com_notas(db_path)` e `resumo_de_mes(mes, db_path)`
      em `src/services/resumo.py` (research.md #4) — reaproveita
      `_query_resumo_por_mes` já existente.
- [X] T004 Adicionar parâmetro opcional `categoria_id` a `listar_notas` em
      `src/storage/db.py` (data-model.md "Relação com a listagem de notas") —
      filtro por tipo de estabelecimento, aditivo e retrocompatível.

**Checkpoint**: fundação pronta — histórias de usuário podem começar.

---

## Phase 3: User Story 1 - Ver o gasto mensal refletindo a classificação real dos itens (Priority: P1) 🎯 MVP

**Goal**: resumo agrega por categoria do item (com fallback para categoria da
nota), com toggle nível 1/nível 2.

**Independent Test**: nota com itens em categorias diferentes + nota sem
nenhum item classificado, mesmo mês; confirmar que o resumo separa por
categoria de item e usa fallback corretamente; alternar nível 1/2.

### Tests for User Story 1

- [X] T005 [P] [US1] Testes unitários de `gasto_por_categoria_item` (fallback
      item→nota, "Sem categoria" para item pendente de nota já classificada,
      nível 1 vs. nível 2, item com valor nulo excluído) em
      `tests/unit/test_resumo.py`
- [X] T006 [P] [US1] Teste de contrato para
      `GET /notas/resumo/categorias?mes=&dimensao=item&nivel=1|2` em
      `tests/contract/test_api_contract.py` (contracts/api.md)

### Implementation for User Story 1

- [X] T007 [US1] Implementar `gasto_por_categoria_item(mes, nivel=1, db_path)`
      em `src/services/resumo.py` (depende de T002; regra de fallback em
      data-model.md)
- [X] T008 [US1] Estender `GET /notas/resumo/categorias` para aceitar
      `dimensao` (default `item`) e `nivel` (default `1`), despachando para
      `gasto_por_categoria_item` em `src/api/routes_consulta.py`
- [X] T009 [US1] Redesenhar `src/api/templates/resumo.html`: estrutura de
      cartões nova, gráfico de pizza consumindo `dimensao=item`, seletor de
      nível 1/2 (dimensão "por estabelecimento" e navegação por mês entram
      nas histórias seguintes, mas o layout base já é criado aqui)

### Real-Data Validation for User Story 1 (MANDATORY — Princípio V)

- [ ] T010 [US1] Validar contra o backlog real do Pi (dev): nota real com
      itens em categorias diferentes; nota real sem nenhum item classificado
      (fallback); nota real com itens parcialmente classificados
  - [ ] Dimensão 1: nota com mistura real de categorias de item (supermercado com Alimentação + Higiene + Pet)
  - [ ] Dimensão 2: nota real sem nenhum item classificado (fallback para categoria da nota)

### Visual Verification for User Story 1 (MANDATORY — Princípio VIII)

- [X] T011 [US1] Captura de tela headless de `/ver/resumo?dimensao=item` (nível
      1 e nível 2) + checagem de zero erros de console

**Checkpoint**: US1 funcional e testável de forma independente.

---

## Phase 4: User Story 2 - Navegar o resumo mês a mês de forma fluida (Priority: P1)

**Goal**: navegação unificada entre meses no resumo.

**Independent Test**: com notas em 3+ meses, navegar mês anterior/seguinte e
voltar ao mês mais recente.

### Tests for User Story 2

- [X] T012 [P] [US2] Testes unitários de `listar_meses_com_notas`/`resumo_de_mes`
      e da lógica de vizinhança (mês anterior/seguinte nunca aponta para mês
      sem nota; mês corrente sempre incluído) em `tests/unit/test_resumo.py`

### Implementation for User Story 2

- [X] T013 [US2] Implementar cálculo de navegação (`meses_navegaveis`,
      `mes_anterior`, `mes_seguinte`, mês-mais-recente) em `pagina_resumo()`,
      `src/api/routes_consulta.py` (depende de T003; research.md #4)
- [X] T014 [US2] Adicionar UI de navegação (botões anterior/seguinte, ação
      "mês mais recente", indicação visual do mês ativo) em
      `src/api/templates/resumo.html`

### Real-Data Validation for User Story 2

N/A — navegação opera sobre dado interno já validado (meses derivados de
notas já importadas), nenhuma entrada externa nova processada.

### Visual Verification for User Story 2 (MANDATORY — Princípio VIII)

- [X] T015 [US2] Captura de tela headless de `/ver/resumo` navegando entre
      mês com dado e mês corrente vazio + checagem de zero erros de console

**Checkpoint**: US1 + US2 funcionam juntas de forma independente.

---

## Phase 5: User Story 3 - Ver as notas por trás de um número do resumo (Priority: P1)

**Goal**: drill-down do resumo para a listagem de notas do mês (e do tipo de
estabelecimento, quando aplicável).

**Independent Test**: clicar numa fatia do resumo e cair em `/ver/notas`
filtrado exatamente pelo mês (e estabelecimento, se aplicável).

### Tests for User Story 3

- [X] T016 [P] [US3] Teste de contrato para
      `GET /ver/notas?mes=&estabelecimento=` em
      `tests/contract/test_api_contract.py`
- [X] T017 [P] [US3] Teste de integração do fluxo ponta a ponta (resumo →
      clique na fatia → notas filtradas) em `tests/integration/test_api.py`

### Implementation for User Story 3

- [X] T018 [US3] Tratar `mes` e `estabelecimento` em `pagina_notas()`,
      `src/api/routes_consulta.py` (depende de T004)
- [X] T019 [US3] Adicionar handler `plotly_click` em `resumo.html` que monta
      `/ver/notas?mes=...` (dimensão item) ou
      `/ver/notas?mes=...&estabelecimento=...` (dimensão estabelecimento) e
      navega (depende de T009)
- [X] T020 [US3] Adicionar ação direta "Ver notas deste mês" em
      `resumo.html`, independente do clique no gráfico (garante FR-006 mesmo
      sem interação com o gráfico)

### Real-Data Validation for User Story 3

N/A — navegação interna, nenhuma entrada externa nova processada.

### Visual Verification for User Story 3 (MANDATORY — Princípio VIII)

- [X] T021 [US3] Captura de tela headless da página de destino do drill-down
      (`/ver/notas?mes=...&estabelecimento=...`) + checagem de zero erros de
      console

**Checkpoint**: US1 + US2 + US3 (MVP completo do pedido original) funcionam
de forma independente.

---

## Phase 6: User Story 4 - Encontrar notas antigas por mês sem esforço (Priority: P2)

**Goal**: listagem de notas agrupada visualmente por mês como modo padrão.

**Independent Test**: abrir `/ver/notas` sem filtro e identificar
visualmente a que mês cada nota pertence, sem tabela plana única.

### Tests for User Story 4

- [X] T022 [P] [US4] Teste unitário de `agrupar_notas_por_mes` (agrupamento
      preserva ordem desc já existente, mês mais recente primeiro) em
      `tests/unit/test_resumo.py`

### Implementation for User Story 4

- [X] T023 [US4] Implementar `agrupar_notas_por_mes(notas)` em
      `src/services/resumo.py` (research.md #6 — `itertools.groupby` sobre
      resultado já ordenado)
- [X] T024 [US4] Atualizar `pagina_notas()` para agrupar por mês via
      `agrupar_notas_por_mes` quando nenhum `mes` explícito for informado,
      em `src/api/routes_consulta.py`
- [X] T025 [US4] Redesenhar `src/api/templates/notas.html`: renderizar notas
      em seções por mês em vez de tabela única, mantendo os filtros de
      titular/estabelecimento já existentes dentro de cada seção

### Real-Data Validation for User Story 4

N/A — apresentação de dado interno já validado, nenhuma entrada externa nova.

### Visual Verification for User Story 4 (MANDATORY — Princípio VIII)

- [X] T026 [US4] Captura de tela headless de `/ver/notas` agrupada (dado real
      multi-mês) + checagem de zero erros de console

**Checkpoint**: US1-US4 funcionam de forma independente.

---

## Phase 7: User Story 5 - Ver o gasto por tipo de estabelecimento (Priority: P2)

**Goal**: visão de gasto agrupada por tipo de estabelecimento, selecionável
junto ou em vez da visão por categoria de item.

**Independent Test**: notas de um mês em estabelecimentos diferentes;
selecionar a visão por estabelecimento e confirmar agrupamento correto,
independente da categoria dos itens.

### Tests for User Story 5

- [X] T027 [P] [US5] Migrar testes de `gasto_por_categoria` para
      `gasto_por_estabelecimento` (mesmo comportamento + novos casos de
      `nivel`) em `tests/unit/test_resumo.py`
- [X] T028 [P] [US5] Teste de contrato para
      `GET /notas/resumo/categorias?dimensao=estabelecimento&nivel=1|2` em
      `tests/contract/test_api_contract.py`

### Implementation for User Story 5

- [X] T029 [US5] Renomear `gasto_por_categoria` → `gasto_por_estabelecimento`
      com parâmetro `nivel` em `src/services/resumo.py` (depende de T002;
      research.md #2)
- [X] T030 [US5] Adicionar branch `dimensao=estabelecimento` em
      `GET /notas/resumo/categorias`, `src/api/routes_consulta.py` (depende
      de T008)
- [X] T031 [US5] Adicionar seletor de dimensão ("Por item" / "Por
      estabelecimento" / "Os dois") em `resumo.html`, renderizando o segundo
      gráfico quando "estabelecimento" ou "ambos" estiver ativo (depende de
      T009)

### Real-Data Validation for User Story 5 (MANDATORY — Princípio V)

- [ ] T032 [US5] Validar contra o backlog real do Pi (dev): mês com notas em
      tipos de estabelecimento diferentes
  - [ ] Dimensão 1: mês real com notas em pelo menos 3 tipos de estabelecimento distintos
  - [ ] Dimensão 2: nota real sem tipo de estabelecimento atribuído ("Sem tipo de estabelecimento")

### Visual Verification for User Story 5 (MANDATORY — Princípio VIII)

- [X] T033 [US5] Captura de tela headless de `/ver/resumo?dimensao=estabelecimento`
      e da visão "os dois" + checagem de zero erros de console

**Checkpoint**: US1-US5 funcionam de forma independente.

---

## Phase 8: User Story 6 - Revisar a taxonomia de tipo de estabelecimento (Priority: P3)

**Goal**: taxonomia de estabelecimento revisada/expandida e notas reais
reclassificadas.

**Independent Test**: criar subcategorias sob "Saúde"; reclassificar uma
nota real; confirmar reflexo imediato no resumo por estabelecimento.

### Tests for User Story 6

- [X] T034 [P] [US6] Teste unitário de idempotência de
      `seed_taxonomia_estabelecimento` (rodar duas vezes não duplica) em
      `tests/unit/test_seed_taxonomia_estabelecimento.py`

### Implementation for User Story 6

- [X] T035 [US6] Criar `src/scripts/seed_taxonomia_estabelecimento.py`
      (idempotente, mesmo padrão de `seed_taxonomia_categorizacao.py` —
      research.md #7): Supermercado, Mercearia, Restaurante, Bar, Farmácia,
      Pet Shop, Saúde (com Dentista e Plano de Saúde)
- [X] T036 [US6] Trocar rótulo "Categoria" → "Tipo de estabelecimento" e
      reaproveitar o autocomplete hierárquico de `classificacao.js` (feature
      008) no lugar do `<select>` plano, em
      `src/api/templates/nota_detalhe.html`
- [ ] T037 [US6] Rodar o seed contra o banco de dev do Pi e reclassificar as
      notas reais existentes via `atribuir_categoria_a_nota` (operação de
      dado, não de código — revisão feita diretamente na conversa,
      research.md #8)

### Real-Data Validation for User Story 6 (MANDATORY — Princípio V)

- [ ] T038 [US6] Confirmar no Pi (dev) que cada nota real reclassificada
      reflete corretamente em `/ver/resumo?dimensao=estabelecimento`
  - [ ] Dimensão 1: nota reclassificada para uma subcategoria nova (ex.: Saúde › Dentista)
  - [ ] Dimensão 2: nota reclassificada para um tipo de estabelecimento de topo novo (ex.: Mercearia)

### Visual Verification for User Story 6 (MANDATORY — Princípio VIII)

- [X] T039 [US6] Captura de tela headless de `nota_detalhe.html` com o campo
      "Tipo de estabelecimento" novo + checagem de zero erros de console

**Checkpoint**: todas as histórias funcionam de forma independente.

---

## Final Phase: Polish & Cross-Cutting Concerns

- [X] T040 Rodar a suíte de testes completa (`python -m pytest -q`) — todas as
      histórias juntas
- [ ] T041 Rodar os 6 cenários de `quickstart.md` contra o app local com dado
      de teste
- [X] T042 [P] Revisar que nenhuma referência ao nome antigo `gasto_por_categoria`
      restou no código ou nos testes (grep)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências.
- **Foundational (Phase 2)**: depende do Setup — bloqueia todas as histórias.
- **US1 (Phase 3)**: depende de T002 (nível) — sem dependência de outra história.
- **US2 (Phase 4)**: depende de T003 (navegação) — sem dependência de outra história.
- **US3 (Phase 5)**: depende de T004 (filtro estabelecimento) e de T009 (resumo.html
  existir para adicionar o handler de clique) — integra com US1/US2 mas
  testável de forma independente.
- **US4 (Phase 6)**: depende de T004/`listar_notas` já existente — sem
  dependência de outra história.
- **US5 (Phase 7)**: depende de T002 (nível) e T008 (rota `/notas/resumo/categorias`
  já estendida por US1) — integra com US1 mas testável de forma independente.
- **US6 (Phase 8)**: depende de US5 (a visão por estabelecimento precisa
  existir para a validação com dado real fazer sentido) e reaproveita
  `classificacao.js` da feature 008.
- **Polish (Final Phase)**: depende de todas as histórias desejadas estarem completas.

### Parallel Opportunities

- T002 e T003 (Foundational) podem rodar em paralelo — arquivos/funções
  diferentes dentro do mesmo módulo, sem dependência entre si.
- Dentro de cada história, as tarefas marcadas `[P]` (testes de arquivos
  diferentes) podem rodar em paralelo.
- US1, US2 e US4 podem ser implementadas em paralelo por pessoas diferentes
  depois da Fase 2 (Foundational) — US3 e US5 têm uma dependência leve de
  UI com US1 (o mesmo `resumo.html`), então em prática (execução solo desta
  sessão) seguem em sequência.

---

## Parallel Example: User Story 1

```bash
# Testes de US1 em paralelo (arquivos diferentes):
Task: "Testes unitários de gasto_por_categoria_item em tests/unit/test_resumo.py"
Task: "Teste de contrato de /notas/resumo/categorias?dimensao=item em tests/contract/test_api_contract.py"
```

---

## Implementation Strategy

### MVP First (US1 + US2 + US3)

1. Completar Fase 1 (Setup) e Fase 2 (Foundational).
2. Completar US1 (resumo por item com fallback e nível) — já entrega o
   valor central do pedido.
3. Completar US2 (navegação por mês) e US3 (drill-down para notas) — juntas,
   US1+US2+US3 cobrem a reestruturação central pedida ("resumo muito melhor
   estruturado... navegação intuitiva... acesso à listagem das notas daquele
   mês").
4. **Validar e mostrar ao usuário neste ponto já é um incremento
   demonstrável**, mesmo antes de US4-US6.

### Incremental Delivery

1. Setup + Foundational → base pronta.
2. US1 → US2 → US3 → MVP completo do pedido original de resumo.
3. US4 (notas agrupadas por mês) → complementa a integração com `/ver/notas`.
4. US5 (visão por estabelecimento) → segunda dimensão de análise pedida.
5. US6 (revisão de taxonomia + reclassificação real) → torna a US5 precisa
   com dado real.

Nesta sessão, todas as histórias são implementadas em sequência sem parar em
checkpoints intermediários (autorização explícita do usuário) — a
numeração/estrutura acima documenta a ordem lógica de dependência, não uma
pausa real entre elas.

---

## Notes

- `[P]` = arquivos diferentes, sem dependência
- `[Story]` mapeia a tarefa à história correspondente em spec.md
- Nenhuma tabela/coluna nova (data-model.md) — todo o trabalho é
  serviço/rota/template + um script de seed idempotente
- Validação com dado real (Princípio V) obrigatória para US1 e US5 (processam
  agregação sobre dado originado de fonte externa frágil — OCR/scraping,
  features 001/004/008); N/A explícito para US2/US3/US4 (navegação/apresentação
  sobre dado interno já validado)
- Verificação visual (Princípio VIII) obrigatória para todas as histórias com
  superfície visual nova/alterada (US1-US6, exceto nenhuma — todas mexem em
  template)
