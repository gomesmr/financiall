# Research: Importar fatura do cartão Mercado Pago

Investigação feita processando o arquivo real do usuário
(`assets/novos-extratos/mercado-pago-2026-06.pdf`, fatura de junho/2026)
com `pdfplumber` antes de escrever qualquer parser, seguindo o mesmo
espírito do Princípio V (validar contra amostra real antes de codificar a
suposição).

## #1 — Biblioteca de extração de texto do PDF

**Decision**: `pdfplumber` (`page.extract_text()`), nova dependência.

**Rationale**: a fatura é um PDF nativo com texto selecionável (não um
scan) — confirmado extraindo o texto e comparando com o conteúdo visual do
PDF. `extract_text()` devolve uma linha por lançamento, já na ordem visual
correta, sem exigir OCR. `pdf2image` + Tesseract (já usado no projeto para
QR code/nota fiscal) processaria a fatura como imagem, perdendo a
confiabilidade de um PDF nativo (falso positivo de erro de leitura em texto
que já é 100% extraível) e adicionando uma dependência de sistema
(poppler/tesseract) que essa rotina não precisa.

**Alternatives considered**:
- `pdftotext -layout` (CLI, poppler): mistura colunas em documentos com
  layout lado a lado (confirmado nesta mesma fatura — linhas de seções
  diferentes intercaladas incorretamente com `-layout`); sem `-layout` a
  ordem também não é garantida. `pdfplumber.extract_text()` já produz a
  ordem correta nesta fatura sem essa armadilha.
- `pdfplumber.extract_tables()`: retornou zero tabelas nas 6 páginas da
  fatura real — o PDF não usa bordas de tabela detectáveis. Não é uma
  opção viável para este formato.
- OCR (pipeline existente `pdf_extractor.py`): descartado por não ser
  necessário (texto já nativo) e por ser estritamente menos confiável que
  extração de texto direta para este tipo de documento.

## #2 — Estrutura da fatura e estratégia de parsing

**Decision**: concatenar o texto de todas as páginas e percorrer linha a
linha com uma máquina de estados simples baseada em cabeçalhos de seção,
em vez de tentar isolar por página (uma seção pode continuar na página
seguinte, como visto no cartão `[****3258]` da fatura real).

Cabeçalhos reconhecidos:
- `Movimentações na fatura` → entra na seção de encargos gerais da fatura
  (conta `MercadoPago`, sem cartão específico).
- `Cartão <bandeira> [************NNNN]` → entra na seção daquele cartão
  (conta `MercadoPago_NNNN`).
- `Data Movimentações Valor em R$` → cabeçalho de tabela, ignorado (não
  muda a seção atual).
- `Total R$ <valor>` ao final de cada seção de cartão → ignorado, não é
  lançamento.

Uma linha de lançamento só é aceita depois que uma seção reconhecida foi
vista (nunca antes) — degrada ignorando a linha, em vez de assumir uma
conta, se o layout mudar e nenhum cabeçalho for reconhecido antes de uma
linha de data (Princípio VII).

**Rationale**: validado contra a fatura real inteira — um regex ancorado
em início de linha (`^\d{2}/\d{2}\s`) capturado sobre o texto concatenado
das 6 páginas produziu exatamente as 25 linhas de lançamento esperadas,
sem nenhum falso positivo vindo de seções informativas (simulação de
parcelamento, texto de rodapé, datas soltas em outras seções).

**Alternatives considered**: parsear por página isoladamente — rejeitado
porque uma seção de cartão real continuou na página seguinte sem repetir
o cabeçalho `Cartão ... [****NNNN]`.

## #3 — Inferência do ano da transação

**Decision**: extrair `Emitida em: DD/MM/AAAA` do cabeçalho da fatura.
Para cada lançamento com mês `M`: se `M <= mês de emissão`, usar o ano de
emissão; se `M > mês de emissão`, usar `ano de emissão - 1`.

**Rationale**: a fatura real de junho/2026 traz parcelas com data original
de março, abril e maio do mesmo ano (compras parceladas cujas parcelas
seguintes aparecem em faturas posteriores com a data original da compra,
não a data de fechamento) — todas com mês ≤ mês de emissão, então caem no
ano corrente sem ambiguidade. A regra do "mês maior que o de emissão"
cobre o caso geral (não presente nesta amostra, mas inevitável em uso
contínuo): uma fatura fechada em janeiro trazendo uma parcela cuja compra
original foi em dezembro do ano anterior.

**Alternatives considered**: assumir sempre o ano de emissão — rejeitado
por quebrar silenciosamente no caso de virada de ano (dezembro→janeiro),
que é inevitável numa importação recorrente mês a mês (US2).

