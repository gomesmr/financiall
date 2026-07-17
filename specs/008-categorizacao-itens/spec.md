# Feature Specification: Categorização de Itens de Nota Fiscal

**Feature Branch**: `008-categorizacao-itens`

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "Como usuário do financiALL, quero que cada item das notas fiscais já importadas receba automaticamente uma categoria de gasto (por exemplo: alimentação, higiene pessoal, saúde, limpeza), para que eu consiga ver quanto gastei por categoria no mês corrente e no histórico. A categorização precisa funcionar mesmo com as descrições curtas e abreviadas típicas de NFC-e, deve permitir que eu corrija manualmente a categoria de qualquer item, e deve aproveitar categorizações anteriores para exigir menos esforço a cada nova nota. Itens que o sistema não conseguir categorizar com segurança devem ficar pendentes de revisão, sem impedir a importação da nota. A mesma categoria deve poder ser reaproveitada por outras fontes de gasto no futuro (ex.: extrato bancário), preservando a base única do projeto."

## Clarifications

### Session 2026-07-17

- Q: Ao excluir uma categoria/subcategoria em uso (FR-004), o que acontece com os itens, entradas de cache e regras que apontavam para ela? → A: O fluxo de exclusão exige que o usuário decida explicitamente o destino dessas referências antes de confirmar — reatribuí-las a uma categoria substituta ou enviá-las para a fila de pendentes de revisão — em vez de aplicar um comportamento automático único e silencioso.
- Q: Excluir uma categoria de topo (nível 1) que tem subcategorias — o que acontece com as subcategorias dela? → A: Exclusão bloqueada enquanto houver qualquer subcategoria; o usuário precisa excluir (ou mover) as subcategorias antes de poder excluir a categoria de topo.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Classificar itens pendentes manualmente (Priority: P1)

Como usuário, quero ver uma fila dos itens de nota que ainda não têm categoria e atribuir uma categoria a eles, para que todo item acabe categorizado mesmo quando o sistema não consegue decidir sozinho.

**Why this priority**: no v1, sem inteligência artificial, esse é o único caminho garantido de classificação para o que cache e regras não cobrem — é o caminho primário, não uma tela acessória. Sem ele, itens ficariam permanentemente sem categoria.

**Independent Test**: importar uma nota com um item de descrição nunca vista antes, abrir a fila de pendentes, atribuir uma categoria e subcategoria a esse item, e confirmar que ele passa a aparecer classificado.

**Acceptance Scenarios**:

1. **Given** existe pelo menos um item sem categoria, **When** o usuário abre a fila de pendentes, **Then** ele vê os itens pendentes agrupados por descrição normalizada (para classificar ocorrências repetidas de uma vez) e também consegue visualizar por nota (para conferir com o contexto do cupom).
2. **Given** o usuário está na fila de pendentes, **When** ele atribui uma categoria e subcategoria a um item, **Then** o item passa a ter essa classificação e todos os demais itens pendentes com a mesma descrição normalizada recebem a mesma classificação automaticamente.
3. **Given** um item novo sem correspondência em cache ou regra chega numa importação, **When** a nota é processada, **Then** o item fica marcado como "pendente de revisão" e a nota é importada normalmente, sem travar por causa desse item.
4. **Given** um item tem a categoria clara mas a subcategoria é ambígua, **When** o usuário (ou o sistema) resolve só a categoria, **Then** o item fica com a categoria atribuída e a subcategoria continua pendente, em vez de forçar uma escolha de subcategoria incerta.

---

### User Story 2 - Reaproveitar classificações já feitas (Priority: P1)

Como usuário, quero que um item cuja descrição eu já classifiquei antes (nesta nota ou em qualquer nota anterior) receba a mesma categoria automaticamente, para que eu não precise reclassificar a mesma coisa repetidas vezes.

**Why this priority**: é o mecanismo central que faz o esforço de classificação cair com o uso — sem ele, cada nota nova exigiria o mesmo trabalho manual da primeira, o que inviabiliza o v1 local na prática.

