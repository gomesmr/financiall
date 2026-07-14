# Feature Specification: Excluir Nota Fiscal

**Feature Branch**: `002-excluir-nota-fiscal`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: "Excluir nota fiscal: permitir que o usuário apague uma nota fiscal já importada (e seus itens associados) pela UI, cobrindo o caso de notas malformadas/com erro de parse que ficaram incorretas no banco. Exclusão remove a nota e seus itens (cascata); após excluir, deve ser possível reimportar a mesma nota (chave/hash) sem bloqueio de idempotência residual. Ação é destrutiva então precisa de confirmação explícita na UI antes de excluir."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Excluir uma nota incorreta (Priority: P1)

Como usuário, depois de importar uma nota fiscal que ficou malformada (ex.: erro de parse deixou dados incompletos ou errados), quero excluí-la da minha base para que ela não polua a listagem de notas nem o resumo de gastos.

**Why this priority**: É o caso concreto que motivou a feature — sem isso, uma nota malformada fica presa na base permanentemente, distorcendo totais e histórico. Sem valor sem esta história.

**Independent Test**: Importar uma nota, acessar sua tela de detalhe ou a listagem, acionar "excluir", confirmar, e verificar que ela some da listagem e do resumo do mês.

**Acceptance Scenarios**:

1. **Given** uma nota fiscal importada (completa ou pendente de revisão) aparece na listagem de notas, **When** o usuário aciona a exclusão dessa nota e confirma a ação, **Then** a nota e todos os seus itens deixam de existir na base e não aparecem mais na listagem nem no resumo mensal.
2. **Given** o usuário está na tela de detalhe de uma nota, **When** ele aciona excluir e confirma, **Then** é redirecionado para a listagem de notas e vê uma confirmação de que a exclusão foi concluída.
3. **Given** o usuário aciona excluir, **When** ele cancela a confirmação (não confirma), **Then** a nota permanece intacta na base, sem nenhuma alteração.

---

### User Story 2 - Reimportar depois de excluir (Priority: P2)

Como usuário, depois de excluir uma nota que ficou malformada, quero conseguir reimportá-la (pela mesma URL/chave/foto) e desta vez ela entrar corretamente na base, sem o sistema recusar por achar que é duplicada.

**Why this priority**: Completa o caso de uso real — excluir sem poder reimportar deixa o usuário sem solução para o problema original (nota com erro de parse). É a continuação natural da US1, mas a base já funciona sem ela (o usuário só não conseguiria corrigir o dado).

**Independent Test**: Excluir uma nota com chave de acesso conhecida, reimportar a mesma nota pela mesma via de entrada, e verificar que ela é aceita e gravada normalmente (não rejeitada como duplicata).

**Acceptance Scenarios**:

1. **Given** uma nota foi excluída, **When** o usuário reimporta uma nota com a mesma chave de acesso (ou mesmo hash de conteúdo, se sem chave), **Then** o sistema grava a nova importação normalmente, como se fosse a primeira vez.

---

### User Story 3 - Feedback de erro ao excluir (Priority: P3)

Como usuário, se eu tentar excluir uma nota que já não existe mais (ex.: já foi excluída em outra aba, ou o link está desatualizado), quero uma mensagem clara em português em vez de uma tela de erro técnica.

**Why this priority**: Cobre um caso de borda de baixa frequência; a funcionalidade principal (US1/US2) já entrega o valor central sem esta história, mas sua ausência deixa uma experiência ruim num caso raro.

**Independent Test**: Tentar excluir uma nota usando um identificador que não existe na base e verificar que a resposta é uma mensagem de erro compreensível, sem quebrar a navegação.

**Acceptance Scenarios**:

1. **Given** um identificador de nota que não existe (ou já foi excluído), **When** o usuário tenta excluí-lo, **Then** o sistema exibe uma mensagem de erro clara em português e não altera nenhum outro dado.
2. **Given** um envio (upload) cujo arquivo e nota foram excluídos, **When** o usuário acessa o link de status desse envio (ex.: aba antiga, favorito), **Then** o sistema exibe uma mensagem clara de que o envio não está mais disponível, sem quebrar a navegação.

---

### Edge Cases