## #4 — Preservar "Parcela X de Y" na descrição (achado crítico)

**Decision**: manter o texto "Parcela X de Y" concatenado à descrição do
lançamento (ex.: `"CLARICELL Parcela 14 de 21"`), em vez de descartá-lo.

**Rationale**: o fingerprint de deduplicação (`calcular_fingerprint`) é
`sha1(data | descrição_normalizada | valor_absoluto | conta)` — **não**
inclui o número da parcela. A data de uma parcela é a data original da
compra, que **não muda** entre faturas mensais consecutivas (confirmado no
dado real: `CLARICELL` aparece com a mesma data `11/05` e mesmo valor
`R$ 166,66` na "Parcela 14 de 21"; a próxima fatura trará a mesma data e
provavelmente o mesmo valor, só mudando para "Parcela 15 de 21"). Se a
descrição não incluir o número da parcela, a parcela 15 teria data,
descrição, valor e conta idênticos à parcela 14 já importada — fingerprint
igual, e o pipeline (`processar_transacoes`) trataria a parcela nova como
"já existente", **descartando um gasto real silenciosamente**. Isso viola
diretamente o Princípio II (idempotência não pode virar perda de dado) e o
FR-007/User Story 2 desta feature.

Incluir o número da parcela no texto resolve isso sem introduzir nenhum
mecanismo novo — muda só o hash, que já é a chave de deduplicação
pretendida.

**Efeito colateral aceito**: o cache de classificação (Tier 1,
correspondência exata por `descricao_normalizada`) não vai bater de uma
parcela para a próxima (o texto muda). A classificação ainda funciona via
regra (Tier 2, correspondência por substring com fronteira de palavra à
esquerda — "CLARICELL" continua batendo mesmo com o sufixo de parcela
depois). Custo aceito: perde-se o hit de cache entre parcelas da mesma
compra, mas nunca a classificação em si (quando há regra) nem a
integridade do dado (Princípio I — não vale complicar o parser para
recuperar um hit de cache que a Tier 2 já resolve de graça).

**Nota**: o parser de fatura Itaú `.xlsx` existente (`_parsear_fatura_paga_xlsx`)
descarta a coluna de parcelamento hoje — mesma exposição, fora do escopo
desta feature corrigir; documentado aqui apenas para não repetir o mesmo
padrão no parser novo.

## #5 — Conta canônica por cartão e conta genérica para encargos

**Decision**: cada seção `Cartão ... [****NNNN]` vira uma conta
`MercadoPago_NNNN` → canônico `mercado_pago_NNNN` (mesmo espírito de
`Itaú_NNNN` → `itau_NNNN`, incluindo um regex genérico para cartões
futuros). A seção `Movimentações na fatura` (juros, multa, IOF, pagamento
da fatura) vira uma conta fixa `MercadoPago` → canônico `mercado_pago`,
sem número de cartão — esses encargos são cobrados no nível da fatura, não
atribuíveis a um cartão específico.

**Rationale**: replica a distinção já existente entre `itau_2486` (cartão)
e `itau_cc` (conta corrente) — contas conceitualmente diferentes sob a
mesma instituição não podem compartilhar um rótulo, sob risco de misturar
o consumo de titulares/cartões diferentes (ex.: os dois cartões Visa desta
fatura têm padrões de consumo claramente distintos — corridas de app vs.
compras parceladas de terceiros).

## #6 — Convenção de sinal para as novas contas Mercado Pago

**Decision**: estender `_eh_conta_cartao()` (em
`importar_historico_extrato.py`) para reconhecer qualquer conta canônica
que comece com `mercado_pago` (com ou sem sufixo de número) como
cartão de crédito — positivo = saída (compra/encargo), negativo = entrada
(estorno/crédito).

**Rationale**: sem essa mudança, a conta genérica `mercado_pago`
(encargos) cairia no `else` de `_interpretar_valor_e_tipo` (convenção de
conta corrente: positivo = entrada), classificando juros e multa como
renda — o oposto do correto. Estender o predicado existente é a mudança
mínima (Princípio I); nenhuma conta Mercado Pago tem hoje o papel de
"conta corrente" (não há essa fonte para o Mercado Pago no projeto), então
não há necessidade do sufixo `_cc` de exclusão que o Itaú usa.

## #7 — Filtro do lançamento de pagamento da fatura anterior

**Decision**: na seção `Movimentações na fatura`, descartar qualquer linha
cuja descrição contenha "pagamento da fatura" (case-insensitive) — mesma
razão e mesmo padrão do filtro `"pagamento efetuado"` já usado no parser
de fatura Itaú.

**Rationale**: esse valor (ex.: "Pagamento da fatura de junho/2026",
R$ 1.822,04) já é contabilizado do lado da conta corrente/PIX que pagou a
fatura anterior. Importar de novo aqui duplicaria o gasto (mesmo dinheiro,
contado nas duas pontas).

