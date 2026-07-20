# Tasks: Importar Extrato Bancário

**Input**: Design documents from `/specs/010-importar-extrato-bancario/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, contracts/cli.md

**Tests**: incluídas — o projeto já segue esse padrão (Princípio V: dedup,
classificação e parsing de entrada externa exigem teste automatizado).

**Organization**: tarefas agrupadas por user story (spec.md), em ordem de
prioridade (US1/US2/US3 = P1, US4/US5 = P2, US6 = P3).

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [ ] T001 Adicionar `xlrd>=2.0` a `dependencies` em `pyproject.toml` (research.md #10)
- [ ] T002 [P] Criar `src/scripts/regras_semente_natureza.json` migrando a lista `REGRAS` de `assets/finalcial/Financeiro/importar_extrato.py` para o formato `{padrao, natureza, categoria, subcategoria, prioridade}` (research.md #5) — `categoria`/`subcategoria` só quando `natureza="gasto"`, mapeados para `TAXONOMIA_RESERVADA_EXTRATO` (Moradia, Transporte, Educação, Lazer, Serviços e assinaturas, Vestuário)

**Checkpoint**: dependência instalada, conteúdo das regras-semente pronto para o seed da Fase 3.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: schema, modelos e operações de persistência de que toda user story depende.

**⚠️ CRITICAL**: nenhuma user story pode começar antes desta fase.

- [ ] T003 Adicionar tabelas `transacao`, `estabelecimento`, `cache_descricao_natureza`, `regra_natureza` a `SCHEMA` em `src/storage/db.py` (data-model.md), com os índices únicos (`fingerprint`, `nota_fiscal_id` parcial, `documento`/`descricao_normalizada` parciais em `estabelecimento`) e chamada em `init_db()`
- [ ] T004 [P] Criar `src/models/transacao.py` (dataclass `Transacao`, enums `TipoTransacao`/`NaturezaTransacao`, constante `NATUREZAS_VALIDAS`)
- [ ] T005 [P] Criar `src/models/estabelecimento.py` (dataclass `Estabelecimento`)
- [ ] T006 Criar `src/services/conta_canonica.py` com `CONTA_CANONICA` (dict) e `canonicalizar_conta(conta)` (research.md #2)
- [ ] T007 Criar `src/services/fingerprint_transacao.py` com `calcular_fingerprint(data_iso, descricao, valor, conta_canonica)` — `sha1(...)[:16]` (research.md #1), reaproveitando `src/services/normalizacao.py::normalizar_descricao` já existente
- [ ] T008 Implementar `_row_to_transacao`/`_row_to_estabelecimento`, `inserir_transacao` (idempotente por fingerprint — em `IntegrityError`, retorna o `id` já existente via `buscar_transacao_por_fingerprint`) e `buscar_transacao_por_fingerprint` em `src/storage/db.py`
- [ ] T009 [P] Implementar `buscar_transacao_por_id`, `buscar_estabelecimento_por_id` em `src/storage/db.py`

**Checkpoint**: schema, modelos e persistência básica prontos — user stories podem começar.

---

## Phase 3: User Story 1 - Classificar automaticamente a natureza de cada transação (Priority: P1)

**Goal**: toda transação recebe `natureza` (e `categoria_id` quando gasto) automaticamente via cache/regra, sem exigir ação manual para o que já é conhecido.

**Independent Test**: aplicar o motor a transações com descrições conhecidas do corpus legado (ex.: "TBI ALUGUEL", "PAGTO SALARIO", "FATURA PAGA") e confirmar a natureza correta sem ação manual.

### Tests for User Story 1

- [ ] T010 [P] [US1] Testes unitários da cascata em `tests/unit/test_classificacao_natureza.py`: cache → regra mais específica → pendente; descrição vazia/None vai direto para pendente (mesmo padrão de `test_classificacao_itens.py`)

### Implementation for User Story 1

- [ ] T011 [US1] Implementar `classificar_natureza_transacao(transacao_id, natureza, categoria_id, metodo, descricao_normalizada, db_path)` em `src/storage/db.py` (upsert em `cache_descricao_natureza`, sem tabela de histórico — data-model.md)
- [ ] T012 [US1] Criar `src/services/classificacao_natureza.py::classificar_natureza(descricao, db_path)` — cascata cache → regra ativa mais específica (por prioridade) → `(None, None, None)` (research.md #6)
- [ ] T013 [US1] Criar `src/scripts/seed_regras_natureza.py` (`seed_regras_natureza(db_path)` + `main`), lendo `regras_semente_natureza.json` (T002), resolvendo `categoria_id` via `TAXONOMIA_RESERVADA_EXTRATO` já semeada, idempotente por (`padrao`, `natureza`) — mesmo padrão de `seed_taxonomia_categorizacao.py::seed_regras`

### Real-Data Validation for User Story 1

- [ ] T014 [US1] Validar a cascata com o corpus real de descrições do `registro.json` (`assets/finalcial/Financeiro/extrato/registro.json`) antes de promover (dev → main)
  - [ ] Dimensão 1: descrições de cartão de crédito (contas 9073/2486) — natureza majoritariamente `gasto`
  - [ ] Dimensão 2: descrições de conta corrente (Itaú_CC) — mistura de `gasto`, `renda`, `pagamento_fatura`, `transferencia_interna`
  - [ ] Dimensão 3: descrições do Flash VR — natureza `gasto`/`renda` num formato de texto distinto dos demais

### Visual Verification for User Story 1

- [ ] T015 [US1] N/A — nenhuma superfície visual nova nesta história (motor de classificação puro)

**Checkpoint**: motor de classificação de natureza funcional e validado com dado real, isoladamente.

---

## Phase 4: User Story 2 - Trazer o histórico de transações para a base única (Priority: P1)

**Goal**: migrar as 418 transações do `registro.json` legado para `transacao`, idempotente, com contas consolidadas e classificação automática (US1) já aplicada.

**Independent Test**: rodar a importação sobre o histórico e confirmar que todas as transações aparecem na base; rodar de novo e confirmar que a contagem não muda.

### Tests for User Story 2

- [ ] T016 [P] [US2] Teste de integração em `tests/integration/test_importar_historico_extrato.py`: fixture JSON sintética com as 6 contas do legado (incluindo as duas grafias duplicadas), confirmando consolidação de conta (research.md #2), idempotência (rodar duas vezes) e que registro sem `data`/`valor`/`conta` reconhecíveis é pulado sem abortar o lote

### Implementation for User Story 2

- [ ] T017 [US2] Criar `src/services/importar_historico_extrato.py`: lê e faz `json.load` do `registro.json` (falha aqui aborta tudo, FR-024); para cada registro — canonicaliza conta (T006), deriva `tipo` do sinal do valor, calcula fingerprint (T007), classifica natureza/categoria (T012), grava via `inserir_transacao` (T008, idempotente), e — quando `natureza=gasto` — tenta reconciliar (chamada adiantada da Fase 5, `reconciliar_transacao`; se ainda não implementada nesta ordem de execução, implementar T017 e a Fase 5 em conjunto). Retorna resumo (`ImportarExtratoResumo`: importadas, já existentes, puladas, classificadas automaticamente, pendentes)
- [ ] T018 [US2] Criar `src/scripts/importar_historico_extrato.py` (CLI: `main(argv)`, `--db-path`, mensagens em português conforme contracts/cli.md, exit codes 0/1)

### Real-Data Validation for User Story 2

- [ ] T019 [US2] Rodar a migração completa contra o `registro.json` real (418 transações, 6 contas) antes de promover (dev → main)
  - [ ] Dimensão 1: primeira execução — `SELECT COUNT(*) FROM transacao` bate com "importadas" da saída
  - [ ] Dimensão 2: segunda execução (idempotência) — nenhuma linha nova, tudo "já existente"
  - [ ] Dimensão 3: `SELECT DISTINCT conta FROM transacao` não contém as duas grafias antigas da mesma conta física

### Visual Verification for User Story 2

- [ ] T020 [US2] N/A — script de linha de comando, sem superfície visual

**Checkpoint**: histórico real migrado e validado; US1+US2 juntas já entregam a base de transações classificadas.

---

## Phase 5: User Story 3 - Ver o gasto do mês sem contar a mesma compra duas vezes (Priority: P1)

**Goal**: transação com `natureza=gasto` reconcilia com a nota fiscal correspondente quando existe; o resumo mensal soma transação + nota não reconciliada, nunca as duas.

**Independent Test**: importar uma nota e a transação de cartão correspondente (mesmo valor, data próxima); confirmar que o resumo do mês soma o gasto uma única vez, e que desfazer a reconciliação mantém a soma correta.

### Tests for User Story 3

- [ ] T021 [P] [US3] Testes unitários em `tests/unit/test_reconciliacao.py`: match único (concilia), zero candidatos (segue sem vínculo), múltiplos candidatos (fica ambíguo, nenhum vínculo automático), janela de data diferente por tipo de conta (research.md #3)
- [ ] T022 [P] [US3] Estender `tests/unit/test_resumo.py`: gasto do mês soma transação(gasto) + nota não reconciliada; nota reconciliada não soma duas vezes; desvincular volta a somar pela nota
- [ ] T023 [P] [US3] Estender `tests/contract/test_api_contract.py`: `GET /transacoes/reconciliacao/pendentes`, `PUT /transacoes/<id>/nota`, `DELETE /transacoes/<id>/nota`, e a composição estendida de `GET /notas/resumo/mes-atual|historico|categorias`

### Implementation for User Story 3

- [ ] T024 [US3] Implementar `reconciliar_transacao(transacao_id, db_path)`, `listar_reconciliacoes_pendentes(db_path)`, `desvincular_reconciliacao(transacao_id, db_path)`, `vincular_reconciliacao_manual(transacao_id, nota_fiscal_id, db_path)` em `src/storage/db.py` (índice único em `transacao.nota_fiscal_id` garante 1:1)
- [ ] T025 [US3] Criar `src/services/reconciliacao.py::tentar_reconciliar(transacao, db_path)` — janela de data por tipo de conta (research.md #3), critério de valor exato, retorna `"reconciliada"|"ambigua"|"sem_candidato"`
- [ ] T026 [US3] Estender `src/services/resumo.py` (`_query_resumo_por_mes`, `gasto_mes_corrente`, `historico_meses_anteriores`, `gasto_por_categoria_item`): somar `transacao` (natureza=gasto) + `nota_fiscal` não reconciliada, ao vivo (data-model.md, research.md #8) — transação reconciliada usa os itens da nota para granularidade fina quando existirem, senão usa `transacao.categoria_id`
- [ ] T027 [US3] Criar `src/api/routes_transacoes.py` com `GET /transacoes/reconciliacao/pendentes`, `PUT /transacoes/<id>/nota`, `DELETE /transacoes/<id>/nota` (contracts/api.md); registrar o blueprint em `src/api/app.py`
- [ ] T028 [US3] Estender `pagina_nota_detalhe` em `src/api/routes_consulta.py` e `src/api/templates/nota_detalhe.html`: exibir a transação reconciliada (conta, data do lançamento) e botão "Desvincular" (aciona `DELETE /transacoes/<id>/nota`)

### Real-Data Validation for User Story 3

- [ ] T029 [US3] Rodar a reconciliação sobre o histórico real migrado (US2) cruzado com as notas fiscais reais já importadas (features 001/004) antes de promover (dev → main)
  - [ ] Dimensão 1: compra de cartão com nota NFC-e correspondente real — concilia corretamente e o total do mês não muda ao conciliar
  - [ ] Dimensão 2: caso ambíguo real (se existir no dado — duas compras do mesmo valor no mesmo dia) cai na fila em vez de decidir por aproximação

### Visual Verification for User Story 3

- [ ] T030 [US3] Capturar screenshot real (navegador headless) de `/ver/notas/<id>` com uma nota reconciliada e checar ausência de erro de console, antes de promover (dev → main)

**Checkpoint**: US1+US2+US3 completam o núcleo não-negociável (P1) — gasto do mês correto e sem dupla contagem.

---

## Phase 6: User Story 4 - Classificar manualmente as transações que a regra não resolveu (Priority: P2)

**Goal**: fila de transações com natureza pendente, agrupada por descrição, classificável em lote; correção manual vira cache.

**Independent Test**: pegar uma transação pendente, classificar via fila, confirmar que uma transação futura de mesma descrição já chega classificada.

### Tests for User Story 4

- [ ] T031 [P] [US4] Estender `tests/contract/test_api_contract.py`: `GET /transacoes/pendentes`, `POST /transacoes/pendentes/classificar-grupo`, `PUT /transacoes/<id>/natureza`

### Implementation for User Story 4

- [ ] T032 [US4] Implementar `listar_transacoes_pendentes_natureza(db_path)` (agrupado por `descricao_normalizada`, mesmo formato de `listar_itens_pendentes`), `classificar_grupo_pendente_natureza(descricao_normalizada, natureza, categoria_id, db_path)` e `atribuir_natureza_manual(transacao_id, natureza, categoria_id, db_path)` em `src/storage/db.py`
- [ ] T033 [US4] Adicionar `GET /transacoes/pendentes`, `POST /transacoes/pendentes/classificar-grupo`, `PUT /transacoes/<id>/natureza` em `src/api/routes_transacoes.py` (contracts/api.md)
- [ ] T034 [US4] Adicionar `GET /ver/transacoes/pendentes` em `src/api/routes_transacoes.py` + criar `src/api/templates/transacoes_pendentes.html` (combina fila de natureza pendente e fila de reconciliação ambígua da US3 — mesmo padrão visual/JS de `pendentes.html`/`classificacao.js`)

### Real-Data Validation for User Story 4

- [ ] T035 [US4] N/A — a fila opera sobre o mesmo dado real já validado em US1/US2; nenhuma nova entrada externa é introduzida por esta história

### Visual Verification for User Story 4

- [ ] T036 [US4] Capturar screenshot real (navegador headless) de `/ver/transacoes/pendentes` com pelo menos um grupo pendente e checar ausência de erro de console, antes de promover (dev → main)

**Checkpoint**: nenhuma transação fica pendente para sempre — usuário sempre tem um caminho de resolução manual.

---

## Phase 7: User Story 5 - Identificar o estabelecimento de cada transação (Priority: P2)

**Goal**: transações sem nota ganham nome fantasia e tipo de estabelecimento, via CNPJ/CPF (quando disponível) ou descrição normalizada.

**Independent Test**: atribuir nome fantasia e tipo a um grupo pendente; confirmar que `gasto_por_estabelecimento` passa a contá-lo.

### Tests for User Story 5

- [ ] T037 [P] [US5] Testes unitários em `tests/unit/test_estabelecimento.py`: extração de documento (11/14 dígitos) da descrição; cascata de identidade (nota reconciliada com CNPJ > documento na descrição > fallback por descrição normalizada); atualização in-place quando um estabelecimento por descrição ganha documento depois (FR-019)
- [ ] T038 [P] [US5] Estender `tests/contract/test_api_contract.py`: `GET /estabelecimentos/pendentes`, `PUT /estabelecimentos/<id>`

### Implementation for User Story 5

- [ ] T039 [US5] Criar `src/services/estabelecimento.py::resolver_estabelecimento(transacao, db_path)` — cascata de research.md #9 (regex de 11/14 dígitos para extrair documento de descrições PIX)
- [ ] T040 [US5] Implementar `obter_ou_criar_estabelecimento_por_documento`, `obter_ou_criar_estabelecimento_por_descricao`, `promover_estabelecimento_para_documento` (atualiza in-place, FR-019), `listar_estabelecimentos_pendentes(db_path)`, `atribuir_estabelecimento(estabelecimento_id, nome_fantasia, tipo_categoria_id, db_path)` em `src/storage/db.py`
- [ ] T041 [US5] Invocar `resolver_estabelecimento` a partir de `importar_historico_extrato` (T017) e do parser recorrente (Fase 8), e novamente após reconciliação bem-sucedida (T024/T025) — para aplicar a promoção por CNPJ quando a nota chega depois
- [ ] T042 [US5] Criar `src/api/routes_estabelecimentos.py` com `GET /estabelecimentos/pendentes`, `PUT /estabelecimentos/<id>`, `GET /ver/estabelecimentos/pendentes`; registrar blueprint em `src/api/app.py`; criar `src/api/templates/estabelecimentos_pendentes.html`
- [ ] T043 [US5] Estender `gasto_por_estabelecimento` em `src/services/resumo.py`: incluir transações sem nota, agrupadas por `estabelecimento.tipo_categoria_id` (FR-020)

### Real-Data Validation for User Story 5

- [ ] T044 [US5] Validar a extração de documento e a cascata de identidade contra transações reais de PIX do `registro.json` (conta Itaú_CC) antes de promover (dev → main)
  - [ ] Dimensão 1: descrição de PIX com CPF/CNPJ do recebedor embutido — extrai corretamente
  - [ ] Dimensão 2: descrição de compra de cartão sem nenhum documento — cai no fallback por descrição normalizada

### Visual Verification for User Story 5

- [ ] T045 [US5] Capturar screenshot real (navegador headless) de `/ver/estabelecimentos/pendentes` com pelo menos um grupo pendente e checar ausência de erro de console, antes de promover (dev → main)

**Checkpoint**: gasto por estabelecimento completo, incluindo transações sem nota fiscal.

---

## Phase 8: User Story 6 - Importar extratos novos continuamente (Priority: P3)

**Goal**: parser de fatura de cartão Itaú (XLS) alimenta a base recorrentemente, reaproveitando a mesma persistência/classificação/reconciliação da migração histórica.

**Independent Test**: rodar o parser sobre um arquivo de fatura novo; confirmar que as transações aparecem classificadas e nenhuma duplica as já migradas.

### Tests for User Story 6

- [ ] T046 [P] [US6] Teste unitário em `tests/unit/test_importar_extrato_itau_cartao.py` com um `.xls` sintético mínimo (via `xlwt` ou fixture binária pré-gravada em `tests/fixtures/`) cobrindo linha de compra válida, linha de cabeçalho/total (ignorada) e linha "pagamento efetuado" (ignorada, mesmo filtro do script legado)

### Implementation for User Story 6

- [ ] T047 [US6] Criar `src/services/importar_extrato_itau_cartao.py::parsear(caminho_arquivo)` — porta a lógica de `parse_itau_cartao_xls` do script legado (via `xlrd`) para retornar `list[Transacao]` não persistidas (mesmos filtros de cabeçalho/total/"pagamento efetuado")
- [ ] T048 [US6] Refatorar a persistência comum de T017 (fingerprint, classificação, reconciliação, resolução de estabelecimento) para uma função reaproveitável `processar_transacoes(transacoes, db_path)` em `src/services/importar_historico_extrato.py` (ou módulo compartilhado), usada tanto pela migração histórica quanto pelo parser recorrente
- [ ] T049 [US6] Criar `src/scripts/importar_extrato_itau_cartao.py` (CLI: aceita arquivo ou pasta, mesmo padrão de `argv`/`--db-path`/mensagens de `importar_historico.py`, contracts/cli.md)

### Real-Data Validation for User Story 6

- [ ] T050 [US6] Rodar o parser contra pelo menos 2 arquivos de fatura Itaú reais de `assets/finalcial/Financeiro/extrato/marcelo/*.xls` antes de promover (dev → main)
  - [ ] Dimensão 1: fatura já coberta pelo `registro.json` (cartão 2486 ou 9073) — nenhuma transação duplicada
  - [ ] Dimensão 2: fatura "parcial" (fechamento antecipado, ex.: `*-parcial-2026-07.xls`) — mesma garantia de não duplicar mesmo com nome de arquivo diferente

### Visual Verification for User Story 6

- [ ] T051 [US6] N/A — script de linha de comando, sem superfície visual

**Checkpoint**: todas as 6 user stories completas e independentemente funcionais.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T052 [P] Rodar a suíte completa (`pytest`) e confirmar 100% verde antes de commit final
- [ ] T053 Rodar `python -m src.scripts.seed_regras_natureza` seguido de `python -m src.scripts.importar_historico_extrato` contra o `registro.json` real, de ponta a ponta, seguindo `quickstart.md`
- [ ] T054 Revisar que nenhuma rotina nova imprime/loga CPF, CNPJ, conta ou valor em texto claro (Princípio IV) — checagem manual de `importar_historico_extrato.py`, `importar_extrato_itau_cartao.py`, `routes_transacoes.py`, `routes_estabelecimentos.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1)**: sem dependências.
- **Foundational (Fase 2)**: depende da Fase 1 — bloqueia todas as user stories.
- **US1 (Fase 3)**: depende só da Fase 2.
- **US2 (Fase 4)**: depende da Fase 2 e de US1 (T012, classificação) — a migração já classifica ao importar. Também depende de T024/T025 (US3, reconciliação) para o passo final de `importar_historico_extrato`; implementar US2 e o núcleo de US3 em conjunto quando possível, ou deixar a chamada de reconciliação como no-op até US3 estar pronta.
- **US3 (Fase 5)**: depende da Fase 2; integra com US1 (natureza=gasto como gatilho) e US2 (opera sobre transações já migradas), mas os testes unitários (T021/T022) são independentes.
- **US4 (Fase 6)**: depende da Fase 2 e de US1 (mesmo domínio, `natureza`); reaproveita a fila de reconciliação ambígua de US3 na mesma página (T034).
- **US5 (Fase 7)**: depende da Fase 2; integra com US3 (promoção de identidade ao reconciliar, T041) mas a resolução por descrição funciona sem US3.
- **US6 (Fase 8)**: depende da Fase 2 e reaproveita diretamente a persistência de US2 (T048).
- **Polish (Fase 9)**: depende de todas as user stories desejadas estarem completas.

### Parallel Opportunities

- T004/T005 (modelos) em paralelo.
- T010, T016, T021+T022+T023, T031, T037+T038, T046 (testes de cada história) em paralelo entre si, dentro da própria história.
- US4 e US5 podem ser implementadas em paralelo depois que US1/US2/US3 (P1) estiverem completas — não têm dependência direta uma da outra.

---

## Implementation Strategy

### MVP First

1. Fase 1 (Setup) + Fase 2 (Foundational).
2. Fase 3 (US1) + Fase 4 (US2) + Fase 5 (US3) — as três P1, entregues juntas: é o núcleo não-negociável (classificação + migração + reconciliação sem dupla contagem). **Parar e validar** com dado real antes de seguir.
3. Fase 6 (US4) e Fase 7 (US5) — P2, filas de gerenciamento manual.
4. Fase 8 (US6) — P3, parser recorrente.
5. Fase 9 (Polish).

### Incremental Delivery

Cada fase de user story termina num checkpoint testável isoladamente; dá para
parar depois de qualquer checkpoint e já ter valor entregue (ex.: parar após
US1+US2+US3 já resolve o objetivo central da spec, mesmo sem as filas
manuais nem o parser recorrente).
