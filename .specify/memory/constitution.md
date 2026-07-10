<!--
Sync Impact Report
==================
Version change: 1.0.0 → 1.1.0
Modified principles: nenhum princípio foi redefinido (conteúdo dos 7 princípios mantido)
Added sections:
  - Identidade do Projeto (nome "financiALL", missão e princípio "ALL" de convergência)
Removed sections: nenhuma
Renamed: "Finanças Pessoais Constitution" → "financiALL Constitution"
Updated: Restrições do Projeto — lista de fontes de dados passa a incluir explicitamente
  extrato bancário, alinhando a restrição de escopo à identidade "ALL"
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ compatível (sem referência ao nome do projeto)
  - .specify/templates/spec-template.md ✅ compatível (sem referência ao nome do projeto)
  - .specify/templates/tasks-template.md ✅ compatível (sem referência ao nome do projeto)
  - specs/001-importar-nfce/spec.md ⚠ pendente — feature em andamento não referencia o nome
    do projeto diretamente, nenhuma ação obrigatória, mas pode citar "financiALL" ao ser retomada
Follow-up TODOs: nenhum
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
aceito sem teste correspondente.

**Racional**: são as três rotinas cuja falha silenciosa corrompe dados
financeiros sem sinal visível ao usuário — precisam de rede de segurança
automatizada, não apenas revisão manual.

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
correspondente antes de merge (Princípio V). Revisão de código verifica: (a)
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

**Version**: 1.1.0 | **Ratified**: 2026-07-10 | **Last Amended**: 2026-07-10
