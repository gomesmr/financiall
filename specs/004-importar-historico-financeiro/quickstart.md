# Quickstart: Validar "Importar Histórico Financeiro"

Pré-requisitos: ambiente já configurado como nas features anteriores.

## 1. Rodar os testes automatizados

```bash
pytest tests/unit/test_importar_historico.py tests/integration/test_api.py -v
```

Usa uma fixture pequena e sintética (nunca o arquivo real do usuário) —
cobre mapeamento, conversão de valores/data, registro malformado pulado,
idempotência numa segunda execução, e o filtro `?titular=`.

## 2. Validação com dado real (Princípio V — obrigatória para esta feature)

> **Cuidado**: nunca imprimir/logar o conteúdo do arquivo real ou das
> notas resultantes (chave, CNPJ, emitente, valor) — só contagens
> (Princípio IV).

```bash
# banco isolado, nao o de producao/dev
FINANCIALL_DB_PATH=/tmp/validacao-004.db python -m src.scripts.importar_historico assets/finalcial/nf-tracking/notas.json
```

1. Confirme que a saída mostra a contagem esperada (bate com o número de
   notas do arquivo, sem repetir nenhum dado da nota).
2. Rode o mesmo comando de novo — confirme que a segunda execução mostra
   `0 nota(s) importada(s)` e a mesma contagem de "já existente(s)" da
   primeira vez (idempotência, US3).
3. Suba o servidor apontando pro mesmo banco (`FINANCIALL_DB_PATH=/tmp/validacao-004.db python -m src.main`) e confira em `/ver/notas`:
   - As notas do histórico aparecem, com itens.
   - Cada nota mostra o titular (Marcelo/Cristine).
   - O filtro por titular restringe a listagem corretamente.
4. Apague o banco temporário ao final (`rm /tmp/validacao-004.db`).

## Critério de aceite (liga com Success Criteria da spec)

- SC-001: toda nota do histórico aparece na listagem depois da
  importação.
- SC-002: segunda execução não duplica nada.
- SC-003/SC-004: titular visível na listagem e filtrável.
- SC-005: um arquivo ausente/corrompido não altera a base em nada.
