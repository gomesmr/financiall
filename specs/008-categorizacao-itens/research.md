# Research: Categorização de Itens de Nota Fiscal

## 1. Normalização da descrição (Tier 0) — sem dependência nova

**Decisão**: `normalizar_descricao(descricao) -> str` faz: maiúsculas,
remoção de acentuação via `unicodedata.normalize("NFKD", ...)` (stdlib,
sem dependência nova), colapso de espaços múltiplos. Um dicionário pequeno
de expansão de abreviações (`REFRIG→REFRIGERANTE`, `FGO→FRANGO`, etc.) é
incluído desde o v1, mas **curado a partir do corpus real** (`assets/
files.zip/corpus-descricoes-produtos.txt`, 760 descrições originais,
reduzidas a 330 em `tests/fixtures/corpus_descricoes_produtos.txt` —
Tarefa 1, decisão de implementação: sem código de barras/NCM nesta
feature, a granularidade de SKU/tamanho/quantidade do corpus original não
agrega valor de teste; a redução manteve uma linha por combinação única
de estilo de escrita × marca, preservando toda a variedade real de
formato que a normalização precisa suportar), não como uma lista
genérica especulativa — só entram abreviações que o corpus comprova
serem comuns.

**Rationale**: acentuação e maiúsculas/minúsculas inconsistentes entre
lojas são a causa mais direta de cache miss desnecessário (a mesma compra
"Refrigerante" vs "REFRIG" vs "Refrig."); resolver isso no Tier 0 é o que
faz o cache (Tier 1) valer a pena. Ficar restrito ao corpus real evita
especular abreviação que nunca aparece na prática (Princípio I).

**Alternatives considered**: biblioteca `unidecode` para remoção de
acentos — rejeitada por ser uma dependência nova só para o que
`unicodedata` (stdlib) já resolve.

## 2. Onde persiste a descrição normalizada

**Decisão**: `item_nota` ganha a coluna `descricao_normalizada` (calculada
uma vez, no momento da classificação, e armazenada) — não recalculada a
cada consulta.

**Rationale**: a fila de pendentes precisa agrupar por descrição
normalizada via SQL (`GROUP BY`) para ser performática e simples de
consultar; recalcular a normalização em Python para cada linha a cada
carregamento de página seria redundante e mais lento sem necessidade —
mesmo padrão de "calcular uma vez, guardar" já usado em
`categoria.nome_normalizado` (feature 003).

## 3. Extensão do schema de `categoria`: hierarquia de 2 níveis

**Decisão**: `categoria` ganha `parent_id INTEGER REFERENCES
categoria(id)` (`NULL` = categoria de topo) via `ALTER TABLE` idempotente
(mesmo padrão de `_garantir_coluna_categoria_id` da feature 003). A
restrição "exatamente 2 níveis" (subcategoria não pode ter uma
subcategoria-filha) é validada na camada de serviço, não em `CHECK` do
SQL — mesma decisão já tomada para validação de `titular` (feature 004,
"validação de valor fica na camada de serviço, não em CHECK do schema").
Categorias já existentes (todas hoje sem hierarquia) viram automaticamente
categorias de topo (`parent_id = NULL`), sem migração de dado necessária.

**Rationale**: reaproveita a tabela `categoria` já existente e usada por
`nota_fiscal.categoria_id` (feature 003) em vez de criar uma tabela
paralela — a taxonomia continua sendo uma só para nota E item, como o
Princípio "ALL" da constituição exige.

## 4. Tabelas novas

**Decisão**: três tabelas novas, todas via `CREATE TABLE IF NOT EXISTS`:

- `cache_descricao_categoria(descricao_normalizada TEXT PRIMARY KEY,
  categoria_id INTEGER NOT NULL REFERENCES categoria(id))` — a "verdade
  atual" de classificação para uma descrição; upsert, nunca acumula
  histórico (histórico vive em `historico_classificacao_item`).
