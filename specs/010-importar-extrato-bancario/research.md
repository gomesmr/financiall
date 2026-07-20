# Research: Importar Extrato Bancário

## #1 — Fórmula de fingerprint (idempotência entre migração e parser recorrente)

**Decisão**: `sha1(f"{data_iso}|{descricao_normalizada}|{valor_centavos_abs}|{conta_canonica}")[:16]` —
exatamente a fórmula do script legado `importar_extrato.py`, trocando só a
fonte da descrição normalizada (reaproveita `src/services/normalizacao.py`,
já existente, em vez da normalização própria do script legado).

**Rationale**: FR-023 exige que migração histórica e parser recorrente nunca
dupliquem a mesma transação. Usar a mesma fórmula nos dois pipelines é a
forma mais simples de garantir isso (Princípio I) — não precisa de nenhuma
tabela de-para entre "fingerprint antigo" e "fingerprint novo".

**Alternativas consideradas**: gerar um fingerprint novo, diferente do
legado, mapeando o antigo à parte — rejeitado por adicionar uma tabela de
tradução sem necessidade.

## #2 — Consolidação de contas duplicadas do legado

**Decisão**: dicionário fixo em `src/services/importar_historico_extrato.py`:

```python
CONTA_CANONICA = {
    "2486": "itau_2486",
    "Itaú_2486": "itau_2486",
    "9073": "itau_9073",
    "Itaú_9073": "itau_9073",
    "Itaú_CC": "itau_cc",
    "Flash": "flash",
}
```

