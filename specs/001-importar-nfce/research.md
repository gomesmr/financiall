# Research: Importar Notas Fiscais sem Duplicar (arquitetura servidor único no Raspberry Pi)

## 1. Linguagem e stack

**Decision**: Python 3.11+, tanto no ambiente de desenvolvimento (Windows,
máquina atual do usuário) quanto em produção (Raspberry Pi OS Bookworm, que
já traz Python 3.11 no repositório padrão).

**Rationale**: mantém a mesma linguagem/versão nos dois ambientes, evitando
divergência de comportamento entre "roda no Windows" e "roda no Pi";
Raspberry Pi OS Bookworm (base Debian 12) tem Python 3.11 diretamente no
`apt`, sem precisar compilar do fonte.

**Alternatives considered**: Node.js/TypeScript (rejeitado — mesmas razões
do research original: stdlib/ecosistema Python é mais direto para
HTTP+HTML/XML+OCR, e não há motivo para dois runtimes num projeto de uma
pessoa).

## 2. Framework HTTP do servidor

**Decision**: Flask, servido em produção por `waitress` (servidor WSGI puro
Python, sem dependência de compilação, single processo com um pequeno
número de threads).

**Rationale**: o Raspberry Pi 3B tem 1GB de RAM total, compartilhado entre
SO, banco, worker de OCR e servidor HTTP. Flask é mais leve em repouso que
FastAPI (que traz Starlette + Pydantic + uma stack ASGI), e não há
necessidade de concorrência assíncrona real neste projeto — as operações
potencialmente lentas (OCR, consulta à SEFAZ) já são tratadas fora do ciclo
de requisição (fila assíncrona) ou com timeout curto. `waitress` é
suficiente como servidor de produção (evita usar o servidor de
desenvolvimento do Flask) sem exigir dependências de sistema adicionais
(diferente de `gunicorn`, que em algumas configurações depende de
compilação nativa).

**Alternatives considered**: FastAPI + `uvicorn` (rejeitado — footprint de
memória maior e modelo de concorrência assíncrona desnecessário para o
volume de uso pessoal e para uma fila já sequencial por design);
`gunicorn` (rejeitado como servidor de produção em favor de `waitress` —
puro Python, mais simples de instalar em ARM sem toolchain de compilação).

## 3. Extração da chave de acesso a partir da URL do QR Code

**Decision** (mantida do research original, sem mudança pela nova
arquitetura): não assumir nome fixo de parâmetro nem domínio fixo; fazer
parse da query string e procurar, em cada valor, uma sequência de 44
dígitos consecutivos que passe na validação do dígito verificador.

**Rationale**: o padrão nacional de QR Code de NFC-e varia por UF, mas
sempre inclui a chave de 44 dígitos como prefixo de um dos valores de
query — resiliente a variação entre UFs sem tabela de mapeamento por
estado (Princípio I).

## 4. Validação do dígito verificador da chave de acesso

**Decision** (mantida): algoritmo módulo 11 padrão do modelo nacional de
NF-e/NFC-e sobre os 43 primeiros dígitos, pesos cíclicos 2–9 da direita
para a esquerda.

**Rationale**: algoritmo público e estável, permite validar sem depender de
rede — inclusive quando a chave vem de OCR, onde erros de leitura de um
dígito são comuns e o dígito verificador detecta isso imediatamente.

## 5. Dados extraíveis da própria chave, sem depender de fonte frágil

**Decision** (mantida): decodificar UF, ano/mês de emissão, CNPJ do
emitente, modelo, série e número da nota diretamente dos 44 dígitos,
independentemente do canal de entrada (URL/chave ou OCR).

**Rationale**: reduz a superfície do que é best-effort — válido tanto para
o canal digital (fonte SEFAZ indisponível) quanto para o canal de OCR
(reconhecimento de texto malsucedido): se ao menos a chave de 44 dígitos for
identificada corretamente (por extração de URL, entrada colada, ou OCR), UF/
CNPJ/ano-mês/modelo ficam garantidos sem custo de rede nem depender do OCR
para o restante do texto.

