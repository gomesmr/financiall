# Feature Specification: Upload de extrato/fatura bancária pela web

**Feature Branch**: `013-upload-extrato-web`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Upload de extrato/fatura bancária pela interface web, substituindo a necessidade de rodar script via SSH para importação recorrente. Hoje (features 010/011/012) o financiALL importa extrato/fatura (Itaú cartão, Itaú conta corrente, BB conta corrente, Mercado Pago fatura) só via script de linha de comando rodado manualmente. O usuário não administra Linux/Raspberry Pi e depende de pedir para o agente de IA rodar o script via SSH toda vez que baixa um extrato novo — isso não é self-service de verdade para uma importação que deveria ser recorrente mês a mês. O sistema deve detectar automaticamente qual dos formatos suportados é o arquivo enviado e mostrar o resumo da importação na mesma página, sem o usuário precisar informar manualmente qual banco/cartão é. Os scripts de linha de comando existentes continuam funcionando, como via adicional."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Importar um extrato/fatura novo sem precisar de ajuda técnica (Priority: P1)

O usuário baixa um extrato ou fatura novo (Itaú, Banco do Brasil ou
Mercado Pago) do site/app do banco. Hoje ele precisa pedir para alguém com
conhecimento técnico rodar um comando no servidor; ele quer conseguir
enviar esse arquivo sozinho, pela mesma tela onde já importa notas
fiscais, e ver na hora quantas transações entraram.

**Why this priority**: é o problema central que motiva a feature — sem
isso, a importação recorrente continua dependendo de alguém rodar um
comando para o usuário, todo mês, indefinidamente.

**Independent Test**: pode ser testado enviando, pela interface web, um
arquivo de cada um dos formatos suportados e conferindo que a importação
acontece e o resumo aparece na tela, sem precisar de acesso ao servidor.

**Acceptance Scenarios**:

1. **Given** um arquivo de fatura de cartão Itaú (`.xls` ou `.xlsx`) já
   baixado, **When** o usuário o envia pela tela de importação, **Then**
   o sistema reconhece o formato automaticamente, importa as transações e
   mostra um resumo (quantas foram importadas, quantas já existiam,
   quantas ficaram pendentes de revisão).
2. **Given** um arquivo de extrato de conta corrente Itaú, de extrato do
   Banco do Brasil, ou de fatura Mercado Pago, **When** enviado pela mesma
   tela, **Then** o sistema reconhece automaticamente qual dos formatos é
   e importa corretamente, sem o usuário precisar indicar o banco/cartão.
3. **Given** um arquivo já importado anteriormente (ou parcialmente
   sobreposto a um já importado), **When** enviado de novo pela tela,
   **Then** nenhuma transação é duplicada — o resumo mostra quantas já
   existiam.

---

### User Story 2 - Saber o que fazer quando o arquivo não é reconhecido (Priority: P2)

O usuário envia um arquivo que não corresponde a nenhum dos formatos
suportados (arquivo errado, exportação de um banco não coberto, arquivo
corrompido). Ele quer entender que o arquivo não foi aceito e por quê, em
vez de ver uma tela quebrada ou um resultado incerto.

**Why this priority**: importante para a confiança no fluxo self-service,
mas não bloqueia o caminho feliz (US1) — o usuário já tem o script CLI
como alternativa enquanto isso não existe.

**Independent Test**: pode ser testado enviando um arquivo de formato não
suportado (ex.: uma imagem, um `.xlsx` com colunas desconhecidas) e
conferindo que o sistema recusa com uma mensagem clara, sem gravar nada
parcial.

**Acceptance Scenarios**:

1. **Given** um arquivo cujo formato não corresponde a nenhum dos
   suportados, **When** o usuário o envia, **Then** o sistema recusa a
   importação com uma mensagem explicando que o formato não foi
   reconhecido, sem gravar nenhuma transação.
2. **Given** um arquivo corrompido ou ilegível, **When** enviado, **Then**
   o sistema recusa com uma mensagem de erro, sem travar a página nem
   gravar dado parcial.

---

### Edge Cases

