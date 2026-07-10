# Quickstart: Validar a Feature 001 (Importar NFC-e sem Duplicar)

## Pré-requisitos

- Python 3.11+ instalado.
- Dependências instaladas (`requests`, `click`, `pytest` — ver
  `pyproject.toml`/`requirements.txt` gerados na fase de implementação).
- Um arquivo SQLite novo (ex.: `financiall.db`), criado automaticamente na
  primeira execução via `src/storage/db.py`.
- Uma URL de QR Code de NFC-e real (ou uma chave de 44 dígitos válida) para
  o teste do caminho feliz, e uma chave inválida (comprimento errado ou
  dígito verificador errado) para o teste de rejeição.

## Cenário 1 — Importar nota nova via URL (US1)

```bash
python -m src.cli.main importar "https://www.sefaz.<uf>.gov.br/.../?p=<44-digitos>|2|1|..."
```

**Esperado**: saída `Nota importada com sucesso...` (ou `...com dados
parciais (pendente de revisão)...` se a fonte de detalhamento estiver fora
do ar) e código de saída `0`. Confirma FR-001, FR-002, FR-007, contrato
`importar` em [contracts/cli.md](./contracts/cli.md).

## Cenário 2 — Importar a mesma nota via chave colada (US1 + US2)

```bash
python -m src.cli.main importar "  <44-digitos-com-espacos>  "
```

**Esperado**: se a chave já foi importada no Cenário 1, a saída MUST ser
`Nota já registrada em ...` (código `0`), e o comando `listar` (Cenário 4)
MUST continuar mostrando exatamente uma nota com essa chave — nunca duas.
Confirma FR-003, FR-005, FR-006 (idempotência, Princípio II).

## Cenário 3 — Rejeitar entrada inválida (US1 cenário 3)

```bash
python -m src.cli.main importar "12345"
```

**Esperado**: `Erro: não foi possível identificar uma chave de acesso
válida de 44 dígitos em "12345".`, código de saída `1`, nenhuma linha nova
em `listar`. Confirma FR-004.

## Cenário 4 — Listar notas importadas (US4)

```bash
python -m src.cli.main listar
```

**Esperado**: uma linha por nota, com data de emissão, emitente, total e
status (`completa` ou `pendente de revisão`). Com a base vazia, a saída
MUST ser `Nenhuma nota importada ainda.`. Confirma FR-009.

## Cenário 5 — Ver resumo mensal (US5)

```bash
python -m src.cli.main resumo-mensal
```

**Esperado**: uma linha por mês com ao menos uma nota, total e contagem de
notas, com o cabeçalho deixando explícito que o total é **parcial** (só
notas fiscais). Com a base vazia, a saída MUST ser `Nenhuma nota importada
ainda — sem dados para o resumo mensal.`. Confirma FR-010, SC-005.

## Cenário 6 — Degradação graciosa quando a fonte de detalhamento falha (US3)

Simular indisponibilidade da fonte (ex.: apontar para uma chave válida cuja
consulta à SEFAZ retorna erro/timeout, ou desconectar a rede):

```bash
python -m src.cli.main importar "<44-digitos-validos-fonte-indisponivel>"
```

**Esperado**: a nota é gravada mesmo assim (UF, CNPJ do emitente e ano-mês
de emissão vêm da própria chave — ver research.md #5), com status `pendente
de revisão`, e o comando não lança exceção nem interrompe o processo.
Confirma FR-008, Princípio VII.

## Verificação final

Rodar a suíte automatizada, que cobre os mesmos cenários de forma
determinística (sem depender de rede real):

```bash
pytest tests/unit tests/integration tests/contract
```

Todos os testes MUST passar antes de considerar a feature pronta para
revisão (Princípio V).
