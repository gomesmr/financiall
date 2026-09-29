---
title: IMPLEMENT.md
summary: Log append-only de decisões e desvios do agente neste projeto, com raciocínio.
tags: [log, decisoes, append-only]
updated: 2026-07-13
---

# IMPLEMENT.md

> Log append-only de decisões e desvios do agente no projeto `financiALL`.
> Novas entradas no topo. Entradas antigas nunca são editadas ou removidas — apenas
> complementadas por entradas novas quando o contexto muda.
> Cada entrada registra o quê foi decidido e por quê, não apenas o resultado.
>
> **Nota de escopo:** este log é da camada de agente (harness), não do desenvolvimento da
> aplicação em si — decisões de arquitetura/feature já ficam em `specs/*/` via spec-kit. Aqui
> entram decisões sobre como o agente opera neste repositório.

---

### 2026-07-13 — Bootstrap do harness/: regras de acesso, leitura e escrita do agente

**Contexto:** `financiALL` já existia como projeto real (3 commits, feature 001 em produção num
Raspberry Pi) rodando inteiramente sobre Spec-Driven Development (GitHub Spec Kit) — sem nenhuma
camada de identidade/memória/guardrail de agente além dos skills `speckit-*` e do
`.claude/settings.local.json` acumulado por uso. O usuário pediu para adicionar este projeto como
irmão do `harness/` e implementar regras de acesso, leitura e escrita.

**Ação:** ritual de bootstrap de `harness/core/README.md` executado — `core/` vendorizado do
harness/, âncora: commit `d59fb39`. `AGENTS.md` criado com permissões específicas deste projeto,
não genéricas.

**Desvio do ritual, registrado como tal:** o ritual descreve copiar `core/` **e**
`.claude/skills/` do harness/. Não copiado aqui — `.claude/skills/` do harness/ tem
`processar-transcricao` e `registrar-mempalace`, irrelevantes ao domínio deste projeto, e
`financiALL` já tem seu próprio `.claude/skills/` (os 10 skills `speckit-*`, pré-existentes,
instalados pelo Spec Kit). Sobrescrever ou mesclar teria conflito de propósito sem ganho. Esta é
a segunda execução real do ritual (a primeira foi `claude-certified-architect/`, 2026-07-08) e a
primeira a expor esse caso — projeto-irmão que já tem skills próprias antes do bootstrap. Candidato
a nota em `harness/core/README.md`: o passo 2 do ritual deveria dizer "copiar, sem sobrescrever
skills já existentes" em vez de assumir pasta vazia.

**Decisão de desenho do `AGENTS.md`:** em vez de genérico, as permissões foram escritas em cima
da sensibilidade real deste projeto — dados financeiros (`Princípio IV` da constituição:
CPF/chave de acesso/CNPJ/valores nunca em texto claro). A regra da constituição cobre o *código
da aplicação*; o `AGENTS.md` estende a mesma regra explicitamente à *saída do agente* (chat,
commits, logs gerados pelo agente), que é uma superfície que a constituição não cobria. Também
formalizado: `core/GUARDRAILS.md` (comportamento do agente, portável) e
`.specify/memory/constitution.md` (engenharia deste software, local) são camadas complementares,
não duplicadas uma na outra — validação prática da fronteira harness engineering / SDD discutida
no `harness/` em 2026-07-08.

**Não tocado:** `.claude/settings.local.json` (permissões de ferramenta do Claude Code,
acumuladas por uso — SSH ao Raspberry Pi, venv, pytest) — já existia, é gerenciado pelo próprio
Claude Code, não pelo `AGENTS.md`. `.specify/memory/constitution.md` — não editado diretamente,
só referenciado; edição correta é via `/speckit.constitution`.

### 2026-09-29 — Revisão manual de pendências de set/2026 e limpeza de duplicatas em produção

A pedido do usuário, as transações de set/2026 sem natureza foram classificadas direto no banco de
produção via `storage_db.atribuir_natureza_manual` (mesmo caminho da rota da UI, então gera
`log_classificacao_manual` e atualiza o cache por descrição). Parcelas de refinanciamento de
fatura foram classificadas como `pagamento_fatura` (não `gasto`), para não contar duas vezes
compras antigas já contadas como gasto.

Com confirmação explícita do usuário para cada lista, 11 duplicatas foram apagadas por `DELETE`
direto (o app não tem exclusão de transação). Backups em `/tmp/` no Pi antes de cada etapa.

Achados que viram trabalho de código (1 e 2 implementados na branch
`feat/mcl-dedup-e-reconciliacao-pendentes`; 3 fica para um ciclo spec-kit próprio, porque mexe no
modelo de dados):
1. **Dedup falha com data ±1 dia** entre upload de extrato e Open Finance, e com espaçamento
   diferente na descrição de cartão (`DL*99` vs `DL          *99`); também duplicou depósitos da
   Flash entre `flash.txt` e os CSVs.
2. **Reconciliação com nota fiscal só roda no import quando a natureza já é `gasto`.** Transação
   que entra pendente nunca é cruzada com NF, nem depois de classificada manualmente.
3. **Parcela de cartão fica com a data da compra original**, o que infla o mês da compra e
   esvazia os seguintes.

Decisões da correção:
- **Dedup aproximado** (`src/services/duplicata_transacao.py`): mesma conta, valor e tipo, data a
  ±1 dia e descrição compatível (igual sem espaços, ignorando `(estorno)` e o sufixo DD/MM igual à
  própria data; ou uma prefixo da outra quando nenhuma tem sufixo de parcela). Transações gravadas
  na mesma importação nunca são candidatas, e cada transação existente absorve um só registro,
  com o casamento por fingerprint exato reservado antes. Validado em modo leitura contra o banco
  real: a regra reencontra exatamente as 11 duplicatas apagadas à mão, e aponta 0 dos 47 pares
  parecidos restantes (todos parcelas distintas).
- **Saída pendente que reconcilia com NF vira `gasto`** com a categoria da nota.
  `metodo_classificacao_natureza` fica NULL: o CHECK da coluna não tem valor para essa origem, e
  alterar CHECK no SQLite exige reconstruir a tabela em produção. Não faz upsert de cache (a
  evidência é da transação, não da descrição).
- **Classificação manual como gasto** (individual ou em grupo) dispara a reconciliação dos gastos
  sem nota, na camada de rota (a camada de storage não conhece o serviço de reconciliação).

---
*Criado: 2026-07-13*
