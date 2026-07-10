# Research: Importar NFC-e sem Duplicar

## 1. Linguagem e stack

**Decision**: Python 3.11+, `requests` para HTTP, stdlib (`xml.etree` /
`html.parser`) para parsing, `click` (ou `argparse`) para CLI, `pytest` para
testes, SQLite como armazenamento.

**Rationale**: projeto pessoal, mantido por uma pessoa (Princípio I). Python
tem stdlib forte para HTTP/HTML/XML e SQLite embutido (`sqlite3`), evitando
qualquer dependência de infraestrutura (servidor de banco, containers).
`pytest` é o padrão de fato para testabilidade por construção (Princípio V).

**Alternatives considered**: Node.js/TypeScript (rejeitado — parsing de
HTML/XML de portais SEFAZ é mais direto com libs Python maduras; equipe de
uma pessoa não precisa de dois runtimes); banco Postgres (rejeitado —
servidor separado é complexidade desnecessária para uso de uma pessoa,
viola Princípio I).

## 2. Interface de entrega (CLI vs web)

**Decision**: CLI fina sobre uma biblioteca de domínio isolada
(`src/services/`, `src/models/`).

**Rationale**: a especificação não exige UI; CLI é a interface mais simples
que satisfaz todos os FRs (importar, listar, resumo mensal). Isolar a
lógica de domínio da CLI garante que uma futura interface (web, por
exemplo, quando o financiALL crescer para reconciliação com extrato) reuse
o mesmo código sem reescrita — alinhado à Identidade do Projeto (base
única, "ALL").

**Alternatives considered**: web app com API (rejeitado para esta feature —
complexidade prematura sem requisito explícito; pode ser adicionado depois
como uma nova camada fina sobre a mesma biblioteca).

## 3. Extração da chave de acesso a partir da URL do QR Code

**Decision**: não assumir um nome fixo de parâmetro de query (ex.: `p=` ou
`chNFe=`) nem um domínio fixo, pois cada UF usa seu próprio portal SEFAZ com
formato de URL próprio. Em vez disso: (a) fazer parse da query string da
URL: (b) para cada valor de parâmetro, procurar uma sequência de 44 dígitos
consecutivos (o valor do parâmetro costuma ser a chave sozinha, ou a chave
seguida de outros campos separados por `|`, ex. `chave|versao|tpAmb|...`);
(c) usar a primeira sequência de 44 dígitos encontrada que passe na
validação do dígito verificador (item 4) como a chave extraída.

**Rationale**: o padrão nacional de QR Code de NFC-e varia o nome do
parâmetro e o domínio por UF, mas sempre inclui a chave de 44 dígitos como
prefixo de um dos valores de query. Uma extração por busca de padrão
numérico (em vez de nome de parâmetro fixo) é mais simples e resiliente a
variação entre UFs (Princípio I e VII), sem exigir uma tabela de mapeamento
por estado.

**Alternatives considered**: manter uma tabela de formatos de URL por UF
(rejeitado — complexidade de manutenção alta para um projeto pessoal,
frágil a mudanças dos portais; viola Princípio I).

## 4. Validação do dígito verificador da chave de acesso (44 dígitos)

**Decision**: implementar o algoritmo padrão (módulo 11) do modelo nacional
de NF-e/NFC-e: os primeiros 43 dígitos são ponderados da direita para a
esquerda com pesos cíclicos 2,3,4,5,6,7,8,9 (repetindo); soma-se
`dígito × peso`; calcula-se `resto = soma % 11`; o dígito verificador (44º
dígito) é `0` se `resto` for `0` ou `1`, senão `11 - resto`. A validação
compara o 44º dígito da chave com o valor calculado.

**Rationale**: é o algoritmo público e estável usado por todos os portais
SEFAZ e pela Receita Federal para o modelo nacional de NF-e/NFC-e; permite
validar uma chave colada manualmente sem depender de rede (Princípio VII —
mais uma verificação que não depende de fonte frágil).

