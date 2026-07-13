# Implementation Plan: Importar Notas Fiscais sem Duplicar

**Branch**: `feat/mcl-importar-nfce` | **Date**: 2026-07-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-importar-nfce/spec.md`

## Summary

Um único Raspberry Pi 3 Model B v1.2 (1GB RAM), sempre ligado na rede local,
hospeda todo o sistema financiALL: banco de dados, API HTTP e um worker de
processamento de OCR. O computador do usuário é apenas um cliente sem
estado, que acessa o servidor pela rede quando está ligado. Duas notas
fiscais podem ser importadas: (1) por URL do QR Code ou chave de acesso
colada, com busca best-effort na fonte SEFAZ; (2) por foto ou PDF
escaneado, reconhecido por OCR (Tesseract) de forma assíncrona e sequencial
(fila com um único worker, para não estourar a RAM). Idempotência é
garantida por chave de acesso (canal digital, ou OCR quando consegue
extraí-la) ou por hash de conteúdo do documento (quando a chave não pode
ser identificada). Falha em obter dados completos, em qualquer canal, nunca
impede o registro da nota — ela é gravada com o que houver e marcada
"pendente de revisão". Categorização fica fora de escopo. O provisionamento
do próprio Raspberry Pi (SO, dependências de sistema, deploy do serviço)
faz parte do escopo de tarefas desta feature, via um script de
provisionamento documentado, porque o usuário não tem experiência prévia de
administração Linux/Raspberry Pi.

## Technical Context

**Language/Version**: Python 3.11+ — ambiente de desenvolvimento (Windows,
máquina atual do usuário) e produção real confirmada por acesso SSH
(hostname `finall`, Raspberry Pi OS de 64 bits, base Debian 13 "trixie",
com Python 3.13.5 já instalado de fábrica).

**Primary Dependencies**: `Flask` (API HTTP + páginas HTML simples
renderizadas no servidor) servido em produção por `waitress`; `requests`
(busca best-effort à fonte SEFAZ, canal URL/chave); `pytesseract` + `Pillow`
(OCR e pré-processamento de imagem, canal foto/PDF); `pdf2image` (conversão
de PDF escaneado em imagem, depende do pacote de sistema `poppler-utils`);
stdlib `hashlib` (hash de conteúdo para dedup sem chave), `xml.etree`/
`html.parser` (parsing da resposta SEFAZ); `pytest` para testes.

**Storage**: SQLite — arquivo único no Raspberry Pi (`financiall.db`), sem
servidor de banco separado, alinhado à Restrição de Projeto (pessoa física)
e ao Princípio I (simplicidade). Inclui agora uma tabela de fila
(`envio_ocr`) além de `nota_fiscal`/`item_nota`.

**Testing**: `pytest` — testes de unidade (extração de chave, dígito
verificador, dedup por chave e por hash, cálculo de resumo, extração de
campos a partir de texto de OCR simulado — sem depender do binário real do
Tesseract), testes de integração (rotas HTTP ponta a ponta via cliente de
teste do Flask, contra SQLite temporário) e testes de contrato (formato das
respostas HTTP). Testes que dependem do binário real do Tesseract MUST ser
puláveis quando ele não está disponível no `PATH` do ambiente (ver
research.md #16), já que o desenvolvimento acontece no Windows.

**Target Platform**: desenvolvimento no Windows (ambiente atual — Tesseract
já instalado localmente em `C:\Program Files\Tesseract-OCR`, então os
testes que exercitam OCR real também rodam aqui, além de no Pi); produção
confirmada em um Raspberry Pi 3 Model B v1.2 real, acessível por SSH
(hostname `finall`, Raspberry Pi OS de 64 bits/`aarch64`, base Debian 13
"trixie", `poppler-utils` e `zram` já presentes de fábrica), sempre ligado
na rede local do usuário.

**Project Type**: aplicação web única — backend Flask com páginas HTML
simples renderizadas no servidor (sem frontend separado nem build step de
JavaScript). O computador do usuário é só um cliente HTTP (navegador ou
requisição direta), sem estado próprio e sem código de aplicação instalado
localmente.

**Performance Goals**: sem meta agressiva de throughput — uso pessoal,
dezenas de importações por mês. Confirmação de recebimento de um upload de
foto/PDF em poucos segundos (SC-002), independente do tempo de
processamento do OCR em si (que pode levar dezenas de segundos por nota, e
é aceitável por rodar de forma assíncrona).

**Constraints**: o hardware do servidor é a restrição central do desenho —
1GB de RAM total, CPU ARM quad-core Cortex-A53 (fraca para padrões atuais),
cartão SD de 32GB como único armazenamento. Processamento de OCR MUST ser
sequencial, um envio por vez, sem paralelismo. Recomenda-se `zram` como
rede de segurança contra picos de memória (research.md #13). Nenhuma
dependência que assuma recursos de servidor robusto (sem Docker, sem
broker de fila externo). Sem certificado e-CNPJ (Restrição de Projeto);
nenhum dado sensível (CPF, chave de acesso, CNPJ, valores, texto bruto de
OCR) em log de texto claro (Princípio IV); falha de fonte externa ou de OCR
MUST NOT impedir o registro da nota (Princípio VII); todo texto voltado ao
usuário em português (Princípio VI); o provisionamento do próprio
Raspberry Pi ainda não foi feito pelo usuário e faz parte do escopo desta
feature (não é um pré-requisito assumido como já resolvido).

**Scale/Scope**: uso de uma única pessoa; volume esperado de dezenas a
poucas centenas de notas por mês, pelos dois canais combinados. Sem
necessidade de concorrência multi-usuário.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate (Princípio) | Como esta feature cumpre |
|---|---|
| I. Simplicidade e Manutenibilidade | SQLite em arquivo único (inclusive para a fila — sem broker externo); Flask + `waitress` (sem stack assíncrona desnecessária); worker de OCR como thread do mesmo processo (sem segundo serviço); um único host (Raspberry Pi) para todo o sistema; script único de provisionamento em vez de orquestração (Docker rejeitado). |
| II. Idempotência é Obrigatória | `chave_acesso` `UNIQUE`; `hash_conteudo` com índice único parcial como identificador alternativo quando a chave não é identificável (US3, FR-010/FR-011); *check-before-insert* nos dois canais antes de qualquer gravação. |
| III. Tratamento de Erro Explícito em Entradas Externas | Extração de chave de URL/OCR, parsing de resposta HTTP da SEFAZ, chamada ao binário do Tesseract e leitura de PDF corrompido MUST tratar exceções explicitamente e nunca propagar stack trace ao usuário (FR-004, US1 cenário 3; US2 cenário 4). |
| IV. Dados Financeiros São Sensíveis | Logging MUST mascarar/omitir chave de acesso, CNPJ e valores — agora também o texto bruto reconhecido por OCR (research.md #15); nenhuma chamada de rede além da fonte SEFAZ que já emitiu a nota (FR-018). |
| V. Testável por Construção | Extração/validação de chave, dedup (por chave e por hash), parsing de itens e de campos via texto de OCR simulado têm testes de unidade cobrindo caminho feliz e bordas, sem depender do binário real do Tesseract (research.md #16). |
| VI. Português nos Artefatos | Mensagens de erro e respostas da API (`importar` por URL/chave, upload de foto/PDF, listagem, status, resumo) em português (FR-019). |
| VII. Fontes Frágeis Degradam sem Quebrar o Fluxo | Busca de dados na SEFAZ e reconhecimento de texto por OCR são best-effort; falha em qualquer um grava a nota com o que houver e marca "pendente de revisão" (US4, FR-013), nunca aborta a importação nem descarta um envio (research.md #11 — item preso em "processando" por queda do processo volta a "pendente" na reinicialização do worker). |
| Identidade do Projeto (ALL) | Nota Fiscal grava chave de acesso (ou hash de conteúdo) como identificador estável, em uma única base acessível pela rede local, preparando a futura conciliação com lançamentos de extrato. |

Nenhuma violação identificada. Nenhuma entrada necessária em Complexity
Tracking.

**Re-check pós-Fase 1 (design)**: `data-model.md`, `contracts/api.md` e
`quickstart.md` confirmam os gates acima sem introduzir desvios —
`chave_acesso` é `UNIQUE` e `hash_conteudo` tem índice único parcial no
schema SQLite (Gate II), nenhum campo sensível (incluindo texto de OCR) é
citado como alvo de log (Gate IV), os testes em `tests/unit` cobrem
exatamente extração de chave/dedup por chave e por hash/parsing de campos
de OCR sem exigir o binário do Tesseract (Gate V), e o contrato da API
define mensagens em português para todo caminho de erro (Gate VI) e um
caminho explícito de "dados parciais (pendente de revisão)" e "pendente de
processamento" sem exceção não tratada (Gates III e VII). Nenhuma violação
nova; Complexity Tracking continua vazio.

## Project Structure

### Documentation (this feature)

```text
specs/001-importar-nfce/
├── plan.md              # Este arquivo (/speckit-plan)
├── research.md          # Fase 0 (/speckit-plan)
├── data-model.md         # Fase 1 (/speckit-plan)
├── quickstart.md         # Fase 1 (/speckit-plan)
├── contracts/            # Fase 1 (/speckit-plan)
│   └── api.md
└── tasks.md              # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
src/
├── models/
│   ├── nota_fiscal.py        # Entidade NotaFiscal (dataclass/schema + regras)
│   └── item_nota.py          # Entidade ItemNota
├── services/
│   ├── chave_acesso.py       # Extração da URL/OCR, normalização, validação (dígito verificador)
│   ├── sefaz_client.py       # Busca best-effort dos dados da nota na SEFAZ (canal URL/chave)
│   ├── ocr_client.py         # Reconhecimento de texto via Tesseract (pytesseract) + pré-processamento (Pillow)
│   ├── pdf_extractor.py      # Conversão de PDF escaneado em imagem (pdf2image)
│   ├── campos_ocr.py         # Heurísticas de extração de campos a partir do texto de OCR
│   ├── fila_processamento.py # Enfileirar envio, marcar status, reconciliar após reinício
│   ├── importador.py         # Orquestra os dois canais: validar/decodificar -> checar dedup -> buscar/OCR -> gravar
│   └── resumo.py             # Gasto parcial do mês corrente e histórico de meses anteriores
├── storage/
│   └── db.py                  # Conexão SQLite, schema, repositório (nota_fiscal, item_nota, envio_ocr)
├── worker/
│   └── ocr_worker.py          # Thread em background: consome a fila envio_ocr sequencialmente
└── api/
    ├── app.py                  # Factory Flask, registra rotas, inicia o worker em thread
    ├── routes_importar.py      # POST /notas (URL/chave), POST /notas/upload (foto/PDF)
    ├── routes_consulta.py      # GET /notas, GET /notas/resumo/mes-atual, GET /notas/resumo/historico, GET /envios/<id>
    └── templates/               # Formulário HTML simples de upload (opcional, servido pelo Flask)

