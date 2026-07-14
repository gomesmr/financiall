---
title: AGENTS.md
summary: Instruções operacionais para agentes de IA neste repositório — visão geral, estrutura, permissões, gates.
tags: [instrucoes, agente, permissoes]
updated: 2026-07-13
---

# AGENTS.md

> Instruções para agentes de IA trabalhando neste repositório.
> Ler antes de qualquer tarefa, **junto com `core/GUARDRAILS.md`** (guardrails e convenções
> portáveis de agente — fonte canônica, não duplicada aqui) **e `.specify/memory/constitution.md`**
> (princípios de engenharia deste software especificamente — não duplicados aqui). Os dois não se
> sobrepõem: `core/GUARDRAILS.md` rege como o agente se comporta como colaborador (idioma, datas,
> viés de corroboração, git) em qualquer projeto; a constituição rege decisões de arquitetura e
> qualidade específicas do financiALL (idempotência, dados sensíveis, tratamento de erro).

---

## Visão geral do projeto

financiALL é um app pessoal de finanças (importação de nota fiscal, e futuramente extrato
bancário) rodando num Raspberry Pi na rede local. Ver `README.md` para a visão funcional completa
e `.specify/memory/constitution.md` para os princípios de engenharia. Este arquivo não repete
esse conteúdo — só define como o agente deve operar sobre o repositório.

O projeto já usa **Spec-Driven Development** via GitHub Spec Kit (`.specify/`, `specs/`) para o
ciclo de desenvolvimento de features — `/speckit.constitution` → `/speckit.specify` →
`/speckit.plan` → `/speckit.tasks` → `/speckit.implement`. Este `AGENTS.md` e o `core/` vendorizado
do harness/ **não substituem nem interferem nesse fluxo** — cobrem a camada complementar de
identidade/memória/guardrails do agente que o spec-kit não cobre (ver `harness/core/README.md`
para o raciocínio completo dessa fronteira).

`core/` foi vendorizado do projeto `harness/` em 2026-07-13, âncora: commit `d59fb39`.

---

## Estrutura do repositório

```
finall/
├── AGENTS.md              # Este arquivo
├── IMPLEMENT.md            # Log append-only de decisões e desvios do agente
├── README.md               # Visão funcional do projeto (pré-existente)
├── core/                   # Superestrutura portável, vendorizada do harness/
│   ├── README.md
│   ├── GUARDRAILS.md
│   ├── HARNESS_CHECKLIST.md
│   └── PROFILE.md
├── .specify/                # Spec-Driven Development (GitHub Spec Kit) — constitution, templates
├── specs/001-importar-nfce/ # Spec, plano, pesquisa, tarefas da feature 001 (spec-kit)
├── .claude/skills/          # Skills speckit-* (pré-existentes) — não tocadas pelo bootstrap do harness/
├── src/                     # Código da aplicação (api/, models/, services/, storage/, worker/)
├── tests/                   # unit/, integration/, contract/
├── infra/                   # Provisionamento do Raspberry Pi
├── docs/                    # Documentos avulsos (relatórios, análises) — fora do fluxo spec-kit
└── data/                    # Banco de dados e uploads — nunca versionado (.gitignore)
```

---

## Convenções, guardrails e git

`core/GUARDRAILS.md` é a fonte canônica para comportamento do agente — este projeto o segue
integralmente, sem cópia local do conteúdo.

---

## Permissões de escrita

### Permitido sem instrução explícita

- Criar e editar código em `src/`, `tests/`, documentação em `docs/`
- Atualizar `IMPLEMENT.md` com novas entradas de log
- Seguir o fluxo spec-kit normalmente (`/speckit.*`) para novas features

### Restrito — perguntar antes de proceder

- Editar `.specify/memory/constitution.md` diretamente (usar `/speckit.constitution`, que já
  mantém o Sync Impact Report) — nunca editar o arquivo à mão
- Editar arquivos dentro de `specs/*/` fora do fluxo `/speckit.*` correspondente
- Reorganizar a estrutura de pastas raiz
- Alterar `infra/financiall.service` ou scripts de provisionamento sem confirmar o impacto no
  Raspberry Pi já em produção (`w3finall@finall.local`)

### Obrigatório

- **Dados financeiros nunca em texto claro na saída do agente.** CPF, chave de acesso, CNPJ e
  valores monetários de notas reais não aparecem em respostas de chat, commits, logs ou qualquer
  artefato gerado pelo agente — mesma regra do Princípio IV da constituição, estendida
  explicitamente à saída do agente (a constituição fala do código da aplicação; esta linha cobre
  o agente que opera sobre o repositório).
- Nunca ler ou exibir o conteúdo de `data/*.db` ou `data/uploads/` diretamente — são dados reais
  do usuário, não fixtures. Testes usam banco/arquivos de teste isolados, nunca `data/` real.
- Respeitar o `.gitignore` existente (`data/`, `*.db`, `uploads/`, `.claude/settings.local.json`)
  — nunca forçar o versionamento desses caminhos.

### Não permitido

- Enviar dados de `data/` a qualquer serviço externo além do já existente na aplicação (consulta
  SEFAZ) — mesma restrição do Princípio IV da constituição.

---

## Gates de verificação

Antes de considerar qualquer tarefa concluída:

- [ ] Mudanças em `src/`/`tests/` rodam contra `pytest tests/unit tests/integration tests/contract`?
- [ ] Decisões relevantes do agente (fora do escopo já coberto por `specs/*/`) registradas em `IMPLEMENT.md`?
- [ ] Nenhum dado financeiro real apareceu na saída do agente ou em artefato versionado?

Revisão periódica do harness (meta-verificação):

- [ ] No início de cada sessão, ler a última linha do `core/HARNESS_CHECKLIST.md`
  (`*Sessões desde última revisão: N*`), incrementar N e salvar. Se N atingir 5, sugerir ao
  usuário rodar o checklist antes de iniciar tarefa nova.

Antes de qualquer `git commit`: seguir as regras de `core/GUARDRAILS.md` (seção Git).

---

## Escalação

Se surgir uma decisão fora do escopo permitido — especialmente sobre a constituição do projeto,
a estrutura de dados financeiros, ou o serviço em produção no Raspberry Pi — parar e descrever o
bloqueio claramente em vez de assumir.
