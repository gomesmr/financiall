# Quickstart: Upload de extrato/fatura bancária pela web

Guia de validação ponta a ponta. Assume o app rodando localmente
(`python -m src.api.app`) com um `data/financiall.db` de teste (seedado
com `seed_taxonomia_categorizacao` e `seed_regras_natureza`).

## Cenário 1 — Detectar e importar cada um dos 4 formatos reais (US1)

1. Abrir `/importar` e usar o card "Extrato ou fatura bancária" (ou
   `curl -F "arquivo=@<caminho>" http://localhost:5000/extratos/upload`)
   para cada um dos 4 arquivos reais:
   - `assets/novos-extratos/fatura-paga-final 1035-junho2026.xlsx` →
     `formato_detectado` deve ser a fatura Itaú
   - `assets/novos-extratos/Extrato Conta Corrente-220720261133.xls` →
     extrato de conta corrente Itaú
   - `assets/finalcial/Financeiro/extrato/cristine/Extrato conta corrente - 012026.xlsx` →
     extrato BB
   - `assets/novos-extratos/mercado-pago-2026-06.pdf` → fatura Mercado
     Pago
2. Conferir que cada resposta reporta o formato certo e um resumo com
   transações importadas (não erro).
3. Repetir o mesmo upload de novo para qualquer um dos 4 e confirmar que
   a segunda vez reporta só "já existentes" (idempotência, FR-005).

## Cenário 2 — Arquivo não reconhecido é recusado, não adivinhado (US2)

1. Enviar um arquivo de extensão não suportada (ex.: uma imagem `.jpg`)
   → esperar `415` com mensagem clara, nenhuma transação gravada.
2. Enviar um `.xlsx` qualquer sem nenhuma das colunas-assinatura
   conhecidas (ex.: uma planilha vazia ou com colunas genéricas) →
   esperar `415`, nenhuma transação gravada.
3. Enviar um arquivo corrompido com extensão válida (ex.: um `.pdf` que
   não é um PDF de verdade) → esperar `422`, nenhuma transação gravada.

## Cenário 3 — Resultado idêntico ao caminho CLI já validado (US1)

1. Escolher um dos 4 arquivos reais já usado na validação real das
   features 010/011/012.
2. Comparar o resumo retornado pelo upload web com o resumo já registrado
   nas validações anteriores dessas features (mesmas contagens de
   importadas/classificadas/reconciliadas) — evidência de que o upload
   web não introduz nenhuma divergência de resultado frente ao script CLI
   (FR-006).

## Validação com dado real (Princípio V — obrigatória antes de promover)

1. Rodar o Cenário 1 contra os 4 arquivos reais listados acima, sobre uma
   cópia do banco real do Pi (ambiente dev) — não só banco de teste local.
2. Verificação visual real (Princípio VIII) do card novo em `/importar`:
   captura de tela via navegador headless (estado inicial, sucesso e
   erro) + checagem de ausência de erro de console, antes de promover
   para produção.
