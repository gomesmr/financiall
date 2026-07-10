# Feature Specification: Importar NFC-e sem Duplicar

**Feature Branch**: `001-importar-nfce`

**Created**: 2026-07-10

**Status**: Draft

**Input**: User description: "Feature 001 do financiALL: importar uma nota fiscal de consumidor (NFC-e) e registrá-la na base, sem duplicar. Entradas aceitas: URL da SEFAZ que o QR Code do cupom aponta, OU a chave de acesso de 44 dígitos colada diretamente. Extrair/normalizar a chave, obter dados da nota (emitente, CNPJ, UF, data, total, itens) quando possível — best-effort. Idempotência: não duplicar chave já registrada. Consultas: listar notas importadas e ver total gasto por mês."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Importar nota fiscal nova via URL ou chave (Priority: P1)

Usuário fornece a URL do QR Code do cupom fiscal ou cola a chave de acesso de
44 dígitos; o sistema extrai/valida a chave, busca os dados da nota quando
possível, e grava um novo registro na base do financiALL.

**Why this priority**: é o fluxo central da feature — sem ele nenhum gasto de
nota fiscal entra na base única do financiALL.

**Independent Test**: fornecer uma URL válida de QR Code de NFC-e (ou uma
chave válida) ainda não importada e verificar que a nota aparece na listagem
com os dados obtidos.

**Acceptance Scenarios**:

1. **Given** o usuário tem a URL do QR Code de um cupom NFC-e ainda não
   importado, **When** ele fornece essa URL ao sistema, **Then** o sistema
   extrai a chave de 44 dígitos, busca os dados da nota, e grava um novo
   registro com emitente, data, total e itens (quando disponíveis).
2. **Given** o usuário tem apenas a chave de acesso de 44 dígitos (com ou sem
   espaços) de um cupom ainda não importado, **When** ele cola essa chave,
   **Then** o sistema valida a chave e segue o mesmo fluxo de importação.
3. **Given** o usuário fornece uma URL ou chave da qual não é possível extrair
   44 dígitos válidos (ou o dígito verificador falha), **When** o sistema
   tenta processar a entrada, **Then** o sistema rejeita a entrada e exibe uma
   mensagem em português explicando o motivo, sem gravar nada.

---

### User Story 2 - Não duplicar nota já importada (Priority: P1)

O sistema reconhece quando uma chave de acesso já foi registrada e recusa
criar um segundo registro para a mesma nota, avisando o usuário.

**Why this priority**: idempotência é inegociável — evita que o mesmo gasto
seja contado duas vezes nos relatórios do financiALL.

**Independent Test**: importar uma nota, depois tentar importar a mesma chave
(via URL ou via chave colada) novamente e verificar que nenhum novo registro
é criado e que o usuário é avisado.

**Acceptance Scenarios**:

1. **Given** uma nota com chave X já está registrada na base, **When** o
   usuário tenta importar novamente essa mesma chave X (por URL ou colada),
   **Then** o sistema não cria novo registro e informa ao usuário que a nota
   já estava importada, mostrando os dados do registro existente.
2. **Given** uma nota com chave X já registrada, **When** o usuário tenta
   importar a chave X vinda de uma fonte diferente da primeira vez (ex.: URL
   na primeira importação, chave colada na segunda), **Then** o sistema ainda
   reconhece a duplicidade pela chave e não duplica.

---

### User Story 3 - Registrar nota mesmo quando o detalhamento falha (Priority: P2)

Quando a busca dos dados completos da nota falha (fonte indisponível, erro,
timeout), o sistema grava a nota com o que conseguir obter e a marca para
revisão, em vez de falhar a importação inteira.

**Why this priority**: a fonte de detalhamento (portal estadual) é frágil por
natureza; a nota deve entrar na base mesmo sem os itens, para não perder o
registro do gasto.

