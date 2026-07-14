# Contrato: API HTTP do financiALL (feature 001)

Servida pelo Raspberry Pi na rede local. Todas as mensagens ao usuário são
em português (Princípio VI). Respostas são JSON, exceto o formulário de
upload servido em HTML simples (opcional, mesma finalidade da rota de
upload). Toda resposta de erro de entrada usa um código de status HTTP
`4xx`; sucesso usa `2xx`, mesmo quando o resultado é "dados parciais" ou
"nota já registrada" (não são erros).

## `POST /notas`

Importa uma nota fiscal a partir de uma URL de QR Code ou de uma chave de
acesso, enviada no corpo da requisição.

**Corpo** (JSON): `{"entrada": "<url ou chave>"}` — string obrigatória,
mesma tolerância de formato do fluxo anterior (URL http(s) com a chave de
44 dígitos em algum parâmetro de consulta, ou uma chave de 44 dígitos com
ou sem espaços/caracteres não numéricos).

**Respostas possíveis**:

| Cenário | Status HTTP | Corpo (campos relevantes) |
|---|---|---|
| Entrada não contém uma chave de 44 dígitos extraível/válida | `422` | `{"erro": "Não foi possível identificar uma chave de acesso válida de 44 dígitos em \"<entrada>\"."}` |
| Chave com dígito verificador inválido | `422` | `{"erro": "A chave de acesso informada tem dígito verificador inválido."}` |
| Chave já registrada | `200` | `{"status": "ja_registrada", "mensagem": "Nota já registrada em <data_importacao>.", "nota": {...dados do registro existente, chave mascarada...}}` — nenhuma gravação nova ocorre |
| Chave nova, fonte SEFAZ respondeu com sucesso | `201` | `{"status": "completa", "mensagem": "Nota importada com sucesso.", "nota": {...emitente, data, total, itens...}}` |
| Chave nova, fonte SEFAZ falhou (parcial ou totalmente) | `201` | `{"status": "pendente_revisao", "mensagem": "Nota importada com dados parciais (pendente de revisão).", "nota": {...uf, cnpj, ano-mês, o que houver...}}` |

**Nunca**: exceção não tratada retornando `500` sem corpo explicativo em
português; qualquer erro externo (SEFAZ) vira uma das respostas acima
(Princípio III).

## `POST /notas/upload`

Envia uma foto ou PDF de um cupom fiscal para processamento assíncrono por
OCR.

**Corpo**: `multipart/form-data` com um campo de arquivo (`imagem/*` ou
`application/pdf`).

**Resposta** (sempre imediata, antes do processamento terminar — FR-006):

| Cenário | Status HTTP | Corpo |
|---|---|---|
| Arquivo aceito (imagem ou PDF válido) | `202` | `{"envio_id": <id>, "status": "pendente", "mensagem": "Arquivo recebido. Consulte o status em /envios/<envio_id>."}` |
| Arquivo não é imagem nem PDF | `415` | `{"erro": "Tipo de arquivo não suportado. Envie uma foto ou um PDF."}` |
| Nenhum arquivo enviado | `400` | `{"erro": "Nenhum arquivo foi enviado."}` |

**Nunca**: aguardar o processamento de OCR terminar antes de responder
(FR-006); perder ou sobrescrever um envio anterior ainda não processado
(FR-007).

## `GET /envios/<envio_id>`

Consulta o status de processamento de um envio de foto/PDF.

**Respostas possíveis**:

| Cenário | Status HTTP | Corpo |
|---|---|---|
| Envio não existe | `404` | `{"erro": "Envio não encontrado."}` |
| Ainda pendente ou em processamento | `200` | `{"status": "pendente"}` ou `{"status": "processando"}` |
| Concluído, nota completa | `200` | `{"status": "concluido", "nota_status": "completa", "nota": {...}}` |
| Concluído, dados incompletos | `200` | `{"status": "concluido", "nota_status": "pendente_revisao", "mensagem": "Processamento concluído com dados incompletos.", "nota": {...o que houver...}}` |

## `GET /notas`

Lista as notas importadas, com filtro opcional por mês.

**Query string**: `?mes=AAAA-MM` (opcional).

**Resposta** (`200`): `{"notas": [{...data_emissao, emitente_nome,
valor_total, status, canal_origem...}, ...]}`, ordenada por
`data_emissao`/`ano_mes_emissao` desc. Lista vazia (`{"notas": []}`) quando
não há notas — nunca um erro.

## `GET /notas/resumo/mes-atual`

Retorna o gasto parcial do mês corrente.

**Resposta** (`200`): `{"mes": "AAAA-MM", "total_gasto": <centavos>,
"quantidade_notas": <n>, "parcial": true, "mensagem": "Total parcial —
reflete apenas notas fiscais importadas."}`. Quando não há notas no mês
corrente: `{"mes": "AAAA-MM", "total_gasto": null, "quantidade_notas": 0,
"parcial": true, "mensagem": "Nenhuma nota importada no mês corrente."}`.

## `GET /notas/resumo/historico`

Retorna o total gasto por mês para meses anteriores ao corrente.

**Resposta** (`200`): `{"meses": [{"mes": "AAAA-MM", "total_gasto":
<centavos>, "quantidade_notas": <n>}, ...], "parcial": true}`, um item por
mês anterior com ao menos uma nota, ordenado do mais recente para o mais
antigo. Lista vazia quando não há notas em meses anteriores.