**Alternatives considered**: só validar comprimento (44 dígitos), sem
dígito verificador (rejeitado — deixaria passar erros de digitação/cópia
que só apareceriam depois, na consulta à SEFAZ; o dígito verificador é
grátis para computar e detecta esse erro imediatamente, cumprindo melhor o
Princípio III de tratamento explícito de entrada externa).

## 5. Dados extraíveis da própria chave, sem depender da fonte frágil

**Decision**: além de validar o dígito verificador, decodificar da própria
chave de 44 dígitos os campos que o modelo nacional já embute
posicionalmente: UF (2 primeiros dígitos, tabela IBGE), ano/mês de emissão
(dígitos 3–6), CNPJ do emitente (dígitos 7–20), modelo do documento
(dígitos 21–22, deve ser `65` para NFC-e), série (dígitos 23–25) e número
da nota (dígitos 26–34). Esses campos MUST ser preenchidos a partir da
chave imediatamente, independentemente do sucesso da consulta à fonte de
detalhamento.

**Rationale**: reduz a superfície do que é realmente "best-effort" (US3):
somente nome do emitente (razão social), dia exato de emissão, valor total
e itens dependem da consulta à SEFAZ; UF, CNPJ, ano-mês e identificação do
documento ficam garantidos mesmo se a fonte estiver fora do ar — reforça o
Princípio VII (degradar graciosamente) com o mínimo de esforço adicional,
já que a decodificação é determinística e local.

**Alternatives considered**: tratar todos os campos (incluindo UF e CNPJ)
como dependentes da consulta externa (rejeitado — desnecessariamente
frágil, quando a chave já garante esses dados sem custo de rede).

## 6. Chamada à fonte de detalhamento (best-effort)

**Decision**: uma única tentativa HTTP com timeout curto (poucos segundos)
por importação, **somente quando `modelo = 65` (NFC-e)** — o fluxo de
extração/consulta pesquisado neste documento (item 3) cobre exclusivamente
os portais de NFC-e por UF. Para chave com `modelo` diferente de `65` (ex.:
`55`, NF-e), a busca de detalhes não é tentada nesta feature: a nota é
gravada só com os campos decodificados da própria chave e permanece
"pendente de revisão" (consulta ao portal de NF-e fica para feature futura).
Qualquer falha na tentativa (timeout, erro HTTP, corpo inesperado) é
capturada explicitamente e resulta em status "pendente de revisão", nunca
em exceção não tratada.

**Rationale**: atende ao Princípio VII (fontes frágeis não podem quebrar o
fluxo principal) e ao Princípio III (tratamento de erro explícito).
Retries/backoff automáticos são complexidade desnecessária para uso pessoal
(usuário pode simplesmente tentar importar de novo mais tarde; como a nota
já foi gravada com status "pendente de revisão", uma nova tentativa não
duplica — reaproveita a checagem de idempotência para, opcionalmente,
completar os dados que faltaram).

**Alternatives considered**: fila de retries com backoff exponencial
(rejeitado — complexidade desproporcional ao volume de uso pessoal; viola
Princípio I).

## 7. Log seguro (sem dados sensíveis em texto claro)

**Decision**: logging estruturado da aplicação nunca inclui chave de
acesso, CNPJ, CPF ou valores monetários em texto claro; quando necessário
referenciar uma nota em log, usa-se um identificador interno (ex.: `id`
autoincremento da base) ou os últimos 4 dígitos da chave, nunca a chave
completa.

**Rationale**: cumpre o Princípio IV diretamente; identificador interno é
suficiente para depuração sem expor dado sensível.

**Alternatives considered**: mascarar a chave inteira com hash reversível
em log (rejeitado — complexidade desnecessária; o `id` interno já resolve o
problema de correlação para depuração).

## Status

Todos os pontos de NEEDS CLARIFICATION do Technical Context foram
resolvidos acima. Nenhum item pendente para a Fase 1.
