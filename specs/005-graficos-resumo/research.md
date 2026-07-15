# Research: Gráficos no Resumo de Gastos

A skill de dataviz do harness foi consultada nesta sessão antes de
qualquer decisão de forma/cor (procedimento: forma → cor → validação →
marks → interação). As decisões abaixo seguem essa ordem.

## 1. Forma: pizza (mesmo a skill preferindo stacked bar) e barras

**Decisão**: mantido o gráfico de **pizza** para a distribuição por
categoria, e **barras** para a evolução mensal — exatamente como o
usuário pediu.

**Rationale**: a tabela "job → forma" da skill recomenda **stacked bar**
(não pizza) como forma padrão para "part-to-whole", especialmente
horizontal quando há categorias com nome longo. Pizza não é o padrão
recomendado pela skill para esse job. Ainda assim, o usuário pediu
"pizza" explicitamente, duas vezes (pedido original e nesta spec) — é
uma escolha deliberada, não uma lacuna a preencher com o "melhor"
genérico. Decisão: honrar o pedido explícito, mas aplicar todas as
regras de execução da skill (paleta computada, teto de séries, legenda
sempre visível, dobra em "Outros") para que a pizza seja bem executada,
em vez de repetir os erros comuns do anti-pattern de pizza (muitas
fatias, cores arbitrárias, sem legenda). O gráfico de barras para a
evolução mensal já está alinhado com a própria recomendação da skill
("Compare magnitude" → bar/column), sem conflito.

**Alternatives considered**: stacked bar horizontal (recomendação
"padrão" da skill) — rejeitada por contrariar um pedido explícito e
repetido do usuário sem necessidade real (a pizza, bem executada, não é
"errada" — só não é o primeiro default da skill).

## 2. Cor: paleta categórica de referência da skill, validada nesta sessão

**Decisão**: usar a paleta categórica de 8 cores da skill de dataviz
(`references/palette.md`) tal como está — sem criar uma paleta de marca
própria (o projeto não tem uma ainda). Ordem fixa das 8 cores (azul,
água, amarelo, verde, violeta, vermelho, magenta, laranja), nunca
ciclada. "Sem categoria" e a cauda de categorias além do teto (item 4)
usam o tom neutro/muted (`#898781`), nunca uma cor categórica.

**Validação rodada nesta sessão** (`scripts/validate_palette.js`, não
"no olho" — exigência da skill):

- **Modo claro** (superfície `#fcfcfb`): `ALL CHECKS PASS`. Faixa de
  luminosidade e piso de croma OK; separação CVD com pior par a ΔE 24.2
  (bem acima do alvo ≥12); **WARN de contraste** em 3 das 8 cores (água,
  amarelo, magenta) abaixo de 3:1 — exige "relief": rótulo visível ou
  view em tabela, nunca só a cor.
- **Modo escuro** (superfície `#1a1a19`): `ALL CHECKS PASS`. Faixa de
  luminosidade e contraste OK; **WARN de CVD** no par verde↔amarelo
  (ΔE 10.3, dentro da faixa-piso 8–12) — legal só com codificação
  secundária (rótulo direto).

**Rationale**: os dois WARNs (não FAIL) obrigam a mesma coisa —
**nunca depender só da cor**. Isso vira requisito de design direto:
a legenda ao lado da pizza sempre mostra nome + valor em texto (não só
o swatch colorido), e cada fatia/barra tem tooltip com valor exato ao
passar o mouse — a cor nunca é o único canal de identidade.

**Alternatives considered**: gerar uma paleta nova para este projeto —
rejeitada por ser exatamente o tipo de escolha "no olho" que a skill
existe para evitar; a paleta de referência já está validada e documentada,
suficiente para um projeto sem marca visual própria ainda (a revisão
visual completa é uma feature futura separada).

## 3. Biblioteca de gráficos: Plotly.js, vendorizado localmente

**Decisão**: os dois gráficos usam **Plotly.js** (`plotly.js-basic-dist`,
que cobre `pie` e `bar` — não a distribuição completa, bem maior).
Vendorizado como arquivo estático local em `src/api/static/`, servido
pela própria rota `/static/<path:filename>` que o Flask já expõe por
padrão — **sem CDN**.

