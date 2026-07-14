# Implementation Plan: Excluir Nota Fiscal

**Branch**: `002-excluir-nota-fiscal` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-excluir-nota-fiscal/spec.md`

## Summary

Adiciona a capacidade de excluir uma nota fiscal já importada, pela UI web
existente (listagem e detalhe de nota). A exclusão é total e em cascata:
remove a nota, seus itens, o(s) registro(s) de envio que a originaram e
o(s) arquivo(s) físicos (foto/PDF) desses envios — sem deixar rastro em
disco nem no banco. Como os índices únicos de `chave_acesso`/
`hash_conteudo` são parciais (só cobrem linhas existentes), excluir a linha
libera automaticamente a chave/hash para reimportação, sem necessidade de
lógica adicional de "desbloqueio". Não há tabela nem dependência nova —
reaproveita o schema, as rotas Flask e os templates Jinja já existentes da
feature 001.

## Technical Context

**Language/Version**: Python 3.11+ (mesmo ambiente da feature 001).

**Primary Dependencies**: `Flask` (rota nova no blueprint existente);
stdlib `sqlite3` e `os`/`pathlib` (remoção de arquivo). Nenhuma dependência
nova.

**Storage**: SQLite (`data/financiall.db`, tabelas `nota_fiscal`,
`item_nota`, `envio_ocr` já existentes — nenhuma migração de schema) +
arquivos em disco (`data/uploads`, referenciados por
`envio_ocr.caminho_arquivo`).

**Testing**: `pytest` — testes de unidade para a função de exclusão no
repositório (cascata correta, retorno dos caminhos de arquivo a remover,
comportamento quando a nota não existe) e testes de integração ponta a
ponta via cliente de teste do Flask (`DELETE /notas/<id>` seguido de
reimportação da mesma chave/hash), mesmo padrão de `tests/unit` e
`tests/integration` da feature 001.

**Target Platform**: mesmo servidor (Raspberry Pi / self-hosted via
`waitress`) e mesma UI web servida pelo Flask.

**Project Type**: Web service single-project (Flask backend + templates
Jinja server-renderizados) — mesma estrutura da feature 001, sem novo
projeto/pasta.

**Performance Goals**: não crítico — uso pessoal, volume de dezenas de
notas; exclusão deve responder em menos de 1s.

**Constraints**: a exclusão de `nota_fiscal` + `item_nota` + `envio_ocr`
MUST ser atômica (uma transação SQL única) — uma falha no meio do caminho
não pode deixar itens órfãos nem a nota "meio excluída". A remoção do
arquivo físico em disco acontece após a transação confirmar (SQLite não
torna I/O de arquivo transacional) e é best-effort: arquivo já ausente não
é erro.

**Scale/Scope**: 1 rota HTTP nova, 1 função de repositório nova, ajuste em
2 templates existentes (`notas.html`, `nota_detalhe.html`) para expor a
ação de excluir.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Simplicidade e Manutenibilidade**: PASS. Reaproveita blueprint Flask,
  `sqlite3` cru e templates Jinja já existentes; nenhuma dependência,
  camada de abstração ou ferramenta de migração nova é introduzida.
- **II. Idempotência é Obrigatória**: PASS — e reforçada. Os índices únicos
  parciais (`WHERE chave_acesso IS NOT NULL` / `WHERE hash_conteudo IS NOT
  NULL`) já existentes liberam a chave/hash automaticamente quando a linha
  é excluída; a reimportação (US2) funciona pela mesma garantia estrutural
  que impede duplicidade, sem exceção especial.
- **III. Tratamento de Erro Explícito em Entradas Externas**: PASS.
  Exclusão de nota/envio inexistente retorna erro tratado (404 + mensagem
  em português), nunca uma exceção não tratada; falha ao remover o arquivo
  físico (ex.: já apagado por fora do sistema) é tratada como best-effort e
  não interrompe a exclusão dos dados no banco.
- **IV. Dados Financeiros São Sensíveis**: PASS. Mensagens de confirmação e
  erro reaproveitam o mascaramento de chave já existente
  (`_mascarar_chave`); nenhum log novo grava CPF/chave/valor em claro.
- **V. Testável por Construção**: PASS, com nota. Excluir/reimportar não é
  uma das três rotinas citadas literalmente pelo princípio (extração de
  chave, dedup, parsing), mas toca diretamente a garantia de idempotência
  (Princípio II, NON-NEGOTIABLE) — por isso o ciclo excluir → reimportar
  (US2) recebe teste automatizado com o mesmo rigor, cobrindo o caminho
  feliz e a ausência de bloqueio residual.
- **VI. Português nos Artefatos Voltados ao Usuário**: PASS. Confirmação,
  mensagens de sucesso e de erro da exclusão em português.
- **VII. Fontes Frágeis Degradam sem Quebrar o Fluxo Principal**: N/A —
  esta feature não integra nenhuma fonte externa nova.

Nenhuma violação identificada. Complexity Tracking não se aplica.

## Project Structure

### Documentation (this feature)

```text
specs/002-excluir-nota-fiscal/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── storage/
│   └── db.py                  # + excluir_nota(nota_id, db_path) -> lista de caminhos de arquivo | None
├── services/
│   └── exclusao.py            # novo — orquestra: chama storage_db.excluir_nota, remove arquivos (best-effort)
├── api/
│   ├── routes_importar.py     # + rota DELETE /notas/<int:nota_id>
│   └── templates/
│       ├── notas.html         # + botão "Excluir" por linha, com confirmação
│       └── nota_detalhe.html  # + botão "Excluir", com confirmação

tests/
├── unit/
│   └── test_exclusao.py       # cascata, múltiplos envios, nota inexistente
└── integration/
    └── test_api.py            # + casos: DELETE /notas/<id>, reimportação pós-exclusão
```

**Structure Decision**: projeto único (mesma estrutura da feature 001);
nenhum diretório novo no nível raiz. A exclusão ganha um módulo de serviço
próprio (`services/exclusao.py`) para separar a orquestração (banco +
disco) das rotas HTTP, seguindo o mesmo padrão de `services/importador.py`
e `services/fila_processamento.py`.

## Complexity Tracking

> Não se aplica — nenhuma violação da Constitution Check.