## 6. Chamada à fonte de detalhamento externa (canal URL/chave)

**Decision** (mantida): uma única tentativa HTTP com timeout curto, apenas
quando `modelo = 65` (NFC-e); qualquer falha é capturada explicitamente e
resulta em "pendente de revisão".

**Rationale**: Princípios III e VII — fontes frágeis não podem quebrar o
fluxo principal; retries/backoff são complexidade desnecessária para uso
pessoal.

## 7. Motor de OCR (canal foto/PDF)

**Decision**: Tesseract OCR (binário `tesseract-ocr` do sistema, com pacote
de idioma `tesseract-ocr-por`), acessado via `pytesseract`, com
pré-processamento de imagem básico via `Pillow` (conversão para escala de
cinza e binarização simples antes de enviar ao Tesseract, para melhorar a
taxa de reconhecimento sem custo de memória relevante).

**Rationale**: Tesseract é um motor de OCR clássico (não baseado em rede
neural pesada), com uso de memória e CPU compatível com os recursos do
Raspberry Pi 3B (1GB RAM, CPU ARM Cortex-A53). Roda como processo externo
(`pytesseract` invoca o binário via subprocess), o que também significa que,
enquanto o Tesseract processa uma imagem, a thread Python que aguarda libera
o GIL — o servidor HTTP continua respondendo a outras requisições mesmo
durante o processamento.

**Alternatives considered**: motores de OCR baseados em deep learning
(EasyOCR, PaddleOCR, modelos baseados em transformers) — rejeitados: exigem
muito mais RAM e CPU do que o Pi 3B oferece com folga, risco real de OOM ou
processamento inviavelmente lento para uso prático.

## 8. Extração de texto/imagem de PDF escaneado

**Decision**: `pdf2image` (wrapper Python sobre `pdftoppm`, do pacote de
sistema `poppler-utils`) para converter cada página do PDF em imagem antes
de passar pelo mesmo pipeline de OCR usado para fotos.

**Rationale**: `poppler-utils` é um pacote `apt` padrão e estável no
Raspberry Pi OS, bem documentado em conjunto com Tesseract; reaproveita o
mesmo caminho de código de extração de campos usado para fotos (uma vez
convertido em imagem, o PDF segue o pipeline idêntico).

**Alternatives considered**: `PyMuPDF` (`fitz`) — embute o motor MuPDF na
própria wheel Python, sem dependência de pacote de sistema separado;
avaliado como alternativa válida e mais simples de instalar, mas
`pdf2image` + `poppler-utils` foi preferido pela documentação/precedente
mais amplo em pipelines de OCR e por já ser o padrão de fato nesse tipo de
integração — trade-off aceito (mais uma dependência de sistema no script de
provisionamento do Pi, ver item 14).

## 9. Extração de campos a partir do texto reconhecido por OCR

**Decision**: aplicar sobre o texto bruto retornado pelo Tesseract as
mesmas heurísticas leves de busca de padrão já usadas para URLs (item 3):
procurar sequência de 44 dígitos válida pelo dígito verificador (chave de
acesso), padrão de CNPJ formatado, padrões textuais comuns de rótulo de
total ("TOTAL", "VALOR TOTAL R$") seguidos de valor monetário, e uma data no
formato `dd/mm/aaaa`. Itens individuais (descrição/quantidade/valor por
linha) são tentados com heurísticas simples de linha tabular, mas o sistema
aceita e grava a nota mesmo que a extração de itens falhe — a chave, o
emitente e o total têm prioridade sobre os itens no canal de OCR.

**Rationale**: texto de OCR de cupom fiscal impresso é inerentemente ruidoso
(fonte pequena, papel térmico desbotado, fotos em ângulo); heurísticas de
regex sobre padrões estáveis (formato de CNPJ, formato de data, rótulo de
total) são mais robustas do que tentar parsear a estrutura completa do
cupom. Itens são o campo mais frágil de extrair corretamente via OCR de
texto corrido — por isso o sistema já assume, por design, que "pendente de
revisão" será o resultado comum para notas do canal de foto/PDF, o que está
alinhado ao Princípio VII.

