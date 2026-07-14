---
title: core/HARNESS_CHECKLIST.md
summary: Checklist de revisão periódica do harness — metodologia portável.
tags: [core, checklist, revisao]
updated: 2026-07-03
---

# Checklist de Revisão do Harness

> Parte do `core/` — metodologia portável, aplicável a qualquer projeto que rode sobre este harness.
>
> Revisão periódica do sistema de gestão — não de tarefas individuais (isso os gates do AGENTS.md já fazem), mas do harness em si: as estruturas que envolvem o agente ainda refletem a realidade?
>
> **Frequência sugerida:** a cada mudança significativa de contexto (novo membro, nova frente, reorganização) ou quando algo escapar por tempo demais sem ser percebido.
>
> Um item falhando não é bloqueio — é sinal de que algo mudou e o harness não acompanhou.
> Um item deliberadamente não aplicável deve ter justificativa escrita.

---

## 1. Instrução ao agente (AGENTS.md)

- [ ] A visão geral do projeto ainda descreve o que o projeto é hoje?
- [ ] A estrutura do repositório reflete o layout real? (rodar `ls` e comparar)
- [ ] As permissões de escrita (permitido / restrito / proibido) ainda são as corretas?
- [ ] O contexto operacional (pessoas, papéis, infraestrutura) está atualizado?
- [ ] Não há instruções ambíguas que o agente poderia interpretar de mais de uma forma?

## 2. Documentos vivos

- [ ] Cada documento classificado como "ativo" no inventário foi tocado nas últimas 2 semanas?
- [ ] Há documentos marcados como "a preencher" que já deveriam estar preenchidos?
- [ ] Há documentos que cresceram a ponto de precisar de refatoração ou divisão?
- [ ] Documentos superados estão marcados como tal (não silenciosamente abandonados)?

## 3. Entrega de contexto

- [ ] O agente consegue iniciar uma sessão e saber onde o projeto está sem explicação oral?
- [ ] O contexto de longa duração (decisões, progresso, pendências) está em arquivos, não na cabeça do usuário?
- [ ] Há informação sensível (credenciais, dados pessoais além do necessário) acessível ao agente?
- [ ] O guardrail de contexto (faixas de consumo) está sendo respeitado?

## 4. Fonte canônica e redundância

- [ ] Para cada tipo de informação relevante, existe uma e apenas uma fonte autoritativa?
- [ ] Não há documentos dizendo a mesma coisa com versões diferentes?
- [ ] Quando uma fonte muda, os documentos que a referenciam são atualizados ou marcados como desatualizados?

## 5. Pendências e itens em aberto

- [ ] As pendências explícitas registradas (IMPLEMENT.md, PLAN.md) foram revisadas?
- [ ] Pendências com mais de 2 semanas sem movimento têm justificativa ou foram fechadas?
- [ ] Milestones do PLAN.md refletem o estado real (não há milestone "em progresso" que na prática parou)?

## 6. Memória e continuidade

- [ ] O mempalace contém o que o agente precisaria para retomar o projeto após semanas de inatividade?
- [ ] Não há drawers no mempalace que contradizem documentos vivos (fonte canônica)?
- [ ] O log de decisões (IMPLEMENT.md) registra as decisões recentes com raciocínio?

## 7. Critério de remoção

> Cada componente do harness existe porque resolve um problema real.
> Se o problema desapareceu, o componente deve ser removido ou marcado como superado.

| Componente | Existe porque | Pode ser removido quando |
|---|---|---|
| Guardrail de contexto (AGENTS.md) | Agente não tem acesso programático ao consumo de tokens | Devin expuser consumo via API ou MCP |
| Verificação computacional de dias/horários | Agente fabrica dias da semana e saudações | Modelo parar de errar fatos temporais verificáveis |
| Skill registrar-mempalace | Agente criou drawers sem envelope (incidente 20/05) | Protocolo estiver internalizado a ponto de não precisar de enforcement |
| Log de consumo de contexto | Não há dados históricos para estimar custo de tarefas | Série temporal tiver dados suficientes para previsão confiável |
| Este checklist | Documentos ficam abandonados sem revisão periódica | Processo de manutenção estar maduro o suficiente para ser orgânico |

---

*Movido para `core/` em 2026-07-02 (harness/), como parte da separação superestrutura/estrutura local (ver `core/README.md`).*
*Vendorizado para `finall/` em 2026-07-13, via ritual de bootstrap (ver `IMPLEMENT.md` deste projeto). Contador e data de revisão reiniciados para o clock deste projeto.*
*Revisado: 2026-07-13*
*Revisor: Marcelo Gomes + agente*
*Sessões desde última revisão: 0*