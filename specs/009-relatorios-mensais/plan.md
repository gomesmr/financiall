# Implementation Plan: Relatórios Mensais (Resumo por Item + Estabelecimento + Navegação por Mês)

**Branch**: `feat/mcl-relatorios-mensais` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-relatorios-mensais/spec.md`

## Summary

O resumo mensal (`/ver/resumo`) passa a agregar gasto por categoria a partir
dos **itens** classificados (feature 008) quando a nota tiver pelo menos um
item classificado, caindo para a categoria da própria nota só quando nenhum
item estiver classificado. A categoria da nota (`nota_fiscal.categoria_id`,
feature 003) passa a ser tratada explicitamente como **tipo de
estabelecimento** (Supermercado, Mercearia, Restaurante, Bar, Saúde ›
Dentista, Saúde › Plano de Saúde etc.) — um eixo independente de "o que foi
comprado". O resumo ganha navegação por mês unificada (substituindo o
seletor solto + lista separada de meses anteriores), um seletor de dimensão
(por item / por estabelecimento / os dois) com toggle de nível (categoria de
topo / subcategoria), e ação de drill-down para a listagem de notas do mês
(e do tipo de estabelecimento, quando aplicável). A listagem de notas
(`/ver/notas`) passa a agrupar visualmente por mês como modo padrão. Nenhuma
tabela ou coluna nova é criada — tudo reaproveita `categoria.parent_id`
(feature 008) e `nota_fiscal.categoria_id` (feature 003) já existentes.

## Technical Context

**Language/Version**: Python 3.11 + Flask (backend), Jinja2 + JavaScript
vanilla (frontend server-renderizado) — mesma stack do projeto, sem
linguagem nova.

**Primary Dependencies**: nenhuma dependência nova. Plotly.js já vendorizado
(feature 005) para os gráficos; evento nativo `plotly_click` para o
drill-down (research.md #5), sem biblioteca adicional.

**Storage**: SQLite (`data/financiall.db`), mesmo arquivo. Nenhuma alteração
de schema — reaproveita `categoria.parent_id` e `nota_fiscal.categoria_id`
já existentes (data-model.md). Novas linhas-semente idempotentes na tabela
`categoria` via script novo (research.md #7).

**Testing**: `pytest`, mesmo padrão já existente (`tests/unit/test_resumo.py`,
`tests/contract/test_api_contract.py`, `tests/integration/test_api.py`).
Validação com amostra real (segunda barreira, Princípio V) obrigatória antes
de promover: rodar a nova agregação por item e a reclassificação de
estabelecimento sobre o backlog real de notas já importadas no Pi (dev) —
research.md #8, quickstart.md.

**Target Platform**: mesmo Raspberry Pi self-hosted já em produção, acessado
via navegador (celular/computador) na rede local — nenhuma mudança de
plataforma.

**Project Type**: Web service single-project — mesma estrutura das features
anteriores.

**Performance Goals**: irrelevante para uso pessoal (poucas notas/itens por
mês); agregação em Python sobre resultado de uma query já pequena
(research.md #1).

**Constraints**: nenhuma mudança nos contratos `POST /notas` e
`POST /notas/<id>/categoria` já existentes; extensão apenas dos endpoints de
leitura do resumo e da listagem de notas (contracts/api.md).

**Scale/Scope**: 0 tabelas novas, 0 colunas novas; 1 script novo de seed
idempotente; ~4 funções novas/renomeadas em `resumo.py`; extensão de 3 rotas
existentes (`/ver/resumo`, `/ver/notas`, `/notas/resumo/categorias`);
1 parâmetro novo em `listar_notas`; 2 superfícies visuais redesenhadas
(`resumo.html`, `notas.html`) + 1 ajuste pequeno em `nota_detalhe.html`
(rótulo "Categoria" → "Tipo de estabelecimento" + autocomplete hierárquico
reaproveitado de `classificacao.js`, feature 008).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Simplicidade e Manutenibilidade**: PASS. Reaproveita `categoria`,
  `nota_fiscal.categoria_id`, `listar_notas` e a função de agregação já
  existente (renomeada, não duplicada — research.md #2); agregação em Python
  em vez de SQL complexo, proporcional ao volume real de dados (research.md
  #1); reclassificação de notas reais sem repetir a cerimônia de documento
  de revisão da feature 008, desproporcional a este volume (research.md #8).
  Nenhuma dependência nova.
- **II. Idempotência é Obrigatória**: PASS — o script de seed da taxonomia de
  estabelecimento só insere o que ainda não existe (research.md #7),
  reaproveitando a validação de duplicata já existente em `criar_categoria`.
  Não há mudança na deduplicação de nota fiscal em si.
- **III. Tratamento de Erro Explícito em Entradas Externas**: N/A direto —
  esta feature agrega dado já validado e persistido (nenhuma entrada externa
  nova); parâmetros de query inválidos (`dimensao`/`nivel` fora do esperado)
  degradam para o default em vez de erro 400 (contracts/api.md), consistente
  com o padrão de tolerância já usado no projeto para páginas de uso pessoal.
- **IV. Dados Financeiros São Sensíveis**: PASS — nenhuma mudança em como
  CPF/chave/CNPJ/valor são tratados ou logados.
- **V. Testável por Construção**: APLICA-SE — a nova agregação por item e a
  reclassificação de estabelecimento operam sobre dado real já importado
  (proveniente de OCR/scraping, fonte externa original das features
  001/004/008). Validação com o backlog real do Pi (dev) é barreira distinta
  dos testes automatizados sintéticos, obrigatória antes de promover
  (research.md #8, quickstart.md "Validação com dado real").
- **VI. Português nos Artefatos Voltados ao Usuário**: PASS — rótulos novos
  ("Tipo de estabelecimento", "Por item", "Por estabelecimento", "Os dois",
  mensagens de mês vazio) em português, mesmo padrão já usado.
- **VII. Fontes Frágeis Degradam sem Quebrar o Fluxo Principal**: N/A — esta
  feature não integra nenhuma fonte externa frágil nova.
- **VIII. Integridade Visual e de Assets de Terceiros**: APLICA-SE
  DIRETAMENTE — duas páginas redesenhadas (`resumo.html`, `notas.html`) e um
  ajuste em `nota_detalhe.html` exigem verificação visual real antes de
  promover (research.md #10, quickstart.md "Verificação visual"). Nenhum
  asset de terceiro novo é vendorizado — cláusula de integridade de asset
  não se aplica.

Nenhuma exceção ao Princípio I é necessária — todas as seções passam sem
ressalva.

## Project Structure

### Documentation (this feature)

```text
specs/009-relatorios-mensais/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── api.md            # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/storage/
└── db.py                      # existente — listar_notas ganha parametro opcional categoria_id
                                # (filtro por tipo de estabelecimento, FR-006/data-model.md); nenhuma
                                # tabela/coluna nova, nenhuma outra funcao muda de assinatura.

