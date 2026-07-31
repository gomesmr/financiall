# Implementation Plan: Importar fatura do cartão Mercado Pago

**Branch**: `012-importar-fatura-mercado-pago` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/012-importar-fatura-mercado-pago/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Adicionar um parser recorrente novo para a fatura em PDF do cartão de
crédito Mercado Pago, seguindo o mesmo padrão já estabelecido pelos
parsers de fatura Itaú e extrato BB: `parsear()` retornando `list[dict]` +
script CLI fino, reaproveitando `processar_transacoes()` sem alteração
estrutural. O trabalho real, descoberto processando o arquivo real do
usuário antes de codificar (research.md): (1) extrair texto do PDF nativo
com `pdfplumber` (nova dependência) e reconhecer seções por cabeçalho
(`Movimentações na fatura`, `Cartão ... [****NNNN]`) em vez de tabela
estruturada; (2) inferir o ano de cada lançamento a partir da data de
emissão da fatura, já que a linha só traz dia/mês; (3) **preservar** o
texto "Parcela X de Y" na descrição (achado crítico, research.md #4) para
não colidir o fingerprint entre parcelas consecutivas da mesma compra
parcelada — sem isso, a importação recorrente descartaria parcelas novas
como duplicatas; (4) duas entradas novas em `conta_canonica.py` (por
cartão + uma genérica para encargos da fatura) e uma extensão pequena de
`_eh_conta_cartao()` para que a conta genérica de encargos use a
convenção de sinal correta (positivo = gasto); (5) filtrar o lançamento de
pagamento da fatura anterior (mesma razão do filtro já existente no
parser Itaú); (6) seed de regras de natureza para o vocabulário novo de
encargos (juros de mora, multa, rotativo, IOF).

## Technical Context

**Language/Version**: Python 3.11+ (mesmo runtime do projeto)

**Primary Dependencies**: Flask (já usado), `pdfplumber` (**nova** — a
fatura Mercado Pago é PDF nativo com texto selecionável; `pdf2image`/OCR,
já usado no projeto para nota fiscal, seria menos confiável e
desnecessário para este formato — research.md #1)

**Storage**: SQLite (`src/storage/db.py`), schema já pronto — nenhuma
migração de coluna necessária (só novos valores de `conta`, dentro da
coluna `TEXT` já existente)

**Testing**: pytest (unit + contract, mesmo padrão das features
anteriores)

**Target Platform**: aplicação web self-hosted (Raspberry Pi, mesmo
destino de deploy das features anteriores)

**Project Type**: single project (web service) — mesma estrutura já
usada

**Performance Goals**: escala pessoal (uma fatura por mês, ~20-30
lançamentos) — sem meta de performance dedicada

**Constraints**: idempotência mesmo entre parcelas consecutivas da mesma
compra parcelada (Princípio II, research.md #4), degradação graciosa para
layout de fatura inesperado (Princípio VII), nenhum dado sensível em log
(Princípio IV)

**Scale/Scope**: histórico real de 1 arquivo (junho/2026) + importação
recorrente mensal contínua daqui em diante

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Simplicidade**: PASSA. Nenhuma abstração nova — o parser Mercado
  Pago segue literalmente o mesmo formato de
  `src/services/importar_extrato_itau_cartao.py` (função `parsear()`
  retornando `list[dict]` + script CLI fino), reaproveitando
  `processar_transacoes()` sem alteração. `conta_canonica.py` ganha
  entradas de dicionário/regex, não um novo mecanismo. A extensão de
  `_eh_conta_cartao()` é uma condição adicional numa função já existente,
  não uma abstração nova.
- **II. Idempotência**: PASSA, com atenção documentada. Mesmo mecanismo de
  fingerprint (`calcular_fingerprint`) já usado por todo o pipeline —
  nenhuma lógica de dedup nova. O achado de research.md #4 (preservar
  "Parcela X de Y" na descrição) existe exatamente para que a idempotência
  não vire perda de dado real entre parcelas consecutivas.
- **III. Tratamento de erro em entrada externa**: PASSA. Arquivo PDF
  ilegível, corrompido, ou sem "Emitida em" reconhecível levanta erro e
  aborta só aquele arquivo (mesmo padrão de `ArquivoExtratoError` já
  usado); linha individual fora de seção reconhecida é pulada sem abortar
  o restante.
- **IV. Dados sensíveis**: PASSA. Segue o padrão já existente — só
  contagens agregadas no stdout do script, nunca descrição/valor/conta
  individual.
- **V. Testável por construção**: aplica-se — parsing de PDF de fatura é
  "dado vindo de fora do controle do código". PASSA desde que (a) teste
  automatizado sintético cubra o parser (seções, cabeçalhos, inferência de
  ano, filtro de pagamento, preservação de parcela) e (b) a importação
  rode contra o arquivo real do usuário
  (`assets/novos-extratos/mercado-pago-2026-06.pdf`) antes de promover
  dev → main — planejado explicitamente em tasks.md/quickstart.md como
  segunda barreira, não substituível pelos testes sintéticos. Dimensão de
  variação relevante já identificada (research.md): layout de PDF nativo
  com múltiplas seções de cartão + seção de encargos gerais.
- **VI. Português**: PASSA. Mensagens de script em português, mesmo
  padrão.
- **VII. Fontes frágeis degradam sem quebrar**: PASSA. Linha de fatura não
  reconhecida (fora de qualquer seção, ou formato de lançamento
  inesperado) é pulada individualmente, nunca aborta a importação inteira
  — mesmo padrão dos parsers Itaú/BB.
- **VIII. Integridade visual**: não se aplica — esta feature não introduz
  nem altera superfície visual (só um parser novo + script CLI).

Nenhuma violação a justificar em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/012-importar-fatura-mercado-pago/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── cli.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── services/
│   ├── conta_canonica.py                  # + entradas MercadoPago / MercadoPago_<NNNN>
│   ├── importar_fatura_mercado_pago.py    # NOVO — parsear() da fatura PDF
│   └── importar_historico_extrato.py      # _eh_conta_cartao() estendido (research.md #6); processar_transacoes() reaproveitado sem mudança
├── scripts/
│   ├── importar_fatura_mercado_pago.py    # NOVO — CLI, espelha importar_extrato_itau_cartao.py
│   └── regras_semente_natureza.json       # + regras dos encargos Mercado Pago
└── (nenhuma mudança em api/ — sem superfície visual nova)

tests/
├── integration/
│   └── test_importar_fatura_mercado_pago.py   # NOVO
└── unit/
    ├── test_importar_fatura_mercado_pago.py   # NOVO — parser (seções, ano, filtro pagamento, parcela)
    └── test_conta_canonica.py                 # + casos Mercado Pago
```

**Structure Decision**: projeto único (mesma estrutura já usada pelas
features 001–011) — `src/{services,scripts}` + `tests/{unit,integration}`.
Nenhuma estrutura nova introduzida; a feature só adiciona arquivos dentro
dos diretórios já existentes, seguindo o par service+script já
estabelecido pelo parser recorrente de cartão Itaú (feature 010, US6).
Sem mudança em `src/api/` — esta feature não introduz superfície visual
(Constitution Check, Princípio VIII: não se aplica).

## Complexity Tracking

*Sem violações do Constitution Check — seção não aplicável.*
