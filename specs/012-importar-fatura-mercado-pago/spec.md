# Feature Specification: Importar fatura do cartão Mercado Pago

**Feature Branch**: `012-importar-fatura-mercado-pago`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Importar fatura do cartão de crédito Mercado Pago (PDF) para o financiALL, seguindo o mesmo padrão de importação recorrente já usado para faturas Itaú e extratos bancários (features 010/011). A fatura do Mercado Pago é exportada em PDF, com seções por cartão vinculado (titular principal e cartões adicionais), uma seção de encargos/juros da própria fatura, e um lançamento de pagamento da fatura anterior que não deve ser contado de novo."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Importar o histórico real da fatura Mercado Pago (Priority: P1)

O usuário já tem uma fatura em PDF do cartão de crédito Mercado Pago (referente a junho/2026) baixada do app. Ele quer que essas transações entrem no financiALL com a mesma qualidade que as do Itaú: sem duplicata, com natureza classificada, e reconciliadas com notas fiscais já importadas quando aplicável.

**Why this priority**: Sem isso, o cartão Mercado Pago fica de fora do "o que foi gasto no mês" — é o gargalo que bloqueia todo o resto do pedido.

**Independent Test**: Pode ser testado rodando a importação contra o arquivo PDF real e conferindo no banco que as transações aparecem, sem duplicata, com natureza atribuída.

**Acceptance Scenarios**:

1. **Given** a fatura PDF de junho/2026 do Mercado Pago ainda não importada, **When** a importação é executada, **Then** todas as compras reais de cada cartão vinculado (ex.: os dois cartões Visa da fatura) são gravadas, cada uma associada à conta do respectivo cartão.
2. **Given** uma fatura já importada, **When** a mesma importação roda de novo, **Then** nenhuma transação é duplicada.
3. **Given** o lançamento de pagamento da fatura anterior (ex.: "Pagamento da fatura de junho/2026"), **When** a importação roda, **Then** esse lançamento não é gravado como gasto (já é contado do lado da conta corrente que pagou a fatura).
4. **Given** lançamentos de encargos da própria fatura (juros de mora, multa por atraso, juros/IOF do rotativo), **When** a importação roda, **Then** esses valores são gravados como gasto, já que representam dinheiro devido de verdade.
5. **Given** uma transação do Mercado Pago cuja data e valor casam com uma nota fiscal já importada, **When** a importação roda, **Then** a transação é automaticamente reconciliada com a nota, do mesmo jeito que já acontece para o Itaú.

---

### User Story 2 - Continuar recebendo faturas novas do Mercado Pago (Priority: P2)

O usuário vai continuar baixando a fatura do Mercado Pago todo mês. Ele quer um caminho claro para importar cada fatura nova sem duplicar o que já existe e sem precisar reconstruir o histórico inteiro toda vez.

**Why this priority**: Garante que o trabalho da US1 não vire um evento único — precisa continuar confiável conforme novas faturas chegam, mês a mês.

**Independent Test**: Pode ser testado importando duas faturas consecutivas (com parcelas recorrentes presentes nas duas) e confirmando que só as transações ainda não vistas entram na segunda importação.

**Acceptance Scenarios**:

1. **Given** uma nova fatura PDF do Mercado Pago com uma parcela recorrente já vista em uma fatura anterior (mesma compra parcelada, parcela seguinte), **When** ela é importada, **Then** a parcela nova entra como transação distinta (data e descrição diferentes da parcela anterior), sem duplicar a parcela já importada.
2. **Given** uma nova fatura PDF do Mercado Pago, **When** ela é importada, **Then** ela passa pelo mesmo pipeline de classificação e reconciliação já usado para as faturas históricas.

---

### Edge Cases

