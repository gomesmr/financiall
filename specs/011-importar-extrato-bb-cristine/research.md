# Research: Importar extrato BB (Cristine) e visão por titular

## #1 — `titular` já existe de ponta a ponta em `Transacao`; nenhuma migração de schema é necessária

**Decisão**: Não alterar `src/storage/db.py` (schema), nem `src/models/transacao.py`
(dataclass), nem `processar_transacoes()` (núcleo de persistência/
classificação/reconciliação). Usar tudo como está.

**Rationale**: Inspeção direta do código mostrou que a feature 010 já foi
desenhada multi-titular, mesmo só tendo dado real do Marcelo até agora:

- `CREATE TABLE transacao (...)` já tem a coluna `titular TEXT` (`src/storage/db.py:115`).
- `Transacao` (dataclass) já tem o campo `titular: str | None = None` (`src/models/transacao.py:37`).
- `processar_transacoes()` já lê `registro.get("titular")` e grava direto em
  `Transacao(titular=...)` (`src/services/importar_historico_extrato.py:118`).
- `inserir_transacao()` já persiste a coluna `titular` no INSERT (`src/storage/db.py:1292/1307`).

Ou seja: o único motivo de hoje só existir dado do Marcelo é que nenhum
parser jamais populou `titular="cristine"` — não uma limitação de schema.

**Alternatives considered**: criar uma tabela `titular` separada com FK —
rejeitado por Princípio I (simplicidade): titular é um enum de 2 valores
fixos (mesmo padrão já usado em `NotaFiscal.titular`), não uma entidade com
atributos próprios.

## #2 — Parser do extrato BB replica o padrão do parser recorrente de cartão Itaú, não o padrão de migração via `registro.json`

**Decisão**: Criar `src/services/importar_extrato_bb.py::parsear(caminho) -> list[dict]`
e `src/scripts/importar_extrato_bb.py` (CLI fino), espelhando exatamente
`src/services/importar_extrato_itau_cartao.py` + `src/scripts/importar_extrato_itau_cartao.py`.
`parsear()` devolve registros no mesmo formato aceito por
`processar_transacoes()`: `{"data", "descricao", "valor_raw", "conta",
"fonte", "titular"}`.

**Rationale**: Existem dois padrões de ingestão na feature 010: (a)
migração histórica pontual via `registro.json` já processado por um script
legado externo ao projeto (`importar_historico_extrato.py`); (b) parser
recorrente que lê o arquivo bruto do banco diretamente e chama
`processar_transacoes()` sem etapa intermediária (`importar_extrato_itau_cartao.py`,
US6). O extrato do BB nunca passou pelo script legado (não existe
`registro.json` equivalente para a Cristine) — não faz sentido introduzir
uma etapa JSON intermediária só para depois descartá-la. O padrão (b) serve
tanto para a importação histórica (primeira execução contra os 5 arquivos
já baixados) quanto para toda importação futura (US3) com o mesmo comando —
sem código duplicado entre "histórico" e "recorrente".

