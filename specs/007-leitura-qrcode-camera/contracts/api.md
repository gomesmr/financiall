# Contrato: API (feature 007)

## Endpoint novo: `POST /notas/qrcode-frame`

Decodifica um frame de câmera enviado pelo cliente e retorna o texto
encontrado (se houver) — não importa a nota, não persiste nada, não
sobrepõe o contrato de `POST /notas` (Seção seguinte, inalterado).

**Request**:
- `Content-Type: image/jpeg`
- Corpo: bytes da imagem JPEG capturada do frame de câmera (ver
  data-model.md — tipicamente reduzida a ~1200px no lado maior antes do
  envio).

**Response — código encontrado**:
```json
200 OK
{"entrada": "https://www.sefaz.sp.gov.br/nfce/qrcode?p=..."}
```

**Response — nenhum código encontrado no frame** (estado normal, não erro):
```json
200 OK
{"entrada": null}
```

**Response — corpo não é uma imagem decodificável**:
```json
415 Unsupported Media Type
{"erro": "Não foi possível processar a imagem enviada."}
```

## Endpoint existente: `POST /notas` — SEM MUDANÇA

Contrato já documentado em `specs/001-importar-nfce/contracts/api.md` e
reafirmado em todas as features seguintes — continua válido sem nenhuma
alteração. O cliente, ao receber uma `entrada` não nula do endpoint novo
acima, chama este endpoint exatamente como já faz hoje ao submeter o
formulário de URL/chave manual: `POST /notas` com corpo
`{"entrada": "<texto decodificado>"}`.

## Contrato visual (não-funcional, mas verificável)

- A página de Importar MUST continuar oferecendo as duas opções de
  importação já existentes (URL/chave em texto; foto/PDF) inalteradas,
  junto com a nova opção de câmera — nenhuma das duas MUST desaparecer ou
  mudar de comportamento (FR-001, FR-002).
- Quando a câmera não está disponível (permissão negada, navegador sem
  suporte, contexto inseguro), a opção de câmera MUST ficar claramente
  indisponível — nunca um botão presente que não faz nada ao ser clicado
  (FR-004).
