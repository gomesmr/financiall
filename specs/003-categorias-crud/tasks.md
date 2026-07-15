---

description: "Task list for feature implementation"
---

# Tasks: CRUD de Categorias

**Input**: Design documents from `/specs/003-categorias-crud/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/api.md](./contracts/api.md), [quickstart.md](./quickstart.md)

**Tests**: Incluídos. `plan.md` (seção Testing) e a "Verificação final" de
`quickstart.md` exigem a suíte `pytest tests/unit tests/integration
tests/contract` passando antes de considerar a feature pronta.

**Real-Data Validation (Princípio V da constituição)**: não se aplica —
mesmo raciocínio de `research.md` #3 da feature 002. Esta feature não
processa dado vindo de fora do controle do código; nome de categoria é
digitado pelo próprio usuário na UI.

**Organization**: Tarefas agrupadas por user story (spec.md) para permitir
implementação e teste independentes de cada uma.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: A qual user story a tarefa pertence (US1..US5)
- Caminhos de arquivo exatos incluídos em cada descrição

## Path Conventions

Aplicação web única (single project): `src/`, `tests/` na raiz do
repositório, mesma estrutura das features 001/002 — nenhum diretório novo
no nível raiz (ver `plan.md` → Project Structure).

---

## Phase 1: Setup (Shared Infrastructure)

Não há inicialização de projeto nova — reaproveita 100% da estrutura,
dependências e configuração já existentes. Nenhuma tarefa de Setup.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Modelo, schema e operações básicas de leitura/escrita de categoria que TODA user story depende

**⚠️ CRITICAL**: Nenhuma user story pode começar antes desta fase estar completa

- [X] T001 [P] Criar modelo `Categoria` (dataclass: `id`, `nome`) em src/models/categoria.py
- [X] T002 Adicionar tabela `categoria` (`CREATE TABLE IF NOT EXISTS` + índice único em `nome_normalizado`) e a coluna `categoria_id` em `nota_fiscal` via `ALTER TABLE` idempotente (checagem por `PRAGMA table_info`) em src/storage/db.py → `init_db()`, conforme data-model.md
- [X] T003 Implementar `listar_categorias` e `buscar_categoria_por_id` em src/storage/db.py (depende de T002)
- [X] T004 Implementar `criar_categoria(nome, db_path) -> int | None` (calcula `nome_normalizado` via `nome.strip().casefold()`, retorna `None` se nome vazio ou índice único violado) em src/storage/db.py conforme research.md #2 (depende de T002)
- [X] T005 Criar o blueprint vazio `categorias` em src/api/routes_categorias.py e registrar em src/api/app.py (depende de T001)

**Checkpoint**: Fundação pronta — implementação das user stories pode começar

---

## Phase 3: User Story 1 - Criar uma categoria nova (Priority: P1) 🎯 MVP

**Goal**: Usuário cria uma categoria informando um nome; nomes vazios ou duplicados são recusados com mensagem clara.

**Independent Test**: `POST /categorias` com um nome novo e verificar que ele aparece em `GET /categorias`; repetir com o mesmo nome (variando maiúsculas/espaços) e verificar a recusa.

### Tests for User Story 1 ⚠️

> **NOTE: Escrever estes testes PRIMEIRO, garantir que falham antes da implementação**

- [X] T006 [P] [US1] Teste unitário: `criar_categoria` — nome válido cria e retorna `id`; nome vazio/só espaços retorna `None`; nome duplicado (variando maiúsculas, espaços nas pontas e acentuação) retorna `None` — tests/unit/test_categorias.py
- [X] T007 [P] [US1] Teste de integração: `POST /categorias` cria a categoria e ela aparece em `GET /categorias` — tests/integration/test_api.py

### Implementation for User Story 1

- [X] T008 [US1] Criar src/services/categorias.py com `validar_e_criar_categoria(nome, db_path)` — recusa nome vazio/só espaços com mensagem própria (FR-010) antes de chamar o repositório; delega a checagem de duplicata a `criar_categoria` (FR-002) (depende de T004)
- [X] T009 [US1] Implementar a rota `POST /categorias` em src/api/routes_categorias.py — `201` sucesso, `422` nome vazio, `422` nome duplicado, conforme contracts/api.md (depende de T005, T008)
- [X] T010 [US1] Implementar a rota `GET /categorias` em src/api/routes_categorias.py — todas as categorias ordenadas por nome (depende de T003, T005)

**Checkpoint**: User Story 1 funcional e testável de forma independente — já dá para criar categorias e confirmar que existem

---

## Phase 4: User Story 2 - Atribuir categoria a uma nota fiscal (Priority: P1)

**Goal**: Usuário escolhe (ou troca, ou remove) a categoria de uma nota já importada, a partir da tela de detalhe; a categoria escolhida aparece na listagem e no detalhe.

**Independent Test**: com ao menos uma categoria criada (US1), atribuir uma categoria a uma nota via `PUT /notas/<id>/categoria` e verificar que ela aparece em `GET /notas` e na página de detalhe.

### Tests for User Story 2 ⚠️

- [X] T011 [P] [US2] Teste unitário: `atribuir_categoria_a_nota` — atribui, troca e remove (`categoria_id=None`); nota inexistente retorna `None`; `categoria_id` informado mas inexistente retorna `False` — tests/unit/test_categorias.py
- [X] T012 [P] [US2] Teste de integração: `PUT /notas/<id>/categoria` atribui/troca/remove, refletido em `GET /notas` — tests/integration/test_api.py

### Implementation for User Story 2

- [X] T013 [US2] Implementar `atribuir_categoria_a_nota(nota_id, categoria_id, db_path)` em src/storage/db.py conforme data-model.md (depende de T002)
- [X] T014 [US2] Implementar a rota `PUT /notas/<id>/categoria` em src/api/routes_categorias.py — `200`/`404`/`422` conforme contracts/api.md (depende de T005, T013)
- [X] T015 [US2] Adicionar o campo `categoria_id` a `NotaFiscal` (src/models/nota_fiscal.py) e lê-lo em `_row_to_nota` (src/storage/db.py)
- [X] T016 [US2] Atualizar `pagina_nota_detalhe` e `pagina_notas` em src/api/routes_consulta.py para passar a lista de categorias (e a categoria atual de cada nota) aos templates (depende de T003, T015)
- [X] T017 [US2] Atualizar `nota_to_dict` em src/api/routes_importar.py para incluir o campo `categoria` (`{"id", "nome"}` ou `null`), usado por `GET /notas` (depende de T003, T015)
- [X] T018 [US2] Adicionar seletor de categoria (select + salvar, `fetch PUT /notas/<id>/categoria`) em src/api/templates/nota_detalhe.html (depende de T014, T016)
- [X] T019 [P] [US2] Adicionar coluna "Categoria" (somente leitura) na listagem em src/api/templates/notas.html (depende de T016)

**Checkpoint**: User Stories 1 e 2 funcionam juntas — o valor central pedido (categorizar notas) já está entregue

---

## Phase 5: User Story 3 - Ver todas as categorias existentes (Priority: P2)

**Goal**: Usuário navega até uma tela dedicada e vê todas as categorias já criadas.

**Independent Test**: com duas ou mais categorias criadas, acessar `/ver/categorias` e verificar que todas aparecem; com nenhuma, ver mensagem clara com caminho para criar a primeira.

### Tests for User Story 3 ⚠️

- [X] T020 [P] [US3] Teste de contrato: `GET /ver/categorias` mostra as categorias existentes e a mensagem de lista vazia quando não há nenhuma — tests/contract/test_api_contract.py

### Implementation for User Story 3

- [X] T021 [US3] Implementar a rota de visão `GET /ver/categorias` em src/api/routes_categorias.py, chamando `listar_categorias` (depende de T003, T005)
- [X] T022 [US3] Criar o template src/api/templates/categorias.html — lista de categorias + formulário de criação (reaproveita `POST /categorias` de US1 via `fetch`) (depende de T021, T009)
- [X] T023 [US3] Adicionar o link "Categorias" à navegação principal em src/api/templates/base.html

**Checkpoint**: Usuário navega e vê todas as categorias numa tela própria

---

## Phase 6: User Story 4 - Editar o nome de uma categoria (Priority: P2)

**Goal**: Usuário corrige/renomeia uma categoria existente, sem perder as notas já atribuídas a ela.

**Independent Test**: editar o nome de uma categoria que já tem notas atribuídas e verificar que o novo nome aparece na lista de categorias e nas notas que a usavam.

### Tests for User Story 4 ⚠️

- [X] T024 [P] [US4] Teste unitário: `editar_categoria` — nome novo válido atualiza; categoria inexistente retorna `None`; nome duplicado de outra categoria retorna `False` — tests/unit/test_categorias.py
- [X] T025 [P] [US4] Teste de integração: `PUT /categorias/<id>` atualiza o nome, refletido em `GET /categorias` e em `GET /notas` para notas que já usavam essa categoria — tests/integration/test_api.py

### Implementation for User Story 4

- [X] T026 [US4] Implementar `editar_categoria(categoria_id, novo_nome, db_path)` em src/storage/db.py conforme data-model.md (depende de T002)
- [X] T027 [US4] Adicionar `validar_e_editar_categoria` a src/services/categorias.py, mesma validação de nome vazio/duplicado de US1 (depende de T026)
- [X] T028 [US4] Implementar a rota `PUT /categorias/<id>` em src/api/routes_categorias.py — `200`/`404`/`422` conforme contracts/api.md (depende de T005, T027)
- [X] T029 [US4] Adicionar edição de nome por categoria (formulário inline + `fetch PUT /categorias/<id>`) em src/api/templates/categorias.html (depende de T022, T028)

**Checkpoint**: Usuário corrige nomes de categoria sem perder o vínculo com notas já categorizadas

---

## Phase 7: User Story 5 - Excluir uma categoria (Priority: P3)

**Goal**: Usuário remove uma categoria que não faz mais sentido; notas que a usavam voltam a "sem categoria", sem erro.

**Independent Test**: excluir uma categoria com notas atribuídas, confirmar, e verificar que essas notas aparecem como "sem categoria" em `GET /notas`.

### Tests for User Story 5 ⚠️

- [X] T030 [P] [US5] Teste unitário: `excluir_categoria` — remove categoria sem notas; remove categoria com notas associadas e desassocia (`nota_fiscal.categoria_id` vira `NULL`); categoria inexistente retorna `False` — tests/unit/test_categorias.py
- [X] T031 [P] [US5] Teste de integração: `DELETE /categorias/<id>` com nota associada — a nota passa a "sem categoria" em `GET /notas`, sem erro — tests/integration/test_api.py

### Implementation for User Story 5

- [X] T032 [US5] Implementar `excluir_categoria(categoria_id, db_path)` — transação única (`UPDATE nota_fiscal SET categoria_id = NULL WHERE categoria_id = ?` seguido de `DELETE FROM categoria WHERE id = ?`) em src/storage/db.py conforme research.md #3 (depende de T002)
- [X] T033 [US5] Implementar a rota `DELETE /categorias/<id>` em src/api/routes_categorias.py — `200`/`404` conforme contracts/api.md (depende de T005, T032)
- [X] T034 [US5] Adicionar botão "Excluir" com `confirm()` por categoria (`fetch DELETE /categorias/<id>`) em src/api/templates/categorias.html (depende de T022, T033)

**Checkpoint**: Todas as user stories funcionam de forma independente

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Revisão final e validação ponta a ponta

- [X] T035 [P] Revisar as mensagens de validação/confirmação novas em todos os templates e rotas tocados quanto à consistência de idioma/tom (Princípio VI)
- [X] T036 Validar manualmente os cenários de quickstart.md contra o servidor local e confirmar os critérios SC-001 a SC-005
- [X] T037 Rodar a suíte completa `pytest tests/unit tests/integration tests/contract` e confirmar 100% de sucesso antes de promover a feature (dev → main)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Vazia — nada a fazer
- **Foundational (Phase 2)**: Sem dependências externas — BLOQUEIA todas as user stories
- **US1 (Phase 3)**: Depende apenas da Foundational
- **US2 (Phase 4)**: Depende da Foundational e de US1 existir (precisa de ao menos uma categoria para atribuir, mas não compartilha arquivos de implementação com US1 além do blueprint)
- **US3 (Phase 5)**: Depende da Foundational e de US1 (reaproveita `POST /categorias` no template novo)
- **US4 (Phase 6)**: Depende da Foundational e de US3 (o template `categorias.html` já precisa existir para ganhar a edição inline)
- **US5 (Phase 7)**: Depende da Foundational e de US3 (mesmo motivo de US4)
- **Polish (Phase 8)**: Depende de todas as user stories completas

### User Story Dependencies

- **US1 (P1)**: Sem dependência de outra story — MVP: criar categorias
- **US2 (P1)**: Depende de categorias existirem (US1) para ter o que atribuir — é o valor central da feature
- **US3 (P2)**: Depende de US1 (endpoint de criação já pronto) — foca na experiência de visualização
- **US4 (P2)**: Depende de US3 (template de categorias já existe)
- **US5 (P3)**: Depende de US3 (template de categorias já existe)

### Within Each User Story

- Testes MUST ser escritos e falhar antes da implementação
- Repositório (`storage/db.py`) antes do serviço (`services/categorias.py`) antes da rota antes do template

### Parallel Opportunities

- T001 (Foundational) é paralelo ao resto da fase
- T006/T007 (US1), T011/T012 (US2), T024/T025 (US4), T030/T031 (US5) — cada par de testes roda em paralelo
- T019 (US2, template de listagem) pode rodar em paralelo a T018 (template de detalhe) depois de T016
- T035 (Polish) é paralelo às demais tarefas de Polish

---

## Parallel Example: User Story 1

```bash
# Testes em paralelo:
Task: "Teste unitário de criar_categoria em tests/unit/test_categorias.py"
Task: "Teste de integração de POST /categorias em tests/integration/test_api.py"
```

## Parallel Example: User Story 2 (templates)

```bash
# Depois que T016 (routes_consulta.py) estiver pronto:
Task: "Seletor de categoria em src/api/templates/nota_detalhe.html"
Task: "Coluna Categoria em src/api/templates/notas.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2)

