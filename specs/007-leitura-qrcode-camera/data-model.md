# Data Model: Leitura de QR Code pela Câmera

Não se aplica — nenhuma tabela, coluna, model Python ou entidade persistida
nova (spec.md → Key Entities: "Nenhuma"). O conteúdo decodificado do QR Code
é tratado exatamente como o texto que já é colado manualmente hoje no campo
"URL do QR Code ou chave de acesso" — mesmo `entrada` (string), mesma
validação, mesmo destino (`POST /notas`, endpoint já existente e
inalterado).

## Forma de dado efêmera (não persistida)

O único dado novo que passa a existir é o frame de câmera capturado no
navegador — nunca gravado em disco, nunca persistido, existe só durante a
requisição HTTP que o envia ao endpoint de decodificação:

| Campo | Direção | Forma |
|---|---|---|
| Frame de câmera | Cliente → servidor | Imagem JPEG (`image/jpeg`), corpo da requisição, gerada de um `<canvas>` reduzido a ~1200px no lado maior (research.md #3) |
| Resultado da decodificação | Servidor → cliente | `{"entrada": "<texto decodificado>"}` ou `{"entrada": null}` — nunca gravado, o cliente decide na hora se chama `POST /notas` com esse valor |

## Estados

Não se aplica — nenhuma entidade nova, nenhuma transição de estado
persistida. O estado da leitura por câmera (buscando / encontrado / erro /
cancelado) existe só na página, no navegador do usuário, enquanto a leitura
está ativa.
