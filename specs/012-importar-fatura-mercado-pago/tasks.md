---

description: "Task list for feature 012: importar fatura do cartão Mercado Pago"
---

# Tasks: Importar fatura do cartão Mercado Pago

**Input**: Design documents from `/specs/012-importar-fatura-mercado-pago/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: Incluídos — mesmo padrão já seguido pelas features 001–011 deste
projeto (constituição, Princípio V: parsing de dado externo exige teste
automatizado + validação com amostra real).

**Organization**: Tarefas agrupadas por user story (spec.md), na mesma
ordem de prioridade declarada lá (US1 é P1; US2 é P2).

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Projeto único (`src/`, `tests/` na raiz) — mesma estrutura das features
001–011.

---

## Phase 1: Setup

- [x] T001 Adicionar `pdfplumber` a `dependencies` em `pyproject.toml`
      (research.md #9) e confirmar que resolve no venv do projeto
      (`pip install -e .`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: identidade de conta e convenção de sinal que o parser (US1)
precisa antes de gravar qualquer transação — sem isso, os encargos
genéricos da fatura seriam classificados com o sinal errado (renda em vez
de gasto).

- [x] T002 Adicionar `"MercadoPago": "mercado_pago"` a `CONTA_CANONICA` e
      um regex `_RE_CARTAO_MERCADO_PAGO` (`^MercadoPago_(\d{4})$` →
      `mercado_pago_<n>`) em `src/services/conta_canonica.py`
      (research.md #5, mesmo padrão do regex genérico já usado para
      `Itaú_<4 dígitos>`)
- [x] T003 [P] Teste unitário em `tests/unit/test_conta_canonica.py`:
      `canonicalizar_conta("MercadoPago") == "mercado_pago"` e
      `canonicalizar_conta("MercadoPago_3258") == "mercado_pago_3258"`
      (cartão não hardcoded, via regex genérico)
- [x] T004 Estender `_eh_conta_cartao()` em
      `src/services/importar_historico_extrato.py` para reconhecer
      qualquer conta canônica iniciada por `"mercado_pago"` como cartão de
      crédito (research.md #6) — positivo = saída, negativo = entrada
- [x] T005 [P] Teste unitário novo em
      `tests/unit/test_convencao_sinal_mercado_pago.py` (arquivo NOVO;
      renomeado de `test_importar_historico_extrato.py` — colide de nome
      de módulo com o arquivo homônimo pré-existente em
      `tests/integration/`, já que o projeto não usa `__init__.py` nos
      subdiretórios de teste): chamar `processar_transacoes()` com um
      registro sintético de conta
      `"MercadoPago"` (encargo, valor positivo) e confirmar
      `tipo == "saida"`; outro registro de conta `"MercadoPago_3258"` com
      valor negativo (estorno) e confirmar `tipo == "entrada"`

**Checkpoint**: conta canônica e convenção de sinal do Mercado Pago
prontas — US1 pode prosseguir sem bloqueio.

---

## Phase 3: User Story 1 - Importar o histórico real da fatura Mercado Pago (Priority: P1) 🎯 MVP

**Goal**: as transações reais da fatura de junho/2026 (compras dos dois
cartões vinculados + encargos da fatura) entram no financiALL sem
duplicata, com natureza classificada e reconciliação automática quando
aplicável — mesma qualidade já entregue para o Itaú.

**Independent Test**: rodar a importação contra o arquivo PDF real e
conferir no banco (`SELECT * FROM transacao WHERE conta LIKE 'mercado_pago%'`)
sem depender de nenhuma outra história.

### Tests for User Story 1

- [x] T006 [P] [US1] Testes unitários do parser em
      `tests/unit/test_importar_fatura_mercado_pago.py`: reconhece a
      seção `Movimentações na fatura` (conta `"MercadoPago"`) e cada seção
      `Cartão ... [****NNNN]` (conta `"MercadoPago_NNNN"`); ignora linha
      `Data Movimentações Valor em R$` e linha `Total R$ ...`; filtra
      lançamento cuja descrição contenha "pagamento da fatura"
      (case-insensitive, research.md #7); infere o ano corretamente a
      partir de `Emitida em: DD/MM/AAAA` (mês do lançamento ≤ mês de
      emissão → mesmo ano; mês > mês de emissão → ano anterior,
      research.md #3); preserva o sufixo "Parcela X de Y" concatenado à
      descrição quando presente (research.md #4); reconhece valor
      precedido de "-" como negativo (estorno); ignora linha de
      lançamento encontrada antes de qualquer cabeçalho de seção
      reconhecido (degradação graciosa, Princípio VII); arquivo sem
      "Emitida em" reconhecível levanta erro
- [x] T007 [P] [US1] Teste de integração em
      `tests/integration/test_fluxo_importar_fatura_mercado_pago.py` (renomeado
      de `test_importar_fatura_mercado_pago.py` — colide de nome de módulo
      com o arquivo homônimo em `tests/unit/`, já que o projeto não usa
      `__init__.py` nos subdiretórios de teste; mesma convenção já usada
      por `test_fluxo_importar_extrato_bb.py`):
      `parsear()` + `processar_transacoes()` ponta a ponta contra um PDF
      sintético (gerado no teste) com múltiplas seções de cartão + seção
      de encargos + lançamento de pagamento a excluir, confirmando
      idempotência ao rodar duas vezes seguidas (nenhuma duplicata na
      segunda execução)

### Implementation for User Story 1

- [x] T008 [US1] Implementar
      `src/services/importar_fatura_mercado_pago.py::parsear(caminho) -> list[dict]`
      usando `pdfplumber` (depende de T001; máquina de estados por
      cabeçalho de seção — research.md #2)
- [x] T009 [US1] Implementar `src/scripts/importar_fatura_mercado_pago.py`
      (CLI — aceita arquivo único ou pasta com `.pdf`, mesma saída/formato
      de `src/scripts/importar_extrato_itau_cartao.py`, contrato em
      `contracts/cli.md`) (depende de T008)
- [x] T010 [US1] Adicionar regras semente de encargos (`JUROS DE MORA`,
      `MULTA POR ATRASO`, `JUROS DO ROTATIVO`, `IOF DO ROTATIVO` →
      `gasto` / Finanças / Tarifas e juros) em
      `src/scripts/regras_semente_natureza.json` (data-model.md,
      research.md #8)

### Real-Data Validation for User Story 1 (MANDATORY — Constitution Principle V)

- [x] T011 [US1] Validar com o arquivo real
      `assets/novos-extratos/mercado-pago-2026-06.pdf` antes de promover
      (dev → main)
  - [x] Dimensão 1 (fidelidade ao total impresso): validado — soma das 25
        transações importadas (`SUM(valor) WHERE conta LIKE
        'mercado_pago%'`) bate **exatamente** com o "Total a pagar"
        impresso na fatura (R$ 1.147,84). **Achado real na primeira
        rodada** (research.md #10): 3 pares de "DL*99 RIDE" no mesmo dia
        com mesmo valor arredondado colidiam no fingerprint — a segunda
        ocorrência de cada par era descartada como "já existente"
        (22 importadas em vez de 25). Corrigido com desambiguação por
        sufixo de ocorrência; depois do fix, 25 importadas / 0 já
        existentes na primeira execução, e reimportar o mesmo arquivo
        confirma idempotência (0 novas / 25 já existentes)
  - [x] Dimensão 2 (taxa de classificação automática): 22 de 25 (88%)
        classificadas automaticamente via cache/regra — comparável à taxa
        do Itaú, sem necessidade de seed adicional além de T010.
        **Achado (research.md #11)**: uma transação (`RecargaPay
        *CRISTINEV`) caiu em `transferencia_interna` por colisão de
        substring com a regra legada `"CRISTINE"` (pré-existente, criada
        para outra fonte) — falso positivo de classificação, não de
        importação; fora do escopo desta feature corrigir a regra legada,
        segue corrigível manualmente em `/ver/transacoes`

### Visual Verification for User Story 1 (Constitution Principle VIII)

- [x] T012 [US1] N/A — esta história não introduz nem muda superfície
      visual (script de importação e regras semente, sem UI) nem
      vendoriza asset de terceiro

**Checkpoint**: US1 completa e testável de forma independente (MVP).

---

## Phase 4: User Story 2 - Continuar recebendo faturas novas do Mercado Pago (Priority: P2)

**Goal**: o usuário consegue importar qualquer fatura nova que baixar daqui
em diante, sozinho, sem duplicar histórico e sem perder parcelas
recorrentes de compras já parceladas.

**Independent Test**: importar uma segunda fatura sintética com uma
parcela recorrente já vista na primeira (mesma compra, parcela seguinte) e
confirmar que ela entra como transação nova, não como duplicata.

### Tests for User Story 2

- [x] T013 [P] [US2] Teste de integração em
      `tests/integration/test_fluxo_importar_fatura_mercado_pago.py`
      confirmando que importar duas faturas sintéticas consecutivas
      contendo a mesma compra parcelada (mesma data original, mesma
      descrição base, mesmo valor, só o número da parcela mudando: "Parcela
      14 de 21" → "Parcela 15 de 21") resulta nas duas parcelas importadas
      como transações distintas — não trata a segunda como "já existente"
      (valida research.md #4 concretamente, FR-007)

### Implementation for User Story 2

- [x] T014 [US2] Nenhuma implementação nova além do que já existe:
      `processar_transacoes()` já é idempotente por fingerprint e
      `importar_fatura_mercado_pago.py` já aceita pasta com múltiplos
      arquivos (T009) — esta história é de validação do fluxo recorrente
      já construído em US1, não de código novo
- [x] T015 [US2] Documentar em `README.md` (seção já existente
      "Importando um extrato bancário novo") o comando de importação da
      fatura Mercado Pago, ao lado dos comandos já documentados para
      Itaú e BB

### Real-Data Validation for User Story 2 (MANDATORY — Constitution Principle V)

- [ ] T016 [US2] Validar quando a próxima fatura real do Mercado Pago (mês
      seguinte à de junho/2026) for baixada: rodar a importação contra ela
      e confirmar que nenhuma parcela recorrente já vista em junho foi
      perdida nem duplicada — **deferido** até o usuário baixar essa
      fatura; retomar nesse momento antes de considerar a importação
      recorrente validada de fato

### Visual Verification for User Story 2 (Constitution Principle VIII)

- [x] T017 [US2] N/A — esta história não introduz nem muda superfície
      visual

**Checkpoint**: US1 + US2 funcionando juntas — histórico real importado e
fluxo recorrente validado (na medida do que já há dado real disponível).

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T018 Rodar `quickstart.md` na íntegra como validação final antes do
      PR para `dev` — Cenários 1, 2 e 4 confirmados contra o arquivo real
      e sintéticos; Cenário 3 (reconciliação com nota fiscal) não
      exercido nesta rodada por falta de nota fiscal correspondente no
      banco de teste, sem bloqueio (mesmo mecanismo já validado para
      Itaú); suíte completa (422 testes) verde
- [ ] T019 Atualizar a memória da sessão
      (`feature_012_importar_fatura_mercado_pago_status.md`) documentando
      o resultado, achados de dado real (T011) e o que ficou pendente
      (T016)

---

## Dependencies & Execution Order

- **Setup (Phase 1)**: sem dependências, roda primeiro.
- **Foundational (Phase 2)**: depende do Setup; bloqueia US1 (T008
  depende de T002/T004 já estarem prontos para o valor/tipo sair
  correto).
- **US1 (Phase 3)**: depende só do Foundational. Pode ser entregue e
  validada isoladamente (MVP).
- **US2 (Phase 4)**: depende de US1 (reaproveita o mesmo parser/CLI) — não
  introduz código novo relevante, só valida o fluxo recorrente e o achado
  crítico da parcela (research.md #4).
- **Polish (Phase 5)**: depende de US1 + US2 completas.

### Parallel Opportunities

- T003 e T005 podem rodar em paralelo com o restante do Foundational
  (arquivos de teste diferentes).
- T006 e T007 podem rodar em paralelo entre si (arquivos diferentes).
- T013 pode ser escrito em paralelo com a implementação de US1, mas só
  roda de fato depois que T008/T009 existirem.

---

## Implementation Strategy

### MVP First (User Story 1)

1. Setup + Foundational.
2. US1 completa, validada com o arquivo real de junho/2026 (T011).
3. **PARAR e VALIDAR**: transações da fatura Mercado Pago no banco, sem
   duplicata, maioria classificada automaticamente, total batendo com o
   "Resumo da fatura" impresso.

### Incremental Delivery

1. Setup + Foundational → conta canônica e convenção de sinal prontas.
2. US1 → histórico real importado (MVP — já resolve a lacuna mais crítica
   apontada pelo usuário).
3. US2 → confirmação de que o fluxo recorrente (parcelas consecutivas
   incluídas) é o mesmo comando, documentado para uso autônomo do
   usuário; validação final com dado real fica pendente até a próxima
   fatura ser baixada.
