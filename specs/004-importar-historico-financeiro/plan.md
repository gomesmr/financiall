# Implementation Plan: Importar Histórico Financeiro

**Branch**: `004-importar-historico-financeiro` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-importar-historico-financeiro/spec.md`

## Summary

Um script de linha de comando (migração pontual, não uma rota HTTP) lê o
arquivo de histórico já existente do sistema anterior do usuário e grava
na base do financiALL toda nota que ainda não existe (por chave de
acesso), com seus itens, status "completa" e sem categoria. Cada nota
importada ganha um novo atributo — `titular` (Marcelo/Cristine) — mapeado
da mesma informação já presente no histórico, exibido e filtrável na UI
de notas já existente. Idempotência reaproveita o índice único de
`chave_acesso` já existente (nenhuma lógica de dedupe nova); um registro
malformado no meio do arquivo é pulado com aviso, sem abortar a
importação inteira.

## Technical Context

**Language/Version**: Python 3.11+ (mesmo ambiente das features
anteriores).

**Primary Dependencies**: stdlib `json`, `sqlite3`, `argparse`. Nenhuma
dependência nova.

**Storage**: SQLite (`data/financiall.db`) — nova coluna `titular` em
`nota_fiscal`, adicionada via `ALTER TABLE` idempotente (mesmo padrão de
`categoria_id`, feature 003).

**Testing**: `pytest` — unidade (mapeamento de um registro do histórico
para `NotaFiscal`/`ItemNota`, conversão de valores monetários e de data,
registro malformado pulado sem abortar o lote, idempotência numa segunda
execução), integração (rodar a importação sobre um arquivo de fixture
pequeno — nunca o arquivo real do usuário — e conferir a base resultante;
filtro `?titular=` em `GET /notas`).

**Target Platform**: mesmo servidor (Raspberry Pi / self-hosted). A
importação roda como script (`python -m src.scripts.importar_historico
<arquivo>`), executado manualmente pelo responsável do projeto — não é
uma rota HTTP nem uma ação da UI web (decisão já tomada no planejamento).

**Project Type**: Web service single-project + um script CLI pontual —
mesma estrutura das features 001-003, sem novo projeto/pasta no nível
raiz.

**Performance Goals**: irrelevante — 22 notas no arquivo atual, dezenas
esperadas no total.

**Constraints**: cada nota do histórico MUST ser gravada com seus itens
numa única transação (uma interrupção no meio da importação em lote nunca
pode deixar nota sem itens correspondentes — edge case explícito da
spec). Um registro sem chave de acesso reconhecível MUST ser pulado com
aviso, sem abortar as demais notas do arquivo. **Nenhum CPF, CNPJ, chave
de acesso ou valor monetário real MUST aparecer em log, mensagem de
diagnóstico ou qualquer saída da rotina** (Princípio IV) — inclui a saída
do próprio script para o operador.

**Scale/Scope**: 1 coluna nova, 1 função de repositório transacional
nova, 1 módulo de serviço de importação, 1 script CLI, ajustes pequenos
em 2 rotas e 1 template existentes para exibir/filtrar por titular.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Simplicidade e Manutenibilidade**: PASS. `json`/`sqlite3` da
  stdlib, sem framework de ETL/migração de dados; script CLI simples,
  mesmo padrão de `src/main.py` como entrypoint.
- **II. Idempotência é Obrigatória**: PASS, reforça o princípio. A
  importação reaproveita o índice único existente de `chave_acesso` —
  mesmo mecanismo *check-before-insert* já usado em
  `services/importador.py` — nenhuma lógica de dedupe nova.
- **III. Tratamento de Erro Explícito em Entradas Externas**: PASS. O
  arquivo de histórico é dado de proveniência externa (gerado por um
  sistema anterior, fora do controle deste código) — arquivo ausente/
  ilegível aborta com erro claro (FR-007); um registro individual
  malformado é pulado com aviso, não propaga exceção nem aborta o lote
  inteiro.
- **IV. Dados Financeiros São Sensíveis**: PASS, com atenção reforçada.
  Nesta sessão de planejamento eu mesmo expus dado real (chave, CNPJ,
  emitente, valor, item) ao inspecionar o arquivo sem mascarar — a
  rotina e qualquer inspeção futura desse arquivo MUST nunca imprimir
  esses campos em texto claro, só contagens/nomes de campo/tipos.
- **V. Testável por Construção**: PASS, e o gate de validação com
  amostra real **se aplica** aqui — ao contrário das features 002/003
  (dado só entrava por digitação do próprio usuário na UI), esta rotina
  processa dado de proveniência externa (histórico de outro sistema),
  exatamente o tipo de entrada que o Princípio V trata como merecedora
  de uma segunda barreira distinta do teste sintético. A validação real
  usa o próprio arquivo do usuário (22 notas), sem imprimir seu
  conteúdo (Princípio IV acima).
- **VI. Português nos Artefatos Voltados ao Usuário**: PASS. Mensagens
  de erro/resumo do script e a UI (coluna/filtro de titular) em
  português.
- **VII. Fontes Frágeis Degradam sem Quebrar o Fluxo Principal**: PASS
  por analogia — o arquivo de histórico não é uma fonte "viva" (é um
  arquivo estático já capturado), mas tem qualidade heterogênea entre
  registros (campos presentes em uns e ausentes em outros, já observado
  na inspeção); um registro ruim MUST degradar (pular, avisar) sem
  interromper o processamento dos demais, mesmo espírito do princípio.

Nenhuma violação identificada. Complexity Tracking não se aplica.

## Project Structure

### Documentation (this feature)

```text
specs/004-importar-historico-financeiro/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── models/
│   └── nota_fiscal.py             # + campo titular
├── storage/
│   └── db.py                      # + coluna titular (ALTER idempotente)
│                                   # + inserir_nota_com_itens (transacional)
│                                   # + listar_notas(titular=...)
├── services/
│   └── importar_historico.py      # novo — parsing, mapeamento, orquestracao do lote
├── scripts/
│   ├── __init__.py                # novo pacote
│   └── importar_historico.py      # novo — entrypoint CLI (argparse, resumo em portugues)
├── api/
│   ├── routes_consulta.py         # + filtro titular (pagina_notas, listar_notas JSON)
│   ├── routes_importar.py         # + campo titular em nota_to_dict
│   └── templates/
│       └── notas.html             # + coluna titular + links de filtro

tests/
├── unit/
│   └── test_importar_historico.py # mapeamento, conversao de valores, registro malformado, idempotencia
└── integration/
    └── test_api.py                # + filtro ?titular= em GET /notas
```

**Structure Decision**: projeto único (mesma estrutura das features
001-003); novo pacote `src/scripts/` para o entrypoint CLI, separado de
`src/api/` porque não é uma rota HTTP — mesmo racional de separação por
natureza de entrada já usado no projeto (`services/` para lógica,
`storage/` para persistência, camada de entrada dedicada por canal).

## Complexity Tracking

> Não se aplica — nenhuma violação da Constitution Check.
