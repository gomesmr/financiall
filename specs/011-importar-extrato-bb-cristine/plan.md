# Implementation Plan: Importar extrato BB (Cristine) e visão por titular

**Branch**: `011-importar-extrato-bb-cristine` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-importar-extrato-bb-cristine/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Estender a feature 010 (importar extrato bancário) para cobrir a conta
corrente do Banco do Brasil da Cristine, hoje fora de escopo. A descoberta
central da investigação de código (research.md #1) é que **quase toda a
infraestrutura necessária já existe e já é titular-aware**: o schema de
`transacao` já tem coluna `titular`, o dataclass `Transacao` já tem o campo,
e `processar_transacoes()` (núcleo já usado pela migração histórica e pelo
parser recorrente de cartão Itaú) já repassa `titular` sem alteração. O
trabalho real é: (1) um parser novo para o formato de extrato do BB,
seguindo o mesmo padrão do parser recorrente de cartão Itaú (`parsear()` +
script CLI, sem tabela intermediária tipo `registro.json`); (2) uma entrada
nova em `conta_canonica.py` mapeando a conta do BB para um identificador
canônico terminado em `_cc`, reaproveitando de graça a lógica de sinal e a
janela de reconciliação de 3 dias já existente para contas correntes; (3)
regras de natureza semente para o vocabulário da Cristine, com o `LANÇAMENTOS
REAIS` de `Cristine.xlsx` servindo de gabarito; (4) um filtro por titular em
`/ver/resumo` e nas funções de `resumo_service`, espelhando o padrão de
filtro por titular que `/ver/notas` já implementa.

## Technical Context

**Language/Version**: Python 3.11+ (mesmo runtime do projeto)

**Primary Dependencies**: Flask (já usado), `openpyxl` (**nova** — o extrato
do BB é `.xlsx`; `xlrd` (já usado pelo parser Itaú) não lê esse formato
desde a v2.0)

**Storage**: SQLite (`src/storage/db.py`), schema já pronto — nenhuma
migração de coluna necessária (`transacao.titular` já existe desde a
feature 010)

**Testing**: pytest (unit + contract, mesmo padrão das features anteriores)

**Target Platform**: aplicação web self-hosted (Raspberry Pi, mesmo destino
de deploy das features anteriores)

**Project Type**: single project (web service) — mesma estrutura já usada

**Performance Goals**: escala pessoal (algumas centenas de transações por
mês, 2 titulares) — sem meta de performance dedicada

**Constraints**: idempotência (Princípio II/FR-004), degradação graciosa
para formato de extrato inesperado (Princípio VII), nenhum dado sensível em
log (Princípio IV)

**Scale/Scope**: histórico real de 5 arquivos (jan–mai/2026) + importação
recorrente contínua daqui em diante

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Simplicidade**: PASSA. Nenhuma abstração nova — o parser BB segue
  literalmente o mesmo formato de `src/services/importar_extrato_itau_cartao.py`
  (função `parsear()` retornando `list[dict]` + script CLI fino), reaproveitando
  `processar_transacoes()` sem alteração. `conta_canonica.py` ganha uma
  entrada de dicionário, não um novo mecanismo.
- **II. Idempotência**: PASSA. Mesmo mecanismo de fingerprint
  (`calcular_fingerprint`) já usado por todo o pipeline — nenhuma lógica de
  dedup nova.
- **III. Tratamento de erro em entrada externa**: PASSA. Arquivo `.xlsx`
  ilegível ou linha com dado ausente segue o mesmo padrão já estabelecido
  (`ArquivoExtratoError` para arquivo inteiro ilegível; linha individual
  pulada e contada em `puladas` sem abortar o restante).
- **IV. Dados sensíveis**: PASSA. Segue o padrão já existente — só contagens
  agregadas no stdout do script, nunca descrição/valor/conta individual.
- **V. Testável por construção**: aplica-se — parsing de extrato bruto é
  "dado vindo de fora do controle do código". PASSA desde que (a) teste
  automatizado cubra o parser BB (linhas de saldo, formato de valor BR,
  timestamp embutido em "Detalhes") e (b) a importação histórica real rode
  contra os 5 arquivos reais já baixados antes de promover para produção —
  planejado explicitamente em tasks.md/quickstart.md como segunda barreira,
  não substituível pelos testes sintéticos.
- **VI. Português**: PASSA. Mensagens de script e UI em português, mesmo
  padrão.
- **VII. Fontes frágeis degradam sem quebrar**: PASSA. Linha de extrato BB
  não reconhecida (formato mudou, célula vazia) é pulada individualmente,
  nunca aborta a importação inteira — mesmo padrão do parser Itaú.
- **VIII. Integridade visual**: aplica-se à mudança em `/ver/resumo`
  (seletor de titular) — verificação visual (headless + console) obrigatória
  antes de promover, mesmo padrão já seguido nas features 009/010. Nenhum
  asset de terceiro novo é vendorizado nesta feature.

Nenhuma violação a justificar em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/011-importar-extrato-bb-cristine/
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
├── models/
│   └── transacao.py                       # já tem `titular` — sem mudança
├── services/
│   ├── conta_canonica.py                  # + entrada BB -> "bb_cristine_cc"
│   ├── importar_extrato_bb.py             # NOVO — parsear() do extrato BB
│   ├── importar_historico_extrato.py      # processar_transacoes() reaproveitado sem mudança
│   └── resumo.py                          # + parâmetro titular opcional nas funções de resumo
├── scripts/
│   ├── importar_extrato_bb.py             # NOVO — CLI, espelha importar_extrato_itau_cartao.py
│   └── regras_semente_natureza.json       # + regras para vocabulário da Cristine
└── api/
    ├── routes_consulta.py                 # pagina_resumo ganha filtro titular
    └── templates/
        └── resumo.html                    # seletor de titular (mesmo padrão de notas.html)

tests/
├── contract/
│   └── test_api_contract.py               # + testes do filtro titular em /ver/resumo
├── integration/
│   └── test_importar_extrato_bb.py        # NOVO
└── unit/
    ├── test_importar_extrato_bb.py        # NOVO — parser (linhas de saldo, formato BR, timestamp)
    ├── test_conta_canonica.py             # + caso BB
    └── test_resumo.py                     # + filtro titular
```

**Structure Decision**: projeto único (mesma estrutura já usada pelas
features 001–010) — `src/{models,services,api,scripts}` + `tests/{unit,
contract,integration}`. Nenhuma estrutura nova introduzida; a feature só
adiciona arquivos dentro dos diretórios já existentes, seguindo o par
service+script já estabelecido pelo parser recorrente de cartão Itaú
(feature 010, US6).

## Complexity Tracking

*Sem violações do Constitution Check — seção não aplicável.*