**Independent Test**: classificar manualmente um item com uma descrição específica, importar uma nova nota (de qualquer loja) contendo um item com a mesma descrição (ou a mesma descrição normalizada), e confirmar que ele já chega classificado, sem exigir nova ação do usuário.

**Acceptance Scenarios**:

1. **Given** a descrição normalizada de um item já tem uma classificação confirmada (manual ou aprovada), **When** um novo item com a mesma descrição normalizada é importado, **Then** ele recebe automaticamente a mesma categoria, sem passar pela fila de pendentes.
2. **Given** o usuário corrige a categoria de um item já classificado, **When** a correção é salva, **Then** ela passa a valer para futuros itens com a mesma descrição normalizada, sobrepondo qualquer classificação automática anterior daquela descrição.
3. **Given** a mesma nota é reprocessada (reimportação), **When** o reprocessamento ocorre, **Then** nenhuma classificação é duplicada nem perdida — o resultado final é o mesmo de antes do reprocessamento.

---

### User Story 3 - Classificar automaticamente por regra pré-definida (Priority: P2)

Como usuário, quero que itens comuns e ainda não vistos (ex.: um item de um produto conhecido, mesmo em outra loja) já cheguem classificados por uma regra pré-definida, para reduzir a quantidade de itens que caem na fila de pendentes logo no início do uso.

**Why this priority**: reduz o esforço inicial (cold-start), quando o cache ainda está vazio; tem menos impacto que as histórias 1 e 2 porque o sistema continua funcional (com mais itens pendentes) mesmo sem essa cobertura.

**Independent Test**: com uma regra pré-definida ativa para um determinado padrão de descrição, importar uma nota contendo um item que casa esse padrão pela primeira vez, e confirmar que ele chega classificado sem passar pela fila de pendentes.

**Acceptance Scenarios**:

1. **Given** um item novo (sem correspondência em cache) casa uma regra de classificação aprovada, **When** o item é processado, **Then** ele recebe a categoria definida pela regra.
2. **Given** um item casa mais de uma regra aprovada, **When** o item é classificado, **Then** a regra mais específica prevalece sobre a mais genérica.

---

### User Story 4 - Corrigir uma categoria atribuída incorretamente (Priority: P2)

Como usuário, quero corrigir a categoria de um item que foi classificado errado (por cache ou regra), e opcionalmente aplicar essa correção a outras ocorrências passadas da mesma descrição, para não conviver com erros que se repetem nem ter que corrigir item por item.

**Why this priority**: sem correção, um erro de classificação se propagaria indefinidamente via cache/regra para todos os itens futuros da mesma descrição; ainda assim, o valor central da feature (histórias 1-2) já existe mesmo sem esta correção em massa.

**Independent Test**: com um item já classificado incorretamente (e outras ocorrências passadas da mesma descrição também classificadas assim), corrigir a categoria desse item pedindo para também corrigir a fonte, confirmar a prévia de quantos itens serão afetados, aplicar, e verificar que todas as ocorrências passadas da mesma descrição foram atualizadas.

**Acceptance Scenarios**:

1. **Given** um item está classificado incorretamente, **When** o usuário corrige apenas esse item (ação padrão), **Then** só aquele item muda; ocorrências passadas da mesma descrição não são alteradas.
2. **Given** um item está classificado incorretamente por causa de uma regra ou de uma entrada de cache específica, **When** o usuário escolhe explicitamente "corrigir a fonte e reclassificar o passado", **Then** o sistema mostra antes de aplicar quantos itens serão afetados, e só altera os demais itens depois de confirmação.

---

### User Story 5 - Gerenciar a taxonomia de categorias (Priority: P3)

Como usuário, quero criar, renomear e excluir categorias e subcategorias de gasto, para manter a taxonomia ajustada às minhas necessidades sem depender de alteração direta no banco de dados.

**Why this priority**: é gestão de suporte — a taxonomia inicial (semente) já cobre o uso comum; esta história importa para evolução de médio prazo, não para o funcionamento do dia a dia da categorização.

