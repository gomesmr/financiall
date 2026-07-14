---

description: "Task list for feature implementation"
---

# Tasks: Excluir Nota Fiscal

**Input**: Design documents from `/specs/002-excluir-nota-fiscal/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/api.md](./contracts/api.md), [quickstart.md](./quickstart.md)

**Tests**: Incluídos. `plan.md` (seção Testing) e a "Verificação final" de
`quickstart.md` exigem a suíte `pytest tests/unit tests/integration
tests/contract` passando antes de considerar a feature pronta.

**Real-Data Validation (Princípio V da constituição)**: não se aplica a
esta feature. O gate cobre rotinas que processam dado vindo de fora do
controle do código (OCR, scraping, parsing de formato externo) — excluir
uma nota opera sobre dado já validado na importação (feature 001), não
sobre entrada externa nova. Nenhuma fase abaixo tem seção de validação com
amostra real.

**Organization**: Tarefas agrupadas por user story (spec.md) para permitir
implementação e teste independentes de cada uma.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: A qual user story a tarefa pertence (US1, US2, US3)
- Caminhos de arquivo exatos incluídos em cada descrição

## Path Conventions

Aplicação web única (single project): `src/`, `tests/` na raiz do
repositório, mesma estrutura da feature 001 — nenhum diretório novo no
nível raiz (ver `plan.md` → Project Structure).

---

## Phase 1: Setup (Shared Infrastructure)

Não há inicialização de projeto nova nesta feature — reaproveita 100% da
estrutura, dependências (`Flask`, `pytest`) e configuração já existentes
da feature 001. Nenhuma tarefa de Setup.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Função de repositório e serviço que TODA user story depende (nenhuma story pode excluir uma nota sem elas)

**⚠️ CRITICAL**: Nenhuma user story pode começar antes desta fase estar completa

- [X] T001 Implementar `excluir_nota(nota_id, db_path) -> list[str] | None` em src/storage/db.py — transação única (`BEGIN`/`COMMIT`) que: verifica se a nota existe (senão retorna `None`), coleta `caminho_arquivo` de todos os `envio_ocr` com aquele `nota_fiscal_id`, deleta `envio_ocr`, deleta `item_nota`, deleta `nota_fiscal`, e retorna a lista de caminhos coletada — conforme data-model.md → Operação `excluir_nota`
- [X] T002 Criar src/services/exclusao.py com `excluir_nota_fiscal(nota_id, db_path) -> bool` — chama `storage_db.excluir_nota`, retorna `False` se `None` (nota não existia), senão tenta `os.remove` em cada caminho retornado ignorando `FileNotFoundError` (best-effort, research.md #2), e retorna `True` (depende de T001). Sem parâmetro `upload_dir` — `caminho_arquivo` já grava o caminho completo (`fila_processamento.salvar_arquivo_recebido`), então seria um parâmetro morto

**Checkpoint**: Fundação pronta — implementação das user stories pode começar

---

## Phase 3: User Story 1 - Excluir uma nota incorreta (Priority: P1) 🎯 MVP

**Goal**: Usuário exclui uma nota fiscal (e seus itens, envio de origem e arquivo físico) a partir da listagem ou do detalhe, com confirmação explícita antes da ação.

**Independent Test**: importar uma nota, acioná-la para exclusão na UI, confirmar, e verificar que ela some da listagem (`GET /notas`) e do resumo mensal.

### Tests for User Story 1 ⚠️

> **NOTE: Escrever estes testes PRIMEIRO, garantir que falham antes da implementação**

- [X] T003 [P] [US1] Teste unitário: `excluir_nota_fiscal` remove nota + itens + envio(s) associados (incluindo o caso de múltiplos envios apontando para a mesma nota) e tenta remover os arquivos; nota com status `completa` ou `pendente_revisao` são tratadas igual (FR-008); nota inexistente retorna `False` sem lançar exceção — tests/unit/test_exclusao.py
- [X] T004 [P] [US1] Teste de integração: `DELETE /notas/<id>` remove a nota da listagem (`GET /notas`) e do resumo do mês (`GET /notas/resumo/mes-atual`) imediatamente após a chamada — tests/integration/test_api.py

### Implementation for User Story 1

- [X] T005 [US1] Implementar a rota `DELETE /notas/<int:nota_id>` em src/api/routes_importar.py — chama `services.exclusao.excluir_nota_fiscal`, responde `200` com `{"mensagem": "Nota excluída com sucesso."}` em sucesso e `404` com `{"erro": "Nota não encontrada."}` quando a nota não existe, conforme contracts/api.md (depende de T002)
- [X] T006 [P] [US1] Adicionar botão "Excluir" em cada linha de src/api/templates/notas.html, com `confirm()` em português antes do `fetch DELETE /notas/<id>` (mesmo padrão de `fetch` já usado em upload.html) e remoção da linha da tabela (ou recarregamento da lista) em caso de sucesso
- [X] T007 [P] [US1] Adicionar botão "Excluir" em src/api/templates/nota_detalhe.html, com `confirm()` em português antes do `fetch DELETE /notas/<id>` e redirecionamento para `/ver/notas` com uma confirmação visível de sucesso

**Checkpoint**: User Story 1 funcional e testável de forma independente — usuário já consegue excluir a nota malformada que motivou a feature

---

## Phase 4: User Story 2 - Reimportar depois de excluir (Priority: P2)

**Goal**: Depois de excluir uma nota, o usuário consegue reimportar o mesmo documento (mesma chave de acesso ou mesmo hash de conteúdo) sem ser bloqueado por duplicidade residual.

**Independent Test**: excluir uma nota com chave conhecida, reimportar a mesma nota pela mesma via, e verificar que ela é aceita como nova (não `"status": "ja_registrada"`).

Nenhuma implementação nova nesta fase — a garantia vem estruturalmente
dos índices únicos parciais (`idx_nota_fiscal_chave_acesso` /
`idx_nota_fiscal_hash_conteudo`, ver data-model.md), que só cobrem linhas
existentes: uma vez que T001 remove a linha, a chave/hash já está livre
para `services/importador.py` (feature 001) aceitar de novo, sem qualquer
alteração naquele código. Esta fase só valida esse comportamento.

### Tests for User Story 2 ⚠️

- [X] T008 [P] [US2] Teste de integração: excluir uma nota importada por chave de acesso (`DELETE /notas/<id>`) e reimportar a mesma chave via `POST /notas` — confirmar `status` `completa`/`pendente_revisao` (nunca `ja_registrada`) — tests/integration/test_api.py (depende de T005)
- [X] T009 [P] [US2] Teste de integração: excluir uma nota sem chave (identificada por `hash_conteudo`) e reenviar o mesmo arquivo via `POST /notas/upload` — confirmar que uma nova nota é criada, não bloqueada — tests/integration/test_api.py (depende de T005)

**Checkpoint**: Excluir e reimportar formam um ciclo completo — o usuário tem uma saída real para uma nota malformada

---

## Phase 5: User Story 3 - Feedback de erro ao excluir (Priority: P3)

**Goal**: Tentar excluir uma nota inexistente, ou acessar um envio cujo arquivo/nota já foi excluído, resulta em mensagem clara em português — nunca erro técnico ou navegação quebrada.

**Independent Test**: chamar `DELETE /notas/<id>` com um id inexistente e verificar a mensagem de erro; acessar `/ver/envios/<id>` (ou `GET /envios/<id>`) de um envio cuja nota foi excluída e verificar que retorna "não encontrado" em vez de quebrar.

O caso de nota inexistente no `DELETE /notas/<id>` já foi implementado em
T005 (US1). O caso de envio já foi coberto pelo tratamento existente de
`envio_ocr` inexistente em `routes_consulta.py` (feature 001) — como T001
exclui o próprio registro de envio junto com a nota, esse caminho de
código já existente passa a cobrir também esta situação, sem alteração.
Esta fase confirma os dois comportamentos com teste.

### Tests for User Story 3 ⚠️

- [X] T010 [P] [US3] Teste de contrato: `DELETE /notas/<id>` com id inexistente retorna `404` com `{"erro": "Nota não encontrada."}`, conforme contracts/api.md — tests/contract/test_api_contract.py (depende de T005)
- [X] T011 [P] [US3] Teste de integração: excluir uma nota originada de um envio (upload de foto/PDF), depois acessar `GET /envios/<envio_id>` e `/ver/envios/<envio_id>` desse envio — confirmar `404`/"Envio não encontrado." nos dois, sem exceção — tests/integration/test_api.py (depende de T005)

**Checkpoint**: Todas as user stories funcionam de forma independente — nenhum caminho de erro quebra a navegação

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Revisão final e validação ponta a ponta

- [X] T012 [P] Revisar as mensagens de confirmação/erro adicionadas em src/api/templates/notas.html e nota_detalhe.html quanto à consistência de tom/idioma com o restante da UI (Princípio VI)
- [X] T013 Validar manualmente os cenários de quickstart.md contra o servidor local (excluir nota via URL/chave, excluir nota via upload, cancelar confirmação, reimportar, acessar envio excluído) e confirmar os critérios SC-001 a SC-005
- [X] T014 Rodar a suíte completa `pytest tests/unit tests/integration tests/contract` e confirmar 100% de sucesso antes de promover a feature (dev → main)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Vazia — nada a fazer
- **Foundational (Phase 2)**: Sem dependências externas — BLOQUEIA todas as user stories
- **US1 (Phase 3)**: Depende apenas da Foundational
- **US2 (Phase 4)**: Depende de US1 (T005, a rota precisa existir para excluir antes de reimportar) — sem implementação própria, só teste
- **US3 (Phase 5)**: Depende de US1 (T005) — sem implementação própria, só teste
- **Polish (Phase 6)**: Depende de US1, US2 e US3 completas

### User Story Dependencies

- **US1 (P1)**: Sem dependência de outra story — MVP: excluir a nota malformada
- **US2 (P2)**: Depende de US1 existir (precisa conseguir excluir antes de validar a reimportação), mas não compartilha código de implementação novo
- **US3 (P3)**: Depende de US1 existir (mesmo motivo) — cobre o caminho de erro do mesmo endpoint

### Within Each User Story

- Testes MUST ser escritos e falhar antes da implementação (US1)
- Repositório (T001) antes do serviço (T002) antes da rota (T005) antes da UI (T006/T007)

### Parallel Opportunities

- T006 e T007 (templates diferentes) podem rodar em paralelo entre si, após T005
- T003 e T004 (US1) podem rodar em paralelo entre si
- T008 e T009 (US2) podem rodar em paralelo entre si
- T010 e T011 (US3) podem rodar em paralelo entre si
- US2 e US3 podem ser desenvolvidas em paralelo uma da outra (ambas só dependem de US1, não uma da outra)

---

## Parallel Example: User Story 1

```bash
# Testes em paralelo:
Task: "Teste unitário de excluir_nota_fiscal em tests/unit/test_exclusao.py"
Task: "Teste de integração de DELETE /notas/<id> em tests/integration/test_api.py"

