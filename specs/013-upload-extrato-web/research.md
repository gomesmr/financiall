# Research: Upload de extrato/fatura bancária pela web

Investigação feita inspecionando a estrutura real (cabeçalhos de coluna,
linhas de metadados) dos 4 formatos já suportados, usando arquivos reais
já validados pelas features 010/011/012, antes de desenhar a lógica de
detecção.

## #1 — Assinatura de cada formato (ground truth, arquivos reais)

| Formato | Extensão | Assinatura distintiva | Fonte inspecionada |
|---|---|---|---|
| Itaú fatura de cartão (legado) | `.xls` | Cabeçalho de 4 colunas: `Data, Lançamento, Tipo, Valor` — **sem** coluna de saldo | fixture de teste (`tests/unit/test_importar_extrato_itau_cartao.py`) |
| Itaú extrato de conta corrente | `.xls` | Cabeçalho de 5 colunas com **"saldos"** na última: `data, lançamento, ag./origem, valor (R$), saldos (R$)`, precedido de metadados (`Nome:`, `Agência:`, `Conta:`) | `assets/novos-extratos/Extrato Conta Corrente-220720261133.xls` (linha 8) |
| Itaú fatura de cartão (novo, "Fatura Paga") | `.xlsx` | Texto `"Fatura Paga"` em uma das primeiras linhas + cabeçalho de tabela com coluna **"Titularidade"** | `assets/novos-extratos/fatura-paga-final {1035,2486}-junho2026.xlsx` (linhas 7 e 14) |
| BB extrato de conta corrente | `.xlsx` | Cabeçalho na própria primeira linha (sem metadados antes): `Data, Lançamento, Detalhes, N° documento, Valor, Tipo Lançamento` | `assets/finalcial/Financeiro/extrato/cristine/Extrato conta corrente - 012026.xlsx` (linha 0) |
| Mercado Pago fatura de cartão | `.pdf` | Texto `"Emitida em: DD/MM/AAAA"` (já usado pelo parser, feature 012) | `assets/novos-extratos/mercado-pago-2026-06.pdf` |

**Decision**: a extensão sozinha resolve `.pdf` (só um formato usa essa
extensão), mas `.xls` e `.xlsx` são ambíguos entre 2 formatos cada — a
extensão restringe a dupla candidata, e o conteúdo (presença de uma
coluna/texto-assinatura nas primeiras ~20 linhas da primeira planilha)
desempata.

**Alternatives considered**: usar o nome do arquivo (ex.: "Extrato Conta
Corrente" vs "fatura-paga") — rejeitado por ser o sinal mais frágil
possível (nome é livre, definido pelo usuário/banco ao salvar, sem
garantia nenhuma); a coluna de cabeçalho já está sempre presente por
construção do próprio banco exportador, é o sinal mais estável disponível
sem exigir escolha manual do usuário (FR-002).

## #2 — Onde a detecção vive e como ela se relaciona com os parsers existentes

**Decision**: uma função nova, `detectar_e_parsear(caminho_arquivo) ->
list[dict]`, num módulo novo `src/services/importar_extrato_upload.py`,
que aplica as assinaturas acima (nessa ordem: extensão → conteúdo) e
despacha para o `parsear()` já existente do formato correspondente — sem
duplicar nenhuma lógica de parsing, sem alterar nenhum dos 4 parsers já
existentes.

**Rationale**: os 4 parsers já retornam o mesmo contrato (`list[dict]`
aceito por `processar_transacoes`) — a única peça que falta é decidir
*qual* `parsear()` chamar. Isolar essa decisão numa função fina, dedicada,
mantém os parsers existentes (e os scripts CLI que os usam) intocados
(FR-007), e a função de detecção fica testável isoladamente contra
excertos sintéticos de cada assinatura.

## #3 — O que fazer quando a detecção é ambígua ou não reconhece nada

**Decision**: se a extensão não for `.xls`/`.xlsx`/`.pdf`, ou se for uma
dessas mas nenhuma assinatura de conteúdo bater nas primeiras ~20 linhas
da primeira planilha (ou nenhum "Emitida em" no PDF), a função levanta
`FormatoNaoReconhecidoError` — a rota HTTP traduz isso em HTTP 415 com
mensagem clara, sem gravar nada (FR-003/FR-008, Princípio III).

**Rationale**: um "melhor palpite" (ex.: cair no primeiro formato daquela
extensão por padrão) arriscaria interpretar um arquivo com o parser
errado e gravar dado incorreto silenciosamente — pior do que recusar
(mesmo racional do Princípio VII: degradar sem quebrar não significa
adivinhar, significa recusar com segurança quando o sinal não é
confiável).

## #4 — Import síncrono, não fila

**Decision**: a rota de upload processa e responde de forma síncrona
(parse + `processar_transacoes()` na mesma requisição), diferente do
upload de nota fiscal (`POST /notas/upload`, fila assíncrona + polling
por `envio_id`).

**Rationale**: nota fiscal usa fila porque o caminho de foto/PDF passa por
OCR (`pytesseract`/`pdf2image`), que é lento e pode falhar de formas que
pedem retry. Nenhum dos 4 parsers de extrato/fatura usa OCR — todos leem
célula de planilha ou texto nativo de PDF (`pdfplumber`), operação da
ordem de dezenas de milissegundos mesmo para uma fatura inteira (medido
na validação real da feature 012: a fatura de 6 páginas processa em bem
menos de 1 segundo). Fila e polling seriam complexidade sem necessidade
concreta (Princípio I).

## #5 — Onde a UI vive

**Decision**: adicionar um card novo ("Extrato ou fatura bancária") na
mesma página `/importar` (`upload.html`) já usada para nota fiscal, em vez
de criar uma página nova.

**Rationale**: `/importar` já é o hub de "trazer dado novo pro
financiALL" (câmera, URL/chave, upload de nota) — adicionar mais um card
segue o padrão visual já estabelecido (grid de cards) sem exigir item de
navegação novo nem uma segunda página pra manter.

## #6 — Reconciliação e classificação

**Decision**: nenhuma mudança — a rota chama exatamente
`processar_transacoes()` (mesmo usado pelos 4 scripts CLI e pela migração
histórica), então classificação de natureza e reconciliação com nota
fiscal já vêm de graça, idênticas independente do caminho de entrada
(FR-006).
