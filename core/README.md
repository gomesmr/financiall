---
title: core/README.md
summary: O que é core/, ritual de bootstrap de projetos-irmãos e hábito de promoção de lições.
tags: [core, bootstrap, documentacao]
updated: 2026-07-08
---

# core/

> Superestrutura portável do harness — a parte que qualquer projeto-irmão herda ao nascer.
> Adotado em 2026-07-02, por analogia ao modelo core/contrib do Drupal: existe um núcleo
> estável e evolutivo (`core/`), e cada site/projeto constrói sua camada local em cima dele
> sem editar o núcleo diretamente. Quando o núcleo evolui, os projetos que dependem dele
> podem atualizar sua instalação local.

---

## Por que isto existe

Antes desta separação, cada projeto-irmão (`d2c-management/`, `edp/`, `catch/`) nascia como
uma cópia única do `AGENTS.md` do harness/ no momento da criação — uma cópia de mão única.
Se o harness/ aprendia uma lição nova depois (um guardrail, uma convenção), ela não voltava
para os projetos já criados, e cada um divergia silenciosamente do que já tinha sido aprendido.

O `core/` resolve isso separando duas coisas que estavam misturadas dentro de `AGENTS.md`:

- **Superestrutura (`core/`):** portável, reaproveitável em qualquer projeto. Guardrails
  comportamentais, convenções de nomenclatura/idioma, regras de git, checklist de revisão,
  skills genéricas (`.claude/skills/`).
- **Estrutura local (`AGENTS.md`, `VESTIBULO.md`, `PLAN.md`, `IMPLEMENT.md`, `PROMPTS.md`):**
  específica deste projeto — sua identidade, seu histórico de decisões, seus objetivos.

## O que está em `core/`

| Arquivo/pasta | Conteúdo |
|---|---|
| `core/GUARDRAILS.md` | Convenções (idioma, datas, nomenclatura) + guardrails comportamentais (verificação temporal, viés de corroboração, atribuição de autoria) + regras de git |
| `core/HARNESS_CHECKLIST.md` | Checklist de revisão periódica do harness — genérico, aplicável a qualquer projeto |
| `.claude/skills/` | Skills reconhecidas pelo Claude Code — já são portáveis por natureza, listadas aqui como parte do que se copia ao bootstrapar |

O `.claude/skills/` fica fora de `core/` porque o Claude Code exige esse caminho exato para
descobrir skills automaticamente — mas é conceitualmente parte da superestrutura, e entra
no ritual de bootstrap abaixo junto com o resto.

## Ritual de bootstrap — iniciando um projeto-irmão

Ao criar um novo projeto que deve herdar o harness:

1. Copiar `core/` (a pasta inteira) para a raiz do novo projeto.
2. Copiar `.claude/skills/` para a raiz do novo projeto.
3. No `AGENTS.md` do novo projeto, adicionar logo no início: "Ler `core/GUARDRAILS.md` antes de qualquer tarefa — guardrails e convenções portáveis, fonte canônica."
4. Registrar no `IMPLEMENT.md` do novo projeto: de qual commit do harness/ o `core/` foi copiado (mesma lógica de âncora usada em `assets/archeology/` — ver `2026-07-02_pre-pivot-harness/README.md`).
5. Construir a estrutura local do novo projeto (`AGENTS.md`, `VESTIBULO.md` ou equivalente, `PLAN.md`, `IMPLEMENT.md`) livremente — isso não é portável, é específico daquele projeto.

O novo projeto não referencia o harness/ em tempo de execução (sem submodule, sem caminho
relativo `../harness/`) — o `core/` é vendorizado (copiado), exatamente como uma instalação
Drupal vendoriza sua própria cópia do core em vez de apontar para o repositório upstream.
Isso mantém cada projeto independente e portátil, ao custo de não haver atualização automática.

## Hábito de promoção — como o core evolui

A garantia de que o `core/` representa sempre "o melhor e mais evolutivo obtido até aquele
instante" não vem de sincronização automática — vem de um hábito:

**Toda lição genuinamente genérica descoberta em qualquer projeto (harness/ ou um irmão)
é promovida para `harness/core/`, não mantida só localmente.**

Uma lição é genérica quando ela não depende do domínio específico do projeto onde foi
descoberta — ex.: "verificar dia da semana computacionalmente" nasceu de um incidente no
harness/, mas vale para qualquer projeto que escreva datas. Uma lição é local quando depende
do domínio — ex.: uma convenção de nomenclatura específica de um glossário de projeto não
sobe para o core.

Quando uma lição é promovida:
1. Adicionar a `harness/core/GUARDRAILS.md` (ou ao arquivo core pertinente), com a origem registrada (igual já era feito).
2. Registrar a promoção no `IMPLEMENT.md` do harness/.
3. Propagação para projetos-irmãos já existentes é manual e ad hoc — não automática. Ao retomar um projeto-irmão, vale conferir se há atualizações no `core/` do harness/ a incorporar.

**Código de aplicação ainda não faz parte deste ritual.** O bootstrap acima (passos
1-2) só cobre `core/` e `.claude/skills/` — documentação e metodologia, não código.
O primeiro código de aplicação do projeto (`mcp-servers/youtube-transcript/`, criado em
2026-07-08) chegou a viver dentro do harness/ por um dia, mas foi extraído para
`youtube-transcript-mcp` (repo próprio, nível de usuário) ainda no mesmo dia — código não
pertence a este meta-projeto, mesmo que tenha nascido dele (ver `IMPLEMENT.md`). Ferramentas
de código que o harness/ ou um projeto-irmão precisar consumir vivem como dependências
externas, referenciadas por link, não vendorizadas junto com `core/`.

## Log de versões do core

- **2026-07-02** — Criação do `core/`. Extraído de `harness/AGENTS.md` (seções Convenções e Git) e `harness/HARNESS_CHECKLIST.md` (movido integralmente). Decisão tomada por analogia ao modelo core/contrib do Drupal, registrada como primeiro turning point da fase pós-pivô (ver `PROMPTS.md`, prt 1, e `IMPLEMENT.md`).

---

*Criado: 2026-07-02*
