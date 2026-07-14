# Quickstart: Validar "CRUD de Categorias"

Pré-requisitos: ambiente já configurado como nas features anteriores
(`.venv` ativo, dependências instaladas).

## 1. Rodar os testes automatizados

```bash
pytest tests/unit/test_categorias.py tests/integration/test_api.py -v
```

Cobre: criação/edição/exclusão de categoria, unicidade de nome
(maiúsculas/minúsculas, espaços, acentuação), desassociação de notas ao
excluir categoria em uso, atribuição/troca/remoção de categoria numa nota,
e os casos de erro (nome vazio, nome duplicado, categoria/nota
inexistente).

## 2. Validação manual ponta a ponta

```bash
python -m src.main
```

1. Acesse `/ver/categorias` — deve mostrar "nenhuma categoria" com um
   caminho para criar a primeira.
2. Crie uma categoria (ex.: "Alimentação"). Confirme que ela aparece na
   lista.
3. Tente criar outra com o mesmo nome em minúsculas (`alimentação`).
   Confirme que é recusada com mensagem clara.
4. Edite o nome de uma categoria existente. Confirme que o novo nome
   aparece na lista.
5. Importe (ou reaproveite) uma nota fiscal. Acesse `/ver/notas/<id>` e
   atribua a categoria criada. Confirme que ela aparece no detalhe e na
   listagem (`/ver/notas`).
6. Troque a categoria da nota por outra, depois remova a atribuição
   ("sem categoria"). Confirme os dois casos.
7. Exclua uma categoria que está atribuída a uma nota. Confirme que a
   exclusão funciona sem erro e que a nota passa a mostrar "sem
   categoria".

## Critério de aceite (liga com Success Criteria da spec)

- SC-001/SC-002: criar categoria e atribuir a uma nota são ações rápidas
  (poucos cliques/segundos).
- SC-003: toda nota mostra sua categoria (ou "sem categoria") em
  `/ver/notas` e `/ver/notas/<id>`.
- SC-004: excluir categoria em uso nunca gera erro nem quebra navegação.
- SC-005: nome duplicado é sempre recusado, com mensagem clara.