**Independent Test**: simular indisponibilidade da fonte de detalhamento ao
importar uma chave nova e verificar que a nota é gravada com o que houver e
marcada como pendente de revisão.

**Acceptance Scenarios**:

1. **Given** a fonte de dados da nota está indisponível ou retorna erro,
   **When** o usuário importa uma chave nova, **Then** o sistema grava a nota
   com os dados que conseguir obter (no mínimo a chave de acesso) e marca o
   status como "pendente de revisão".
2. **Given** a fonte de dados retorna apenas parte dos campos (ex.: sem
   itens, mas com emitente e total), **When** a nota é importada, **Then** o
   sistema grava os campos disponíveis e marca como pendente de revisão.

---

### User Story 4 - Listar notas importadas (Priority: P2)

Usuário consulta a lista de notas já registradas na base, com os dados
principais de cada uma.

**Why this priority**: usuário precisa ver o que já foi registrado para
conferir e acompanhar o que entrou no financiALL.

**Independent Test**: com pelo menos uma nota importada, solicitar a listagem
e verificar que os dados aparecem corretamente.

**Acceptance Scenarios**:

1. **Given** existem notas importadas, **When** o usuário solicita a
   listagem, **Then** o sistema exibe cada nota com data de emissão,
   emitente, valor total e status (completa / pendente de revisão).
2. **Given** nenhuma nota foi importada ainda, **When** o usuário solicita a
   listagem, **Then** o sistema exibe uma mensagem informando que não há
   notas registradas.

---

### User Story 5 - Ver total gasto por mês (Priority: P3)

Usuário consulta um resumo do valor total gasto, agrupado por mês, com base
nas notas já registradas. Este resumo é parcial: cobre apenas o gasto
documentado por notas fiscais importadas, não o gasto total do mês (compras
sem NFC-e não entram aqui). A visão definitiva de gasto mensal depende da
reconciliação com o extrato bancário, prevista para uma feature futura.

**Why this priority**: dá uma primeira visão consolidada de gasto — o
primeiro valor entregue pela convergência de dados do financiALL, mesmo que
ainda parcial nesta feature.

**Independent Test**: com notas importadas em meses diferentes, solicitar o
resumo mensal e verificar que os totais por mês estão corretos.

**Acceptance Scenarios**:

1. **Given** existem notas importadas em um ou mais meses (pela data de
   emissão), **When** o usuário solicita o resumo mensal, **Then** o sistema
   exibe o total gasto de cada mês que tem ao menos uma nota.
2. **Given** nenhuma nota foi importada ainda, **When** o usuário consulta o
   resumo mensal, **Then** o sistema informa que não há dados suficientes
   para exibir o resumo.

---

### Edge Cases

- URL fornecida não é reconhecida como QR Code de NFC-e ou não contém uma
  chave de 44 dígitos no parâmetro esperado.
- Chave colada contém espaços, pontos, hífens ou outros caracteres
  não numéricos misturados aos dígitos.
- Chave com 44 caracteres, mas dígito verificador inválido.
- Chave com comprimento diferente de 44 dígitos (curta ou longa demais).
- Fonte de detalhamento da nota está lenta, indisponível ou retorna erro
  (timeout, portal fora do ar, resposta inesperada).
- Mesma chave é enviada duas vezes seguidas na mesma sessão, e também em
  sessões diferentes (dias distintos).
- Nota não tem itens discriminados na fonte (ex.: cupom simplificado).
- Listagem ou resumo mensal são solicitados sem nenhuma nota importada.
- Nota tem data de emissão em mês diferente do mês em que foi importada
  (o resumo mensal deve considerar a data de emissão, não a de importação).
- Chave válida (44 dígitos, dígito verificador correto) corresponde a um
  modelo de documento diferente de NFC-e (ex.: `55`, NF-e comum) — a nota é
  gravada normalmente com os dados decodificáveis da chave, mas fica
  "pendente de revisão" porque a busca de detalhes não é tentada para esse
  modelo nesta feature (FR-007, FR-013).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST aceitar como entrada uma URL apontada pelo QR
  Code de uma NFC-e OU uma chave de acesso de 44 dígitos colada diretamente
  (com ou sem espaços e outros caracteres não numéricos).