## #8 — Vocabulário novo de encargos para o seed de regras de natureza

**Decision**: adicionar ao seed de regras de natureza (`regras_semente_natureza.json`)
os padrões `JUROS DE MORA`, `MULTA POR ATRASO`, `JUROS DO ROTATIVO`,
`IOF DO ROTATIVO` → `natureza: gasto`, `categoria: Finanças`,
`subcategoria: Tarifas e juros` — mesma categoria/subcategoria já usada
para os encargos equivalentes do rotativo do BB (feature 011).

**Rationale**: sem essas regras, todo mês esses 4 lançamentos (que se
repetem sempre que há rotativo/atraso) cairiam em pendente de revisão
manual, apesar de já existir uma categoria e um padrão de nomenclatura
estabelecidos para o mesmo tipo de encargo em outra fonte (BB). Verificado
que nenhuma regra existente (`JUROS SALDO DEVEDOR`, `IOF SALDO DEVEDOR`,
específicas do vocabulário do BB) bate com o texto usado pelo Mercado
Pago — são literais diferentes, exigem entradas novas.

**Risco verificado e descartado**: existe uma regra já ativa
(`"MERCADO PAG"` → `pagamento_fatura`, prioridade 90) usada para
reconhecer o pagamento da fatura do Mercado Pago quando ele aparece do
lado do extrato bancário (PIX/débito). Confirmado que nenhuma descrição
real desta fatura (`MERCADOLIVRE*MERCADOLIVRE`, `DL*99 RIDE`, `CLARICELL`,
etc.) contém a substring `"MERCADO PAG"` — não há colisão com essa regra.

## #10 — Achado da validação com dado real: lançamentos idênticos no mesmo dia (Princípio V em ação)

**Decision**: contar ocorrências de `(conta, data, descrição, valor)` dentro
do próprio parsing; a partir da segunda ocorrência idêntica, acrescentar
um sufixo `" #N"` à descrição antes de gerar o registro.

**Rationale**: rodando a importação contra o arquivo real de junho/2026
(validação obrigatória do Princípio V), a primeira execução importou só
22 das 25 transações reais — 3 pares de "DL*99 RIDE" (corridas de app
distintas, no mesmo dia, com o mesmo valor arredondado) colidiram no
fingerprint (mesma data, descrição e valor) e a segunda ocorrência de cada
par foi silenciosamente tratada como "já existente", descartando um gasto
real. Mesma classe de risco do achado #4 (parcela), resolvida com a mesma
técnica (diferenciar via texto da descrição, sem tocar no esquema de
fingerprint). Depois da correção, a mesma fatura real importa exatamente
as 25 transações esperadas, e reimportar o mesmo arquivo confirma
idempotência (0 novas, 25 já existentes).

**Nota**: esse é um risco genérico do esquema de fingerprint do projeto
(dois eventos genuinamente diferentes com data/descrição/valor/conta
coincidentes colidem, em qualquer fonte, não só Mercado Pago) — a correção
aqui é local ao parser desta feature; não foi generalizada para os
parsers Itaú/BB existentes, por estar fora do escopo desta feature.

## #11 — Achado da validação com dado real: falso positivo de classificação pré-existente

**Observação, sem mudança de código**: uma transação real desta fatura
(`RecargaPay *CRISTINEV`, recarga de celular) foi classificada como
`transferencia_interna` pela regra legada `"CRISTINE"` (prioridade 88,
`_evidencia: "REGRAS legado - Transferencia Cristine"`, já existente antes
desta feature) — a regra bate por substring com fronteira de palavra à
esquerda, e `"CRISTINEV"` contém `"CRISTINE"` logo após o `*` (fronteira
de palavra real). Essa regra foi criada para reconhecer transferência de
dinheiro para a Cristine (ex.: "PIX TRANSF CRISTINE"), não para reconhecer
o nome dela dentro do descritor de um serviço de terceiro. **Fora do
escopo desta feature corrigir** (a regra é pré-existente, usada por outras
fontes, e alterá-la exige avaliar efeito colateral nelas) — a transação
cai numa classificação levemente incorreta em vez de pendente, mas
continua visível e corrigível manualmente em `/ver/transacoes`, mesmo
caminho já disponível para qualquer classificação automática errada.

## #9 — Nova dependência

**Decision**: adicionar `pdfplumber` a `pyproject.toml` (`[project.dependencies]`).

**Rationale**: única biblioteca nova necessária; leve, puramente Python
(usa `pypdfium2` internamente, sem exigir poppler/Ghostscript instalado à
parte, diferente de `pdf2image`).
