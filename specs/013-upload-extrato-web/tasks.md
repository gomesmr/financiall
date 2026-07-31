---

description: "Task list for feature 013: upload de extrato/fatura bancária pela web"
---

# Tasks: Upload de extrato/fatura bancária pela web

**Input**: Design documents from `/specs/013-upload-extrato-web/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Incluídos — mesmo padrão já seguido pelas features 001–012
deste projeto (constituição, Princípio V: parsing/detecção de dado
externo exige teste automatizado + validação com amostra real).

**Organization**: Tarefas agrupadas por user story (spec.md), na mesma
ordem de prioridade declarada lá (US1 é P1; US2 é P2).

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Projeto único (`src/`, `tests/` na raiz) — mesma estrutura das features
001–012.

---

## Phase 1: Setup

Sem tarefas — nenhuma dependência nova (research.md): reaproveita
`xlrd`/`openpyxl`/`pdfplumber` já presentes em `pyproject.toml` desde as
features 010/011/012.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: a função de detecção de formato é a base que tanto o
caminho feliz (US1) quanto a recusa de arquivo não reconhecido (US2)
precisam antes de existir a rota.

- [x] T001 Implementar
      `src/services/importar_extrato_upload.py::detectar_e_parsear(caminho, nome_original) -> list[dict]`
      — inspeciona extensão (`.xls`/`.xlsx`/`.pdf`) e, quando ambígua,
      assinatura de conteúdo (research.md #1: coluna "saldos" para conta
      corrente Itaú vs. cabeçalho de 4 colunas para fatura Itaú legado;
      texto "Fatura Paga"/coluna "Titularidade" vs. colunas "Detalhes"/
      "Tipo Lançamento" para `.xlsx`); despacha para o `parsear()` já
      existente do formato correspondente; levanta
      `FormatoNaoReconhecidoError` quando nenhuma assinatura bate
      (research.md #2/#3)
- [x] T002 [P] Testes unitários em
      `tests/unit/test_importar_extrato_upload.py`: cada uma das 4
      assinaturas (excertos sintéticos de cabeçalho, não os arquivos
      reais) é detectada corretamente e despachada pro `parsear()` certo;
      extensão não suportada (ex. `.docx`) levanta
      `FormatoNaoReconhecidoError`; `.xlsx`/`.xls` sem nenhuma coluna
      reconhecível levanta o mesmo erro (não adivinha)

**Checkpoint**: detecção de formato pronta e testada — US1 e US2 podem
prosseguir sem bloqueio mútuo.

---

## Phase 3: User Story 1 - Importar um extrato/fatura novo sem precisar de ajuda técnica (Priority: P1) 🎯 MVP

**Goal**: o usuário sobe qualquer um dos 4 formatos já suportados pela
tela `/importar` e vê o resumo da importação na hora, sem acesso ao
servidor.

**Independent Test**: enviar, via `POST /extratos/upload`, um arquivo de
cada um dos 4 formatos e conferir que a resposta reporta o formato certo
e um resumo de importação bem-sucedida.

### Tests for User Story 1

- [x] T003 [P] [US1] Testes de contrato em `tests/contract/test_api_contract.py`:
      `POST /extratos/upload` com um excerto sintético de cada um dos 4
      formatos retorna `200` com `formato_detectado` correto e resumo
      (`importadas`, `ja_existentes`, etc.); enviar o mesmo arquivo duas
      vezes seguidas resulta na segunda vez com `importadas=0` e
      `ja_existentes` igual ao total da primeira (idempotência, FR-005)

### Implementation for User Story 1

- [x] T004 [US1] Implementar rota `POST /extratos/upload` em
      `src/api/routes_importar.py` (mesmo blueprint `importar`): lê o
      arquivo enviado, chama `detectar_e_parsear()` (depende de T001),
      depois `processar_transacoes()`, devolve o resumo em JSON
      (contrato em `contracts/api.md`)
- [x] T005 [US1] Adicionar card "Extrato ou fatura bancária" em
      `src/api/templates/upload.html`: formulário de upload de arquivo
      único, chama `POST /extratos/upload` via fetch, mostra o resumo (ou
      erro) inline — mesmo padrão visual dos cards já existentes na
      página (depende de T004)

### Real-Data Validation for User Story 1 (MANDATORY — Constitution Principle V)

- [x] T006 [US1] Validar contra os 4 arquivos reais antes de promover
      (dev → main): `assets/novos-extratos/fatura-paga-final
      {1035,2486}-junho2026.xlsx`, `assets/novos-extratos/Extrato Conta
      Corrente-220720261133.xls`, `assets/finalcial/Financeiro/extrato/cristine/Extrato
      conta corrente - 012026.xlsx`, `assets/novos-extratos/mercado-pago-2026-06.pdf`
  - [x] Dimensão 1 (detecção correta): validado contra os 5 arquivos reais
        (incluindo os 2 cartões Itaú) rodando o servidor local — todos os
        4 formatos detectados corretamente
        (`itau_fatura_cartao`/`itau_extrato_cc`/`bb_extrato_cc`/`mercado_pago_fatura`),
        sem nenhum falso positivo entre os pares ambíguos
  - [x] Dimensão 2 (paridade com o caminho CLI): reenviar a fatura
        Mercado Pago (já importada via CLI na feature 012) pelo upload
        web retornou exatamente `25 já existentes / 0 importadas` — o
        mesmo fingerprint bate perfeitamente entre os dois caminhos de
        entrada (CLI e web). Reenviar a fatura Itaú 1035 pela web duas
        vezes seguidas confirmou idempotência também dentro do próprio
        caminho web (`12 importadas` na primeira, `0 importadas / 12 já
        existentes` na segunda)

### Visual Verification for User Story 1 (Constitution Principle VIII)

- [x] T007 [US1] Nenhum asset de terceiro vendorizado — N/A para
      checagem de integridade de formato. Capturar screenshot via
      navegador headless de `/importar` com o card novo (estado inicial
      e após uma importação bem-sucedida) e confirmar ausência de erro de
      console, antes de promover para produção

**Checkpoint**: US1 completa e testável de forma independente (MVP).

---

## Phase 4: User Story 2 - Saber o que fazer quando o arquivo não é reconhecido (Priority: P2)

**Goal**: um arquivo que não corresponde a nenhum formato suportado, ou
está corrompido, é recusado com mensagem clara — nunca importado com o
parser errado nem trava a página.

**Independent Test**: enviar um arquivo de extensão não suportada e um
`.xlsx`/`.pdf` sem assinatura reconhecível, conferindo recusa clara em
ambos, sem gravar transação.

### Tests for User Story 2

- [x] T008 [P] [US2] Testes de contrato em `tests/contract/test_api_contract.py`:
      extensão não suportada (`.jpg`, `.docx`) → `415`; `.xlsx` sem
      nenhuma coluna reconhecível → `415`; arquivo corrompido com
      extensão válida (ex. `.pdf` que não é PDF de verdade) → `422`; sem
      arquivo enviado → `400` (mesmo padrão de `/notas/upload`); em todos
      os casos, `SELECT COUNT(*) FROM transacao` não muda

### Implementation for User Story 2

- [x] T009 [US2] Confirmar em `routes_importar.py` (depende de T004) que
      `FormatoNaoReconhecidoError` mapeia para `415` e que exceções dos
      parsers individuais (`ArquivoExtratoError`, `FaturaInvalidaError`)
      mapeiam para `422`, ambas com mensagem em português e sem gravar
      nada parcial (contrato em `contracts/api.md`)

### Real-Data Validation for User Story 2 (MANDATORY — Constitution Principle V)

- [x] T010 [US2] N/A — esta história cobre rejeição de formato
      desconhecido/corrompido; não há "amostra real" de arquivo inválido
      a validar além dos casos sintéticos já cobertos em T008 (a
      validação real relevante, de detecção correta dos formatos
      válidos, já está em T006)

### Visual Verification for User Story 2 (Constitution Principle VIII)

- [x] T011 [US2] Capturar screenshot via navegador headless de
      `/importar` no estado de erro (após enviar um arquivo não
      reconhecido pelo card novo) e confirmar ausência de erro de
      console, antes de promover para produção

**Checkpoint**: US1 + US2 completas — upload cobre tanto o caminho feliz
quanto a rejeição segura.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T012 Atualizar `README.md` (seção "Importando um extrato bancário
      novo") mencionando o upload pela web como alternativa aos scripts
      CLI, já que resolve o problema original (usuário não precisa de
      SSH)
- [x] T013 Rodar `quickstart.md` na íntegra como validação final antes do
      PR para `dev`
- [ ] T014 Atualizar a memória da sessão
      (`feature_013_upload_extrato_web_status.md`) documentando o
      resultado e achados de dado real (T006)

---

## Dependencies & Execution Order

- **Setup (Phase 1)**: nenhuma tarefa.
- **Foundational (Phase 2)**: bloqueia US1 e US2 (T004 depende de T001).
- **US1 (Phase 3)**: depende só do Foundational. MVP.
- **US2 (Phase 4)**: depende de T004 (mesma rota) — tecnicamente pode ser
  implementada em paralelo com US1 já que o mapeamento de erro é parte da
  mesma rota, mas os testes de rejeição (T008) só fazem sentido depois
  que a rota existe.
- **Polish (Phase 5)**: depende de US1 + US2 completas.

### Parallel Opportunities

- T002 pode rodar em paralelo com o restante do Foundational (arquivo de
  teste próprio).
- T003 e T008 podem ser escritos em paralelo (arquivos/casos diferentes
  no mesmo arquivo de teste), mas ambos dependem de T004 existir para
  rodar de fato.

---

## Implementation Strategy

### MVP First (User Story 1)

1. Foundational (detecção de formato).
2. US1 completa, validada com os 4 arquivos reais (T006).
3. **PARAR e VALIDAR**: usuário consegue subir um extrato pela web e ver
   o resumo, sem SSH.

### Incremental Delivery

1. Foundational → detecção pronta.
2. US1 → caminho feliz de upload funcionando (MVP — resolve o problema
   central: self-service sem SSH).
3. US2 → rejeição seguindo com mensagem clara quando o arquivo não é
   reconhecido, fechando a US1 com uma rede de segurança visível ao
   usuário.
