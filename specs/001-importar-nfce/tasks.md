---

description: "Task list for feature implementation"
---

# Tasks: Importar Notas Fiscais sem Duplicar

**Input**: Design documents from `/specs/001-importar-nfce/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/api.md](./contracts/api.md), [quickstart.md](./quickstart.md)

**Tests**: Incluídos. `plan.md` (seção Testing), o Princípio V da constituição
("Testável por Construção") e a "Verificação final" de `quickstart.md`
exigem a suíte `pytest tests/unit tests/integration tests/contract`
passando antes de considerar a feature pronta — rodável no Windows (dev)
sem depender do binário real do Tesseract (research.md #16).

**Organization**: Tarefas agrupadas por user story (spec.md) para permitir
implementação e teste independentes de cada uma. Esta é a versão
redesenhada da feature (servidor único no Raspberry Pi + canal de OCR),
substituindo integralmente a versão anterior baseada em CLI local.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: A qual user story a tarefa pertence (US1..US8)
- Caminhos de arquivo exatos incluídos em cada descrição

## Path Conventions

Aplicação web única (single project): `src/`, `tests/`, `infra/` na raiz do
repositório, conforme `plan.md` → Project Structure.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Inicialização do projeto, estrutura de código e provisionamento do Raspberry Pi

- [X] T001 Criar estrutura de diretórios `src/{models,services,storage,worker,api/templates}`, `infra/` e `tests/{unit,integration,contract}` (com `__init__.py` em cada pacote Python) conforme `plan.md` → Project Structure
- [X] T002 Inicializar projeto Python em `pyproject.toml` na raiz com dependências `Flask`, `waitress`, `requests`, `pytesseract`, `Pillow`, `pdf2image`, `pytest` (Python 3.11+, conforme research.md #1)
- [X] T003 [P] Criar `infra/setup-raspberry-pi.sh` — script de provisionamento que instala `python3`, `python3-venv`, `tesseract-ocr`, `tesseract-ocr-por`, `poppler-utils`, `zram-tools` via `apt`, cria o ambiente virtual e instala as dependências do projeto (research.md #14)
- [X] T004 [P] Criar `infra/financiall.service` — unit `systemd` que roda o servidor via `waitress`, com `Restart=on-failure` e início automático no boot (research.md #14)
- [X] T005 [P] Criar `.gitignore` na raiz cobrindo `financiall.db`, diretório de uploads, `__pycache__/`, `.pytest_cache/`, `.venv/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestrutura central que TODA user story depende (modelos, schema SQLite, repositório básico, esqueleto do servidor)

**⚠️ CRITICAL**: Nenhuma user story pode começar antes desta fase estar completa

- [X] T006 [P] Criar modelo `NotaFiscal` (dataclass, `chave_acesso`/`hash_conteudo` opcionais, `canal_origem`, enum de status `completa`/`pendente_revisao`) em src/models/nota_fiscal.py conforme data-model.md
- [X] T007 [P] Criar modelo `ItemNota` (dataclass) em src/models/item_nota.py conforme data-model.md
- [X] T008 Implementar o schema SQLite (`nota_fiscal` com `CHECK` de identidade e índices únicos parciais para `chave_acesso`/`hash_conteudo`, `item_nota`, `envio_ocr`) e gestão de conexão em src/storage/db.py conforme o esquema de referência de data-model.md
- [X] T009 Implementar operações básicas de repositório de notas — `inserir_nota`, `inserir_itens`, `buscar_por_chave_acesso`, `buscar_por_hash_conteudo` — em src/storage/db.py (depende de T006, T007, T008)
- [X] T010 Implementar operações de repositório da fila — `inserir_envio`, `atualizar_status_envio`, `buscar_envio_por_id`, `reconciliar_processando_para_pendente` — em src/storage/db.py (depende de T008)
- [X] T011 [P] Criar o esqueleto do app Flask (factory que registra os blueprints de importação e consulta, ainda vazios) em src/api/app.py
- [X] T012 [P] Criar o entrypoint em src/main.py (cria o app, inicia o worker de OCR em thread de background, roda o servidor via `waitress`)

**Checkpoint**: Fundação pronta — implementação das user stories pode começar

---

## Phase 3: User Story 1 - Importar nota nova via URL ou chave de acesso (Priority: P1) 🎯 MVP

