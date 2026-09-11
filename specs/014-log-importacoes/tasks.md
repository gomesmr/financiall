---

description: "Task list for feature 014: log de importações"
---

# Tasks: Log de importações

**Input**: Design documents from `/specs/014-log-importacoes/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Incluídos — mesmo padrão já seguido pelas features 001–013
deste projeto.

**Organization**: Tarefas agrupadas por user story (spec.md), na mesma
ordem de prioridade declarada lá (US1 é P1; US2 é P2).

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Projeto único (`src/`, `tests/` na raiz) — mesma estrutura das features
001–013.

---

## Phase 1: Setup

Sem tarefas — nenhuma dependência nova (research.md): usa só
`sqlite3`/`datetime` da stdlib, já em uso em todo o projeto.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: modelo e repositório de `LogImportacao` são a base que
tanto US1 (ver o histórico) quanto US2 (confiar no histórico em casos de
borda) precisam antes de existir qualquer gravação ou leitura.

- [x] T001 Criar dataclass `LogImportacao` em
      `src/models/log_importacao.py` (mesmo padrão de
      `models/compromisso_futuro.py`): campos `data_hora`, `fonte`,
      `periodo_inicio`, `periodo_fim`, `importadas`, `ja_existentes`,
      `puladas`, `classificadas_automaticamente`, `pendentes_natureza`,
      `reconciliadas`, `ambiguas`, `id` (data-model.md)
- [x] T002 Em `src/storage/db.py`: adicionar `CREATE TABLE IF NOT EXISTS
      log_importacao` ao `SCHEMA` (data-model.md), e as funções
      `inserir_log_importacao(log: LogImportacao, db_path) -> int` e
      `listar_logs_importacao(db_path) -> list[LogImportacao]`
      (`ORDER BY data_hora DESC, id DESC` — data-model.md), seguindo o
      mesmo padrão de `criar_compromisso_futuro`/`listar_compromissos_futuros`
- [x] T003 [P] Testes unitários em
      `tests/unit/test_storage_log_importacao.py`: inserir um
      `LogImportacao` e recuperá-lo por `listar_logs_importacao`; duas
      inserções aparecem na ordem certa (mais recente primeiro); campos
      `fonte`/`periodo_inicio`/`periodo_fim` nulos são persistidos e
      lidos corretamente como `None`

**Checkpoint**: modelo e repositório prontos e testados — US1 e US2
podem prosseguir sem bloqueio mútuo.

---

## Phase 3: User Story 1 - Saber quando foi a última importação de cada fonte, sem acessar o servidor (Priority: P1) 🎯 MVP

**Goal**: toda importação bem-sucedida (por qualquer caminho de entrada)
gera um evento de histórico visível numa página nova, com fonte, período
e contagens corretas, ordenados do mais recente pro mais antigo.

**Independent Test**: rodar uma importação com transações novas (script
CLI ou upload web) e conferir que um evento aparece no topo de
`/ver/log-importacoes` com os dados certos.

### Tests for User Story 1

- [x] T004 [P] [US1] Teste unitário em
      `tests/unit/test_log_importacao_processar_transacoes.py`: chamar
      `processar_transacoes()` com uma lista de registros válidos (mesma
      fonte, datas variadas) e conferir, via `listar_logs_importacao`,
      que um `LogImportacao` foi gravado com `fonte` igual à dos
      registros, `periodo_inicio`/`periodo_fim` iguais ao mínimo/máximo
      das datas de entrada, e as 7 contagens iguais ao
      `ImportarExtratoResumo` retornado (research.md #1/#2/#3)

### Implementation for User Story 1

- [x] T005 [US1] Em `src/services/importar_historico_extrato.py`,
      `processar_transacoes()`: ao final do laço, calcular `fonte`
      (primeiro `registro.get("fonte")` não vazio da lista de entrada,
      `None` se a lista for vazia — research.md #2), `periodo_inicio`/
      `periodo_fim` (`min`/`max` de `registro.get("data")` entre todos os
      registros de entrada com data não vazia, `None`/`None` se nenhum
      tiver — research.md #3), montar um `LogImportacao` com essas
      informações mais os campos do `resumo`, e gravar via
      `storage_db.inserir_log_importacao()` (depende de T001/T002)
- [x] T006 [US1] Criar blueprint `src/api/routes_log_importacoes.py`
      com `GET /ver/log-importacoes` (`pagina_ativa="log_importacoes"`),
      chamando `storage_db.listar_logs_importacao()` e renderizando
      `log_importacoes.html` (contracts/api.md); registrar o blueprint
      em `src/api/app.py`
- [x] T007 [US1] Criar `src/api/templates/log_importacoes.html` (mesmo
      padrão visual Argon das demais páginas "Ver", ex.
      `compromissos_futuros.html`): tabela com as colunas de
      contracts/api.md, mostrando "—" quando `fonte`/período forem nulos;
      adicionar link "Log de importações" na navegação de `base.html`

### Real-Data Validation for User Story 1

- [x] T008 [US1] N/A — esta feature não faz parsing de dado externo
      novo (Princípio V não se aplica); ela só lê o `resumo` já calculado
      pelos parsers existentes, cuja validação real já ocorreu nas
      features 010–015

### Visual Verification for User Story 1 (Constitution Principle VIII)

- [x] T009 [US1] Nenhum asset de terceiro vendorizado — N/A para
      checagem de integridade de formato. Screenshot via navegador
      headless de `/ver/log-importacoes` com 2 eventos reais de teste
      confirmou tabela correta (fonte, período, 7 contagens) e nav
      destacando "Log de importações"; sem erro de console em nenhum
      dos dois estados verificados

**Checkpoint**: US1 completa e testável de forma independente (MVP) —
qualquer importação já passa a aparecer na página.

---

## Phase 4: User Story 2 - Confiar no histórico mesmo quando a importação não traz nada novo (Priority: P2)

**Goal**: reimportar um arquivo já processado, ou processar registros
sem data válida, ou uma execução que falha no meio, se comportam
corretamente no histórico (evento com zero novidade / sem período / sem
evento nenhum, respectivamente).

**Independent Test**: reimportar um conjunto de registros já
100% existente no banco e conferir um evento novo com `importadas=0`;
processar registros sem nenhuma data válida e conferir evento sem
período; forçar uma exceção no meio do laço e conferir que nenhum
evento novo aparece.

### Tests for User Story 2

- [x] T010 [P] [US2] Testes unitários em
      `tests/unit/test_log_importacao_processar_transacoes.py`:
      (a) chamar `processar_transacoes()` duas vezes com os mesmos
      registros — o segundo evento de log tem `importadas=0` e
      `ja_existentes` igual ao total de registros válidos;
      (b) chamar com registros cujo campo `"data"` está sempre vazio —
      o evento gravado tem `periodo_inicio`/`periodo_fim` `None`;
      (c) forçar uma exceção durante o laço (ex.: monkeypatch em
      `storage_db.inserir_transacao` para lançar em algum item) e
      conferir, via `listar_logs_importacao`, que nenhum evento novo foi
      gravado para aquela chamada (research.md #5)

### Implementation for User Story 2

- [x] T011 [US2] Confirmado: a implementação de T005 satisfez os três
      casos de T010 sem nenhuma mudança adicional (os 5 testes de
      T004+T010 passaram de primeira) — o cálculo de período/fonte já é
      resiliente a data vazia/lista vazia, e o `INSERT` do log já
      acontece só após o laço terminar sem exceção

### Real-Data Validation for User Story 2

- [x] T012 [US2] N/A — mesma justificativa de T008; os casos de borda
      aqui são sintéticos por natureza (arquivo vazio, dado sem data,
      falha simulada), não amostra real de fonte externa

### Visual Verification for User Story 2 (Constitution Principle VIII)

- [x] T013 [US2] Screenshot via navegador headless de
      `/ver/log-importacoes` confirmou o caso "0 importadas / 2 já
      existentes" (reimportação) exibido com clareza junto do evento
      original, e o estado vazio ("Nenhuma importação registrada
      ainda.") também renderizando corretamente — sem erro de console
      em nenhum dos dois

**Checkpoint**: US1 + US2 completas — o histórico é confiável tanto no
caminho feliz quanto nos casos de borda.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T014 Atualizado `README.md` (seção "Importando um extrato bancário
      novo") mencionando a página `/ver/log-importacoes` como forma de
      consultar o histórico de importações sem acesso ao servidor
- [x] T015 Rodado `quickstart.md` na íntegra: os 3 comandos passaram (5,
      3 e 3 testes respectivamente); suíte completa também passou (476
      passed, 1 skipped)
- [x] T016 Atualizada a memória da sessão
      (`feature_014_log_importacoes_status.md`) documentando o resultado,
      incluindo nota sobre a colisão de numeração "014" com o apelido
      informal já existente do importador Open Finance Itaú

---

## Dependencies & Execution Order

- **Setup (Phase 1)**: nenhuma tarefa.
- **Foundational (Phase 2)**: bloqueia US1 e US2 (T005 depende de
  T001/T002).
- **US1 (Phase 3)**: depende só do Foundational. MVP.
- **US2 (Phase 4)**: depende de T005 (mesma implementação) — os testes de
  T010 só fazem sentido depois que T005 existe; T011 é, na prática, uma
  confirmação/ajuste fino sobre o que T005 já implementou.
- **Polish (Phase 5)**: depende de US1 + US2 completas.

### Parallel Opportunities

- T003 pode rodar em paralelo com o restante do Foundational (arquivo de
  teste próprio).
- T004 e T010 podem ser escritos em paralelo (casos diferentes no mesmo
  arquivo de teste), mas ambos dependem de T005 existir para passar de
  fato.

---

## Implementation Strategy

### MVP First (User Story 1)

1. Foundational (modelo + repositório de `LogImportacao`).
2. US1 completa: toda importação passa a gerar um evento, visível em
   `/ver/log-importacoes`.
3. **PARAR e VALIDAR**: o usuário (ou o agente) consegue responder
   "quando foi a última importação desta fonte?" só olhando a página.

### Incremental Delivery

1. Foundational → modelo/repositório prontos.
2. US1 → histórico visível e correto no caminho feliz (MVP — resolve o
   problema central: nada de SSH pra saber o que já foi importado).
3. US2 → confiabilidade do histórico nos casos de borda (reimportação
   sem novidade, dado sem data, falha no meio do processamento).
