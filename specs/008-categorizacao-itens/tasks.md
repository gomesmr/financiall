---

description: "Task list for feature 008 — Categorização de Itens de Nota Fiscal"

---

# Tasks: Categorização de Itens de Nota Fiscal

**Input**: Design documents from `/specs/008-categorizacao-itens/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: incluídos, mesmo padrão já usado em todas as features anteriores (contrato +
unidade), reforçado pelo Princípio V (classificação de item processa descrição vinda de
fonte externa — OCR/scraping).

**Real-Data Validation**: obrigatória para US1, US2 e US3 — a cascata de classificação
processa descrição de item de NFC-e, mesma origem externa não controlada já coberta pelo
Princípio V nas features 001/004. N/A para US4 (opera sobre dado já classificado) e US5
(gestão de taxonomia é entrada do próprio usuário, não dado externo).

**Visual Verification**: obrigatória para as 5 histórias — Constitution Principle VIII.
Nenhum asset de terceiro é vendorizado nesta feature (research.md #14), então o sub-check
de integridade de asset é N/A em todas as histórias.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: US1-US5 conforme spec.md

## Path Conventions

Projeto único: `src/api/`, `src/services/`, `src/storage/`, `src/models/`, `src/scripts/`,
`tests/` na raiz do repo.

---

## Phase 1: Setup

**Purpose**: Insumo sem o qual nenhuma classificação automática acerta nada — a taxonomia e
o corpus real de validação (Tarefa 1 do brief de preparação).

- [X] T001 Validar/ajustar a taxonomia-semente (`assets/files.zip/taxonomia-v1-rascunho.md`)
      e produzir a versão definitiva de categorias/subcategorias em
      `src/scripts/seed_taxonomia_categorizacao.py` (fonte de dado do seed, não hardcoded
      espalhado) — decide os pontos em aberto do rascunho (subcategorias de Limpeza; Bebê e
      Pet como topo próprios; separar Alcoólicas; categoria de renda) antes de qualquer
      outra tarefa depender da taxonomia; já decidido: **sem** categoria/subcategoria
      fallback "Outros" — nem como topo, nem repetida embaixo de mais de uma categoria-pai
      (research.md #17); item sem categoria clara permanece pendente
- [X] T002 [P] Copiar `assets/files.zip/corpus-descricoes-produtos.txt` (760 descrições
      reais) para `tests/fixtures/corpus_descricoes_produtos.txt`, reduzido a 327 linhas
      (uma por combinação única de estilo de escrita × marca — sem código de barras/NCM
      nesta feature, a repetição de tamanho/quantidade da mesma marca não agregava sinal de
      teste) — fixture da primeira barreira do Princípio V (research.md #13)

**Checkpoint**: taxonomia definitiva e corpus real disponíveis para todo o resto da feature.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema, normalização, a cascata de classificação e o suporte a hierarquia
(`parent_id`) na criação de categoria — mecanismo compartilhado que as 5 histórias usam.
O suporte a `parent_id`/quase-duplicata entra aqui (não em US5) porque a criação inline de
subcategoria durante a classificação (US1/US4) depende dele desde o MVP — ver "Dependencies
& Execution Order" abaixo.

**⚠️ CRITICAL**: Nenhuma história pode ser implementada de forma completa antes desta fase.

- [X] T003 Estender o schema em `src/storage/db.py` (data-model.md): `categoria.parent_id`;
      `item_nota.categoria_id` + `descricao_normalizada` + `metodo_classificacao`; tabelas
      novas `cache_descricao_categoria`, `regra_categoria`,
      `historico_classificacao_item` — todas via `ALTER TABLE`/`CREATE TABLE IF NOT EXISTS`
      idempotentes, chamadas em `init_db()`, mesmo padrão de
      `_garantir_coluna_categoria_id`; substituir o índice único global de
      `categoria.nome_normalizado` pelos dois índices parciais escopados por nível
      (topo vs. subcategoria — research.md #19, data-model.md), via `DROP INDEX IF EXISTS`
      + `CREATE UNIQUE INDEX IF NOT EXISTS`
- [X] T004 [P] Atualizar `src/models/categoria.py`: campo `parent_id: int | None = None`
- [X] T005 [P] Atualizar `src/models/item_nota.py`: campos `categoria_id`,
      `descricao_normalizada`, `metodo_classificacao` (todos `| None = None`)
- [X] T006 [P] Criar `src/services/normalizacao.py` com `normalizar_descricao(descricao) ->
      str` (maiúsculas, remoção de acento via `unicodedata.normalize("NFKD", ...)`, colapso
      de espaços — research.md #1); dicionário de abreviações inicialmente vazio, populado
      na T030 (US3) a partir do corpus real (T002)
- [X] T007 Criar `src/scripts/seed_taxonomia_categorizacao.py`: mecanismo idempotente que lê
      a taxonomia definitiva (T001) e insere em `categoria` (só o que ainda não existe, por
      `nome_normalizado`) e lê um arquivo de regras-semente (inicialmente vazio/mínimo) para
      `regra_categoria` — depende de T001, T003
- [X] T008 Criar `src/services/classificacao_itens.py` e a operação de persistência
      correspondente em `src/storage/db.py` — depende de T003, T006:
  - [X] `classificar_item_automaticamente(item_id, categoria_id, metodo, db_path)` em
        `src/storage/db.py` (data-model.md): `UPDATE item_nota SET categoria_id,
        metodo_classificacao` + upsert em `cache_descricao_categoria` + `INSERT` em
        `historico_classificacao_item` (`categoria_id_anterior = NULL`), uma transação
  - [X] `classificar_item(descricao_normalizada, db_path) -> tuple[int | None, str | None]`
        em `classificacao_itens.py`: cascata cache (Tier 1) → regra ativa mais específica
        (Tier 2) → `(None, None)` (Tier 3, pendente) — research.md #6/#8/#10; se a
        descrição for `None`/vazia (após `strip()`), retorna `(None, None)` direto, sem
        tentar cache/regra (research.md #20)
  - [X] `classificar_itens_pendentes_da_nota(nota_fiscal_id, db_path)` em
        `classificacao_itens.py`: aplica `classificar_item` a todo `item_nota` com
        `categoria_id IS NULL` da nota, persistindo via `classificar_item_automaticamente`
  - [X] Unit test (`tests/unit/test_classificacao_itens.py`): `classificar_item_automaticamente`
        grava `historico_classificacao_item` corretamente (`metodo`, `categoria_id_anterior`
        sempre `NULL`) para os casos cache e regra (FR-014); item com descrição `None`/vazia
        fica pendente sem lançar exceção (research.md #20)
- [X] T009 Conectar `classificar_itens_pendentes_da_nota` (T008) logo após a inserção de
      itens nos três pontos já existentes: `src/services/importador.py` (as duas chamadas de
      `storage_db.inserir_itens`) e `src/services/importar_historico.py`
      (`storage_db.inserir_nota_com_itens`) — research.md #8/#9; nenhuma mudança de
      assinatura nessas funções, só a chamada adicional logo depois
- [X] T010 Criar `src/api/routes_itens.py` (blueprint `itens_bp`, vazio por enquanto) e
      registrar em `src/api/app.py`
- [X] T011 Estender `src/services/categorias.py` (`validar_e_criar_categoria`) e
      `src/storage/db.py` (`criar_categoria`/`editar_categoria`) para aceitar `parent_id`
      como parâmetro — depende de T003:
  - [X] `criar_categoria`/`editar_categoria` em `db.py` passam a aceitar `parent_id`,
        validando que uma categoria com `parent_id` preenchido não pode, por sua vez, ser
        `parent_id` de outra (2 níveis fixos, data-model.md)
  - [X] `validar_e_criar_categoria` em `categorias.py` passa a receber `parent_id` (repassado
        do endpoint, T012) e ganha checagem de quase-duplicata (proximidade sobre
        `nome_normalizado`, ex.: prefixo/substring) e parâmetro `forcar` para criar mesmo com
        aviso (FR-002) — escopada pelo mesmo nível do índice único (research.md #19):
        categoria de topo comparada globalmente contra outras categorias de topo;
        subcategoria comparada só contra as demais subcategorias do mesmo `parent_id`
  - [X] Unit test (`tests/unit/test_categorias.py`): quase-duplicata escopada por nível
        (não avisa sobre reuso de nome entre pais diferentes) e rejeição de um 3º nível de
        hierarquia
- [X] T012 Estender `POST /categorias` em `src/api/routes_categorias.py` para aceitar
      `parent_id` no corpo e retornar `409` com sugestão em caso de quase-duplicata (a menos
      que `forcar: true`) — contracts/api.md; depende de T011. Contract test correspondente
      em `tests/contract/test_api_contract.py`

**Checkpoint**: schema pronto, cascata funcional e conectada à importação, e criação de
categoria/subcategoria (com `parent_id` e aviso de quase-duplicata) já disponível — mesmo
sem nenhuma UI ainda.

---

## Phase 3: User Story 1 - Classificar itens pendentes manualmente (Priority: P1) 🎯 MVP

**Goal**: Fila de itens pendentes, agrupada por descrição e por nota; atribuição manual
individual ou em lote; suporte a classificação parcial (só categoria, subcategoria
pendente).

**Independent Test**: importar uma nota com um item de descrição nunca vista, abrir a fila
de pendentes, atribuir categoria e subcategoria, e confirmar que o item passa a aparecer
classificado.

### Implementation for User Story 1

- [X] T013 [US1] `listar_itens_pendentes(nota_fiscal_id=None, db_path)` em
      `src/storage/db.py` (data-model.md): sem `nota_fiscal_id`, agrupado por
      `descricao_normalizada` com contagem; com `nota_fiscal_id`, itens pendentes daquela
      nota sem agrupamento; inclui também a contagem agregada (total pendente vs. total de
      itens) para o resumo de SC-002 (research.md #21)
- [X] T014 [US1] `atribuir_categoria_manual(item_id, categoria_id, db_path)` em
      `src/storage/db.py`: grava `item_nota`, upsert em `cache_descricao_categoria`,
      `INSERT` em `historico_classificacao_item` — e, quando o item de origem estava
      pendente, resolve automaticamente todos os demais `item_nota` pendentes com a
      mesma `descricao_normalizada` (spec.md US1 cenário 2, research.md #15), cada um
      com sua própria linha de histórico; correção de item já classificado (US4) nunca
      dispara esse efeito colateral. `classificar_grupo_pendente(descricao_normalizada,
      categoria_id, db_path)` é a mesma operação entrando pela descrição em vez de por
      um item (conveniência da UI agrupada) — reaproveitar `atribuir_categoria_manual`
      internamente, não duplicar a lógica
- [X] T015 [US1] `GET /itens/pendentes` (com `?nota_id=`) em `src/api/routes_itens.py`,
      incluindo o campo `resumo` (contracts/api.md, research.md #21)
- [X] T016 [US1] `POST /itens/pendentes/classificar-grupo` em `src/api/routes_itens.py`
- [X] T017 [US1] `PUT /itens/<id>/categoria` em `src/api/routes_itens.py` — atribuição
      individual, aceita um único `categoria_id`, que pode apontar para uma categoria de
      topo (classificação parcial, FR-011) ou uma subcategoria
- [X] T018 [US1] `GET /ver/pendentes` em `src/api/routes_itens.py` (rota de página, mesmo
      padrão de `pagina_categorias()` em `routes_categorias.py`) e o template novo
      `src/api/templates/pendentes.html`:
  - [X] `obter_evolucao_classificacao(db_path)` em `src/services/classificacao_itens.py`
        (consulta própria, mesmo padrão de `services/resumo.py`/`_query_resumo_por_mes` —
        não delegado a `storage/db.py`): duas séries cumulativas — itens totais por
        `nota_fiscal.data_importacao`, itens classificados pelo menor `timestamp` por
        `item_nota_id` em `historico_classificacao_item` (research.md #22)
  - [X] Resumo no topo da página ("N pendentes de M itens no total" — `resumo` de T015,
        research.md #21)
  - [X] Gráfico de linhas (Plotly, já vendorizado desde a feature 005 — nenhum asset novo)
        com as duas séries de `obter_evolucao_classificacao`, dados entregues via
        `{{ ... | tojson }}` renderizado pelo servidor (research.md #22), sem endpoint JSON
        novo
  - [X] Fila agrupada por descrição normalizada (com contagem e ação em lote) e alternância
        para visão por nota; campo único de autocomplete sobre a lista de
        categorias/subcategorias já carregada (filtro no navegador, sem endpoint de busca
        novo — research.md #16), exibindo a categoria-pai automaticamente quando uma
        subcategoria é escolhida, resolvendo sempre para um único `categoria_id` enviado à
        API; ao digitar um nome sem correspondência e dar Enter, oferecer criar essa
        **subcategoria** ali mesmo, perguntando a categoria-pai dela — escolher uma pai já
        existente, ou digitar o nome de uma pai nova (cria os dois em sequência via
        `POST /categorias`, T012, já disponível desde a Fase 2) — e selecionando a
        subcategoria criada para o item em seguida (research.md #18); criar uma categoria de
        topo isolada, sem subcategoria, continua exclusivo de `/ver/categorias` (T050), não
        deste fluxo
  - [X] Link novo em `src/api/templates/base.html` (navegação)
- [X] T019 [P] [US1] Contract tests para os 3 endpoints acima em
      `tests/contract/test_api_contract.py`
- [X] T020 [P] [US1] Unit tests para `listar_itens_pendentes`, `atribuir_categoria_manual`,
      `classificar_grupo_pendente` em `tests/unit/test_classificacao_itens.py` — inclui caso
      de classificação parcial (só categoria); caso de atribuir a um item pendente via
      `atribuir_categoria_manual` resolvendo automaticamente os demais itens pendentes da
      mesma descrição, sem precisar de `classificar_grupo_pendente` (research.md #15); caso
      de `atribuir_categoria_manual` gravando o histórico corretamente (`metodo = 'manual'`,
      `categoria_id_anterior` real do item) — FR-014; e caso de
      `obter_evolucao_classificacao` retornando as duas séries corretamente ordenadas e
      cumulativas (research.md #22)

### Real-Data Validation for User Story 1 (MANDATORY — Constitution Principle V)

> Distinta dos testes automatizados acima — confirma que a cascata e a fila de pendentes
> sobrevivem ao contato com descrições reais, não só com dado sintético construído pelo
> autor.

- [X] T021 [US1] Validar com itens reais antes de promover esta história (dev → main) —
      rodado no Pi (dev) em 2026-07-17: 5 notas/41 itens reais, cascata ativada sobre o
      backlog (`classificar_itens_pendentes_da_nota` chamada para cada nota já existente,
      research.md #9), classificação manual real de um grupo (`BANANA NANICA KG`, 4
      ocorrências) confirmada resolvendo o grupo inteiro via API real
  - [X] Dimensão 1: descrições curtas/abreviadas de lojas diferentes (variação de formato
        entre emitentes, como no corpus real) — confirmado com descrições reais truncadas/
        abreviadas (`BATATA PALHA YOKI L105 P`, `PAO PANCO CASEIRO 500G M`, `DIPIRONA 500
        EMG 20ML`), todas agrupadas corretamente
  - [X] Dimensão 2: itens do backlog histórico (feature 004, importação em lote) vs. itens
        de nota importada individualmente (feature 001) — as 5 notas reais do Pi (dev) são
        todas `url_chave` (feature 001); não há nota real via importação em lote (feature
        004) nesse ambiente para comparar diretamente. Validado por revisão de código (T009:
        `classificar_itens_pendentes_da_nota` é chamada de forma idêntica pelos dois pontos
        de inserção) e por teste sintético local equivalente

### Visual Verification for User Story 1 (MANDATORY — Constitution Principle VIII)

- [X] T022 [US1] Integridade de asset de terceiro vendorizado: **N/A** — nenhum asset novo
      nesta feature (research.md #14)
- [X] T023 [US1] Captura de tela via navegador headless local de `/ver/pendentes` com pelo
      menos um grupo de itens pendentes visível **e o gráfico de evolução renderizado**
      (research.md #22), e checagem de zero erros de console JS

**Checkpoint**: todo item novo termina classificado ou pendente, e o usuário consegue
resolver qualquer pendente pela fila — valor central da feature já entregue (MVP).

---

## Phase 4: User Story 2 - Reaproveitar classificações já feitas (Priority: P1)

**Goal**: Item com descrição já classificada (cache) chega automaticamente classificado em
notas futuras; correção manual sobrescreve o cache; reprocessamento não duplica nem perde
classificação.

**Independent Test**: classificar manualmente um item, importar uma nova nota com item de
mesma descrição normalizada, e confirmar que já chega classificado sem ação do usuário.

### Implementation for User Story 2

> O mecanismo de cache (Tier 1) já foi construído na Fase 2 (T008, compartilhado por todas
> as histórias) — esta fase valida e fecha o comportamento ponta a ponta específico do
> reaproveitamento e da idempotência.

- [X] T024 [P] [US2] Integration test: classificar item manualmente numa nota, importar uma
      segunda nota com item de descrição igual (ou que normaliza igual), confirmar
      classificação automática sem passar pela fila de pendentes — `tests/integration/test_api.py`
- [X] T025 [P] [US2] Unit test de idempotência: chamar `classificar_itens_pendentes_da_nota`
      duas vezes seguidas para a mesma nota não duplica linhas em
      `historico_classificacao_item` nem altera classificações já existentes (FR-015) —
      `tests/unit/test_classificacao_itens.py`
- [X] T026 [US2] Unit test de precedência: corrigir manualmente um item já classificado por
      cache/regra sobrescreve a entrada de `cache_descricao_categoria`, e um item novo com a
      mesma descrição normalizada passa a receber a categoria corrigida (FR-012 cenário 2) —
      `tests/unit/test_classificacao_itens.py`

### Real-Data Validation for User Story 2 (MANDATORY — Constitution Principle V)

- [X] T027 [US2] Reimportar (reprocessar) pelo menos uma nota real já importada no Pi (dev)
      e confirmar que nenhuma classificação existente muda e nenhuma linha de histórico é
      duplicada antes de promover esta história (dev → main) — validado em 2026-07-17 com o
      banco de produção copiado para dev (nota real id=30, item classificado manualmente via
      API real, `classificar_itens_pendentes_da_nota` chamada de novo: categoria/método
      idênticos antes/depois, histórico permaneceu em 1 linha)

### Visual Verification for User Story 2 (MANDATORY — Constitution Principle VIII)

- [X] T028 [US2] Integridade de asset de terceiro vendorizado: **N/A**
- [X] T029 [US2] Captura de tela: **N/A** — nenhuma superfície visual nova nesta história
      (reaproveita `/ver/pendentes` da US1 sem mudança de layout)

**Checkpoint**: o esforço de classificação cai visivelmente ao reimportar itens repetidos —
mecanismo central de "flywheel" da feature comprovado.

---

## Phase 5: User Story 3 - Classificar automaticamente por regra pré-definida (Priority: P2)

**Goal**: Itens novos (sem cache) que casam uma regra-semente aprovada chegam classificados
sem passar pela fila, reduzindo o volume de pendentes desde o início do uso (cold-start).

**Independent Test**: com uma regra-semente ativa para um padrão, importar um item novo que
casa esse padrão pela primeira vez e confirmar que chega classificado sem passar pela fila.

### Implementation for User Story 3

- [X] T030 [US3] Curar o conteúdo definitivo das regras-semente a partir da taxonomia (T001)
      e do corpus real (T002) — pelo menos as regras de "papel higiênico" (143 das 327
      descrições do corpus via token `HIGIENICO`, research.md #13) e mais 10-15 padrões
      comuns de outras categorias — no arquivo de regras lido por
      `seed_taxonomia_categorizacao.py` (T007); completar o dicionário de abreviações de
      `normalizacao.py` (T006) com as abreviações que o corpus comprova serem comuns.
      17 regras curadas ao todo (`src/scripts/regras_semente_categorizacao.json`): papel
      higiênico (1), Pet/Petisco (`CANINO`/`CAES`, prioridade alta — vence sobre a regra
      genérica de biscoito), Alimentação/Matinais e doces (7 marcas/produtos: `BISCOITO`,
      `DUNGA`, `CHELKEN`, `MARILAN`, `KARINTO`, `CLUB SOCIAL`, `GOSTO DE AMOR`) e Higiene/Bucal
      (7: `BUCAL`, `LISTERINE`, `COLGATE`, `PLAX`, `DENTALCLEAN`, `SORRISO`, `ORAL-B`) —
      cobertura medida em 282/327 (86%) do corpus. Abreviação `HIGIE`→`HIGIENICO` adicionada
      (3 ocorrências reais); abreviação de "H" isolado (17 ocorrências em "PAPEL H ...")
      descartada por risco de falso positivo (token de uma letra só)
- [X] T031 [US3] Confirmar/ajustar em `classificacao_itens.py` (T008) o desempate
      determinístico de prioridade (maior `prioridade` vence; empate resolvido pelo menor
      `id` — research.md #6) — já implementado corretamente desde a Fase 2
      (`ORDER BY prioridade DESC, id ASC`), sem mudança necessária
- [X] T032 [P] [US3] Unit tests de prioridade de regra: duas regras casando o mesmo item,
      mais específica vence; caso de empate — `tests/unit/test_classificacao_itens.py`
- [X] T033 [P] [US3] Teste parametrizado da cascata contra as 327 descrições do corpus real
      (`tests/fixtures/corpus_descricoes_produtos.txt`), registrando quantas classificam via
      regra-semente vs. ficam pendentes — sem asserção de "100% classificado" (o corpus é
      enviesado para papel higiênico, não é amostra representativa — research.md #13) —
      `tests/unit/test_classificacao_itens.py`

### Real-Data Validation for User Story 3 (MANDATORY — Constitution Principle V)

- [X] T034 [US3] Rodar a cascata (regras-semente da T030) sobre o backlog real de itens já
      importados no Pi (dev) e revisar manualmente uma amostra do que foi classificado
      automaticamente por regra, confirmando que a categoria faz sentido — não só que o
      código não quebrou — antes de promover esta história (dev → main). Validado em
      2026-07-17: `seed_taxonomia_categorizacao` rodado no banco dev real (17 regras + taxonomia
      carregadas); reprocessamento do backlog (385 itens reais) não classificou nenhum item por
      regra — achado honesto: o corpus curado (papel higiênico/biscoito/bucal) não se sobrepõe
      ao mix de produtos deste backlog específico (hortifruti/farmácia/pet). Mecanismo
      confirmado correto via dois testes diretos: descrição sintética `BISCOITO MARILAN
      INTEGRAL 200G` classificou corretamente via regra; descrição real `TAPETES HIGIENICOS
      MR DRY` (tapete higiênico de pet) corretamente ficou pendente — o token `HIGIENICO` não
      bate com o plural `HIGIENICOS`, evitando um falso positivo real (classificar tapete de
      pet como papel higiênico)
  - [X] Dimensão 1: itens de lojas/emitentes diferentes casando a mesma regra — não há
        ocorrência real no backlog atual do Pi para demonstrar isso diretamente (achado acima);
        coberto indiretamente pela diversidade de formato do corpus real em T033 (327
        descrições de fontes variadas)
  - [X] Dimensão 2: taxa de "pendente" por nota antes vs. depois das regras-semente — sem
        mudança neste backlog específico (380/385 antes e depois), pelo motivo acima
  - **Achado adicional (fora do escopo de T034, reportado ao usuário)**: o seed da taxonomia
        criou uma categoria de topo nova "Alimentação › Padaria" que coexiste com uma
        categoria de topo "Padaria" pré-existente (id=4, já usada por 1 nota real,
        `VILLA GRANO`) — duplicata permitida pelo schema (níveis diferentes, sem violação de
        índice único), mas é uma decisão de dado real (mesclar, renomear ou manter as duas)
        que cabe ao usuário, não decidida aqui

### Visual Verification for User Story 3 (MANDATORY — Constitution Principle VIII)

- [X] T035 [US3] Integridade de asset de terceiro vendorizado: **N/A**
- [X] T036 [US3] Captura de tela: **N/A** — nenhuma superfície visual nova nesta história
      (classificação por regra é 100% backend, visível na fila de pendentes já coberta pela
      US1)

**Checkpoint**: cold-start mitigado — volume de itens caindo na fila de pendentes já
menor desde a primeira nota importada após o seed de regras.

---

## Phase 6: User Story 4 - Corrigir uma categoria atribuída incorretamente (Priority: P2)

**Goal**: Corrigir a categoria de um item já classificado, com opção explícita de corrigir a
fonte (cache) e reclassificar ocorrências passadas da mesma descrição, com prévia de
impacto antes de aplicar.

**Independent Test**: com um item classificado incorretamente (e outra ocorrência passada da
mesma descrição também errada), corrigir pedindo para também corrigir a fonte, confirmar a
prévia, aplicar, e verificar que a outra ocorrência foi atualizada.

### Implementation for User Story 4

- [ ] T037 [US4] `calcular_impacto_correcao_fonte(item_id, db_path)` em `src/storage/db.py`
      (data-model.md)
- [ ] T038 [US4] `corrigir_fonte_e_reclassificar(item_id, nova_categoria_id, db_path)` em
      `src/storage/db.py`: upsert do cache para a descrição normalizada do item + `UPDATE`
      em lote dos itens com mesma descrição e mesma categoria antiga + uma linha de
      histórico por item afetado (research.md #11, data-model.md)
- [ ] T039 [US4] `GET /itens/<id>/impacto-correcao-fonte` em `src/api/routes_itens.py`
- [ ] T040 [US4] `POST /itens/<id>/corrigir-fonte` em `src/api/routes_itens.py`
- [ ] T041 [US4] Estender `src/api/templates/nota_detalhe.html`: cada item da tabela ganha
      exibição da categoria/subcategoria atual (ou "pendente") e o mesmo campo de
      autocomplete único de T018, incluindo a criação inline de subcategoria nova (nunca
      categoria de topo isolada — research.md #16, #18) para corrigi-la via `PUT
      /itens/<id>/categoria` (T017, já existe); quando o item já tem
      `metodo_classificacao` em `cache`/`regra`, oferecer a ação separada e explícita
      "Corrigir a fonte e reclassificar o passado" que busca a prévia
      (`GET .../impacto-correcao-fonte`) antes de habilitar a confirmação (FR-013, SC-006)
- [ ] T042 [P] [US4] Contract tests para os 3 endpoints (`PUT categoria` já coberto em T019;
      `GET impacto-correcao-fonte`, `POST corrigir-fonte`) em
      `tests/contract/test_api_contract.py`
- [ ] T043 [P] [US4] Unit tests para `calcular_impacto_correcao_fonte` e
      `corrigir_fonte_e_reclassificar` — casos de zero itens afetados (só o próprio item) e
      de vários — `tests/unit/test_classificacao_itens.py`

### Real-Data Validation for User Story 4

- [X] T044 [US4] **N/A** — esta história opera sobre classificações já validadas pelas
      US1/US2/US3 (dado externo já normalizado antes de chegar aqui); não introduz um novo
      caminho de processamento de dado externo

### Visual Verification for User Story 4 (MANDATORY — Constitution Principle VIII)

- [X] T045 [US4] Integridade de asset de terceiro vendorizado: **N/A**
- [ ] T046 [US4] Captura de tela via navegador headless local de `nota_detalhe.html` com a
      edição de categoria por item e a prévia de "corrigir a fonte" visíveis, checagem de
      zero erros de console JS

**Checkpoint**: erro de classificação não se propaga indefinidamente — o usuário tem uma
saída clara e auditável para corrigi-lo, com ou sem efeito retroativo.

---

## Phase 7: User Story 5 - Gerenciar a taxonomia de categorias (Priority: P3)

**Goal**: Excluir categorias/subcategorias com prévia de impacto, destino explícito e
bloqueio por subcategoria; gerir a taxonomia numa tela dedicada (criação com `parent_id` e
quase-duplicata já disponíveis desde a Fase 2 — T011/T012).

**Independent Test**: criar uma subcategoria nova, renomeá-la, e excluí-la vendo a prévia de
impacto antes de confirmar.

### Implementation for User Story 5

- [ ] T047 [US5] `calcular_impacto_exclusao(categoria_id, db_path)` em `src/storage/db.py`
      (data-model.md) — inclui `tem_subcategorias`
- [ ] T048 [US5] `excluir_categoria_com_destino(categoria_id, destino,
      categoria_substituta_id, db_path)` em `src/storage/db.py`: bloqueia se
      `tem_subcategorias` (FR-017); com destino `"substituta"`, reatribui item/cache/regra
      (validando mesmo nível); com destino `"pendente"`, zera item e remove cache/regra
      associados; depois `DELETE FROM categoria` (research.md #12, data-model.md)
- [ ] T049 [US5] Atualizar `src/api/routes_categorias.py`: novo `GET
      /categorias/<id>/impacto-exclusao`; `DELETE /categorias/<id>` passa a exigir corpo com
      `destino` quando há referências em uso (contracts/api.md) — `parent_id`/quase-duplicata
      de `POST /categorias` já foram feitos em T012 (Fase 2), esta tarefa só cobre exclusão
- [ ] T050 [US5] Atualizar `src/api/templates/categorias.html`: exibição hierárquica
      (subcategorias aninhadas sob a categoria de topo), formulário de criar subcategoria
      (reaproveitando `POST /categorias` de T012, com aviso de quase-duplicata), e fluxo de
      exclusão que busca a prévia (`GET .../impacto-exclusao`) e — quando não bloqueado por
      subcategoria — pede o destino (substituta ou pendente) antes de confirmar
- [ ] T051 [P] [US5] Contract tests para os endpoints de exclusão em
      `tests/contract/test_api_contract.py`: impacto-exclusão, exclusão bloqueada por
      subcategoria, exclusão com destino substituta e com destino pendente (quase-duplicata
      e `parent_id` de criação já cobertos em T012)
- [ ] T052 [P] [US5] Unit tests em `tests/unit/test_categorias.py`: exclusão bloqueada por
      subcategoria, exclusão com destino substituta (nível igual exigido) e com destino
      pendente, e renomear uma categoria/subcategoria preserva `parent_id` e não gera nenhuma
      linha em `historico_classificacao_item` (FR-003) — quase-duplicata e rejeição de 3º
      nível já cobertos em T011

### Real-Data Validation for User Story 5

- [X] T053 [US5] **N/A** — gestão de taxonomia é entrada direta do próprio usuário (nome de
      categoria), não dado externo não controlado; Princípio V não se aplica

### Visual Verification for User Story 5 (MANDATORY — Constitution Principle VIII)

- [X] T054 [US5] Integridade de asset de terceiro vendorizado: **N/A**
- [ ] T055 [US5] Captura de tela via navegador headless local de `/ver/categorias` com a
      hierarquia categoria → subcategoria visível e o fluxo de exclusão com prévia/destino,
      checagem de zero erros de console JS

**Checkpoint**: todas as 5 histórias funcionam de forma independente; a taxonomia pode
evoluir sem exigir alteração direta no banco de dados.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Validação final cruzando todas as histórias.

- [ ] T056 Rodar a suíte completa (`pytest tests/unit tests/integration tests/contract -v`)
      e confirmar 100% passando — depende de T011, T012, T019, T020, T024, T025, T026, T032,
      T033, T042, T043, T051, T052
- [ ] T057 Validação completa do `quickstart.md` (§1-§8), consolidando as validações com
      amostra real (T021, T027, T034) e visuais (T023, T046, T055) já feitas
      individualmente por história, antes de promover dev → main
- [ ] T058 [P] Confirmar que o link de navegação para `/ver/pendentes` (T018) está visível
      em `src/api/templates/base.html` em todas as páginas, mesmo padrão dos links já
      existentes (`/ver/notas`, `/ver/categorias`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1)**: sem dependências — pode começar imediatamente. Habilita T007 e T030
  (dependem da taxonomia definitiva, T001) e T033 (depende do corpus copiado, T002)
- **Foundational (Fase 2)**: depende da Fase 1 (T007 depende de T001); T004/T005/T006 são
  `[P]` entre si (arquivos diferentes); T011 depende de T003, T012 depende de T011 — BLOQUEIA
  todas as 5 histórias. T011/T012 (suporte a `parent_id` + quase-duplicata em
  `POST /categorias`) são pré-requisito da criação inline de subcategoria em US1 (T018) e
  US4 (T041) — por isso entram aqui, não em US5, apesar de também servirem à tela de gestão
  de taxonomia (US5/T050)
- **User Story 1 (Fase 3)**: depende da Fase 2 completa (inclusive T011/T012, por causa da
  criação inline em T018) — nenhuma dependência de outra história
- **User Story 2 (Fase 4)**: depende da Fase 2 completa; reaproveita a fila de pendentes da
  US1 (T018) para o teste de integração ponta a ponta (T024), mas o mecanismo de cache em si
  já existe desde a Fase 2 — independentemente testável via API mesmo sem a UI da US1
- **User Story 3 (Fase 5)**: depende da Fase 2 completa; independente das outras 4
- **User Story 4 (Fase 6)**: depende da Fase 2 completa (inclusive T011/T012, por causa da
  criação inline em T041); a UI (T041) estende `nota_detalhe.html`, arquivo não tocado pelas
  outras histórias, mas reaproveita o endpoint de T017 (US1) — não é totalmente independente
  na prática, ainda que testável isoladamente via API
- **User Story 5 (Fase 7)**: depende da Fase 2 completa (T011/T012 já cobrem criação;
  esta fase só adiciona exclusão); independente das outras 4
- **Polish (Fase 8)**: depende de todas as histórias completas

### Parallel Opportunities

- T004, T005, T006 (Foundational) são `[P]` — arquivos diferentes. T011/T012 não são `[P]`
  com T003/T008 (todos tocam `src/storage/db.py`) — mantidos sequenciais para evitar
  conflito de edição no mesmo arquivo, mesmo padrão já usado para T007/T008/T009
- Uma vez a Fase 2 completa, as 5 histórias podem ser trabalhadas em paralelo (arquivos
  majoritariamente distintos: `routes_itens.py`+`pendentes.html` para US1/US2/US4 parcial;
  `nota_detalhe.html` só para US4; `routes_categorias.py`+`categorias.html` só para US5)
- T019/T020 (US1), T024/T025/T026 (US2), T032/T033 (US3), T042/T043 (US4), T051/T052 (US5)
  são testes `[P]` dentro de cada história

---

## Parallel Example: Foundational

```bash
# Lançar as três tarefas paralelas da Fase 2 (arquivos diferentes):
Task: "Atualizar src/models/categoria.py: campo parent_id"
Task: "Atualizar src/models/item_nota.py: categoria_id, descricao_normalizada, metodo_classificacao"
Task: "Criar src/services/normalizacao.py com normalizar_descricao()"
```

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Fase 1: Setup (taxonomia validada + corpus copiado)
2. Completar Fase 2: Foundational (schema + cascata + conexão com a importação + criação de
   categoria/subcategoria com `parent_id`)
3. Completar Fase 3: User Story 1 (fila de pendentes + classificação manual)
4. **PARAR e VALIDAR**: suíte + Real-Data Validation (T021) + Visual Verification (T023)
5. Deploy/demo em dev se pronto — já entrega o valor central (todo item termina classificado
   ou pendente, nunca indefinido)

### Incremental Delivery

1. Setup + Foundational → cascata pronta e conectada, criação de categoria/subcategoria já
   funcional (mesmo sem UI dedicada)
2. US1 → validar independentemente (real + visual) → deploy/demo (MVP)
3. US2 → validar independentemente → deploy/demo (reaproveitamento comprovado)
4. US3 → validar independentemente → deploy/demo (cold-start mitigado)
5. US4 → validar independentemente → deploy/demo (correção com prévia)
6. US5 → validar independentemente → deploy/demo (exclusão de taxonomia com prévia/destino)
7. Polish → suíte completa + quickstart completo → promover dev → main

---

## Notes

- [P] = arquivos diferentes, sem dependência
- Nenhuma tarefa desta feature altera a assinatura de `POST /notas`,
  `PUT /notas/<id>/categoria`, `GET /categorias` ou `PUT /categorias/<id>` — todos
  reaproveitados/estendidos sem quebrar contrato existente (contracts/api.md)
- A cascata de classificação (T008/T009) só atua sobre `item_nota.categoria_id IS NULL` —
  isso cobre de graça tanto o reprocessamento de nota (US2/FR-015) quanto o backlog
  histórico (research.md #9), sem tarefa de migração de dado separada
- Suporte a `parent_id`/quase-duplicata em `POST /categorias` (T011/T012) foi movido de US5
  para Foundational nesta revisão — é consumido por US1 (T018) e US4 (T041) desde o MVP, não
  só pela tela de gestão de taxonomia (US5/T050)
