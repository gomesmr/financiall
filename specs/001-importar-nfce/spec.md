# Feature Specification: Importar Notas Fiscais sem Duplicar

**Feature Branch**: `001-importar-nfce`

**Created**: 2026-07-13

**Status**: Draft

**Input**: User description: "Redesenho completo da feature 001 do financiALL:
um servidor dedicado, sempre ligado, na rede local do usuário, recebe notas
fiscais por dois canais — (1) URL do QR Code ou chave de acesso de 44 dígitos
colada, e (2) foto ou PDF escaneado de um cupom fiscal, processado por OCR de
forma assíncrona e sequencial (um envio de cada vez). O computador do usuário
não fica sempre ligado e não guarda estado — é só um cliente que acessa o
servidor pela rede quando está ligado. Idempotência por chave de acesso (ou,
quando ela não pode ser extraída da imagem, por hash de conteúdo do
documento) continua não-negociável. Falha em obter dados completos (fonte
externa indisponível ou OCR malsucedido) nunca impede o registro da nota.
Categorização fica fora de escopo. Consultas disponíveis: listar notas
importadas, status de processamento de um envio por foto/PDF, gasto parcial
do mês corrente e histórico de gasto por mês em meses anteriores."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Importar nota nova via URL ou chave de acesso (Priority: P1)

Usuário fornece a URL do QR Code de um cupom fiscal ou cola a chave de acesso
de 44 dígitos; o sistema extrai/valida a chave, busca os dados da nota quando
possível e grava um novo registro.

**Why this priority**: é o canal de entrada mais simples e confiável — não
depende de OCR nem de qualidade de imagem, e sozinho já entrega o valor
central da feature (registrar o gasto documentado por nota fiscal).

**Independent Test**: fornecer uma URL válida de QR Code (ou uma chave
válida) ainda não importada e verificar que a nota aparece na listagem com os
dados obtidos.

**Acceptance Scenarios**:

1. **Given** o usuário tem a URL do QR Code de um cupom fiscal ainda não
   importado, **When** ele envia essa URL ao sistema, **Then** o sistema
   extrai a chave de 44 dígitos, busca os dados da nota e grava um novo
   registro com emitente, data, total e itens (quando disponíveis).
2. **Given** o usuário tem apenas a chave de acesso de 44 dígitos (com ou sem
   espaços) de um cupom ainda não importado, **When** ele envia essa chave,
   **Then** o sistema valida a chave e segue o mesmo fluxo de importação.
3. **Given** o usuário envia uma URL ou chave da qual não é possível extrair
   44 dígitos válidos (ou o dígito verificador falha), **When** o sistema
   tenta processar a entrada, **Then** o sistema rejeita a entrada e informa,
   em português, o motivo, sem gravar nada.

---

### User Story 2 - Importar nota via foto ou PDF escaneado (Priority: P1)

Usuário envia uma foto ou um arquivo PDF de um cupom fiscal em papel; o
sistema reconhece o texto da imagem (OCR), extrai os dados possíveis e grava
um novo registro, sem exigir que o usuário aguarde o processamento terminar
para receber a confirmação de recebimento.

**Why this priority**: é o segundo canal de entrada central da feature —
sem ele, notas em papel (sem QR Code acessível ou já descartado) nunca
entrariam na base.

**Independent Test**: enviar a foto ou PDF de um cupom fiscal legível ainda
não importado e, após o processamento, verificar que a nota aparece na
listagem com os dados extraídos.

**Acceptance Scenarios**:

1. **Given** o usuário tem uma foto legível de um cupom fiscal ainda não
   importado, **When** ele envia essa foto ao sistema, **Then** o sistema
   confirma o recebimento imediatamente e, em seguida, processa a imagem
   (reconhecimento de texto) para extrair chave de acesso (quando presente),
   emitente, data, total e itens.
2. **Given** o usuário tem um PDF escaneado de um cupom fiscal ainda não
   importado, **When** ele envia esse arquivo, **Then** o sistema segue o
   mesmo fluxo de confirmação imediata e processamento em segundo plano.
3. **Given** o sistema já está processando um envio anterior de foto/PDF,
   **When** um novo envio chega, **Then** o sistema aceita o novo envio e o
   processa em ordem, sem descartar nem perder nenhum dos dois.