**Independent Test**: criar uma nova subcategoria dentro de uma categoria existente, renomeá-la, e depois excluí-la vendo a prévia de quantos itens/entradas seriam afetados antes de confirmar.

**Acceptance Scenarios**:

1. **Given** o usuário está criando uma categoria ou subcategoria nova, **When** o nome digitado é muito parecido com um já existente, **Then** o sistema avisa da quase-duplicata e sugere usar a existente antes de permitir criar uma nova.
2. **Given** uma categoria ou subcategoria existe, **When** o usuário renomeia, **Then** apenas o nome muda, o identificador permanece o mesmo, e nenhum item precisa ser reprocessado por causa disso.
3. **Given** uma categoria ou subcategoria está em uso por itens, cache ou regras, **When** o usuário pede para excluí-la, **Then** o sistema mostra quantos itens e entradas de cache/regra serão afetados e exige que o usuário escolha explicitamente o destino dessas referências (reatribuir a uma categoria substituta, ou enviar para a fila de pendentes) antes de confirmar a exclusão.
4. **Given** uma categoria de topo tem uma ou mais subcategorias, **When** o usuário pede para excluir a categoria de topo, **Then** o sistema bloqueia a exclusão e informa que as subcategorias precisam ser excluídas (ou movidas) primeiro.

---

### Edge Cases

