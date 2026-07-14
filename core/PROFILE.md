---
title: core/PROFILE.md
summary: Perfil do usuário — só fatos confirmados explicitamente, nunca inferência do agente.
tags: [core, perfil, usuario]
updated: 2026-07-03
---

# core/PROFILE.md

> Perfil do usuário — portável entre projetos-irmãos, porque quem você é não muda entre projetos.
>
> **Regra dura deste arquivo: só entra fato confirmado explicitamente pelo usuário. Nunca
> inferência do agente.** Se o agente precisar de um dado sobre o usuário que não está aqui,
> pergunta — não presume, não escreve "provavelmente", não generaliza a partir de uma ação
> isolada.

---

## Fatos confirmados

- **Experiência profissional:** trabalha com desenvolvimento de software (confirmado em 2026-07-02; duração exata pendente — ver seção "A confirmar" abaixo).
- Conhecimento de Python e Kotlin.
- Stack técnica adicional, conforme texto do LinkedIn colado em 2026-07-03: Java, Drupal, Docker, AWS.
- Áreas de atuação/interesse declaradas (LinkedIn, 2026-07-03): arquitetura de sistemas e automação de processos; design de APIs resilientes e de alta performance; orquestração de containers; otimização de infraestrutura cloud.
- Traços de atuação declarados (LinkedIn, 2026-07-03): mentoria ativa, comunicação transparente, foco em qualidade de código além da entrega funcional.

## A confirmar (fontes em conflito — não resolver por inferência)

- **Duração da experiência profissional:** o usuário declarou "5 anos" em 2026-07-02 (ver `IMPLEMENT.md`); o texto do LinkedIn colado em 2026-07-03 diz "over a decade of experience in software development". As duas fontes não batem. Não presumir qual está certa — perguntar.
- **Empregador/projeto atual:** o texto do LinkedIn (2026-07-03) descreve "Currently, I work at Zup Innovation... particularly for the Samsung Marketplace at Itaú". O próprio usuário advertiu que o LinkedIn "precisa atualizar". Isso pode já estar desatualizado frente ao contexto mais recente do harness/ (nova squad desde 25/06/2026, registrada no `AGENTS.md` pré-pivô, `assets/archeology/2026-07-02_pre-pivot-harness/`). Não assumir current status sem confirmação.

## Fatos explicitamente não assumidos

- Nível de proficiência em git especificamente — o usuário afirma não dominar "cada interstício", mas isso não equivale a iniciante. Não presumir nível de git a partir de ações isoladas (ex.: pedir `git init`, perguntar sintaxe de um comando específico).

---

*Criado: 2026-07-02*
