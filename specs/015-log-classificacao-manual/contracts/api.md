# Contrato: Log de classificação manual de natureza (feature 015)

## `GET /ver/log-classificacoes`

Página nova, mesmo padrão de `/ver/log-importacoes` (feature 014) —
lista os eventos de classificação manual, do mais recente para o mais
antigo (FR-003).

### Resposta

Página HTML (`render_template`), sem parâmetro de query obrigatório.
Cada linha da tabela mostra:

| Coluna | Origem | Exibição quando ausente |
|---|---|---|
| Data/hora | `log.data_hora` | — (sempre presente) |
| Método | `log.metodo` ("Em grupo" / "Individual") | — |
| Alvo | `log.alvo_descricao_normalizada` (grupo) ou `#{log.alvo_transacao_id}` (individual) | — (sempre um dos dois presente) |
| Natureza | `log.natureza` | — |
| Categoria | nome da categoria (via `categoria_id`) | "—" quando `NULL` (naturezas que não são "gasto") |
| Transações afetadas | `log.quantidade_afetada` | — |

Sem paginação nesta primeira versão (mesmo raciocínio da feature 014 —
volume esperado é baixo).

## Sem endpoint novo de escrita

Nenhuma rota nova grava um `LogClassificacaoManual` diretamente — o
registro acontece de forma automática, de dentro de
`storage_db.classificar_grupo_pendente_natureza()` e
`storage_db.atribuir_natureza_manual()` (research.md #1), reaproveitadas
sem mudança de assinatura pelas rotas já existentes:

- `POST /transacoes/pendentes/classificar-grupo` (método "grupo")
- `PUT /transacoes/<id>/natureza` (método "individual")

Nenhum desses pontos de chamada muda de comportamento visível
(Assumptions da spec) — o log é um efeito colateral interno das funções
de storage já existentes.
