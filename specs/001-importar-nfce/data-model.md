# Data Model: Importar Notas Fiscais sem Duplicar

## NotaFiscal

Representa um cupom fiscal importado, por qualquer canal. Corresponde à
entidade "Nota Fiscal" do spec.

| Campo | Tipo | Origem | Obrigatório | Regras de validação |
|---|---|---|---|---|
| `id` | inteiro, autoincremento | gerado pela base | sim | chave primária interna, nunca exposta como identificador de negócio |
| `chave_acesso` | string, 44 dígitos, opcional | canal 1: decodificado da URL ou colado; canal 2: extraído por OCR quando legível | não | quando presente: exatamente 44 dígitos numéricos, dígito verificador válido (módulo 11); **único** entre as notas que o possuem (índice único parcial — ver esquema) — é o identificador primário de deduplicação (Princípio II) |
| `hash_conteudo` | string (SHA-256 hex), opcional | canal 2: hash do arquivo (foto/PDF) enviado, quando `chave_acesso` não pôde ser identificada | não | preenchido apenas quando `chave_acesso` é nulo; **único** entre as notas que o possuem (índice único parcial) — identificador alternativo de deduplicação (Princípio II) |
| `canal_origem` | enum: `url_chave` \| `foto_pdf` | determinado pelo endpoint de entrada | sim | usado para exibição na listagem (FR-014) |
| `uf` | string, 2 letras, opcional | decodificado da `chave_acesso`, quando presente | não | nulo quando `chave_acesso` é nulo (canal 2 sem chave identificável) |
| `cnpj_emitente` | string, 14 dígitos, opcional | decodificado da `chave_acesso`, quando presente | não | nulo quando `chave_acesso` é nulo |
| `ano_mes_emissao` | string `AAMM`, opcional | decodificado da `chave_acesso`, quando presente | não | usado como fallback de `data_emissao` quando o dia exato não é obtido; nulo quando `chave_acesso` é nulo e o OCR também não conseguiu extrair uma data |
| `modelo` | string, 2 dígitos, opcional | decodificado da `chave_acesso`, quando presente | não | qualquer modelo válido é aceito (ex.: `65` NFC-e, `55` NF-e); busca best-effort na fonte SEFAZ só é tentada quando `modelo = 65` (canal 1) |
| `emitente_nome` | string | canal 1: fonte SEFAZ (best-effort); canal 2: heurística sobre o texto do OCR (best-effort) | não | nulo quando a fonte/OCR falha; nota fica "pendente de revisão" |
| `data_emissao` | data (dia exato) | canal 1: fonte SEFAZ; canal 2: heurística de data no texto do OCR; fallback é `ano_mes_emissao` sem o dia (quando há chave) | não | usada nas consultas de gasto do mês corrente/histórico; se ausente e `ano_mes_emissao` também ausente, a nota não entra em nenhuma consulta de gasto mensal (só na listagem geral) |
| `valor_total` | inteiro (centavos) | canal 1: fonte SEFAZ; canal 2: heurística de valor total no texto do OCR | não | armazenado em centavos para evitar erro de arredondamento; conversão para exibição é responsabilidade da camada de apresentação (API/HTML), nunca do armazenamento; nunca aparece em log de texto claro (Princípio IV) |
| `status` | enum: `completa` \| `pendente_revisao` | calculado | sim | `pendente_revisao` quando qualquer campo best-effort (`emitente_nome`, `data_emissao` exata, `valor_total`, itens) não foi obtido, ou quando nem `chave_acesso` foi identificada |
| `data_importacao` | timestamp | gerado no momento da gravação | sim | usada apenas para auditoria; consultas de gasto usam `data_emissao`/`ano_mes_emissao`, nunca `data_importacao` |

