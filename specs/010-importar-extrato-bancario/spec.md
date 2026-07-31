# Feature Specification: Importar Extrato Bancário

**Feature Branch**: `010-importar-extrato-bancario`

**Created**: 2026-07-20

**Status**: Draft

**Input**: User description: "Importar extrato bancário e fatura de cartão para o financiALL, convergindo para a mesma base única de nota fiscal (Identidade do Projeto). Nova entidade Transacao com três campos de classificação em cascata: tipo (Entrada/Saída, cru do extrato), natureza (gasto/renda/transferencia_interna/pagamento_fatura/estorno_credito — classificado por cache/regra/manual) e categoria_id (só quando natureza=gasto, reaproveitando a taxonomia hierárquica da feature 008). Seed inicial de regras de natureza migrado das REGRAS já existentes no script legado (importar_extrato.py), preservando o conhecimento de classificação já capturado em vez de recomeçar do zero. Reconciliação Nota Fiscal ↔ Transação é obrigatória nesta fase (match por valor + janela de data + pista de emitente), evitando dupla contagem: relatórios passam a somar transações com natureza=gasto mais notas ainda não reconciliadas, calculado ao vivo em cada consulta. O sistema MUST permitir desfazer/corrigir manualmente uma reconciliação incorreta. Reconciliação Cartão↔Pagamento-de-Fatura fica para uma fase futura. Migração histórica lê o registro.json já processado pelo script legado (418 transações) como fonte primária, normalizando contas duplicadas do legado. A planilha serve de checagem de sanidade, não fonte primária. Parser de importação recorrente começa pelo formato Itaú cartão XLS, desenhado como adaptador plugável. Nova entidade Estabelecimento (identidade por CNPJ/CPF quando disponível, fallback por descrição normalizada) com fila de gerenciamento no mesmo padrão da fila de pendentes de item (feature 008). gasto_por_estabelecimento passa a incluir transações sem nota."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Classificar automaticamente a natureza de cada transação (Priority: P1)

Como usuário, quero que cada transação de extrato (compra, salário, transferência, pagamento de fatura, estorno) receba automaticamente uma "natureza" a partir de regras já validadas no meu processo anterior, para não ter que reclassificar manualmente milhares de lançamentos que já sabíamos identificar.

**Why this priority**: sem essa classificação, nenhuma outra parte da feature funciona — é o que distingue um gasto real de uma movimentação interna, e é o alicerce que evita contar dinheiro duas vezes.

**Independent Test**: aplicar o motor de classificação a um conjunto de transações com descrições conhecidas (ex.: "TBI ALUGUEL", "PAGTO SALARIO", "FATURA PAGA") e verificar que cada uma recebe a natureza correspondente sem ação manual.

**Acceptance Scenarios**:

1. **Given** uma transação cuja descrição casa uma regra de natureza aprovada, **When** ela é processada, **Then** recebe a natureza definida pela regra automaticamente.
2. **Given** uma transação com `natureza = gasto`, **When** ela é classificada, **Then** o sistema também tenta atribuir uma categoria de gasto usando a mesma cascata cache/regra já existente para itens de nota fiscal (feature 008).
3. **Given** uma transação cuja descrição normalizada já foi classificada manualmente antes, **When** uma nova transação com a mesma descrição normalizada aparece, **Then** ela recebe a mesma natureza automaticamente (cache), sem repetir o trabalho manual.
4. **Given** uma transação cuja descrição não casa nenhuma regra nem cache, **When** ela é processada, **Then** fica marcada como "natureza pendente de revisão", sem travar a importação.

---

### User Story 2 - Trazer o histórico de transações para a base única sem perder nem duplicar nada (Priority: P1)

Como usuário, quero importar de uma vez as transações de extrato que já processei no meu sistema anterior (script `importar_extrato.py`), para não perder esse histórico e ter tudo reunido no financiALL junto com as notas fiscais.

