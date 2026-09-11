# Implementation Plan: Log de importações

**Branch**: `feat/mcl-log-importacoes` (spec dir `014-log-importacoes`) | **Date**: 2026-09-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/014-log-importacoes/spec.md`

## Summary

Registrar automaticamente um evento de histórico toda vez que
`processar_transacoes()` (o ponto central já usado por todos os
importadores: Itaú CC, Itaú cartão, BB, Mercado Pago, Open Finance Itaú
e upload web) concluir uma execução — data/hora, fonte, período coberto
e as contagens do resumo — e expor esse histórico numa página nova
(`/ver/log-importacoes`), ordenada da mais recente para a mais antiga.
Abordagem técnica: instrumentar só o ponto de convergência já existente
(research.md #1), sem tocar nos seis chamadores, gravando numa tabela
SQLite nova via o mesmo padrão repositório já usado por
`compromisso_futuro`.

## Technical Context

**Language/Version**: Python 3.11 (mesmo do resto do projeto)

**Primary Dependencies**: Flask (rota/página), sqlite3 (stdlib, já usado
em todo `src/storage/db.py`) — nenhuma dependência nova.

**Storage**: SQLite (`data/financiall.db`), tabela nova `log_importacao`.

**Testing**: pytest (`tests/unit`, `tests/integration`), mesmo padrão do
projeto.

**Target Platform**: Servidor Flask rodando no Raspberry Pi (prod porta
5000, dev porta 5005) — mesma infraestrutura já existente.

**Project Type**: Web application (single Flask app, server-rendered
com Jinja2/Argon) — Option 1 da estrutura abaixo.

**Performance Goals**: N/A — volume esperado de dezenas de eventos por
mês; sem exigência de performance além do já padrão do app (páginas
respondem em menos de 1s com SQLite local).

**Constraints**: Nenhum importador existente pode mudar de assinatura ou
comportamento visível (Assumptions da spec) — a instrumentação precisa
ser inteiramente interna a `processar_transacoes()`.

**Scale/Scope**: Uma tabela nova, ~2 funções de repositório
(`inserir_log_importacao`, `listar_logs_importacao`), uma função de
cálculo de período dentro do serviço já existente, um blueprint/rota
nova, um template novo.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Simplicidade**: instrumentação concentrada num único ponto
  (`processar_transacoes`), reaproveitando o padrão repositório já
  existente (`db.py` + dataclass em `models/`) — sem abstração nova.
  **PASS**.
- **II. Idempotência**: não se aplica a esta feature — o log é um
  registro de execução (intencionalmente não deduplicado; ver edge case
  da spec: duas execuções da mesma fonte geram dois eventos). **PASS**
  (fora de escopo do princípio, que trata de nota fiscal/transação, não
  de log de auditoria).
- **III. Tratamento de erro explícito**: o log só é gravado após o laço
  principal terminar sem exceção (research.md #5) — nenhuma entrada
  externa nova é processada por esta feature (ela só lê o resumo já
  calculado). **PASS**.
- **IV. Dados sensíveis**: o evento de log armazena fonte (nome de
  arquivo) e contagens agregadas — nunca descrição, valor ou conta de
  transação individual. **PASS**.
- **V. Testável por construção**: não é uma rotina de parsing de entrada
  externa (não lida com OCR/scraping/QR code) — testes automatizados
  sintéticos bastam, sem exigência de validação com amostra real
  adicional além da já feita pelos parsers que ela envolve. **PASS**.
- **VI. Português**: página e mensagens em português. **PASS**.
- **VII. Fontes frágeis**: não se aplica — não há integração externa
  frágil nesta feature. **N/A**.
- **VIII. Integridade visual**: página nova introduz superfície visual
  → verificação visual real (captura headless + checagem de console)
  obrigatória antes de promover (já registrado em quickstart.md).
  Nenhum asset de terceiro novo é vendorizado. **PASS, com gate
  pendente de execução na fase de implementação/promoção.**

Nenhuma violação a justificar — Complexity Tracking não se aplica.

## Project Structure

### Documentation (this feature)

```text
specs/014-log-importacoes/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
src/
├── models/
│   └── log_importacao.py        # NOVO — dataclass LogImportacao
├── services/
│   └── importar_historico_extrato.py  # MODIFICADO — grava o log ao fim de processar_transacoes()
├── storage/
│   └── db.py                    # MODIFICADO — tabela log_importacao + inserir_log_importacao/listar_logs_importacao
└── api/
    ├── routes_log_importacoes.py    # NOVO — blueprint com GET /ver/log-importacoes
    ├── app.py                       # MODIFICADO — registrar o blueprint novo
    └── templates/
        └── log_importacoes.html     # NOVO — página de listagem (padrão Argon já usado)

tests/
├── unit/
│   ├── test_log_importacao_processar_transacoes.py  # MODIFICADO — casos de log (evento gravado, período, sem exceção→sem log)
│   └── test_storage_log_importacao.py      # NOVO — inserir/listar
└── integration/
    └── test_log_importacoes_pagina.py      # NOVO — GET /ver/log-importacoes reflete uma importação real
```

**Structure Decision**: Option 1 (single project) — mesma estrutura já
usada por todo o financiALL (`src/{models,services,storage,api}`,
`tests/{unit,integration,contract}`); esta feature não introduz nenhuma
pasta nova, só arquivos dentro da estrutura existente.

## Complexity Tracking

*Sem violações — seção não aplicável.*
