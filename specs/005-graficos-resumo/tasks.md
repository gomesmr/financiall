---

description: "Task list for feature implementation"
---

# Tasks: Gráficos no Resumo de Gastos

**Input**: Design documents from `/specs/005-graficos-resumo/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/api.md](./contracts/api.md), [quickstart.md](./quickstart.md)

**Tests**: Incluídos. `plan.md` (seção Testing) e a "Verificação final" de
`quickstart.md` exigem a suíte `pytest tests/unit tests/integration
tests/contract` passando antes de considerar a feature pronta.

**Real-Data Validation (Princípio V da constituição)**: não se aplica —
mesmo raciocínio das features 002/003. A agregação opera sobre dado já
validado ao entrar na base; não processa arquivo ou fonte externa nova.

**Organization**: Tarefas agrupadas por user story (spec.md) para permitir
implementação e teste independentes de cada uma. Renderização via
Plotly.js (research.md #3, decisão revertida durante o planejamento por
preferência explícita do usuário) — sem framework de teste JS no projeto
(Princípio I), a renderização é validada por teste de contrato
(marcadores no HTML) e pela validação manual de `quickstart.md`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: A qual user story a tarefa pertence (US1..US3)
- Caminhos de arquivo exatos incluídos em cada descrição

## Path Conventions

Aplicação web única (single project): `src/`, `tests/` na raiz do
repositório, mesma estrutura das features anteriores (ver `plan.md` →
Project Structure).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Vendorizar a biblioteca de gráficos (única inicialização nova desta feature)

- [X] T001 Baixar `plotly.js-basic-dist.min.js` (cobre `pie`/`bar`, não a distribuição completa) e salvar em src/api/static/plotly-basic.min.js — arquivo vendorizado, sem CDN (research.md #3)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Agregação de dados e paleta de cores que TODA user story depende

**⚠️ CRITICAL**: Nenhuma user story pode começar antes desta fase estar completa

- [X] T002 Implementar `GastoCategoria` (dataclass) e `gasto_por_categoria(mes, db_path) -> list[GastoCategoria]` em src/services/resumo.py conforme data-model.md — agrupa por categoria (incluindo "Sem categoria"), exclui notas com `valor_total` nulo
- [X] T003 Implementar a rota `GET /notas/resumo/categorias?mes=AAAA-MM` em src/api/routes_consulta.py conforme contracts/api.md (depende de T002)
- [X] T004 Referenciar `plotly-basic.min.js` (`<script src="/static/plotly-basic.min.js">`) e definir a paleta categórica validada (8 hex + tom neutro, light + dark — research.md #2) como constante JS reaproveitável, em src/api/templates/resumo.html (ajustado de base.html — só o resumo usa gráficos, mesmo padrão de scripts por página já usado no projeto) (depende de T001)

**Checkpoint**: Fundação pronta — implementação das user stories pode começar

---

## Phase 3: User Story 1 - Ver a distribuição do gasto do mês por categoria (Priority: P1) 🎯 MVP

**Goal**: A página de resumo mostra um gráfico de pizza (Plotly) com o gasto do mês corrente por categoria, incluindo "Sem categoria" como fatia própria, com legenda e tooltip mostrando o valor exato.

**Independent Test**: com notas categorizadas no mês corrente, abrir `/ver/resumo` e verificar que o gráfico de pizza mostra uma fatia por categoria, proporcional ao gasto de cada uma, com legenda visível.

### Tests for User Story 1 ⚠️

> **NOTE: Escrever estes testes PRIMEIRO, garantir que falham antes da implementação**

- [X] T005 [P] [US1] Teste unitário: `gasto_por_categoria` — soma correta por categoria, notas sem `categoria_id` agrupam sob "Sem categoria", notas com `valor_total` nulo excluídas da soma — tests/unit/test_resumo.py
- [X] T006 [P] [US1] Teste de integração: soma de `GET /notas/resumo/categorias` bate exatamente com o total de `GET /notas/resumo/mes-atual` (FR-006) — tests/integration/test_api.py

### Implementation for User Story 1

- [X] T007 [US1] Implementar `Plotly.newPlot(..., [{type: 'pie', ...}])` consumindo `GET /notas/resumo/categorias` (mês corrente) em src/api/templates/resumo.html — `marker.colors` via `categoria_id % 8` (research.md #4, nunca a paleta padrão do Plotly), tom neutro para "Sem categoria"/cauda dobrada em "Outros" além de 8 categorias com gasto, legenda ativa (`showlegend: true`), layout claro/escuro conforme `prefers-color-scheme` usando os hex validados de cada modo (depende de T003, T004)
- [X] T008 [US1] Configurar `hovertemplate` da pizza para mostrar nome da categoria + valor formatado (R$) em vez do tooltip padrão do Plotly, em src/api/templates/resumo.html (depende de T007)

**Checkpoint**: User Story 1 funcional e testável de forma independente — pizza do mês corrente já entrega o valor central pedido

---

## Phase 4: User Story 2 - Ver a evolução do gasto mês a mês (Priority: P1)

**Goal**: A página de resumo mostra um gráfico de barras (Plotly) com o total gasto em cada mês do histórico, com tooltip mostrando o valor exato por mês.

**Independent Test**: com notas em pelo menos três meses diferentes, abrir `/ver/resumo` e verificar que o gráfico de barras mostra uma barra por mês, com altura proporcional ao total.

Nenhuma rota nova nesta fase — reaproveita `GET /notas/resumo/historico`
já existente (research.md #5).

### Tests for User Story 2 ⚠️

- [X] T009 [P] [US2] Teste de contrato: `/ver/resumo`, com notas em vários meses, inclui o container do gráfico de barras (marcador identificável no HTML, ex.: `id="grafico-barras"`) — tests/contract/test_api_contract.py

### Implementation for User Story 2

- [X] T010 [US2] Passar o histórico já calculado (`historico_meses_anteriores`) como JSON embutido no template, em src/api/routes_consulta.py → `pagina_resumo`
- [X] T011 [US2] Implementar `Plotly.newPlot(..., [{type: 'bar', ...}])` com um mês por barra (eixo X) e total gasto (eixo Y), cor sequencial única (research.md #2), `hovertemplate` mostrando mês + valor exato, layout claro/escuro conforme `prefers-color-scheme`, em src/api/templates/resumo.html (depende de T004, T010)

**Checkpoint**: User Stories 1 e 2 funcionam juntas — MVP completo (pizza + barras)

---

## Phase 5: User Story 3 - Ver a distribuição por categoria de um mês específico (Priority: P2)

**Goal**: O usuário escolhe um mês do histórico e o gráfico de pizza passa a refletir a distribuição por categoria daquele mês.

**Independent Test**: escolher um mês do histórico (diferente do corrente) no seletor e verificar que o gráfico de pizza atualiza para a distribuição daquele mês.

### Tests for User Story 3 ⚠️

- [X] T012 [P] [US3] Teste de integração: `GET /notas/resumo/categorias?mes=AAAA-MM` (mês passado) retorna a distribuição daquele mês, diferente da do mês corrente — tests/integration/test_api.py (depende de T003)
- [X] T013 [P] [US3] Teste de integração: mês sem nenhuma nota com valor retorna `{"categorias": []}`, sem erro — tests/integration/test_api.py (depende de T003)

### Implementation for User Story 3

- [X] T014 [US3] Passar a lista de meses disponíveis (histórico + mês corrente) da rota `pagina_resumo` para o template, em src/api/routes_consulta.py (depende de T010)
- [X] T015 [US3] Implementar o seletor de mês em src/api/templates/resumo.html, disparando `fetch GET /notas/resumo/categorias?mes=` e atualizando a pizza via `Plotly.react` (não recriar o gráfico do zero) (depende de T007, T014)
- [X] T016 [US3] Implementar a mensagem clara ("nenhum gasto neste mês") quando o mês escolhido retorna `categorias: []`, substituindo o gráfico em vez de deixá-lo vazio/quebrado (FR-005) em src/api/templates/resumo.html (depende de T015)

**Checkpoint**: Todas as user stories funcionam de forma independente

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Revisão final e validação ponta a ponta

- [X] T017 [P] Confirmar que todo hex usado em `base.html`/`resumo.html` bate exatamente com os validados em research.md #2 (nenhuma cor "no olho" introduzida durante a implementação)
- [X] T018 [P] Confirmar `responsive: true` no `config` do Plotly e que os gráficos não vazam da tela em telas estreitas
- [X] T019 Validar manualmente os 7 passos de quickstart.md contra o servidor local, incluindo modo escuro e que `plotly-basic.min.js` carrega de `/static/` sem depender de rede externa
- [X] T020 Rodar a suíte completa `pytest tests/unit tests/integration tests/contract` e confirmar 100% de sucesso antes de promover a feature (dev → main)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 (vendorizar Plotly) — sem dependências
- **Foundational (Phase 2)**: Depende de T001 (T004 referencia o arquivo vendorizado) — BLOQUEIA todas as user stories
- **US1 (Phase 3)**: Depende apenas da Foundational
- **US2 (Phase 4)**: Depende apenas da Foundational — independente de US1
- **US3 (Phase 5)**: Depende de US1 (T007, reaproveita o gráfico de pizza) e de US2 (T010, reaproveita a lista de meses)
- **Polish (Phase 6)**: Depende de todas as user stories completas

### User Story Dependencies

- **US1 (P1)**: Sem dependência de outra story — pizza do mês corrente
- **US2 (P1)**: Sem dependência de US1 — barras da evolução mensal; pode ser feita em paralelo a US1 (funções JS distintas no mesmo template — cuidado ao mesclar `resumo.html`)
- **US3 (P2)**: Depende de US1 e de US2

### Within Each User Story

- Testes MUST ser escritos e falhar antes da implementação (quando aplicável — backend)
- Vendorizar Plotly → agregação/rota → `Plotly.newPlot` → `hovertemplate`/layout

### Parallel Opportunities

- T005/T006 (US1), T012/T013 (US3) — cada par de testes roda em paralelo
- US1 (T007–T008) e US2 (T010–T011) podem ser desenvolvidas em paralelo por sessões diferentes
- T017/T018 (Polish) em paralelo

---

## Parallel Example: User Story 1

```bash
Task: "Teste unitário de gasto_por_categoria em tests/unit/test_resumo.py"
Task: "Teste de integração de GET /notas/resumo/categorias em tests/integration/test_api.py"
```

## Parallel Example: User Story 1 + User Story 2 (após Foundational)

```bash
# Pizza (US1):
Task: "Plotly.newPlot tipo pie em src/api/templates/resumo.html"

