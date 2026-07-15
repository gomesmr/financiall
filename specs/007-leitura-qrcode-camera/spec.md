# Feature Specification: Leitura de QR Code pela Câmera

**Feature Branch**: `007-leitura-qrcode-camera`

**Created**: 2026-07-15

**Status**: Draft

**Input**: User description: "Leitura de QR Code pela câmera do celular, direto na página, como alternativa ao upload de foto/PDF: hoje o financiALL tem dois jeitos de importar uma nota — colar a URL do QR Code ou a chave de acesso num campo de texto, ou enviar uma foto/PDF do cupom para OCR (processamento assíncrono, sujeito a falha de leitura). O usuário já usa um terceiro caminho manual que funciona perfeitamente: aponta o app nativo de câmera do celular pro QR Code da nota, o app abre a URL da SEFAZ automaticamente no navegador, ele copia essa URL da barra de endereço e cola no campo de texto do financiALL. A ideia desta feature é eliminar esse passo manual de sair do app e copiar/colar: adicionar uma terceira opção de importação na própria página de Importar, que ativa a câmera do celular ali mesmo, decodifica o QR Code ao vivo (sem precisar fotografar/enviar nada), extrai a mesma URL que o usuário já cola manualmente hoje, e envia pro mesmo fluxo de importação por URL/chave já existente — sem precisar do pipeline de OCR nem de um app externo."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Importar apontando a câmera pro QR Code (Priority: P1)

Como usuário, quero abrir a página de Importar do financiALL, ativar a leitura de QR Code pela câmera do celular ali mesmo, e ao apontar para o QR Code da nota fiscal ter a nota importada automaticamente — sem precisar sair do app, sem precisar tirar foto e enviar, e sem precisar copiar/colar nenhuma URL manualmente.

**Why this priority**: é o pedido central da feature — elimina o passo manual (usar o app de câmera nativo do celular, copiar a URL, voltar pro financiALL e colar) que o usuário já faz hoje com sucesso, mas que exige sair do app.

**Independent Test**: na página de Importar, ativar a opção de leitura por câmera, apontar para um QR Code de nota fiscal válido, e confirmar que a nota é importada com o mesmo resultado de quando a mesma URL é colada manualmente no campo de texto já existente.

**Acceptance Scenarios**:

1. **Given** o usuário está na página de Importar com a câmera disponível, **When** ele ativa a leitura por câmera e aponta para um QR Code de nota fiscal válido, **Then** o sistema decodifica o código, envia a URL extraída pelo mesmo fluxo de importação por URL/chave já existente, e o usuário vê o mesmo resultado (nota importada ou mensagem de erro) que já veria colando a URL manualmente.
2. **Given** a leitura por câmera decodificou um QR Code com sucesso, **When** a importação é concluída, **Then** o usuário não precisa realizar nenhuma ação extra de copiar ou colar — a única ação manual é apontar a câmera para o código.

---

### User Story 2 - Degradação graciosa quando a câmera não está disponível (Priority: P1)

Como usuário, quando a leitura por câmera não puder funcionar no meu navegador ou dispositivo no momento (permissão negada, navegador sem suporte, ou o financiALL acessado sem os requisitos que o navegador exige para usar a câmera), quero que a opção simplesmente não apareça disponível, e que os dois jeitos de importar que já uso hoje (colar URL/chave, ou enviar foto/PDF) continuem funcionando exatamente como sempre funcionaram.

**Why this priority**: mesmo peso da história 1 — sem essa garantia, a feature corre o risco de quebrar ou confundir o fluxo de importação já existente e testado, que é o valor central já entregue do financiALL.

**Independent Test**: acessar a página de Importar num navegador ou situação em que a câmera não está disponível (ex.: permissão negada) e confirmar que nenhum botão quebrado aparece, e que importar por URL/chave e por foto/PDF continuam funcionando sem nenhuma mudança perceptível.

**Acceptance Scenarios**:

1. **Given** o navegador ou dispositivo do usuário não consegue oferecer acesso à câmera pela página (por qualquer motivo), **When** o usuário abre a página de Importar, **Then** a opção de leitura por câmera não é oferecida de forma que pareça quebrada — fica claramente indisponível ou simplesmente ausente — e as opções de URL/chave e foto/PDF continuam visíveis e funcionais.
2. **Given** o usuário nega a permissão de câmera quando o navegador solicita, **When** isso acontece, **Then** o sistema informa que a leitura por câmera não está disponível e direciona o usuário de volta às outras opções, sem travar a página.

---

### User Story 3 - Feedback claro durante a leitura (Priority: P2)

Como usuário, enquanto estou com a câmera ativa procurando o QR Code, quero ver algum indicativo de que a leitura está em andamento (e não travada), e se o código não for reconhecido ou não for uma nota fiscal válida, quero um aviso claro — do mesmo jeito que já acontece hoje quando colo uma entrada inválida no campo de texto.

**Why this priority**: melhora a confiança no uso da funcionalidade central (história 1), mas o valor principal já existe mesmo com um retorno visual simples.

**Independent Test**: ativar a leitura por câmera, apontar para algo que não é um QR Code de nota fiscal (ex.: um QR Code de outro tipo, ou nenhum código), e confirmar que o sistema dá um retorno compreensível em vez de ficar sem resposta aparente.

**Acceptance Scenarios**:

