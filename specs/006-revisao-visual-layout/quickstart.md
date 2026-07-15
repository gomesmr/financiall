# Quickstart: Validar "Revisão Visual do Layout"

Pré-requisitos: ambiente já configurado como nas features anteriores.

## 1. Rodar os testes automatizados (rede de segurança de regressão)

```bash
pytest tests/unit tests/integration tests/contract -v
```

Nenhum teste novo é esperado especificamente para esta feature (FR-002 —
sem mudança de contrato) — a suíte completa continuar passando 100% é o
próprio critério de "nenhuma funcionalidade quebrou".

## 2. Checklist de regressão manual (uma vez por página)

Para cada página — Importar (`/`), Notas (`/ver/notas`), detalhe de Nota,
Categorias (`/ver/categorias`), Resumo (`/ver/resumo`), status de Envio:

1. A página carrega com o novo visual (menu lateral, cards).
2. Toda ação que já existia antes continua funcionando: importar por
   URL/chave, importar por foto, excluir nota, criar/editar/excluir
   categoria, atribuir categoria, filtrar por mês/titular.
3. Ações destrutivas ainda pedem confirmação antes de executar.

## 3. Responsividade (celular)

Testar cada página numa largura de tela estreita (ferramenta de
dispositivo do navegador, ~360-390px):

1. Nenhuma página exige zoom nem gera rolagem horizontal da página
   inteira.
2. A tabela de notas (muitas colunas) rola horizontalmente dentro dela
   mesma.
3. O formulário de upload de foto é utilizável (botão de escolher
   arquivo/tirar foto acessível e do tamanho adequado ao toque).

## 4. Gráficos (feature 005) dentro do novo layout

1. Abrir `/ver/resumo` — pizza e barras aparecem completos, sem
   sobreposição, com as mesmas cores validadas em
   `specs/005-graficos-resumo/research.md` #2.
2. Alternar entre modo claro/escuro do sistema — nenhum texto ou
   elemento fica ilegível (SC não exige tema escuro completo, só
   ausência de quebra).

## 5. Funciona sem internet

1. Desconectar a máquina/Pi da internet (ou bloquear acesso externo).
2. Recarregar qualquer página — visual e funcionalidade continuam
   completos (assets vendorizados localmente, sem CDN).

## Critério de aceite (liga com Success Criteria da spec)

- SC-001: fluxo de enviar foto pelo celular sem zoom/rolagem horizontal.
- SC-002: suíte completa passando + checklist manual das 6 páginas sem
  nenhuma regressão encontrada.
- SC-003: gráficos do resumo com os mesmos valores/cores de antes.
- SC-004: aplicação funciona por completo sem internet.
