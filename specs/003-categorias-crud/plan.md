# Implementation Plan: CRUD de Categorias

**Branch**: `003-categorias-crud` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-categorias-crud/spec.md`

## Summary

Adiciona uma entidade `categoria` (nome único) com CRUD completo pela UI web
existente, e uma associação opcional de categoria a `nota_fiscal` (nota
inteira, não por item — granularidade combinada com o usuário, deixando a
evolução para item-nível como horizonte futuro sem travar o schema). A
atribuição é sempre manual (sem motor de regra/IA neste ciclo). Excluir
uma categoria em uso desassocia as notas (elas voltam a "sem categoria")
em vez de bloquear — mesmo espírito não-destrutivo/gracioso já adotado na
feature 002. Reaproveita integralmente Flask + `sqlite3` + templates Jinja
já existentes, sem ORM nem framework novo.

## Technical Context

**Language/Version**: Python 3.11+ (mesmo ambiente das features 001/002).

**Primary Dependencies**: `Flask` (rotas novas nos blueprints existentes);
stdlib `sqlite3`. Nenhuma dependência nova.

**Storage**: SQLite (`data/financiall.db`) — nova tabela `categoria` e
nova coluna `categoria_id` (nullable) em `nota_fiscal`. Adicionada via
`ALTER TABLE` idempotente em `init_db()` (não via `CREATE TABLE IF NOT
EXISTS`, que não altera uma tabela já existente) — o banco de produção e
de desenvolvimento no Raspberry Pi já existem com dados reais, mesmo
raciocínio de research.md #1 da feature 002.

**Testing**: `pytest` — unidade (repositório de categoria: criar, listar,
editar, excluir, unicidade de nome, desassociação em cascata), integração
(rotas HTTP ponta a ponta) e contrato (formato das respostas), mesmo
padrão de `tests/unit`, `tests/integration`, `tests/contract` já
existentes.

**Target Platform**: mesmo servidor (Raspberry Pi / self-hosted via
`waitress`) e mesma UI web servida pelo Flask.

**Project Type**: Web service single-project — mesma estrutura das
features 001/002, sem novo projeto/pasta.

**Performance Goals**: não crítico — uso pessoal, dezenas de categorias no
máximo.

**Constraints**: criar/editar categoria MUST recusar nome vazio ou
duplicado (comparação insensível a maiúsculas/minúsculas e a espaços nas
pontas) antes de gravar. Excluir uma categoria MUST ser atômico junto com
a desassociação das notas que a usavam (uma transação única) — nunca
deixar uma nota apontando para uma categoria que não existe mais.

**Scale/Scope**: 1 tabela nova, 1 coluna nova em tabela existente, 5 rotas
HTTP novas (CRUD de categoria + atribuição em nota), 1 template novo
(`categorias.html`), ajustes em 2 templates existentes (`notas.html`,
`nota_detalhe.html`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Simplicidade e Manutenibilidade**: PASS. Reaproveita Flask,
  `sqlite3` cru e templates Jinja já existentes; nenhuma dependência,
  ORM ou ferramenta de migração nova. A checagem de nome único usa um
  índice único no banco (defesa em profundidade, mesmo padrão já usado
  para `chave_acesso`/`hash_conteudo` de `nota_fiscal`), não uma camada
  nova de validação.
- **II. Idempotência é Obrigatória**: PASS, aplicado por analogia —
  criar a mesma categoria duas vezes (mesmo nome, variando
  maiúsculas/espaços) nunca resulta em duas linhas; o índice único
  garante isso independentemente da checagem em nível de aplicação.
- **III. Tratamento de Erro Explícito em Entradas Externas**: PASS. Nome
  vazio, nome duplicado, categoria inexistente e nota inexistente
  retornam erro tratado (4xx + mensagem em português), nunca exceção não
  tratada.
- **IV. Dados Financeiros São Sensíveis**: N/A — nome de categoria não é
  CPF/CNPJ/chave/valor; nenhuma mudança nesta feature introduz exposição
  de dado sensível novo.
- **V. Testável por Construção**: PASS, com nota — Real-Data Validation
  não se aplica (mesmo raciocínio de research.md da feature 002): esta
  feature não processa dado vindo de fora do controle do código (não é
  OCR, scraping nem parsing de formato externo); nome de categoria é
  digitado pelo próprio usuário na UI.
- **VI. Português nos Artefatos Voltados ao Usuário**: PASS. Mensagens de
  validação, confirmação e templates em português.
- **VII. Fontes Frágeis Degradam sem Quebrar o Fluxo Principal**: N/A —
  nenhuma integração externa nova.

Nenhuma violação identificada. Complexity Tracking não se aplica.

## Project Structure

### Documentation (this feature)

```text
specs/003-categorias-crud/
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
│   └── categoria.py           # novo — dataclass Categoria (id, nome)
├── storage/
│   └── db.py                  # + tabela categoria, coluna nota_fiscal.categoria_id (ALTER idempotente)
│                               # + criar_categoria, listar_categorias, buscar_categoria_por_id,
│                               #   editar_categoria, excluir_categoria, atribuir_categoria_a_nota
├── services/
│   └── categorias.py          # novo — validação de nome (vazio/duplicado) antes de gravar
├── api/
│   ├── routes_categorias.py   # novo blueprint — CRUD de categoria + atribuir a nota
│   └── templates/
│       ├── categorias.html    # novo — lista + criar + editar + excluir
│       ├── notas.html         # + coluna "Categoria"
│       └── nota_detalhe.html  # + seletor de categoria (atribuir/trocar/remover)

tests/
├── unit/
│   └── test_categorias.py     # unicidade de nome, desassociacao em cascata, validacao
└── integration/
    └── test_api.py            # + casos: CRUD de categoria via HTTP, atribuir categoria a nota
```

**Structure Decision**: projeto único (mesma estrutura das features
001/002); nenhum diretório novo no nível raiz. Categoria ganha seu próprio
blueprint (`routes_categorias.py`) em vez de entrar em
`routes_importar.py`/`routes_consulta.py`, porque é uma entidade nova e
independente (não é uma operação sobre nota), seguindo o mesmo padrão de
separação por domínio já usado no projeto.

## Complexity Tracking

> Não se aplica — nenhuma violação da Constitution Check.
