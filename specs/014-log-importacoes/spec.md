# Feature Specification: Log de importações

**Feature Branch**: `014-log-importacoes`

**Created**: 2026-09-10

**Status**: Draft

**Input**: User description: "Log de importações: toda vez que uma importação de extrato/fatura/Open Finance for processada (via processar_transacoes, o ponto central usado por todos os importadores: Itaú CC, Itaú cartão, BB, Mercado Pago, Open Finance Itaú, upload web), o sistema deve registrar automaticamente um evento de histórico com: data/hora da importação, fonte (nome do arquivo ou dump), período coberto (data mínima e máxima entre os registros importados naquela execução), e as contagens já calculadas no resumo (importadas, já existentes, puladas, classificadas automaticamente, pendentes de natureza, reconciliadas, ambíguas). Esse histórico deve ficar visível numa página nova do financiALL (lista ordenada da mais recente pra mais antiga), pra que o usuário e o agente consigam checar rapidamente quando foi a última importação de cada fonte e o que ela cobriu, sem precisar acessar o banco de produção diretamente via SSH. Motivação: hoje, pra saber se um extrato já tinha sido importado (ex.: extrato Itaú de agosto/2026 via Open Finance), foi preciso consultar o banco de produção manualmente por SSH -- isso deve virar uma consulta simples na própria interface do app."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Saber quando foi a última importação de cada fonte, sem acessar o servidor (Priority: P1)

O usuário (ou o agente de IA que o ajuda) precisa descobrir se um extrato
ou fatura específico já foi importado, e até que data ele cobriu. Hoje
isso só é possível consultando o banco de produção diretamente por SSH.
Ele quer ver, numa página do próprio financiALL, o histórico de todas as
importações já feitas, da mais recente para a mais antiga.

**Why this priority**: é o problema central que motiva a feature — sem
isso, a única forma de responder "isso já foi importado?" continua sendo
acesso direto ao servidor.

**Independent Test**: pode ser testado rodando uma importação (por
qualquer via já existente: script CLI ou upload web) e conferindo que um
evento novo aparece no topo da página de histórico, com fonte, período e
contagens corretas.

**Acceptance Scenarios**:

1. **Given** uma importação de extrato/fatura/Open Finance já processada
   com sucesso, **When** o usuário abre a página de histórico de
   importações, **Then** ele vê um evento com data/hora da importação,
   fonte (nome do arquivo/dump), período coberto (data mínima e máxima
   dos registros) e as contagens do resumo (importadas, já existentes,
   puladas, classificadas automaticamente, pendentes de natureza,
   reconciliadas, ambíguas).
2. **Given** várias importações já feitas ao longo do tempo, **When** o
   usuário abre a página, **Then** os eventos aparecem ordenados da mais
   recente para a mais antiga.
3. **Given** uma importação feita por qualquer um dos caminhos existentes
   (script CLI de Itaú CC, Itaú cartão, BB, Mercado Pago, Open Finance
   Itaú, ou upload web), **When** ela é processada, **Then** um evento de
   histórico correspondente é registrado automaticamente, sem exigir
   nenhuma ação manual adicional do usuário.

---

### User Story 2 - Confiar no histórico mesmo quando a importação não traz nada novo (Priority: P2)

O usuário reenvia um extrato já importado antes (ou um período sem
transações novas). Ele quer que o evento apareça no histórico do mesmo
jeito, mostrando que rodou e não trouxe nada novo — em vez de o histórico
ficar em silêncio e dar a falsa impressão de que a importação não
aconteceu.

**Why this priority**: reforça a confiabilidade do histórico como fonte
única de verdade, mas não bloqueia o caminho feliz da User Story 1.

**Independent Test**: pode ser testado reimportando um arquivo já
processado anteriormente e conferindo que um evento novo aparece no
histórico com "0 importadas" e a contagem de "já existentes" correta.

**Acceptance Scenarios**:

1. **Given** um arquivo/dump cujas transações já foram todas importadas
   antes, **When** ele é processado novamente, **Then** um evento de
   histórico é registrado mesmo assim, mostrando 0 transações novas
   importadas e a contagem real de "já existentes".
