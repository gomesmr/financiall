# Implementation Plan: Importar NFC-e sem Duplicar

**Branch**: `001-importar-nfce` | **Date**: 2026-07-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-importar-nfce/spec.md`

## Summary

Importar uma NFC-e a partir da URL do QR Code ou da chave de acesso de 44
dígitos colada, extrair/validar a chave, checar duplicidade antes de gravar
(idempotência não-negociável), buscar best-effort os dados completos da nota
(emitente, data, total, itens) e persistir tudo em uma base local única do
financiALL. Expor `importar`, `listar` e `resumo-mensal` como uma CLI Python
fina sobre uma biblioteca de domínio testável, com SQLite como armazenamento.
O resumo mensal é explicitamente parcial (só notas fiscais) nesta feature.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `requests` (busca HTTP à fonte de detalhamento da
nota), `httpx`/`requests` com timeout explícito, biblioteca padrão
`xml.etree.ElementTree`/`html.parser` para extrair dados da resposta da
SEFAZ, `click` (ou `argparse` da stdlib) para a CLI, `pytest` para testes.
Sem framework web nesta feature — ver Project Type.

**Storage**: SQLite (arquivo local, ex.: `financiall.db`) — um único arquivo
por instalação, sem servidor, alinhado à Restrição de Projeto (pessoa física,
uso individual) e ao Princípio I (simplicidade).

**Testing**: `pytest`, com testes de unidade (extração de chave, validação
de dígito verificador, dedup, parsing de itens) e testes de integração da
CLI (comandos ponta a ponta contra um banco SQLite temporário).

**Target Platform**: Execução local (desktop, Linux/Windows/macOS) via
Python — sem dependência de SO específico.

**Project Type**: CLI de linha de comando sobre uma biblioteca de domínio
(`single project`). Não há requisito de UI web nesta feature; a lógica de
domínio (extração de chave, dedup, obtenção de dados, cálculo de resumo)
fica isolada em uma camada de serviço/biblioteca reutilizável, para que uma
futura interface (web, por exemplo) possa reaproveitá-la sem reescrita —
consistente com a Identidade do Projeto (base única, "ALL").

**Performance Goals**: Não há meta de performance agressiva — uso pessoal,
dezenas de importações por mês. Cada importação deve completar em segundos
(latência dominada pela chamada de rede best-effort à fonte de
detalhamento, que tem timeout curto para não travar o fluxo principal).

**Constraints**: Sem certificado e-CNPJ (Restrição de Projeto); nenhum dado
sensível (CPF, chave de acesso, CNPJ, valores) em log de texto claro
(Princípio IV); falha da fonte de detalhamento MUST NOT impedir o registro
da nota (Princípio VII); todo texto voltado ao usuário em português
(Princípio VI).

**Scale/Scope**: Uso de uma única pessoa; volume esperado de dezenas a
poucas centenas de notas por mês. Sem necessidade de concorrência
multi-usuário nesta feature.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate (Princípio) | Como esta feature cumpre |
|---|---|
| I. Simplicidade e Manutenibilidade | SQLite em arquivo único, sem ORM nem framework web; CLI fina sobre biblioteca de domínio; nenhuma abstração especulativa (sem filas, sem microsserviços). |
| II. Idempotência é Obrigatória | FR-005/FR-006: chave de acesso é `UNIQUE` na base; toda importação faz *check-before-insert* pela chave antes de qualquer gravação (US2). Testado (ver Gate V). |
| III. Tratamento de Erro Explícito em Entradas Externas | Extração de chave de URL, parsing de resposta HTTP da SEFAZ e leitura de chave colada MUST tratar exceções explicitamente (URL malformada, resposta não-HTTP-200, timeout, HTML inesperado) e nunca propagar stack trace ao usuário (FR-004, US1 cenário 3). |
| IV. Dados Financeiros São Sensíveis | Logging da aplicação MUST mascarar/omitir chave de acesso, CNPJ e valores; nenhuma chamada de rede além da consulta à SEFAZ que já emitiu a nota (FR-011). |
| V. Testável por Construção | Extração/validação de chave (dígito verificador), dedup e parsing de itens têm testes de unidade cobrindo caminho feliz e bordas (chave inválida, resposta vazia, item sem código) antes de qualquer merge. |
| VI. Português nos Artefatos | Mensagens de erro e saída da CLI (`importar`, `listar`, `resumo-mensal`) em português (FR-012). |
| VII. Fontes Frágeis Degradam sem Quebrar o Fluxo | Busca de dados completos na SEFAZ é best-effort com timeout curto; falha grava a nota com o que houver e status "pendente de revisão" (US3, FR-008), nunca aborta a importação. Chave com `modelo` diferente de `65` (ex.: NF-e) é gravada normalmente com os campos decodificados da chave, mas a busca de detalhes não é tentada (portal pesquisado cobre só NFC-e) — cai no mesmo caminho de "pendente de revisão" por construção, sem exceção nem rejeição. |
| Identidade do Projeto (ALL) | Nota Fiscal grava chave de acesso como identificador estável, preparando a futura conciliação com lançamentos de extrato (feature futura) na mesma base SQLite. |

Nenhuma violação identificada. Nenhuma entrada necessária em Complexity
Tracking.

**Re-check pós-Fase 1 (design)**: `data-model.md`, `contracts/cli.md` e
`quickstart.md` confirmam os gates acima sem introduzir desvios — `chave_acesso`
é `UNIQUE` no schema SQLite (Gate II), nenhum campo sensível é citado como
alvo de log (Gate IV), os testes em `tests/unit` cobrem exatamente extração
de chave/dedup/parsing (Gate V), e o contrato da CLI define mensagens em
português para todo caminho de erro (Gate VI) e um caminho explícito de
"dados parciais (pendente de revisão)" sem exceção não tratada (Gates III e
VII). Nenhuma violação nova; Complexity Tracking continua vazio.

## Project Structure

### Documentation (this feature)

```text
specs/001-importar-nfce/
├── plan.md              # Este arquivo (/speckit-plan)
├── research.md          # Fase 0 (/speckit-plan)
├── data-model.md         # Fase 1 (/speckit-plan)
├── quickstart.md         # Fase 1 (/speckit-plan)
├── contracts/            # Fase 1 (/speckit-plan)
│   └── cli.md
└── tasks.md              # Fase 2 (/speckit-tasks — ainda não gerado)
```

### Source Code (repository root)

```text
src/
├── models/
│   ├── nota_fiscal.py       # Entidade NotaFiscal (dataclass/schema + regras)
│   └── item_nota.py         # Entidade ItemNota
├── services/
│   ├── chave_acesso.py      # Extração da URL, normalização, validação (dígito verificador)
│   ├── sefaz_client.py      # Busca best-effort dos dados da nota na SEFAZ (HTTP, timeout, parsing)
│   ├── importador.py        # Orquestra: validar chave -> checar dedup -> buscar dados -> gravar
│   └── resumo.py            # Cálculo do resumo mensal (parcial, só notas fiscais)
├── storage/
│   └── db.py                 # Conexão SQLite, schema, repositório (CRUD por chave de acesso)
└── cli/
    └── main.py                # Comandos `importar`, `listar`, `resumo-mensal`

tests/
├── unit/
│   ├── test_chave_acesso.py  # Extração de URL + validação de dígito verificador (Princípio V)
│   ├── test_importador.py    # Dedup (Princípio II) e degradação best-effort (Princípio VII)
│   └── test_resumo.py        # Agrupamento por mês pela data de emissão
├── integration/
│   └── test_cli.py           # Comandos ponta a ponta contra SQLite temporário
└── contract/
    └── test_cli_contract.py  # Formato de saída/mensagens dos comandos (contracts/cli.md)
```

**Structure Decision**: Opção 1 (single project). Não há frontend nem
serviço web nesta feature — apenas uma CLI Python sobre uma biblioteca de
domínio e um arquivo SQLite local, conforme justificado em Technical
Context e no Gate I (Simplicidade).

## Complexity Tracking

*Sem violações a justificar — tabela omitida intencionalmente.*
