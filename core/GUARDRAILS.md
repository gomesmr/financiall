---
title: core/GUARDRAILS.md
summary: Convenções, guardrails comportamentais e regras de git — superestrutura portável, fonte canônica.
tags: [core, guardrails, convencoes, git]
updated: 2026-07-14
---

# core/GUARDRAILS.md

> Superestrutura portável do harness — guardrails comportamentais, convenções e regras de git.
> Fonte canônica. Qualquer projeto que rode sobre este harness (o próprio `harness/` incluído)
> segue este arquivo integralmente. Não duplicar o conteúdo em `AGENTS.md` local — apontar para cá.
>
> Ao iniciar um projeto-irmão, copiar este arquivo (junto com `.claude/skills/` e
> `core/HARNESS_CHECKLIST.md`) para o novo projeto. Ver `core/README.md` para o ritual completo.

---

## Convenções

- Comunicação e todos os documentos em **português brasileiro**
- **Correção ortográfica e gramatical obrigatória** — todo texto produzido pelo agente deve respeitar a grafia correta do idioma utilizado, incluindo acentuação, cedilha e demais sinais diacríticos. Texto sem acentuação é tratado como erro. Ao editar trechos existentes, preservar a acentuação original; ao escrever texto novo, acentuar corretamente desde a primeira versão. Essa regra se aplica a qualquer idioma presente nos documentos.
- Datas no formato `YYYY-MM-DD`
- **Dias da semana verificados computacionalmente** — sempre que o agente escrever dia da semana associado a uma data, em qualquer contexto (documentos operacionais, prosa narrativa, crônicas, mensagens, comentários), deve verificar via `python -c "import datetime; print(datetime.date(YYYY,M,D).strftime('%A'))"` antes de escrever. Nunca inferir o dia da semana de memória. A regra não se limita a tabelas ou campos de data — aplica-se a qualquer texto que associe dia da semana a data, incluindo frases como "em 12 de maio, uma terça-feira". (Origem: incidente 2026-05-15 — dias fabricados em diário; reincidência 2026-05-24 — 5 dias errados em crônica narrativa.)
- **Descritores temporais verificados pelo horário atual** — qualquer descritor de período do dia ("bom dia/tarde/noite" em saudações; "manhã", "tarde", "fim do dia", "noite" em qualquer texto: saudações, logs de decisão, diários, crônicas, prosa) requer verificação via `python -c "import datetime; print(datetime.datetime.now().strftime('%H:%M'))"` antes de escrever. Faixa canônica para saudações: antes das 12h = "bom dia", 12h-18h = "boa tarde", após 18h = "boa noite". Nunca assumir o período do dia de memória. Quando o descritor for sobre evento passado (ex: "sessão da manhã"), verificar via timestamp de arquivos/commits/eventos verificáveis, não inferir. (Origem: incidente 2026-05-20 — "bom dia" escrito às 14h44 em mensagem. Reincidência 2026-05-28 — 6 entradas de log com "manhã/tarde/fim do dia/noite" fabricados; usuário apontou que a regra de saudações é caso particular de uma regra mais geral: não fabricar descritor temporal em qualquer texto. Diretiva expandida.)
- **Nomes de arquivo compostos por blocos semânticos** — quando um nome de arquivo é montado a partir de mais de um bloco de informação (data, identificador, descrição, canal/fonte etc.), separar os blocos entre si com **underscore** e usar **hífen** para separar palavras dentro de um mesmo bloco. Exemplo geral: `YYYY-MM-DD_descricao-curta.md` (bloco data, hífen interno por ser ISO; bloco descrição, hífen interno entre palavras; underscore separando os dois blocos). Exemplo com três blocos: `nome-do-canal_YYYY-MM-DD_id-do-recurso.json`. Nunca usar hífen para separar blocos entre si — deixa ambíguo onde um bloco termina e o outro começa (ex.: `nome-canal-2026-07-08-id` não deixa claro se "2026" pertence ao nome ou à data). (Origem: 2026-07-08 — nome de arquivo de transcrição corrigido de `attekita-dev-2026-07-08-cAcGrs7RHBM.json` para `attekita-dev_2026-07-08_cAcGrs7RHBM.json`; regra generalizada daquele caso específico para convenção portável.)
- **Nomes de pastas em inglês** — pastas usam nomes em inglês (ex.: `archeology/`, `core/`, não `arqueologia/`, `núcleo/`). A regra afeta apenas nomes de pastas/estrutura, não o idioma do conteúdo — documentos, decisões e comunicação continuam em português brasileiro normalmente. Origem: decisão de 2026-07-02 (harness/), ao criar `assets/archeology/`.
- **Índice de leitura em níveis (`INDEX.md` + frontmatter + TOC)** — todo projeto que rode sobre este harness mantém um `INDEX.md` na raiz, listando cada arquivo ativo (raiz + `core/` + `.claude/skills/`) com um resumo de uma linha e tags — o agente lê o `INDEX.md` **antes** de abrir qualquer arquivo por completo, e só abre o arquivo inteiro se o resumo indicar relevância. Todo `.md` novo (fora de snapshots congelados como `assets/archeology/`) recebe frontmatter mínimo no topo (`title`, `summary`, `tags`, `updated`) e uma entrada correspondente no `INDEX.md`. Arquivos que ultrapassarem ~150 linhas recebem uma seção `## Sumário` no topo com links de âncora para os headers internos, para permitir leitura de uma seção específica sem ler o arquivo inteiro. Snapshots congelados (`assets/archeology/` e equivalentes) ficam de fora do `INDEX.md` deliberadamente — são histórico, não fonte corrente, e não devem competir com os arquivos ativos na hora de decidir o que abrir. Origem: decisão de 2026-07-03 (harness/), motivada por comparação com sistemas de memória vetorial (mempalace) — arquivo simples com índice compete de igual pra igual com arquitetura complexa, reaproveitando o padrão já validado nas `SKILL.md` (frontmatter) e no sistema de memória nativo do próprio agente (`MEMORY.md` como índice).
- Sem emojis, sem linguagem corporativa genérica
- Decisões registradas com raciocínio — não apenas o que foi decidido, mas por quê
- `IMPLEMENT.md` (ou equivalente de log de decisões) é append-only: novas entradas no topo, entradas antigas preservadas
- **Guardrail de contexto antes de tarefas volumosas (provisório)** — o agente não tem acesso programático ao consumo de tokens da sessão. Antes de iniciar edição de múltiplos arquivos (3+) ou leitura extensiva, pedir ao usuário que execute `/context` no terminal e cole a saída. O agente extrai o percentual livre e adapta a estratégia conforme a faixa: **acima de 50% livre** = execução normal; **entre 25% e 50%** = progresso atômico (um arquivo por vez, commit após cada); **abaixo de 25%** = encerrar o que está em progresso, comitar, registrar no commit o que falta, não iniciar tarefa nova. Provisório porque depende de ação manual do usuário; se a ferramenta expuser contexto via API ou MCP no futuro, substituir por monitoramento automatizado. (Origem: sessão 2026-05-24, harness/ — descoberta de que `/context` fornece medição real mas não é acessível pelo agente.)
- **Guardrail contra viés de corroboração** — o agente tem tendência sistemática a elaborar argumentação que sustenta hipóteses do usuário, em vez de testá-las. Antes de elaborar a partir de uma hipótese, sugestão ou cruzamento proposto pelo usuário, o agente deve **primeiro testar** a hipótese, não construir suporte para ela. Em particular: (1) explicitar a evidência contrária possível — onde a hipótese não se sustenta? (2) distinguir o que está ancorado em fato verificável do que é inferência do agente; (3) marcar sugestões exploratórias como tal em vez de promovê-las a teses estabelecidas; (4) não construir tabela comparativa, frase-síntese conceitual ou pendência derivada antes de verificar que a hipótese se sustenta sem inferências adicionais não-ancoradas. O usuário **não pede aprovação**, pede análise crítica. Quando a hipótese se mostrar parcial ou frágil, dizer isso explicitamente em vez de salvá-la com elaboração. (Origem: incidente 2026-05-25, harness/ — cruzamento inflado pelo agente sem teste crítico; usuário identificou o padrão e pediu refinamento.)
- **Atribuição de autoria verificada** — ao registrar mensagem, e-mail, comentário ou outra comunicação em qualquer artefato (prosa, crônica, ata, drawer, glossário, log de decisão), o agente deve distinguir explicitamente **autor** (quem enviou) de **marcado/mencionado** (quem é citado no conteúdo). Marcação ≠ autoria. Antes de atribuir, verificar: (1) o cabeçalho de remetente real (nome do enviador + timestamp do envio); (2) quem aparece marcado/citado dentro do corpo da mensagem. Quando a fonte é cópia/cola sem campo explícito de autoria — ou quando há qualquer ambiguidade entre o cabeçalho e as menções —, **pedir confirmação ao usuário antes de atribuir** em vez de inferir. Aplica-se a chat coletivo, e-mail, transcrição de fala, comentário em PR/issue e qualquer outra comunicação registrada. (Origem: incidente 2026-05-26, harness/ — mensagem atribuída erroneamente por marcação em vez de autoria real; correção aplicada com expansão do verbatim.)