4. **Given** uma imagem enviada está ilegível ou não corresponde a um cupom
   fiscal, **When** o processamento é concluído, **Then** o sistema grava o
   envio com o mínimo de dados possível (ou nenhum dado extraído) e marca a
   nota como "pendente de revisão", sem descartar o envio nem travar o
   sistema.

---

### User Story 3 - Não duplicar nota já importada (Priority: P1)

O sistema reconhece quando uma nota já foi registrada — pela chave de acesso
ou, quando ela não puder ser identificada (ex.: OCR não conseguiu ler a
chave), pelo conteúdo do documento — e recusa criar um segundo registro,
avisando o usuário.

**Why this priority**: idempotência é inegociável, independentemente do
canal de entrada — evita que o mesmo gasto seja contado duas vezes.

**Independent Test**: importar uma nota por um canal, depois tentar importar
a mesma nota novamente (pelo mesmo canal ou por um canal diferente) e
verificar que nenhum novo registro é criado.

**Acceptance Scenarios**:

1. **Given** uma nota com chave de acesso X já está registrada, **When** o
   usuário tenta importar novamente essa mesma chave (por URL, por chave
   colada, ou por uma foto/PDF da qual o sistema consiga extrair a mesma
   chave via OCR), **Then** o sistema não cria novo registro e informa que a
   nota já estava importada, mostrando os dados do registro existente.
2. **Given** uma nota foi registrada a partir de uma foto/PDF cuja chave de
   acesso não pôde ser extraída, **When** o usuário envia novamente a mesma
   imagem (ou uma cópia idêntica do mesmo documento), **Then** o sistema
   reconhece que o conteúdo já foi registrado e não cria um novo registro.
3. **Given** uma nota com chave de acesso X já registrada, **When** o usuário
   tenta importar a chave X vinda de um canal diferente do da primeira
   importação, **Then** o sistema ainda reconhece a duplicidade pela chave e
   não duplica.

---

### User Story 4 - Registrar nota mesmo quando os dados completos não são obtidos (Priority: P1)

Quando a busca de dados completos falha — fonte externa indisponível para o
canal de URL/chave, ou reconhecimento de texto malsucedido/parcial para o
canal de foto/PDF — o sistema grava a nota com o que conseguir obter e a
marca para revisão, em vez de descartar a tentativa.

**Why this priority**: tanto a fonte de detalhamento externa quanto o
reconhecimento de texto em imagens são processos frágeis por natureza; a
nota deve entrar na base mesmo com dados incompletos, para não perder o
registro do gasto.

**Independent Test**: simular indisponibilidade da fonte externa (canal
URL/chave) e uma imagem de baixa qualidade (canal foto/PDF) e verificar, nos
dois casos, que a nota é gravada com o que houver e marcada como pendente de
revisão.

**Acceptance Scenarios**:

1. **Given** a fonte externa de dados da nota está indisponível ou retorna
   erro, **When** o usuário importa uma chave nova por URL/chave, **Then** o
   sistema grava a nota com os dados que conseguir obter (no mínimo a chave
   de acesso) e marca o status como "pendente de revisão".
2. **Given** o reconhecimento de texto de uma foto/PDF retorna apenas parte
   dos campos esperados (ex.: sem itens, mas com total), **When** o
   processamento é concluído, **Then** o sistema grava os campos disponíveis
   e marca a nota como "pendente de revisão".
3. **Given** o reconhecimento de texto de uma foto/PDF não retorna nenhum
   campo utilizável, **When** o processamento é concluído, **Then** o
   sistema ainda registra o envio (marcado como "pendente de revisão", sem
   dados extraídos) em vez de descartá-lo silenciosamente.

---

### User Story 5 - Consultar status de processamento de um envio por foto/PDF (Priority: P2)

Usuário consulta se uma foto/PDF que enviou já foi processada, ainda está na
fila, ou falhou ao processar.

**Why this priority**: como o processamento por foto/PDF não é imediato, o
usuário precisa de uma forma de acompanhar o que enviou sem esperar
bloqueado pela resposta do envio.