**Goal**: Usuário envia a URL do QR Code ou a chave de acesso de 44 dígitos; o sistema extrai/valida a chave, busca os dados na fonte SEFAZ quando possível e grava um novo registro.

**Independent Test**: enviar `POST /notas` com uma URL válida (ou chave válida) ainda não importada e verificar que a nota aparece em `GET /notas` com os dados obtidos.

### Tests for User Story 1 ⚠️

> **NOTE: Escrever estes testes PRIMEIRO, garantir que falham antes da implementação**

- [X] T013 [P] [US1] Teste unitário de extração de chave a partir de URL e validação de dígito verificador (módulo 11) em tests/unit/test_chave_acesso.py
- [X] T014 [P] [US1] Teste de contrato de `POST /notas` (sucesso completo, entrada inválida) conforme contracts/api.md em tests/contract/test_api_contract.py
- [X] T015 [P] [US1] Teste de integração: importar nota nova via URL e via chave colada, ponta a ponta via cliente de teste do Flask contra SQLite temporário, em tests/integration/test_api.py

### Implementation for User Story 1

- [X] T016 [US1] Implementar extração da chave de 44 dígitos a partir da query string da URL (busca por sequência numérica válida) em src/services/chave_acesso.py conforme research.md #3
- [X] T017 [US1] Implementar normalização de chave colada e validação de comprimento + dígito verificador (módulo 11) em src/services/chave_acesso.py conforme research.md #4 (depende de T016)
- [X] T018 [US1] Implementar decodificação posicional de UF, ano-mês de emissão, CNPJ do emitente e modelo a partir da chave válida em src/services/chave_acesso.py conforme research.md #5 (depende de T017)
- [X] T019 [US1] Implementar busca best-effort dos dados da nota na fonte SEFAZ (timeout curto, apenas para `modelo = 65`) em src/services/sefaz_client.py conforme research.md #6
- [X] T020 [US1] Implementar orquestração do canal URL/chave — validar chave, checar existência prévia por chave, buscar dados, gravar nota e itens — em src/services/importador.py (depende de T009, T018, T019)
- [X] T021 [US1] Implementar a rota `POST /notas` chamando o importador e formatando as respostas em português conforme contracts/api.md em src/api/routes_importar.py (depende de T011, T020)
- [X] T022 [US1] Adicionar tratamento explícito de entrada inválida (status `422`, mensagem em português, sem gravar nada) em src/services/chave_acesso.py e src/api/routes_importar.py (depende de T017, T021)

**Checkpoint**: User Story 1 funcional e testável de forma independente (canal digital completo)

---

## Phase 4: User Story 2 - Importar nota via foto ou PDF escaneado (Priority: P1)

**Goal**: Usuário envia uma foto ou PDF de um cupom fiscal; o sistema confirma o recebimento imediatamente e processa o reconhecimento de texto (OCR) de forma assíncrona e sequencial.

**Independent Test**: enviar `POST /notas/upload` com a foto/PDF de um cupom legível ainda não importado e, após o processamento, verificar via `GET /envios/<id>` e `GET /notas` que a nota foi gravada com os dados extraídos.

### Tests for User Story 2 ⚠️

- [X] T023 [P] [US2] Teste unitário de extração de campos (chave, CNPJ, total, data) a partir de texto de OCR simulado, sem depender do binário real do Tesseract, em tests/unit/test_campos_ocr.py
- [X] T024 [P] [US2] Teste de contrato de `POST /notas/upload` (arquivo aceito, tipo não suportado, nenhum arquivo enviado) conforme contracts/api.md em tests/contract/test_api_contract.py
- [X] T025 [P] [US2] Teste de integração: enviar foto/PDF e consultar `GET /envios/<id>` até o status chegar a `concluido`, em tests/integration/test_api.py

### Implementation for User Story 2

