# Contrato: Log de importações (feature 014)

## `GET /ver/log-importacoes`

Página nova, mesmo padrão das demais páginas "Ver" do financiALL (ex.
`/ver/compromissos-futuros`) — lista os eventos de histórico de
importação, do mais recente para o mais antigo (FR-003).

### Resposta

Página HTML (`render_template`), sem parâmetro de query obrigatório.
Cada linha da tabela mostra:

| Coluna | Origem | Exibição quando ausente |
|---|---|---|
| Data/hora da importação | `log.data_hora` | — (sempre presente) |
| Fonte | `log.fonte` | "—" quando `NULL` |
| Período coberto | `log.periodo_inicio` – `log.periodo_fim` | "—" quando ambos `NULL` |
| Importadas | `log.importadas` | — (sempre presente, pode ser 0) |
| Já existentes | `log.ja_existentes` | — |
| Puladas | `log.puladas` | — |
| Classificadas automaticamente | `log.classificadas_automaticamente` | — |
| Pendentes de natureza | `log.pendentes_natureza` | — |
| Reconciliadas | `log.reconciliadas` | — |
| Ambíguas | `log.ambiguas` | — |

Sem paginação nesta primeira versão (Assumptions da spec — volume
esperado é poucas importações por mês).

## Sem endpoint novo de escrita

Nenhuma rota nova grava um `LogImportacao` diretamente — o registro
acontece de forma automática, de dentro de
`processar_transacoes()` (research.md #1), reaproveitado por todos os
caminhos de importação já existentes:

- `POST /extratos/upload` (feature 013)
- `src/scripts/importar_extrato_itau_cc.py`
- `src/scripts/importar_extrato_itau_cartao.py` (via serviço equivalente)
- `src/scripts/importar_extrato_itau_cc.py` (BB usa o mesmo
  `processar_transacoes`, ver `importar_extrato_bb.py`)
- `src/scripts/importar_openfinance_itau.py`
- Script de fatura Mercado Pago

Nenhum desses pontos de chamada muda de assinatura ou de comportamento
visível (Assumptions da spec) — o log é um efeito colateral interno da
função central.
