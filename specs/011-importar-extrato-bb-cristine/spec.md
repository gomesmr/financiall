# Feature Specification: Importar extrato BB (Cristine) e visão por titular

**Feature Branch**: `011-importar-extrato-bb-cristine`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Importar extrato bancário do Banco do Brasil (conta da Cristine) para o financiALL, estendendo a feature 010 (importar extrato bancário) que hoje só cobre as contas do Marcelo (Itaú + Flash). Trazer o financiALL ao nível de mostrar corretamente o que foi gasto no mês e em que, para as duas contas do casal, e permitir receber novos extratos no futuro."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Importar o histórico real do extrato BB da Cristine (Priority: P1)

O usuário já tem 5 arquivos de extrato da conta corrente do Banco do Brasil da Cristine, referentes a janeiro–maio/2026, baixados do internet banking. Ele quer que essas transações entrem no financiALL com a mesma qualidade que as do Marcelo: sem duplicata, com natureza classificada (gasto/renda/transferência), e reconciliadas com notas fiscais já importadas quando aplicável.

**Why this priority**: Sem isso, "o que foi gasto no mês" no financiALL mostra só a metade do orçamento do casal (só Marcelo) — é o gargalo que bloqueia todo o resto do pedido.

**Independent Test**: Pode ser testado rodando a importação histórica contra os 5 arquivos reais e conferindo no banco que as transações da Cristine aparecem, sem duplicata, com natureza atribuída.

**Acceptance Scenarios**:

1. **Given** os 5 arquivos de extrato BB da Cristine (jan–mai/2026) ainda não importados, **When** a importação histórica é executada, **Then** todas as transações reais (excluindo linhas de saldo) são gravadas, cada uma associada à titular Cristine.
2. **Given** uma transação já importada de um arquivo de extrato BB, **When** a importação é executada novamente (ex.: o mesmo arquivo baixado de novo, ou um novo arquivo que sobrepõe datas já cobertas), **Then** nenhuma transação é duplicada.
3. **Given** uma transação do extrato BB cuja data e valor casam com uma nota fiscal já importada (ex.: compra reconciliável), **When** a importação roda, **Then** a transação é automaticamente reconciliada com a nota, do mesmo jeito que já acontece para o Marcelo.

---

### User Story 2 - Ver o gasto do mês quebrado por titular (Priority: P1)

Hoje o resumo mensal mostra apenas o consolidado do casal. O usuário quer conseguir ver quanto cada um (Marcelo, Cristine) gastou no mês e em quê, além do total conjunto.

**Why this priority**: É o valor final que o usuário pediu explicitamente ("exibir corretamente o que foi gasto no mês e em que") — sem quebra por titular, gastos de um mascaram os do outro.

**Independent Test**: Pode ser testado abrindo o resumo mensal com dados de ambos os titulares e conferindo que dá pra ver o total e o detalhamento (por categoria) de cada pessoa separadamente, além do conjunto.

**Acceptance Scenarios**:

1. **Given** transações de Marcelo e de Cristine no mesmo mês, **When** o usuário abre o resumo mensal, **Then** ele vê o total gasto de cada titular separadamente, além do total do casal.
2. **Given** um titular selecionado, **When** o usuário navega para o detalhamento por categoria, **Then** só as transações daquele titular aparecem.
3. **Given** uma transferência de dinheiro de um titular para o outro (ex.: Cristine envia para Marcelo), **When** o resumo mensal é calculado, **Then** essa transferência não é contada como gasto nem como renda de nenhum dos dois — é movimentação interna do casal, não duplica o saldo conjunto.

---

### User Story 3 - Continuar recebendo extratos novos (Priority: P2)

O usuário vai continuar baixando extratos periodicamente — tanto faturas/extratos do Itaú (Marcelo) quanto extratos do BB (Cristine). Ele quer um caminho claro para importar cada arquivo novo sem duplicar o que já existe e sem precisar reconstruir o histórico inteiro toda vez.

**Why this priority**: Garante que o trabalho da US1 não vire um evento único — o financiALL precisa continuar confiável conforme novos meses chegam.

**Independent Test**: Pode ser testado baixando um extrato com um período que se sobrepõe parcialmente ao já importado e confirmando que só as transações novas (fora da sobreposição) entram.

**Acceptance Scenarios**:

1. **Given** um novo arquivo de extrato (Itaú ou BB) com transações de um período parcialmente já coberto, **When** ele é importado, **Then** só as transações ainda não vistas são adicionadas.
2. **Given** um novo arquivo de extrato do BB, **When** ele é importado, **Then** ele passa pelo mesmo pipeline de classificação e reconciliação que os arquivos históricos.

---

### Edge Cases

