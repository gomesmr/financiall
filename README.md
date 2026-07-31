# financiALL

Base única de finanças pessoais: toda fonte de gasto ou renda — nota
fiscal, extrato bancário, fatura de cartão — converge para o mesmo lugar,
sem duplicar, com o gasto detalhado item a item sempre que a fonte
permitir. Esse é o princípio organizador do projeto — "**ALL**".

Construído incrementalmente, uma feature por vez (spec-kit), rodando
inteiramente num Raspberry Pi na rede local. Hoje reúne, entre outras
coisas: importação de nota fiscal (URL/QR Code/foto/PDF) e de extrato
bancário/fatura (Itaú, BB, Mercado Pago), categorização automática de
notas e itens, reconciliação entre transação e nota, visão por titular e
relatórios mensais com gráficos. Ver [`specs/`](specs/) para o histórico
completo de features (001 a 013) e a Constituição do projeto em
[`.specify/memory/constitution.md`](.specify/memory/constitution.md).

## Como funciona

Um Raspberry Pi, sempre ligado, hospeda o banco de dados, a API HTTP e um
worker de processamento — é o único servidor. Qualquer outro dispositivo
(celular, computador) é só um cliente sem estado, que acessa esse servidor
pela rede local pelo navegador.

```text
┌─────────────────┐         rede local          ┌──────────────────────────┐
│  celular /      │ ───────────────────────────▶│  Raspberry Pi            │
│  computador     │      HTTP (upload/consulta)  │  (financiall.service)    │
│  (navegador)    │◀─────────────────────────── │                          │
└─────────────────┘                              │  Flask + waitress        │
                                                  │  ├─ fila (SQLite)        │
                                                  │  ├─ worker OCR (thread)  │
                                                  │  └─ financiall.db        │
                                                  └──────────────────────────┘
```

Duas formas de importar uma nota:

1. **URL do QR Code ou chave de acesso colada** — busca best-effort os
   dados completos direto na página pública da SEFAZ que emitiu a nota.
2. **Foto ou PDF do cupom** — processado de forma assíncrona (o upload
   responde na hora, o processamento roda em segundo plano). Primeiro
   tenta ler o **QR Code** da imagem (mais confiável, tem correção de erro
   embutida); se não achar, cai para **OCR** de texto (Tesseract) como
   segunda tentativa.

Em ambos os casos, se os dados completos não puderem ser obtidos, a nota é
gravada mesmo assim com o que houver — nunca perde o registro do gasto,
só marca como "pendente de revisão" (ver Constituição do projeto,
Princípio VII).

## Funcionalidades

**Notas fiscais**

- Importar por URL do QR Code, chave de acesso de 44 dígitos, foto ou PDF
  do cupom (fila assíncrona), com leitura de QR Code pela câmera do
  celular direto no navegador
- Leitura de QR Code na imagem como estratégia primária de identificação,
  com OCR (Tesseract) como segunda tentativa
- Deduplicação por chave de acesso (ou por hash do arquivo, quando a
  chave não pôde ser identificada) — a mesma nota nunca é gravada duas
  vezes, venha ela por qual canal vier
- Degradação graciosa: fonte externa fora do ar ou OCR malsucedido nunca
  impedem o registro da nota, só marcam como pendente de revisão
- Exclusão de nota, e importação de histórico financeiro antigo em lote

**Extrato bancário e fatura de cartão**

- Importar extrato/fatura do Itaú, Banco do Brasil e Mercado Pago, pela
  interface web (formato detectado automaticamente) ou por linha de
  comando — deduplicação idempotente, mesmo com sobreposição parcial de
  período
- Classificação automática de natureza (gasto/renda/transferência) e
  reconciliação automática com nota fiscal já importada
- Visão por titular (Casal/Titular A/Titular B) em resumo e listagem

**Categorização e relatórios**

- CRUD de categorias, com categorização de notas inteiras ou item a item
  (individual ou em lote), e fila de pendentes para revisão manual
- Resumo de gasto do mês corrente, histórico de meses anteriores e
  relatórios detalhados por item/estabelecimento com navegação por mês
- Gráficos no resumo de gastos

**Geral**

- Interface web simples (sem framework de frontend) para importar e
  navegar pelas notas e extratos do celular ou do computador

## Stack

