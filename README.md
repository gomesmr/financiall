# financiALL

Base única de finanças pessoais: toda fonte de gasto (nota fiscal, e no
futuro extrato bancário) converge para o mesmo lugar, com o gasto
detalhado item a item sempre que a fonte permitir. Esse é o princípio
organizador do projeto — "**ALL**".

Esta é a **feature 001**: importar notas fiscais de consumidor (NFC-e) sem
duplicar, rodando inteiramente num Raspberry Pi na rede local.

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

- Importar por URL do QR Code ou chave de acesso de 44 dígitos
- Importar por foto ou PDF do cupom (fila assíncrona, um por vez)
- Leitura de QR Code na imagem como estratégia primária de identificação
- Deduplicação por chave de acesso (ou por hash do arquivo, quando a
  chave não pôde ser identificada) — a mesma nota nunca é gravada duas
  vezes, venha ela por qual canal vier
- Degradação graciosa: fonte externa fora do ar ou OCR malsucedido nunca
  impedem o registro da nota
- Listagem de notas com filtro por mês, e página de detalhe com os itens
- Resumo de gasto do mês corrente e histórico de meses anteriores
  (parcial — só o que já foi documentado por nota fiscal)
- Interface web simples (sem framework de frontend) para importar e
  navegar pelas notas do celular ou do computador

## Stack

Python 3.11+, Flask + waitress, SQLite, Tesseract OCR (`pytesseract`),
`pyzbar` (leitura de QR Code), `pdf2image`/Poppler (PDF), `requests`
(busca best-effort na SEFAZ), `pytest`.

Ver [`specs/001-importar-nfce/research.md`](specs/001-importar-nfce/research.md)
para o racional de cada escolha técnica.

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

Acesse `http://<host-do-pi>:5000/` no navegador — formulário para importar
por URL/chave ou enviar foto/PDF, com navegação para a lista de notas e o
resumo mensal.

Para uso programático, a API expõe (ver
[`specs/001-importar-nfce/contracts/api.md`](specs/001-importar-nfce/contracts/api.md)
para o contrato completo):

| Método | Rota | O que faz |
|---|---|---|
| `POST` | `/notas` | Importa por URL do QR Code ou chave colada |
| `POST` | `/notas/upload` | Envia foto/PDF (`multipart/form-data`, campo `arquivo`) |
| `GET` | `/envios/<id>` | Status de processamento de um envio de foto/PDF |
| `GET` | `/notas` | Lista notas importadas (`?mes=AAAA-MM` opcional) |
| `GET` | `/notas/resumo/mes-atual` | Gasto parcial do mês corrente |
| `GET` | `/notas/resumo/historico` | Gasto por mês em meses anteriores |

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
importada. Ao baixar um extrato novo do banco, o comando a rodar depende
da conta:

```bash
# Itaú (Marcelo) -- fatura de cartão em .xls, um arquivo ou uma pasta inteira
.venv/Scripts/python -m src.scripts.importar_extrato_itau_cartao "<arquivo-ou-pasta>.xls"

# Banco do Brasil (Cristine) -- extrato de conta corrente em .xlsx, um arquivo ou uma pasta inteira
.venv/Scripts/python -m src.scripts.importar_extrato_bb "<arquivo-ou-pasta>.xlsx"

# Mercado Pago (Marcelo) -- fatura de cartão em .pdf, um arquivo ou uma pasta inteira
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
extrato, com o filtro por titular (Casal/Marcelo/Cristine) mostrando o
gasto de cada um separadamente. Ver
[`specs/011-importar-extrato-bb-cristine/contracts/cli.md`](specs/011-importar-extrato-bb-cristine/contracts/cli.md)
e [`specs/012-importar-fatura-mercado-pago/contracts/cli.md`](specs/012-importar-fatura-mercado-pago/contracts/cli.md)
para o contrato completo dos três comandos.

## Estrutura do projeto

```text
src/
├── api/            # Flask: rotas HTTP + páginas HTML (templates/)
├── models/         # Entidades (NotaFiscal, ItemNota)
├── services/       # Lógica de domínio (chave de acesso, OCR, QR Code,
│                   #   busca SEFAZ, fila, resumo mensal)
├── storage/        # Schema e repositório SQLite
└── worker/         # Worker sequencial que consome a fila de OCR

tests/              # unit/, integration/, contract/
infra/              # Script de provisionamento + unit systemd
specs/001-importar-nfce/  # Spec, plano técnico, pesquisa, tarefas (spec-kit)
```

## Roadmap

- ~~Categorização de notas/itens~~ — entregue (feature 008)
- ~~Reconciliação com extrato bancário~~ — entregue (feature 010)
- ~~Múltiplas contas/pessoas (titular)~~ — entregue (feature 011)
- Suporte a CF-e SAT (cupom de modelo 59)

## Princípios do projeto

Simplicidade acima de esperteza, idempotência não-negociável, tratamento
explícito de erro em toda entrada externa, dados financeiros nunca em log
de texto claro, testável por construção, artefatos voltados ao usuário em
português, fontes frágeis degradam sem quebrar o fluxo principal, integridade
visual e de assets de terceiros. Ver
[`.specify/memory/constitution.md`](.specify/memory/constitution.md) para
o texto completo.
