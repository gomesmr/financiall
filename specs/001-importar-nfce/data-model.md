# Data Model: Importar NFC-e sem Duplicar

## NotaFiscal

Representa um cupom fiscal (NFC-e) importado. Corresponde à entidade "Nota
Fiscal (NFC-e)" do spec.

| Campo | Tipo | Origem | Obrigatório | Regras de validação |
|---|---|---|---|---|
| `id` | inteiro, autoincremento | gerado pela base | sim | chave primária interna, nunca exposta como identificador de negócio |
| `chave_acesso` | string, 44 dígitos | decodificado da URL ou colado pelo usuário | sim | exatamente 44 dígitos numéricos; dígito verificador (44º dígito) MUST validar pelo algoritmo módulo 11 (ver research.md #4); **`UNIQUE`** na base — é a chave de deduplicação (Princípio II) |
| `uf` | string, 2 letras | decodificado da própria `chave_acesso` (posições 1–2, tabela de código IBGE de UF) | sim | preenchido sempre, independe da fonte de detalhamento |
| `cnpj_emitente` | string, 14 dígitos | decodificado da própria `chave_acesso` (posições 7–20) | sim | preenchido sempre, independe da fonte de detalhamento |
| `ano_mes_emissao` | string `AAMM` | decodificado da própria `chave_acesso` (posições 3–6) | sim | preenchido sempre; usado como fallback de `data_emissao` se o dia exato não for obtido |
| `modelo` | string, 2 dígitos | decodificado da própria `chave_acesso` (posições 21–22) | sim | preenchido sempre, qualquer modelo válido é aceito e gravado (ex.: `65` NFC-e, `55` NF-e) — alinhado ao Princípio ALL (toda fonte de gasto converge para a base única); a busca best-effort de detalhes (`emitente_nome`, `data_emissao` exata, `valor_total`, itens) só é tentada quando `modelo = 65`, porque o fluxo de consulta pesquisado (research.md #3 e #6) cobre apenas portais de NFC-e por UF — para `modelo` diferente de `65`, a nota é gravada com os campos decodificados da própria chave e permanece `pendente_revisao` até uma feature futura pesquisar a consulta ao portal correspondente |
| `emitente_nome` | string | fonte de detalhamento (best-effort) | não | nulo quando a fonte falha; nota fica "pendente de revisão" |
| `data_emissao` | data (dia exato) | fonte de detalhamento (best-effort); fallback é `ano_mes_emissao` sem o dia | não (mas sempre há ao menos ano-mês) | quando ausente o dia exato, resumo mensal ainda funciona via `ano_mes_emissao` |
| `valor_total` | inteiro (centavos) | fonte de detalhamento (best-effort) | não | armazenado em centavos (ex.: R$ 45,90 → `4590`) para evitar erro de arredondamento de ponto flutuante em soma financeira; conversão para exibição (`R$ x,xx`) é responsabilidade exclusiva da camada de apresentação (CLI), nunca da camada de armazenamento; nulo quando a fonte falha, nota fica "pendente de revisão"; nunca aparece em log de texto claro (Princípio IV) |
| `status` | enum: `completa` \| `pendente_revisao` | calculado | sim | `pendente_revisao` quando qualquer campo best-effort (`emitente_nome`, `data_emissao` exata, `valor_total`, itens) não foi obtido |
| `data_importacao` | timestamp | gerado no momento da gravação | sim | usada apenas para auditoria; resumo mensal usa `data_emissao`/`ano_mes_emissao`, nunca `data_importacao` (ver Assumptions do spec) |

**Regras de transição de estado**: `pendente_revisao` → `completa` só pode
ocorrer se uma nova tentativa de importação da mesma `chave_acesso` (que não
duplica, por já existir) obtiver com sucesso os campos que faltavam — fora
de escopo desta feature automatizar isso; nesta feature o status é somente
exibido (ver Assumptions do spec).

## ItemNota

Representa uma linha de produto/serviço dentro de uma `NotaFiscal`.
Corresponde à entidade "Item da Nota" do spec.

| Campo | Tipo | Origem | Obrigatório | Regras de validação |
|---|---|---|---|---|
| `id` | inteiro, autoincremento | gerado pela base | sim | chave primária interna |
| `nota_fiscal_id` | inteiro (FK) | relação com `NotaFiscal` | sim | `ON DELETE CASCADE` não se aplica nesta feature (notas não são excluídas — ver Assumptions do spec) |
| `codigo_item` | string | fonte de detalhamento (best-effort) | não | armazenado exatamente como veio da nota, **sem validação de formato GTIN/EAN** e sem assumir unicidade entre estabelecimentos (ver Assumptions do spec — costuma ser SKU interno do emitente) |
| `descricao` | string | fonte de detalhamento (best-effort) | não | nulo quando a fonte falha |
| `quantidade` | decimal | fonte de detalhamento (best-effort) | não | nulo quando a fonte falha |
| `valor_unitario` | inteiro (centavos) | fonte de detalhamento (best-effort) | não | armazenado em centavos, mesma justificativa de `NotaFiscal.valor_total`; nunca aparece em log de texto claro (Princípio IV) |
| `valor_total_item` | inteiro (centavos) | fonte de detalhamento (best-effort) | não | armazenado em centavos, mesma justificativa de `NotaFiscal.valor_total`; nunca aparece em log de texto claro (Princípio IV) |

**Relacionamento**: um `ItemNota` pertence a exatamente uma `NotaFiscal`
(1:N a partir de `NotaFiscal`). Uma `NotaFiscal` "pendente de revisão" pode
ter zero itens.

## ResumoMensal (view derivada, não persistida)

Não é uma tabela própria — é calculada sob demanda a partir de
`NotaFiscal.valor_total` agrupado por mês (usando `data_emissao` quando
disponível, senão `ano_mes_emissao`).

| Campo | Tipo | Regra |
|---|---|---|
| `mes` | string `AAAA-MM` | chave de agrupamento |
| `total_gasto` | inteiro (centavos) | soma de `valor_total` (em centavos) das notas do mês; notas com `valor_total` nulo (pendentes de revisão sem total) não entram na soma e o resumo MUST sinalizar que o total é parcial (FR-010) |
| `quantidade_notas` | inteiro | contagem de notas do mês, incluindo pendentes de revisão (para o usuário perceber que o total pode estar incompleto) |

## Esquema SQLite (referência)

```sql
CREATE TABLE nota_fiscal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave_acesso TEXT NOT NULL UNIQUE,
    uf TEXT NOT NULL,
    cnpj_emitente TEXT NOT NULL,
    ano_mes_emissao TEXT NOT NULL,
    modelo TEXT NOT NULL,
    emitente_nome TEXT,
    data_emissao TEXT,
    valor_total INTEGER,
    status TEXT NOT NULL CHECK (status IN ('completa', 'pendente_revisao')),
    data_importacao TEXT NOT NULL
);

CREATE TABLE item_nota (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nota_fiscal_id INTEGER NOT NULL REFERENCES nota_fiscal(id),
    codigo_item TEXT,
    descricao TEXT,
    quantidade REAL,
    valor_unitario INTEGER,
    valor_total_item INTEGER
);
```
