# Contrato: Script de Importação (feature 012)

## `python -m src.scripts.importar_fatura_mercado_pago <arquivo-ou-pasta> [--db-path <caminho>]`

Parser recorrente para fatura de cartão de crédito Mercado Pago (`.pdf`).
Aceita um arquivo único ou uma pasta (processa todo `.pdf` dentro dela,
mesmo padrão de `importar_extrato_itau_cartao`). Serve tanto para a
importação histórica (primeira execução contra a fatura de junho/2026 já
baixada) quanto para toda importação futura (mesmo comando, fatura nova) —
idempotente por fingerprint, nenhuma transação já importada é duplicada
(incluindo parcelas subsequentes da mesma compra parcelada — research.md #4).

Reaproveita `processar_transacoes()` (mesma função usada pela migração
histórica e pelos parsers de fatura Itaú e extrato BB) — mesma
classificação/reconciliação/persistência, só troca a origem e o formato
dos dados.

### Saída (stdout, em português — Princípio VI)

```text
Importação concluída: <N> transação(ões) importada(s), <M> já existente(s) na base, <P> registro(s) pulado(s) por dado inválido.
Classificação automática: <A> por cache/regra, <B> pendente(s) de revisão.
Reconciliação: <R> transação(ões) ligada(s) a nota fiscal, <C> caso(s) ambíguo(s) na fila de revisão.
```

Nunca imprime descrição, valor ou conta de nenhuma transação individual
(Princípio IV) — só contagens.

### Código de saída

| Cenário | Exit code |
|---|---|
| Execução concluída (mesmo com registros pulados/pendentes) | `0` |
| Arquivo/pasta não encontrado | `1`, mensagem em stderr |
| Arquivo não é um `.pdf` interpretável (corrompido, layout mudou de forma que nenhuma seção reconhecida foi encontrada, ou "Emitida em" ausente) | `1`, mensagem em stderr — aborta só aquele arquivo quando processando uma pasta com múltiplos arquivos; não apaga o que já foi importado dos arquivos anteriores da mesma execução |

Linha individual fora de qualquer seção reconhecida (nenhum cabeçalho
`Movimentações na fatura` ou `Cartão ... [****NNNN]` visto ainda), ou que
não bate com o formato esperado de lançamento, é ignorada individualmente
sem abortar o arquivo inteiro (research.md #2, Princípio VII).