- `regra_categoria(id, padrao TEXT NOT NULL, categoria_id INTEGER NOT
  NULL REFERENCES categoria(id), prioridade INTEGER NOT NULL DEFAULT 0,
  ativa INTEGER NOT NULL DEFAULT 1)` — regras-semente, carregadas por
  script/fixture (Tarefa 1), não por uma tela de CRUD nesta versão
  (Assumptions do spec: sem sugestão automática de regra em v1).
- `historico_classificacao_item(id, item_nota_id INTEGER NOT NULL
  REFERENCES item_nota(id), categoria_id_anterior INTEGER,
  categoria_id_nova INTEGER, metodo TEXT NOT NULL, timestamp TEXT NOT
  NULL)` — trilha de auditoria (FR-014), append-only.

**Rationale**: entidades distintas do spec (data-model.md detalha cada
uma) — separar cache de histórico evita que uma tabela de auditoria
cresça sem limite vire também o caminho de leitura quente (toda
classificação de item consulta o cache primeiro).

## 5. Tipo de casamento de regra: token com fronteira, sem regex no v1

**Decisão**: `regra_categoria.padrao` é sempre casado como
token/palavra com fronteira (`\bPADRAO\b` sobre a descrição normalizada) —
**sem** um campo `tipo_match` (token vs. regex) distinguindo os dois. Todo
padrão é tratado da mesma forma.

**Rationale**: o brief de preparação explorava `tipo_match` com regex cru
"só como exceção documentada" — mas nenhuma regra-semente do v1 precisa
de regex (o corpus real não exigiu isso na prática), e carregar uma
distinção de tipo que nunca é exercitada é complexidade especulativa
(Princípio I). Se uma regra futura genuinamente precisar de regex, o
campo pode ser adicionado então (não é uma migração cara).

## 6. Prioridade de regra (mais específica vence)

**Decisão**: `prioridade` é um inteiro explícito, atribuído por quem cura
a regra-semente (maior número = mais específica, vence em caso de duas
regras casarem o mesmo item). Em empate de prioridade, o desempate é pela
regra de menor `id` (mais antiga) — comportamento determinístico, mas a
curadoria deve evitar empates de propósito.

**Rationale**: inferir "especificidade" automaticamente a partir do
padrão (ex.: padrão mais longo = mais específico) adicionaria lógica não
trivial para um ganho pequeno, já que as regras-semente são poucas e
curadas manualmente (Tarefa 1) — um campo explícito é mais simples e mais
previsível de auditar.

## 7. "Regra aprovada" simplificado para v1

**Decisão**: o schema usa `ativa` (booleana), não `aprovada` com um fluxo
de aprovação. Toda regra-semente é, por definição, curada manualmente
antes de entrar no repositório — não existe, nesta versão, um caminho de
regra "sugerida" que precise de aprovação (isso só nasce com a
auto-sugestão de regras, explicitamente fora do escopo — Assumptions do
spec). "Regra aprovada" no texto do spec (FR-007) equivale, na
implementação, a "regra com `ativa = 1`".

**Rationale**: evita construir um fluxo de aprovação (tela, estado,
permissão) que não tem nenhum produtor de regra "não aprovada" para
consumir nesta versão — complexidade sem uso real ainda (Princípio I).

## 8. Onde a cascata de classificação roda

**Decisão**: um serviço novo, `src/services/classificacao_itens.py`, com
`classificar_itens_pendentes_da_nota(nota_fiscal_id, db_path)`, chamado
logo após a inserção de itens nos três pontos já existentes que inserem
`item_nota`: `services/importador.py` (fluxo URL/chave e foto/PDF,
`inserir_itens`) e `services/importar_historico.py` (`inserir_nota_com_itens`).
A função é idempotente por construção: só atua sobre itens com
`categoria_id IS NULL` da nota informada — chamar de novo (reprocessamento,
FR-015) não reclassifica nem duplica nada já classificado.

