# Quickstart: Log de importações

## Pré-requisitos

- Ambiente de dev do financiALL rodando (`venv` ativo, dependências
  instaladas).
- Banco de teste isolado (nunca `data/financiall.db` real — Princípio
  IV/AGENTS.md).

## Validar via teste automatizado (caminho principal)

```bash
pytest tests/unit/test_log_importacao_processar_transacoes.py -k log_importacao
pytest tests/unit/test_storage_log_importacao.py
pytest tests/integration -k log_importacoes
```

Cobre: um evento é gravado por chamada de `processar_transacoes()`
(inclusive quando 0 transações são novas); período `NULL` quando nenhum
registro tem data válida; nenhum evento é gravado se a função lançar
exceção antes de terminar.

## Validar end-to-end manualmente (dev, porta 5005)

1. Rodar a app de dev localmente ou no Pi (`systemctl restart
   financiall-dev`, ou `flask run` local contra um banco de teste).
2. Importar qualquer extrato/fatura de teste (script CLI ou
   `POST /extratos/upload`).
3. Abrir `http://<host>:5005/ver/log-importacoes` e conferir que:
   - Um evento novo aparece no topo da lista.
   - Fonte, período e as 7 contagens batem com o resumo que o script/
     rota já imprimiu/retornou naquela mesma execução.
4. Repetir a importação do mesmo arquivo (User Story 2) e conferir que:
   - Aparece um segundo evento (não substitui o primeiro).
   - `importadas = 0` e `ja_existentes` bate com a quantidade de
     transações do arquivo.

## Verificação visual (Princípio VIII)

Esta feature introduz página nova (`/ver/log-importacoes`) — antes de
promover para produção, capturar tela via navegador headless local e
confirmar ausência de erro de console JS (mesmo processo já usado nas
features 009/013), já que a suíte automatizada verifica dado/contrato,
não aparência.