**Regra de identidade**: toda `NotaFiscal` MUST ter pelo menos um dos dois
identificadores de deduplicação preenchido (`chave_acesso` ou
`hash_conteudo`) — nunca os dois nulos ao mesmo tempo. No canal 1
(URL/chave), `chave_acesso` é sempre obrigatório antes de qualquer
gravação (entrada sem chave válida é rejeitada, FR-004, nunca chega a
criar um registro). No canal 2 (foto/PDF), `hash_conteudo` está sempre
disponível a partir do arquivo recebido, então mesmo uma falha total de
OCR ainda produz um identificador válido para a nota.

**Regras de transição de estado**: `pendente_revisao` → `completa` só pode
ocorrer se uma nova tentativa de importação da mesma nota (que não
duplica, por já existir) obtiver com sucesso os campos que faltavam —
automatizar essa transição fica fora de escopo desta feature; o status é
somente exibido.

## ItemNota

Representa uma linha de produto/serviço dentro de uma `NotaFiscal`.
Corresponde à entidade "Item da Nota" do spec.

| Campo | Tipo | Origem | Obrigatório | Regras de validação |
|---|---|---|---|---|
| `id` | inteiro, autoincremento | gerado pela base | sim | chave primária interna |
| `nota_fiscal_id` | inteiro (FK) | relação com `NotaFiscal` | sim | notas não são excluídas nesta feature, `ON DELETE CASCADE` não se aplica |
| `codigo_item` | string | canal 1: fonte SEFAZ; canal 2: heurística de linha no texto do OCR | não | armazenado exatamente como veio, **sem validação de formato GTIN/EAN** — costuma ser SKU interno do emitente |
| `descricao` | string | canal 1/2 (best-effort) | não | nulo quando a fonte/OCR falha |
| `quantidade` | decimal | canal 1/2 (best-effort) | não | nulo quando a fonte/OCR falha |
| `valor_unitario` | inteiro (centavos) | canal 1/2 (best-effort) | não | mesma justificativa de centavos de `NotaFiscal.valor_total`; nunca em log de texto claro |
| `valor_total_item` | inteiro (centavos) | canal 1/2 (best-effort) | não | mesma justificativa de centavos; nunca em log de texto claro |

**Relacionamento**: um `ItemNota` pertence a exatamente uma `NotaFiscal`
(1:N). Itens são o campo mais frágil de extrair no canal 2 (OCR) — uma
`NotaFiscal` "pendente de revisão" pode ter zero itens, inclusive vinda do
canal 1.

## EnvioOcr

Representa um arquivo (foto ou PDF) enviado pelo canal de digitalização,
antes (ou independentemente) de virar/apontar para uma `NotaFiscal`
processada. Corresponde à entidade "Envio de Foto/PDF" do spec. Não existe
para o canal 1 (URL/chave), que é processado de forma síncrona dentro do
próprio pedido.

| Campo | Tipo | Origem | Obrigatório | Regras de validação |
|---|---|---|---|---|
| `id` | inteiro, autoincremento | gerado pela base | sim | identificador usado pelo usuário para consultar o status (US5) |
| `caminho_arquivo` | string | gravado no momento do upload | sim | caminho no sistema de arquivos do Raspberry Pi onde o arquivo bruto foi salvo |
| `tipo_arquivo` | enum: `foto` \| `pdf` | detectado no upload | sim | determina se o arquivo já é imagem ou se passa primeiro por `pdf2image` |
| `hash_conteudo` | string (SHA-256 hex) | calculado no momento do upload, sobre os bytes brutos do arquivo | sim | sempre calculável, independentemente do sucesso do OCR; usado na checagem de dedup quando a `chave_acesso` não é identificada |
| `status` | enum: `pendente` \| `processando` \| `concluido` | gerenciado pelo worker | sim | `pendente` ao ser recebido; `processando` enquanto o worker trabalha nele; `concluido` sempre que o processamento terminar — inclusive quando não extraiu nenhum dado utilizável (o resultado nesse caso é uma `NotaFiscal` "pendente de revisão", nunca um estado de erro exposto ao usuário, Princípio VII) |
| `nota_fiscal_id` | inteiro (FK), opcional | preenchido ao concluir o processamento | não | aponta para a nota criada, **ou** para uma nota já existente quando o processamento identifica uma duplicata (US3 cenário 2) |
| `data_envio` | timestamp | gerado no momento do upload | sim | usado para ordenar a fila (FIFO) |
| `data_processamento` | timestamp, opcional | gerado quando o status vira `concluido` | não | usado para auditoria |