**Why this priority**: é o propósito central da feature — sem isso, o histórico de extrato fica só no sistema legado, contrariando a base única.

**Independent Test**: rodar a importação sobre o histórico já processado e verificar que todas as transações aparecem na base, cada uma com sua natureza (ou pendente de revisão quando a classificação automática não resolve).

**Acceptance Scenarios**:

1. **Given** o histórico contém transações que ainda não existem na base (por fingerprint), **When** a importação é executada, **Then** cada uma passa a existir na base, já classificada pela US1 quando possível.
2. **Given** uma transação do histórico já existe na base (mesmo fingerprint), **When** a importação é executada, **Then** essa transação não é duplicada.
3. **Given** o histórico tem a mesma conta física registrada sob nomes diferentes (ex.: "2486" e "Itaú_2486"), **When** a importação é executada, **Then** ambas são consolidadas sob uma única identidade de conta.
4. **Given** a importação já foi executada uma vez, **When** ela é executada novamente sobre o mesmo histórico, **Then** nenhuma transação é duplicada e a contagem na base permanece a mesma.

---

### User Story 3 - Ver o gasto do mês sem contar a mesma compra duas vezes (Priority: P1)

Como usuário, quero que uma compra que aparece tanto na fatura do cartão (transação) quanto no cupom fiscal (nota) seja contada uma única vez no meu gasto do mês, para que os relatórios financeiros continuem confiáveis depois que o extrato passa a alimentar a mesma base que as notas.

**Why this priority**: é o requisito não-negociável da feature — sem ele, unir extrato e nota fiscal na mesma base introduz um risco real de inflar os relatórios já em produção (features 005/009).

**Independent Test**: importar uma nota fiscal e a transação de cartão correspondente à mesma compra (mesmo valor, data próxima), verificar que o sistema associa as duas, e que o resumo do mês soma esse gasto uma única vez.

**Acceptance Scenarios**:

1. **Given** uma transação com `natureza = gasto` e uma nota fiscal com valor e data compatíveis, **When** o sistema tenta reconciliar, **Then** a transação passa a referenciar a nota, e o gasto passa a exibir o detalhe item a item da nota, contando o valor uma única vez.
2. **Given** uma transação sem nenhuma nota fiscal correspondente, **When** o gasto do mês é calculado, **Then** essa transação soma normalmente pelo seu próprio valor e categoria.
3. **Given** uma nota fiscal sem nenhuma transação correspondente (ex.: compra em dinheiro), **When** o gasto do mês é calculado, **Then** essa nota soma normalmente pelo seu valor, sem esperar por uma reconciliação que pode nunca acontecer.
4. **Given** mais de uma transação é candidata plausível para a mesma nota (mesmo valor, mesma janela de data), **When** a reconciliação automática não consegue decidir, **Then** o caso fica numa fila de revisão manual, e nenhuma das duas soma a nota duas vezes enquanto isso.
5. **Given** uma transação foi reconciliada automaticamente com a nota errada, **When** o usuário identifica o erro, **Then** ele consegue desfazer essa reconciliação manualmente, e o gasto volta a ser contado corretamente (transação e nota separadas).

---

### User Story 4 - Classificar manualmente as transações que a regra não resolveu (Priority: P2)

Como usuário, quero ver uma fila das transações com natureza pendente e classificá-las eu mesmo, para que toda transação acabe com uma natureza definida mesmo quando as regras herdadas do sistema anterior não cobrem um caso novo.

**Why this priority**: reforça a US1 para o resíduo que as regras não cobrem; sem isso, transações ficariam pendentes para sempre e sairiam dos relatórios de gasto.

**Independent Test**: pegar uma transação com natureza pendente, atribuir manualmente (e categoria, se for gasto), confirmar que ela passa a contar no relatório certo, e que uma nova transação futura com a mesma descrição normalizada recebe automaticamente a mesma classificação.