- Dois dos formatos suportados compartilham a mesma extensão de arquivo
  (`.xls`/`.xlsx`) — a extensão sozinha não basta para decidir qual
  parser usar; o conteúdo do arquivo precisa desempatar.
- Um arquivo que "parece" um dos formatos suportados (mesma extensão,
  layout parecido) mas na verdade é de outra origem não deve ser aceito
  por engano e importado com o parser errado — nesse caso, é preferível
  recusar a arriscar interpretar dado incorretamente.
- O usuário envia o mesmo arquivo duas vezes seguidas por engano (ex.:
  clicou enviar duas vezes) — não pode duplicar transações.
- Um arquivo grande ou com muitas transações não deve travar a página
  enquanto processa (a operação é rápida, mas o usuário precisa de algum
  retorno visual enquanto aguarda).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir que o usuário envie um arquivo de
  extrato ou fatura bancária pela interface web, sem precisar de acesso
  ao servidor.
- **FR-002**: O sistema DEVE detectar automaticamente qual dos formatos
  suportados (fatura de cartão Itaú, extrato de conta corrente Itaú,
  extrato de conta corrente Banco do Brasil, fatura de cartão Mercado
  Pago) corresponde ao arquivo enviado, sem exigir que o usuário informe
  manualmente o banco ou tipo de conta.
- **FR-003**: Quando o arquivo não corresponder com confiança a nenhum
  formato suportado, o sistema DEVE recusar a importação com uma
  mensagem explicando o problema, sem gravar nenhuma transação.
- **FR-004**: O sistema DEVE mostrar, na mesma tela, um resumo da
  importação (transações importadas, já existentes, pendentes de
  revisão) imediatamente após o envio do arquivo.
- **FR-005**: O sistema DEVE continuar impedindo duplicata de transação
  já importada, incluindo quando o mesmo arquivo (ou um arquivo
  parcialmente sobreposto) é enviado mais de uma vez pela web.
- **FR-006**: As transações importadas pela web DEVEM passar pela mesma
  classificação automática de natureza e pela mesma reconciliação com
  nota fiscal já usadas pela importação via linha de comando — mesma
  qualidade de resultado, independente do caminho de entrada.
- **FR-007**: Os scripts de linha de comando já existentes DEVEM
  continuar funcionando sem alteração de comportamento — o upload web é
  um caminho adicional, não uma substituição.
- **FR-008**: Um arquivo corrompido ou ilegível enviado pela web NÃO DEVE
  gravar nenhum dado parcial.

### Key Entities

- **Transação**: mesma entidade já existente — nenhum atributo novo;
  passa a poder ser originada também por um envio feito pela interface
  web, além da importação histórica e dos scripts recorrentes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O usuário consegue importar um extrato ou fatura novo,
  sozinho, do início ao fim (enviar o arquivo e ver o resumo), sem pedir
  ajuda técnica nem acessar o servidor.
- **SC-002**: Os quatro formatos hoje suportados são reconhecidos
  corretamente sem o usuário precisar indicar qual é, com 100% de acerto
  contra os arquivos reais já usados para validar as features 010/011/012.
- **SC-003**: Um arquivo de formato não suportado é recusado com uma
  mensagem clara, sem gerar dado inconsistente no banco.
- **SC-004**: Reenviar um arquivo já importado pela web não duplica
  nenhuma transação.

## Assumptions

- Esta feature não adiciona suporte a nenhum banco/formato novo além dos
  4 já implementados (Itaú cartão, Itaú conta corrente, BB conta corrente,
  Mercado Pago fatura) — é só uma via de entrada nova para os mesmos
  parsers já existentes.
- A importação pela web é síncrona (o usuário aguarda alguns segundos e
  já vê o resultado), diferente da importação de nota fiscal (que usa
  fila assíncrona por causa de OCR) — extrato/fatura não precisa de OCR,
  então não há necessidade de fila.
- Reconciliação com nota fiscal e classificação automática de natureza já
  existem e não são alteradas por esta feature — só o caminho de entrada
  do arquivo muda.
- O titular (Marcelo/Cristine) de cada transação continua determinado
  pela conta/cartão de origem do arquivo (mesma regra já usada pelos
  parsers existentes), não por uma escolha manual do usuário no momento
  do upload.
