<!--
Sync Impact Report
==================
Version change: 1.1.0 → 1.2.0
Modified principles:
  - V. Testável por Construção — expandido: para rotinas que processam dado externo ao
    controle do código, teste sintético e validação com amostra real são tratados como
    **duas barreiras distintas**, não uma extensão da mesma — a segunda MUST acontecer
    antes de promover a história, mesmo quando a primeira já passou. Racional ampliado
    com o achado concreto que motivou a mudança. Adicionado também: ao definir a tarefa
    de validação real, identificar as dimensões de variação relevantes para o tipo de
    entrada (fonte, condição de captura, formato) em vez de validar contra amostra única
    genérica.
Added sections: nenhuma
Removed sections: nenhuma
Updated: Fluxo de Desenvolvimento e Qualidade — cláusula (a) sobre Princípio V passa a
  citar a exigência de amostra real explicitamente, como etapa distinta antes de promover.
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ compatível ("Constitution Check" é placeholder
    genérico, sem texto específico do Princípio V a atualizar)
  - .specify/templates/spec-template.md ✅ compatível (sem referência ao conteúdo do
    Princípio V)
  - .specify/templates/tasks-template.md ⚠ atualizado — nova subseção "Real-Data
    Validation for User Story N" adicionada após "Implementation" em cada história de
    exemplo (US1/US2/US3), explicitamente separada de "Tests", com nota de que não é
    extensão do teste automatizado. Numeração de tarefas ajustada (T018→T031) para
    acomodar as novas tarefas sem colisão. Instrução adicionada em cada subseção: ao
    preencher para uma feature real, identificar 2-3 dimensões de variação real
    relevantes ao tipo de entrada daquela história (não uma lista fixa genérica —
    depende do que a história ingere), com sub-itens de tarefa por dimensão.
  - README.md ✅ compatível (lista princípios só por nome/rótulo — "testável por
    construção" continua correto como rótulo, detalhe expandido fica só na constituição)
Follow-up TODOs: nenhum
Origem da mudança: finall/docs/RELATORIO-FEATURE-001.md (Seção 4) — 6 bugs de
  comportamento na feature 001 só apareceram testando com notas fiscais reais, apesar de
  testes automatizados cobrindo os casos de borda conhecidos passarem o tempo todo.
  Promovido também como lição de processo em harness/core/SDD_GUARDRAILS.md (2026-07-14).
-->

# financiALL Constitution

## Identidade do Projeto

financiALL é a base única de finanças pessoais do usuário: extrato bancário e
nota fiscal convergem para o mesmo lugar, com o gasto detalhado item a item
sempre que a fonte permitir. "ALL" é o princípio organizador — toda fonte de
gasto (banco, nota fiscal, e futuras fontes) MUST alimentar a mesma base de
dados única, nunca bases paralelas ou silos por fonte. Uma nova fonte de dados
só é aceita no projeto se puder ser conciliada com o que já existe na base
(ex.: um lançamento de extrato e a nota fiscal correspondente devem poder ser
associados), preservando uma visão unificada do gasto.

## Core Principles

### I. Simplicidade e Manutenibilidade
A solução direta é sempre preferida à solução esperta. Código deve ser fácil de
ler e de manter por uma única pessoa, sem camadas de abstração especulativas.
Complexidade adicional (novas dependências, padrões genéricos, camadas de
indireção) só é aceitável quando resolve uma necessidade concreta e documentada;
caso contrário, é rejeitada na revisão.

**Racional**: este é um projeto pessoal mantido por poucas mãos; esperteza
prematura custa mais em manutenção do que economiza em execução.

### II. Idempotência é Obrigatória (NON-NEGOTIABLE)
A mesma nota fiscal NUNCA é gravada duas vezes. A deduplicação é feita
primariamente pela chave de acesso de 44 dígitos; na ausência de chave de
acesso, usa-se hash de conteúdo do documento como chave alternativa. Toda
rotina de ingestão (arquivo, URL, e-mail, upload manual) MUST verificar
existência antes de persistir.

**Racional**: dados financeiros duplicados corrompem relatórios e somas;
idempotência é a única garantia contra reprocessamento acidental (reimport,
reexecução de job, múltiplas fontes para a mesma nota).

### III. Tratamento de Erro Explícito em Entradas Externas
Toda entrada que se origina fora do controle direto do código (URL, HTML de
terceiros, arquivo enviado pelo usuário, resposta de portal externo) MUST ter
tratamento de erro explícito — nunca deixar exceção não tratada propagar para
o usuário final. Decisões não óbvias (ex.: por que um campo é opcional, por
que um encoding específico é assumido) são comentadas em 1–2 linhas no ponto
da decisão.

**Racional**: entradas externas são a maior fonte de falhas silenciosas;
comentários curtos no código evitam que a próxima pessoa (ou o próprio autor
em 6 meses) reintroduza o mesmo bug.

### IV. Dados Financeiros São Sensíveis
CPF, chave de acesso, CNPJ e valores monetários NUNCA são gravados em log em
texto claro. Esses dados MUST ser mascarados ou omitidos em qualquer saída de
log, stack trace ou mensagem de diagnóstico. Envio a serviços externos além do
estritamente necessário para a funcionalidade (ex.: consulta ao portal SEFAZ
que emitiu a nota) é proibido.

**Racional**: é um sistema de finanças pessoais de pessoa física; vazamento de
CPF/valores tem custo real e nenhum benefício correspondente para o projeto.

### V. Testável por Construção
Extração de chave de acesso, deduplicação e parsing de notas MUST ter testes
automatizados cobrindo o caminho feliz e os casos de borda conhecidos (chave
ausente, HTML malformado, arquivo corrompido). Código novo nessas áreas não é
aceito sem teste correspondente. **Para rotinas que processam dado vindo de
fora do controle direto do código (OCR de foto, scraping de portal externo,
leitura de QR code, qualquer parsing de formato não controlado pelo
projeto), teste automatizado sintético e validação com amostra real são
duas barreiras distintas, não uma extensão da mesma: a primeira confirma
que o código trata os casos já previstos; a segunda confirma que ele
sobrevive a uma amostra real, não construída pelo autor do teste. A segunda
barreira MUST acontecer antes de promover a história (dev → main), mesmo
quando a primeira já passa — passar nos testes automatizados não é
suficiente para considerar a rotina pronta. Ao definir a tarefa de
validação real, identificar as dimensões de variação relevantes para o
tipo de entrada da rotina (ex.: fonte/proveniência, condição de captura,
formato) em vez de validar contra uma única amostra genérica.**

**Racional**: são as três rotinas cuja falha silenciosa corrompe dados
financeiros sem sinal visível ao usuário — precisam de rede de segurança
automatizada, não apenas revisão manual. **A exigência de amostra real além
do teste sintético existe porque a feature 001 (importação de NFC-e) teve 6
bugs de comportamento que só apareceram testando com notas fiscais reais do
usuário, apesar de testes automatizados cobrindo os casos de borda
conhecidos passarem o tempo todo — iluminação desigual de foto, chave
formatada em grupos de 4 dígitos, layout real de um portal específico e
resolução de foto de celular degradando leitura de QR code não eram "casos
de borda conhecidos" até acontecerem de fato.**

### VI. Português nos Artefatos Voltados ao Usuário
Mensagens ao usuário, docstrings e artefatos gerados (relatórios, exports,
mensagens de erro exibidas) MUST estar em português. Identificadores de código
e termos técnicos permanecem na forma original quando não há tradução natural.

**Racional**: o público-alvo do projeto é falante de português; consistência
de idioma reduz atrito de uso e de manutenção.

### VII. Fontes Frágeis Degradam sem Quebrar o Fluxo Principal
Integrações com fontes frágeis por natureza (portais SEFAZ por UF, captcha,
scraping de HTML de terceiros) são tratadas como best-effort. Falha nessas
fontes MUST degradar graciosamente (pular, marcar como pendente, seguir sem
o dado complementar) e nunca interromper o fluxo principal de ingestão e
registro de notas.

**Racional**: portais de terceiros mudam e falham fora do controle do
projeto; o valor central (registrar a nota) não pode depender da
disponibilidade de um enriquecimento opcional.

## Restrições do Projeto

Escopo é pessoa física: não há suporte a certificado e-CNPJ nem a fluxos que
dependam dele. Qualquer integração que exija e-CNPJ está fora de escopo e deve
ser rejeitada ou adiada, não contornada com workarounds frágeis. Fontes de
dados esperadas incluem extrato bancário (import de arquivo ou integração),
QR codes e URLs de NF-e/NFC-e, e-mails com XML/PDF anexado, e upload manual de
arquivo pelo usuário — todas convergindo para a mesma base única (Identidade
do Projeto).

## Fluxo de Desenvolvimento e Qualidade

Mudanças em extração de chave, deduplicação e parsing exigem teste
correspondente antes de merge. Quando a rotina processa dado externo, há
uma segunda barreira distinta, obrigatória antes de promover para produção:
validação com pelo menos uma amostra real (Princípio V) — não confundir com
a primeira, nem pular por já ter passado nos testes automatizados. Revisão
de código verifica: (a)
ausência de dados sensíveis em log (Princípio IV), (b) tratamento de erro em
toda entrada externa nova (Princípio III), (c) que nenhuma solução foi
adicionada além do necessário para o requisito (Princípio I). Falhas de fontes
frágeis são validadas com um teste que simula a fonte indisponível, confirmando
degradação graciosa (Princípio VII).

## Governance

Esta constituição prevalece sobre qualquer outra prática ou convenção
informal do projeto. Emendas exigem: (1) descrição da mudança e motivação,
(2) atualização deste arquivo com o Sync Impact Report no topo, (3) revisão
dos templates dependentes em `.specify/templates/` para consistência. O
versionamento segue semântica: MAJOR para remoção ou redefinição incompatível
de princípio; MINOR para adição de princípio ou expansão material de
orientação; PATCH para esclarecimentos e correções de redação. Toda revisão
de código MUST verificar conformidade com os princípios acima; complexidade
que viole o Princípio I MUST ser justificada explicitamente na revisão.

**Version**: 1.2.0 | **Ratified**: 2026-07-10 | **Last Amended**: 2026-07-14
