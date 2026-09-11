# Research: Log de classificação manual de natureza

## #1 — Onde interceptar para cobrir os dois caminhos (grupo e individual)

**Decision**: instrumentar `storage_db.classificar_grupo_pendente_natureza()`
e `storage_db.atribuir_natureza_manual()` diretamente, em `src/storage/db.py`
— os dois únicos pontos de convergência da classificação manual de
natureza (ambos, e só eles, chamam `classificar_natureza_transacao()`
com `metodo="manual"`).

**Rationale**: mesmo raciocínio da feature 014 (research.md #1) —
instrumentar o ponto de convergência já existente evita duplicar lógica
de log nas duas rotas (`POST /transacoes/pendentes/classificar-grupo` e
`PUT /transacoes/<id>/natureza`) e cobre automaticamente qualquer chamador
futuro dessas duas funções, sem precisar lembrar de adicionar o log de
novo (Princípio I). Confirmado por grep: `classificar_natureza_transacao()`
só é chamada a partir desses dois pontos — nenhuma classificação
automática (cache/regra, aplicada durante a importação) passa por eles,
então não há risco de logar classificação automática como manual.

**Alternatives considered**:
- Instrumentar dentro de `classificar_natureza_transacao()` (a função
  mais interna, chamada por ambos): rejeitado — ela é chamada uma vez
  por transação dentro do laço de `classificar_grupo_pendente_natureza`,
  então logaria um evento por transação individual em vez de um evento
  por ação em grupo (contradiz FR-002: quantidade de transações afetadas
  por evento).
- Instrumentar nas rotas Flask (`routes_transacoes.py`): rejeitado pelo
  mesmo motivo da feature 014 — duplicaria a decisão de "o que logar" em
  cada rota, quando as funções de storage já são o ponto único de
  verdade sobre o que de fato mudou no banco.

## #2 — Como representar o "alvo" (grupo vs. individual) numa única tabela

**Decision**: duas colunas nullable, `alvo_descricao_normalizada` e
`alvo_transacao_id`. Classificação em grupo preenche só a primeira;
classificação individual preenche as duas (a descrição normalizada da
transação também é conhecida nesse caminho, e mantê-la ajuda a
correlacionar eventos de grupo e individuais da mesma descrição).

**Rationale**: os dois caminhos têm identificadores de alvo
estruturalmente diferentes (uma string de agrupamento vs. um id
numérico) — nenhum dos dois sozinho cobre os dois casos sem ambiguidade.
Manter ambas as colunas, uma delas sempre nula dependendo do método, é
mais simples que uma coluna genérica tipo "alvo: str" que exigiria
parsing/convenção para diferenciar os dois formatos (Princípio I).

**Alternatives considered**:
- Uma única coluna `alvo` (texto livre): rejeitado — obrigaria a página
  de histórico a inferir se o valor é um id ou uma descrição, frágil e
  sem necessidade real.

## #3 — Não logar quando nada foi afetado ou a validação recusou

**Decision**: o evento só é gravado depois que a operação já confirmou
sucesso real: `classificar_grupo_pendente_natureza()` só loga se
`len(ids) > 0`; `atribuir_natureza_manual()` só loga no ramo que retorna
`True` (depois da validação de natureza e da existência da transação já
terem passado).

**Rationale**: atende FR-005/FR-006 diretamente — um evento de histórico
deve significar "isso realmente aconteceu", não "isso foi tentado". Como
as duas funções já retornam informação suficiente para saber se algo
mudou (quantidade de ids, ou `None`/`False`/`True`), não é necessário
nenhum cálculo novo além do que a função já faz.

## #4 — Persistência: mesma tabela ou tabela nova?

**Decision**: tabela nova, `log_classificacao_manual`, mesmo padrão
repositório (`db.py` + dataclass em `models/`) já usado por
`log_importacao` (feature 014) e `compromisso_futuro`.

**Rationale**: escopo e ciclo de vida diferentes de `log_importacao`
(um é sobre execução de importação de arquivo, outro sobre uma ação de
classificação manual) — misturar as duas na mesma tabela exigiria campos
opcionais demais e uma coluna de "tipo de evento" só para diferenciar,
mais complexo que duas tabelas simples e específicas (Princípio I).
`historico_classificacao_item` (item de nota fiscal) permanece um
terceiro histórico separado, fora de escopo desta feature (Assumptions
da spec).

**Alternatives considered**:
- Reaproveitar `historico_classificacao_item`: rejeitado — é sobre
  `item_nota`, não `transacao`; forçar o reaproveitamento exigiria
  tornar `item_nota_id` opcional e adicionar campos que não fazem
  sentido para esse histórico (quantidade afetada, método em
  grupo/individual), degradando um schema que já funciona bem para seu
  propósito original.
