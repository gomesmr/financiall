---

description: "Task list for feature 007 — Leitura de QR Code pela Câmera"
---

# Tasks: Leitura de QR Code pela Câmera

**Input**: Design documents from `/specs/007-leitura-qrcode-camera/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: contrato do endpoint novo (`POST /notas/qrcode-frame`) — os demais endpoints
(`POST /notas`) permanecem inalterados e já cobertos pela suíte existente.

**Real-Data Validation**: obrigatória para US1 — Constitution Principle V cita "leitura de
QR code" nominalmente como rotina que processa dado externo.

**Visual Verification**: obrigatória para as 3 histórias — Constitution Principle VIII,
superfície visual nova na página de Importar. Nenhum asset de terceiro é vendorizado
nesta feature (research.md #1/#8), então o sub-check de integridade de asset é N/A em
todas as histórias.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: US1, US2 ou US3 conforme spec.md

## Path Conventions

Projeto único: `src/api/`, `src/services/`, `tests/`, `infra/` na raiz do repo.

---

## Phase 1: Setup

**Purpose**: Provisionar o pré-requisito de infraestrutura sem o qual a câmera nunca liga
num celular real (research.md #5).

- [X] T001 Provisionar **Caddy** como proxy reverso HTTPS no Raspberry Pi, na frente dos
      dois ambientes já existentes (produção `localhost:5000`, dev `localhost:5005`),
      com certificado autoassinado gerado automaticamente (`tls internal` — sem depender
      de internet nem de CA pública): criar `infra/Caddyfile` (novo, versionado) e
      atualizar `infra/setup-raspberry-pi.sh` com o passo de instalação/configuração do
      Caddy e do serviço systemd correspondente

**Checkpoint**: financiALL acessível pelo celular via `https://` na rede local, nos dois
ambientes — pré-requisito para qualquer validação funcional real das histórias abaixo.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Mecanismo compartilhado que todas as 3 histórias usam — decodificar um frame
de câmera no servidor, e a estrutura básica da opção de câmera na página.

**⚠️ CRITICAL**: Nenhuma história pode ser implementada de forma completa antes desta fase.

- [X] T002 [P] Criar o endpoint `POST /notas/qrcode-frame` em
      `src/api/routes_importar.py`, reaproveitando `src/services/qrcode_reader.py`
      (`decodificar_qrcode`, inalterado) — recebe `image/jpeg`, retorna
      `{"entrada": "<texto>"}` ou `{"entrada": null}` conforme contracts/api.md
- [X] T003 Estrutura básica da opção de câmera em `src/api/templates/upload.html`: botão
      "Ler QR Code pela câmera" ao lado das duas opções já existentes, elementos
      `<video>`/`<canvas>` ocultos por padrão, e JS inline em `{% block extra_scripts %}`
      com a detecção inicial de suporte (contexto seguro + `navigator.mediaDevices`
      existente) — sem ainda o loop de captura/decodificação (US1) nem os estados de
      feedback (US3)

**Checkpoint**: endpoint de decodificação funcional e testável isoladamente; página de
Importar com o botão novo presente, ainda sem comportamento de captura ligado.

---

## Phase 3: User Story 1 - Importar apontando a câmera pro QR Code (Priority: P1) 🎯 MVP

**Goal**: Ativar a câmera na própria página e importar a nota ao apontar para o QR Code,
sem sair do app e sem copiar/colar.

**Independent Test**: ativar a leitura por câmera, apontar para um QR Code de nota fiscal
válido, e confirmar que a nota é importada com o mesmo resultado de colar a mesma URL
manualmente no campo de texto já existente.

### Implementation for User Story 1