Python 3.11+, Flask + waitress, SQLite, Tesseract OCR (`pytesseract`),
`pyzbar` (leitura de QR Code), `pdf2image`/Poppler e `pdfplumber` (PDF),
`xlrd`/`openpyxl` (extrato/fatura em planilha), `requests` (busca
best-effort na SEFAZ), `pytest`.

Ver [`specs/001-importar-nfce/research.md`](specs/001-importar-nfce/research.md)
para o racional das escolhas técnicas da primeira feature; cada feature
seguinte tem seu próprio `research.md` em `specs/<NNN>-<nome>/`.

## Rodando localmente (desenvolvimento)

```bash
python -m venv .venv
.venv/Scripts/pip install -e .        # Windows
# .venv/bin/pip install -e .          # Linux/macOS

.venv/Scripts/pip install pytest
.venv/Scripts/python -m pytest tests/

.venv/Scripts/python -m src.main      # sobe em http://localhost:5000
```

No Windows, o Tesseract precisa ser instalado à parte (ex.:
[UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)) para
os testes que exercitam OCR real; sem ele, esses testes são pulados
automaticamente.

## Implantando no Raspberry Pi

Testado num Raspberry Pi 3 Model B (1GB RAM) com Raspberry Pi OS de 64
bits. O hardware limitado molda várias decisões do projeto: processamento
sequencial (nunca em paralelo), sem Docker, sem dependências pesadas — ver
[`specs/001-importar-nfce/plan.md`](specs/001-importar-nfce/plan.md).

```bash
# no Pi, com o repositório clonado em ~/financiall
./infra/setup-raspberry-pi.sh ~/financiall

sudo cp infra/financiall.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now financiall
```

O script é idempotente (só instala o que ainda não está presente) e cria
o ambiente virtual + banco de dados automaticamente. Ajuste `User`/`Group`/
`WorkingDirectory` em `infra/financiall.service` para o seu usuário antes
de instalar o serviço.

## Uso

Acesse `http://<host-do-pi>:5000/` no navegador — página inicial com os
cards para importar nota fiscal e extrato/fatura, e navegação para lista
de notas, transações, categorias, pendentes de revisão e resumo mensal.

Para uso programático, a API expõe as rotas principais abaixo (ver o
`contracts/api.md` de cada feature em `specs/<NNN>-<nome>/` — por exemplo
[`specs/001-importar-nfce/contracts/api.md`](specs/001-importar-nfce/contracts/api.md)
e [`specs/013-upload-extrato-web/contracts/api.md`](specs/013-upload-extrato-web/contracts/api.md)
— para o contrato completo de cada uma):

| Método | Rota | O que faz |
|---|---|---|
| `POST` | `/notas` | Importa nota por URL do QR Code ou chave colada |
| `POST` | `/notas/upload` | Envia foto/PDF da nota (`multipart/form-data`, campo `arquivo`) |
| `GET` | `/envios/<id>` | Status de processamento de um envio de foto/PDF |
| `GET` | `/notas` | Lista notas importadas (`?mes=AAAA-MM` opcional) |
| `POST` | `/extratos/upload` | Envia extrato/fatura (Itaú, BB ou Mercado Pago); formato detectado automaticamente |
| `GET` | `/notas/resumo/mes-atual` | Gasto parcial do mês corrente |
| `GET` | `/notas/resumo/historico` | Gasto por mês em meses anteriores |
| `GET` | `/notas/resumo/categorias` | Gasto do mês agrupado por categoria |
| `GET/POST/PUT/DELETE` | `/categorias` | CRUD de categorias |
| `GET` | `/transacoes/pendentes` | Transações de extrato pendentes de classificação de natureza |

## Testes

```bash
pytest tests/unit tests/integration tests/contract
```

Testes que dependem de binários externos (Tesseract, Poppler) são pulados
automaticamente quando o binário não está no `PATH` do ambiente — a suíte
roda completa no Raspberry Pi (onde ambos estão instalados) e roda o
essencial em qualquer máquina de desenvolvimento.

## Importando um extrato bancário novo

Desde a feature 010/011, o financiALL também importa extrato bancário (não
só nota fiscal), com o mesmo cuidado de nunca duplicar uma transação já
importada.

