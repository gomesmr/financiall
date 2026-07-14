# Quickstart: Validar a Feature 001 (Importar Notas Fiscais sem Duplicar)

## Pré-requisitos

- Raspberry Pi 3 Model B v1.2 provisionado com `infra/setup-raspberry-pi.sh`
  (dependências de sistema instaladas, `zram` ativo) e o serviço
  `financiall.service` rodando (`systemctl status financiall`).
- Um dispositivo cliente (computador ou celular) na mesma rede local,
  apontando para o endereço do Raspberry Pi (ex.: `http://raspberrypi.local:5000`
  ou o IP local configurado).
- Uma URL de QR Code de nota fiscal real (ou uma chave de 44 dígitos
  válida) para o teste do caminho feliz do canal digital, e uma chave
  inválida (comprimento errado ou dígito verificador errado) para o teste
  de rejeição.
- Uma foto legível de um cupom fiscal em papel para o teste do canal de
  OCR.
- No ambiente de desenvolvimento (Windows), o Tesseract não precisa estar
  instalado para rodar a suíte automatizada — apenas para validar
  manualmente o Cenário 4 contra o servidor real no Raspberry Pi.

## Cenário 1 — Importar nota nova via URL (US1)

```bash
curl -X POST http://<raspberrypi>:5000/notas \
  -H "Content-Type: application/json" \
  -d '{"entrada": "https://www.sefaz.<uf>.gov.br/.../?p=<44-digitos>|2|1|..."}'
```

**Esperado**: status `201`, corpo com `"status": "completa"` (ou
`"pendente_revisao"` se a fonte SEFAZ estiver fora do ar). Confirma FR-001,
FR-002, FR-012, contrato `POST /notas` em [contracts/api.md](./contracts/api.md).

## Cenário 2 — Importar a mesma nota via chave colada (US1 + US3)

```bash
curl -X POST http://<raspberrypi>:5000/notas \
  -H "Content-Type: application/json" \
  -d '{"entrada": "  <44-digitos-com-espacos>  "}'
```

**Esperado**: se a chave já foi importada no Cenário 1, a resposta MUST ter
`"status": "ja_registrada"` (status HTTP `200`), e `GET /notas` MUST
continuar mostrando exatamente uma nota com essa chave — nunca duas.
Confirma FR-003, FR-010, FR-011 (idempotência, Princípio II).

## Cenário 3 — Rejeitar entrada inválida (US1 cenário 3)

```bash
curl -X POST http://<raspberrypi>:5000/notas \
  -H "Content-Type: application/json" \
  -d '{"entrada": "12345"}'
```

**Esperado**: status `422`, corpo `{"erro": "Não foi possível identificar
uma chave de acesso válida de 44 dígitos em \"12345\"."}`, nenhuma linha
nova em `GET /notas`. Confirma FR-004.

## Cenário 4 — Importar nota via foto de cupom fiscal (US2 + US5)

```bash
curl -X POST http://<raspberrypi>:5000/notas/upload \
  -F "arquivo=@caminho/para/foto-do-cupom.jpg"
```

**Esperado**: resposta imediata (poucos segundos, sem esperar o OCR),
status `202`, corpo com `envio_id`. Em seguida:

```bash
curl http://<raspberrypi>:5000/envios/<envio_id>
```

**Esperado**: logo após o envio, `"status": "pendente"` ou `"processando"`;
após o processamento terminar (segundos a poucas dezenas de segundos),
`"status": "concluido"` com `"nota_status": "completa"` (se o OCR
reconheceu os campos principais) ou `"pendente_revisao"` (se não). Confirma
FR-005, FR-006, FR-008, FR-009, e o comando não deve travar nem retornar
erro mesmo quando a foto é de baixa qualidade — Princípio VII.

## Cenário 5 — Listar notas importadas (US6)

```bash
curl http://<raspberrypi>:5000/notas
curl "http://<raspberrypi>:5000/notas?mes=2026-06"
```

**Esperado**: uma entrada por nota, com data de emissão, emitente, total,
status e canal de origem; com a base vazia, `{"notas": []}`. Confirma
FR-014.

## Cenário 6 — Ver gasto parcial do mês corrente e histórico (US7 + US8)

```bash
curl http://<raspberrypi>:5000/notas/resumo/mes-atual
curl http://<raspberrypi>:5000/notas/resumo/historico
```

**Esperado**: `mes-atual` retorna o total do mês corrente identificado
como parcial; `historico` retorna uma entrada por mês anterior com ao
menos uma nota. Com a base vazia, ambos indicam que não há dados
suficientes, sem erro. Confirma FR-015, FR-016, SC-005.

## Cenário 7 — Degradação graciosa quando a fonte externa ou o OCR falham (US4)

Repetir o Cenário 1 com uma chave válida cuja consulta à SEFAZ retorna
erro/timeout (ex.: desconectar a rede do Pi momentaneamente para a
tentativa), e repetir o Cenário 4 com uma foto ilegível (borrada ou
recortada).

**Esperado**: em ambos os casos, a nota é gravada mesmo assim (com o que
for decodificável da chave, no canal digital; ou apenas com
`hash_conteudo`, no canal de foto), com status `pendente_revisao`, e
nenhuma das duas chamadas retorna erro `5xx` nem trava o servidor. Confirma
FR-013, Princípio VII.

## Cenário 8 — Envios simultâneos não se perdem (US2 cenário 3, FR-007)

Enviar duas fotos diferentes em sequência rápida (sem esperar a primeira
terminar de processar) e consultar `GET /envios/<id>` de cada uma até
ambas chegarem a `concluido`.

**Esperado**: as duas são processadas em ordem, nenhuma é perdida ou
sobrescrita pela outra. Confirma FR-007, SC-007.

## Verificação final

Rodar a suíte automatizada (roda no Windows, sem precisar do Tesseract
instalado — testes que dependem dele são pulados automaticamente quando o
binário não está no `PATH`, ver research.md #16):

```bash
pytest tests/unit tests/integration tests/contract
```

Todos os testes MUST passar antes de considerar a feature pronta para
revisão (Princípio V). Os cenários 1–8 acima (que dependem do servidor
real rodando no Raspberry Pi) são a verificação manual complementar de
ponta a ponta, incluindo o comportamento real do Tesseract.
