# Research: CRUD de Categorias

Não há `NEEDS CLARIFICATION` no Technical Context — a feature reaproveita
integralmente a stack já validada nas features 001/002 (Flask + SQLite +
pytest). As decisões abaixo resolvem escolhas de implementação levantadas
pela spec.

## 1. Adicionar `categoria` e `nota_fiscal.categoria_id` sem ferramenta de migração

**Decisão**: a tabela `categoria` é criada via `CREATE TABLE IF NOT
EXISTS` (igual às tabelas existentes). A coluna nova `categoria_id` em
`nota_fiscal` é adicionada via um passo idempotente em `init_db()`: checar
`PRAGMA table_info(nota_fiscal)` por uma coluna chamada `categoria_id` e,
se ausente, rodar `ALTER TABLE nota_fiscal ADD COLUMN categoria_id INTEGER
REFERENCES categoria(id)`.

**Rationale**: o banco de produção e de desenvolvimento no Raspberry Pi já
existem com dados reais, criados pelo schema atual sem essa coluna.
`CREATE TABLE IF NOT EXISTS` não altera uma tabela já criada. O projeto
não usa Alembic nem outra ferramenta de migração (Princípio I —
simplicidade, sem dependência nova para um caso de uso pontual). Esse é o
mesmo raciocínio já registrado em research.md #1 da feature 002 para a
cascata de exclusão — reaproveitado aqui por consistência.

**Alternatives considered**: recriar a tabela `nota_fiscal` do zero
(copiar dados, dropar, recriar com a coluna nova) — rejeitada por
complexidade desproporcional ao ganho; introduzir Alembic — rejeitada por
adicionar uma dependência nova e uma camada de abstração (migrações
versionadas) que este projeto de uso pessoal não precisa agora.

## 2. Unicidade de nome de categoria — índice único, não só checagem em app

**Decisão**: a tabela `categoria` guarda `nome` (como o usuário digitou,
para exibição) e uma coluna `nome_normalizado` (gerada em Python:
`nome.strip().casefold()`) com índice único. Toda escrita (criar/editar)
calcula `nome_normalizado` antes de gravar; o índice único é a garantia
final contra duplicata.

**Rationale**: `COLLATE NOCASE` do SQLite só dobra maiúsculas/minúsculas
do intervalo ASCII (A-Z) — não cobre acentuação comum em português
("Alimentação" vs "alimentação" funcionaria, mas "Ó" vs "ó" não, por
exemplo, dependendo da build do SQLite). `str.casefold()` do Python trata
Unicode corretamente, então a normalização acontece em Python antes de
gravar, e o índice único no banco garante a regra mesmo sob as 4 threads
do `waitress` (research.md da feature 001, #14) — mesmo padrão de defesa
em profundidade já usado para `chave_acesso`/`hash_conteudo` de
`nota_fiscal` (checagem em `services/` + índice único parcial no banco).

**Alternatives considered**: só checagem em nível de aplicação
(`SELECT` antes de `INSERT`, sem índice único) — rejeitada por não ter a
mesma garantia sob concorrência que o resto do projeto já assume como
padrão; `COLLATE NOCASE` puro — rejeitado por não cobrir acentuação
portuguesa corretamente.

## 3. Excluir categoria em uso — desassociação explícita em transação

**Decisão**: excluir uma categoria roda, numa única transação: `UPDATE
nota_fiscal SET categoria_id = NULL WHERE categoria_id = ?` seguido de
`DELETE FROM categoria WHERE id = ?`. Não se usa `ON DELETE SET NULL`
declarado na FK.

**Rationale**: mesmo raciocínio do item 1 — a coluna `categoria_id` é
adicionada via `ALTER TABLE` sem poder declarar `ON DELETE SET NULL` de
forma confiável em todas as versões/casos (e, mais uma vez, não altera
comportamento de FK em bancos já existentes de forma implícita). SQL
explícito numa transação única funciona igual em banco novo e no banco já
populado do usuário, sem exigir migração separada — mesma decisão de
research.md #1 da feature 002.

**Alternatives considered**: bloquear a exclusão de categoria em uso
(exigir remover a associação de cada nota antes) — rejeitada por spec
(FR-006 exige desassociação automática, não bloqueio) e por ir contra o
espírito de simplicidade/não-fricção já estabelecido na feature 002.

## 4. Superfície da API: blueprint próprio `routes_categorias.py`

**Decisão**: `GET/POST /categorias`, `PUT/DELETE /categorias/<id>` e `PUT
/notas/<id>/categoria` num blueprint novo (`categorias`), registrado em
`src/api/app.py` junto aos blueprints existentes. UI aciona via `fetch`
com `confirm()` para exclusão — mesmo padrão já usado em `upload.html` e
nos templates de nota da feature 002.

**Rationale**: categoria é uma entidade independente de nota (não é uma
sub-operação de `/notas`), então um blueprint próprio segue a mesma
separação por domínio já usada (`routes_importar` para mutações de nota,
`routes_consulta` para leitura/views). A rota de atribuição
(`PUT /notas/<id>/categoria`) fica no blueprint de categoria por
conveniência de coesão (toda lógica de categoria num só lugar), já que
ela só grava um `categoria_id`, não mexe em nenhum outro campo de nota.

**Alternatives considered**: colocar tudo em `routes_importar.py` (que já
cresceu com o `DELETE /notas/<id>` da feature 002) — rejeitada por
misturar duas entidades num único arquivo de rotas, reduzindo a
legibilidade que o Princípio I valoriza.
