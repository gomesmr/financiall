# Research: Leitura de QR Code pela Câmera

## 1. Onde decodificar o QR Code: reaproveitar o decodificador já existente no servidor

**Decisão**: os frames capturados pela câmera do celular (client-side, via
`getUserMedia`) são enviados como imagens JPEG comprimidas para um endpoint
novo e enxuto no backend, que reaproveita `src/services/qrcode_reader.py`
(`decodificar_qrcode`, baseado em `pyzbar`/`zbar`) — a mesma função já usada
em produção pelo pipeline de foto/OCR (feature 001) desde sempre. Nenhuma
biblioteca de decodificação de QR Code nova é vendorizada no frontend.

**Rationale**: decodificar QR Code é um algoritmo não trivial (detecção de
padrão de posição, correção de erro Reed-Solomon) — reimplementar do zero
não se paga, mas o projeto **já tem** um decodificador testado e comprovado
em produção; usá-lo de novo é a opção mais simples possível (Princípio I),
mais simples até que vendorizar uma biblioteca JS nova. Evita por completo o
risco que já se concretizou na feature 006 (asset de terceiro vendorizado
vindo corrompido da própria origem) para a parte de decodificação — não há
asset de terceiro novo para essa parte.

**Alternatives considered**: biblioteca JS de decodificação client-side
(ex.: `jsQR`) — rejeitada por introduzir uma dependência nova onde já existe
uma solução testada no projeto, e por reintroduzir exatamente o tipo de
risco (integridade de asset de terceiro vendorizado) que motivou o Princípio
VIII da constituição.

## 2. Contrato do novo endpoint de decodificação

**Decisão**: `POST /notas/qrcode-frame`, recebendo o corpo como imagem
(`Content-Type: image/jpeg`), retornando `200 {"entrada": "<texto decodificado>"}`
quando um código é encontrado, ou `200 {"entrada": null}` quando não (não é
erro — o cliente simplesmente tenta o próximo frame). O cliente, ao receber
uma `entrada` não nula, chama o endpoint `POST /notas` **já existente** e
inalterado, exatamente como já acontece hoje ao colar a URL manualmente —
reaproveitando toda a validação e as mensagens de erro já existentes (cobre
FR-003 e FR-006 sem nenhum código novo de validação).

**Rationale**: mantém o endpoint de importação por URL/chave (`POST /notas`)
totalmente intocado, como já pedido na descrição original da feature; a
decodificação de frame é uma responsabilidade separada e pequena o
suficiente para não precisar de nenhuma lógica de importação duplicada.

**Alternatives considered**: um único endpoint combinado
"decodifica-e-importa" — rejeitado por duplicar a validação que `POST
/notas` já faz, e por acoplar duas responsabilidades (decodificar imagem;
validar/importar nota) que o projeto já mantém separadas em outros pontos
(ex.: upload de foto enfileira, decodifica e só then importa, em etapas
distintas dentro do worker).

## 3. Resolução do frame capturado (revisado após validação com QR Code real pequeno)

**Decisão original**: o frame capturado do vídeo seria desenhado num
`<canvas>` reduzido para no máximo ~1200px no lado maior antes de exportar
como JPEG (qualidade ~0.7) e enviar ao servidor, com base no comentário do
`qrcode_reader.py` sobre fotos de celular em resolução total (~4032x3024)
decodificando melhor reduzidas a ~1500px.

**Achado real (Princípio V)**: essa decisão presumia um frame de origem em
resolução ALTA (como uma foto), mas o `getUserMedia` sem restrição
explícita de resolução entrega um stream de vídeo tipicamente bem mais
baixo (algo como 640x480) — nesse caso o alvo de 1200px nunca chegava a
reduzir nada (o vídeo já era menor que o alvo), e o frame de origem em si
não tinha pixels suficientes para resolver os módulos de um QR Code
pequeno (~1,4x1,4cm) à distância normal de captura. Confirmado na prática:
um QR Code de ~2,4x2,4cm foi lido sem problema, mas um de ~1,4x1,4cm não —
mesmo o app nativo de câmera do iPhone (que usa resolução alta do sensor)
lendo o menor sem dificuldade.

**Decisão revisada**: pedir explicitamente resolução alta ao `getUserMedia`
(`width: {ideal: 1920}, height: {ideal: 1080}` — `ideal`, não `exact`, para
o navegador cair graciosamente para o que a câmera suportar) e elevar o
alvo de captura para 1920px no lado maior (não reduzir de volta abaixo da
resolução agora pedida), com qualidade JPEG ~0.85 (menos perda de detalhe
fino nos módulos do código).

**Rationale**: mais pixels por módulo do QR Code é o fator que realmente
resolve códigos pequenos — o raciocínio original (reduzir uma foto grande)
não se aplicava a um frame de vídeo que já não era grande o suficiente.

## 4. Frequência de tentativa e cancelamento

**Decisão**: enquanto a leitura por câmera está ativa, o cliente captura e
envia um frame a cada ~700ms; para ao primeiro `entrada` não nula (aciona a
importação e encerra a captura), ou quando o usuário cancela explicitamente
(FR-007) — sem limite arbitrário de tentativas, já que "nenhum código
encontrado ainda" não é um estado de erro, é o estado normal enquanto o
usuário mira o QR Code (FR-005).