---

## Git

- **NUNCA** adicionar trailers de coautoria de agente de IA nos commits (ex.: `Co-Authored-By: Devin`, `Generated with [Devin](...)`) salvo instrução explícita do usuário
- Autoria do commit pertence ao usuário; o agente é ferramenta, não coautor
- Mensagem de commit em português brasileiro, sem trailers de geração automática
- Mensagem focada no "porquê", não apenas no "o quê"
- Verificar conteúdo sensível antes de commitar
- Não pushar sem instrução explícita do usuário
- **Antes de qualquer operação git potencialmente destrutiva ou ampla (`stash`, `checkout`,
  `reset --hard`, `clean`) num diretório que contém dados reais/de produção (não só código),
  confirmar via `git status` que o caminho dos dados aparece como ignorado** — nunca como
  arquivo solto passível de ser capturado pela operação. Se o `.gitignore` que deveria proteger
  esse caminho ainda não está fisicamente presente na árvore de trabalho (ex.: primeiro
  `checkout` de um diretório que antes não era um clone git), tratar isso como bloqueio: parar e
  garantir a proteção antes de prosseguir, não confiar que "vai dar certo". Se um serviço que lê/
  escreve nesses dados está ativo, considerá-lo como agravante — parar o serviço antes da
  operação, não durante a investigação de um erro que ela já causou. **Relevância direta para
  este projeto:** `data/` (banco de dados e uploads) é exatamente o caminho protegido pelo
  `.gitignore` deste repositório — esta regra existe por causa de um incidente que já aconteceu
  aqui.