**Acceptance Scenarios**:

1. **Given** existe ao menos uma transação com natureza pendente, **When** o usuário abre a fila de pendentes, **Then** ele vê as transações agrupadas por descrição normalizada, para classificar ocorrências repetidas de uma vez.
2. **Given** o usuário atribui natureza (e categoria, quando aplicável) a um grupo de transações pendentes de mesma descrição, **When** ele confirma, **Then** todas elas são classificadas numa única ação, e a classificação vira cache para transações futuras com a mesma descrição.
3. **Given** uma transação já classificada automaticamente está errada, **When** o usuário corrige manualmente, **Then** a correção prevalece e passa a valer para futuras transações da mesma descrição normalizada.

---

### User Story 5 - Identificar o estabelecimento de cada transação (Priority: P2)

Como usuário, quero atribuir um nome legível e um tipo a cada estabelecimento que aparece nas minhas transações (ex.: transformar "SJX COM DE ALIM LTDA" em "SJX Comercial" do tipo "Supermercado"), para poder ver meu gasto agrupado por estabelecimento mesmo quando a compra não tem nota fiscal.

**Why this priority**: agrega valor de organização e alimenta `gasto_por_estabelecimento`, mas os relatórios de gasto por categoria (US1-US3) já funcionam sem essa identificação.

**Independent Test**: com uma transação cujo estabelecimento nunca foi identificado, abrir a fila de gerenciamento, atribuir nome fantasia e tipo, e verificar que a transação passa a aparecer com esses dados e que `gasto_por_estabelecimento` passa a contá-la.

**Acceptance Scenarios**:

1. **Given** existe uma transação sem estabelecimento identificado, **When** o usuário abre a fila de gerenciamento, **Then** ele vê as transações agrupadas por CNPJ/CPF (quando disponível) ou por descrição normalizada (quando não há documento).
2. **Given** o usuário atribui nome fantasia e tipo a um grupo, **When** ele confirma, **Then** todas as transações daquele CNPJ/CPF ou descrição passam a exibir esses dados, e transações futuras com a mesma identidade herdam a classificação automaticamente.
3. **Given** uma transação foi reconciliada com uma nota fiscal que traz CNPJ, **When** já existe um estabelecimento identificado antes por descrição para a mesma loja, **Then** o sistema não cria duas identidades conflitantes — o CNPJ da nota prevalece como identidade principal.
4. **Given** transações com estabelecimento identificado, **When** o usuário consulta o gasto por estabelecimento de um mês, **Then** transações sem nota fiscal aparecem agrupadas pelo estabelecimento identificado, ao lado das notas.

---

### User Story 6 - Importar extratos novos continuamente (Priority: P3)

Como usuário, quero processar um novo arquivo de fatura de cartão (formato Itaú) assim que eu baixar do banco, para manter a base atualizada sem depender só da migração histórica única.

**Why this priority**: estende o valor da feature para o futuro, mas a base já é útil e consistente com o histórico migrado (US1-US3) mesmo antes de existir um parser recorrente.

**Independent Test**: rodar a importação sobre um arquivo de fatura Itaú novo (formato XLS) e verificar que as transações dele aparecem na base, classificadas quando possível, sem duplicar as que já vieram da migração histórica.

**Acceptance Scenarios**:

1. **Given** um arquivo de fatura Itaú (XLS) com transações que ainda não existem na base, **When** a importação é executada, **Then** cada transação nova é gravada com o mesmo fingerprint e a mesma cascata de classificação usados na migração histórica.
2. **Given** o arquivo contém uma transação já importada anteriormente (pela migração histórica ou por uma execução anterior deste parser), **When** a importação é executada, **Then** essa transação não é duplicada.
3. **Given** o arquivo de fatura está ausente ou não pode ser interpretado, **When** a importação é executada, **Then** o sistema informa um erro claro em português e não grava dado parcial.

---

### Edge Cases

