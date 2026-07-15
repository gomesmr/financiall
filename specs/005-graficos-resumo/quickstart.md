# Quickstart: Validar "Gráficos no Resumo de Gastos"

Pré-requisitos: ambiente já configurado como nas features anteriores.

## 1. Rodar os testes automatizados

```bash
pytest tests/unit/test_resumo.py tests/integration/test_api.py -v
```

Cobre: agregação por categoria (soma correta, "Sem categoria" incluída,
notas sem valor excluídas), e que `GET /notas/resumo/categorias` bate
com o total já exibido em `/notas/resumo/mes-atual`.

## 2. Validar a paleta (se algum valor de cor for alterado)

```bash
node <caminho-da-skill-dataviz>/scripts/validate_palette.js \
  "#2a78d6,#1baf7a,#eda100,#008300,#4a3aa7,#e34948,#e87ba4,#eb6834" --mode light
```

Já validado nesta sessão (research.md #2) — só precisa rodar de novo se
algum hex for alterado.

## 3. Validação manual

```bash
python -m src.main
```

1. Com notas categorizadas no mês corrente, abra `/ver/resumo` — confirme
   que o gráfico de pizza mostra uma fatia por categoria, mais "Sem
   categoria" se houver notas sem categoria.
2. Passe o mouse numa fatia — confirme que aparece o nome e o valor exato.
3. Confirme que a soma das fatias bate com o total do mês já mostrado em
   texto.
4. Escolha um mês diferente no seletor — confirme que a pizza atualiza
   para a distribuição daquele mês.
5. Escolha um mês sem nenhuma nota — confirme a mensagem clara em vez de
   um gráfico vazio/quebrado.
6. Confirme que o gráfico de barras mostra uma barra por mês da tabela
   "Meses anteriores", e que passar o mouse numa barra mostra o valor
   exato daquele mês.
7. Abra em modo escuro (preferência do SO/navegador) — confirme que as
   cores continuam legíveis (paleta validada nos dois modos, research.md #2).

## Critério de aceite (liga com Success Criteria da spec)

- SC-001/SC-002: categoria de maior gasto e comparação entre meses são
  identificáveis visualmente, sem cálculo manual.
- SC-003: soma das fatias == total em texto, em qualquer mês testado.
- SC-004: qualquer mês do histórico disponível pode ser visualizado por
  categoria, não só o corrente.