# Barras (US2), em paralelo:
Task: "Plotly.newPlot tipo bar em src/api/templates/resumo.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2)

1. Completar Phase 1: Setup (T001) e Phase 2: Foundational (T002–T004)
2. Completar Phase 3: User Story 1 (T005–T008)
3. Completar Phase 4: User Story 2 (T009–T011)
4. **PARAR e VALIDAR**: abrir `/ver/resumo` e conferir os dois gráficos com dado real
5. Já entrega o pedido central — pizza por categoria + barras por mês

### Incremental Delivery

1. Setup + Foundational → Plotly vendorizado, agregação e paleta prontas
2. US1 → Testar independentemente → pizza do mês corrente
3. US2 → Testar independentemente → barras da evolução mensal (MVP completo com US1)
4. US3 → Testar independentemente → pizza de qualquer mês do histórico
5. Polish → auditoria de cor, responsividade, validação manual completa, suíte completa

### Ordem sugerida de execução

**Setup → Foundational → (US1 e US2 em paralelo) → US3 → Polish**. US3
depende das duas anteriores, então não faz sentido paralelizá-la com elas.

---

## Notes

- [P] tasks = arquivos diferentes, sem dependências
- [Story] label mapeia a tarefa à user story correspondente para rastreabilidade
- Fazer commit após cada tarefa ou grupo lógico
- Parar em cada checkpoint para validar a story de forma independente
- **Nenhuma cor é escolhida "no olho"** — toda cor usada nos gráficos vem da paleta validada em research.md #2; qualquer cor nova exige rodar `scripts/validate_palette.js` de novo antes de usar
- Nomes de categoria/mês vêm do banco (dado do usuário) — usar as opções de `hovertemplate`/`labels` do Plotly (que já escapam texto), nunca concatenar HTML manualmente com esses valores
- `plotly-basic.min.js` é um arquivo vendorizado (binário/minificado) — commitar como está, sem tentar formatá-lo ou revisá-lo linha a linha