- [X] T026 [US2] Implementar cálculo de hash de conteúdo (SHA-256) e gravação do arquivo recebido em disco em src/services/fila_processamento.py
- [X] T027 [US2] Implementar a rota `POST /notas/upload` — valida tipo de arquivo, calcula hash, enfileira via `inserir_envio` e responde `202` imediatamente, sem esperar o processamento — em src/api/routes_importar.py (depende de T010, T026)
- [X] T028 [US2] Implementar reconhecimento de texto via Tesseract (`pytesseract`) com pré-processamento de imagem (`Pillow`: escala de cinza, binarização) em src/services/ocr_client.py conforme research.md #7
- [X] T029 [US2] Implementar conversão de PDF escaneado em imagem (`pdf2image`) em src/services/pdf_extractor.py conforme research.md #8
- [X] T030 [US2] Implementar heurísticas de extração de campos (chave de acesso, CNPJ, valor total, data, itens) a partir do texto reconhecido em src/services/campos_ocr.py conforme research.md #9 (depende de T023)
- [X] T031 [US2] Implementar o worker sequencial (thread em background, um envio por vez, sem paralelismo) que consome a fila `envio_ocr` em ordem em src/worker/ocr_worker.py conforme research.md #10 (depende de T010, T028, T029, T030)
- [X] T032 [US2] Integrar a inicialização do worker ao processo principal (inicia a thread no startup do servidor) em src/main.py (depende de T012, T031)

**Checkpoint**: User Stories 1 e 2 funcionam de forma independente — os dois canais de entrada gravam notas

---

## Phase 5: User Story 3 - Não duplicar nota já importada (Priority: P1)

**Goal**: O sistema reconhece uma nota já registrada — por chave de acesso ou por hash de conteúdo — e recusa criar um segundo registro, em qualquer canal ou combinação de canais.

**Independent Test**: importar uma nota por um canal, tentar importar a mesma nota novamente (mesmo canal ou canal diferente) e verificar que nenhum novo registro é criado.

### Tests for User Story 3 ⚠️

- [X] T033 [P] [US3] Teste unitário de idempotência por chave de acesso e por hash de conteúdo em tests/unit/test_importador.py
- [X] T034 [P] [US3] Teste de integração: importar a mesma nota por canais diferentes (URL e depois foto da mesma nota) e confirmar que `GET /notas` mostra exatamente um registro, em tests/integration/test_api.py

### Implementation for User Story 3

- [X] T035 [US3] Implementar a checagem *check-before-insert* por `chave_acesso` OU `hash_conteudo` (usando `buscar_por_chave_acesso`/`buscar_por_hash_conteudo` de T009) e retorno dos dados do registro existente sem gravar novo, em src/services/importador.py (depende de T020)
- [X] T036 [US3] Formatar a resposta `"status": "ja_registrada"` (chave mascarada) conforme contracts/api.md na rota `POST /notas` em src/api/routes_importar.py (depende de T035)
- [X] T037 [US3] Aplicar a mesma checagem de dedup na conclusão do processamento do worker, apontando `envio_ocr.nota_fiscal_id` para a nota existente quando o envio corresponder a uma duplicata, em src/worker/ocr_worker.py (depende de T031, T035)

**Checkpoint**: User Stories 1, 2 e 3 funcionam juntas — zero duplicação em qualquer canal

---

## Phase 6: User Story 4 - Registrar nota mesmo quando os dados completos não são obtidos (Priority: P1)

**Goal**: Falha na fonte SEFAZ (canal 1) ou no reconhecimento de texto (canal 2) nunca impede o registro da nota — ela é gravada com o que houver e marcada "pendente de revisão".

**Independent Test**: simular indisponibilidade da fonte SEFAZ e uma foto ilegível e verificar, nos dois casos, que a nota é gravada com status "pendente de revisão", sem erro nem exceção.

### Tests for User Story 4 ⚠️

- [X] T038 [P] [US4] Teste unitário de degradação best-effort do canal URL/chave (falha da fonte SEFAZ resulta em `pendente_revisao`, nunca em exceção) em tests/unit/test_importador.py
- [X] T039 [P] [US4] Teste unitário de robustez do worker (exceção durante OCR ou extração de campos resulta em envio `concluido` apontando para nota `pendente_revisao`, nunca preso em `processando`) em tests/unit/test_fila_processamento.py
- [X] T040 [P] [US4] Teste de integração: fonte SEFAZ indisponível (canal 1) e foto ilegível (canal 2) — nos dois casos a nota é gravada como `pendente_revisao` sem erro `5xx`, em tests/integration/test_api.py

### Implementation for User Story 4