- Item cuja descrição normalizada nunca foi vista e não casa nenhuma regra aprovada: fica pendente, nota segue importada normalmente (não é erro, é o caminho esperado no cold-start).
- Item "misto" ou kit (uma linha da nota que na prática cobre mais de um tipo de gasto, ex.: cupom com alimentação + limpeza): recebe a categoria do item principal da linha; não é dividido em várias categorias nesta versão.
- Grande volume de itens do histórico já importado (features 001/004) sem categoria: entram no mesmo backlog de pendentes; a feature não exige reclassificar tudo de uma vez antes de ficar disponível.
- Reprocessamento da mesma nota (reimportação): não duplica nem perde classificações já existentes.
- Duas regras aprovadas casam o mesmo item: a mais específica prevalece.
- Exclusão de uma categoria/subcategoria referenciada por itens, entradas de cache e regras: exige prévia do impacto e uma decisão explícita do usuário sobre o destino dessas referências (categoria substituta ou pendente de revisão) antes de aplicar.
- Exclusão de uma categoria de topo que ainda tem subcategorias: bloqueada até que as subcategorias sejam excluídas ou movidas.
- Correção manual de um item entra em conflito com o que cache/regra diriam para a mesma descrição: a correção manual sempre prevalece.
- Item sem descrição (campo ausente/vazio, ex.: falha do OCR ao extrair aquela linha): fica pendente diretamente, sem tentar casar cache ou regra (não é erro, mesmo caminho de "sem correspondência").

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST manter uma taxonomia de categorias de gasto compartilhada por toda a base (não exclusiva de nota fiscal), com dois níveis fixos — categoria e subcategoria — e identificador estável por categoria/subcategoria.
- **FR-002**: O sistema MUST permitir criar uma nova categoria ou subcategoria, avisando antes quando o nome informado for muito parecido com um já existente (quase-duplicata) e sugerindo a existente.
- **FR-003**: O sistema MUST permitir renomear uma categoria ou subcategoria sem alterar seu identificador e sem exigir reprocessamento de itens já classificados.
- **FR-004**: O sistema MUST permitir excluir uma categoria ou subcategoria, mostrando ao usuário, antes de aplicar, quantos itens e entradas de cache/regra seriam afetados pela exclusão; quando houver referências afetadas, o sistema MUST exigir que o usuário escolha explicitamente o destino delas — reatribuir a uma categoria substituta ou enviar para a fila de pendentes de revisão — antes de confirmar (nunca aplicar um destino automático e silencioso).
- **FR-005**: Ao importar uma nota, o sistema MUST tentar classificar automaticamente cada item, sem exigir ação do usuário, antes de considerar o item pendente.
- **FR-006**: Quando a descrição normalizada de um item já tiver uma classificação confirmada anteriormente (manual ou por regra aprovada), o sistema MUST reaproveitar essa classificação para o novo item automaticamente.
- **FR-007**: Quando um item não tiver classificação reaproveitável mas casar uma regra de classificação aprovada, o sistema MUST atribuir a categoria definida pela regra; se mais de uma regra aprovada casar, a mais específica MUST prevalecer sobre a mais genérica.
- **FR-008**: Quando um item não tiver classificação reaproveitável nem casar nenhuma regra aprovada, o sistema MUST marcá-lo como "pendente de revisão" e MUST permitir que a importação da nota prossiga normalmente, sem bloquear por causa desse item.
- **FR-009**: O sistema MUST oferecer uma fila de itens pendentes de revisão, permitindo ao usuário visualizá-los agrupados por descrição normalizada (para classificar ocorrências repetidas de uma vez) e também por nota individual.
- **FR-010**: O usuário MUST poder atribuir categoria (e subcategoria) a um item pendente ou a um grupo de itens pendentes de mesma descrição normalizada em uma única ação; essa atribuição MUST alimentar a classificação automática de itens futuros com a mesma descrição.
- **FR-011**: O sistema MUST permitir resolver apenas a categoria de um item e deixar a subcategoria pendente, quando só o nível mais fino for ambíguo.
- **FR-012**: O usuário MUST poder corrigir a categoria de qualquer item já classificado, a qualquer momento; a correção manual MUST prevalecer sobre qualquer classificação automática (cache ou regra) para aquele item e MUST passar a valer para futuros itens da mesma descrição normalizada.
- **FR-013**: Ao corrigir um item classificado incorretamente por cache ou regra, o padrão MUST ser corrigir apenas aquele item; o sistema MUST oferecer, como ação separada e explícita, corrigir a fonte (cache/regra) e reclassificar ocorrências passadas da mesma descrição — mostrando uma prévia de quantos itens seriam afetados antes de aplicar.
- **FR-014**: O sistema MUST manter, por classificação de item, o método usado (cache, regra ou manual) e o histórico de mudança (classificação anterior e nova) quando um item é reclassificado, para permitir auditoria.
- **FR-015**: O sistema MUST NOT duplicar nem perder classificações de item ao reprocessar uma nota já importada anteriormente.
- **FR-016**: A taxonomia de categorias MUST ser desenhada de forma agnóstica à origem do gasto (nota fiscal hoje; outras fontes, como extrato bancário, no futuro), sem exigir uma base de categorias paralela por fonte.
- **FR-017**: O sistema MUST bloquear a exclusão de uma categoria de topo enquanto ela tiver qualquer subcategoria associada; o usuário MUST excluir (ou mover) as subcategorias antes de poder excluir a categoria de topo.

### Key Entities

- **Categoria**: representa uma categoria ou subcategoria de gasto (ex.: "Alimentação" → "Mercearia seca"). Tem nome, identificador estável, e uma referência à categoria-pai quando é subcategoria (ausente quando é categoria de topo). Estende a categoria de nota fiscal já existente no projeto, agora com hierarquia.
- **Regra de Classificação**: define um padrão de descrição de item associado a uma categoria, usado para classificar itens novos automaticamente. Tem prioridade (mais específica prevalece sobre mais genérica), origem e um estado de aprovação — só regras aprovadas valem.
- **Classificação de Item**: liga um item de nota à categoria atribuída, registrando o método usado (cache, regra ou manual), e o histórico de mudança quando reclassificado.
- **Cache de Descrição**: associação entre uma descrição de item normalizada e a categoria a ela atribuída, usada para reaproveitar classificações já confirmadas em itens futuros com a mesma descrição.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Todo item de toda nota importada termina em um de dois estados possíveis — classificado ou pendente de revisão — nunca em um estado indefinido, e a importação da nota nunca é bloqueada por causa da classificação de um item.
- **SC-002**: A fração de itens classificados automaticamente (sem ação manual do usuário) cresce ao longo do tempo de uso do sistema, à medida que cache e regras acumulam cobertura.
- **SC-003**: Uma descrição de item já classificada manualmente uma vez não volta a exigir classificação manual para a mesma descrição normalizada em nenhuma nota futura.
- **SC-004**: O usuário consegue classificar um grupo de itens pendentes com a mesma descrição em uma única ação, em vez de um item de cada vez.
- **SC-005**: O usuário consegue corrigir a categoria de qualquer item já classificado a qualquer momento, e essa correção prevalece sobre classificações automáticas anteriores e futuras da mesma descrição.
- **SC-006**: Antes de qualquer alteração que afete múltiplos itens ou entradas de cache/regra de uma só vez (ex.: excluir uma categoria, corrigir a fonte de uma classificação), o usuário vê quantos itens seriam afetados e decide explicitamente o que fazer com eles antes de confirmar.
- **SC-007**: A taxonomia de categorias usada para itens de nota fica disponível, sem alteração estrutural, para ser reaproveitada por uma futura fonte de gasto (ex.: extrato bancário).