**Independent Test**: enviar uma foto/PDF e, antes e depois do processamento
terminar, consultar o status e verificar que ele reflete corretamente o
estado (pendente, processada, falhou).

**Acceptance Scenarios**:

1. **Given** o usuário acabou de enviar uma foto/PDF, **When** ele consulta o
   status logo em seguida, **Then** o sistema informa que o envio está
   pendente de processamento.
2. **Given** o processamento de um envio já terminou com sucesso, **When** o
   usuário consulta o status, **Then** o sistema informa que foi processado e
   aponta para a nota resultante.
3. **Given** o processamento de um envio terminou sem conseguir extrair dados
   utilizáveis, **When** o usuário consulta o status, **Then** o sistema
   informa que o processamento foi concluído com dados incompletos (nota
   pendente de revisão), sem apresentar isso como uma falha do sistema em si.

---

### User Story 6 - Listar notas importadas (Priority: P2)

Usuário consulta a lista de notas já registradas, com os dados principais de
cada uma, com filtro opcional por mês.

**Why this priority**: usuário precisa ver o que já foi registrado para
conferir e acompanhar o que entrou no financiALL.

**Independent Test**: com pelo menos uma nota importada, solicitar a
listagem e verificar que os dados aparecem corretamente; solicitar com
filtro de mês e verificar que só as notas daquele mês aparecem.

**Acceptance Scenarios**:

1. **Given** existem notas importadas, **When** o usuário solicita a
   listagem, **Then** o sistema exibe cada nota com data de emissão,
   emitente, valor total, status e canal de origem (URL/chave ou foto/PDF).
2. **Given** existem notas de meses diferentes, **When** o usuário solicita a
   listagem filtrando por um mês específico, **Then** o sistema exibe
   apenas as notas daquele mês.
3. **Given** nenhuma nota foi importada ainda, **When** o usuário solicita a
   listagem, **Then** o sistema informa que não há notas registradas.

---

### User Story 7 - Ver gasto parcial do mês corrente (Priority: P2)

Usuário consulta, a qualquer momento, o total já gasto no mês corrente com
base nas notas fiscais já registradas.

**Why this priority**: dá ao usuário uma visão de acompanhamento do gasto do
mês em andamento, mesmo sabendo que é parcial (só o que já foi importado).

**Independent Test**: com notas importadas no mês corrente, solicitar o
gasto parcial do mês e verificar que o total está correto e sinalizado como
parcial.

**Acceptance Scenarios**:

1. **Given** existem notas importadas no mês corrente, **When** o usuário
   consulta o gasto parcial do mês, **Then** o sistema exibe o total somado
   dessas notas, identificado explicitamente como parcial.
2. **Given** nenhuma nota foi importada no mês corrente, **When** o usuário
   consulta o gasto parcial do mês, **Then** o sistema informa que não há
   dados suficientes para o mês corrente.

---

### User Story 8 - Ver histórico de gasto por mês (Priority: P3)

Usuário consulta o total gasto de meses anteriores, um valor por mês, com
base nas notas já registradas.

**Why this priority**: complementa a visão do mês corrente com uma
perspectiva histórica; é a prioridade mais baixa porque não é necessária
para o acompanhamento do dia a dia.

**Independent Test**: com notas importadas em meses diferentes, solicitar o
histórico e verificar que os totais de cada mês anterior estão corretos.

**Acceptance Scenarios**:

1. **Given** existem notas importadas em um ou mais meses anteriores ao mês
   corrente, **When** o usuário solicita o histórico, **Then** o sistema
   exibe o total gasto de cada um desses meses.
2. **Given** nenhuma nota foi importada em meses anteriores, **When** o
   usuário solicita o histórico, **Then** o sistema informa que não há dados
   suficientes para exibir o histórico.

---

### Edge Cases

- URL fornecida não é reconhecida como QR Code de nota fiscal ou não contém
  uma chave de 44 dígitos no parâmetro esperado.
- Chave colada contém espaços, pontos, hífens ou outros caracteres não
  numéricos misturados aos dígitos.
- Chave com 44 caracteres, mas dígito verificador inválido.
- Chave com comprimento diferente de 44 dígitos (curta ou longa demais).
- Fonte de detalhamento externa (canal URL/chave) está lenta, indisponível
  ou retorna erro.
