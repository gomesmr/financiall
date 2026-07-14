# Research: Importar Histórico Financeiro

Não há `NEEDS CLARIFICATION` no Technical Context. As decisões abaixo
resolvem escolhas de implementação levantadas pela spec e pela inspeção
(cuidadosa, sem expor dado real) do arquivo de histórico atual.

## 1. Coluna `titular` via `ALTER TABLE` idempotente, sem `CHECK` no schema

**Decisão**: `nota_fiscal.titular` é adicionada em `init_db()` pelo mesmo
mecanismo de `categoria_id` (feature 003) — checar `PRAGMA
table_info(nota_fiscal)` e rodar `ALTER TABLE nota_fiscal ADD COLUMN
titular TEXT` se ausente. Os valores esperados (`marcelo`, `cristine`,
`nao_identificado`) são validados na camada de serviço, não por `CHECK`
declarado no schema.

**Rationale**: mesmo raciocínio de research.md #1 da feature 002/003 — o
banco de produção/dev no Raspberry Pi já existe sem essa coluna, e
`ALTER TABLE ADD COLUMN` com `CHECK` tem suporte que varia entre versões
de SQLite (o ambiente de desenvolvimento é Windows, a produção é o
Raspberry Pi — versões de SQLite podem divergir). Validar em Python evita
essa dependência de versão e mantém a mesma abordagem já adotada.

## 2. Conversão de valores monetários: reais (float) → centavos (int)

**Decisão**: todo valor monetário do histórico (`total`, `vl_unit`,
`vl_total`, `vl_liquido`) é convertido via `round(valor * 100)` antes de
gravar.

**Rationale**: o schema já grava `valor_total`/`valor_unitario`/
`valor_total_item` como inteiros em centavos (mesmo padrão desde a
feature 001) — o histórico traz valores em reais como `float`.
`round()` evita erro de ponto flutuante (`554.54 * 100` não é
exatamente `55454.0` em `float`).

## 3. Conversão de data: `DD/MM/YYYY` → `YYYY-MM-DD`

**Decisão**: `data_emissao` do histórico (formato `DD/MM/YYYY`) é
convertida para o formato ISO já usado no schema (`YYYY-MM-DD`).
`ano_mes_emissao` é derivado da própria data já convertida
(`AAMM`), no mesmo formato usado pelas notas importadas pelos outros
canais.

**Rationale**: consistência de formato entre notas de qualquer origem —
`listar_notas` já ordena e filtra por mês assumindo esse formato
(`COALESCE(substr(data_emissao, 1, 7), ...)`).

## 4. `valor_total_item` usa `vl_liquido` quando presente, senão `vl_total`

**Decisão**: ao mapear um item do histórico, `valor_total_item` recebe
`vl_liquido` (valor após desconto) quando o campo existe; cai para
`vl_total` (bruto) quando `vl_liquido` está ausente.

**Rationale**: a soma dos itens deve refletir o valor realmente pago,
não o valor bruto antes de desconto — mantém consistência com o `total`
da nota (que já é o valor pago). Campos `un` (unidade) e `desconto`
individual não têm coluna correspondente em `item_nota` e não são
importados (Assumption já registrada na spec — perda aceita).

## 5. `canal_origem` mapeado a partir de `fonte`, quando presente

**Decisão**: `fonte = 'pdf'` → `CanalOrigem.FOTO_PDF`; `fonte = 'qr'` ou
ausente → `CanalOrigem.URL_CHAVE` (a chave de acesso está sempre presente
nesses registros, então o canal digital é a leitura mais fiel quando não
há indicação de PDF).

**Rationale**: a inspeção da estrutura (sem expor conteúdo real) mostrou
que nem todo registro tem o campo `fonte` — o mapeamento precisa
degradar para um valor razoável em vez de falhar.

## 6. Nota + itens gravados numa única transação (`inserir_nota_com_itens`)

**Decisão**: uma função de repositório nova grava a nota e seus itens
numa única transação (uma conexão, um `commit`), diferente do padrão
atual de `inserir_nota`/`inserir_itens` (duas conexões/commits
separados, usado pelos canais de importação unitária da feature 001).

**Rationale**: a spec exige explicitamente (edge case) que uma
interrupção no meio da importação em lote nunca deixe uma nota gravada
sem os itens correspondentes. Esse risco é mais real aqui do que numa
importação unitária via UI (um único registro por request), porque a
rotina processa múltiplos registros em sequência dentro do mesmo
processo — uma falha após gravar a nota N mas antes de seus itens (ex.:
processo interrompido) deixaria essa nota específica inconsistente sem
essa garantia.

## 7. Registro malformado é pulado com aviso, não aborta o lote

**Decisão**: um registro do histórico sem chave de acesso reconhecível
(campo ausente, vazio, ou não numérico de 44 dígitos) é pulado — contado
à parte no resumo final — sem interromper o processamento dos demais
registros do arquivo. Já um arquivo inteiro ausente ou com JSON inválido
aborta a execução inteira com erro (FR-007, diferente do caso acima).

**Rationale**: mesmo espírito do Princípio VII (fontes frágeis degradam
sem quebrar o fluxo principal), aplicado à qualidade heterogênea já
observada no arquivo real (nem todo registro tem os mesmos campos). Um
registro ruim não deveria custar a importação de todos os outros.

## 8. Rotina é script CLI, não rota HTTP

**Decisão**: `python -m src.scripts.importar_historico <arquivo>`,
executado manualmente pelo responsável do projeto — não uma rota Flask
nem uma ação disponível na UI.

**Rationale**: decisão já tomada no planejamento anterior à spec — é uma
migração pontual de dados legados, não um canal de entrada recorrente
como URL/chave ou foto/PDF (que continuam como rotas HTTP, feature 001).
Expor isso como rota adicionaria superfície de API para uma ação que
acontece, na prática, um número pequeno de vezes na vida do projeto.
