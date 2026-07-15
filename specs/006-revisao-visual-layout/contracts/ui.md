# Contrato: Interface (feature 006)

## Nenhum contrato de API HTTP muda

FR-002 exige explicitamente que nenhuma rota, formato de resposta JSON
ou comportamento de endpoint mude nesta feature. Os contratos já
documentados em `specs/001-importar-nfce/contracts/api.md`,
`specs/002-excluir-nota-fiscal/contracts/api.md`,
`specs/003-categorias-crud/contracts/api.md`,
`specs/004-importar-historico-financeiro/contracts/cli.md` e
`specs/005-graficos-resumo/contracts/api.md` continuam válidos sem
alteração.

## Contrato novo: assets estáticos do Argon

Servidos pela mesma rota Flask padrão `/static/<path:filename>` já usada
para `plotly-basic.min.js` (feature 005) — sem rota nova. Caminho
esperado: `/static/argon/css/argon-dashboard.min.css`,
`/static/argon/js/argon-dashboard.min.js`, e demais arquivos de fonte/
imagem sob `/static/argon/`.

## Contrato visual (não-funcional, mas verificável)

- Toda página MUST conter a mesma navegação principal (as 4 seções:
  Importar, Notas, Categorias, Resumo), agora como menu lateral.
  Continua havendo alguma marcação identificável na página ativa
  (equivalente à classe `.ativo` já usada hoje), para os testes de
  contrato existentes que verificam esse comportamento continuarem
  válidos ou serem adaptados sem perder a cobertura.
- Toda ação destrutiva (excluir nota, excluir categoria) MUST continuar
  disparando `confirm()` do navegador (ou padrão equivalente) antes do
  `fetch` — nenhuma mudança visual pode remover essa barreira (FR-006).
