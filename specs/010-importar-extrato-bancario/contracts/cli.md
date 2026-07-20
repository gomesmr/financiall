# Contrato: Scripts de Importação e Semeadura (feature 010)

## `python -m src.scripts.seed_regras_natureza [--db-path <caminho>]`

Semeia `regra_natureza` a partir de `src/scripts/regras_semente_natureza.json`
(migrado da lista `REGRAS` do script legado, research.md #5). Idempotente —
rodar de novo não duplica (insere só o que ainda não existe, por `padrao` +
`natureza`). Deve rodar **antes** da importação histórica, para que a
classificação automática já cubra a maioria das transações migradas.

Saída: `Regras-semente de natureza aplicadas com sucesso.` — exit `0`.

## `python -m src.scripts.importar_historico_extrato <caminho-do-registro.json> [--db-path <caminho>]`

Executado manualmente (mesmo padrão de `importar_historico`, feature 004 —
migração pontual, não canal recorrente). Lê o `registro.json` já processado
pelo script legado, mapeia cada registro para `Transacao` (conta
canonicalizada, `tipo`, `natureza`/`categoria_id` via cascata de
classificação), grava (idempotente por fingerprint) e tenta reconciliar com
nota fiscal cada transação classificada como `gasto`.

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
| Arquivo não encontrado | `1`, `Arquivo não encontrado: <caminho>` em stderr |
| Arquivo não é um JSON válido | `1`, `Não foi possível interpretar o arquivo como JSON válido.` em stderr |

Registro sem `data`, `valor` ou `conta` reconhecíveis é pulado
individualmente (conta como "pulado"), sem abortar a execução inteira — só
`data`/JSON do arquivo inteiro ilegível aborta tudo, sem gravar nada
parcial (FR-024).

## `python -m src.scripts.importar_extrato_itau_cartao <arquivo-ou-pasta> [--db-path <caminho>]`

Parser recorrente (US6) para fatura de cartão Itaú (`.xls`). Aceita um
arquivo único ou uma pasta (processa todo `.xls` dentro dela, mesmo padrão
do script legado). Mesma saída/idempotência/classificação/reconciliação do
comando de migração histórica acima — reaproveita a mesma função de
persistência, só troca a origem dos dados (parser de arquivo em vez de
`registro.json`).
