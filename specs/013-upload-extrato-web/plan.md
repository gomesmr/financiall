# Implementation Plan: Upload de extrato/fatura bancária pela web

**Branch**: `013-upload-extrato-web` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/013-upload-extrato-web/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Adicionar uma rota HTTP síncrona (`POST /extratos/upload`) e um card novo
na página `/importar` já existente, permitindo que o usuário importe
qualquer um dos 4 formatos de extrato/fatura já suportados (features
010/011/012) sem precisar de acesso ao servidor. O trabalho real é uma
função de detecção de formato (research.md #1/#2) que inspeciona a
extensão e, quando ambígua (`.xls` cobre 2 formatos, `.xlsx` cobre outros
2), uma assinatura de conteúdo (coluna/texto distintivo encontrado
inspecionando os arquivos reais já usados nas validações anteriores) para
decidir qual dos 4 `parsear()` já existentes chamar — nenhuma lógica de
parsing nova, nenhuma mudança nos parsers/scripts CLI existentes (FR-007).
Formato não reconhecido com confiança é recusado (415), nunca adivinhado
(research.md #3, Princípio III/VII). Sem fila assíncrona — diferente do
upload de nota fiscal, nenhum dos 4 parsers usa OCR, então o processamento
é rápido o bastante para responder na mesma requisição (research.md #4).

## Technical Context

**Language/Version**: Python 3.11+ (mesmo runtime do projeto)

**Primary Dependencies**: Flask (já usado) — nenhuma dependência nova;
reaproveita `xlrd`/`openpyxl`/`pdfplumber` já adicionados pelas features
anteriores, só para inspecionar cabeçalho/assinatura antes de despachar

**Storage**: SQLite (`src/storage/db.py`) — nenhuma migração, reaproveita
`processar_transacoes()` sem alteração

**Testing**: pytest (unit para detecção de formato + contract para a rota
HTTP, mesmo padrão das features anteriores)

**Target Platform**: aplicação web self-hosted (Raspberry Pi, mesmo
destino de deploy das features anteriores)

**Project Type**: single project (web service) — mesma estrutura já usada

**Performance Goals**: resposta síncrona em menos de ~2s para o maior
arquivo real já visto (fatura Mercado Pago de 6 páginas, medida na
validação da feature 012: bem menos de 1s)

**Constraints**: nunca gravar dado parcial quando o formato não é
reconhecido ou o arquivo está corrompido (Princípio III); nunca adivinhar
formato ambíguo (Princípio VII); verificação visual real do card novo
antes de promover (Princípio VIII)

**Scale/Scope**: uso pessoal (poucos uploads por mês, um por titular/fonte
de extrato) — sem meta de performance dedicada além do acima

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Simplicidade**: PASSA. Nenhum parser novo, nenhuma fila, nenhuma
  página nova — só uma função de detecção fina + 1 rota + 1 card na
  página já existente. A detecção despacha para os 4 `parsear()` já
  existentes sem duplicar lógica.
- **II. Idempotência**: PASSA. Mesmo `processar_transacoes()` (mesmo
  fingerprint) já usado pelos scripts CLI — nenhuma lógica de dedup nova,
  nenhum risco novo introduzido pelo caminho web.
- **III. Tratamento de erro em entrada externa**: PASSA. Arquivo com
  extensão não suportada, conteúdo ambíguo, ou corrompido é recusado com
  mensagem clara (415/422) antes de qualquer persistência — nunca deixa
  exceção não tratada propagar pra tela do usuário.
- **IV. Dados sensíveis**: PASSA. Resposta HTTP e log de erro só trazem
  contagens agregadas e o nome do formato detectado — nunca
  descrição/valor/conta de transação individual.
- **V. Testável por construção**: aplica-se — a função de detecção
  inspeciona formato vindo de fora do controle do código. PASSA desde que
  (a) teste automatizado cubra as 4 assinaturas + o caso ambíguo/não
  reconhecido e (b) a rota rode contra os 4 arquivos reais já usados nas
  validações anteriores antes de promover — segunda barreira obrigatória
  (quickstart.md), não substituível pelo teste sintético.
- **VI. Português**: PASSA. Mensagens de erro da rota e texto do card em
  português, mesmo padrão.
- **VII. Fontes frágeis degradam sem quebrar**: PASSA — com uma nuance
  importante: aqui "degradar sem quebrar" significa **recusar** o arquivo
  ambíguo/não reconhecido (não gravar com o parser errado), não tentar um
  palpite. A rota nunca derruba a página nem propaga stack trace ao
  usuário.
- **VIII. Integridade visual**: aplica-se — card novo em `/importar`.
  Verificação visual real (captura headless + checagem de erro de
  console) obrigatória antes de promover. Nenhum asset de terceiro novo é
  vendorizado.

Nenhuma violação a justificar em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/013-upload-extrato-web/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── api.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── services/
│   └── importar_extrato_upload.py   # NOVO — detectar_e_parsear() (research.md #1/#2)
├── api/
│   ├── routes_importar.py           # + rota POST /extratos/upload (mesmo blueprint "importar")
│   └── templates/
│       └── upload.html              # + card "Extrato ou fatura bancária"

tests/
├── contract/
│   └── test_api_contract.py         # + testes da rota /extratos/upload (sucesso, 415, 422)
└── unit/
    └── test_importar_extrato_upload.py   # NOVO — detecção contra as 4 assinaturas + caso ambíguo
```

**Structure Decision**: projeto único (mesma estrutura já usada pelas
features 001–012) — só adiciona um serviço novo (`src/services/`), uma
rota no blueprint `importar` já existente e um card na página já
existente. Nenhuma estrutura nova introduzida; os 4 parsers e seus
scripts CLI permanecem intocados (FR-007).

## Complexity Tracking

*Sem violações do Constitution Check — seção não aplicável.*