- Transação de cartão com valor negativo (estorno/crédito de uma compra anterior) recebe `natureza = estorno_credito`, não `renda`.
- Transação sem descrição reconhecível (linha malformada do extrato) fica com natureza pendente diretamente, sem tentar casar cache ou regra.
- A conta do Banco do Brasil (Cristine) não tem nenhuma transação processada no histórico legado — a migração desta feature não cobre essa conta; fica disponível para quando o parser desse formato for priorizado.
- Reprocessar o mesmo arquivo de extrato (migração histórica ou parser recorrente) não duplica nem perde nenhuma transação.
- Uma nota fiscal e uma transação com valores muito próximos mas não idênticos (ex.: arredondamento) não reconciliam automaticamente — ficam como candidatas na fila de revisão em vez de casar por aproximação silenciosa.
- Uma transação classificada como `pagamento_fatura` nunca soma no gasto do mês, independente de ter sido reconciliada com as compras do cartão que ela liquidou (essa reconciliação fina fica para uma fase futura).
- Transferência entre as contas do próprio casal (`transferencia_interna`) nunca soma como gasto nem como renda.
- Uma execução de importação que falha no meio do processo não deixa a base com uma transação gravada sem seus dados obrigatórios (fingerprint, tipo, valor, conta).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST manter, para cada transação, um campo `tipo` (Entrada ou Saída) copiado diretamente do sinal registrado no extrato de origem, nunca inferido.
- **FR-002**: O sistema MUST classificar cada transação com uma `natureza` dentre um conjunto fechado de valores (gasto, renda, transferência interna, pagamento de fatura, estorno/crédito), usando uma cascata cache → regra aprovada → pendente de revisão, sem exigir ação do usuário antes de considerar a transação pendente.
- **FR-003**: O sistema MUST atribuir uma categoria de gasto (reaproveitando a taxonomia hierárquica da feature 008) a toda transação classificada com `natureza = gasto`, e somente a essas; as demais naturezas não usam essa taxonomia.
- **FR-004**: O sistema MUST semear as regras de classificação de natureza a partir do conhecimento já capturado no script `importar_extrato.py` do sistema anterior, em vez de exigir que o usuário reconstrua essas regras do zero.
- **FR-005**: Quando a descrição normalizada de uma transação já tiver uma classificação de natureza confirmada anteriormente (manual ou por regra aprovada), o sistema MUST reaproveitar essa classificação para toda nova transação com a mesma descrição normalizada.
- **FR-006**: O sistema MUST oferecer uma fila de transações com natureza pendente de revisão, agrupadas por descrição normalizada, permitindo classificar ocorrências repetidas numa única ação.
- **FR-007**: O usuário MUST poder corrigir manualmente a natureza (e a categoria, quando aplicável) de qualquer transação já classificada; a correção manual MUST prevalecer sobre qualquer classificação automática e passar a valer para futuras transações da mesma descrição normalizada.
- **FR-008**: O sistema MUST importar, a partir do histórico já processado pelo sistema anterior, todas as transações que ainda não existem na base (deduplicadas por fingerprint), preservando data, descrição, valor, tipo e conta de origem.
- **FR-009**: A importação do histórico MUST poder ser executada mais de uma vez sem duplicar transações já importadas.
- **FR-010**: A migração do histórico MUST consolidar contas do sistema anterior que representam a mesma conta física sob nomes diferentes, sob uma única identidade de conta na base nova.
- **FR-011**: O sistema MUST tentar reconciliar toda transação com `natureza = gasto` a uma nota fiscal correspondente, usando valor, janela de data compatível com o tipo de conta (débito vs. cartão de crédito) e pistas de emitente na descrição como critérios de match.
- **FR-012**: Quando uma transação reconcilia com uma nota fiscal, o sistema MUST usar o detalhe item a item da nota para compor o gasto por categoria daquela transação, sem somar o valor da nota separadamente do valor da transação.
- **FR-013**: Quando existe mais de uma transação candidata plausível para a mesma nota fiscal (mesmo valor, mesma janela de data), o sistema MUST colocar o caso numa fila de revisão manual em vez de decidir automaticamente por aproximação.
- **FR-014**: O usuário MUST poder desfazer manualmente uma reconciliação entre nota fiscal e transação, mesmo quando ela foi decidida automaticamente e sem ambiguidade.
- **FR-015**: O gasto do mês (e o gasto por categoria) MUST ser calculado somando as transações com `natureza = gasto` mais as notas fiscais que não estão reconciliadas a nenhuma transação, recalculado a cada consulta, nunca contando a mesma compra duas vezes.
- **FR-016**: Transações com `natureza` diferente de `gasto` (renda, transferência interna, pagamento de fatura, estorno/crédito) MUST NOT ser somadas como gasto em nenhum relatório.
- **FR-017**: O sistema MUST manter uma entidade de estabelecimento, identificada primariamente por CNPJ/CPF quando disponível (de nota fiscal reconciliada ou de dado presente na própria descrição da transação, como em PIX) e, na ausência de documento, por descrição normalizada.
- **FR-018**: O usuário MUST poder atribuir um nome fantasia e um tipo de estabelecimento (reaproveitando a mesma taxonomia de tipo de estabelecimento já usada por nota fiscal, feature 003) a um grupo de transações não identificadas, numa única ação; essa atribuição MUST valer automaticamente para transações futuras da mesma identidade (CNPJ/CPF ou descrição).
- **FR-019**: Quando uma transação identificada por descrição normalizada posteriormente reconcilia com uma nota fiscal que traz CNPJ, o sistema MUST tratar o CNPJ como a identidade definitiva do estabelecimento, sem manter duas identidades conflitantes para o mesmo estabelecimento.
- **FR-020**: O relatório de gasto por estabelecimento MUST incluir transações sem nota fiscal correspondente, agrupadas pelo estabelecimento identificado a partir da transação.
- **FR-021**: Toda transação MUST registrar um titular (Marcelo, Cristine, ou não identificado), seguindo o mesmo padrão já usado por nota fiscal (feature 004).
- **FR-022**: O sistema MUST oferecer um parser de importação recorrente para o formato de fatura de cartão Itaú (XLS), desenhado de forma que novos formatos possam ser adicionados como adaptadores independentes, sem alterar o desenho da entidade de transação nem o motor de classificação.
- **FR-023**: O fingerprint gerado pelo parser de importação recorrente MUST seguir a mesma fórmula usada na migração do histórico, garantindo que a mesma transação processada por qualquer um dos dois caminhos nunca seja gravada duas vezes.
- **FR-024**: Se um arquivo de extrato (histórico ou recorrente) estiver ausente ou não puder ser interpretado, o sistema MUST informar um erro claro em português e não gravar dado parcial.
- **FR-025**: CPF, CNPJ, número de conta e valores de transação MUST seguir o mesmo tratamento de dado sensível já aplicado a nota fiscal — nunca em log, stack trace ou mensagem de diagnóstico em texto claro.