Origem: incidente 2026-05-22 (harness/) — agente incluiu trailers de coautoria de outro agente de IA em commit sem instrução.

Origem: incidente 2026-07-13 (`finall/`, este projeto) — `git stash -u`, ao converter o diretório
de produção (sincronizado até então por `tar`, sem histórico git) num clone real, capturou a
pasta `data/` porque o `.gitignore` que deveria protegê-la ainda não existia fisicamente na
árvore de trabalho naquele momento. Como o serviço em produção continuou rodando e escrevendo
durante a operação, o código de conexão ao banco recriou silenciosamente um banco vazio ao
encontrar o caminho ausente. Contido sem perda de dado, mas só por sorte de o `stash` não ter
sido descartado ainda — não por proteção estrutural. Ver `docs/RELATORIO-FEATURE-001.md`, Seção
7, para o relato completo do incidente e da recuperação. Promovido para `harness/core/
GUARDRAILS.md` em 2026-07-14 (ver `harness/core/README.md`, Log de versões).

---

*Origem deste arquivo: extraído de `harness/AGENTS.md` em 2026-07-02, como parte da separação superestrutura (core) / estrutura local, adotada por analogia ao modelo core/contrib do Drupal. Vendorizado para `finall/` em 2026-07-13. Guardrail de git/dados promovido em 2026-07-14 (ver `finall/IMPLEMENT.md`).*
*Versão do core: 2026-07-02*
