# Feature Specification: Importar Histórico Financeiro

**Feature Branch**: `004-importar-historico-financeiro`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: "Importar histórico financeiro: trazer para o financiALL as notas fiscais já capturadas no sistema anterior do usuário. Escopo é só notas fiscais — extrato bancário fica para uma feature futura separada. Introduzir um campo 'titular' em nota_fiscal (Marcelo/Cristine), sem autenticação. Importação idempotente por chave de acesso. É uma migração pontual de dados legados, não um canal de entrada recorrente pela UI web. Notas importadas entram com status 'completa' e sem categoria atribuída."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trazer o histórico de notas para a base única (Priority: P1)

Como usuário, quero importar de uma vez as notas fiscais que eu já tinha capturado no meu sistema anterior, para não perder esse registro de gastos passados e ter tudo reunido no financiALL (Identidade do Projeto: base única).

**Why this priority**: é o propósito inteiro da feature — sem isso, o histórico fica perdido num sistema paralelo, contrariando o princípio de base única do projeto.

**Independent Test**: rodar a importação sobre o arquivo de histórico atual e verificar que todas as notas dele aparecem na listagem de notas do financiALL, com seus itens.

**Acceptance Scenarios**:

1. **Given** o arquivo de histórico contém notas que ainda não existem no financiALL, **When** a importação é executada, **Then** cada uma dessas notas passa a existir na base, com seus itens, emitente, data e valor total.
2. **Given** uma nota do histórico já existe na base (mesma chave de acesso — ex.: importada antes por outro canal), **When** a importação é executada, **Then** essa nota não é duplicada.
3. **Given** o arquivo de histórico está ausente ou não pode ser interpretado, **When** a importação é executada, **Then** o processo informa um erro claro e não grava nenhum dado parcial.

---

### User Story 2 - Saber de quem é cada nota (Priority: P2)

Como usuário, quero ver e filtrar as notas por titular (Marcelo ou Cristine), já que o histórico mistura notas dos dois, para conseguir separar os gastos de cada um quando precisar.

**Why this priority**: agrega valor de organização, mas a US1 já entrega o objetivo central (não perder o histórico) mesmo sem essa distinção visível.

**Independent Test**: após a importação, abrir a listagem de notas e verificar que cada nota mostra seu titular; aplicar o filtro por titular e verificar que só as notas daquela pessoa aparecem.

**Acceptance Scenarios**:

1. **Given** notas importadas com titulares diferentes, **When** o usuário abre a listagem de notas, **Then** cada nota mostra de quem é (Marcelo ou Cristine).
2. **Given** notas de titulares diferentes na base, **When** o usuário filtra a listagem por um titular específico, **Then** só as notas daquele titular aparecem.

---

### User Story 3 - Reexecutar a importação com segurança (Priority: P3)

Como usuário, quero poder rodar a importação de novo no futuro (ex.: depois de adicionar mais notas ao arquivo do sistema antigo), sem me preocupar em duplicar o que já foi importado.

**Why this priority**: é um reforço de robustez sobre a US1 — a importação já nasce idempotente (Princípio II, não-negociável), mas vale confirmar esse comportamento como cenário próprio, já que é isso que torna a rotina segura de repetir.

**Independent Test**: rodar a importação duas vezes seguidas sobre o mesmo arquivo e verificar que a segunda execução não altera a quantidade de notas na base.

**Acceptance Scenarios**:

1. **Given** a importação já foi executada uma vez, **When** ela é executada novamente sobre o mesmo arquivo, **Then** nenhuma nota é duplicada e a base permanece com a mesma quantidade de notas de antes.
2. **Given** o arquivo de histórico ganhou notas novas desde a última execução, **When** a importação é executada de novo, **Then** só as notas novas são adicionadas — as já existentes permanecem intactas.

---

### Edge Cases

