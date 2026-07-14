# Quickstart: Validar "Excluir Nota Fiscal"

Pré-requisitos: ambiente já configurado como na feature 001 (`.venv`
ativo, dependências instaladas — ver `specs/001-importar-nfce/quickstart.md`).

## 1. Rodar os testes automatizados

```bash
pytest tests/unit/test_exclusao.py tests/integration/test_api.py -v
```

Cobre: cascata (nota + itens + envio + arquivo), múltiplos envios para a
mesma nota, exclusão de nota inexistente (404), e o ciclo completo
excluir → reimportar (US2/FR-004).

## 2. Validação manual ponta a ponta

```bash
# Sobe o app localmente (mesma forma da feature 001)
python -m src.main
```

1. Importe uma nota qualquer (via UI em `/` ou `curl -X POST /notas -d
   '{"entrada": "<chave ou url>"}'`) — anote o `id` retornado.
2. Acesse `/ver/notas` — confirme que a nota aparece na listagem.
3. Acesse `/ver/notas/<id>` — clique em "Excluir", confirme o diálogo.
4. Verifique:
   - Redirecionado para `/ver/notas`, nota não aparece mais na lista.
   - `GET /notas/resumo/mes-atual` não conta mais essa nota no total.
   - Se a nota veio de upload (foto/PDF), o arquivo correspondente em
     `data/uploads/` (ou `FINANCIALL_UPLOAD_DIR`) não existe mais.
   - Acessar `/ver/envios/<envio_id>` do envio original agora mostra "não
     encontrado", sem erro de servidor.
5. Reimporte a mesma nota (mesma chave/URL, ou reenvie a mesma foto/PDF).
   Confirme que o status retornado é `completa`/`pendente_revisao` (nota
   nova), não `ja_registrada`.

## Critério de aceite (liga com Success Criteria da spec)

- SC-001/SC-002: nota some da listagem e do resumo imediatamente após a
  exclusão confirmada.
- SC-003: reimportação funciona sem qualquer passo manual fora da UI.
- SC-004: nenhuma exclusão ocorre sem o diálogo de confirmação.
- SC-005: nenhum arquivo órfão permanece em `data/uploads/` após a
  exclusão.
