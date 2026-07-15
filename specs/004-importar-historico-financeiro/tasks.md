---

description: "Task list for feature implementation"
---

# Tasks: Importar Histórico Financeiro

**Input**: Design documents from `/specs/004-importar-historico-financeiro/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/cli.md](./contracts/cli.md), [quickstart.md](./quickstart.md)

**Tests**: Incluídos. `plan.md` (seção Testing) e a "Verificação final" de
`quickstart.md` exigem a suíte `pytest tests/unit tests/integration
tests/contract` passando antes de considerar a feature pronta.

**Real-Data Validation (Princípio V da constituição)**: **se aplica** a
esta feature — diferente das features 002/003, a rotina processa dado de
proveniência externa (histórico de outro sistema, não digitado pelo
usuário na nossa UI). Teste sintético (fixture pequena) e validação com o
arquivo real do usuário são duas barreiras distintas — a segunda é
tarefa própria na fase de User Story 1 (T013), não pulável por já ter
passado nos testes automatizados.

**Organization**: Tarefas agrupadas por user story (spec.md) para permitir
implementação e teste independentes de cada uma.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: A qual user story a tarefa pertence (US1..US3)
- Caminhos de arquivo exatos incluídos em cada descrição

## Path Conventions

Aplicação web única (single project) + script CLI: `src/`, `tests/` na
raiz do repositório, mesma estrutura das features 001-003 (ver `plan.md`
→ Project Structure).

---

## Phase 1: Setup (Shared Infrastructure)

Não há inicialização de projeto nova — reaproveita 100% da estrutura,
dependências e configuração já existentes. Nenhuma tarefa de Setup.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Coluna, modelo e operações de repositório que TODA user story depende

**⚠️ CRITICAL**: Nenhuma user story pode começar antes desta fase estar completa

- [X] T001 Adicionar a coluna `titular` em `nota_fiscal` via `ALTER TABLE` idempotente (mesmo padrão de `categoria_id`) em src/storage/db.py → `init_db()`, conforme data-model.md
- [X] T002 Adicionar o campo `titular` a `NotaFiscal` (src/models/nota_fiscal.py) e lê-lo em `_row_to_nota` (src/storage/db.py) (depende de T001)
- [X] T003 Implementar `inserir_nota_com_itens(nota, itens, db_path) -> int` — grava nota e itens numa única transação — em src/storage/db.py conforme research.md #6
- [X] T004 Adicionar o parâmetro `titular` a `listar_notas` (filtro opcional, mesmo padrão de `mes`) em src/storage/db.py (depende de T002)

**Checkpoint**: Fundação pronta — implementação das user stories pode começar

---

## Phase 3: User Story 1 - Trazer o histórico de notas para a base única (Priority: P1) 🎯 MVP

**Goal**: Rodar a importação sobre o arquivo de histórico grava na base toda nota que ainda não existe, com itens, sem duplicar as que já existem, e sem quebrar por causa de um registro malformado isolado.

**Independent Test**: rodar `python -m src.scripts.importar_historico <arquivo>` sobre um arquivo de fixture e verificar, via `GET /notas`, que as notas dele aparecem com seus itens.

### Tests for User Story 1 ⚠️

> **NOTE: Escrever estes testes PRIMEIRO, garantir que falham antes da implementação**

- [X] T005 [P] [US1] Teste unitário: mapeamento de um registro sintético do histórico para `NotaFiscal`/`ItemNota` — conversão de valor (reais→centavos), data (`DD/MM/YYYY`→`YYYY-MM-DD`), `canal_origem` a partir de `fonte`, `valor_total_item` preferindo `vl_liquido` — tests/unit/test_importar_historico.py
- [X] T006 [P] [US1] Teste unitário: `importar_historico` grava notas novas com itens; nota cuja chave já existe na base não é gravada de novo (idempotência) — tests/unit/test_importar_historico.py
- [X] T007 [P] [US1] Teste de integração: rodar a importação sobre um arquivo de fixture e conferir via `GET /notas` que as notas aparecem com itens, status `completa` e sem categoria — tests/integration/test_api.py

### Implementation for User Story 1

- [X] T008 [US1] Implementar o mapeamento de um registro do histórico (chave, cnpj, emitente, data, total, itens, conversões de valor/data/canal) em src/services/importar_historico.py conforme data-model.md e research.md #2/#3/#4/#5
- [X] T009 [US1] Implementar a orquestração do lote — `importar_historico(caminho_arquivo, db_path) -> ResumoImportacao` (contagens: importadas, já existentes, puladas) — checando `buscar_por_chave_acesso` antes de cada gravação e usando `inserir_nota_com_itens` em src/services/importar_historico.py (depende de T003, T008)
- [X] T010 [US1] Implementar o tratamento de arquivo ausente ou JSON inválido (aborta com erro claro, nada é gravado) e de registro malformado sem chave reconhecível (pulado, contado à parte, não aborta o lote) em src/services/importar_historico.py conforme contracts/cli.md e research.md #7 (depende de T009)
- [X] T011 [US1] Criar o entrypoint CLI (`argparse`, `--db-path` opcional, resumo em português, códigos de saída) em src/scripts/importar_historico.py conforme contracts/cli.md (depende de T009, T010)
- [X] T012 [P] [US1] Criar src/scripts/__init__.py (pacote novo)

### Real-Data Validation for User Story 1 (MANDATORY — Princípio V da constituição)

> **NOTE: Esta é uma barreira distinta dos "Tests" acima, não uma extensão deles.** Os testes
> sintéticos confirmam que o código trata os casos já previstos; esta barreira confirma que ele
> sobrevive ao contato com uma amostra real que não foi construída por quem escreveu o teste.
> Não marcar como concluído só porque os testes acima passam.

- [X] T013 [US1] Validar com o arquivo real do usuário (`assets/finalcial/nf-tracking/notas.json`) antes de promover esta história (dev → main), conforme quickstart.md — **nunca imprimir/logar chave, CNPJ, emitente ou valor real** (Princípio IV), só contagens
  - [X] Dimensão 1 — proveniência: registros com `fonte` `'qr'`, `'pdf'` e ausente (confirma que `canal_origem` é mapeado corretamente nos três casos, não só no caminho feliz) — confirmado: `foto_pdf` (9) e `url_chave` (13) no arquivo real
  - [X] Dimensão 2 — completude do registro: registros com todos os campos esperados presentes vs. registros com algum campo ausente (confirma degradação sem quebrar o lote) — confirmado: 0 campos nulos neste lote real, sem quebra
  - [X] Dimensão 3 — titular: notas dos dois titulares presentes no arquivo real (marcelo e cristine) — confirmado: marcelo (21), cristine (1)

**Checkpoint**: User Story 1 funcional e testável de forma independente — o histórico real já está na base

---

## Phase 4: User Story 2 - Saber de quem é cada nota (Priority: P2)

**Goal**: Cada nota mostra seu titular na listagem/detalhe, e o usuário consegue filtrar a listagem por titular.

**Independent Test**: com notas de titulares diferentes na base, abrir `/ver/notas`, conferir que cada uma mostra o titular, e que `?titular=marcelo` restringe a lista.

### Tests for User Story 2 ⚠️

- [X] T014 [P] [US2] Teste de integração: `GET /notas?titular=marcelo` retorna só as notas daquele titular; `GET /notas` sem filtro retorna todas, cada uma com o campo `titular` — tests/integration/test_api.py
- [X] T015 [P] [US2] Teste de contrato: `/ver/notas` exibe o titular de cada nota e `/ver/notas?titular=cristine` restringe a listagem renderizada — tests/contract/test_api_contract.py

### Implementation for User Story 2

- [X] T016 [US2] Adicionar o campo `titular` a `nota_to_dict` em src/api/routes_importar.py (depende de T002)
- [X] T017 [US2] Adicionar o filtro `titular` a `pagina_notas` e a `listar_notas` (JSON) em src/api/routes_consulta.py, usando o parâmetro de `listar_notas` de T004 (depende de T004)
- [X] T018 [US2] Adicionar a coluna "Titular" e links de filtro (Todos / Marcelo / Cristine) em src/api/templates/notas.html (depende de T017)

**Checkpoint**: User Stories 1 e 2 funcionam juntas — histórico importado e organizável por titular

---

## Phase 5: User Story 3 - Reexecutar a importação com segurança (Priority: P3)

**Goal**: Rodar a importação de novo (mesmo arquivo, ou arquivo com notas novas) nunca duplica o que já foi importado.

**Independent Test**: rodar a importação duas vezes seguidas sobre o mesmo arquivo de fixture e confirmar que a segunda execução não altera a contagem de notas na base.

Nenhuma implementação nova nesta fase — a garantia vem de T009 (US1),
que já checa `buscar_por_chave_acesso` antes de cada gravação. Esta fase
só cobre esse comportamento com testes próprios, incluindo o caso de
registro malformado dentro do lote.

### Tests for User Story 3 ⚠️

- [X] T019 [P] [US3] Teste unitário: rodar `importar_historico` duas vezes sobre o mesmo arquivo de fixture — a segunda execução conta `0` notas importadas e a mesma contagem de "já existentes" da primeira — tests/unit/test_importar_historico.py (depende de T009)
- [X] T020 [P] [US3] Teste unitário: um arquivo de fixture com um registro malformado (sem chave reconhecível) no meio de registros válidos importa todos os válidos e conta o malformado como pulado, sem abortar o lote — tests/unit/test_importar_historico.py (depende de T010)

**Checkpoint**: Todas as user stories funcionam de forma independente — reexecução e dado heterogêneo comprovadamente seguros

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Revisão final e validação ponta a ponta

- [X] T021 [P] Revisar `src/services/importar_historico.py` e `src/scripts/importar_historico.py` garantindo que nenhuma chave de acesso, CNPJ, emitente ou valor monetário real aparece em qualquer mensagem, log ou saída (Princípio IV)
- [X] T022 Rodar a suíte completa `pytest tests/unit tests/integration tests/contract` e confirmar 100% de sucesso antes de promover a feature (dev → main)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Vazia — nada a fazer
- **Foundational (Phase 2)**: Sem dependências externas — BLOQUEIA todas as user stories
- **US1 (Phase 3)**: Depende apenas da Foundational
- **US2 (Phase 4)**: Depende da Foundational (T002, T004) — independente de US1 na implementação, mas só faz sentido testar com notas já importadas (US1) na base
- **US3 (Phase 5)**: Depende de US1 (T009, T010) — sem implementação própria, só teste
- **Polish (Phase 6)**: Depende de todas as user stories completas

### User Story Dependencies

- **US1 (P1)**: Sem dependência de outra story — MVP: histórico importado
- **US2 (P2)**: Depende de T002/T004 (Foundational); usa dados de US1 pra ser útil, mas não compartilha arquivos de implementação novos com ela
- **US3 (P3)**: Depende de US1 existir (T009/T010) — cobre o comportamento que ela já implementa

### Within Each User Story

- Testes MUST ser escritos e falhar antes da implementação (US1)
- Mapeamento (T008) antes da orquestração (T009) antes do tratamento de erro (T010) antes do CLI (T011)
- Real-Data Validation (T013) é a última etapa de US1, depois de toda a implementação

### Parallel Opportunities

- T005, T006, T007 (testes de US1) podem rodar em paralelo entre si
- T012 (pacote `scripts/`) é paralelo ao resto de US1
- T014 e T015 (testes de US2) podem rodar em paralelo entre si
- T019 e T020 (testes de US3) podem rodar em paralelo entre si
- T021 (Polish) é paralelo a T022

---

## Parallel Example: User Story 1

```bash
# Testes em paralelo:
Task: "Teste unitário de mapeamento em tests/unit/test_importar_historico.py"
Task: "Teste unitário de idempotência em tests/unit/test_importar_historico.py"
Task: "Teste de integração via GET /notas em tests/integration/test_api.py"
```

## Parallel Example: User Story 3

```bash
Task: "Teste de reexecução idempotente em tests/unit/test_importar_historico.py"
Task: "Teste de registro malformado pulado em tests/unit/test_importar_historico.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Phase 2: Foundational (T001–T004)
2. Completar Phase 3: User Story 1 (T005–T013, incluindo a validação com dado real)
3. **PARAR e VALIDAR**: rodar a importação real e conferir a listagem de notas
4. Já resolve o objetivo central — histórico preservado na base única

