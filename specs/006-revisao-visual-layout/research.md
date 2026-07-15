# Research: Revisão Visual do Layout

## 1. Fonte do template: `creativetimofficial/argon-dashboard` (gratuito, MIT)

**Decisão**: vendorizar a partir do produto **Argon Dashboard** puro
(HTML/CSS/JS, Bootstrap 5) — `github.com/creativetimofficial/argon-dashboard`
— não a edição "Argon Dashboard Flask" (que empacota um esqueleto de
aplicação Flask completo: app factory, models, auth). Confirmado nesta
sessão via consulta ao repositório: licença **MIT**
(`LICENSE.md` do próprio repositório), permite uso, modificação e
distribuição, inclusive em projeto que não é o financiALL público
original — sem custo, sem atribuição obrigatória além da manutenção do
arquivo de licença.

**Rationale**: a decisão de projeto já tomada é "pele, não esqueleto" —
queremos só os assets visuais e a estrutura HTML (sidebar, navbar,
cards, tabelas), mantendo nosso Flask/blueprints/sqlite exatamente como
estão (research.md da sessão de planejamento anterior à spec). A edição
"Flask" do produto empacota justamente o esqueleto que não queremos
(app factory, SQLAlchemy, scaffolding de autenticação) — usá-la exigiria
encaixar nosso código dentro da estrutura deles ou extrair manualmente
só os templates de lá, o que não economiza trabalho sobre partir direto
do produto HTML puro.

**Alternatives considered**: "Argon Dashboard Flask" (edição completa) —
rejeitada pelo motivo acima, já era a alternativa descartada na decisão
de projeto anterior a esta spec; outro template gratuito qualquer — não
avaliado, pedido do usuário já nomeou este especificamente.

## 2. Assets pré-compilados, sem Node/Gulp

**Decisão**: vendorizar os arquivos já compilados/minificados do
repositório (`assets/css/argon-dashboard.min.css`,
`assets/js/argon-dashboard.min.js`, `assets/fonts/`, `assets/img/` — os
nomes exatos são confirmados durante a tarefa de download, feature 005
já estabeleceu que isso é uma tarefa de implementação, não de pesquisa).
Não se usa a pasta `assets/scss/` (fonte Sass, exigiria build).

**Rationale**: mesmo racional da feature 005 (Plotly.js) — o projeto não
tem Node/npm como ferramenta de desenvolvimento; introduzir um passo de
build só para gerar CSS que o próprio repositório de origem já
disponibiliza pronto seria complexidade sem ganho (Princípio I).

## 3. Baixar exige aprovação explícita da fonte (mesmo processo da feature 005)

**Decisão**: a tarefa de download dos assets (fase de implementação, não
deste plano) MUST pedir confirmação explícita do usuário sobre a URL
exata antes de baixar — mesmo processo já seguido para o Plotly.js
(classificador de segurança do agente bloqueia download de código
executável de fonte não nomeada explicitamente pelo usuário).

**Rationale**: registrado aqui para não repetir a surpresa da feature
005 — antecipar que essa aprovação vai ser pedida de novo antes de
qualquer tentativa de download.

## 4. Layout: menu lateral (sidebar) substitui a navegação horizontal atual

**Decisão**: adotar o layout padrão do Argon Dashboard — menu lateral
fixo (recolhível em telas estreitas) + navbar superior — no lugar da
barra horizontal simples de `base.html` hoje. As mesmas 4 seções
(Importar, Notas, Categorias, Resumo) viram itens do menu lateral.

**Rationale**: é o layout padrão do template escolhido, já responsivo
por construção (colapsa num menu hambúrguer em telas estreitas) —
atende FR-003 sem trabalho de adaptação manual de uma navegação
horizontal para mobile.

**Alternatives considered**: manter a navegação horizontal atual só com
cores/tipografia do Argon — rejeitada por entregar responsividade pior
(uma barra horizontal com 4 links já é apertada em tela de celular) e
não aproveitar o design responsivo que o template já resolve pronto.

## 5. Compatibilidade com o JS/CSS já existente (fetch, `confirm()`, Plotly)

**Decisão**: nenhuma mudança no JS de domínio já existente (chamadas
`fetch`, `confirm()` antes de ações destrutivas, os scripts de
`resumo.html` que montam os gráficos Plotly) — só a marcação HTML ao
redor (classes CSS, estrutura de card/tabela) muda. Os containers dos
gráficos Plotly (`#grafico-pizza`/`#grafico-barras`, já com altura
explícita desde a correção da feature 005) MUST ficar dentro de um card
do Argon com largura previsível, para não reintroduzir o bug de
sobreposição já corrigido.

**Rationale**: Bootstrap 5 (base do Argon) não depende de jQuery,
reduzindo risco de conflito com o JS vanilla já existente. FR-002/FR-005
exigem exatamente essa preservação de comportamento — qualquer
adaptação visual dos templates MUST tratar o HTML ao redor dos gráficos
como "não confiável para redimensionar sem verificar", já que isso já
causou um bug real nesta mesma sessão.

## 6. Sem tema escuro completo do Argon neste ciclo

**Decisão**: não implementar um tema escuro dedicado e completo do
Argon nesta feature — só garantir que nada fica ilegível/quebrado em
modo escuro (FR do texto branco em fundo branco, etc., mesmo tratamento
básico), já registrado como suposição na spec.

**Rationale**: os gráficos (feature 005) já tratam `prefers-color-scheme`
por conta própria; replicar um tema escuro visualmente refinado em cima
de um template pensado primariamente para modo claro é trabalho
adicional não pedido explicitamente pelo usuário para este ciclo.