**Rationale**: ~1.4 tentativas/segundo é frequente o suficiente para
parecer responsivo ao usuário, e leve o suficiente para não sobrecarregar
um Raspberry Pi atendendo no máximo duas pessoas da mesma casa.

## 5. Acesso à câmera exige contexto seguro (HTTPS) — provisionamento no Raspberry Pi

**Decisão**: instalar **Caddy** como proxy reverso na frente do `waitress`
já existente, usando a diretiva `tls internal` (Caddy gera e gerencia sua
própria autoridade certificadora local e certificados-folha automaticamente,
sem precisar de comandos manuais de `openssl` nem de um domínio público).
Caddy escuta numa porta HTTPS e encaminha para `localhost:5000` (produção) e
`localhost:5005` (dev) — o `waitress`/Flask/systemd existentes continuam
exatamente como estão, sem nenhuma mudança.

**Rationale**: `getUserMedia()` (a API do navegador para acessar a câmera)
só funciona em "contexto seguro" — HTTPS, ou `localhost` — e o financiALL
hoje é acessado pelo celular via `http://finall.local:5005`, que não
satisfaz esse requisito. Um proxy reverso é a mudança de menor superfície
possível: nenhuma linha de código Python muda, só uma camada nova na frente.
Caddy foi escolhido entre proxies reversos por ser um único binário, com
geração de certificado autoassinado embutida (não depende de acesso à
internet nem de uma CA pública — mesma restrição de "funciona offline" já
aplicada a outros assets do projeto), e configuração mínima (poucas linhas
de `Caddyfile`).

O aviso de certificado não confiável que o navegador do celular mostra na
primeira visita **não bloqueia** a funcionalidade: uma vez que o usuário
prossegue (toque em "Avançado → Continuar"), a página carrega como origem
`https://`, que já satisfaz o requisito de contexto seguro do navegador
para liberar a câmera — não é necessário instalar a autoridade certificadora
do Caddy no celular para a feature funcionar (é um passo opcional, só para
remover o aviso visual permanentemente).

**Alternatives considered**: habilitar a câmera via flag de navegador
(`chrome://flags/#unsafely-treat-insecure-origin-as-secure`) — rejeitada
por só existir em navegadores baseados em Chromium (não funciona em Safari
iOS), exigir configuração manual repetida por dispositivo, e ser reiniciada
a cada atualização do navegador em alguns casos — muito mais frágil que uma
mudança de infraestrutura feita uma vez. Trocar o `waitress` por um
servidor WSGI com suporte nativo a TLS — rejeitada por exigir mudança no
código/configuração da aplicação já testada e estável, quando um proxy na
frente resolve o mesmo problema sem tocar nela (Princípio I).

## 6. Câmera preferencial: traseira

**Decisão**: ao solicitar acesso à câmera via `getUserMedia`, pedir
`facingMode: "environment"` (câmera traseira) como preferência.

**Rationale**: é a câmera fisicamente prática para apontar para um objeto
(o QR Code impresso no cupom), mesmo comportamento que o app nativo de
câmera do celular já usa por padrão quando o usuário lê o QR Code
manualmente hoje.

## 7. Dimensões de variação real para a validação obrigatória (Princípio V)

O Princípio V da constituição cita "leitura de QR code" nominalmente como
rotina que processa dado externo — validação com amostra real é uma
barreira distinta dos testes automatizados sintéticos, obrigatória antes de
promover. Dimensões de variação real identificadas para esta feature
especificamente (diferente da validação já feita para o decodificador em
si, na feature 001 — aqui a variação nova é a **captura ao vivo pela
câmera**, não o decodificador):

1. **Distância/ângulo de captura ao vivo** — diferente de uma foto já
   enquadrada e estática enviada por upload, a câmera ao vivo captura vários
   frames em posições variáveis enquanto o usuário mira o QR Code.
2. **Compressão do frame gerado no navegador** (JPEG de canvas, qualidade
   ~0.7) — potencialmente mais degradado que o arquivo de foto original que
   o pipeline de upload já testa.
3. **Dispositivo/câmera diferente** — pelo menos os dois celulares reais da
   casa (do usuário e da Cristine), que podem ter câmeras/qualidade
   distintas.

## 8. Princípio VIII — o que exige validação de integridade nesta feature

**Decisão**: nenhum asset de terceiro é vendorizado para o frontend desta
feature (Seção 1) — a checagem de integridade de formato do Princípio VIII
não se aplica a nenhum arquivo novo do projeto. O Caddy é instalado como
pacote/binário do sistema operacional no Raspberry Pi (canal com
verificação de integridade própria do gerenciador de pacotes/distribuição),
não como um arquivo copiado manualmente para dentro do repositório — a
cláusula do Princípio VIII sobre "asset de terceiro vendorizado" tem como
alvo arquivos como fonte/imagem/script/CSS copiados para `static/`, não
software de sistema instalado via canal confiável. A verificação visual
real (captura headless + checagem de erro de console) **se aplica**
normalmente, por esta feature introduzir superfície visual nova na página
de Importar.
