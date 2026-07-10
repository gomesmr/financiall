# Contrato: CLI do financiALL (feature 001)

Todas as mensagens ao usuário são em português (Princípio VI). Todo
comando sai com código `0` em sucesso e código diferente de `0` em falha de
entrada (para permitir uso em scripts).

## `importar <entrada>`

Importa uma NFC-e a partir de uma URL de QR Code ou de uma chave de acesso
colada.

**Entrada**: `<entrada>` — string obrigatória. Aceita:
- uma URL http(s) contendo a chave de 44 dígitos em algum parâmetro de
  consulta; ou
- uma chave de 44 dígitos, com ou sem espaços/caracteres não numéricos
  misturados.

**Saídas possíveis**:

| Cenário | Código de saída | Mensagem (formato) |
|---|---|---|
| Entrada não contém uma chave de 44 dígitos extraível/válida | 1 | `Erro: não foi possível identificar uma chave de acesso válida de 44 dígitos em "<entrada>".` |
| Chave com dígito verificador inválido | 1 | `Erro: a chave de acesso informada tem dígito verificador inválido.` |
| Chave já registrada | 0 | `Nota já registrada em <data_importacao> (chave <chave_acesso mascarada, ex.: ...últimos 4 dígitos>). Emitente: <emitente_nome ou "não disponível">. Total: <valor_total ou "não disponível">.` — nenhuma gravação nova ocorre |
| Chave nova, fonte de detalhamento respondeu com sucesso | 0 | `Nota importada com sucesso. Emitente: <emitente_nome>. Data: <data_emissao>. Total: <valor_total>. Itens: <quantidade_itens>.` |
| Chave nova, fonte de detalhamento falhou (parcial ou totalmente) | 0 | `Nota importada com dados parciais (pendente de revisão). UF: <uf>. Emitente: não disponível no momento.` |

**Nunca**: exceção não tratada impressa no terminal (stack trace Python);
qualquer erro externo vira uma das mensagens acima (Princípio III).

## `listar`

Lista as notas importadas.

**Entrada**: nenhuma (opcionalmente, filtro por mês `AAAA-MM` — fora de
escopo obrigatório desta feature, pode ser adicionado depois).

**Saída** (tabela, uma linha por nota, ordenada por `data_emissao`/`ano_mes_emissao` desc):

```text
Data        Emitente              Total      Status
2026-06-15  Farmácia Exemplo Ltda R$ 45,90    completa
2026-06-01  (não disponível)      (não disp.) pendente de revisão
```

**Quando não há notas**: `Nenhuma nota importada ainda.` (código de saída
`0`).

## `resumo-mensal`

Exibe o total gasto por mês, com base nas notas fiscais importadas.

**Entrada**: nenhuma.

**Saída** (uma linha por mês com ao menos uma nota):

```text
Mês       Total (parcial — só notas fiscais)   Notas
2026-06   R$ 312,40                             5
2026-05   R$ 128,00                             2
```

O cabeçalho **MUST** deixar explícito que o total é parcial (FR-010) — não
é o gasto total do mês, apenas o que está documentado por notas fiscais
importadas.

**Quando não há notas**: `Nenhuma nota importada ainda — sem dados para o
resumo mensal.` (código de saída `0`).
