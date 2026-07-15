# Implementation Plan: Revisão Visual do Layout

**Branch**: `006-revisao-visual-layout` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-revisao-visual-layout/spec.md`

## Summary

Substitui o CSS inline atual e a navegação horizontal simples por uma
"pele" visual vendorizada localmente a partir do **Argon Dashboard**
(produto gratuito da Creative Tim, licença MIT — research.md #1),
aplicada a todos os templates Jinja já existentes (Importar, Notas,
detalhe de Nota, Categorias, Resumo, status de Envio). Nenhuma rota,
model, ou lógica de backend muda — é uma reestruturação de
`templates/`/`static/` sobre a aplicação Flask já existente, seguindo o
mesmo padrão de vendorização local sem CDN já usado para o Plotly.js
(feature 005).

## Technical Context

**Language/Version**: HTML/Jinja2 + CSS + JavaScript vanilla (Bootstrap 5,
já incluído no bundle compilado do Argon Dashboard — sem jQuery, sem
conflito esperado com o JS vanilla já existente no projeto).

**Primary Dependencies**: **Argon Dashboard** (`creativetimofficial/argon-dashboard`,
gratuito, licença MIT — research.md #1), vendorizado localmente
(`assets/css/argon-dashboard.min.css`, `assets/js/argon-dashboard.min.js`,
fontes/ícones, todos pré-compilados — sem Node/Gulp). Nenhuma dependência
Python nova.

**Storage**: N/A — nenhuma mudança de schema ou dado.

**Testing**: `pytest` — os testes de contrato já existentes (páginas
retornam `200`, textos/marcadores específicos presentes) servem de rede
de segurança de regressão (FR-002); responsividade e verificação visual
são validadas manualmente (sem navegador headless no projeto, mesma
limitação já registrada nas features 004/005).

**Target Platform**: mesmo servidor (Raspberry Pi self-hosted), mesma
aplicação Flask.

**Project Type**: Web service single-project — mesma estrutura das
features anteriores.

**Performance Goals**: irrelevante para uso pessoal.

**Constraints**: nenhuma rota, comportamento ou contrato de API MUST
mudar (FR-002) — só `templates/` e `static/`. O JS já existente (fetch,
`confirm()`, Plotly) MUST continuar funcionando sem conflito com o JS do
Argon. Os gráficos Plotly (feature 005) MUST continuar legíveis dentro
do novo layout, com a paleta validada intacta (FR-005). A aplicação MUST
continuar carregando por completo sem internet (FR-007) — mesma restrição
de vendorização local já aplicada ao Plotly.

**Scale/Scope**: 1 diretório de assets novo vendorizado, `base.html`
reestruturado (navegação em menu lateral no padrão Argon), 6 templates
existentes adaptados à nova estrutura HTML (cards/tabelas do Argon) sem
alterar nenhuma variável Jinja nem endpoint que consomem.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Simplicidade e Manutenibilidade**: PASS, com uma exceção
  justificada (ver Complexity Tracking) — mesmo raciocínio já aceito
  para o Plotly.js na feature 005: primeira dependência de frontend
  "grande" da área visual, mas vendorizada localmente, sem build step,
  sem gerenciador de pacote no projeto.
- **II. Idempotência é Obrigatória**: N/A — feature não grava nem lê
  dado novo, é puramente apresentação.
- **III. Tratamento de Erro Explícito em Entradas Externas**: N/A —
  nenhuma entrada externa nova nesta feature.
- **IV. Dados Financeiros São Sensíveis**: PASS — nenhuma mudança em
  como dados sensíveis são tratados, mascarados ou exibidos; a
  reestruturação visual não adiciona nem remove nenhum dado exibido.
- **V. Testável por Construção**: PASS — Real-Data Validation não se
  aplica (mesmo raciocínio das features 002/003/005): não há
  processamento de dado externo nesta feature.
- **VI. Português nos Artefatos Voltados ao Usuário**: PASS — nenhum
  texto novo voltado ao usuário além do que já existe; qualquer texto
  de interface do próprio template Argon (ex.: placeholders de exemplo)
  MUST ser substituído ou removido, nunca deixado em inglês na versão
  final.
- **VII. Fontes Frágeis Degradam sem Quebrar o Fluxo Principal**: N/A —
  nenhuma integração externa nova.

Uma exceção justificada ao Princípio I (ver Complexity Tracking) — as
demais seções passam sem ressalva.

## Project Structure

### Documentation (this feature)

```text
specs/006-revisao-visual-layout/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/api/
├── static/
│   ├── plotly-basic.min.js        # ja existente (feature 005), inalterado
│   ├── plotly-basic.LICENSE       # ja existente, inalterado
│   └── argon/                     # novo — assets vendorizados (research.md #1)
│       ├── css/argon-dashboard.min.css
│       ├── js/argon-dashboard.min.js
│       ├── fonts/                 # icones Nucleo + webfonts
│       ├── img/                   # imagens do template (ex.: placeholder de avatar, se usado)
│       └── ARGON.LICENSE          # copia da licenca MIT do projeto de origem
└── templates/
    ├── base.html                  # reestruturado — layout Argon (menu lateral + navbar)
    ├── upload.html                # adaptado ao novo card/form
    ├── notas.html                 # adaptado a tabela estilizada do Argon
    ├── nota_detalhe.html          # adaptado a card + tabela do Argon
    ├── categorias.html            # adaptado a card + tabela do Argon
    ├── resumo.html                # adaptado a cards do Argon (graficos Plotly dentro de card)
    └── envio.html                 # adaptado a card simples do Argon

tests/
└── contract/
    └── test_api_contract.py       # sem teste novo dedicado — os testes existentes
                                    # ja cobrem presenca de conteudo/status por pagina,
                                    # servindo de regressao (FR-002) sem duplicar cobertura
```

**Structure Decision**: projeto único (mesma estrutura das features
anteriores); assets do Argon isolados em `src/api/static/argon/` (não
misturados com `plotly-basic.min.js`) para manter clara a origem de cada
dependência vendorizada. Nenhum diretório novo no nível raiz.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Dependência de frontend nova (Argon Dashboard, CSS/JS) | Pedido explícito do usuário ("incrementar esse visual"), decisão já alinhada em sessão de planejamento anterior de adotar a "pele" Argon; escrever um design system próprio do zero (cards, grid responsivo, tipografia, ícones) seria ordens de magnitude mais trabalho para o mesmo resultado | CSS próprio incremental sobre o `base.html` atual — rejeitada porque o pedido específico foi por esse template, e replicar manualmente a qualidade visual de um design system pronto não se paga para um projeto de uma pessoa. Risco de dependência mitigado vendorizando localmente (sem CDN), sem build step nem gerenciador de pacote — mesmo padrão já aceito para o Plotly.js na feature 005. |