**Alternatives considered**: usar apenas o texto para localizar a chave de
acesso e nunca tentar os demais campos via OCR (rejeitado — descartaria
dados que frequentemente são recuperáveis com heurísticas simples, como o
valor total, que costuma aparecer em padrão consistente nos cupons).

## 10. Fila de processamento assíncrono

**Decision**: uma tabela própria no mesmo arquivo SQLite (`envio_ocr`, ver
data-model.md) com status `pendente` / `processando` / `concluido` /
`falhou`; um único worker, rodando como thread em background dentro do
mesmo processo do servidor Flask, consulta a tabela em loop (poll a cada
poucos segundos) e processa um envio de cada vez, em ordem de chegada.

**Rationale**: evita introduzir um broker de fila externo (Redis,
RabbitMQ, Celery) — complexidade desproporcional ao volume de uso pessoal e
peso de memória adicional que o hardware não comporta (Princípio I). Rodar
o worker como thread do mesmo processo (em vez de um processo separado)
evita duplicar o footprint de memória de um segundo interpretador Python; a
liberação do GIL durante a chamada ao binário do Tesseract (item 7) torna
essa escolha segura para não travar o atendimento HTTP.

**Alternatives considered**: fila com Celery + Redis (rejeitado —
complexidade e memória incompatíveis com 1GB de RAM); worker como processo
systemd separado do servidor HTTP (avaliado como alternativa válida e mais
isolada — rejeitado apenas pela simplicidade de operar um único processo/
serviço em vez de dois, dado o Princípio I; pode ser revisitado se o
processo único mostrar problemas de estabilidade em produção).

## 11. Recuperação da fila após reinício do processo

**Decision**: ao iniciar, o worker MUST reverter para `pendente` qualquer
envio que esteja com status `processando` (indica que o processo foi
interrompido no meio do processamento anterior), antes de retomar o
consumo normal da fila.

**Rationale**: sem essa reconciliação, uma queda de energia ou reinício do
serviço no meio do processamento de um envio deixaria esse envio preso
permanentemente em `processando`, nunca mais sendo tentado — o que violaria
o Princípio VII (degradar sem quebrar o fluxo) na sua forma mais básica:
perder silenciosamente um envio do usuário.

## 12. Deduplicação por hash de conteúdo (canal foto/PDF sem chave extraível)

**Decision**: SHA-256 (`hashlib`, biblioteca padrão) sobre os bytes brutos
do arquivo enviado (foto ou PDF), armazenado em `hash_conteudo`; índice
único parcial no SQLite (`CREATE UNIQUE INDEX ... WHERE hash_conteudo IS
NOT NULL`), permitindo múltiplas notas com esse campo nulo (quando a chave
já foi identificada) sem violar unicidade.

