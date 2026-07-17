# Implementation Plan: Categorização de Itens de Nota Fiscal

**Branch**: `008-categorizacao-itens` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-categorizacao-itens/spec.md`

## Summary

Cada item de nota fiscal passa a receber uma categoria de gasto (taxonomia
de 2 níveis, categoria + subcategoria), reaproveitando a tabela `categoria`
já existente (feature 003) em vez de criar uma base paralela. A
classificação roda em cascata — cache de descrição normalizada (Tier 1) →
regra-semente (Tier 2) → pendente de revisão (Tier 3, caminho manual
primário do v1, sem IA) — como uma etapa nova chamada logo após a inserção
de itens já existente, sem alterar os fluxos de importação já testados
(features 001/004). Uma fila de revisão nova (`/ver/pendentes`) permite
classificar itens individualmente ou em lote por descrição; correção
manual sempre prevalece e realimenta o cache. Exclusão de categoria em uso
passa a exigir prévia de impacto e destino explícito (reatribuir a uma
substituta, ou enviar para pendente), com bloqueio de exclusão de
categoria de topo enquanto tiver subcategorias (clarificação de
2026-07-17).

## Technical Context

**Language/Version**: Python 3.11 + Flask (backend), Jinja2 + JavaScript
vanilla (frontend server-renderizado) — mesma stack do projeto, sem
linguagem nova.

**Primary Dependencies**: nenhuma dependência nova. Normalização de texto
usa `unicodedata` da stdlib (research.md #1); nenhuma biblioteca de
fuzzy-matching é adicionada para detecção de quase-duplicata na criação de
categoria — comparação feita sobre `nome_normalizado` (mesmo campo/técnica
já usado desde a feature 003) mais uma checagem de proximidade simples
(prefixo/substring) suficiente para o volume de categorias de uma
taxonomia pessoal (dezenas, não milhares).

**Storage**: SQLite (`data/financiall.db`), mesmo arquivo já usado por
todas as features anteriores. Extensão de schema via `ALTER TABLE`
idempotente (`categoria.parent_id`; `item_nota.categoria_id` +
`descricao_normalizada` + `metodo_classificacao`) e três tabelas novas
(`cache_descricao_categoria`, `regra_categoria`,
`historico_classificacao_item`) via `CREATE TABLE IF NOT EXISTS`; o
índice único global de `categoria.nome_normalizado` (feature 003) é
substituído por dois índices parciais escopados por nível (research.md
#19) — ver data-model.md.

**Testing**: `pytest` para normalização, cascata de classificação (cache →
regra → pendente), CRUD de taxonomia hierárquica, exclusão com
destino/bloqueio, e os contratos HTTP novos — mesmo padrão dos testes já
existentes (unit/integration/contract). Teste parametrizado sobre o
corpus real de 327 descrições (`assets/files.zip/corpus-descricoes-produtos.txt`,
copiado para `tests/fixtures/`) como primeira barreira do Princípio V.
Validação com amostra real (segunda barreira, distinta) obrigatória antes
de promover: rodar a cascata sobre o backlog real de notas já importadas
no Pi (dev) e revisar uma amostra do resultado — research.md #13.

**Target Platform**: mesmo Raspberry Pi self-hosted já em produção,
acessado via navegador (celular/computador) na rede local — nenhuma
mudança de plataforma.

**Project Type**: Web service single-project — mesma estrutura das
features anteriores.

**Performance Goals**: irrelevante para uso pessoal (poucas notas/itens
por mês); a cascata roda de forma síncrona logo após a inserção de itens,
sem impacto perceptível no tempo de resposta de importação já aceito hoje.

**Constraints**: v1 é totalmente local — nenhuma chamada de rede/IA na
cascata de classificação (Assumptions do spec); a aplicação continua
funcionando por completo sem acesso à internet. Nenhuma mudança nos
contratos de `POST /notas` e `POST /notas/<id>/categoria` já existentes
(contracts/api.md).

**Scale/Scope**: 3 tabelas novas, extensão de 2 tabelas existentes, ~1
serviço novo (`classificacao_itens.py`) + extensão de `categorias.py`, 1
blueprint novo (`routes_itens.py`) ou extensão de `routes_categorias.py`
(ver Project Structure), 2 superfícies visuais novas/alteradas
(`/ver/pendentes` nova; `/ver/categorias` ganha hierarquia).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Simplicidade e Manutenibilidade**: PASS. Reaproveita a tabela
  `categoria` já existente em vez de uma base paralela (research.md #3);
  simplifica deliberadamente em relação ao brief de preparação em três
  pontos — sem `tipo_match` regex (research.md #5), sem fluxo de
  aprovação de regra (research.md #7), "corrigir a fonte" opera só no
  nível do cache, nunca editando regra diretamente (research.md #11).
  Nenhuma dependência nova.
- **II. Idempotência é Obrigatória**: PASS — a cascata de classificação só
  atua sobre itens com `categoria_id IS NULL` (research.md #8), o que
  torna reprocessamento de nota e migração de backlog histórico
  idempotentes por construção, sem lógica extra de deduplicação
  (FR-015). A dedução de nota em si (chave/hash) continua inalterada.
- **III. Tratamento de Erro Explícito em Entradas Externas**: N/A direto
  — a cascata processa a descrição do item já persistida (não uma nova
  entrada externa não tratada); os erros de validação (categoria
  inexistente, exclusão bloqueada por subcategoria, destino ausente) são
  tratados explicitamente nos endpoints novos (contracts/api.md), mesmo
  padrão dos endpoints já existentes.
- **IV. Dados Financeiros São Sensíveis**: PASS — nenhuma mudança em como
  CPF/chave/CNPJ/valor são tratados; a classificação lida só com
  descrição de item e categoria, nunca enviados a serviço externo no v1
  (Assumptions do spec).
- **V. Testável por Construção**: APLICA-SE — a descrição de item vem de
  fonte externa não controlada (OCR/scraping, mesma origem já coberta
  pelo princípio nas features 001/004). Validação com amostra real
  (corpus + backlog real do Pi) é barreira distinta dos testes
  automatizados sintéticos, obrigatória antes de promover (research.md
  #13).
- **VI. Português nos Artefatos Voltados ao Usuário**: PASS — toda
  mensagem de erro, rótulo de categoria e texto da fila de pendentes em
  português, mesmo padrão já usado.
- **VII. Fontes Frágeis Degradam sem Quebrar o Fluxo Principal**: PASS —
  item sem cache nem regra nunca bloqueia a importação da nota (FR-008,
  mesmo espírito do `status: pendente_revisao` já existente em
  `nota_fiscal`).
- **VIII. Integridade Visual e de Assets de Terceiros**: APLICA-SE
  DIRETAMENTE — duas superfícies visuais novas/alteradas exigem
  verificação visual real antes de promover (research.md #14). Nenhum
  asset de terceiro novo é vendorizado — cláusula de integridade de asset
  não se aplica.

Nenhuma exceção ao Princípio I é necessária — todas as seções passam sem
ressalva.

## Project Structure

### Documentation (this feature)

```text
specs/008-categorizacao-itens/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── api.md            # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/storage/
└── db.py                      # existente — ganha as colunas/tabelas novas (data-model.md) e as
                                # operações de repositório novas (classificar_item_automaticamente,
                                # atribuir_categoria_manual, classificar_grupo_pendente,
                                # calcular_impacto_correcao_fonte, corrigir_fonte_e_reclassificar,
                                # calcular_impacto_exclusao, excluir_categoria_com_destino,
                                # listar_itens_pendentes) + excluir_categoria ganha destino explícito