src/services/
└── resumo.py                   # existente — gasto_por_categoria renomeada para
                                 # gasto_por_estabelecimento (+ parametro nivel); nova
                                 # gasto_por_categoria_item (+ parametro nivel); novas
                                 # listar_meses_com_notas e resumo_de_mes (navegacao,
                                 # research.md #4); mes_atual/gasto_mes_corrente/
                                 # historico_meses_anteriores inalteradas.

src/scripts/
└── seed_taxonomia_estabelecimento.py  # novo — mesmo padrao do
                                          # seed_taxonomia_categorizacao.py (feature 008),
                                          # insere taxonomia-semente de estabelecimento
                                          # (research.md #7), idempotente.

src/api/
├── routes_consulta.py         # existente — pagina_resumo (mes/dimensao/nivel + navegacao
                                # de mes), pagina_notas (mes/estabelecimento + agrupamento
                                # por mes em Python), resumo_categorias (dimensao/nivel)
└── templates/
    ├── resumo.html            # existente — redesign: navegacao unificada de mes, seletor
                                #             de dimensao (item/estabelecimento/os dois) +
                                #             nivel, drill-down por clique na fatia
                                #             (plotly_click)
    ├── notas.html              # existente — redesign: agrupamento visual por mes,
                                 #              filtro/badge de estabelecimento ativo
    └── nota_detalhe.html       # existente — rotulo "Categoria" -> "Tipo de
                                 #              estabelecimento", reaproveita o
                                 #              autocomplete hierarquico de classificacao.js
                                 #              (feature 008) em vez do <select> plano

tests/
├── unit/
│   └── test_resumo.py          # existente — testes de gasto_por_categoria migram para
                                 #             gasto_por_estabelecimento; novos testes de
                                 #             gasto_por_categoria_item (fallback, nivel),
                                 #             listar_meses_com_notas, resumo_de_mes
├── contract/
│   └── test_api_contract.py    # existente — ganha os casos de contracts/api.md
                                 #             (dimensao/nivel/estabelecimento)
└── integration/
    └── test_api.py             # existente — ganha os fluxos ponta a ponta novos
                                 #             (drill-down, agrupamento por mes)
```

**Structure Decision**: projeto único (mesma estrutura das features
001-008); nenhuma pasta/módulo novo além do script de seed — a lógica de
agregação continua dentro de `src/services/resumo.py` (mesmo dono já
responsável por essa responsabilidade desde a feature 005), e as rotas
continuam dentro de `routes_consulta.py` (mesmo dono das páginas
`/ver/resumo` e `/ver/notas` desde as features 001/005). `listar_notas`
ganha um parâmetro em vez de uma função nova, pois o filtro por
estabelecimento é conceitualmente o mesmo tipo de filtro que `mes`/`titular`
já existentes.

## Complexity Tracking

> Não se aplica — nenhuma violação da Constitution Check.
