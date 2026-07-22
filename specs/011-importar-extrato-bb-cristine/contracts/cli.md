# Contrato: Script de Importação (feature 011)

## `python -m src.scripts.importar_extrato_bb <arquivo-ou-pasta> [--db-path <caminho>]`

Parser recorrente para extrato de conta corrente do Banco do Brasil
(`.xlsx`) da Cristine. Aceita um arquivo único ou uma pasta (processa todo
`.xlsx` dentro dela, mesmo padrão de `importar_extrato_itau_cartao`). Serve
tanto para a importação histórica (primeira execução contra os 5 arquivos
já baixados) quanto para toda importação futura (mesmo comando, arquivo
novo) — idempotente por fingerprint, nenhuma transação já importada é
duplicada.

Reaproveita `processar_transacoes()` (mesma função usada pela migração
histórica do Marcelo e pelo parser de cartão Itaú) — mesma
classificação/reconciliação/persistência, só troca a origem e o formato dos
dados.

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
| Arquivo não é um `.xlsx` interpretável (corrompido, formato mudou) | `1`, mensagem em stderr — aborta só aquele arquivo quando processando uma pasta com múltiplos arquivos; não apaga o que já foi importado dos arquivos anteriores da mesma execução |

Linha individual sem "Lançamento"/"Detalhes"/"Valor" reconhecíveis, ou
identificada como linha de saldo (research.md #6), é pulada individualmente
(conta como "pulada"), sem abortar o arquivo inteiro.

## Endpoint HTML: `GET /ver/resumo?titular=<marcelo|cristine>`

Extensão do endpoint já existente (feature 009). Parâmetro `titular`
opcional (querystring) — quando presente, os totais e o detalhamento por
categoria mostrados refletem só as transações e notas daquele titular; quando
ausente, mostra o consolidado do casal (comportamento atual, inalterado).
Mesmo padrão de filtro já usado por `GET /ver/notas?titular=...`.

## Endpoint HTML: `GET /ver/transacoes?titular=<marcelo|cristine>`

Mesma extensão aplicada à listagem de transações já existente (feature
010), para permitir navegar o extrato de um titular específico.
