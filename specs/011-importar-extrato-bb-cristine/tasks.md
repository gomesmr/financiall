---

description: "Task list for feature 011: importar extrato BB (Cristine) e visão por titular"
---

# Tasks: Importar extrato BB (Cristine) e visão por titular

**Input**: Design documents from `/specs/011-importar-extrato-bb-cristine/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: Incluídos — mesmo padrão já seguido pelas features 001–010 deste
projeto (constituição, Princípio V: parsing de dado externo exige teste
automatizado + validação com amostra real).

**Organization**: Tarefas agrupadas por user story (spec.md), na mesma ordem
de prioridade declarada lá (US1 e US2 são P1; US3 é P2).

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Projeto único (`src/`, `tests/` na raiz) — mesma estrutura das features
001–010.

---

## Phase 1: Setup

- [x] T001 Adicionar `openpyxl` a `dependencies` em `pyproject.toml`
      (research.md #3) e confirmar que resolve no venv do projeto
      (`pip install -e .`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: infraestrutura mínima que tanto o parser (US1) quanto o filtro
de resumo (US2) precisam — sem quebrar nada da feature 010 já em produção.

- [x] T002 Adicionar `"BB_Cristine": "bb_cristine_cc"` a `CONTA_CANONICA`
      em `src/services/conta_canonica.py` (research.md #4)
- [x] T003 [P] Teste unitário para a nova entrada em
      `tests/unit/test_conta_canonica.py`: `canonicalizar_conta("BB_Cristine")
      == "bb_cristine_cc"` e `eh_conta_debito("bb_cristine_cc") is True`

**Checkpoint**: conta canônica do BB pronta — US1 e US2 podem prosseguir sem
bloqueio mútuo.

---

## Phase 3: User Story 1 - Importar o histórico real do extrato BB da Cristine (Priority: P1) 🎯 MVP

**Goal**: as transações reais dela (jan–mai/2026) entram no financiALL sem
duplicata, com natureza classificada e reconciliação automática quando
aplicável — mesma qualidade já entregue para o Marcelo na feature 010.

**Independent Test**: rodar a importação contra os 5 arquivos reais e
conferir no banco (`SELECT * FROM transacao WHERE titular='cristine'`) sem
depender de nenhuma outra história.

### Tests for User Story 1

- [x] T004 [P] [US1] Testes unitários do parser em
      `tests/unit/test_importar_extrato_bb.py`: pula linhas "Saldo
      Anterior"/"Saldo do dia" (research.md #6); converte valor em formato
      BR (`"1.234,56"`, `"-500,00"`) para float com sinal correto;
      `titular` sempre `"cristine"` (research.md #7); usa "Detalhes" como
      descrição removendo o prefixo de timestamp `"dd/mm hh:mm "`, caindo
      para "Lançamento" quando "Detalhes" vier vazio (research.md #5);
      `conta` sempre `"BB_Cristine"` (canonicalizada depois por
      `processar_transacoes`, não pelo parser)
- [x] T005 [P] [US1] Teste de integração em
      `tests/integration/test_importar_extrato_bb.py`: `parsear()` +
      `processar_transacoes()` ponta a ponta contra uma amostra sintética
      no formato real (múltiplas linhas incluindo linhas de saldo e uma
      transferência para o Marcelo), confirmando idempotência ao rodar
      duas vezes seguidas (nenhuma duplicata na segunda execução)

### Implementation for User Story 1

- [x] T006 [US1] Implementar `src/services/importar_extrato_bb.py::parsear(caminho) -> list[dict]`
      (depende de T002; espelha `src/services/importar_extrato_itau_cartao.py`
      — colunas Data/Lançamento/Detalhes/N° documento/Valor/Tipo Lançamento,
      via `openpyxl`)
- [x] T007 [US1] Implementar `src/scripts/importar_extrato_bb.py` (CLI —
      aceita arquivo único ou pasta, mesma saída/formato de
      `src/scripts/importar_extrato_itau_cartao.py`, contrato em
      `contracts/cli.md`) (depende de T006)
- [x] T008 [US1] Adicionar regras semente para o vocabulário da Cristine em
      `src/scripts/regras_semente_natureza.json` (CDC BB, Consignação BB,
      salário via "SECRETARIA MUNICIPAL DA FAZENDA", CRB, Tarifa Bancária
      BB, entre outras recorrentes) usando `assets/finalcial/Financeiro/Cristine.xlsx`
      (tabela "LANÇAMENTOS REAIS" de cada aba) como gabarito (research.md #9)
- [x] T009 [US1] Adicionar regra semente `transferencia_interna` para
      transferência entre o casal (padrão de descrição "MARCELO RENATO
      GOMES" no extrato da Cristine; confirmar/adicionar o padrão
      equivalente do lado do Marcelo se ainda não coberto) (research.md #8)

### Real-Data Validation for User Story 1 (MANDATORY — Constitution Principle V)

- [x] T010 [US1] Validar com os 5 arquivos reais de
      `assets/finalcial/Financeiro/extrato/cristine/*.xlsx` antes de
      promover (dev → main)
  - [x] Dimensão 1 (consistência entre meses): rodado contra jan (61
        importadas, 48 classificadas automaticamente) e mai (51 importadas,
        41 classificadas) — parser e regras funcionam nos dois extremos do
        período sem ajuste extra
  - [x] Dimensão 2 (sobreposição real entre arquivos): confirmado — importar
        os 6 arquivos em sequência (jan, fev, mar, abr, abr_01, mai) resulta
        em 278 importadas + 12 já-existentes, mesmo total do processamento
        em lote da pasta inteira; 10 das 11 transações de `042026.xlsx`
        reaparecem em `042026_01.xlsx` como "já existente" (zero duplicata)

### Visual Verification for User Story 1 (Constitution Principle VIII)

- [x] T011 [US1] N/A — esta história não introduz nem muda superfície
      visual (script de importação e regras semente, sem UI) nem vendoriza
      asset de terceiro

**Checkpoint**: US1 completa e testável de forma independente.

---

## Phase 4: User Story 2 - Ver o gasto do mês quebrado por titular (Priority: P1)

**Goal**: `/ver/resumo` e `/ver/transacoes` mostram o total e o
detalhamento de cada titular separadamente, além do consolidado do casal,
sem que transferências entre os dois distorçam o saldo.

**Independent Test**: com transações de ambos os titulares no banco (real,
via US1, ou sintéticas), abrir o resumo filtrado por cada titular e
conferir que só as transações daquele titular aparecem.

### Tests for User Story 2

- [x] T012 [P] [US2] Testes de contrato em `tests/contract/test_api_contract.py`:
      `GET /ver/resumo?mes=<m>&titular=cristine` só reflete transações/notas
      dela; `GET /ver/resumo?mes=<m>` (sem `titular`) continua consolidado
      (regressão); `GET /ver/transacoes?titular=marcelo` idem
- [x] T013 [P] [US2] Testes unitários em `tests/unit/test_resumo.py`:
      `resumo_de_mes`, `saldo_do_mes`, `gasto_por_categoria_item`,
      `gasto_por_estabelecimento` filtram corretamente quando `titular` é
      informado (cobrindo tanto a origem nota_fiscal quanto transacao) e
      continuam consolidados quando `titular=None` (regressão explícita)

### Implementation for User Story 2

- [x] T014 [US2] Adicionar parâmetro `titular: str | None = None` a
      `_query_resumo_por_mes`/`resumo_de_mes`/`gasto_mes_corrente`/
      `historico_meses_anteriores` em `src/services/resumo.py`, filtrando
      por `nota_fiscal.titular` e `transacao.titular` nas duas pontas do
      `UNION ALL`
- [x] T015 [US2] Adicionar parâmetro `titular` a `saldo_do_mes` em
      `src/services/resumo.py` (filtra a query de entradas por
      `transacao.titular` e repassa para `resumo_de_mes`)
- [x] T016 [US2] Adicionar parâmetro `titular` a `gasto_por_categoria_item`
      e `gasto_por_estabelecimento` em `src/services/resumo.py`
- [x] T017 [US2] Adicionar parâmetro `titular` a
      `storage_db.listar_transacoes` (mesmo padrão de `categoria_id` já
      existente)
- [x] T018 [US2] `routes_consulta.py::pagina_resumo` lê `titular` de
      `request.args` e repassa às funções de `resumo_service`;
      `routes_transacoes.py::pagina_transacoes` idem para
      `listar_transacoes` (depende de T014–T017)
- [x] T019 [US2] `resumo.html`: adicionar seletor de titular (Todos /
      Marcelo / Cristine), mesmo padrão de botões/`?titular=` já usado em
      `notas.html`
- [x] T020 [US2] `transacoes.html`: mesmo seletor de titular

### Real-Data Validation for User Story 2 (MANDATORY — Constitution Principle V)

- [ ] T021 [US2] Validar com dado real do Pi dev, após US1 já ter importado
      o histórico da Cristine, antes de promover (dev → main)
  - [ ] Dimensão 1 (mês com renda atípica de ambos): mar/2026 — PLR do
        Marcelo + salário maior da Cristine no mesmo mês; conferir que o
        saldo por titular reflete cada renda corretamente
  - [ ] Dimensão 2 (mês com transferência real entre o casal): confirmar
        que a transferência não aparece como gasto nem renda de nenhum
        lado, e que a soma dos dois saldos individuais bate com o saldo
        conjunto (SC-003)

### Visual Verification for User Story 2 (Constitution Principle VIII)

- [x] T022 [US2] Nenhum asset de terceiro vendorizado — N/A para checagem
      de integridade de formato
- [x] T023 [US2] Capturar screenshot via navegador headless de
      `/ver/resumo` e `/ver/transacoes` em cada estado do seletor de
      titular (Todos/Marcelo/Cristine) e confirmar ausência de erro de
      console, antes de promover para produção

**Checkpoint**: US1 + US2 funcionando juntas — dá para ver o gasto do mês
de cada um separadamente, com dado real.

---

## Phase 5: User Story 3 - Continuar recebendo extratos novos (Priority: P2)

**Goal**: o usuário consegue importar qualquer extrato novo (Itaú ou BB)
que baixar daqui em diante, sozinho, sem duplicar histórico.

**Independent Test**: importar um arquivo com período parcialmente
sobreposto ao já importado e confirmar que só o delta entra.

### Tests for User Story 3

- [ ] T024 [P] [US3] Teste de integração confirmando que rodar
      `importar_extrato_bb` contra dois arquivos sintéticos de meses
      consecutivos com sobreposição parcial só importa o delta (reaproveita
      a base de T005 com dois arquivos distintos)

### Implementation for User Story 3

- [ ] T025 [US3] Nenhuma implementação nova além do que já existe:
      `processar_transacoes()` já é idempotente por fingerprint e
      `importar_extrato_bb.py`/`importar_extrato_itau_cartao.py` já aceitam
      pasta com múltiplos arquivos — esta história é de validação do fluxo
      recorrente já construído em US1, não de código novo
- [ ] T026 [US3] Documentar em `AGENTS.md` (ou `README.md`, conforme
      convenção já usada no projeto) o passo a passo "baixei um extrato
      novo, e agora?" para os dois formatos (Itaú `.xls` e BB `.xlsx`) —
      comando exato a rodar, sem depender de mim numa sessão futura

### Real-Data Validation for User Story 3 (MANDATORY — Constitution Principle V)

- [ ] T027 [US3] Validar rodando `importar_extrato_bb` e
      `importar_extrato_itau_cartao` de novo contra os mesmos arquivos
      reais já importados nas validações de US1, confirmando 100% "já
      existente(s)", 0 duplicata
  - [ ] Dimensão 1: reimportação idêntica (mesmo arquivo, sem mudança)
  - [ ] Dimensão 2: arquivo novo real, se o usuário já tiver baixado um até
        este ponto da implementação (extrato de junho/2026 em diante do BB
        ou do Itaú); se ainda não houver arquivo novo disponível, simular
        com uma cópia editada de um arquivo real cobrindo um período que
        avança além do já importado

### Visual Verification for User Story 3 (Constitution Principle VIII)

- [ ] T028 [US3] N/A — esta história não introduz nem muda superfície
      visual

**Checkpoint**: histórico + visão por titular + fluxo recorrente, todos
funcionando com dado real.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T029 [P] Revisar `AGENTS.md`/`README.md` quanto a menções desatualizadas
      ao escopo "só Marcelo" da feature 010, se houver
- [ ] T030 Rodar `quickstart.md` na íntegra como validação final antes do
      PR para `dev`
- [ ] T031 Atualizar a memória da sessão
      (`feature_011_importar_extrato_bb_cristine_status.md`) documentando
      o resultado, achados de dado real e o que ficou pendente

---

## Dependencies & Execution Order

- **Setup (Phase 1)**: sem dependências, roda primeiro.
- **Foundational (Phase 2)**: depende do Setup; bloqueia US1 e US2 (T006 e
  T014 dependem de T002).
- **US1 (Phase 3)**: depende só do Foundational. Pode ser entregue e
  validada isoladamente (MVP).
- **US2 (Phase 4)**: depende só do Foundational estruturalmente, mas a
  Real-Data Validation (T021) depende de US1 já ter importado dado real da
  Cristine para ter o que comparar.
- **US3 (Phase 5)**: depende de US1 (reaproveita o mesmo parser/CLI) — não
  introduz código novo, só valida o fluxo recorrente.
- **Polish (Phase 6)**: depende de US1+US2+US3 completas.

### Parallel Opportunities

- T003 pode rodar em paralelo com o restante do Foundational.
- Dentro de cada história, as tarefas marcadas `[P]` (testes, arquivos
  diferentes) podem rodar em paralelo entre si.
- US1 e US2 podem ser implementadas em paralelo por pessoas diferentes após
  o Foundational — a única serialização real é a Real-Data Validation de
  US2 (T021), que precisa do dado real que US1 importa.

---

## Implementation Strategy

### MVP First (User Story 1)

1. Setup + Foundational.
2. US1 completa, validada com os 5 arquivos reais (T010).
3. **PARAR e VALIDAR**: histórico da Cristine no banco, sem duplicata,
   maioria classificada automaticamente.

### Incremental Delivery

1. Setup + Foundational → base pronta.
2. US1 → histórico real importado (MVP — já resolve a lacuna mais crítica
   apontada pelo usuário).
3. US2 → visão por titular no resumo/transações, usando o dado real de US1
   para validar.
4. US3 → confirmação de que o fluxo recorrente (histórico + futuro) é o
   mesmo comando, documentado para uso autônomo do usuário.
