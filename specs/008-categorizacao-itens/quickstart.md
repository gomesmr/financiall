# Quickstart: Validar "Categorização de Itens de Nota Fiscal"

Pré-requisitos: ambiente já configurado como nas features anteriores.
Antes de tudo, rodar a Tarefa 1 (validar/ajustar a taxonomia-semente e
carregar as regras-semente) — sem isso a cascata automática nunca acerta
nada, todo item cai em pendente.

## 1. Rodar os testes automatizados (rede de segurança de regressão)

```bash
pytest tests/unit tests/integration tests/contract -v
```

Espera-se cobertura nova para: normalização (`test_normalizacao.py`),
cascata de classificação (`test_classificacao_itens.py`, incluindo um
teste parametrizado sobre o corpus real de 330 descrições —
`assets/files.zip/corpus-descricoes-produtos.txt`, copiado para
`tests/fixtures/`), CRUD de taxonomia hierárquica e exclusão com
destino/bloqueio (`test_categorias.py`), e os contratos novos de
`contracts/api.md`. O restante da suíte continua passando 100%.

## 2. Verificação visual real (Princípio VIII)

1. Capturar uma tela de `/ver/pendentes` (fila de revisão, com pelo menos
   um grupo de itens pendentes) via navegador headless local — layout sem
   sobreposição/quebra.
2. Capturar uma tela de `/ver/categorias` mostrando a hierarquia
   categoria → subcategoria.
3. Checar ausência de erro de console JS nas duas capturas.

## 3. Cold-start: item novo sem cache nem regra (US1)

1. Importar uma nota (ou usar uma já existente) com um item de descrição
   nunca vista.
2. Abrir `/ver/pendentes` e confirmar que o item aparece agrupado pela
   descrição normalizada, e que a nota foi importada normalmente (não
   travou) — SC-001.
3. Atribuir uma categoria/subcategoria ao grupo.
4. Importar uma segunda nota com um item de mesma descrição (ou
   descrição que normaliza igual) e confirmar que ele já chega
   classificado, sem passar por `/ver/pendentes` — SC-002/SC-003 (US2).

## 4. Classificação por regra-semente (US3)

1. Com uma regra-semente ativa para um padrão conhecido (ex.: item cuja
   descrição normalizada contém "PAPEL HIGIENICO"), importar um item novo
   que casa o padrão pela primeira vez.
2. Confirmar que ele chega classificado sem passar pela fila.

## 5. Corrigir sem afetar o passado vs. corrigir a fonte (US4)

1. Com um item já classificado incorretamente (e ao menos mais uma
   ocorrência passada da mesma descrição, também errada), corrigir
   **apenas aquele item** (`PUT /itens/<id>/categoria`) e confirmar que a
   outra ocorrência passada não muda.
2. Em seguida, chamar `GET /itens/<id>/impacto-correcao-fonte` e
   confirmar que a contagem bate com o número real de ocorrências
   passadas com a mesma descrição e categoria antiga.
3. Chamar `POST /itens/<id>/corrigir-fonte` e confirmar que todas as
   ocorrências passadas foram atualizadas, e que uma nova importação com
   a mesma descrição já chega com a categoria corrigida (cache
   sobrescrito — research.md #11).

## 6. Exclusão de categoria (US5, clarificação de 2026-07-17)

1. Tentar excluir uma categoria de topo que tem subcategorias — confirmar
   bloqueio (`422`, FR-017), sem nenhuma alteração de dado.
2. Excluir uma subcategoria em uso: chamar `GET
   /categorias/<id>/impacto-exclusao`, conferir a contagem, e excluir com
   `destino: "pendente"` — confirmar que os itens afetados voltam a
   aparecer em `/ver/pendentes`.
3. Repetir com `destino: "substituta"` apontando para outra subcategoria
   de mesmo nível — confirmar que os itens afetados passam a apontar para
   a substituta, sem passar por pendente.

## 7. Reprocessamento (idempotência — FR-015)

1. Reimportar uma nota já importada e já com itens classificados.
2. Confirmar que nenhuma linha de `historico_classificacao_item` nova é
   criada e que as classificações existentes permanecem exatamente como
   estavam (nenhuma duplicação, nenhuma perda).

## 8. Validação com amostra real (Princípio V — distinta dos testes acima)

Antes de promover para produção: rodar a cascata de classificação sobre
o backlog real de itens já importados no Pi (dev) — medir a taxa de
"pendente" por nota, e conferir manualmente uma amostra dos itens que a
cascata classificou automaticamente (cache/regra) para confirmar que a
categoria faz sentido, não só que o código não quebrou.

## Critério de aceite (liga com Success Criteria da spec)

- SC-001: todo item termina classificado ou pendente, nunca indefinido;
  importação nunca bloqueada por causa disso.
- SC-002: fração de itens auto-classificados cresce com o uso.
- SC-003: descrição já classificada manualmente não exige nova
  classificação manual no futuro.
- SC-004: grupo de itens de mesma descrição classificado em uma ação.
- SC-005: correção manual prevalece sobre classificações automáticas
  passadas e futuras da mesma descrição.
- SC-006: prévia de impacto + decisão explícita antes de qualquer
  alteração em massa (exclusão, corrigir a fonte).
- SC-007: mesma taxonomia disponível para reaproveitamento futuro por
  outra fonte de gasto, sem alteração estrutural.