### Key Entities

- **Transação** (nova): representa um lançamento de extrato bancário ou fatura de cartão. Tem tipo (Entrada/Saída), natureza (gasto/renda/transferência interna/pagamento de fatura/estorno-crédito), categoria (só quando natureza=gasto), conta, titular, fingerprint (chave de dedupe), e uma referência opcional à nota fiscal que a reconcilia.
- **Estabelecimento** (nova): identifica quem recebeu uma transação. Identidade primária por CNPJ/CPF, com fallback por descrição normalizada. Tem nome fantasia e um tipo (reaproveitando a taxonomia de tipo de estabelecimento já usada por nota fiscal).
- **Regra de Natureza / Cache de Descrição-Natureza** (nova): mecanismo de classificação automática de natureza, análogo à Regra de Classificação e ao Cache de Descrição já existentes para itens de nota fiscal (feature 008), mas aplicado ao domínio de natureza de transação em vez de categoria de item.
- **Categoria** (já existente, feature 008): reaproveitada sem alteração estrutural para classificar transações com natureza=gasto, e para o tipo de estabelecimento.
- **Nota Fiscal** (já existente): ganha uma referência de reconciliação vinda da transação correspondente; seu valor deixa de ser somado isoladamente quando reconciliada.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das transações do histórico já processado pelo sistema anterior aparecem na base depois da migração.
- **SC-002**: Rodar a migração do histórico duas vezes seguidas nunca resulta em nenhuma transação duplicada.
- **SC-003**: Uma compra registrada tanto por nota fiscal quanto por transação de extrato nunca é contada mais de uma vez no gasto de nenhum mês.
- **SC-004**: A fração de transações classificadas automaticamente (natureza e categoria, sem ação manual) é alta desde o primeiro uso, graças às regras migradas do sistema anterior, e cresce com o tempo de uso.
- **SC-005**: O usuário consegue corrigir uma reconciliação incorreta ou uma classificação incorreta a qualquer momento, e a correção nunca é revertida por uma nova execução de importação.
- **SC-006**: O usuário identifica o estabelecimento de qualquer transação (por nome legível, não pela descrição crua do banco) sem precisar reclassificar a mesma loja mais de uma vez.
- **SC-007**: Um arquivo de extrato ausente ou corrompido nunca deixa a base num estado parcial ou inconsistente.