- [X] T041 [US4] Implementar tratamento explícito de exceções na busca à fonte SEFAZ (timeout, erro HTTP, corpo inesperado) em src/services/sefaz_client.py (depende de T019)
- [X] T042 [US4] Implementar o cálculo do `status` da nota (`completa`/`pendente_revisao`) com base nos campos ausentes, para os dois canais, em src/services/importador.py (depende de T020, T041)
- [X] T043 [US4] Implementar tratamento explícito de exceções no reconhecimento de texto/extração de campos do worker, garantindo que todo envio conclui apontando para uma nota (ao menos com `hash_conteudo`) em src/worker/ocr_worker.py (depende de T031)
- [X] T044 [US4] Implementar a reconciliação de envios presos em `processando` para `pendente` na inicialização do worker em src/services/fila_processamento.py conforme research.md #11 (depende de T010)

**Checkpoint**: Falha de qualquer fonte externa (SEFAZ ou OCR) nunca impede o registro da nota, em nenhum canal

---

## Phase 7: User Story 5 - Consultar status de processamento de um envio por foto/PDF (Priority: P2)

**Goal**: Usuário consulta se um envio de foto/PDF está pendente, em processamento, ou concluído (completo ou com dados incompletos).

**Independent Test**: enviar uma foto/PDF e, antes e depois do processamento terminar, consultar `GET /envios/<id>` e verificar que o status reflete corretamente o estado.

### Tests for User Story 5 ⚠️

- [X] T045 [P] [US5] Teste de contrato de `GET /envios/<id>` (pendente, processando, concluído completo, concluído com dados incompletos, envio não encontrado) conforme contracts/api.md em tests/contract/test_api_contract.py
- [X] T046 [P] [US5] Teste de integração: consultar o status de um envio antes e depois do processamento terminar, em tests/integration/test_api.py

### Implementation for User Story 5

- [X] T047 [US5] Implementar a rota `GET /envios/<envio_id>` retornando o status e, quando concluído, os dados da nota resultante, em src/api/routes_consulta.py (depende de T010, T011)

**Checkpoint**: Usuário consegue acompanhar qualquer envio de foto/PDF do início ao fim

---

## Phase 8: User Story 6 - Listar notas importadas (Priority: P2)

**Goal**: Usuário consulta a lista de notas registradas, com filtro opcional por mês.

**Independent Test**: com pelo menos uma nota importada, solicitar `GET /notas` e verificar que os dados aparecem corretamente; filtrar por mês e verificar que só as notas daquele mês aparecem.

### Tests for User Story 6 ⚠️

- [X] T048 [P] [US6] Teste de contrato do formato de `GET /notas` (com filtro `?mes=`, e com base vazia) conforme contracts/api.md em tests/contract/test_api_contract.py
- [X] T049 [P] [US6] Teste de integração: importar notas em meses diferentes e listar com e sem filtro de mês, em tests/integration/test_api.py

### Implementation for User Story 6

- [X] T050 [US6] Implementar a consulta `listar_notas` (ordenada por `data_emissao`/`ano_mes_emissao` desc, com filtro opcional por mês) em src/storage/db.py (depende de T008)
- [X] T051 [US6] Implementar a rota `GET /notas` em src/api/routes_consulta.py (depende de T011, T050)

**Checkpoint**: Todas as notas registradas podem ser consultadas e filtradas por mês

---

## Phase 9: User Story 7 - Ver gasto parcial do mês corrente (Priority: P2)

**Goal**: Usuário consulta o total já gasto no mês corrente, com base nas notas fiscais já registradas.

**Independent Test**: com notas importadas no mês corrente, solicitar `GET /notas/resumo/mes-atual` e verificar que o total está correto e identificado como parcial.

### Tests for User Story 7 ⚠️

- [X] T052 [P] [US7] Teste unitário de cálculo do gasto do mês corrente (soma em centavos, ignora notas com `valor_total` nulo) em tests/unit/test_resumo.py
- [X] T053 [P] [US7] Teste de contrato do formato de `GET /notas/resumo/mes-atual` (com notas e com base vazia) conforme contracts/api.md em tests/contract/test_api_contract.py

### Implementation for User Story 7

- [X] T054 [US7] Implementar o cálculo do gasto parcial do mês corrente em src/services/resumo.py (depende de T008)
- [X] T055 [US7] Implementar a rota `GET /notas/resumo/mes-atual` em src/api/routes_consulta.py (depende de T011, T054)

**Checkpoint**: Usuário acompanha o gasto do mês em andamento a qualquer momento

---

## Phase 10: User Story 8 - Ver histórico de gasto por mês (Priority: P3)

**Goal**: Usuário consulta o total gasto de meses anteriores ao corrente, um valor por mês.

