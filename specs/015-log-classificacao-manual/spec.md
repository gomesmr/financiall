# Feature Specification: Log de classificação manual de natureza

**Feature Branch**: `015-log-classificacao-manual`

**Created**: 2026-09-10

**Status**: Draft

**Input**: User description: "Log de classificação manual de transações: hoje não existe nenhum histórico de quando/o quê foi alterado ao classificar manualmente a natureza (gasto/renda/transferência interna/pagamento de fatura/estorno de crédito) de uma transação pendente -- nem pela fila de pendentes (POST /transacoes/pendentes/classificar-grupo, que classifica todas as transações com a mesma descrição normalizada de uma vez) nem pela edição individual (PUT /transacoes/<id>/natureza). O sistema deve registrar automaticamente um evento de histórico toda vez que uma classificação manual de natureza acontecer -- data/hora, descrição normalizada (ou id da transação, no caso de edição individual), natureza atribuída, categoria atribuída (quando aplicável), método (classificação em grupo pela fila de pendentes vs. edição individual), e quantas transações foram afetadas por aquele evento. Esse histórico deve ficar visível numa página nova do financiALL (lista ordenada da mais recente pra mais antiga), no mesmo espírito da página /ver/log-importações que já existe (feature 014) -- mesma motivação: poder checar rapidamente o que já foi classificado e como, sem precisar acessar o banco de produção diretamente. Motivação concreta: hoje eu (o usuário) pedi para o agente de IA classificar manualmente os itens mais óbvios da fila de pendentes de natureza (57 transações em ~41 grupos), e não há nenhum registro consultável dessa ação depois que ela acontece -- se algo for classificado errado, não há como saber quando/como aconteceu sem lembrar de cabeça. Fora de escopo nesta feature: histórico de classificação de categoria de item de nota fiscal (já existe uma tabela histórico_classificacao_item para isso, mas sem página de visualização -- pode ser tratado como feature separada no futuro, não misturar escopo aqui)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Saber o que foi classificado manualmente e como, sem acessar o servidor (Priority: P1)

O usuário (ou o agente de IA que o ajuda) classifica manualmente a
natureza de transações pendentes — em grupo, pela fila de pendentes, ou
individualmente. Mais tarde, ele precisa conferir o que foi feito: que
natureza/categoria foi atribuída, quando, e a quantas transações aquilo
se aplicou. Hoje isso só seria possível lembrando de cabeça ou
consultando o banco de produção diretamente.

**Why this priority**: é o problema central que motiva a feature — sem
isso, não há como auditar uma classificação manual depois que ela
acontece.

**Independent Test**: pode ser testado classificando um grupo pendente
(ou uma transação individual) e conferindo que um evento novo aparece no
topo da página de histórico, com natureza, categoria (quando aplicável),
método e quantidade de transações afetadas corretos.

**Acceptance Scenarios**:

1. **Given** um grupo de transações pendentes de natureza, **When** o
   usuário (ou o agente) classifica esse grupo inteiro de uma vez pela
   fila de pendentes, **Then** um evento de histórico é registrado com
   data/hora, a descrição normalizada do grupo, a natureza atribuída, a
   categoria atribuída (quando a natureza é "gasto"), o método "em
   grupo" e a quantidade de transações afetadas.
2. **Given** uma transação específica, **When** o usuário edita sua
   natureza individualmente, **Then** um evento de histórico é
   registrado com data/hora, o identificador da transação, a natureza e
   categoria atribuídas, o método "individual" e quantidade afetada
   igual a 1.
3. **Given** vários eventos de classificação já registrados, **When** o
   usuário abre a página de histórico, **Then** ele vê os eventos
   ordenados do mais recente para o mais antigo.

---

### User Story 2 - Confiar no histórico mesmo numa reclassificação (Priority: P2)

O usuário percebe que uma classificação anterior estava errada e
reclassifica o mesmo grupo (ou a mesma transação) com uma natureza/
categoria diferente. Ele quer que o histórico mostre as duas tentativas,
não apenas a mais recente — para conseguir reconstruir o que aconteceu
se precisar investigar um erro.

**Why this priority**: reforça a confiabilidade do histórico como fonte
de auditoria, mas não bloqueia o caminho feliz da User Story 1.

**Independent Test**: pode ser testado classificando o mesmo grupo duas
vezes com naturezas diferentes e conferindo que dois eventos distintos
aparecem no histórico, na ordem certa.