1. Completar Phase 2: Foundational (T001–T005)
2. Completar Phase 3: User Story 1 (T006–T010)
3. Completar Phase 4: User Story 2 (T011–T019)
4. **PARAR e VALIDAR**: criar uma categoria e atribuí-la a uma nota real pela UI
5. Já entrega o valor central pedido — categorizar gastos já registrados

### Incremental Delivery

1. Foundational → schema e repositório básico prontos
2. US1 → Testar independentemente → categorias podem ser criadas
3. US2 → Testar independentemente → notas podem ser categorizadas (MVP)
4. US3 → Testar independentemente → usuário navega e vê todas as categorias
5. US4 → Testar independentemente → nomes podem ser corrigidos
6. US5 → Testar independentemente → categorias antigas podem ser removidas
7. Polish → revisão de idioma, validação manual de quickstart.md, suíte completa

### Ordem sugerida de execução

**Foundational → US1 → US2 → US3 → (US4 e US5 em paralelo) → Polish**. US4
e US5 não compartilham arquivos de implementação nova entre si além do
template `categorias.html` já existente (de US3), então podem ser feitas
em paralelo por sessões diferentes.

---

## Notes

- [P] tasks = arquivos diferentes, sem dependências
- [Story] label mapeia a tarefa à user story correspondente para rastreabilidade
- Verificar que os testes falham antes de implementar (TDD)
- Fazer commit após cada tarefa ou grupo lógico
- Parar em cada checkpoint para validar a story de forma independente
- Nenhum dado sensível em log de texto claro em nenhuma tarefa (Princípio IV) — não se aplica diretamente aqui (nome de categoria não é dado sensível), mas nenhuma tarefa deve logar nota/valor/chave ao manipular a associação categoria↔nota
