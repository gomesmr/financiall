# Research: Log de importações

## #1 — Onde interceptar para cobrir todos os importadores sem tocar em cada um

**Decision**: instrumentar exclusivamente `processar_transacoes()` em
`src/services/importar_historico_extrato.py` — grava um evento de log ao
final da função, depois do laço que já persiste cada transação e calcula
o `ImportarExtratoResumo`.

**Rationale**: essa função já é o único ponto de convergência entre os
seis caminhos de importação existentes (scripts CLI de Itaú CC, Itaú
cartão, BB, Mercado Pago, Open Finance Itaú, e a rota web
`POST /extratos/upload`) — todos chamam `processar_transacoes(registros,
db_path=...)` e usam o `ImportarExtratoResumo` resultante. Instrumentar
aqui satisfaz FR-001 (registrar automaticamente, independente do caminho
de entrada) sem alterar nenhum dos seis chamadores nem duplicar lógica de
log em cada um (Princípio I — nenhuma solução além do necessário).

**Alternatives considered**:
- Instrumentar cada script/rota individualmente: rejeitado — duplica a
  lógica de cálculo de período/contagens seis vezes, e qualquer
  importador futuro precisaria lembrar de adicionar o log manualmente.
- Um decorator em volta de `processar_transacoes`: rejeitado por
  complexidade desnecessária — a função já centraliza tudo, um decorator
  não simplifica nada aqui, só adiciona indireção.

## #2 — Como obter a "fonte" sem mudar a assinatura de `processar_transacoes`

**Decision**: derivar a fonte do primeiro registro da lista de entrada
(`registros[0]["fonte"]`, já presente em todo `dict` produzido pelos
parsers existentes). Quando a lista vier vazia, o evento é registrado com
fonte `None`.

**Rationale**: todo `dict` de registro já carrega a chave `"fonte"` (nome
do arquivo ou do dump), e uma única chamada a `processar_transacoes`
sempre processa registros de uma única fonte (nunca mistura arquivos).
Derivar da lista evita adicionar um parâmetro novo à função central,
mantendo os seis chamadores inalterados (Princípio I). O caso de lista
vazia (arquivo sem nenhuma transação) é raro e já é coberto como edge
case aceito na spec — o evento ainda é registrado, só sem fonte
identificável.

**Alternatives considered**:
- Adicionar parâmetro `fonte: str | None = None` explícito à função:
  rejeitado — exigiria editar os seis pontos de chamada para passar o
  nome do arquivo, que eles já não guardam separadamente (só dentro dos
  registros), sem ganho real sobre derivar da lista.

## #3 — Como calcular o período coberto

**Decision**: `min()`/`max()` sobre o campo `"data"` (string ISO
`AAAA-MM-DD`) de todos os registros de entrada que tiverem esse campo
não vazio — independente de o registro ter sido importado, já existente
ou pulado por outro motivo (descrição/valor/conta inválidos). Quando
nenhum registro tiver data válida, `periodo_inicio`/`periodo_fim` ficam
`None`.

**Rationale**: strings no formato `AAAA-MM-DD` já são comparáveis
lexicograficamente como datas (mesmo padrão já usado em
`importar_openfinance_itau.py`, ex. `data_iso < _data_corte_parcela_antiga`),
então não é necessário parsear para `datetime.date` só para achar
min/max. Usar todos os registros com data (não só os efetivamente
importados) reflete com mais fidelidade "o que o arquivo/dump cobria",
que é a pergunta que motiva a feature (FR-002) — um registro pulado por
descrição vazia ainda faz parte do período coberto pelo arquivo.

**Alternatives considered**:
- Calcular período só sobre os registros efetivamente importados
  (`resumo.importadas`): rejeitado — reimportar um arquivo 100% já
  existente (User Story 2) faria o período desaparecer mesmo o arquivo
  cobrindo um intervalo real e conhecido.

## #4 — Onde e como persistir o evento

**Decision**: nova tabela `log_importacao` no schema já existente de
`src/storage/db.py` (mesmo arquivo/padrão de todas as demais tabelas —
`CREATE TABLE IF NOT EXISTS` idempotente), com uma linha por execução de
`processar_transacoes` que não lançou exceção.

**Rationale**: o projeto já usa SQLite direto (sem ORM) com uma função
`init_db()` central e um repositório de funções `inserir_*`/`listar_*`
por entidade em `db.py` — mesmo padrão de `compromisso_futuro`
(introduzido na feature de parcelas futuras). Não há necessidade de
migração de dado (tabela nova, sem coluna adicionada a tabela
existente), então não precisa de `_garantir_coluna_*` idempotente, só do
`CREATE TABLE IF NOT EXISTS` normal.

**Alternatives considered**:
- Arquivo de log em texto/JSON append-only: rejeitado pela própria
  decisão do usuário (quer tabela + página, não arquivo) — também seria
  inconsistente com o padrão de dado estruturado já usado no resto do
  projeto (SQLite), exigindo lógica de leitura/paginação própria em vez
  de reaproveitar SQL.

## #5 — Falha durante o processamento não deve gerar log parcial

**Decision**: o `INSERT` do evento de log acontece só depois que o laço
principal de `processar_transacoes` termina sem lançar exceção — se uma
exceção for lançada no meio do laço (ex.: erro inesperado gravando uma
transação), a função propaga a exceção normalmente e nenhum evento de
log é gravado (FR-006).

**Rationale**: consistente com o comportamento atual de
`processar_transacoes` (já propaga exceção sem tratamento especial — o
tratamento de erro de arquivo/parsing acontece antes, nos chamadores) e
com Princípio III (erro explícito, não mascarado) — um log de sucesso
não deve ser gravado para uma execução que não terminou de fato.

**Alternatives considered**:
- `try/finally` gravando o log sempre, com uma flag de sucesso/falha:
  rejeitado — a spec (FR-006) só exige "não gerar log numa falha", não
  pede rastrear falhas; adicionar isso seria escopo além do requisito
  (Princípio I).