**Alternatives considered**: estender o script legado
`assets/finalcial/Financeiro/importar_extrato.py` (que já tem um branch "BB
Cristine XLSX" nunca exercitado) para gerar entradas em `registro.json` e
reusar `importar_historico_extrato.py` tal qual — rejeitado: esse script
vive fora do repositório do financiALL (é ferramenta pessoal legada da
pasta `assets/`), e a feature 010 já estabeleceu o padrão (b) como o
caminho recorrente oficial dentro do projeto.

## #3 — Nova dependência: `openpyxl` (extrato BB é `.xlsx`, não `.xls`)

**Decisão**: Adicionar `openpyxl` a `pyproject.toml` (`dependencies`).

**Rationale**: O parser Itaú existente usa `xlrd`, que só lê o formato
binário legado `.xls` (suporte a `.xlsx` foi removido do `xlrd` a partir da
v2.0). Os 5 arquivos reais de extrato do BB (`assets/finalcial/Financeiro/extrato/cristine/*.xlsx`)
são `.xlsx` (OOXML moderno). `openpyxl` já está presente no ambiente virtual
do projeto (usado ad-hoc nesta sessão para inspeção), mas não está
declarado como dependência formal — precisa ser adicionado.

**Alternatives considered**: converter os arquivos para `.xls` antes de
importar — rejeitado, adiciona um passo manual frágil ao fluxo recorrente
que o usuário precisa repetir a cada novo extrato (contraria US3/FR-011).

## #4 — Conta BB mapeada para identificador canônico terminado em `_cc`, reaproveitando sinal e janela de reconciliação já existentes

**Decisão**: Adicionar em `CONTA_CANONICA` (`src/services/conta_canonica.py`):
`"BB_Cristine": "bb_cristine_cc"`.

**Rationale**: `_interpretar_valor_e_tipo()` (`importar_historico_extrato.py`)
já trata contas cujo identificador canônico termina em `_cc` como conta
corrente: valor positivo = entrada, negativo = saída — exatamente a
convenção de sinal confirmada nos arquivos reais do BB (`E2='-500,00'`
= saída, `E3='2.500,00'` = entrada). `eh_conta_debito()`
(`src/services/conta_canonica.py`) também já usa esse mesmo sufixo `_cc`
para aplicar a janela de reconciliação de 3 dias (em vez dos 45 dias de
cartão) — a conta corrente do BB deve usar a mesma janela curta, pelo mesmo
motivo (correspondência quase imediata entre compra e lançamento em conta
corrente/débito). Resultado: **zero código novo** de interpretação de sinal
ou de janela de reconciliação — só uma entrada de dicionário.

**Alternatives considered**: interpretar o tipo a partir da coluna "Tipo
Lançamento" (Entrada/Saída) explícita no extrato do BB, em vez do sinal do
valor — equivalente na prática (os dois sempre concordam nos dados reais
inspecionados) e rejeitado por não reaproveitar `_interpretar_valor_e_tipo()`
existente; manter só como validação cruzada opcional no parser (`assert`/log
se um dia divergirem), não como fonte de verdade.

## #5 — Formato de valor e de descrição do extrato BB

**Decisão**:
- Valor: string em formato brasileiro (`"-500,00"`, `"2.500,00"`) →
  remover separador de milhar (`.`), trocar vírgula decimal por ponto,
  `float()`.
- Descrição: **concatenar "Lançamento" + "Detalhes"** (`"<Lançamento> -
  <Detalhes>"`), removendo o prefixo de timestamp `"dd/mm hh:mm "` de
  "Detalhes" quando presente (ex.: `"Pix - Enviado"` + `"02/01 13:50
  INSTITUTO CG CLIN ODONTOL"` → `"Pix - Enviado - INSTITUTO CG CLIN
  ODONTOL"`). Quando "Detalhes" vier vazio, usar só "Lançamento".

**Rationale (revisado após inspecionar os 5 arquivos reais na íntegra —
Princípio V)**: a primeira hipótese (usar só "Detalhes", já registrada
abaixo em "Alternatives considered") partia de amostras onde "Detalhes"
sempre carregava o nome do estabelecimento/contraparte (`"Pix - Enviado"` →
`"INSTITUTO CG CLIN ODONTOL"`). Inspecionando os 5 arquivos completos, achei
um contraexemplo real: a tarifa bancária mensal tem `Lançamento = "Tarifa
Pacote de Serviços"` e `Detalhes = "Cobrança referente 06/01/2026"` — nesse
caso é o "Lançamento" que carrega a informação útil, e "Detalhes" é só uma
data genérica. Usar somente "Detalhes" faria essa transação (recorrente
todo mês) perder toda identidade reconhecível. Concatenar os dois cobre
ambos os casos sem custo real: quando "Detalhes" já é a informação
relevante, o "Lançamento" na frente não atrapalha o match de regra por
substring (`\b<padrão>` ainda encontra o padrão em qualquer posição da
string).

**Alternatives considered**: usar só "Detalhes" com fallback para
"Lançamento" quando vazio — era a decisão original antes da inspeção
completa dos arquivos reais; abandonada pelo motivo acima (perde a
identidade da tarifa bancária e de qualquer outro lançamento onde
"Detalhes" for genérico). Concatenar sempre os dois, mesmo quando
redundante (ex.: `"BB Rende Fácil - Rende Facil"`), foi preferida a uma
lógica de deduplicação entre os dois campos (comparar se são
"parecidos") por simplicidade (Princípio I) — a leve redundância não
atrapalha nem a classificação nem a leitura na UI.

## #6 — Linhas não-transacionais do extrato BB

**Decisão**: Pular linhas cujo "Lançamento", depois de remover todo espaço
e colocar em minúsculas, seja `"saldoanterior"`, `"saldododia"` ou
`"saldo"`.

**Rationale**: Confirmado nos arquivos reais — existem **três** grafias de
linha de conferência de saldo, não duas: `"Saldo Anterior"` (primeira linha,
data válida do dia anterior ao período), `"Saldo do dia"` (uma por dia,
sempre com data `"00/00/0000"`) e **`"S A L D O"`** (letras espaçadas,
última linha de cada arquivo, com a **data e o valor válidos** do saldo de
fechamento — só descoberto inspecionando os 5 arquivos completos, não
apareceria numa amostra parcial). Como a terceira variante tem data válida,
checar só "data inválida" como sinal auxiliar (como cogitado inicialmente)
não a pegaria — por isso a decisão final normaliza o texto do "Lançamento"
(remove espaço, minúsculas) em vez de comparar contra strings com espaço
fixo, cobrindo as três grafias com uma lógica só.

## #7 — Titular fixo no parser, não inferido por heurística

**Decisão**: `parsear()` recebe/atribui `titular="cristine"` de forma fixa
(constante no módulo, não descoberta a partir do conteúdo do arquivo).

**Rationale**: Todo arquivo de extrato do BB da pasta `extrato/cristine/`
pertence à mesma e única conta dela — não há ambiguidade a resolver, e
inferir por heurística seria complexidade sem necessidade concreta
(Princípio I). Se um extrato do BB de outro titular precisar ser importado
no futuro, o padrão (parser dedicado por titular/formato) já comporta isso
sem mudança estrutural.

## #8 — Transferências entre o casal não devem distorcer o saldo conjunto

**Decisão**: Adicionar regras de natureza `transferencia_interna` para
padrões de descrição que identificam transferência para o cônjuge em ambos
os extratos (ex.: `"MARCELO RENATO GOMES"` no extrato da Cristine),
seguindo exatamente o mesmo mecanismo (`regra_natureza`/`cache_descricao_natureza`)
já usado para transferências internas do Marcelo entre suas próprias
contas — sem introduzir um conceito novo de "transferência entre titulares"
distinto de `transferencia_interna`.

**Rationale**: `saldo_do_mes()` (`resumo_service`) já exclui
`transferencia_interna` do cálculo de entradas/saídas — o mecanismo de
exclusão já existe e já é exatamente o comportamento desejado (FR-010): uma
transferência não é gasto nem renda "de verdade" para o casal, é só dinheiro
mudando de bolso. Cada lado da transferência (saída na conta de quem envia,
entrada na conta de quem recebe) é uma transação independente que precisa
ser classificada como `transferencia_interna` nos dois extratos — não é uma
entidade "transferência" única que precisa de reconciliação entre as duas
pontas (diferente de nota fiscal ↔ transação); double-counting já é evitado
simplesmente por nenhum dos dois lados contar como gasto/renda.

**Alternatives considered**: modelar transferência entre titulares como uma
entidade própria com link entre as duas transações (como a reconciliação
nota↔transação) — rejeitado por complexidade desnecessária: não há nenhum
requisito de navegação "ver a outra ponta da transferência", só de não
distorcer o saldo, que a natureza `transferencia_interna` já resolve
sozinha.

**Achado de dado real**: o nome do Marcelo aparece truncado de formas
diferentes em "Detalhes" conforme o tipo de lançamento do BB — `"MARCELO
RENATO GOMES"` completo em Pix, `"...MARCELO RENATO GO"` cortado em TED, e
`"...MARCELO REN"` cortado ainda mais em Pix recebido (limite de caracteres
do campo, não erro de digitação). O padrão semeado usa o prefixo comum mais
curto, `"MARCELO REN"`, para cobrir as três variantes observadas em vez de
`"MARCELO RENATO GOMES"` completo, que perderia as duas truncadas.

## #9 — Regras de natureza semente para o vocabulário da Cristine

**Decisão**: Adicionar entradas a `src/scripts/regras_semente_natureza.json`
cobrindo os padrões recorrentes já identificados no extrato real dela (CDC
BB, Consignação BB, salário via "SECRETARIA MUNICIPAL DA FAZENDA", CRB,
Tarifa Bancária BB, etc.), usando `Cristine.xlsx` (aba por mês, tabela
"LANÇAMENTOS REAIS") como gabarito de categoria/natureza já validado
manualmente por ela.

**Rationale**: Mesma abordagem já usada na feature 010 (research.md #5) para
elevar a taxa de classificação automática do Marcelo de 67% para 78% — sem
isso, toda transação da Cristine cairia em revisão manual (`/ver/transacoes/pendentes`),
o que ainda funciona mas não entrega o valor de "mostrar automaticamente o
que foi gasto e em quê" pedido pelo usuário.

**Alternatives considered**: nenhuma — regra semente é o mecanismo já
estabelecido pelo projeto para esse problema, sem necessidade de avaliar
alternativas.

## #10 — Filtro por titular no resumo mensal espelha o padrão já usado em `/ver/notas`

**Decisão**: Adicionar parâmetro `titular: str | None = None` às funções
relevantes de `src/services/resumo.py` (`resumo_de_mes`, `saldo_do_mes`,
`gasto_por_categoria_item`, `gasto_por_estabelecimento`) e a
`storage_db.listar_transacoes` (que já aceita filtros compostos por
querystring, ex.: `categoria_id`). Em `/ver/resumo`
(`routes_consulta.py::pagina_resumo`), ler `titular` de `request.args` e
repassar. Na UI, reaproveitar o mesmo componente de botões "Todos / Marcelo
/ Cristine" que `notas.html` já implementa (`titular_filtro`).

**Rationale**: `/ver/notas` já implementa esse exato padrão de filtro
(`titular_filtro`, botões de seleção, querystring `?titular=`) — reaproveitar
em vez de inventar um mecanismo novo (Princípio I). `NotaFiscal.titular` e
o novo `Transacao.titular` usam o mesmo conjunto de valores
(`TITULARES_VALIDOS`), então o mesmo componente de UI serve para os dois.

**Alternatives considered**: dashboard separado por titular (rota própria
`/ver/resumo/marcelo`, `/ver/resumo/cristine`) — rejeitado, quebra a
convenção de filtro por querystring já usada em toda a aplicação
(`/ver/notas`, `/ver/transacoes`, `/ver/itens`).