## Assumptions

- A reconciliação entre transações de cartão e o respectivo pagamento de fatura na conta corrente (match 1 pagamento : N compras do ciclo) fica fora do escopo desta feature — a classificação `natureza = pagamento_fatura` já é suficiente para excluir essa transação da soma de gasto, sem depender desse match fino. Fica reservada como evolução futura, focada em conferência/navegação, não em corretude do total.
- A conta do Banco do Brasil (Cristine) fica fora do escopo da migração histórica desta feature, porque o histórico já processado pelo sistema anterior não contém nenhuma transação dela; pode ser coberta quando o parser desse formato for priorizado.
- Subclassificação de renda (salário vs. distribuição de lucros vs. rendimento de aplicação) fica fora do escopo desta versão — toda entrada classificada como `renda` recebe esse valor único de natureza, sem detalhamento adicional.
- A planilha de orçamento (Marcelo.xlsx/Cristine.xlsx) é usada apenas como checagem de sanidade dos totais após a migração, não como fonte de dados da importação — sua granularidade de transação é insuficiente em Gastos Fixos e Receitas, e as linhas de Gastos à Vista já vêm agregadas manualmente.
- O parser de importação recorrente cobre inicialmente só o formato de fatura de cartão Itaú (XLS); os demais formatos do sistema anterior (conta corrente Itaú, Flash VR, Banco do Brasil) ficam para fases seguintes, usando o mesmo desenho de adaptador plugável.
- Não há diferenciação de permissões entre Marcelo e Cristine para visualizar ou classificar transações de qualquer titular — consistente com a ausência de autenticação já assumida pelas features anteriores.
- A fila de gerenciamento de estabelecimento é uma superfície visual nova e, por isso, exige verificação visual real (captura de tela via navegador headless + checagem de ausência de erro de console) antes de ser promovida para produção, seguindo o mesmo padrão já aplicado à fila de pendentes de item (feature 008, Princípio VIII da constituição).
- Reconciliação Nota Fiscal ↔ Transação usa janelas de data diferentes por tipo de conta (compra no débito casa em poucos dias; compra no cartão de crédito pode aparecer só no fechamento do ciclo, semanas depois) — os valores exatos dessas janelas ficam para a fase de planejamento técnico (`/speckit-plan`), não para esta especificação.
