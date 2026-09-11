# Quickstart: Log de classificação manual de natureza

## Pré-requisitos

- Ambiente de dev do financiALL rodando (`.venv` ativo, dependências
  instaladas).
- Banco de teste isolado (nunca `data/financiall.db` real — Princípio
  IV/AGENTS.md).

## Validar via teste automatizado (caminho principal)

```bash
pytest tests/unit/test_storage_log_classificacao_manual.py
pytest tests/unit/test_classificacao_natureza_log.py
pytest tests/integration -k log_classificacoes
```

Cobre: um evento é gravado por classificação em grupo bem-sucedida (com
a quantidade afetada correta); um evento é gravado por classificação
individual bem-sucedida; uma classificação em grupo sem nenhuma
transação afetada não gera evento; uma classificação recusada por
validação (natureza inválida, categoria ausente) não gera evento; uma
reclassificação gera um evento novo sem apagar o anterior.

## Validar end-to-end manualmente (dev, porta 5005)

1. Rodar a app de dev localmente ou no Pi.
2. Classificar um grupo pendente via `/ver/transacoes/pendentes` (ou
   `POST /transacoes/pendentes/classificar-grupo` diretamente).
3. Abrir `http://<host>:5005/ver/log-classificacoes` e conferir que:
   - Um evento novo aparece no topo, com método "Em grupo", a descrição
     do grupo, natureza/categoria e a quantidade afetada corretas.
4. Editar a natureza de uma transação individual (`PUT
   /transacoes/<id>/natureza`) e conferir que um evento com método
   "Individual" e o id da transação aparece no topo.

## Verificação visual (Princípio VIII)

Esta feature introduz página nova (`/ver/log-classificacoes`) — antes de
promover para produção, capturar tela via navegador headless e confirmar
ausência de erro de console JS, mesmo processo já usado na feature 014.
