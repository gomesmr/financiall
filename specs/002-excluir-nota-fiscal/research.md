# Research: Excluir Nota Fiscal

Não há `NEEDS CLARIFICATION` no Technical Context — a feature reaproveita
integralmente a stack da 001 (Flask + SQLite + pytest), sem tecnologia
nova a avaliar. As decisões abaixo resolvem escolhas de implementação
levantadas pela spec (FR-003/FR-005 e os edge cases de arquivo/envio).

## 1. Onde a cascata acontece: SQL explícito em transação, não `ON DELETE CASCADE`

**Decisão**: a exclusão de `item_nota` e `envio_ocr` associados a uma
`nota_fiscal` é feita por `DELETE` explícitos dentro de uma única
transação SQL (`BEGIN` → deletes → `COMMIT`), executados pela função de
repositório, em vez de declarar `ON DELETE CASCADE` no schema.

**Rationale**: o banco do usuário (`data/financiall.db`) já existe,
criado pelo schema atual sem `ON DELETE CASCADE` na FK de `item_nota`.
SQLite não permite adicionar essa cláusula a uma FK existente via `ALTER
TABLE`, e o projeto não usa ferramenta de migração (Princípio I —
simplicidade, sem dependência nova para um caso de uso único). SQL
explícito funciona igual em bancos novos e no banco já existente do
usuário, sem exigir passo de migração separado.

**Alternatives considered**: adicionar `ON DELETE CASCADE` ao `CREATE
TABLE IF NOT EXISTS` do schema — rejeitada porque `IF NOT EXISTS` não
altera uma tabela já criada; exigiria recriar a tabela (copiar dados,
dropar, recriar) só para este propósito, complexidade desproporcional ao
ganho (Princípio I).

## 2. Remoção do arquivo físico: best-effort, fora da transação SQL

**Decisão**: a função de repositório (`storage/db.py`) faz apenas a parte
transacional (banco) e retorna a lista de `caminho_arquivo` dos envios
excluídos. A camada de serviço (`services/exclusao.py`) tenta remover cada
arquivo do disco depois que a transação do banco já confirmou, ignorando
`FileNotFoundError` (arquivo já ausente não é erro).

**Rationale**: SQLite não torna operações de filesystem transacionais
junto com o `COMMIT` do banco — não há como garantir atomicidade real
entre as duas coisas. Tratar a remoção do arquivo como best-effort (em vez
de abortar a exclusão se o arquivo já não existir) respeita o Princípio
III (tratamento de erro explícito, sem exceção não tratada) e evita que o
usuário fique sem conseguir excluir uma nota cujo arquivo sumiu do disco
por fora do sistema (ex.: limpeza manual). A ordem (banco primeiro, disco
depois) prioriza a consistência dos dados financeiros sobre a limpeza de
disco — se a remoção do arquivo falhar por outro motivo (permissão, disco
cheio), a nota já está corretamente excluída do banco, que é o dado que
importa para os totais e relatórios.

**Alternatives considered**: apagar o arquivo antes do `COMMIT` do banco —
rejeitada porque, se o `COMMIT` falhar depois, o arquivo já teria sumido
sem a nota ter sido de fato excluída (inconsistência na direção oposta,
pior: perde o arquivo sem remover o registro).

## 3. Múltiplos envios apontando para a mesma nota

**Decisão**: a query de exclusão busca **todos** os `envio_ocr` cujo
`nota_fiscal_id` aponta para a nota (não apenas o primeiro/último), e cada
um tem seu arquivo removido.

**Rationale**: o schema permite múltiplos envios resolverem para a mesma
nota (ex.: usuário envia a mesma foto duas vezes; o segundo envio é
processado, encontra a nota já existente via dedup, e é vinculado a ela).
O edge case já foi identificado na spec — ignorar isso deixaria arquivo
órfão em disco, violando SC-005.

## 4. Superfície da API: `DELETE /notas/<id>`

**Decisão**: nova rota `DELETE /notas/<int:nota_id>` no blueprint
`routes_importar`, respondendo JSON, seguindo o mesmo padrão REST-ish já
usado por `POST /notas` e `GET /notas` (ver
`specs/001-importar-nfce/contracts/api.md`). A UI (templates HTML) aciona
essa rota via `fetch` com `confirm()` nativo do navegador antes do
disparo — mesmo padrão já usado em `upload.html` para `POST /notas` e
`POST /notas/upload` (não há framework JS no projeto; não se introduz
um agora).

**Rationale**: HTML puro não suporta método `DELETE` em formulários
(apenas `GET`/`POST`), mas o projeto já resolve isso com `fetch` +
JavaScript inline para as outras mutações — reaproveitar o padrão em vez
de introduzir uma rota `POST /notas/<id>/excluir` alternativa evita ter
duas convenções diferentes para mutação no mesmo projeto (Princípio I).

**Alternatives considered**: `POST /notas/<id>/excluir` (form-friendly,
sem JS) — rejeitada porque o projeto já tem precedente de `fetch` para
mutações e misturar os dois estilos (form POST puro aqui, fetch JSON ali)
seria menos consistente, não mais simples.

## 5. Confirmação na UI

**Decisão**: `window.confirm()` nativo do navegador antes de disparar o
`fetch DELETE`, com uma mensagem clara em português mencionando que a ação
não pode ser desfeita.

**Rationale**: atende FR-002 (confirmação explícita) com o menor custo de
implementação possível, consistente com o restante da UI atual (HTML
simples, sem modais customizados). Um modal mais elaborado fica a critério
da feature de revisão visual (006), que já está no roadmap separadamente —
não há necessidade de antecipar esse trabalho aqui.
