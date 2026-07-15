# Implementation Plan: Gráficos no Resumo de Gastos

**Branch**: `005-graficos-resumo` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-graficos-resumo/spec.md`

## Summary

Adiciona à página de resumo já existente (`/ver/resumo`) um gráfico de
pizza (distribuição do gasto por categoria do mês corrente, ou de um mês
do histórico escolhido pelo usuário) e um gráfico de barras (evolução do
gasto mês a mês, visualizando a tabela "Meses anteriores" já calculada).
Os dois gráficos são renderizados com **Plotly.js** (`plotly.js-basic-dist`,
vendorizado localmente, sem CDN — preferência explícita do usuário,
research.md #3), com forma e paleta de cores decididas seguindo a
metodologia da skill de dataviz consultada nesta sessão (forma → cor →
validação → marks → interação, nessa ordem) — a cor é passada explicitamente
para o Plotly a partir da paleta validada, nunca a paleta padrão da
biblioteca. Nenhuma tabela/coluna de banco nova — só uma consulta agregada
nova (gasto por categoria por mês) sobre dados já existentes.

## Technical Context

**Language/Version**: Python 3.11+ (agregação no backend) + JavaScript
vanilla no navegador (nenhum framework/transpilador).

**Primary Dependencies**: **Plotly.js** (`plotly.js-basic-dist`, cobre
`pie`/`bar`), vendorizado como arquivo estático local — preferência
explícita do usuário, ver research.md #3 (reverte a decisão inicial de
SVG/JS puro). Nenhuma dependência Python nova; reaproveita
Flask/Jinja/`sqlite3`.

**Storage**: SQLite — nenhuma tabela/coluna nova. Nova consulta agregada
(`LEFT JOIN nota_fiscal`/`categoria`, agrupada por categoria, filtrada por
mês) sobre o schema já existente.

**Testing**: `pytest` — unidade (agregação de gasto por categoria: soma
correta, "sem categoria" incluída como grupo próprio, notas sem
`valor_total` excluídas da soma — mesma regra já aplicada ao resumo
existente), integração (rota JSON nova retorna os valores certos e batem
com o total já exibido em texto, FR-006).

**Target Platform**: mesmo servidor, mesma página `/ver/resumo`.

**Project Type**: Web service single-project — mesma estrutura das
features anteriores, sem projeto/pasta novo.

**Performance Goals**: irrelevante — dezenas de notas, poucas categorias,
poucas dezenas de meses no histórico.

**Constraints**: paleta e execução dos gráficos MUST seguir a skill de
dataviz consultada nesta sessão (`references/palette.md`,
`color-formula.md`, `marks-and-anatomy.md`, `interaction.md`) —
**cor computada e validada por script, nunca escolhida no olho**
(research.md #2 registra o resultado real da validação rodada nesta
sessão). "Sem categoria" e qualquer categoria que exceda o teto de 8
cores categóricas MUST usar tom neutro (cinza), nunca uma cor categórica
nova gerada. Plotly.js vendorizado localmente (sem CDN); sem passo de
build (o arquivo já vem minificado, só é copiado para `static/`).
Os valores exibidos nos gráficos MUST bater exatamente com os já
exibidos em texto na mesma página (FR-006) — nunca duas fontes de
verdade divergentes para o mesmo número.

**Scale/Scope**: 1 função de serviço nova (`gasto_por_categoria`), 1 rota
JSON nova, 1 arquivo estático vendorizado (Plotly.js), ajustes em
`resumo.html` (gráfico de pizza + barras via Plotly, com legenda/tooltip
nativos, paleta de cores e seletor de mês). Sem mudança de schema.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Simplicidade e Manutenibilidade**: PASS, com uma exceção
  justificada (ver Complexity Tracking) — Plotly.js é a primeira
  dependência de frontend do projeto, mas vendorizada localmente (sem
  CDN, sem passo de build, um único arquivo estático) e por preferência
  explícita do usuário; reaproveita a agregação de histórico já
  calculada para o gráfico de barras.
- **II. Idempotência é Obrigatória**: N/A — feature é somente leitura,
  não grava nenhum dado novo.
- **III. Tratamento de Erro Explícito em Entradas Externas**: PASS. Mês
  sem nenhuma nota com valor gasto exibe mensagem clara em vez de
  tentar desenhar um gráfico vazio ou quebrado (FR-005). Não há entrada
  externa nova nesta feature (mês escolhido vem de um seletor da própria
  UI, não de arquivo/URL/upload).
- **IV. Dados Financeiros São Sensíveis**: PASS. Gráficos mostram só
  valores agregados (soma por categoria/mês) — nunca CPF, CNPJ ou chave
  de acesso individual. Nenhuma exposição nova.
- **V. Testável por Construção**: PASS — Real-Data Validation não se
  aplica (mesmo raciocínio das features 002/003): a agregação opera
  sobre dado já validado ao entrar na base (import/categorização), não
  processa arquivo ou fonte externa nova.
- **VI. Português nos Artefatos Voltados ao Usuário**: PASS. Legendas,
  rótulos, mensagens de "sem dados" e tooltips em português.
- **VII. Fontes Frágeis Degradam sem Quebrar o Fluxo Principal**: N/A —
  nenhuma integração externa nova.

Uma exceção justificada ao Princípio I (ver Complexity Tracking) — as
demais seções passam sem ressalva.

## Project Structure

### Documentation (this feature)

```text
specs/005-graficos-resumo/
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
├── services/
│   └── resumo.py                  # + gasto_por_categoria(mes, db_path) -> list[GastoCategoria]
├── api/
│   ├── routes_consulta.py         # + rota GET /notas/resumo/categorias?mes=AAAA-MM
│   │                               # + pagina_resumo passa historico/meses pro template
│   ├── static/
│   │   └── plotly-basic.min.js    # novo — Plotly.js vendorizado (research.md #3)
│   └── templates/
│       ├── base.html              # + variaveis CSS da paleta categorica (light/dark)
│       └── resumo.html            # + <script src="/static/plotly-basic.min.js">
│                                   #   + Plotly.newPlot (pizza + barras) + seletor de mes

tests/
├── unit/
│   └── test_resumo.py             # + gasto_por_categoria: soma, "sem categoria", exclusao de valor nulo
└── integration/
    └── test_api.py                # + GET /notas/resumo/categorias bate com o total em texto
```

**Structure Decision**: projeto único (mesma estrutura das features
anteriores); nenhum diretório novo no nível raiz. Toda a lógica de
agregação fica em `services/resumo.py` (já existe, mesmo módulo do
resumo em texto) — os gráficos são só uma forma nova de exibir dado que
o serviço já sabe calcular, não uma feature de dados separada.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Dependência de frontend nova (Plotly.js) | Preferência explícita do usuário, expressa durante o planejamento desta feature; também reduz trabalho de implementação real (legenda, tooltip e responsividade vêm prontos em vez de construídos à mão em SVG) | SVG/JS puro (decisão inicial deste plano) foi descartada por não ser o que o usuário quer usar — mantê-la seria ignorar uma preferência direta sem ganho correspondente. O risco de dependência é mitigado vendorizando localmente (sem CDN) um único arquivo estático, sem passo de build nem gerenciador de pacote no projeto. |