**Rationale**: já previsto na constituição do projeto (Princípio II — "na
ausência de chave de acesso, usa-se hash de conteúdo do documento"); SHA-256
da biblioteca padrão não exige dependência nova e é barato de calcular
mesmo no hardware do Pi.

**Alternatives considered**: hash perceptual de imagem (rejeitado —
resolveria o caso de duas fotos ligeiramente diferentes do mesmo cupom, mas
adiciona complexidade e uma dependência extra; o spec.md já documenta essa
limitação como aceita nesta feature).

## 13. Proteção de memória (swap/zram)

**Decision**: recomendar `zram` (swap comprimido em RAM, via
`systemd-zram-generator` ou `zram-tools` do `apt`) como rede de segurança
contra picos de memória durante o processamento de OCR, em vez de um
arquivo de swap tradicional no cartão SD.

**Rationale**: zram comprime a memória em vez de gravar em disco, então é
mais rápido e não desgasta o cartão SD com escritas repetidas de swap —
importante porque o cartão SD é o único armazenamento do sistema (Princípio
I aplicado à operação, não só ao código).

**Alternatives considered**: swapfile tradicional em `/swapfile` no cartão
SD (rejeitado como escolha primária pelo desgaste de escrita no SD, mas
documentado como alternativa mais simples caso zram não esteja disponível
na imagem do SO escolhida).

**Confirmado em campo (2026-07-13)**: a imagem padrão gravada pelo usuário
(Raspberry Pi OS de 64 bits, base Debian 13 "trixie", gerada por `pi-gen`)
já vem com `zram` ativo de fábrica via `systemd-zram-generator`
(`systemd-zram-setup@zram0.service`), sem precisar instalar nada — o script
de provisionamento (item 14) só verifica e não tenta reinstalar.

## 14. Provisionamento e deploy do Raspberry Pi

**Decision**: um script de provisionamento (`infra/setup-raspberry-pi.sh`),
**idempotente** (seguro rodar mais de uma vez, verificando o que já está
presente antes de instalar), que garante as dependências de sistema
(`python3`, `python3-venv`, `tesseract-ocr`, `tesseract-ocr-por`,
`poppler-utils`, zram), cria o ambiente virtual Python e instala as
dependências do projeto, e uma unit `systemd`
(`infra/financiall.service`) que roda o servidor via `waitress` como
serviço do sistema, com `Restart=on-failure` e início automático no boot.

**Confirmado em campo (2026-07-13)**: acesso SSH por chave à máquina real
(hostname `finall`, usuário `w3finall`, `sudo` sem senha) confirmou:
Raspberry Pi OS 64 bits (`aarch64`) base Debian 13 "trixie", `Python
3.13.5` e `pip3` já instalados, `poppler-utils` e `zram` já presentes,
`python3-venv` (módulo `venv`) funcional, cartão de 29GB com 22GB livres.
Falta apenas `tesseract-ocr` e `tesseract-ocr-por`. O script foi ajustado
para checar cada dependência antes de instalar, em vez de assumir uma
imagem totalmente vazia — evita reinstalar o que a imagem padrão já
resolve, mantendo o Princípio I (não fazer trabalho desnecessário).

**Rationale**: o usuário não tem experiência prévia de administração
Linux/Raspberry Pi; um script único e documentado (em vez de uma lista de
passos manuais) reduz a chance de erro e permite reexecução caso algo saia
errado, além de servir como documentação viva do que o servidor precisa
para rodar. `systemd` é o gerenciador de serviços padrão do Raspberry Pi
OS, não exige dependência adicional.

**Alternatives considered**: Docker (rejeitado — camada de abstração extra
com custo de memória que o hardware de 1GB não deveria pagar sem
necessidade real; a constituição já rejeita complexidade especulativa,
Princípio I).

## 15. Log seguro

**Decision** (mantida e estendida): logging da aplicação nunca inclui
chave de acesso, CNPJ, CPF, valores monetários, nem o texto bruto extraído
por OCR (que pode conter os mesmos dados sensíveis) em texto claro; usa-se
`id` interno ou últimos 4 dígitos da chave para correlacionar registros em
log.

**Rationale**: Princípio IV, agora explicitamente estendido ao conteúdo
reconhecido por OCR, que é uma nova superfície de dado sensível introduzida
por esta arquitetura.

## 16. Ambiente de desenvolvimento (Windows) vs produção (Raspberry Pi)

**Decision**: testes unitários que exercitam a lógica de negócio (extração
de chave, dedup, cálculo de resumo, parsing de campos a partir de texto
simulado) MUST rodar sem depender do binário real do Tesseract, usando um
texto de entrada já "reconhecido" como fixture. Testes que chamam o
Tesseract de verdade (validação de que a integração `pytesseract` funciona
contra uma imagem real) MUST ser puláveis automaticamente quando o binário
`tesseract` não é encontrado no `PATH` do ambiente onde os testes rodam.

**Rationale**: o desenvolvimento acontece no Windows, onde o Tesseract não
está necessariamente instalado; a suíte de testes não pode depender de
infraestrutura só disponível no Raspberry Pi de produção para validar a
lógica de negócio (Princípio V continua exigindo teste automatizado, mas
sem acoplar isso à presença de um binário de sistema específico).

## Status

Todos os pontos de NEEDS CLARIFICATION do Technical Context foram
resolvidos acima. Nenhum item pendente para a Fase 1.