# UI em paralelo, após a rota (T005) existir:
Task: "Botão excluir em src/api/templates/notas.html"
Task: "Botão excluir em src/api/templates/nota_detalhe.html"
```

## Parallel Example: User Story 2 + User Story 3 (após US1)

```bash
# US2 — validação da reimportação:
Task: "Reimportar por chave após exclusão em tests/integration/test_api.py"
Task: "Reimportar por upload após exclusão em tests/integration/test_api.py"

# US3 — validação dos caminhos de erro, em paralelo:
Task: "DELETE /notas/<id> inexistente retorna 404 em tests/contract/test_api_contract.py"
Task: "Envio de nota excluída retorna 404 em tests/integration/test_api.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Phase 2: Foundational (T001, T002)
2. Completar Phase 3: User Story 1 (T003–T007)
3. **PARAR e VALIDAR**: excluir uma nota real pela UI e confirmar que ela some da listagem e do resumo
4. Já resolve o caso concreto que motivou a feature (nota malformada travada na base)

### Incremental Delivery

1. Foundational → função de exclusão pronta no repositório/serviço
2. US1 → Testar independentemente → usuário consegue excluir pela UI (MVP)
3. US2 → Testar independentemente → ciclo excluir→reimportar garantido
4. US3 → Testar independentemente → nenhum caminho de erro quebra a navegação
5. Polish → revisão de idioma, validação manual de quickstart.md, suíte completa

### Ordem sugerida de execução

**Foundational → US1 → (US2 e US3 em paralelo) → Polish**. US2 e US3 não
compartilham arquivos de implementação nova entre si (ambas só adicionam
testes sobre o comportamento que US1 já implementou).

---

## Notes

- [P] tasks = arquivos diferentes, sem dependências
- [Story] label mapeia a tarefa à user story correspondente para rastreabilidade
- Verificar que os testes falham antes de implementar (TDD)
- Fazer commit após cada tarefa ou grupo lógico
- Parar em cada checkpoint para validar a story de forma independente
- Nenhum dado sensível (chave de acesso, CNPJ, CPF, valores) em log de texto claro em nenhuma tarefa (Princípio IV)
- A remoção de arquivo em disco é sempre best-effort (research.md #2) — nunca bloqueia a exclusão dos dados no banco