**Rationale**: preferência explícita do usuário por Plotly. Reverte a
decisão inicial deste research.md (SVG/JS puro) — registrado aqui para
rastreabilidade da mudança. Vendorizar localmente (em vez de CDN) mantém
o motivo original de não depender de internet no Raspberry Pi self-hosted;
o ganho de usar uma biblioteca em vez de construir os marks à mão é real
aqui: legenda, tooltip por hover/foco e responsividade já vêm prontos,
reduzindo várias tarefas de implementação (interaction.md da skill) a
configuração de `layout`/`config` em vez de código novo. A metodologia da
skill de dataviz continua valendo integralmente — ela é sobre *forma* e
*cor*, não sobre a ferramenta de renderização: a paleta validada
(item 2) é passada direto para `marker.colors` (pizza) / `marker.color`
(barras) do Plotly, mantendo a mesma cor por categoria e o mesmo tom
neutro para "Sem categoria"/"Outros".

**Alternatives considered**: SVG/JS puro (decisão original) — descartada
por preferência direta do usuário, mesmo sendo a opção de menor
dependência; Chart.js — não considerada depois da preferência do usuário
por Plotly especificamente; CDN do Plotly em vez de vendorizar — rejeitada
pelo mesmo motivo de sempre (Pi self-hosted, sem depender de internet
para a própria UI funcionar).

## 4. Atribuição estável de cor por categoria + teto de série

**Decisão**: cada categoria recebe seu slot de cor categórica (1–8) de
forma **estável e determinística**: `slot = categoria.id % 8`. Se num
mês houver mais de 8 categorias distintas com gasto, as categorias de
menor valor são dobradas em uma fatia "Outros" até restarem 8 fatias
coloridas — "Sem categoria" e "Outros" sempre em tom neutro, nunca
ocupam um slot categórico.

No Plotly, esse array de cores é passado explicitamente em
`marker.colors` (pizza) — nunca deixado para a paleta padrão do Plotly
escolher, que não segue nossa regra de estabilidade nem nossa validação.

**Rationale**: a skill exige que a cor **siga a entidade, nunca o
ranking** — trocar o conjunto de categorias visíveis (ex.: filtrar por
mês) não pode repintar as sobreviventes. Usar `id % 8` (não a posição
entre as categorias atualmente exibidas) garante que a mesma categoria
sempre tenha a mesma cor em qualquer gráfico, em qualquer mês, mesmo que
outras categorias sejam criadas/excluídas depois (feature 003). A escada
de séries da skill (7–8 é teto; além disso, dobrar em "Outros") é
aplicada diretamente — hoje o usuário só tem 2 categorias criadas, mas a
regra já protege o gráfico se ele criar muitas mais.

**Alternatives considered**: atribuir cor pela posição/ordem alfabética
das categorias visíveis no mês — rejeitada porque viola a regra "nunca
repintar sobreviventes": criar uma categoria nova que entra antes
alfabeticamente deslocaria a cor de todas as categorias depois dela.

## 5. Gráfico de barras usa a mesma janela do histórico já calculado

**Decisão**: o gráfico de barras usa exatamente `historico_meses_anteriores()`
já existente (meses anteriores ao corrente, completos) — o mês corrente
(parcial) não entra como uma barra a mais, continua exibido separadamente
como já é hoje.

**Rationale**: misturar um mês parcial (corrente, ainda em andamento) com
meses completos no mesmo gráfico de barras induziria a leitura errada
("esse mês caiu" quando na verdade só não acabou) — um anti-padrão de
comparação enganosa. A spec já assume isso ("mesma janela já calculada
pela funcionalidade de histórico existente").

**Alternatives considered**: incluir o mês corrente como última barra
(com alguma marcação visual de "parcial") — não descartado para sempre,
mas fora de escopo desta primeira versão; pode ser revisitado se o
usuário sentir falta.

## 6. Rota de dados: reaproveita o padrão REST-ish já usado

**Decisão**: `GET /notas/resumo/categorias?mes=AAAA-MM` (mês opcional,
default mês corrente) — mesmo padrão de `?mes=` já usado em `GET
/notas`. O gráfico de barras não precisa de rota nova — consome os
mesmos dados já servidos por `GET /notas/resumo/historico`.

**Rationale**: consistência com o contrato de API já documentado
(features 001-004); menos superfície nova por reaproveitar o que já
existe sempre que possível (Princípio I).