2. **Given** uma importação cujos registros não têm nenhuma data válida
   (todos pulados por dado inválido), **When** ela é processada, **Then**
   o evento é registrado sem período coberto (em vez de quebrar ou
   inventar um período).

---

### Edge Cases

- Uma execução de importação processa zero registros (arquivo vazio ou
  filtro sem resultado) — o evento ainda deve ser registrado, com
  contagens zeradas e sem período coberto.
- Duas importações da mesma fonte em datas próximas (ex.: mesmo dump
  Open Finance reprocessado) devem gerar dois eventos distintos no
  histórico, não substituir um pelo outro — o histórico é um registro de
  execuções, não um resumo por fonte.
- Uma importação falha antes de terminar (exceção durante o
  processamento) não deve gerar um evento de histórico parcial/incorreto.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE registrar automaticamente um evento de
  histórico toda vez que uma importação de extrato/fatura/Open Finance
  for processada com sucesso, independente do caminho de entrada (script
  CLI ou upload web).
- **FR-002**: Cada evento de histórico DEVE conter: data/hora em que a
  importação foi executada, a fonte (nome do arquivo ou dump importado),
  o período coberto (data mínima e máxima entre os registros processados
  naquela execução, quando houver ao menos um registro com data válida),
  e as contagens do resumo da importação (transações importadas, já
  existentes, puladas por dado inválido, classificadas automaticamente,
  pendentes de revisão de natureza, reconciliadas com nota fiscal, e
  casos ambíguos de reconciliação).
- **FR-003**: O sistema DEVE expor uma página nova, dentro do financiALL,
  listando os eventos de histórico ordenados da execução mais recente
  para a mais antiga.
- **FR-004**: Um evento de histórico DEVE ser registrado mesmo quando a
  importação não traz nenhuma transação nova (todas já existentes, ou
  arquivo/dump vazio) — o histórico reflete que a execução aconteceu, não
  só quando ela trouxe novidade.
- **FR-005**: Quando nenhum registro da execução tiver data válida, o
  evento de histórico DEVE ser registrado sem período coberto, em vez de
  falhar ou de inferir um período incorreto.
- **FR-006**: Uma importação que falhar antes de concluir o processamento
  (exceção, arquivo ilegível) NÃO DEVE gerar um evento de histórico.
- **FR-007**: O histórico de importações DEVE persistir entre reinícios
  do serviço (não é um dado apenas de memória).

### Key Entities

- **Evento de Importação**: representa uma única execução de importação
  já concluída. Atributos: data/hora da execução, fonte (arquivo/dump de
  origem), período coberto (data mínima e máxima dos registros
  processados, opcional), e as contagens do resumo (importadas, já
  existentes, puladas, classificadas automaticamente, pendentes de
  natureza, reconciliadas, ambíguas). Não se relaciona diretamente a
  Transação individual — é um registro agregado por execução.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O usuário (ou o agente de IA que o ajuda) consegue
  responder "quando foi a última importação desta fonte e o que ela
  cobriu?" só olhando a página de histórico, sem precisar de acesso ao
  servidor de produção.
- **SC-002**: 100% das importações concluídas com sucesso, por qualquer
  caminho de entrada existente, geram exatamente um evento de histórico
  correspondente.
- **SC-003**: O histórico permanece correto e consultável mesmo após o
  reinício do serviço.

## Assumptions

- Esta feature não altera nenhum parser de importação existente nem a
  lógica de deduplicação de transação (Princípio II) — só acrescenta um
  registro de auditoria em torno do ponto central já usado por todos os
  importadores (`processar_transacoes`).
- Não há necessidade de autenticação/permissão diferenciada para ver essa
  página — mesmo modelo de acesso das demais páginas do financiALL (uso
  pessoal, rede local).
- Não há requisito de retenção/expurgo do histórico — o volume esperado
  (poucas importações por mês) não justifica limpeza automática por
  enquanto.
- Uma execução do script `importar_extrato_itau_cc.py` (ou equivalente)
  que processa vários arquivos de uma pasta em sequência conta como uma
  execução por arquivo, já que cada arquivo passa por uma chamada
  independente a `processar_transacoes`.