**Acceptance Scenarios**:

1. **Given** um grupo já classificado anteriormente, **When** ele é
   reclassificado com uma natureza/categoria diferente, **Then** um novo
   evento de histórico é registrado (não substitui o evento anterior),
   e ambos ficam visíveis na página, o mais recente primeiro.

---

### Edge Cases

- Uma tentativa de classificação em grupo que não afeta nenhuma
  transação (ex.: descrição normalizada sem nenhuma transação pendente
  correspondente) não deve gerar um evento de histórico enganoso — ver
  Requisitos Funcionais para o comportamento esperado.
- Uma tentativa de classificação com dado inválido (natureza inexistente,
  categoria obrigatória ausente para "gasto") que a validação já recusa
  hoje não deve gerar nenhum evento de histórico.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE registrar automaticamente um evento de
  histórico toda vez que uma classificação manual de natureza for
  aplicada com sucesso, seja em grupo (fila de pendentes) ou
  individualmente (edição de uma transação específica).
- **FR-002**: Cada evento de histórico DEVE conter: data/hora da
  classificação, identificação do alvo (descrição normalizada do grupo,
  ou identificador da transação individual), a natureza atribuída, a
  categoria atribuída (quando a natureza é "gasto"; ausente nos demais
  casos), o método usado ("em grupo" ou "individual"), e a quantidade de
  transações efetivamente afetadas por aquele evento.
- **FR-003**: O sistema DEVE expor uma página nova, dentro do
  financiALL, listando os eventos de histórico de classificação
  ordenados da mais recente para a mais antiga.
- **FR-004**: Uma reclassificação (mesmo grupo ou transação já
  classificado antes, com natureza/categoria diferente) DEVE gerar um
  novo evento de histórico, sem apagar ou substituir eventos anteriores.
- **FR-005**: Uma tentativa de classificação em grupo que não afeta
  nenhuma transação (quantidade afetada igual a zero) NÃO DEVE gerar um
  evento de histórico.
- **FR-006**: Uma tentativa de classificação recusada pela validação já
  existente (natureza inválida, categoria obrigatória ausente) NÃO DEVE
  gerar nenhum evento de histórico.
- **FR-007**: O histórico de classificação manual DEVE persistir entre
  reinícios do serviço (não é um dado apenas de memória).

### Key Entities

- **Evento de Classificação Manual**: representa uma única ação de
  classificação de natureza já concluída com sucesso (em grupo ou
  individual). Atributos: data/hora, alvo (descrição normalizada do
  grupo, ou id da transação), natureza atribuída, categoria atribuída
  (opcional), método (em grupo/individual), quantidade de transações
  afetadas. Não se relaciona diretamente a uma linha específica de
  Transação — é um registro por ação de classificação, podendo
  representar várias transações afetadas de uma vez (caso "em grupo").

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O usuário (ou o agente de IA que o ajuda) consegue
  responder "o que foi classificado manualmente, quando e como?" só
  olhando a página de histórico, sem precisar de acesso ao servidor de
  produção.
- **SC-002**: 100% das classificações manuais de natureza aplicadas com
  sucesso (em grupo ou individual) geram exatamente um evento de
  histórico correspondente.
- **SC-003**: Uma reclassificação nunca apaga o registro da
  classificação anterior — o histórico acumula, não sobrescreve.
- **SC-004**: O histórico permanece correto e consultável mesmo após o
  reinício do serviço.

## Assumptions

- Esta feature não altera a lógica de validação nem o comportamento
  existente de `POST /transacoes/pendentes/classificar-grupo` e
  `PUT /transacoes/<id>/natureza` — só acrescenta um registro de
  auditoria em torno dessas duas operações já existentes.
- Fora de escopo: histórico de classificação de categoria de item de
  nota fiscal (já existe `historico_classificacao_item`, sem página de
  visualização — feature candidata separada no futuro).
- Fora de escopo: qualquer forma de "desfazer" uma classificação a
  partir do histórico — esta feature é só de consulta/auditoria.
- Não há necessidade de autenticação/permissão diferenciada para ver
  essa página — mesmo modelo de acesso das demais páginas do financiALL.
- Não há requisito de retenção/expurgo do histórico — volume esperado
  (dezenas a poucas centenas de eventos) não justifica limpeza
  automática por enquanto.