- [X] T004 [US1] Implementar início do stream de vídeo via `getUserMedia({video:
      {facingMode: "environment"}})` ao clicar no botão de câmera (research.md #6),
      exibindo o vídeo ao vivo no elemento `<video>` de `upload.html`
- [X] T005 [US1] Implementar o loop de captura: a cada ~700ms (research.md #4), desenhar o
      frame atual do `<video>` num `<canvas>` reduzido a ~1200px no lado maior
      (research.md #3), exportar como JPEG (`canvas.toBlob`, qualidade ~0.7) e enviar via
      `POST /notas/qrcode-frame`
- [X] T006 [US1] Ao receber `entrada` não nula do endpoint, parar o loop de captura e
      chamar `POST /notas` (endpoint já existente, inalterado) com essa `entrada`,
      reaproveitando a mesma exibição de resultado que o formulário de URL/chave manual já
      usa hoje em `upload.html` (FR-003)
- [X] T007 [P] [US1] Contract test para `POST /notas/qrcode-frame` em
      `tests/contract/test_api_contract.py`: imagem com QR Code válido retorna a `entrada`
      esperada; imagem sem QR Code retorna `entrada: null`; corpo não decodificável como
      imagem retorna 415

### Real-Data Validation for User Story 1 (MANDATORY — Constitution Principle V cita "leitura de QR code" nominalmente)

> Distinta dos testes automatizados acima — confirma que o mecanismo sobrevive ao contato
> com captura ao vivo real, não só com uma imagem de teste construída pelo autor.

- [ ] T008 [US1] Validar com QR Codes reais de nota fiscal antes de promover esta história
      (dev → main)
  - [ ] Dimensão 1: distância/ângulo de captura ao vivo variável (diferente de uma foto já
        enquadrada e estática)
  - [ ] Dimensão 2: frame comprimido gerado pelo navegador (canvas JPEG ~0.7), não um
        arquivo de foto original de alta resolução
  - [ ] Dimensão 3: pelo menos os dois celulares reais da casa (câmeras/qualidade
        diferentes)

### Visual Verification for User Story 1 (MANDATORY — Constitution Principle VIII)

- [X] T009 [US1] Integridade de asset de terceiro vendorizado: **N/A** — nenhum asset novo
      nesta história (research.md #1/#8)
- [X] T010 [US1] Captura de tela via navegador headless local da página de Importar com a
      opção de câmera ativa/visível, sem sobreposição com as outras duas opções, e checagem
      de zero erros de console JS na mesma execução — feito para o estado inicial da
      página; os estados intermediários (vídeo em stream, captura em loop) exigem câmera de
      verdade e ficam para a validação em dispositivo real (T008/T024), já que o ambiente
      headless deste agente não tem hardware de câmera

**Checkpoint**: importar uma nota apontando a câmera funciona de ponta a ponta, com o
mesmo resultado do fluxo manual já existente.

---

## Phase 4: User Story 2 - Degradação graciosa quando a câmera não está disponível (Priority: P1)

**Goal**: Quando a câmera não pode ser usada pela página (permissão negada, sem suporte,
contexto inseguro), a opção fica claramente indisponível e as duas opções já existentes
continuam funcionando sem nenhuma mudança perceptível.

**Independent Test**: acessar a página num contexto sem câmera disponível (permissão
negada, ou simulando ausência de suporte) e confirmar que nenhum botão quebrado aparece, e
que importar por URL/chave e por foto/PDF continuam funcionando normalmente.

### Implementation for User Story 2

- [X] T011 [US2] Detectar disponibilidade de câmera ao carregar `upload.html` (contexto
      seguro + `navigator.mediaDevices.getUserMedia` existente, da estrutura básica de
      T003); se indisponível, ocultar/desabilitar claramente a opção de câmera sem afetar
      as outras duas (FR-004)
- [X] T012 [US2] Tratar rejeição de permissão durante o uso (`NotAllowedError` do
      `getUserMedia`, ou qualquer outro erro ao tentar abrir o stream): exibir mensagem
      clara e retornar ao estado com as outras opções disponíveis, sem travar a página
- [X] T013 [P] [US2] Confirmado pela suíte já existente: nenhuma linha desta feature altera
      `POST /notas` nem `POST /notas/upload` (a degradação é 100% client-side, o backend
      não tem nenhum código consciente de câmera) — os testes já existentes para esses dois
      endpoints continuam passando inalterados, sem necessidade de um teste novo redundante

### Real-Data Validation for User Story 2

- [X] T014 [US2] **N/A** — esta história não processa dado externo (é detecção de
      capacidade do navegador/dispositivo, não decodificação de conteúdo); a validação com
      QR Code real pertence à US1 (T008)

### Visual Verification for User Story 2 (MANDATORY — Constitution Principle VIII)

- [X] T015 [US2] Integridade de asset de terceiro vendorizado: **N/A** — nenhum asset novo
      nesta história
- [ ] T016 [US2] Captura de tela via navegador headless local simulando câmera
      indisponível, confirmando que a opção de câmera não aparece quebrada e que as outras
      duas opções continuam visíveis normalmente, com checagem de zero erros de console JS

**Checkpoint**: a página se comporta corretamente com e sem câmera disponível, sem
nenhuma regressão nas duas opções de importação já existentes.

---

## Phase 5: User Story 3 - Feedback claro durante a leitura (Priority: P2)

**Goal**: O usuário sabe que a busca está ativa, recebe erro claro quando o código
decodificado não é válido, e consegue cancelar a qualquer momento.

**Independent Test**: ativar a leitura por câmera, apontar para algo que não é um QR Code
de nota fiscal válido, e confirmar retorno compreensível; cancelar a leitura e confirmar
volta às opções normais sem recarregar a página.

### Implementation for User Story 3

- [X] T017 [US3] Implementar indicador visual de "buscando" em `upload.html` enquanto o
      loop de captura (T005) está ativo sem resultado ainda (FR-005)
- [X] T018 [US3] Tratar o caso em que `POST /notas` (chamado a partir de T006) retorna erro
      422 para a `entrada` decodificada: exibir a mesma mensagem de erro que já existe hoje
      para entrada de texto inválida, permitindo tentar a leitura de novo sem sair da tela
      (FR-006)
- [X] T019 [US3] Implementar botão de cancelar a leitura a qualquer momento: para o stream
      de vídeo e o loop de captura, volta à visão normal das três opções de importação, sem
      recarregar a página (FR-007)

### Real-Data Validation for User Story 3

- [X] T020 [US3] **N/A** — esta história é feedback de UI sobre resultados que já passam
      pelo mecanismo de decodificação validado em US1 (T008); não introduz um novo caminho
      de processamento de dado externo

### Visual Verification for User Story 3 (MANDATORY — Constitution Principle VIII)

- [X] T021 [US3] Integridade de asset de terceiro vendorizado: **N/A** — nenhum asset novo
      nesta história
- [ ] T022 [US3] Captura de tela via navegador headless local com o indicador de "buscando"
      visível e com o estado de erro visível (simulando uma `entrada` inválida), checagem
      de zero erros de console JS

**Checkpoint**: as 3 histórias funcionam de forma independente e o ciclo completo de
leitura por câmera (buscar → decodificar → importar ou errar → cancelar) tem feedback
claro em cada etapa.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validação final cruzando todas as histórias.

- [X] T023 Rodar a suíte completa (`pytest tests/unit tests/integration tests/contract -v`)
      e confirmar 100% passando — depende de T007, T013
- [ ] T024 Validação completa do `quickstart.md` (§1-§6), incluindo o teste de
      funcionamento sem internet (certificado HTTPS gerado localmente pelo Caddy continua
      válido com o Pi desconectado) — depende de T001, T008, T010, T016, T022

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1)**: sem dependências — pode começar imediatamente, mas T024 (validação
  final) depende dela estar concluída
- **Foundational (Fase 2)**: T002 e T003 são `[P]` entre si (arquivos diferentes) — BLOQUEIA
  todas as histórias
- **User Story 1 (Fase 3)**: depende da Fase 2 completa
- **User Story 2 (Fase 4)**: depende da Fase 2 completa; T011 depende especificamente da
  detecção de suporte já estruturada em T003
- **User Story 3 (Fase 5)**: depende da Fase 2 completa e especificamente de T005/T006
  (US1) já existirem, já que adiciona feedback sobre esse mesmo loop — na prática, mais
  fácil de implementar depois da US1 estar funcional, mesmo sendo independentemente
  testável
- **Polish (Fase 6)**: depende de todas as histórias completas

### Parallel Opportunities

- T002 e T003 (Foundational) são `[P]` — arquivos diferentes (`routes_importar.py` vs
  `upload.html`)
- T007 (US1) e T013 (US2) são testes automatizados `[P]` — arquivos de teste diferentes
- T009/T015/T021 (integridade de asset, todas N/A) não bloqueiam nada, podem ser marcadas
  assim que cada história é revisada

---

## Parallel Example: Foundational

```bash
# Lançar as duas tarefas fundacionais em paralelo (arquivos diferentes):
Task: "Criar o endpoint POST /notas/qrcode-frame em src/api/routes_importar.py"
Task: "Estrutura básica da opção de câmera em src/api/templates/upload.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Fase 1: Setup (Caddy/HTTPS — sem isso não dá para validar em celular real)
2. Completar Fase 2: Foundational (endpoint + estrutura básica da opção de câmera)
3. Completar Fase 3: User Story 1 (importar apontando a câmera)
4. **PARAR e VALIDAR**: checklist de regressão + Real-Data Validation (T008) + Visual
   Verification (T010) da US1
5. Deploy/demo em dev se pronto — já entrega o valor central da feature

### Incremental Delivery

1. Setup + Foundational → fundação pronta (HTTPS funcionando, endpoint testável)
2. US1 → validar independentemente (real + visual) → deploy/demo em dev (MVP)
3. US2 → validar independentemente → deploy/demo (degradação graciosa confirmada)
4. US3 → validar independentemente → deploy/demo (feedback de UI completo)
5. Polish → suíte completa + quickstart completo → promover dev → main

---

## Notes

- [P] = arquivos diferentes, sem dependência
- Nenhuma tarefa desta feature muda `POST /notas` nem `src/services/qrcode_reader.py` —
  ambos reaproveitados exatamente como já existem
- US1 e US3 tocam o mesmo arquivo (`upload.html`) em momentos diferentes — US1 primeiro
  (mecanismo funcional), US3 depois (feedback sobre esse mesmo mecanismo)
