# Contrato: API HTTP — Excluir Nota Fiscal (feature 002)

Adiciona um endpoint ao contrato existente em
`specs/001-importar-nfce/contracts/api.md`. Mesmas convenções: JSON,
mensagens em português (Princípio VI), erro de entrada usa `4xx`, sucesso
usa `2xx`.

## `DELETE /notas/<id>`

Exclui uma nota fiscal, seus itens, o(s) envio(s) que a originaram e o(s)
arquivo(s) físicos associados (FR-003, FR-005). Ação destrutiva e
definitiva — a confirmação acontece na UI antes da chamada (FR-002), este
endpoint não pede confirmação adicional.

**Parâmetro de rota**: `id` — id numérico da nota (`nota_fiscal.id`).

**Respostas possíveis**:

| Cenário | Status HTTP | Corpo |
|---|---|---|
| Nota excluída com sucesso | `200` | `{"mensagem": "Nota excluída com sucesso."}` |
| Nota não existe (id inválido ou já excluída) | `404` | `{"erro": "Nota não encontrada."}` |

**Nunca**: excluir parcialmente (nota sem itens, ou itens sem nota) —
FR-003 exige que a exclusão de `nota_fiscal`/`item_nota`/`envio_ocr` seja
atômica; exceção não tratada retornando `500` sem corpo explicativo em
português (Princípio III).

## `GET /envios/<envio_id>` — comportamento alterado

Mesma rota já existente (`specs/001-importar-nfce/contracts/api.md`), com
um cenário novo: quando o envio referenciava uma nota que foi excluída por
este novo endpoint, o próprio registro de envio também foi excluído (ver
data-model.md) — portanto o cenário já documentado "Envio não existe →
`404` `{"erro": "Envio não encontrado."}`" agora também cobre esse caso,
sem necessidade de um código de erro novo.

## Reimportação após exclusão (sem endpoint novo)

`POST /notas` e `POST /notas/upload` (contrato inalterado, ver feature
001) voltam a se comportar como se a chave/hash nunca tivesse sido
importada, uma vez que a linha correspondente em `nota_fiscal` não existe
mais (US2/FR-004) — nenhuma mudança de contrato nesses dois endpoints, só
a garantia de que o cenário "chave já registrada" não se aplica mais a uma
nota excluída.