src/models/
├── categoria.py               # existente — ganha parent_id
└── item_nota.py                # existente — ganha categoria_id, descricao_normalizada, metodo_classificacao

src/services/
├── normalizacao.py            # novo — normalizar_descricao() (research.md #1/#2)
├── classificacao_itens.py     # novo — cascata cache → regra → pendente (research.md #8)
└── categorias.py              # existente — ganha validação de quase-duplicata (FR-002), validação
                                # de nível para categoria substituta, e a orquestração de exclusão
                                # com destino/bloqueio (research.md #12)

src/api/
├── routes_categorias.py       # existente — POST/DELETE ganham parent_id/destino; novo
                                # GET /categorias/<id>/impacto-exclusao
├── routes_itens.py            # novo — GET /itens/pendentes, POST /itens/pendentes/classificar-grupo,
                                # PUT /itens/<id>/categoria, GET/POST .../impacto-correcao-fonte
                                # e .../corrigir-fonte (contracts/api.md)
├── app.py                      # existente — registra o blueprint novo routes_itens
└── templates/
    ├── base.html               # existente — ganha o link de navegação para /ver/pendentes
    ├── categorias.html        # existente — ganha exibição hierárquica, criar subcategoria,
                                #             aviso de quase-duplicata, fluxo de exclusão com prévia/destino
    ├── nota_detalhe.html       # existente — tabela de itens ganha categoria/subcategoria por item,
                                #              correção individual, e o fluxo "corrigir a fonte" (US4)
    └── pendentes.html          # novo — fila de revisão (agrupada por descrição; visão por nota)

src/scripts/
└── seed_taxonomia_categorizacao.py  # novo — carrega taxonomia-semente e regras-semente validadas
                                       # na Tarefa 1 (idempotente: só insere o que ainda não existe)

tests/
├── fixtures/
│   └── corpus_descricoes_produtos.txt  # novo — copiado de assets/files.zip (research.md #13)
├── unit/
│   ├── test_normalizacao.py           # novo
│   ├── test_classificacao_itens.py    # novo — inclui teste parametrizado sobre o corpus real
│   └── test_categorias.py             # existente — ganha hierarquia, quase-duplicata, exclusão c/ destino
├── contract/
│   └── test_api_contract.py           # existente — ganha os casos de contracts/api.md
└── integration/
    └── test_api.py                    # existente — ganha os fluxos ponta a ponta novos
```

**Structure Decision**: projeto único (mesma estrutura das features
001-007); item de nota ganha um blueprint próprio (`routes_itens.py`) em
vez de crescer dentro de `routes_categorias.py` ou `routes_importar.py`,
porque a fila de pendentes e a classificação de item são uma
responsabilidade nova e independente (opera sobre `item_nota`, não sobre
`categoria` nem sobre o fluxo de importação em si) — mesmo padrão de
separação por domínio já usado no projeto (`routes_categorias.py` nasceu
separado por essa mesma razão na feature 003). `categorias.py` (serviço e
rotas) continua sendo o dono do CRUD de taxonomia, só ganha campo/validação
nova. `seed_taxonomia_categorizacao.py` entra em `src/scripts/`, mesmo
pacote já usado para o entrypoint CLI da feature 004, por não ser uma rota
HTTP.

## Complexity Tracking

> Não se aplica — nenhuma violação da Constitution Check.