- Foto enviada está borrada, mal enquadrada, ou com iluminação ruim ao
  ponto do reconhecimento de texto não identificar nenhum campo.
- PDF enviado está corrompido ou não é um documento de texto/imagem válido.
- Arquivo enviado não é nem imagem nem PDF (tipo de arquivo não suportado).
- O reconhecimento de texto extrai uma sequência de 44 dígitos da imagem,
  mas o dígito verificador dela é inválido — o sistema deve tratar como se a
  chave não tivesse sido identificada (cair no fluxo de identificação por
  conteúdo do documento), não travar nem rejeitar o envio inteiro.
- A mesma nota é enviada duas vezes seguidas (mesma sessão) e também em
  momentos diferentes (dias distintos), pelo mesmo canal ou por canais
  diferentes (ex.: primeiro por foto, depois a URL do QR Code da mesma
  nota).
- Vários envios de foto/PDF chegam próximos no tempo, antes que o anterior
  termine de ser processado.
- Listagem, status de processamento, gasto do mês ou histórico são
  solicitados sem nenhuma nota importada.
- Nota tem data de emissão em mês diferente do mês em que foi importada (as
  consultas de gasto mensal devem considerar a data de emissão, não a de
  importação).
- Usuário consulta o sistema a partir do computador enquanto ele está
  desligado ou fora da rede local — a consulta simplesmente não é possível
  até o computador voltar a se conectar; isso não afeta a disponibilidade do
  sistema em si nem os dados já registrados.
- Chave válida (44 dígitos, dígito verificador correto), obtida por
  qualquer canal, corresponde a um modelo de documento diferente de NFC-e
  (ex.: `55`, NF-e comum) — a nota é gravada normalmente com os dados
  decodificáveis da chave, mas fica "pendente de revisão" porque a busca de
  detalhes não é tentada para esse modelo nesta feature.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST aceitar como entrada, para o canal digital, uma
  URL apontada pelo QR Code de uma nota fiscal OU uma chave de acesso de 44
  dígitos enviada diretamente (com ou sem espaços e outros caracteres não
  numéricos).
- **FR-002**: O sistema MUST extrair a chave de acesso de 44 dígitos a
  partir do parâmetro de consulta da URL fornecida.
- **FR-003**: Quando a chave é enviada diretamente, o sistema MUST
  normalizar a entrada (remover espaços e caracteres não numéricos) e
  validar comprimento (44 dígitos) e dígito verificador antes de prosseguir.
- **FR-004**: Se a URL ou a chave enviada não resultar em uma chave válida
  de 44 dígitos, o sistema MUST rejeitar a entrada e informar ao usuário, em
  português, o motivo, sem gravar nada.
- **FR-005**: O sistema MUST aceitar como entrada, para o canal de
  digitalização, uma foto ou um arquivo PDF de um cupom fiscal.
- **FR-006**: Ao receber uma foto ou PDF, o sistema MUST confirmar o
  recebimento ao usuário imediatamente, sem esperar o processamento
  (reconhecimento de texto) terminar.
- **FR-007**: O sistema MUST processar os envios de foto/PDF em ordem, um de
  cada vez, sem perder ou descartar envios recebidos enquanto outro ainda
  está sendo processado.
- **FR-008**: O sistema MUST permitir que o usuário consulte o status de
  processamento de um envio de foto/PDF (pendente, processado, ou concluído
  com dados incompletos).
- **FR-009**: Ao processar uma foto/PDF, o sistema MUST tentar extrair, por
  reconhecimento de texto, os mesmos dados obtidos no canal digital: chave
  de acesso (quando presente e legível), nome do emitente, CNPJ, data de
  emissão, valor total e itens (código, descrição, quantidade, valor
  unitário e valor total de cada item).
- **FR-010**: Antes de gravar qualquer nota nova, o sistema MUST verificar
  se ela já existe na base: pela chave de acesso quando disponível (em
  qualquer canal); quando a chave não puder ser identificada (ex.: OCR não
  conseguiu extraí-la), pelo conteúdo do documento enviado.