infra/
├── setup-raspberry-pi.sh      # Script de provisionamento (dependências de sistema, venv, zram)
└── financiall.service          # Unit systemd (servidor via waitress, restart automático)

tests/
├── unit/
│   ├── test_chave_acesso.py    # Extração de URL + validação de dígito verificador
│   ├── test_importador.py      # Dedup por chave e por hash; degradação best-effort (ambos os canais)
│   ├── test_resumo.py          # Agrupamento por mês pela data de emissão
│   ├── test_campos_ocr.py      # Extração de campos a partir de texto de OCR simulado (sem Tesseract real)
│   └── test_fila_processamento.py  # Transições de status, reconciliação após reinício
├── integration/
│   └── test_api.py             # Rotas HTTP ponta a ponta (cliente de teste do Flask) contra SQLite temporário
└── contract/
    └── test_api_contract.py    # Formato/mensagens das respostas HTTP (contracts/api.md)
```

**Structure Decision**: aplicação web única (Flask) rodando inteiramente no
Raspberry Pi — sem projeto de frontend separado (Opção 2 do template,
"web application" com frontend próprio, foi descartada: não há requisito de
UI rica, e uma segunda base de código/build step de JavaScript violaria o
Princípio I sem necessidade concreta). O diretório `infra/` é novo em
relação ao plano anterior e existe especificamente porque o provisionamento
do Raspberry Pi é parte do escopo desta feature, não um pré-requisito já
resolvido.

## Complexity Tracking

*Sem violações a justificar — tabela omitida intencionalmente.*