**Independent Test**: com notas importadas em meses diferentes, solicitar `GET /notas/resumo/historico` e verificar que os totais de cada mês anterior estão corretos.

### Tests for User Story 8 ⚠️

- [X] T056 [P] [US8] Teste unitário de agrupamento do histórico por mês (apenas meses anteriores ao corrente) em tests/unit/test_resumo.py
- [X] T057 [P] [US8] Teste de contrato do formato de `GET /notas/resumo/historico` (com notas e com base vazia) conforme contracts/api.md em tests/contract/test_api_contract.py
- [X] T058 [P] [US8] Teste de integração: notas em meses diferentes retornam o histórico correto, ordenado do mais recente para o mais antigo, em tests/integration/test_api.py

### Implementation for User Story 8

- [X] T059 [US8] Implementar o cálculo do histórico de gasto por mês (meses anteriores ao corrente) em src/services/resumo.py (depende de T054)
- [X] T060 [US8] Implementar a rota `GET /notas/resumo/historico` em src/api/routes_consulta.py (depende de T011, T059)

**Checkpoint**: Todas as user stories funcionam de forma independente

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Melhorias que atravessam múltiplas user stories e ativação em produção

- [X] T061 [P] Revisar todo logging em src/services/, src/worker/ e src/api/ para garantir que chave de acesso, CNPJ, CPF, valores monetários e texto bruto de OCR nunca aparecem em texto claro (Princípio IV, research.md #15)
- [X] T062 [P] Criar um formulário HTML simples de upload em src/api/templates/upload.html e a rota que o serve, para facilitar o envio de foto pelo celular sem precisar de `curl`
- [X] T063 Executar infra/setup-raspberry-pi.sh no Raspberry Pi real, habilitar e iniciar o serviço financiall.service via systemd
- [X] T064 Validar manualmente os 8 cenários de quickstart.md contra o servidor real rodando no Raspberry Pi
- [X] T065 Rodar a suíte completa `pytest tests/unit tests/integration tests/contract` (no Windows, sem depender do Tesseract real) e confirmar 100% de sucesso (Princípio V) antes de considerar a feature pronta para revisão

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — pode começar imediatamente (inclui o provisionamento do Raspberry Pi, que roda em paralelo ao desenvolvimento do código)
- **Foundational (Phase 2)**: Depende do Setup — BLOQUEIA todas as user stories
- **US1 (Phase 3)**: Depende apenas da Foundational
- **US2 (Phase 4)**: Depende apenas da Foundational — independente de US1 (canal de entrada diferente), mas reaproveita o mesmo repositório de notas
- **US3 (Phase 5)**: Depende da Foundational e reaproveita `importador.py` (US1, T020) e o worker (US2, T031) — não pode ser testada de forma útil sem ao menos um dos dois canais já gravando notas
- **US4 (Phase 6)**: Depende da Foundational e reaproveita `sefaz_client.py`/`importador.py` (US1) e o worker (US2)
- **US5 (Phase 7)**: Depende da Foundational e do repositório de fila (T010); independente de US1/US3/US4, mas precisa de US2 (T031) para ter envios reais para consultar
- **US6 (Phase 8)**: Depende apenas da Foundational (T008) — independente das demais
- **US7 (Phase 9)**: Depende apenas da Foundational (T008) — independente das demais
- **US8 (Phase 10)**: Depende de US7 (T054, reaproveita a mesma lógica de agrupamento) — não é totalmente independente por design (mesma computação, filtro diferente)
- **Polish (Phase 11)**: Depende de todas as user stories desejadas estarem completas; T063 (provisionar o Pi de verdade) pode acontecer a qualquer momento em paralelo, desde que antes de T064

### User Story Dependencies

- **US1 (P1)**: Sem dependência de outra story — MVP do canal digital
- **US2 (P1)**: Sem dependência de US1 — MVP do canal de OCR; pode ser desenvolvida em paralelo a US1 por não compartilhar arquivos de implementação (compartilha só o repositório de notas da Foundational)
- **US3 (P1)**: Depende de US1 e/ou US2 já gravarem notas para ter o que deduplicar
- **US4 (P1)**: Depende de US1 (canal SEFAZ) e US2 (worker de OCR) já existirem para adicionar tratamento de falha a cada um
- **US5 (P2)**: Depende de US2 (fila) existir para ter envios reais
- **US6 (P2)**: Independente — só precisa do schema (Foundational)
- **US7 (P2)**: Independente — só precisa do schema (Foundational)
- **US8 (P3)**: Depende de US7 (reaproveita a lógica de cálculo de resumo)

### Within Each User Story

- Testes (quando incluídos) MUST ser escritos e falhar antes da implementação
- Modelos antes de serviços
- Serviços antes de rotas da API
- Implementação core antes de integração com o worker/servidor

### Parallel Opportunities

- T003, T004, T005 (Setup) podem rodar em paralelo entre si (e com T002)
- T006, T007, T011, T012 (Foundational) podem rodar em paralelo entre si
- Após a Foundational: **US1 e US2 podem ser desenvolvidas em paralelo** (não compartilham arquivos de implementação); US6 e US7 também podem avançar em paralelo a qualquer momento após a Foundational
- Todos os testes marcados `[P]` dentro de uma mesma story podem rodar em paralelo
- T061 e T062 (Polish) podem rodar em paralelo; T063 (provisionar o Pi) pode rodar em paralelo ao desenvolvimento, mas T064 exige que T063 e as user stories relevantes já estejam prontas

---

## Parallel Example: Foundational

```bash
Task: "Criar modelo NotaFiscal em src/models/nota_fiscal.py"
Task: "Criar modelo ItemNota em src/models/item_nota.py"
Task: "Criar esqueleto do app Flask em src/api/app.py"
Task: "Criar entrypoint em src/main.py"
```

## Parallel Example: User Story 1 + User Story 2 (após Foundational)

```bash
# Time A trabalha no canal digital (US1):
Task: "Extração de chave da URL em src/services/chave_acesso.py"
Task: "Busca best-effort na SEFAZ em src/services/sefaz_client.py"

# Time B trabalha no canal de OCR (US2), em paralelo:
Task: "Reconhecimento de texto via Tesseract em src/services/ocr_client.py"
Task: "Conversão de PDF em imagem em src/services/pdf_extractor.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Phase 1: Setup (incluindo iniciar o provisionamento do Pi em paralelo)
2. Completar Phase 2: Foundational (CRÍTICO — bloqueia todas as stories)
3. Completar Phase 3: User Story 1
4. **PARAR e VALIDAR**: testar User Story 1 de forma independente (Cenário 1 de quickstart.md)
5. Entregar/demonstrar se pronto — já é um importador funcional do canal digital

### Incremental Delivery

1. Setup + Foundational → Fundação pronta (código + Pi provisionado)
2. US1 → Testar independentemente → canal digital funcionando (URL/chave)
3. US2 → Testar independentemente → canal de OCR funcionando (foto/PDF)
4. US3 → Testar independentemente → garante idempotência nos dois canais (não-negociável, Princípio II)
5. US4 → Testar independentemente → nenhuma falha externa (SEFAZ ou OCR) trava a importação
6. US5 → Testar independentemente → usuário acompanha o processamento assíncrono
7. US6 → Testar independentemente → usuário confere o que foi importado
8. US7 → Testar independentemente → primeira visão de gasto do mês corrente
9. US8 → Testar independentemente → visão histórica complementar
10. Polish → revisão de log sensível, formulário de upload, ativação real no Pi, validação final de quickstart.md, suíte completa

### Ordem sugerida de execução

**Foundational → US1 e US2 em paralelo → US3 → US4 → US5, US6 e US7 em
paralelo → US8 → Polish**. US1 e US2 não compartilham arquivos de
implementação e podem ser feitas por pessoas/sessões diferentes ao mesmo
tempo; US3 e US4 precisam dos dois canais existindo para fazer sentido
completo (embora tecnicamente pudessem começar com apenas um canal pronto).

---

## Notes

- [P] tasks = arquivos diferentes, sem dependências
- [Story] label mapeia a tarefa à user story correspondente para rastreabilidade
- Verificar que os testes falham antes de implementar (TDD)
- Fazer commit após cada tarefa ou grupo lógico
- Parar em cada checkpoint para validar a story de forma independente
- Nenhum dado sensível (chave de acesso, CNPJ, CPF, valores, texto bruto de OCR) em log de texto claro em nenhuma tarefa (Princípio IV)
- O provisionamento do Raspberry Pi (T003, T004, T063) é parte do escopo desta feature, não um pré-requisito assumido — o usuário não tem experiência prévia de administração Linux/Raspberry Pi