- **FR-011**: Se a nota já existir (por chave ou por conteúdo), o sistema
  MUST NOT criar um novo registro e MUST informar ao usuário que a nota já
  estava registrada, exibindo os dados do registro existente.
- **FR-012**: Se a chave for nova e corresponder a modelo `65` (NFC-e), o
  sistema MUST tentar obter os dados completos da nota na fonte externa
  correspondente. Para chave nova de outro modelo (ex.: `55`, NF-e), o
  sistema grava a nota apenas com os dados decodificáveis da própria chave,
  sem tentar essa busca.
- **FR-013**: Se a busca de dados completos falhar, parcial ou totalmente —
  em qualquer canal (fonte externa indisponível, ou reconhecimento de texto
  malsucedido/parcial) — o sistema MUST gravar a nota com os dados
  disponíveis (no mínimo a chave de acesso, ou o registro do envio quando
  nem a chave foi identificada) e marcá-la com status "pendente de revisão",
  sem interromper o fluxo de importação.
- **FR-014**: O sistema MUST permitir listar as notas importadas, exibindo
  ao menos data de emissão, emitente, valor total, status e canal de
  origem, com filtro opcional por mês.
- **FR-015**: O sistema MUST permitir consultar o gasto parcial do mês
  corrente, somando o valor total das notas registradas com data de emissão
  no mês corrente, identificado explicitamente como parcial.
- **FR-016**: O sistema MUST permitir consultar o histórico de gasto por
  mês para meses anteriores ao corrente, com base na data de emissão das
  notas registradas, identificado explicitamente como parcial.
- **FR-017**: As consultas (listar, status de processamento, gasto do mês,
  histórico) MUST estar disponíveis sempre que o sistema estiver em
  funcionamento, independentemente do estado de qualquer outro dispositivo
  usado para acessá-lo.
- **FR-018**: O sistema MUST NOT registrar CPF, chave de acesso, CNPJ ou
  valores monetários em log de texto claro.
- **FR-019**: Mensagens exibidas ao usuário MUST estar em português.
- **FR-020**: O sistema MUST aceitar e gravar qualquer chave de acesso
  válida (44 dígitos, dígito verificador correto), independentemente do
  modelo do documento — não há rejeição de entrada baseada no campo modelo.
- **FR-021**: Categorização de notas ou itens está fora de escopo desta
  feature — notas MUST ser registradas sem categoria.

### Key Entities

- **Nota Fiscal**: representa um cupom fiscal importado, por qualquer canal.
  Atributos: chave de acesso (44 dígitos, quando identificada — identificador
  primário de deduplicação), hash de conteúdo do documento (usado como
  identificador alternativo de deduplicação quando a chave não pôde ser
  identificada), canal de origem (URL/chave ou foto/PDF), nome do emitente,
  CNPJ do emitente, UF, data de emissão, valor total, status (completa /
  pendente de revisão / pendente de processamento), data de importação.
- **Item da Nota**: representa uma linha de produto/serviço dentro de uma
  Nota Fiscal. Atributos: código do item (conforme informado pelo emitente),
  descrição, quantidade, valor unitário, valor total do item. Relaciona-se a
  exatamente uma Nota Fiscal.
- **Envio de Foto/PDF**: representa um arquivo enviado pelo canal de
  digitalização antes (ou independentemente) de virar uma Nota Fiscal
  processada. Atributos: status de processamento (pendente, processado,
  concluído com dados incompletos), data do envio, referência à Nota Fiscal
  resultante (quando o processamento identifica ou cria uma).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das tentativas de importar uma nota já registrada — por
  qualquer canal ou combinação de canais — resultam em zero notas
  duplicadas na base.
- **SC-002**: Usuário recebe confirmação de recebimento de uma foto/PDF
  enviado em poucos segundos, sem precisar aguardar o processamento
  terminar.
- **SC-003**: Quando a busca de dados completos tem sucesso (em qualquer
  canal), 100% das notas importadas são gravadas com emitente, data, total e
  itens completos.
- **SC-004**: Quando a busca de dados completos falha ou está indisponível
  (em qualquer canal), 100% das notas ainda são registradas na base.
- **SC-005**: Usuário consegue consultar o gasto parcial do mês corrente e
  o histórico de meses anteriores em uma única consulta, a qualquer momento
  em que o sistema esteja em funcionamento.