- Nota do histórico sem nenhum item associado é importada mesmo assim (só a nota, sem itens) — não é tratada como erro.
- Nota do histórico com titular ausente ou não reconhecido (nem Marcelo nem Cristine) é importada com o titular marcado como "não identificado", em vez de falhar a importação inteira.
- Uma execução que falha no meio (ex.: processo interrompido) não deixa a base com uma nota gravada sem seus itens correspondentes.
- Rodar a importação sem nenhuma nota nova no arquivo (tudo já importado antes) conclui normalmente, informando que nada novo foi adicionado.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST importar, a partir do arquivo de histórico, todas as notas que ainda não existem na base (por chave de acesso), gravando cada nota com seus itens.
- **FR-002**: O sistema MUST identificar notas do histórico cuja chave de acesso já existe na base e não gravá-las novamente (mesma garantia de idempotência já aplicada às demais fontes de entrada).
- **FR-003**: Cada nota importada do histórico MUST registrar um titular (Marcelo ou Cristine), a partir da informação já presente no histórico.
- **FR-004**: O sistema MUST exibir o titular de cada nota na listagem e na tela de detalhe de notas.
- **FR-005**: O usuário MUST poder filtrar a listagem de notas por titular.
- **FR-006**: A importação MUST poder ser executada mais de uma vez sem duplicar notas já importadas, adicionando apenas as que forem novas no arquivo.
- **FR-007**: Se o arquivo de histórico estiver ausente ou não puder ser interpretado, o sistema MUST informar um erro claro em português e não gravar nenhum dado parcial.
- **FR-008**: Notas importadas do histórico MUST entrar com status "completa" (os dados já vêm completos na fonte).
- **FR-009**: Notas importadas do histórico MUST iniciar sem categoria atribuída (a categorização continua manual, pela funcionalidade já existente).
- **FR-010**: Ao final de uma execução, o sistema MUST informar quantas notas foram importadas e quantas já existiam (não precisaram ser gravadas de novo).

### Key Entities

- **Nota Fiscal** (já existente): ganha o atributo "titular" (Marcelo, Cristine, ou não identificado).
- **Item da Nota** (já existente): populado a partir dos itens já detalhados no histórico.
- **Arquivo de Histórico**: fonte externa de dados legados, lida uma vez por execução da importação — não é uma entidade persistida na base, apenas a origem dos dados trazidos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das notas do arquivo de histórico que ainda não existiam na base aparecem na listagem de notas depois da importação.
- **SC-002**: Rodar a importação duas vezes seguidas sobre o mesmo arquivo nunca resulta em nenhuma nota duplicada.
- **SC-003**: O usuário identifica o titular de qualquer nota (histórica ou nova) sem precisar abrir o detalhe — visível direto na listagem.
- **SC-004**: O usuário consegue restringir a listagem de notas a um único titular.
- **SC-005**: Um arquivo de histórico ausente ou corrompido nunca deixa a base num estado parcial ou inconsistente (nota sem itens, item sem nota).

## Assumptions

- A fonte do histórico é o arquivo já existente do sistema anterior do usuário (notas fiscais com chave de acesso, CNPJ, emitente, data, total e itens já estruturados); o caminho do arquivo é fixo/conhecido pelo responsável do projeto, não é enviado pelo usuário via upload nesta feature.
- A importação é uma rotina executada manualmente pelo responsável do projeto (fora da UI web), por ser uma migração pontual de dados legados — não um canal de entrada recorrente como os já existentes (URL/chave, foto/PDF).
- O campo "titular" do histórico mapeia diretamente para o campo equivalente já presente na fonte de dados original.
- Detalhes de desconto e unidade de medida dos itens do histórico, quando não tiverem campo correspondente no schema atual, não são importados nesta feature — não bloqueia o objetivo central de preservar o gasto histórico.
- Extrato bancário/fatura e categorias herdadas do sistema anterior continuam fora de escopo desta feature (decisão já tomada antes de abrir esta spec).
- Não há diferenciação de permissões entre Marcelo e Cristine para visualizar ou filtrar notas de qualquer titular — consistente com a decisão de não ter autenticação no sistema (mesma suposição das features 002/003).