- Uma transação do extrato BB tem "Tipo Lançamento" explícito (Entrada/Saída) na própria linha — diferente do formato Itaú, que infere o tipo pelo sinal do valor. O sistema deve confiar no tipo informado pelo BB em vez de tentar re-derivá-lo.
- Linhas de "Saldo Anterior" e "Saldo do dia" aparecem no extrato BB mas não são transações reais — devem ser ignoradas na importação.
- Valores no extrato BB usam formatação brasileira (ex.: "1.234,56") — precisam ser convertidos corretamente para o valor numérico interno.
- Uma transferência entre o casal aparece nos dois extratos ao mesmo tempo (saída no extrato de quem envia, entrada no extrato de quem recebe) — não pode ser contada como despesa de um lado e renda do outro, sob risco de distorcer o saldo conjunto.
- Um arquivo de extrato BB de um titular desconhecido (nem Marcelo nem Cristine) não deve quebrar a importação — deve cair em fila de revisão manual, como já acontece hoje para estabelecimento não identificado.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE reconhecer e importar o formato de extrato de conta corrente do Banco do Brasil (colunas Data, Lançamento, Detalhes, N° documento, Valor, Tipo Lançamento).
- **FR-002**: O sistema DEVE ignorar linhas de saldo (ex.: "Saldo Anterior", "Saldo do dia") durante a importação, tratando-as como não-transacionais.
- **FR-003**: Cada transação importada DEVE ser associada a um titular (Marcelo ou Cristine), determinado pela conta bancária de origem do arquivo.
- **FR-004**: O sistema DEVE evitar duplicar uma transação já importada, mesmo que o mesmo arquivo (ou um arquivo com sobreposição de período) seja importado novamente.
- **FR-005**: Transações importadas do extrato BB DEVEM passar pelo mesmo pipeline de classificação de natureza (gasto, renda, transferência interna, pagamento de fatura, estorno) já usado para as transações do Marcelo.
- **FR-006**: Transações importadas do extrato BB DEVEM ser candidatas à reconciliação automática com notas fiscais já importadas, do mesmo jeito que as transações do Marcelo.
- **FR-007**: O sistema DEVE importar o histórico real dos 5 arquivos de extrato BB já baixados (janeiro a maio de 2026) da Cristine.
- **FR-008**: O resumo mensal DEVE mostrar o total gasto de cada titular separadamente, além do total consolidado do casal.
- **FR-009**: O usuário DEVE conseguir ver o detalhamento de gasto por categoria filtrado por um titular específico.
- **FR-010**: Uma transferência de dinheiro entre os dois titulares do casal NÃO DEVE ser contada como gasto nem como renda no resumo mensal de nenhum dos dois lados.
- **FR-011**: O sistema DEVE continuar suportando a importação incremental de novos arquivos de extrato — tanto do formato Itaú (já suportado) quanto do formato BB (novo) — sem exigir reimportação do histórico inteiro.
- **FR-012**: Ao exibir uma transação numa visão consolidada do casal, o sistema DEVE indicar a qual titular ela pertence.

### Key Entities

- **Transação**: passa a carregar o titular (Marcelo ou Cristine) responsável pela conta de origem, além dos atributos já existentes (data, descrição, valor, tipo, natureza, categoria, estabelecimento, conciliação com nota fiscal).
- **Titular**: identifica a pessoa (Marcelo ou Cristine) dona da conta de origem de uma transação; já existe hoje como atributo em Nota Fiscal, passa a existir também em Transação.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: As 5 planilhas de extrato BB já baixadas (jan–mai/2026) são importadas com 100% das transações reais capturadas e zero duplicata.
- **SC-002**: O usuário consegue ver o total gasto de cada titular no mês, individualmente, sem cálculo manual.
- **SC-003**: Transferências entre o casal não geram distorção no saldo mensal conjunto (o saldo consolidado do casal bate com renda total menos gasto total, sem contar a transferência como gasto ou renda).
- **SC-004**: Um novo extrato baixado (Itaú ou BB) pode ser importado e refletido no resumo mensal sem exigir reconstrução do histórico já importado.

## Assumptions

- A conta do BB da Cristine é uma única conta corrente; compras no cartão dela aparecem diretamente no extrato da conta corrente (linhas "Compra com Cartão"), não em uma fatura de cartão separada — confirmado observando os arquivos reais já baixados.
- Titular é um atributo de duas opções fixas (Marcelo, Cristine), reaproveitando o mesmo conjunto de valores já usado hoje em Nota Fiscal.
- Uma transferência entre o casal é reconhecível pela descrição da transação (ex.: menção ao nome da outra pessoa) em ambos os extratos, do mesmo jeito que transferências internas entre contas do Marcelo já são reconhecidas hoje.
- O formato de exportação do extrato do BB (nome das colunas, ordem) permanece estável entre downloads futuros; se o banco mudar o layout, é esperado que a importação caia em revisão manual em vez de falhar silenciosamente.
- Esta feature não reproduz a lógica de orçamento (orçado vs. real, percentuais por categoria) das planilhas legadas — isso fica fora de escopo, como já indicado no pedido original.