- **FR-002**: O sistema MUST extrair a chave de acesso de 44 dígitos a partir
  do parâmetro de consulta da URL fornecida.
- **FR-003**: Quando a chave é colada diretamente, o sistema MUST normalizar
  a entrada (remover espaços e caracteres não numéricos) e validar
  comprimento (44 dígitos) e dígito verificador antes de prosseguir.
- **FR-004**: Se a URL ou a chave colada não resultar em uma chave válida de
  44 dígitos, o sistema MUST rejeitar a entrada e informar ao usuário, em
  português, o motivo (ex.: comprimento incorreto, dígito verificador
  inválido), sem gravar nada.
- **FR-005**: Antes de gravar qualquer nota, o sistema MUST verificar se a
  chave de acesso já existe na base.
- **FR-006**: Se a chave já existir, o sistema MUST NOT criar um novo
  registro e MUST informar ao usuário que a nota já estava registrada,
  exibindo os dados do registro existente.
- **FR-007**: Se a chave for nova e corresponder a modelo `65` (NFC-e), o
  sistema MUST tentar obter os dados da nota: nome do emitente, CNPJ do
  emitente, UF, data de emissão, valor total e itens (código do item
  conforme informado pelo emitente, descrição, quantidade, valor unitário e
  valor total de cada item). Para chave nova de outro modelo (ex.: `55`,
  NF-e), o sistema grava a nota apenas com os dados decodificáveis da
  própria chave (FR-013), sem tentar a busca — não há rejeição por modelo.
- **FR-008**: Se a busca dos dados completos falhar parcial ou totalmente, o
  sistema MUST gravar a nota com os dados disponíveis (no mínimo a chave de
  acesso) e marcá-la com status "pendente de revisão", sem interromper o
  fluxo de importação.
- **FR-009**: O sistema MUST permitir listar as notas importadas, exibindo ao
  menos data de emissão, emitente, valor total e status (completa /
  pendente de revisão).
- **FR-010**: O sistema MUST permitir visualizar um resumo do valor total
  gasto agrupado por mês, com base na data de emissão das notas registradas.
  Este resumo é parcial (apenas notas fiscais) e MUST ser identificado como
  tal ao usuário, não como o gasto total do mês.
- **FR-011**: O sistema MUST NOT registrar CPF, chave de acesso, CNPJ ou
  valores monetários em log de texto claro.
- **FR-012**: Mensagens exibidas ao usuário MUST estar em português.
- **FR-013**: O sistema MUST aceitar e gravar qualquer chave de acesso
  válida (44 dígitos, dígito verificador correto), independentemente do
  modelo do documento (ex.: `65` NFC-e, `55` NF-e) — alinhado ao princípio
  ALL de convergência de toda fonte de gasto para a mesma base. Não há
  rejeição de entrada baseada no campo modelo.

### Key Entities

- **Nota Fiscal (NFC-e)**: representa um cupom fiscal importado. Atributos:
  chave de acesso (44 dígitos, identificador único de deduplicação), nome do
  emitente, CNPJ do emitente, UF, data de emissão, valor total, status
  (completa / pendente de revisão), data de importação.
- **Item da Nota**: representa uma linha de produto/serviço dentro de uma
  Nota Fiscal. Atributos: código do item (conforme informado pelo emitente —
  na prática, frequentemente um código interno/SKU da loja, não um GTIN/EAN
  global), descrição, quantidade, valor unitário, valor total do item.
  Relaciona-se a exatamente uma Nota Fiscal.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das tentativas de importar uma chave de acesso já
  registrada resultam em zero notas duplicadas na base.