- **SC-006**: Usuário consegue verificar o status de processamento de
  qualquer envio de foto/PDF (pendente, processado, ou concluído com dados
  incompletos) em uma única consulta.
- **SC-007**: Envios de foto/PDF feitos em sequência rápida são todos
  processados eventualmente, sem nenhum ser perdido ou sobrescrito por
  outro.

## Assumptions

- O uso é de uma única pessoa (pessoa física), sem necessidade de múltiplos
  usuários ou contas nesta feature.
- Existe um servidor dedicado, sempre ligado, na rede local do usuário, que
  hospeda o sistema e a base de dados; os dispositivos usados para enviar
  notas ou fazer consultas (ex.: computador) são clientes que acessam esse
  servidor pela rede quando estão ligados, sem guardar estado próprio.
- Indisponibilidade do próprio servidor (queda de energia, falha de rede do
  servidor) é fora de escopo desta feature — apenas a indisponibilidade de
  fontes externas (busca de dados na fonte do canal digital, qualidade da
  imagem no canal de digitalização) é tratada como degradação esperada.
- Envios de foto/PDF são processados em ordem, um de cada vez; em momentos
  de muitos envios simultâneos, pode haver uma fila de espera perceptível
  ao usuário antes de um envio específico ser processado.
- O formato de URL de QR Code de nota fiscal contém a chave de 44 dígitos
  em um parâmetro de consulta, seguindo o padrão comum adotado pelos
  portais estaduais participantes do modelo nacional de NFC-e.
- A validação do dígito verificador segue o algoritmo padrão (módulo 11)
  usado para chaves de acesso de NF-e/NFC-e no modelo nacional.
- O hash de conteúdo do documento (usado como identificador alternativo
  quando a chave não é identificável) é calculado sobre o arquivo enviado
  (foto ou PDF); duas fotos diferentes do mesmo cupom físico (ângulos,
  iluminação ou recortes diferentes) podem gerar hashes diferentes e não
  serem reconhecidas automaticamente como a mesma nota — esse caso é aceito
  como limitação conhecida desta feature.
- "Pendente de revisão" e "pendente de processamento" são apenas status
  exibidos; ações de correção ou complementação manual dos dados ficam fora
  de escopo (feature futura).
- Notas importadas não podem ser editadas ou excluídas nesta feature —
  apenas importadas e consultadas.
- As consultas de gasto (parcial do mês corrente e histórico) somam o valor
  total das notas pela data de emissão, não pela data em que foram
  importadas.
- O código do item vindo da nota não é confiável como identificador global
  de produto (frequentemente é um código interno do emitente); o sistema
  armazena o código exatamente como veio, sem validá-lo como GTIN/EAN nem
  assumir que identifica o mesmo produto entre estabelecimentos diferentes.
- As consultas de gasto desta feature são parciais: refletem somente o
  gasto documentado por notas fiscais importadas (por qualquer canal), não
  o gasto total do mês, que inclui compras sem nota registrada. A visão
  definitiva de gasto mensal virá da reconciliação com o extrato bancário
  (feature futura).
- Fora de escopo nesta feature: resolução de captcha de portais estaduais,
  categorização de itens, reconciliação com extrato bancário, edição ou
  correção manual de notas pendentes de revisão, e suporte a múltiplas
  contas/pessoas (features futuras do financiALL).
- CF-e SAT (modelo 59, arquivo TXT do COMSAT) fica fora de escopo desta
  feature: o formato de entrada e obtenção de dados é diferente dos dois
  canais desta feature (URL/chave e foto/PDF de NFC-e). Vira uma feature
  separada.
- Chave de acesso com modelo diferente de NFC-e (ex.: `55`, NF-e comum) é
  aceita e gravada por esta feature — não é rejeitada por modelo. A busca
  best-effort de detalhes complementares não é tentada para esses modelos
  nesta feature; a nota permanece "pendente de revisão" até uma feature
  futura pesquisar a consulta ao portal correspondente.
- Associação da nota a uma pessoa/conta específica fica fora de escopo:
  nesta feature a nota é registrada na base única sem distinção de dono.
