# Implementation Plan: Importar Extrato Bancário

**Branch**: `feat/mcl-importar-extrato-bancario` | **Date**: 2026-07-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-importar-extrato-bancario/spec.md`

## Summary

Extrato bancário e fatura de cartão passam a alimentar a mesma base única
do financiALL, através de uma nova entidade `Transacao` classificada em
cascata (`tipo` cru → `natureza` via cache/regra/manual → `categoria_id`
só quando `natureza=gasto`, reaproveitando a taxonomia já reservada pela
feature 008). Toda transação com `natureza=gasto` tenta reconciliar
automaticamente com uma nota fiscal (valor + janela de data), o que torna a
transação a fonte de verdade do valor sem duplicar o gasto já contado pela
nota — o resumo mensal passa a somar transação (gasto) + nota não
reconciliada, calculado ao vivo, nunca as duas para a mesma compra. A
migração histórica lê o `registro.json` já processado pelo script legado
(418 transações reais); o fluxo recorrente ganha um parser para fatura Itaú
(XLS), reaproveitando a mesma persistência/classificação/reconciliação da
migração. Uma nova entidade `Estabelecimento` (identidade por CNPJ/CPF, com
fallback por descrição normalizada) recebe nome fantasia e tipo por uma fila
de gerenciamento, no mesmo padrão da fila de pendentes de item (feature
008), destravando `gasto_por_estabelecimento` para transações sem nota.

## Technical Context

**Language/Version**: Python 3.11 + Flask — mesma stack do projeto, sem
linguagem nova.

**Primary Dependencies**: `xlrd>=2.0` (nova — leitura de `.xls`, formato
real da fatura Itaú exportada do internet banking; research.md #10). Nenhuma
outra dependência nova — a migração histórica lê JSON (stdlib).

**Storage**: SQLite (`data/financiall.db`), mesmo arquivo. 4 tabelas novas
(`transacao`, `estabelecimento`, `cache_descricao_natureza`,
`regra_natureza`) via `CREATE TABLE IF NOT EXISTS` em `init_db()` — seguro
para o banco de produção/dev já existente no Pi. Reaproveita `categoria`
(inclusive `TAXONOMIA_RESERVADA_EXTRATO` já semeada pela feature 008) e
`nota_fiscal` sem alteração de schema.

**Testing**: `pytest`, mesmo padrão (`tests/unit`, `tests/contract`,
`tests/integration`). Validação com amostra real obrigatória antes de
promover (Princípio V) — migração histórica completa contra o
`registro.json` real (418 transações) e o parser recorrente contra pelo
menos 2 faturas Itaú reais (quickstart.md).

**Target Platform**: mesmo Raspberry Pi self-hosted já em produção — sem
mudança de plataforma.

**Project Type**: Web service single-project — mesma estrutura.

**Performance Goals**: irrelevante para uso pessoal (centenas de
transações, não milhares); reconciliação é uma query por transação
(`valor` + janela de data), volume real pequeno o bastante para não
precisar de índice composto dedicado além dos já criados.

**Constraints**: nenhuma mudança nos contratos já existentes de nota fiscal
(`POST /notas`, `PUT /notas/<id>/categoria` etc.) além da extensão pontual
em `GET /ver/notas/<id>` para exibir/desvincular a reconciliação
(contracts/api.md).

**Scale/Scope**: 4 tabelas novas, 0 colunas novas em tabelas existentes;
1 script de seed novo + 2 scripts de importação novos (histórico + parser
recorrente); ~3 serviços novos (`classificacao_natureza`,
`importar_historico_extrato`, `importar_extrato_itau_cartao`) + extensão de
`resumo.py`; ~12 rotas novas (fila de natureza, fila de reconciliação, fila
de estabelecimento) + extensão pontual de 4 rotas existentes; 2 superfícies
visuais novas (`transacoes_pendentes.html`, `estabelecimentos_pendentes.html`)
+ extensão pequena de `nota_detalhe.html`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Simplicidade e Manutenibilidade**: PASS. Reaproveita a cascata
  cache/regra/manual já validada em produção (feature 008) para um segundo
  domínio (natureza) em vez de inventar mecanismo novo; reaproveita a
  taxonomia de categoria já reservada (`TAXONOMIA_RESERVADA_EXTRATO`) sem
  criar categorias novas; resumo calculado ao vivo (sem tabela de cache/job
  de recomputação) porque `resumo.py` já é query on-demand. Única
  dependência nova (`xlrd`) é estritamente necessária pelo formato real do
  arquivo bancário (research.md #10).
- **II. Idempotência é Obrigatória**: PASS — `transacao.fingerprint` único,
  mesma fórmula entre migração histórica e parser recorrente (research.md
  #1/#2, FR-023); `inserir_transacao` idempotente por fingerprint, mesma
  semântica de `buscar_por_chave_acesso` para nota fiscal.
- **III. Tratamento de Erro Explícito em Entradas Externas**: PASS —
  `registro.json` ilegível ou arquivo `.xls` corrompido abortam a execução
  inteira sem gravar dado parcial (FR-024); registro individual malformado
  é pulado, não trava o lote (mesmo padrão de `importar_historico`).
- **IV. Dados Financeiros São Sensíveis**: PASS — CPF/CNPJ de estabelecimento,
  conta e valores nunca aparecem em log/stdout além de contagens agregadas
  (FR-025, contracts/cli.md); mesma disciplina já aplicada a nota fiscal.
- **V. Testável por Construção**: APLICA-SE — o parser de fatura Itaú lê
  arquivo externo (formato do banco, fora do controle do projeto) e a
  reconciliação decide sobre dado real de duas fontes independentes;
  validação com amostra real (418 transações do histórico + faturas reais)
  é barreira obrigatória e distinta dos testes sintéticos antes de promover
  (quickstart.md "Validação com dado real").
- **VI. Português nos Artefatos Voltados ao Usuário**: PASS — mensagens de
  script, rótulos das duas telas novas e erros em português.
- **VII. Fontes Frágeis Degradam sem Quebrar o Fluxo Principal**: PASS —
  transação sem natureza resolvida, sem reconciliação encontrada, ou sem
  estabelecimento identificado nunca bloqueia a importação (FR-002, edge
  cases do spec.md) — cada uma fica pendente numa fila, degradação
  graciosa consistente com o tratamento já dado a item de nota sem
  categoria (feature 008).
- **VIII. Integridade Visual e de Assets de Terceiros**: APLICA-SE — duas
  páginas novas (`/ver/transacoes/pendentes`, `/ver/estabelecimentos/pendentes`)
  exigem verificação visual real (captura headless + checagem de console)
  antes de promover para produção; nenhum asset de terceiro novo é
  vendorizado nesta feature (reaproveita CSS/JS já existente de
  `pendentes.html`/`classificacao.js`).

Nenhuma violação sem justificativa — Complexity Tracking não se aplica.

## Project Structure

### Documentation (this feature)

```text
specs/010-importar-extrato-bancario/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── api.md
│   └── cli.md
└── tasks.md             # gerado por /speckit-tasks
```

### Source Code (repository root)

```text
src/
├── models/
│   ├── transacao.py                        # novo
│   └── estabelecimento.py                  # novo
├── services/
│   ├── classificacao_natureza.py           # novo
│   ├── importar_historico_extrato.py       # novo
│   ├── importar_extrato_itau_cartao.py     # novo
│   ├── reconciliacao.py                    # novo
│   └── resumo.py                           # estendido
├── storage/
│   └── db.py                               # estendido (SCHEMA + operações novas)
├── scripts/
│   ├── regras_semente_natureza.json        # novo
│   └── seed_regras_natureza.py             # novo
└── api/
    ├── routes_transacoes.py                # novo (fila natureza + reconciliação)
    ├── routes_estabelecimentos.py          # novo
    ├── routes_importar.py                  # sem mudança de contrato
    ├── routes_consulta.py                  # estendido (resumo, nota_detalhe)
    └── templates/
        ├── transacoes_pendentes.html       # novo
        ├── estabelecimentos_pendentes.html # novo
        └── nota_detalhe.html               # estendido

tests/
├── unit/
│   ├── test_classificacao_natureza.py
│   ├── test_reconciliacao.py
│   └── test_resumo.py                      # estendido
├── contract/
│   └── test_api_contract.py                # estendido
└── integration/
    └── test_importar_historico_extrato.py
```

**Structure Decision**: mesma estrutura single-project já usada pelo
projeto (`src/{models,services,storage,api,scripts}` + `tests/{unit,
contract,integration}`), sem diretório novo — cada peça nova entra no
mesmo lugar onde sua contraparte de nota fiscal/item já mora.

## Complexity Tracking

*Nenhuma violação da Constitution Check acima — seção não aplicável.*
