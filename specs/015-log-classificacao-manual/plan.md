# Implementation Plan: Log de classificação manual de natureza

**Branch**: `feat/mcl-log-classificacao-manual` (spec dir `015-log-classificacao-manual`) | **Date**: 2026-09-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/015-log-classificacao-manual/spec.md`

## Summary

Registrar automaticamente um evento de histórico toda vez que uma
classificação manual de natureza (em grupo, via fila de pendentes, ou
individual, via edição de uma transação) for aplicada com sucesso —
método, alvo, natureza, categoria e quantidade de transações afetadas —
e expor esse histórico numa página nova (`/ver/log-classificacoes`),
ordenada da mais recente para a mais antiga. Abordagem técnica:
instrumentar os dois pontos de convergência já existentes
(`storage_db.classificar_grupo_pendente_natureza()` e
`storage_db.atribuir_natureza_manual()` — research.md #1), sem tocar nas
rotas Flask que os chamam, gravando numa tabela SQLite nova via o mesmo
padrão repositório já usado por `log_importacao` (feature 014).

## Technical Context

**Language/Version**: Python 3.11 (mesmo do resto do projeto)

**Primary Dependencies**: Flask (rota/página), sqlite3 (stdlib) —
nenhuma dependência nova.

**Storage**: SQLite (`data/financiall.db`), tabela nova
`log_classificacao_manual`.

**Testing**: pytest (`tests/unit`, `tests/integration`), mesmo padrão do
projeto.

**Target Platform**: Servidor Flask rodando no Raspberry Pi (prod porta
5000, dev porta 5005) — mesma infraestrutura já existente.

**Project Type**: Web application (single Flask app, server-rendered
com Jinja2/Argon) — Option 1 da estrutura abaixo.

**Performance Goals**: N/A — volume esperado de dezenas de eventos;
sem exigência de performance além do já padrão do app.

**Constraints**: `classificar_grupo_pendente_natureza()` e
`atribuir_natureza_manual()` não podem mudar de assinatura nem de
comportamento visível (Assumptions da spec) — a instrumentação precisa
ser inteiramente interna a essas duas funções.

**Scale/Scope**: Uma tabela nova, ~2 funções de repositório
(`inserir_log_classificacao_manual`, `listar_logs_classificacao_manual`),
duas pequenas adições nas funções de storage já existentes, um
blueprint/rota nova, um template novo.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Simplicidade**: instrumentação concentrada nos dois pontos de
  convergência já existentes, reaproveitando o padrão repositório já
  usado por `log_importacao`/`compromisso_futuro` — sem abstração nova.
  **PASS**.
- **II. Idempotência**: não se aplica — o log é um registro de auditoria
  intencionalmente não deduplicado (uma reclassificação gera um evento
  novo, FR-004). **PASS** (fora de escopo do princípio, que trata de
  nota fiscal/transação, não de log de auditoria).
- **III. Tratamento de erro explícito**: o log só é gravado depois que a
  operação já confirmou sucesso real (research.md #3) — nenhuma entrada
  externa nova é processada por esta feature. **PASS**.
- **IV. Dados sensíveis**: o evento de log armazena descrição
  normalizada/id de transação, natureza e categoria — nunca valor
  monetário nem dado de terceiro (CPF/CNPJ). **PASS**.
- **V. Testável por construção**: não é uma rotina de parsing de entrada
  externa — testes automatizados sintéticos bastam. **PASS**.
- **VI. Português**: página e mensagens em português. **PASS**.
- **VII. Fontes frágeis**: não se aplica. **N/A**.
- **VIII. Integridade visual**: página nova introduz superfície visual
  → verificação visual real (captura headless + checagem de console)
  obrigatória antes de promover. Nenhum asset de terceiro novo é
  vendorizado. **PASS, com gate pendente de execução na fase de
  implementação/promoção.**

Nenhuma violação a justificar — Complexity Tracking não se aplica.

## Project Structure

### Documentation (this feature)

```text
specs/015-log-classificacao-manual/
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
│   └── log_classificacao_manual.py   # NOVO — dataclass LogClassificacaoManual
├── storage/
│   └── db.py                          # MODIFICADO — tabela log_classificacao_manual +
│                                       #   inserir_log_classificacao_manual/listar_logs_classificacao_manual +
│                                       #   log dentro de classificar_grupo_pendente_natureza/atribuir_natureza_manual
└── api/
    ├── routes_log_classificacoes.py   # NOVO — blueprint com GET /ver/log-classificacoes
    ├── app.py                         # MODIFICADO — registrar o blueprint novo
    └── templates/
        ├── base.html                  # MODIFICADO — link de nav novo
        └── log_classificacoes.html    # NOVO — página de listagem (padrão Argon já usado)

tests/
├── unit/
│   ├── test_storage_log_classificacao_manual.py   # NOVO — inserir/listar
│   └── test_classificacao_natureza_log.py         # NOVO — casos de log em torno das duas funções de storage
└── integration/
    └── test_log_classificacoes_pagina.py          # NOVO — GET /ver/log-classificacoes reflete uma classificação real
```

**Structure Decision**: Option 1 (single project) — mesma estrutura já
usada por todo o financiALL; esta feature não introduz nenhuma pasta
nova, só arquivos dentro da estrutura existente (mesmo padrão da feature
014).

## Complexity Tracking

*Sem violações — seção não aplicável.*
