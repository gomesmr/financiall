# Contrato: Upload de extrato/fatura pela web (feature 013)

## `POST /extratos/upload`

Recebe um arquivo de extrato ou fatura bancária (`multipart/form-data`,
campo `arquivo`), detecta automaticamente o formato (research.md #1) e
importa **de forma síncrona** (sem fila — research.md #4), reaproveitando
o mesmo `parsear()` + `processar_transacoes()` já usados pelos scripts
CLI existentes.

### Requisição

- `multipart/form-data` com campo `arquivo` (obrigatório).
- Extensões aceitas: `.xls`, `.xlsx`, `.pdf`.

### Resposta de sucesso — `200 OK`

```json
{
  "formato_detectado": "mercado_pago_fatura",
  "importadas": 25,
  "ja_existentes": 0,
  "puladas": 0,
  "classificadas_automaticamente": 22,
  "pendentes_natureza": 3,
  "reconciliadas": 0,
  "ambiguas": 0
}
```

### Respostas de erro

| Cenário | HTTP | Corpo |
|---|---|---|
| Nenhum arquivo enviado | `400` | `{"erro": "Nenhum arquivo foi enviado."}` |
| Extensão não suportada, ou conteúdo não bate com nenhuma assinatura conhecida (research.md #3) | `415` | `{"erro": "Não foi possível reconhecer o formato deste arquivo. Formatos aceitos: fatura Itaú, extrato de conta corrente Itaú, extrato BB, fatura Mercado Pago."}` |
| Arquivo do formato certo, mas corrompido/ilegível para o parser correspondente | `422` | `{"erro": "<mensagem específica do parser>"}` |

Nenhum desses cenários grava transação parcial (FR-003/FR-008,
Princípio III) — a exceção do parser (`ArquivoExtratoError`,
`FaturaInvalidaError`, ou a nova `FormatoNaoReconhecidoError`) é
capturada antes de qualquer chamada a `processar_transacoes()`.

### Nunca loga dado sensível (Princípio IV)

A resposta e qualquer log de erro nunca incluem descrição, valor ou conta
de uma transação individual — só o resumo agregado (mesmo padrão dos
scripts CLI).

## Página `/importar`

Card novo "Extrato ou fatura bancária" na página já existente de upload
de nota fiscal (`upload.html`) — formulário de upload de arquivo único que
chama `POST /extratos/upload` e mostra o resumo (ou o erro) inline, mesmo
padrão visual dos cards já existentes na página.
