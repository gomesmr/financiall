# Implementation Plan: Leitura de QR Code pela Câmera

**Branch**: `007-leitura-qrcode-camera` | **Date**: 2026-07-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-leitura-qrcode-camera/spec.md`

## Summary

Adiciona uma terceira opção de importação na página de Importar: ativar a
câmera do celular ali mesmo e decodificar o QR Code da nota fiscal ao vivo,
eliminando o passo manual de usar o app de câmera nativo e colar a URL. A
captura do vídeo é feita no navegador (`getUserMedia`); a decodificação
reaproveita o decodificador de QR Code já existente e testado no backend
(`src/services/qrcode_reader.py`, usado desde a feature 001 no pipeline de
foto/OCR) via um endpoint novo e enxuto — nenhuma biblioteca de terceiro é
vendorizada para isso. Como acesso à câmera exige contexto seguro (HTTPS) e
o financiALL hoje roda em HTTP puro no Raspberry Pi, esta feature também
inclui provisionar HTTPS local via proxy reverso (Caddy, certificado
autoassinado gerado automaticamente) na frente do `waitress`/Flask já
existentes, sem alterá-los.

## Technical Context

**Language/Version**: JavaScript vanilla no navegador (câmera, canvas,
`fetch`) + Python 3.11/Flask no backend (endpoint novo reaproveitando
serviço já existente) — mesma stack do projeto, sem linguagem nova.

**Primary Dependencies**: nenhuma dependência de frontend nova (sem
biblioteca JS de QR Code — research.md #1). Backend reaproveita `pyzbar`/
`Pillow`, já instalados desde a feature 001. Infraestrutura nova: Caddy
(proxy reverso HTTPS, instalado no Raspberry Pi como pacote/binário do
sistema, não vendorizado no repositório da aplicação — research.md #5/#8).

**Storage**: N/A — nenhuma mudança de schema ou dado.

**Testing**: `pytest` para o endpoint novo de decodificação de frame
(unidade/contrato, mesmo padrão dos endpoints já existentes). Verificação
visual real (captura headless + checagem de erro de console) para a UI de
câmera nova na página de Importar (Princípio VIII). Validação com amostra
real obrigatória antes de promover — QR Codes reais de notas fiscais,
capturados ao vivo pela câmera dos celulares reais da casa (Princípio V,
que cita "leitura de QR code" nominalmente — research.md #7).

**Target Platform**: navegador do celular (Android/iOS) acessando o
financiALL via HTTPS na rede local de casa, servido pelo mesmo Raspberry Pi
self-hosted já em produção.

**Project Type**: Web service single-project — mesma estrutura das
features anteriores, mais um componente novo de infraestrutura (proxy
reverso) documentado em `infra/`.

**Performance Goals**: irrelevante para uso pessoal, além de "parecer
responsivo" — captura e tentativa de decodificação a cada ~700ms enquanto a
leitura está ativa (research.md #4).

**Constraints**: acesso à câmera exige contexto seguro do navegador
(HTTPS) — restrição rígida da própria plataforma web, não uma escolha desta
feature. A aplicação MUST continuar funcionando por completo sem acesso à
internet (mesma restrição já aplicada às features 005/006) — o certificado
HTTPS MUST ser gerado localmente (Caddy `tls internal`), nunca depender de
uma autoridade certificadora pública online. Nenhuma mudança no endpoint de
importação por URL/chave já existente (`POST /notas`) — pedido explícito do
usuário na descrição original da feature.

**Scale/Scope**: 1 endpoint novo no backend (decodificação de frame), 1
opção nova de UI na página de Importar (`upload.html`), 1 componente novo
de infraestrutura no Raspberry Pi (proxy reverso HTTPS) cobrindo os dois
ambientes já existentes (produção porta 5000, dev porta 5005).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Simplicidade e Manutenibilidade**: PASS. Reaproveita o decodificador
  de QR Code já existente em vez de adicionar uma biblioteca de frontend
  nova (research.md #1) — mais simples que a alternativa óbvia, não menos.
  Uma exceção justificada (ver Complexity Tracking): o componente novo de
  infraestrutura (proxy HTTPS), necessário por uma restrição da própria
  plataforma web, não por escolha de design.
- **II. Idempotência é Obrigatória**: N/A — a importação em si continua
  pelo endpoint `POST /notas` já existente e inalterado, com a mesma
  garantia de idempotência de sempre; esta feature não grava nada nova.
- **III. Tratamento de Erro Explícito em Entradas Externas**: PASS — frame
  de câmera sem QR Code legível retorna `entrada: null` (estado normal, não
  erro); QR Code decodificado que não é uma URL/chave válida reaproveita a
  validação e mensagem de erro já existentes em `POST /notas` (FR-006);
  falha de câmera/permissão degrada graciosamente (FR-004).
- **IV. Dados Financeiros São Sensíveis**: PASS — o conteúdo do QR Code é a
  mesma URL pública da SEFAZ que o campo de texto já aceita hoje; nenhuma
  mudança em como dado sensível é tratado, mascarado ou logado.
- **V. Testável por Construção**: APLICA-SE DIRETAMENTE — "leitura de QR
  code" é citada nominalmente no texto do princípio. Validação com amostra
  real (QR Codes reais, capturados ao vivo) é obrigatória antes de
  promover, como barreira distinta dos testes automatizados sintéticos
  (research.md #7 identifica as dimensões de variação real relevantes).
- **VI. Português nos Artefatos Voltados ao Usuário**: PASS — todo texto de
  estado da câmera (buscando, erro, cancelar) e qualquer mensagem nova em
  português.
- **VII. Fontes Frágeis Degradam sem Quebrar o Fluxo Principal**: PASS —
  câmera indisponível/permissão negada é tratada como fonte frágil que
  degrada sem quebrar (FR-004/US2), mesmo espírito já aplicado a outras
  integrações frágeis do projeto.
- **VIII. Integridade Visual e de Assets de Terceiros**: APLICA-SE
  DIRETAMENTE — superfície visual nova (UI de câmera) exige verificação
  visual real (captura headless + checagem de erro de console) antes de
  promover. A cláusula de integridade de asset de terceiro vendorizado não
  se aplica a esta feature — nenhum asset de terceiro é vendorizado
  (research.md #8).

Uma exceção justificada ao Princípio I (ver Complexity Tracking) — as
demais seções passam sem ressalva.

## Project Structure

### Documentation (this feature)

```text
specs/007-leitura-qrcode-camera/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
src/api/
├── routes_importar.py         # existente — ganha o novo endpoint POST /notas/qrcode-frame
├── templates/
│   └── upload.html            # existente — ganha a terceira opção de importação (câmera)
└── static/
    └── (nenhum arquivo novo — sem asset de terceiro vendorizado, research.md #1/#8)

src/services/
└── qrcode_reader.py           # existente e inalterado — reaproveitado pelo novo endpoint

tests/
├── contract/
│   └── test_api_contract.py   # existente — ganha casos de contrato do novo endpoint
└── unit/
    └── (novo teste unitário do novo endpoint, se necessário além do contrato)

infra/
├── financiall.service         # existente, inalterado
├── financiall-dev.service     # existente, inalterado
├── Caddyfile                  # novo — configuração do proxy reverso HTTPS (research.md #5)
└── setup-raspberry-pi.sh      # existente — ganha o passo de instalar/configurar o Caddy
```

**Structure Decision**: projeto único (mesma estrutura das features
anteriores); o único endpoint novo entra em `routes_importar.py` (mesmo
arquivo dos outros endpoints de importação, por coerência); nenhum
diretório novo em `src/`. A única adição estrutural de fato é em `infra/`
(configuração do proxy reverso), acompanhando o padrão já existente de
versionar a configuração de implantação do Raspberry Pi.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Componente novo de infraestrutura no Raspberry Pi (proxy reverso HTTPS) | `getUserMedia()` (API de câmera do navegador) exige contexto seguro (HTTPS) — sem isso a função central desta feature nunca liga num celular real acessando pela rede local; é uma restrição da própria plataforma web, não uma escolha de design | Não fornecer HTTPS e aceitar que a feature só funcione em `localhost` — rejeitada porque o uso real é sempre pelo celular via wifi, nunca no navegador do próprio Pi; flag de navegador (`chrome://flags`) — rejeitada por só funcionar em Chromium e exigir configuração manual frágil por dispositivo (research.md #5) |