**Rationale**: mantém a inserção de item (já testada, features 001/004)
intocada — classificar é uma responsabilidade separada que roda depois,
mesmo padrão de composição em etapas distintas já usado no projeto (ex.:
upload enfileira, decodifica, then importa — feature 001). A
idempotência por "só atua sobre `categoria_id IS NULL`" também cobre de
graça o backlog histórico (research.md #9) e o reprocessamento de nota
(Princípio II), sem lógica extra de deduplicação.

## 9. Backlog do histórico já importado

**Decisão**: nenhuma migração em lote é necessária no deploy — todo item
já existente hoje já tem `categoria_id IS NULL` (a coluna nem existe
ainda), então passa a aparecer na fila de pendentes automaticamente assim
que a coluna é criada. Rodar a cascata cache/regra sobre esse backlog
(para reduzir o volume manual antes de começar a rotular) é a mesma
função `classificar_itens_pendentes_da_nota`, chamada para cada nota
existente — uma tarefa de ativação (`tasks.md`), não uma migração de dado
com lógica própria.

**Rationale**: reaproveita a mesma função de classificação em vez de
escrever um script de migração paralelo — menos código, e a garantia de
comportamento idêntico entre "nota nova" e "nota antiga sendo classificada
pela primeira vez" (mesma cascata, mesmas regras).

## 10. Cache é alimentado por qualquer classificação confirmada, não só manual

**Decisão**: sempre que um item recebe uma categoria — por regra OU
manualmente — o resultado é gravado (upsert) em
`cache_descricao_categoria`. Uma correção manual sobrescreve o que já
estava lá.

**Rationale**: simplifica o "tier 1 > tier 2" do brief de preparação — em
vez de o cache só nascer de rótulo manual, ele nasce da primeira
classificação bem-sucedida de qualquer descrição nova, por qualquer
método. Efeito prático: uma regra só precisa re-casar cada descrição
única uma vez; da segunda ocorrência em diante, o cache (mais barato,
`O(1)` por chave primária) resolve — sem mudar o resultado (a categoria é
a mesma), só evita recasar a mesma regra repetidamente. Também unifica o
código: só existe um caminho de escrita no cache, não dois.

## 11. "Corrigir a fonte" (FR-013) opera no nível do cache, não da regra

**Decisão**: a ação "corrigir a fonte e reclassificar o passado" sempre
atualiza `cache_descricao_categoria` para a descrição normalizada do item
corrigido (independente de o item ter sido classificado originalmente por
regra ou por cache), e então atualiza em lote todos os `item_nota` com a
mesma `descricao_normalizada` **e** a mesma `categoria_id` (antiga,
incorreta) para a nova categoria — a prévia de impacto (FR-013, SC-006) é
a contagem desses itens antes de aplicar.

**Rationale**: editar `regra_categoria.categoria_id` diretamente seria
arriscado — uma regra pode casar várias descrições diferentes, e mudar seu
destino afetaria itens não relacionados ao que o usuário está corrigindo.
Corrigir no nível do cache (por descrição exata) tem o raio de efeito que
o usuário realmente pediu (só ocorrências passadas *daquela descrição*),
e passa a valer para o futuro porque o cache (Tier 1) sempre vence sobre
regra (Tier 2) — mesma precedência do research.md #10, sem precisar tocar
na regra-semente.

## 12. Exclusão de categoria/subcategoria com destino explícito

**Decisão**: `DELETE /categorias/<id>` passa a exigir, quando há
referências em uso, um corpo `{"destino": "substituta" | "pendente",
"categoria_substituta_id": <id ou omitido>}`. Uma função nova,
`calcular_impacto_exclusao(categoria_id)`, retorna a contagem de itens,
entradas de cache e regras afetadas, exposta via `GET
/categorias/<id>/impacto-exclusao` para o cliente montar a prévia antes de
deixar o usuário confirmar. Exclusão de categoria de topo com
subcategorias é bloqueada (`422`) antes mesmo de calcular impacto —
FR-017.

**Rationale**: implementa a decisão da clarificação do spec — nunca um
destino automático e silencioso quando há referências em uso. Categoria
substituta, quando escolhida, deve ser do mesmo nível (topo↔topo,
subcategoria↔subcategoria) — validado na camada de serviço, mesmo
raciocínio de "2 níveis fixos" do research.md #3.

## 13. Segunda barreira do Princípio V — dimensões de variação real

A cascata de classificação processa descrição de item de NFC-e — texto
vindo de fonte externa (OCR ou scraping de portal), já coberto pelo
Princípio V como "qualquer parsing de formato não controlado pelo
projeto". Dimensões de variação real identificadas para a validação
obrigatória antes de promover:

1. **Amostra real do corpus** (`corpus-descricoes-produtos.txt`, 330
   descrições — reduzidas das 760 originais para uma linha por
   combinação única de estilo de escrita × marca, já que sem código de
   barras/NCM nesta feature a repetição de tamanho/quantidade da mesma
   marca não agregava sinal de teste novo) — ainda enviesado para papel
   higiênico (153 das 330); serve para testar robustez do normalizador e
   semear regras de Higiene, **não** para medir taxa de pendente
   representativa (o corpus não é uma cesta
   de compra típica).
2. **Notas reais já importadas no Pi (dev)** — itens do backlog histórico
   real (features 001/004), com a variedade de lojas/formatos de
   descrição que o corpus sintético não cobre — usado para medir a taxa
   de "pendente" por nota de verdade antes de promover.
3. **Rotulagem manual real do usuário** — a via primária de classificação
   do v1; validar que uma correção feita na tela de revisão realmente
   resolve as demais ocorrências pendentes da mesma descrição (US1
   cenário 2), não só em teste sintético.

## 14. Princípio VIII — superfícies visuais novas

**Decisão**: duas superfícies novas exigem verificação visual real
(captura headless + checagem de erro de console) antes de promover: a
fila de pendentes (`/ver/pendentes`) e a extensão de `/ver/categorias`
(hierarquia, criar subcategoria, exclusão com prévia/destino). Nenhum
asset de terceiro novo é vendorizado (reaproveita Bootstrap/Argon já
presentes no projeto) — a cláusula de integridade de asset de terceiro do
Princípio VIII não se aplica a esta feature.

## 15. Atribuir a um item pendente resolve os demais da mesma descrição

**Decisão**: `atribuir_categoria_manual` (usada por `PUT
/itens/<id>/categoria`) sempre resolve, de graça, todos os outros itens
ainda pendentes com a mesma `descricao_normalizada` — o mesmo efeito de
`classificar_grupo_pendente` (`POST /itens/pendentes/classificar-grupo`),
que passa a ser a mesma operação de fundo, só entrando pela descrição em
vez de por um item. Esse efeito só dispara quando o item de origem
estava pendente; corrigir um item já classificado (US4) nunca afeta
outros itens.

**Rationale**: é o que a spec descreve literalmente no cenário 2 da
User Story 1 — atribuir categoria a um item da fila já resolve "todos os
demais itens pendentes com a mesma descrição normalizada", sem exigir
uma ação de lote separada. Deixar de fora esse efeito colateral em
`atribuir_categoria_manual` faria o caminho mais comum de uso (clicar um
item da fila) não cumprir o cenário de aceite — só o endpoint de lote
cumpriria. Não há risco de mutação-em-massa-silenciosa (Princípio II)
aqui porque os itens afetados estavam todos **sem** categoria antes
(nenhum dado existente é sobrescrito às escondidas, diferente de
"corrigir a fonte", research.md #11, que exige prévia por afetar itens
já classificados).

## 16. Seleção de categoria/subcategoria: autocomplete de campo único, sem endpoint novo

**Decisão**: o cliente carrega a lista completa de categorias (`GET
/categorias`, já existente) uma vez e oferece um único campo de
autocomplete que filtra no navegador conforme o usuário digita, listando
tanto categorias de topo quanto subcategorias (rotuladas como
"Categoria" ou "Categoria › Subcategoria"). Ao escolher uma subcategoria,
a categoria-pai é exibida automaticamente a partir do `parent_id` do item
escolhido — sem um segundo campo/select dependente. Escolher diretamente
uma categoria de topo é a classificação parcial do FR-011. Sempre um
único `categoria_id` enviado à API (contracts/api.md).

**Rationale**: a taxonomia é pequena (dezenas de categorias/subcategorias
— Technical Context do plan.md), então filtrar no navegador é
suficiente; um endpoint de busca no servidor seria complexidade sem
necessidade real (Princípio I). Também é mais simples de implementar que
dois `<select>` em cascata (categoria → filtra subcategorias → popula o
segundo), que exigiriam a mesma lista completa carregada no cliente de
qualquer forma para popular o primeiro select.

**Alternatives considered**: dois campos dependentes (select de
categoria, depois select de subcategoria filtrado pelo pai escolhido) —
rejeitado por exigir mais código de UI que o autocomplete único para o
mesmo resultado, e por tornar a classificação parcial (escolher só a
categoria) um caminho especial em vez do comportamento natural de
"parar de digitar antes de entrar numa subcategoria".

## 17. Sem categoria fallback "Outros" — item sem categoria clara fica pendente

**Decisão**: a taxonomia-semente (T001) não inclui nenhuma categoria ou
subcategoria "Outros" / "não classificado". Um item que não se encaixa
claramente em nenhuma categoria definida simplesmente permanece
**pendente** (`categoria_id IS NULL`) — já um dos dois estados finais
válidos por SC-001, não uma pendência a ser forçosamente resolvida.

**Rationale**: uma categoria "Outros" correria dois riscos, dependendo
de como fosse usada — (a) virar destino automático de cache/regra,
esvaziando o valor de revisão humana que sustenta o flywheel do v1
(mesmo risco já descartado para a classificação automática, FR-008); ou
(b) virar uma escolha manual redundante com a classificação parcial já
existente (FR-011 — categoria definida, subcategoria pendente), que já
cobre "sei a categoria, não quero precisar mais". O rascunho original
tinha "Outros" tanto como categoria de topo quanto repetido como
subcategoria em mais de uma categoria-pai (Higiene, Bebê) — essa segunda
forma só passou a ser representável depois da correção do índice único
em research.md #19; mesmo assim, "Outros" continua fora da
taxonomia-semente, e não só por causa do schema — evita sobretudo a
ambiguidade "categoria=Outros, subcategoria=Outros" e o risco de virar
destino automático (parágrafo acima). Se um padrão real de itens
genuinamente incategorizáveis aparecer com o uso, uma categoria dedicada
pode ser criada depois via a gestão de taxonomia (US5) — não há
necessidade de antecipar isso agora (Princípio I).

## 18. Criar subcategoria inline a partir do autocomplete de classificação

**Decisão**: o campo de classificação (research.md #16) é sempre um
campo de **subcategoria** — selecionar diretamente uma categoria de topo
já existente da lista continua sendo a classificação parcial do FR-011,
sem passar por este fluxo. Quando o nome digitado não corresponde a
nada na lista carregada, e o usuário dá Enter, o cliente pergunta a
categoria-pai da subcategoria nova: (a) escolher uma categoria-pai **já
existente**, ou (b) digitar o nome de uma categoria-pai **nova** (cria a
categoria de topo e a subcategoria em sequência) — nunca um default
silencioso. A confirmação chama o `POST /categorias` já existente
(`parent_id` + aviso de quase-duplicata do FR-002/T045, contracts/api.md)
— nenhum endpoint novo, uma chamada para o pai (só quando novo) e uma
para a subcategoria. Em sucesso (ou depois de resolver um aviso de
quase-duplicata), a subcategoria criada já fica selecionada para o item,
completando a classificação numa ação só.

Criar uma categoria de topo **sem** nenhuma subcategoria continua sendo
exclusivo da gestão de taxonomia (`/ver/categorias`, US5/T050) — este
fluxo inline nunca cria uma categoria de topo isolada.

**Rationale**: reduz o atrito de trocar de tela (ir até
`/ver/categorias`, criar, voltar) no meio de uma sessão de revisão de
pendentes — sem exigir nenhuma lógica nova de servidor, já que
`POST /categorias` já cobre `parent_id` e quase-duplicata. Manter o
fluxo inline restrito a "criar subcategoria (com pai existente ou novo)"
em vez de deixar "categoria de topo isolada" também nascer daqui separa
as duas naturezas de decisão: adicionar um detalhe fino durante a
classificação de um item é uma ação leve e frequente; criar uma
categoria de orçamento nova do zero é uma decisão estrutural da
taxonomia, deliberada, que pertence à tela de gestão dedicada (US5) — a
escolha explícita de pai (em vez de inferir) segue o mesmo espírito do
Princípio II citado em research.md #12: nenhuma decisão estrutural da
taxonomia acontece de forma implícita/silenciosa.

## 19. Índice único de `categoria.nome_normalizado` escopado por nível

**Decisão**: substituir o índice único global (feature 003) por dois
índices únicos parciais — nome único entre categorias de topo
(`parent_id IS NULL`), nome único só dentro do mesmo `parent_id` para
subcategorias — mesmo padrão de índice parcial já usado no projeto
(`idx_nota_fiscal_chave_acesso ... WHERE chave_acesso IS NOT NULL`). Ver
data-model.md.

**Rationale**: deixou de ser bloqueante depois de research.md #17
remover "Outros" (o único caso concreto de nome repetido entre pais
diferentes na taxonomia-semente), mas continua valendo como correção
defensiva: sem ela, a taxonomia nunca poderia reaproveitar o mesmo nome
de subcategoria embaixo de categorias-pai diferentes no futuro — uma
restrição arbitrária que o schema não deveria impor. Seguro para o dado
de produção existente (research.md #3): toda categoria hoje é de topo,
então a troca de índice é comportamentalmente equivalente até a primeira
subcategoria ser criada.

**Alternatives considered**: `UNIQUE(parent_id, nome_normalizado)` como
índice composto único (sem parcial) — rejeitado porque SQLite trata cada
`NULL` como distinto em índice único, então não impediria categorias de
topo duplicadas (o problema original que o índice de nomes já existe
para evitar); `COALESCE(parent_id, 0)` — funcionaria, mas o índice
parcial é mais explícito e já é o padrão do projeto.

## 20. Item sem descrição vai direto para pendente

**Decisão**: `classificar_item` (research.md #8) trata `descricao`
`None` ou vazia (após `strip()`) como um caso especial que **não** passa
pelo Tier 0/1/2 — vai direto para pendente, sem tentar normalizar nem
casar cache/regra.

**Rationale**: `item_nota.descricao` já é nullable hoje (falha do OCR ao
extrair aquela linha é um caminho real, não hipotético — mesma
degradação graciosa já aplicada a outros campos ausentes do item).
Tentar normalizar `None` quebraria a cascata; tratar como pendente é
consistente com o resto do desenho — "sem informação suficiente para
decidir" é exatamente o caso que "pendente" existe para cobrir (FR-008),
sem precisar de um caminho de erro separado (Princípio III: aqui não é
uma entrada externa malformada exigindo tratamento de exceção, é
ausência de dado já esperada e já modelada como nullable).

## 21. Resumo observável na fila de pendentes (SC-002)

**Decisão**: `GET /itens/pendentes` retorna também um resumo agregado —
total de itens pendentes e total de itens já classificados — e
`/ver/pendentes` exibe essa contagem no topo da página (ex.: "42
pendentes de 310 itens no total"). Nenhum endpoint novo: é um campo a
mais na resposta já prevista (contracts/api.md), derivado de uma
contagem simples sobre `item_nota` (`categoria_id IS NULL` vs. total).

**Rationale**: SC-002 ("a fração de itens classificados automaticamente
cresce ao longo do tempo") não tinha, antes desta decisão, nenhum jeito
de o usuário observar essa tendência — só uma checagem pontual durante a
Real-Data Validation de US3 (research.md #13). O resumo agregado é o
retrato do instante (barato, já vem de graça na mesma consulta de
`listar_itens_pendentes`); a evolução ao longo do tempo — o pedido real
por trás de SC-002 — é o gráfico de research.md #22, que complementa este
resumo sem substituí-lo.

## 22. Gráfico de evolução (burndown) — itens totais vs. classificados

**Decisão**: `/ver/pendentes` ganha um gráfico de linhas com duas séries
cumulativas: **itens totais** (um ponto por evento de importação de nota,
usando `nota_fiscal.data_importacao`) e **itens classificados** (um ponto
por item na primeira vez que aparece em `historico_classificacao_item`,
usando o menor `timestamp` por `item_nota_id`). Nenhum bucket fixo de
tempo (dia/semana/mês): as duas linhas plotam os eventos reais como uma
função em degrau cumulativa — o espaçamento no eixo X já reflete o ritmo
real de uso, sem precisar escolher nem trocar de granularidade conforme o
histórico cresce. Mostra todo o histórico disponível por padrão; zoom/pan
para recortes menores é o comportamento interativo padrão do Plotly, sem
seletor de datas customizado. A distância vertical entre as duas linhas
em cada ponto no tempo é o backlog pendente naquele momento — abrindo
("boca do jacaré") quando o backlog cresce, fechando quando é absorvido.

Dado calculado por uma função nova em `src/services/classificacao_itens.py`
(consulta própria via `storage_db.get_connection`, mesmo padrão de
`services/resumo.py`/`_query_resumo_por_mes` — não delegado a
`storage/db.py`, por ser leitura agregada de relatório, não CRUD de
repositório). Entregue à página via renderização do lado do servidor
(`{{ ... | tojson }}` no Jinja, mesmo padrão de `resumo.html` — feature
005), **não** como campo do `GET /itens/pendentes` (contracts/api.md):
são dados de gráfico carregados junto com a página, não parte da API de
listagem de pendentes.

**Rationale**: reaproveita a mesma infraestrutura de gráfico já
vendorizada pela feature 005 (`plotly-basic.min.js`) — nenhum asset novo
(Princípio VIII continua sem se aplicar) nem dependência nova (Princípio
I). Nenhuma coluna/tabela nova: os dois eixos são derivados de colunas já
existentes (`nota_fiscal.data_importacao`, já na feature 001;
`historico_classificacao_item.timestamp`, já nesta feature). Evitar
bucket fixo evita também o problema oposto de escolher mal a
granularidade: diário ficaria esparso demais dado o volume baixo da app
("poucas notas por mês", Technical Context do plan.md); mensal esconderia
justamente o sinal que se quer ver logo nas primeiras semanas depois do
deploy (o backlog inicial grande começando a fechar); um mecanismo de
auto-troca de escala conforme o histórico cresce seria complexidade sem
necessidade real comprovada ainda (Princípio I) — o efeito colateral de
plotar eventos crus é que backlog resolvido em massa (ex.: uma sessão de
revisão que zera 50 pendentes) aparece como um degrau visível, exatamente
o sinal que um bucket grosso apagaria.

**Alternatives considered**: agregação por semana/mês fixa — rejeitada
pelos motivos acima; granularidade adaptativa (trocar de escala conforme
o range de dados) — rejeitada por complexidade especulativa sem
necessidade demonstrada (app pessoal, volume baixo); endpoint JSON
dedicado para o gráfico — rejeitado em favor de renderização server-side
direto na página, mesmo padrão já usado por `resumo.html`, sem endpoint
novo.