### Incremental Delivery

1. Foundational → coluna e repositório prontos
2. US1 → Testar independentemente (incluindo dado real) → histórico importado (MVP)
3. US2 → Testar independentemente → titular visível e filtrável
4. US3 → Testar independentemente → reexecução e dado heterogêneo comprovadamente seguros
5. Polish → revisão de dado sensível na saída, suíte completa

### Ordem sugerida de execução

**Foundational → US1 (com validação de dado real) → US2 → US3 → Polish**.
US3 depende logicamente de US1 já existir (mesmo sem compartilhar
arquivos de implementação novos), então não faz sentido paralelizar as
duas.

---

## Notes

- [P] tasks = arquivos diferentes, sem dependências
- [Story] label mapeia a tarefa à user story correspondente para rastreabilidade
- Verificar que os testes falham antes de implementar (TDD)
- Fazer commit após cada tarefa ou grupo lógico
- Parar em cada checkpoint para validar a story de forma independente
- **Nenhuma tarefa desta feature deve imprimir/logar chave de acesso, CNPJ, emitente ou valor monetário real** (Princípio IV) — inclusive ao inspecionar o arquivo de histórico manualmente durante o desenvolvimento
- Fixtures de teste usam sempre dados sintéticos (nunca o arquivo real do usuário), mesmo padrão já usado em `tests/helpers.py`
