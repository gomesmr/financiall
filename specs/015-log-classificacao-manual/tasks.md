---

description: "Task list for feature 015: log de classificação manual de natureza"
---

# Tasks: Log de classificação manual de natureza

**Input**: Design documents from `/specs/015-log-classificacao-manual/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Incluídos — mesmo padrão já seguido pelas features 001–014
deste projeto.

**Organization**: Tarefas agrupadas por user story (spec.md), na mesma
ordem de prioridade declarada lá (US1 é P1; US2 é P2).

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Projeto único (`src/`, `tests/` na raiz) — mesma estrutura das features
001–014.

---

## Phase 1: Setup

Sem tarefas — nenhuma dependência nova (research.md): usa só
`sqlite3`/`datetime` da stdlib.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: modelo e repositório de `LogClassificacaoManual` são a base
que tanto US1 (ver o histórico) quanto US2 (confiar no histórico numa
reclassificação) precisam antes de existir qualquer gravação ou leitura.

- [x] T001 Criar dataclass `LogClassificacaoManual` em
      `src/models/log_classificacao_manual.py` (mesmo padrão de
      `models/log_importacao.py`): campos `data_hora`, `metodo`,
      `alvo_descricao_normalizada`, `alvo_transacao_id`, `natureza`,
      `categoria_id`, `quantidade_afetada`, `id` (data-model.md)
- [x] T002 Em `src/storage/db.py`: adicionar `CREATE TABLE IF NOT EXISTS
      log_classificacao_manual` ao `SCHEMA` (data-model.md), e as
      funções `inserir_log_classificacao_manual(log, db_path) -> int` e
      `listar_logs_classificacao_manual(db_path) -> list[LogClassificacaoManual]`
      (`ORDER BY data_hora DESC, id DESC`), seguindo o mesmo padrão de
      `inserir_log_importacao`/`listar_logs_importacao`
- [x] T003 [P] Testes unitários em
      `tests/unit/test_storage_log_classificacao_manual.py`: inserir um
      `LogClassificacaoManual` (método grupo e método individual) e
      recuperá-lo por `listar_logs_classificacao_manual`; duas inserções
      aparecem na ordem certa (mais recente primeiro); `alvo_transacao_id`/
      `categoria_id` nulos são persistidos e lidos corretamente como `None`

**Checkpoint**: modelo e repositório prontos e testados — US1 e US2
podem prosseguir sem bloqueio mútuo.

---

## Phase 3: User Story 1 - Saber o que foi classificado manualmente e como, sem acessar o servidor (Priority: P1) 🎯 MVP

**Goal**: toda classificação manual de natureza bem-sucedida (em grupo
ou individual) gera um evento de histórico visível numa página nova,
com alvo, natureza, categoria e quantidade afetada corretos, ordenados
do mais recente pro mais antigo.

**Independent Test**: classificar um grupo pendente e uma transação
individual, e conferir que dois eventos aparecem em
`/ver/log-classificacoes` com os dados certos.

### Tests for User Story 1

- [x] T004 [P] [US1] Testes unitários em
      `tests/unit/test_classificacao_natureza_log.py`: chamar
      `storage_db.classificar_grupo_pendente_natureza()` com um grupo
      pendente real e conferir, via `listar_logs_classificacao_manual`,
      que um evento foi gravado com `metodo="grupo"`,
      `alvo_descricao_normalizada` correta, natureza/categoria
      corretas e `quantidade_afetada` igual ao retorno da função;
      chamar `storage_db.atribuir_natureza_manual()` numa transação e
      conferir evento com `metodo="individual"`, `alvo_transacao_id`
      correto e `quantidade_afetada == 1` (research.md #1/#2)

### Implementation for User Story 1

- [x] T005 [US1] Em `src/storage/db.py`,
      `classificar_grupo_pendente_natureza()`: depois de calcular
      `len(ids)`, se maior que zero, montar um `LogClassificacaoManual`
      (`metodo="grupo"`) e gravar via
      `inserir_log_classificacao_manual()` antes do `return` (depende de
      T001/T002)
- [x] T006 [US1] Em `src/storage/db.py`, `atribuir_natureza_manual()`:
      no ramo de sucesso (depois de `classificar_natureza_transacao()`,
      antes do `return True`), montar um `LogClassificacaoManual`
      (`metodo="individual"`, `alvo_transacao_id=transacao_id`,
      `quantidade_afetada=1`) e gravar via
      `inserir_log_classificacao_manual()` (depende de T001/T002)
- [x] T007 [US1] Criar blueprint `src/api/routes_log_classificacoes.py`
      com `GET /ver/log-classificacoes`
      (`pagina_ativa="log_classificacoes"`), chamando
      `storage_db.listar_logs_classificacao_manual()` e
      `storage_db.listar_categorias()` (pra resolver nome da categoria)
      e renderizando `log_classificacoes.html` (contracts/api.md);
      registrar o blueprint em `src/api/app.py`
- [x] T008 [US1] Criar `src/api/templates/log_classificacoes.html`
      (mesmo padrão visual Argon de `log_importacoes.html`): tabela com
      as colunas de contracts/api.md; adicionar link "Classificações
      manuais" na navegação de `base.html`

### Real-Data Validation for User Story 1

- [x] T009 [US1] N/A — esta feature não faz parsing de dado externo
      novo (Princípio V não se aplica); ela só audita uma ação de
      classificação que o próprio usuário/agente já dispara pela UI

### Visual Verification for User Story 1 (Constitution Principle VIII)

- [x] T010 [US1] Nenhum asset de terceiro vendorizado — N/A para
      checagem de integridade de formato. Screenshot via navegador
      headless de `/ver/log-classificacoes` com eventos de teste (grupo
      e individual) confirmou tabela correta (método, alvo, natureza,
      categoria, quantidade); sem erro de console

**Checkpoint**: US1 completa e testável de forma independente (MVP).

---

## Phase 4: User Story 2 - Confiar no histórico mesmo numa reclassificação (Priority: P2)

**Goal**: reclassificar o mesmo grupo/transação com natureza diferente
gera um evento novo, sem apagar o anterior; uma tentativa que não afeta
nada, ou é recusada pela validação, não gera evento nenhum.

**Independent Test**: classificar o mesmo grupo duas vezes com naturezas
diferentes e conferir dois eventos distintos, na ordem certa; tentar
classificar com natureza inválida e um grupo já 100% classificado (0
afetados) e conferir que nenhum evento novo aparece em nenhum dos dois
casos.

### Tests for User Story 2

- [x] T011 [P] [US2] Testes unitários em
      `tests/unit/test_classificacao_natureza_log.py`:
      (a) classificar o mesmo grupo duas vezes com naturezas diferentes
      — dois eventos aparecem, o mais recente primeiro;
      (b) classificar um grupo cuja `descricao_normalizada` não tem
      nenhuma transação pendente (`0` afetadas) — nenhum evento novo é
      gravado;
      (c) chamar `atribuir_natureza_manual()` com natureza inválida — a
      função retorna `False` e nenhum evento é gravado (research.md #3)

### Implementation for User Story 2

- [x] T012 [US2] Confirmado: a implementação de T005/T006 satisfez os
      três casos de T011 sem nenhuma mudança adicional (os 6 testes de
      T004+T011 passaram de primeira)

### Real-Data Validation for User Story 2

- [x] T013 [US2] N/A — mesma justificativa de T009

### Visual Verification for User Story 2 (Constitution Principle VIII)

- [x] T014 [US2] Screenshot via navegador headless de
      `/ver/log-classificacoes` confirmou dois eventos do mesmo alvo
      ("BURGER KING", gasto e depois estorno_credito) exibidos com
      clareza, ordem correta (reclassificação no topo), sem erro de
      console

**Checkpoint**: US1 + US2 completas — o histórico é confiável tanto no
caminho feliz quanto nos casos de borda.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T015 Atualizado `README.md` mencionando a página
      `/ver/log-classificacoes`
- [x] T016 Rodado `quickstart.md` na íntegra (corrigido um filtro `-k`
      errado no comando de exemplo durante a validação); suíte completa
      passou: 488 passed, 1 skipped
- [x] T017 Atualizada a memória da sessão
      (`feature_015_log_classificacao_manual_status.md`), incluindo nota
      sobre a colisão de numeração "015" com o apelido informal já
      existente (parcelas futuras + backfill)

---

## Dependencies & Execution Order

- **Setup (Phase 1)**: nenhuma tarefa.
- **Foundational (Phase 2)**: bloqueia US1 e US2 (T005/T006 dependem de
  T001/T002).
- **US1 (Phase 3)**: depende só do Foundational. MVP.
- **US2 (Phase 4)**: depende de T005/T006 (mesma implementação) — os
  testes de T011 só fazem sentido depois que elas existem.
- **Polish (Phase 5)**: depende de US1 + US2 completas.

### Parallel Opportunities

- T003 pode rodar em paralelo com o restante do Foundational.
- T004 e T011 podem ser escritos em paralelo (casos diferentes no mesmo
  arquivo de teste), mas ambos dependem de T005/T006 existir pra passar.

---

## Implementation Strategy

### MVP First (User Story 1)

1. Foundational (modelo + repositório de `LogClassificacaoManual`).
2. US1 completa: toda classificação manual passa a gerar um evento,
   visível em `/ver/log-classificacoes`.
3. **PARAR e VALIDAR**: o usuário (ou o agente) consegue responder "o
   que foi classificado manualmente e como?" só olhando a página.

### Incremental Delivery

1. Foundational → modelo/repositório prontos.
2. US1 → histórico visível e correto no caminho feliz (MVP).
3. US2 → confiabilidade do histórico nos casos de borda (reclassificação,
   tentativa sem efeito, tentativa inválida).