- A fatura traz apenas dia/mês nas linhas de lançamento (sem ano) — o ano de cada transação deve ser inferido a partir da data de emissão da fatura, considerando que parcelas de compras antigas podem aparecer com mês posterior ao mês de fechamento (ex.: fatura fechada em junho trazendo uma parcela original de dezembro do ano anterior).
- Uma fatura pode ter mais de um cartão vinculado (titular principal e cartões adicionais); cada cartão deve virar uma conta distinta dentro do financiALL, para não misturar o consumo de pessoas diferentes sob o mesmo rótulo.
- A linha "Total" ao final de cada seção de cartão não é uma transação — deve ser ignorada.
- Um estorno/crédito de uma compra anterior (ex.: cancelamento) deve ser reconhecido como entrada, não como gasto — mesma lógica já aplicada às faturas Itaú.
- Um arquivo de fatura corrompido ou com formato inesperado (ex.: mudança de layout do Mercado Pago) não deve gravar dado parcial — a importação inteira aborta e nada é persistido.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE reconhecer e importar o formato de fatura em PDF do cartão de crédito Mercado Pago.
- **FR-002**: O sistema DEVE identificar cada seção de cartão vinculado dentro da fatura (ex.: "Cartão Visa [****NNNN]") e associar as transações daquela seção a uma conta distinta por cartão.
- **FR-003**: O sistema DEVE inferir o ano de cada transação a partir da data de emissão da fatura, já que a linha de lançamento só traz dia e mês.
- **FR-004**: O sistema DEVE excluir da importação o lançamento de pagamento da fatura anterior, para não duplicar um valor já contado do lado da conta que pagou.
- **FR-005**: O sistema DEVE importar como gasto os encargos da própria fatura (juros de mora, multa por atraso, juros e IOF do rotativo).
- **FR-006**: O sistema DEVE ignorar linhas que não são transações (linha de cabeçalho de tabela, linha "Total" ao final de cada seção de cartão).
- **FR-007**: O sistema DEVE evitar duplicar uma transação já importada, mesmo que a mesma fatura (ou uma fatura com parcelas recorrentes já vistas) seja importada novamente.
- **FR-008**: Transações importadas da fatura Mercado Pago DEVEM passar pelo mesmo pipeline de classificação de natureza (gasto, renda, transferência interna, estorno) já usado para as transações do Itaú.
- **FR-009**: Transações importadas da fatura Mercado Pago DEVEM ser candidatas à reconciliação automática com notas fiscais já importadas, do mesmo jeito que as transações do Itaú.
- **FR-010**: O sistema DEVE importar o histórico real da fatura de junho/2026 já baixada.
- **FR-011**: Um arquivo de fatura ilegível ou corrompido NÃO DEVE gravar nenhum dado parcial — a importação inteira aborta.

### Key Entities

- **Transação**: mesmos atributos já existentes (data, descrição, valor, tipo, natureza, categoria, conta, titular); a conta passa a incluir também os cartões Mercado Pago (um por cartão vinculado à fatura), além das contas Itaú/Flash/BB já existentes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A fatura de junho/2026 já baixada é importada com 100% das transações reais de compra capturadas e zero duplicata.
- **SC-002**: O lançamento de pagamento da fatura anterior nunca aparece como gasto duplicado no resumo mensal.
- **SC-003**: Uma fatura futura pode ser importada e refletida no resumo mensal sem exigir reconstrução do histórico já importado.

## Assumptions

- Todos os cartões vinculados a esta fatura (titular principal e adicionais) pertencem ao mesmo titular fixo (Marcelo), já que a fatura inteira é emitida em nome dele — mesma convenção hoje usada para os cartões Itaú.
- O formato de exportação da fatura do Mercado Pago (PDF com texto selecionável, não digitalizado/scaneado) permanece estável entre downloads futuros; se o app mudar o layout, é esperado que a importação falhe de forma explícita (erro, sem gravar dado parcial) em vez de interpretar dado errado silenciosamente.
- Esta feature não cobre parcelamento futuro simulado (ofertas de "parcele sua fatura") nem informações de limite/saque — apenas as transações reais já lançadas na fatura.