Aplicado à conta **antes** de calcular o fingerprint e antes de persistir —
tanto na migração quanto no parser recorrente (mesma função reaproveitada),
o que também resolve o requisito de fingerprint idêntico entre pipelines
(#1): duas grafias antigas da mesma conta física agora sempre produzem o
mesmo fingerprint.

**Rationale**: FR-010. Conta não mapeada (ex.: uma conta nova que apareça no
futuro) passa direto (usa o valor original), em vez de falhar — degrada sem
quebrar o fluxo (Princípio VII, mesmo espírito).

## #3 — Janela de data para reconciliação Nota Fiscal ↔ Transação

**Decisão**: janela depende do tipo de conta, inferido pelo sufixo da conta
canônica (#2): contas terminadas em `_cc` (débito/conta corrente) usam
janela de **3 dias** (nota e lançamento aparecem quase juntos); as demais
(cartão de crédito) usam janela de **até 45 dias** (nota pode ser emitida
semanas antes do fechamento da fatura). Em ambos os casos, `transacao.data
>= nota_fiscal.data_emissao` (a transação nunca aparece no extrato antes da
compra).

**Rationale**: compra no cartão só vira lançamento no fechamento do ciclo,
que pode ser até ~45 dias depois da emissão (research da estrutura real de
fatura Itaú, mesma lógica do script legado); compra em débito cai no
extrato em poucos dias.

**Alternativas consideradas**: janela única fixa — rejeitada por gerar
falsos negativos em compra de cartão perto do fim do ciclo.

## #4 — Taxonomia de categoria para `natureza = gasto`

**Decisão**: reaproveitar a `TAXONOMIA_RESERVADA_EXTRATO` que a feature 008
**já semeou** em `src/scripts/seed_taxonomia_categorizacao.py` (categoria
`categoria`, mesma tabela de item), especificamente reservada para esta
feature: Moradia (Aluguel, Contas de consumo), Transporte (Combustível,
Transporte público, Apps de mobilidade), Educação, Lazer, Serviços e
assinaturas, Vestuário. Nenhuma categoria nova precisa ser criada — só
mapear os padrões de descrição do script legado para essas categorias
já existentes.

**Rationale**: Princípio I — a feature 008 já previu e criou esse espaço
exatamente para não fragmentar a taxonomia depois; usá-lo agora fecha esse
propósito sem trabalho duplicado.

## #5 — Seed de `regra_natureza` a partir do script legado

**Decisão**: novo arquivo `src/scripts/regras_semente_natureza.json`,
migrando a lista `REGRAS` de `assets/finalcial/Financeiro/importar_extrato.py`
(cada entrada: `padrao`, `natureza`, `categoria`/`subcategoria` quando
`natureza=gasto`, `prioridade`). Aplicado por um novo
`src/scripts/seed_regras_natureza.py`, mesmo padrão idempotente de
`seed_taxonomia_categorizacao.py::seed_regras` (insere só o que ainda não
existe, por `padrao` + `natureza`).

**Rationale**: FR-004. Preserva o trabalho de classificação já validado
pelo usuário em vez de recomeçar do zero.

## #6 — Motor de classificação de natureza (cascata)

**Decisão**: duas tabelas novas, espelhando exatamente
`cache_descricao_categoria`/`regra_categoria` (feature 008), mas para o
domínio de natureza: `cache_descricao_natureza` (chave
`descricao_normalizada`, valor `natureza` + `categoria_id` opcional) e
`regra_natureza` (`padrao`, `natureza`, `categoria_id` opcional,
`prioridade`, `ativa`). Serviço novo `src/services/classificacao_natureza.py`
com `classificar_natureza(descricao, db_path)` seguindo a mesma cascata
cache → regra mais específica → pendente já usada por
`classificacao_itens.classificar_item`.

**Rationale**: Princípio I — reaproveita um padrão já validado em produção
em vez de inventar um mecanismo novo; FR-002/FR-005/FR-006.

## #7 — Reconciliação: quando tentar, e o que fazer com múltiplos candidatos

**Decisão**: a tentativa de reconciliar roda automaticamente logo após uma
transação ser classificada com `natureza = gasto` (na importação, histórica
ou recorrente) e também sob demanda (endpoint manual, para cobrir o caso de
a nota chegar depois da transação). Critério: `nota_fiscal.valor_total =
transacao.valor`, dentro da janela de data (#3), e a nota ainda não
reconciliada com nenhuma outra transação (índice único em
`transacao.nota_fiscal_id`). Exatamente um candidato → liga
automaticamente. Zero candidatos → segue sem vínculo (maioria dos casos).
Mais de um candidato → nenhum vínculo automático; ambos aparecem juntos
numa fila de revisão (`GET /transacoes/reconciliacao/pendentes`), resolvida
manualmente (`PUT /transacoes/<id>/nota/<nota_id>`).

**Rationale**: FR-011/FR-013. Evita decidir por aproximação quando há
ambiguidade real (edge case do spec.md).

## #8 — Cálculo do gasto do mês sem dupla contagem (query ao vivo)

**Decisão**: `resumo.py` ganha uma função `gasto_por_categoria_item` (e
`gasto_mes_corrente`/`historico_meses_anteriores`) estendida para somar
`transacao` (natureza=gasto) **e** `nota_fiscal` cujo `id` não aparece em
nenhum `transacao.nota_fiscal_id` do mês — nunca as duas para a mesma
compra, porque no instante em que uma reconciliação existe, a nota some do
segundo termo. Sem tabela de resumo persistida, sem job de recomputação —
a mesma soma acontece na hora de cada consulta (mesmo padrão já existente
em `_query_resumo_por_mes`).

**Rationale**: FR-015/FR-016, SC-003. Decisão já validada com o usuário na
sessão de brainstorm que originou esta spec.

## #9 — Identidade de `Estabelecimento` (CNPJ/CPF vs. descrição)

**Decisão**: `estabelecimento.documento` (CNPJ/CPF, nullable, único quando
presente) é a chave primária de identidade; `descricao_normalizada`
(nullable, único quando presente e `documento IS NULL`) é o fallback.
Resolução em cascata ao processar uma transação:
1. Se a transação reconciliou (#7) com uma nota que tem `cnpj_emitente` →
   usa esse CNPJ.
2. Senão, tenta extrair um documento (11 ou 14 dígitos consecutivos) da
   própria `descricao` da transação (comum em PIX) via regex simples.
3. Senão, cai no fallback por `descricao_normalizada`.

Quando uma transação já tinha `estabelecimento_id` resolvido por descrição
e depois reconcilia com uma nota que traz CNPJ (FR-019), o registro por
descrição é **atualizado in-place** para passar a ter o `documento` (em vez
de criar um segundo registro) — evitando duas identidades para a mesma
loja.

**Rationale**: FR-017/FR-018/FR-019.

## #10 — Dependência nova: `xlrd`

**Decisão**: adicionar `xlrd>=2.0` a `pyproject.toml` — é a biblioteca que
lê `.xls` (formato binário antigo do Excel, usado pela fatura Itaú
exportada do internet banking), mesma biblioteca já usada pelo script
legado. `openpyxl` (que o projeto não tem) não abre `.xls`, só `.xlsx`.

**Rationale**: Princípio I — dependência mínima, justificada pelo formato
real do arquivo que o parser precisa ler (não há como evitar sem reescrever
o arquivo de origem, que não está sob controle do projeto).
