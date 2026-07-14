# Contrato: Script de Importação (feature 004)

## `python -m src.scripts.importar_historico <caminho-do-arquivo>`

Executado manualmente pelo responsável do projeto (não é uma rota HTTP —
research.md #8). Argumento obrigatório: caminho do arquivo de histórico
(JSON).

**Opcional**: `--db-path <caminho>` — sobrescreve o banco de destino
(mesma variável `FINANCIALL_DB_PATH` usada pelo resto do projeto quando
omitido).

### Saída (stdout, em português — Princípio VI)

Ao final de uma execução bem-sucedida (mesmo que zero notas novas sejam
encontradas):

```text
Importação concluída: <N> nota(s) importada(s), <M> já existente(s) na base, <P> registro(s) pulado(s) por dado inválido.
```

Nunca imprime chave de acesso, CNPJ, emitente, ou valor de nenhuma nota
(Princípio IV) — só contagens.

### Código de saída

| Cenário | Exit code |
|---|---|
| Execução concluída (mesmo com registros pulados) | `0` |
| Arquivo não encontrado | `1`, mensagem `Arquivo não encontrado: <caminho>` em stderr |
| Arquivo não é um JSON válido | `1`, mensagem `Não foi possível interpretar o arquivo como JSON válido.` em stderr |

**Nunca**: gravar qualquer nota quando o arquivo inteiro é ilegível
(FR-007) — nesse caso a base fica exatamente como estava antes da
execução.

## Efeito colateral em `GET /notas` e `GET /ver/notas`

Ambos passam a aceitar `?titular=marcelo` / `?titular=cristine` /
`?titular=nao_identificado` (query string opcional, mesmo padrão de
`?mes=`), restringindo a listagem a notas daquele titular. Sem o
parâmetro, comportamento inalterado (todas as notas, de qualquer
titular).

`GET /notas` (JSON) passa a incluir `"titular"` em cada nota do array
`notas` — string (`"marcelo"`, `"cristine"`, `"nao_identificado"`).