**Regra de recuperação após reinício**: ao iniciar, o worker MUST reverter
para `pendente` qualquer envio que esteja com status `processando`
(indica interrupção no meio do processamento anterior — research.md #11).

**Regra de robustez do processamento**: qualquer exceção não prevista
durante o reconhecimento de texto ou a extração de campos de um envio MUST
ser capturada; o envio ainda é marcado `concluido`, apontando para uma
`NotaFiscal` mínima (identificada só por `hash_conteudo`, status
`pendente_revisao`) — nunca fica preso indefinidamente nem propaga exceção
para o usuário (Princípios III e VII).

## ResumoMensal (view derivada, não persistida)

Não é uma tabela própria — calculada sob demanda a partir de
`NotaFiscal.valor_total` agrupado por mês (usando `data_emissao` quando
disponível, senão `ano_mes_emissao`). Alimenta tanto a consulta de gasto
parcial do mês corrente (US7) quanto o histórico de meses anteriores (US8)
— a mesma computação, filtrada por mês.

| Campo | Tipo | Regra |
|---|---|---|
| `mes` | string `AAAA-MM` | chave de agrupamento |
| `total_gasto` | inteiro (centavos) | soma de `valor_total` (em centavos) das notas do mês; notas com `valor_total` nulo não entram na soma, e a resposta MUST sinalizar que o total é parcial (FR-015/FR-016) |
| `quantidade_notas` | inteiro | contagem de notas do mês, incluindo pendentes de revisão (para o usuário perceber que o total pode estar incompleto) |

## Esquema SQLite (referência)

```sql
CREATE TABLE nota_fiscal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave_acesso TEXT,
    hash_conteudo TEXT,
    canal_origem TEXT NOT NULL CHECK (canal_origem IN ('url_chave', 'foto_pdf')),
    uf TEXT,
    cnpj_emitente TEXT,
    ano_mes_emissao TEXT,
    modelo TEXT,
    emitente_nome TEXT,
    data_emissao TEXT,
    valor_total INTEGER,
    status TEXT NOT NULL CHECK (status IN ('completa', 'pendente_revisao')),
    data_importacao TEXT NOT NULL,
    CHECK (chave_acesso IS NOT NULL OR hash_conteudo IS NOT NULL)
);

CREATE UNIQUE INDEX idx_nota_fiscal_chave_acesso
    ON nota_fiscal(chave_acesso) WHERE chave_acesso IS NOT NULL;

CREATE UNIQUE INDEX idx_nota_fiscal_hash_conteudo
    ON nota_fiscal(hash_conteudo) WHERE hash_conteudo IS NOT NULL;

CREATE TABLE item_nota (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nota_fiscal_id INTEGER NOT NULL REFERENCES nota_fiscal(id),
    codigo_item TEXT,
    descricao TEXT,
    quantidade REAL,
    valor_unitario INTEGER,
    valor_total_item INTEGER
);

CREATE TABLE envio_ocr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caminho_arquivo TEXT NOT NULL,
    tipo_arquivo TEXT NOT NULL CHECK (tipo_arquivo IN ('foto', 'pdf')),
    hash_conteudo TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pendente', 'processando', 'concluido')) DEFAULT 'pendente',
    nota_fiscal_id INTEGER REFERENCES nota_fiscal(id),
    data_envio TEXT NOT NULL,
    data_processamento TEXT
);
```