**Forma recomendada (feature 013)**: pela própria interface web, na
página inicial (`/`), no card "Extrato ou fatura bancária" — basta
escolher o arquivo baixado do banco (Itaú, BB ou Mercado Pago) e enviar; o
formato é detectado automaticamente, sem precisar informar qual banco é
nem ter acesso ao servidor. Ver
[`specs/013-upload-extrato-web/contracts/api.md`](specs/013-upload-extrato-web/contracts/api.md)
para o contrato completo (`POST /extratos/upload`).

**Alternativa via linha de comando** (útil para reprocessar em lote uma
pasta inteira, ou para quem tem acesso ao servidor): o comando a rodar
depende da conta:

```bash
# Itaú (Titular A) -- fatura de cartão em .xls, um arquivo ou uma pasta inteira
.venv/Scripts/python -m src.scripts.importar_extrato_itau_cartao "<arquivo-ou-pasta>.xls"

# Banco do Brasil (Titular B) -- extrato de conta corrente em .xlsx, um arquivo ou uma pasta inteira
.venv/Scripts/python -m src.scripts.importar_extrato_bb "<arquivo-ou-pasta>.xlsx"

# Mercado Pago (Titular A) -- fatura de cartão em .pdf, um arquivo ou uma pasta inteira
.venv/Scripts/python -m src.scripts.importar_fatura_mercado_pago "<arquivo-ou-pasta>.pdf"
```

Os três comandos:

- podem ser rodados contra um arquivo único ou uma pasta (processam todo
  arquivo do formato certo dentro dela);
- são **idempotentes** — rodar de novo com um arquivo já importado (ou um
  novo arquivo cujo período se sobrepõe parcialmente ao já importado) não
  duplica nada, só reporta quantas transações já existiam;
- classificam automaticamente a natureza (gasto/renda/transferência) e
  tentam reconciliar com nota fiscal já importada, sem passo manual
  adicional;
- imprimem um resumo em português (quantas foram importadas, quantas já
  existiam, quantas ficaram pendentes de revisão) — o que ficar pendente
  aparece em `/ver/transacoes/pendentes` para classificar manualmente.

Depois de importar, `/ver/resumo` e `/ver/transacoes` já refletem o novo
extrato, com o filtro por titular (Casal/Titular A/Titular B) mostrando o
gasto de cada um separadamente. Ver
[`specs/011-importar-extrato-bb-cristine/contracts/cli.md`](specs/011-importar-extrato-bb-cristine/contracts/cli.md)
e [`specs/012-importar-fatura-mercado-pago/contracts/cli.md`](specs/012-importar-fatura-mercado-pago/contracts/cli.md)
para o contrato completo dos três comandos.

## Estrutura do projeto

```text
src/
├── api/            # Flask: rotas HTTP + páginas HTML (templates/)
├── models/         # Entidades (NotaFiscal, ItemNota, Transacao, ...)
├── services/       # Lógica de domínio (chave de acesso, OCR, QR Code,
│                   #   busca SEFAZ, fila, resumo mensal, extrato/fatura,
│                   #   categorização, reconciliação)
├── scripts/        # Comandos de linha de comando (importação em lote)
├── storage/        # Schema e repositório SQLite
└── worker/         # Worker sequencial que consome a fila de OCR

tests/              # unit/, integration/, contract/
infra/              # Script de provisionamento + unit systemd
specs/              # Spec, plano técnico, pesquisa, tarefas de cada
                    #   feature (spec-kit), uma pasta <NNN>-<nome> por
                    #   feature, de 001 a 013
```

## Roadmap

- ~~Categorização de notas/itens~~ — entregue (feature 008)
- ~~Relatórios mensais detalhados~~ — entregue (feature 009)
- ~~Reconciliação com extrato bancário~~ — entregue (feature 010)
- ~~Múltiplas contas/pessoas (titular)~~ — entregue (feature 011)
- ~~Fatura Mercado Pago~~ — entregue (feature 012)
- ~~Upload de extrato/fatura pela web~~ — entregue (feature 013)
- Suporte a CF-e SAT (cupom de modelo 59)

## Princípios do projeto

Simplicidade acima de esperteza, idempotência não-negociável, tratamento
explícito de erro em toda entrada externa, dados financeiros nunca em log
de texto claro, testável por construção, artefatos voltados ao usuário em
português, fontes frágeis degradam sem quebrar o fluxo principal, integridade
visual e de assets de terceiros. Ver
[`.specify/memory/constitution.md`](.specify/memory/constitution.md) para
o texto completo.