- Ao excluir uma nota, o arquivo físico (foto/PDF) do envio que a originou também é excluído — não fica retido em disco. Se o usuário quiser importar o mesmo documento novamente, precisa refazer o upload, mesmo que seja exatamente a mesma imagem/arquivo de antes.
- Se mais de um envio (ex.: uploads repetidos do mesmo documento) resultou na mesma nota, todos os arquivos desses envios são excluídos junto com a nota, não só o primeiro.
- Excluir uma nota com status "pendente de revisão" (dados incompletos) segue as mesmas regras de uma nota "completa" — não há tratamento diferenciado por status.
- Exclusão em lote (marcar várias notas e excluir de uma vez) está fora do escopo desta feature.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir que o usuário exclua uma nota fiscal individual a partir da tela de listagem de notas e da tela de detalhe da nota.
- **FR-002**: O sistema MUST exigir confirmação explícita do usuário antes de efetivar a exclusão, deixando claro que a ação é destrutiva e não pode ser desfeita.
- **FR-003**: Ao excluir uma nota, o sistema MUST excluir também todos os itens associados a ela (exclusão em cascata) e o(s) arquivo(s) físico(s) (foto/PDF) do(s) envio(s) que a originaram, sem deixar itens ou arquivos órfãos na base ou em disco.
- **FR-004**: Após a exclusão de uma nota, o sistema MUST permitir que uma nova importação com a mesma chave de acesso (ou mesmo hash de conteúdo, para notas sem chave) seja aceita e gravada normalmente, sem ser bloqueada por resquício da nota excluída.
- **FR-005**: Ao excluir uma nota, o sistema MUST excluir também o(s) registro(s) de envio (upload) que a originaram, junto com o arquivo físico — não fica um registro de envio apontando para um arquivo ou nota que não existem mais. Se o usuário acessar um link para um envio excluído dessa forma, o sistema MUST exibir uma mensagem clara de que o envio não está mais disponível, sem quebrar a navegação.
- **FR-006**: O sistema MUST exibir uma confirmação visível ao usuário de que a exclusão foi concluída com sucesso.
- **FR-007**: O sistema MUST exibir uma mensagem de erro clara em português quando o usuário tentar excluir uma nota que não existe (ou já foi excluída), sem quebrar a navegação.
- **FR-008**: Notas em qualquer status (completa ou pendente de revisão) MUST poder ser excluídas pela mesma funcionalidade.

### Key Entities

- **Nota Fiscal**: registro de uma nota importada (chave de acesso ou hash de conteúdo, emitente, valor, data, status). É o alvo direto da exclusão.
- **Item da Nota**: linha de produto/serviço pertencente a uma nota fiscal. Excluído em cascata junto com a nota.
- **Envio (upload)**: registro de uma tentativa de importação (foto/PDF ou URL) que pode ter gerado a nota. É excluído junto com a nota (registro e arquivo físico) — as duas entidades representam a mesma tentativa de importação incorreta e saem juntas da base.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O usuário consegue remover uma nota incorreta em até 30 segundos a partir do momento em que a encontra na listagem.
- **SC-002**: 100% das notas excluídas deixam de aparecer na listagem de notas e no resumo mensal imediatamente após a exclusão.
- **SC-003**: O usuário consegue reimportar com sucesso uma nota previamente excluída, sem qualquer intervenção manual fora da interface do sistema.
- **SC-004**: Nenhuma exclusão ocorre sem uma etapa de confirmação explícita do usuário.
- **SC-005**: Nenhum arquivo de imagem/PDF órfão permanece em disco após a exclusão de uma nota.

## Assumptions

- Exclusão é definitiva (não há lixeira, soft-delete ou "desfazer" neste ciclo); se essa necessidade aparecer no uso real, é revisitada em uma feature futura.
- Excluir uma nota remove por completo o rastro do envio que a originou (registro + arquivo); não há necessidade de manter auditoria de uploads passados neste ciclo.
- Não há diferenciação de permissões entre usuários (Marcelo/Cristine) para excluir notas — qualquer um pode excluir qualquer nota, consistente com a decisão de não ter autenticação no sistema.
- Exclusão em lote (múltiplas notas de uma vez) está fora do escopo; cada exclusão é de uma nota por vez.
- A funcionalidade é acessada pela mesma interface web já existente (listagem e detalhe de notas), sem necessidade de uma tela nova dedicada.