1. **Given** a câmera está ativa e buscando um código, **When** nenhum código é encontrado ainda, **Then** o usuário vê uma indicação de que a busca está ativa (não uma tela parada sem explicação).
2. **Given** um código é decodificado mas não é uma URL/chave de nota fiscal válida, **When** isso é detectado, **Then** o usuário recebe a mesma mensagem de erro clara que já existe hoje para uma entrada de texto inválida.
3. **Given** o usuário decide não continuar com a leitura por câmera, **When** ele cancela, **Then** ele volta a ver as opções de importação normalmente, sem precisar recarregar a página.

---

### Edge Cases

- QR Code de outro tipo de documento (não nota fiscal) é escaneado por engano — tratado como entrada inválida, reaproveitando a validação que já existe hoje para o campo de texto.
- Usuário nega a permissão de câmera do navegador.
- Câmera já está em uso por outra aba ou aplicativo no momento.
- Iluminação ruim ou QR Code ilegível/danificado — a busca continua ativa sem travar, até o usuário conseguir um ângulo/luz melhor ou cancelar.
- Celular com mais de uma câmera (frontal e traseira) — a leitura deve preferir a câmera traseira por padrão, por ser a mais prática para apontar para um objeto físico.
- financiALL acessado num contexto em que o navegador não permite ligar a câmera pela página (ver História 2) — degrada sem quebrar as opções já existentes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A página de Importar MUST oferecer uma terceira opção de entrada — leitura de QR Code pela câmera — ao lado das duas já existentes (URL/chave em texto, foto/PDF).
- **FR-002**: Ao ativar a leitura por câmera, o sistema MUST usar a câmera do dispositivo do usuário para capturar e decodificar o QR Code ao vivo, sem exigir que o usuário tire uma foto e a envie manualmente.
- **FR-003**: Ao decodificar um QR Code com sucesso, o sistema MUST extrair o conteúdo (a URL) e enviá-lo automaticamente pelo mesmo fluxo de importação por URL/chave já existente, sem exigir nenhuma ação extra de copiar/colar do usuário.
- **FR-004**: Se o acesso à câmera não estiver disponível pela página (permissão negada pelo usuário, navegador sem suporte, ou qualquer outro motivo), o sistema MUST degradar graciosamente: a opção de leitura por câmera MUST ficar claramente indisponível, e as duas opções de importação já existentes MUST continuar funcionando normalmente, sem nenhuma mudança perceptível.
- **FR-008**: O financiALL MUST estar acessível por um endereço que satisfaça o requisito de contexto seguro do navegador (HTTPS, ou o equivalente reconhecido como seguro) na rede local onde o usuário o acessa pelo celular, para que a leitura por câmera desta feature seja de fato utilizável — provisionar esse acesso (ex.: certificado, e o que for necessário no Raspberry Pi para servi-lo) faz parte do escopo desta feature, não é um pré-requisito externo a ela.
- **FR-005**: Durante a leitura, o sistema MUST dar retorno visual claro do estado (buscando um código; código encontrado; erro), para o usuário saber que a leitura está em andamento.
- **FR-006**: Se o conteúdo decodificado do QR Code não for uma URL/chave de nota fiscal válida, o sistema MUST informar o erro de forma clara, reaproveitando a mesma validação e mensagem que já existem hoje para uma entrada de texto inválida.
- **FR-007**: O usuário MUST poder cancelar a leitura por câmera a qualquer momento e voltar às outras opções de importação, sem precisar recarregar a página.

### Key Entities

Nenhuma entidade nova — a leitura por câmera é só um novo canal de captura da mesma URL que o campo de texto "URL do QR Code ou chave de acesso" já aceita e processa hoje; nenhum dado novo é armazenado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O usuário importa uma nota fiscal apontando a câmera para o QR Code, sem sair do financiALL e sem copiar/colar nenhuma URL manualmente.
- **SC-002**: Quando o acesso à câmera não está disponível no navegador/dispositivo do usuário, as duas opções de importação já existentes continuam funcionando sem nenhuma mudança perceptível, e nenhum botão quebrado é exibido.
- **SC-003**: 100% dos QR Codes de nota fiscal válidos e legíveis apontados pela câmera resultam na mesma importação que colar a mesma URL manualmente já produz hoje.
- **SC-004**: O usuário consegue cancelar a leitura por câmera e usar outro método de importação sem recarregar a página.
- **SC-005**: O usuário consegue acessar o financiALL pelo celular, na rede local de casa, por um endereço que o navegador reconhece como seguro o suficiente para liberar o uso da câmera pela página.

## Assumptions

- O conteúdo do QR Code da nota fiscal é sempre a mesma URL que o campo de texto "URL do QR Code ou chave de acesso" já aceita hoje — nenhuma mudança no endpoint de backend de importação por URL é necessária; esta feature é só um novo canal de captura no frontend.
- O uso principal é pelo navegador do celular (onde o usuário hoje faz a leitura de QR Code); suporte em navegador de desktop é bônus, não requisito — poucos desktops têm câmera voltada para capturar um QR Code físico com praticidade.
- Não é necessário solicitar permissão de câmera de forma antecipada/persistente — a permissão é pedida pelo navegador só quando o usuário ativa a opção de leitura, comportamento padrão do navegador.
- Superfície visual nova nesta página — a verificação visual real (captura de tela + ausência de erro de console) e, se uma biblioteca de terceiro for vendorizada para decodificar QR Code, a validação de integridade desse asset, são obrigatórias antes de promover (Princípio VIII da constituição).
