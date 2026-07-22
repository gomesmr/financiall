# Data Model: Importar extrato BB (Cristine) e visão por titular

Nenhuma entidade nova e nenhuma migração de schema (research.md #1) — esta
feature usa campos/tabelas que já existem.

## Transação (`transacao`, `src/models/transacao.py`)

Sem mudança de estrutura. Campos relevantes para esta feature (já
existentes):

| Campo | Tipo | Uso nesta feature |
|---|---|---|
| `titular` | `str \| None` | Passa a ser populado (`"cristine"`) pelo novo parser BB. Continua opcional — transações antigas do Marcelo continuam com `titular=None` até (se algum dia) o parser Itaú for retroativamente ajustado; não é requisito desta feature. |
| `conta` | `str` | Recebe o identificador canônico novo `"bb_cristine_cc"` (via `conta_canonica.py`) para transações do BB. |
| `natureza` | `str \| None` | Passa a incluir `"transferencia_interna"` para transferências entre o casal identificadas nos extratos do BB e do Itaú (research.md #8), usando o enum já existente — nenhum valor novo. |
| `fingerprint` | `str` | Calculado do mesmo jeito (`data + descricao_normalizada + valor + conta`) — dedup funciona entre re-importações do mesmo arquivo ou de arquivos com período sobreposto. |

**Regra de validação (já existente, reaproveitada)**: `titular`, quando
presente, deve pertencer a `TITULARES_VALIDOS = {"marcelo", "cristine",
"nao_identificado"}` (`src/models/nota_fiscal.py`) — o parser BB nunca grava
um valor fora desse conjunto porque `titular` é uma constante fixa
(research.md #7), não input de usuário.

## Conta canônica (`src/services/conta_canonica.py`, dicionário em memória, não tabela)

Nova entrada:

| Conta bruta (origem do arquivo) | Canônica | Efeito |
|---|---|---|
| `"BB_Cristine"` | `"bb_cristine_cc"` | Sufixo `_cc` ativa: sinal do valor = tipo (positivo→entrada, negativo→saída) e janela de reconciliação de 3 dias — mesma lógica já aplicada a `itau_cc`. |

## Regra de natureza (`regra_natureza`, já existente)

Novas linhas semeadas via `src/scripts/regras_semente_natureza.json`
(nenhuma mudança de schema), cobrindo padrões do extrato da Cristine:
dívidas BB (CDC, Consignação), salário (SMF), tarifas/anuidades, e
transferência para o Marcelo. Mesma tabela, mesmo mecanismo de cascata
cache → regra → manual já usado para o Marcelo.

## Fluxo de dados (não é uma entidade, mas documentado aqui por ser central à feature)

```text
extrato/cristine/*.xlsx (BB)
        │
        ▼
src/services/importar_extrato_bb.py :: parsear()
        │  {data, descricao, valor_raw, conta="BB_Cristine",
        │   fonte=<nome do arquivo>, titular="cristine"}
        ▼
src/services/importar_historico_extrato.py :: processar_transacoes()
        │  (canonicaliza conta, interpreta sinal, calcula fingerprint,
        │   classifica natureza via cascata, grava, tenta reconciliar
        │   com nota fiscal, resolve estabelecimento)
        ▼
tabela transacao (titular="cristine", conta="bb_cristine_cc", ...)
        │
        ▼
resumo_service (filtrado por titular) → /ver/resumo, /ver/transacoes
```