- **SC-002**: Usuário consegue concluir a importação de uma nota (fornecer
  URL ou chave até ver a confirmação) em uma única interação, sem precisar
  de conhecimento técnico sobre o formato da chave ou da URL.
- **SC-003**: Quando a fonte de detalhamento responde com sucesso, 100% das
  notas importadas são gravadas com emitente, data, total e itens
  completos.
- **SC-004**: Quando a fonte de detalhamento falha ou está indisponível,
  100% das notas ainda são registradas na base (nenhuma falha de fonte
  externa impede o registro da chave e dos dados básicos).
- **SC-005**: Usuário consegue visualizar o total gasto (parcial, apenas
  notas fiscais importadas) de qualquer mês com notas registradas em uma
  única consulta, sem etapas adicionais.

## Assumptions

- O uso é de uma única pessoa (pessoa física), sem necessidade de múltiplos
  usuários ou contas nesta feature.
- O formato de URL de QR Code de NFC-e contém a chave de 44 dígitos em um
  parâmetro de consulta, seguindo o padrão comum adotado pelos portais
  estaduais (SEFAZ) participantes do modelo nacional de NFC-e.
- A validação do dígito verificador segue o algoritmo padrão (módulo 11)
  usado para chaves de acesso de NF-e/NFC-e no modelo nacional.
- "Pendente de revisão" nesta feature é apenas um status exibido na
  listagem; ações de correção ou complementação manual dos dados ficam fora
  de escopo (feature futura).
- Notas importadas não podem ser editadas ou excluídas nesta feature —
  apenas importadas e consultadas.
- O resumo mensal soma o valor total das notas pela data de emissão, não
  pela data em que foram importadas.
- O código do item vindo da nota (às vezes chamado de GTIN/EAN) não é
  confiável como identificador global de produto: na prática, muitos
  emitentes usam códigos internos (SKU da própria loja) nesse campo. O
  sistema armazena o código exatamente como veio na nota, sem validá-lo como
  GTIN nem assumir que ele identifica o mesmo produto em estabelecimentos
  diferentes; casar produtos entre lojas pelo código fica fora de escopo
  desta feature (é insumo para uma feature futura de categorização).
- O resumo mensal desta feature é parcial: reflete somente o gasto
  documentado por notas fiscais importadas, não o gasto total do mês (que
  inclui compras sem NFC-e). A visão definitiva de gasto mensal virá da
  reconciliação com o extrato bancário (feature futura), que passa a ser a
  fonte de verdade para evitar contagem duplicada entre nota fiscal e
  lançamento de extrato.
- Fora de escopo nesta feature: leitura de foto/imagem do QR Code, OCR de
  cupom em papel, resolução de captcha de portais estaduais, categorização
  de itens e reconciliação com extrato bancário (features futuras do
  financiALL).
- CF-e SAT (modelo 59, arquivo TXT do COMSAT) fica fora de escopo desta
  feature: o formato de entrada, validação e obtenção de dados é diferente
  do fluxo por URL/chave de 44 dígitos da NFC-e. Vira uma feature separada.
- Chave de acesso com modelo diferente de NFC-e (ex.: `55`, NF-e comum) é
  aceita e gravada por esta feature — não é rejeitada por modelo, pelo
  princípio ALL de convergência de toda fonte de gasto para a base única.
  A busca best-effort de detalhes (emitente, data exata, total, itens) não
  é tentada para esses modelos nesta feature, porque o fluxo de consulta
  pesquisado (research.md #3 e #6) cobre apenas portais de NFC-e por UF;
  a nota permanece "pendente de revisão" até uma feature futura pesquisar a
  consulta ao portal correspondente ao modelo.
- Associação da nota a uma pessoa/conta específica (ex.: Marcelo vs
  Cristine) fica fora de escopo: nesta feature a nota é registrada na base
  única sem distinção de dono. Suporte a múltiplas contas/pessoas é
  requisito de uma feature futura.