## Assumptions

- v1 é totalmente local: nenhuma etapa de classificação depende de um serviço de IA externo; IA como camada adicional de classificação é uma fase futura, fora do escopo desta spec.
- A taxonomia inicial (categorias e subcategorias) parte de um rascunho já levantado (alimentação, bebidas, limpeza doméstica, higiene pessoal e perfumaria, saúde/medicamentos, beleza/dermocosméticos, bebê/infantil, pet, casa/bazar/utilidades, outros/não classificado), a ser validada/ajustada como primeira tarefa de implementação; categorias que só farão sentido para uma futura fonte de gasto (ex.: extrato bancário) ficam reservadas na taxonomia desde já, mas fora do escopo de classificação de item nesta feature.
- Regras de classificação pré-definidas ("regras-semente") são criadas a partir da taxonomia inicial para reduzir o volume de itens pendentes desde o primeiro uso; não há mecanismo de sugestão automática de novas regras nesta versão (fica para uma fase futura).
- A categoria hoje é atribuída apenas à nota inteira (feature 003, já existente); esta feature adiciona a categorização por item, sem remover a atribuição por nota já existente — as duas convivem.
- Todo o histórico de notas já importado (features 001 e 004) passa a fazer parte do backlog de itens pendentes de categorização; a feature não exige que esse backlog inteiro seja reclassificado antes de ser considerada pronta.
- Um item "misto" ou de kit recebe a categoria do item principal da linha (uma única categoria por item); divisão de um item em múltiplas categorias fica para uma fase futura.
- Fusão de categorias quase-duplicadas e reclassificação automática em massa de todo o histórico quando a taxonomia evolui ficam para uma iteração seguinte (v1.1); o necessário para v1 nessa frente é: aviso de quase-duplicata na criação, renomear sem reprocessar, e excluir com prévia de impacto.
- Exclusão de categoria/subcategoria segue o mesmo padrão já usado no projeto (exclusão definitiva, não uma marcação de inativo). Diferente da exclusão de categoria de nota já existente (que hoje zera a referência automaticamente), aqui o usuário decide explicitamente o destino de itens/cache/regras afetados (categoria substituta ou pendente) antes de aplicar, dado que uma categoria de item costuma ter muito mais referências em uso.
- Uma categoria de topo só pode ser excluída depois que todas as suas subcategorias forem excluídas ou movidas — não há exclusão em cascata automática.
- Não há necessidade de um limiar numérico de confiança configurável nesta versão: como a classificação automática do v1 é só cache (correspondência exata) ou regra aprovada (correspondência determinística), a ausência de correspondência já é o critério suficiente para marcar um item como pendente.
- Uma superfície visual nova é introduzida (fila de revisão, atribuição e correção de categoria, gestão de taxonomia), exigindo verificação visual real (captura de tela + ausência de erro de console) antes de promover para produção (Princípio VIII da constituição).
- Uma feature futura e separada de identificação de item por código de barras vai reaproveitar a taxonomia e o cache criados aqui, sem bloquear a entrega desta feature.
