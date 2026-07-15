# Quickstart: Validar "Leitura de QR Code pela Câmera"

Pré-requisitos: ambiente já configurado como nas features anteriores, mais
o proxy reverso HTTPS (Caddy) provisionado no Raspberry Pi (research.md #5)
— sem isso, a leitura por câmera não liga em nenhum celular real, só o
resto da página continua funcionando (US2).

## 1. Rodar os testes automatizados (rede de segurança de regressão)

```bash
pytest tests/unit tests/integration tests/contract -v
```

Espera-se cobertura nova para o endpoint `POST /notas/qrcode-frame`
(ver contracts/api.md); o restante da suíte (incluindo `POST /notas`
inalterado) continua passando 100%.

## 2. Verificação visual real (Princípio VIII)

1. Capturar uma tela da página de Importar (navegador headless local) com
   a nova opção de leitura por câmera visível, junto das duas já
   existentes, sem sobreposição ou quebra de layout.
2. Checar ausência de erro de console JS na mesma execução.

## 3. Validação funcional na rede local (celular real)

1. No celular, acessar `https://finall.local:<porta-https>` (produção) ou
   a porta equivalente de dev — confirmar que o navegador aceita prosseguir
   mesmo com aviso de certificado autoassinado (research.md #5).
2. Na página de Importar, ativar a leitura por câmera.
3. Apontar para um QR Code real de nota fiscal (SC-001) — confirmar que a
   nota é importada com o mesmo resultado de colar a mesma URL manualmente.
4. Repetir apontando para algo que não é um QR Code de nota fiscal válido
   — confirmar a mesma mensagem de erro que já existe hoje para entrada de
   texto inválida (FR-006).
5. Cancelar uma leitura em andamento e confirmar que as outras duas opções
   de importação continuam disponíveis sem recarregar a página (SC-004).

## 4. Degradação graciosa sem câmera disponível (US2)

1. Negar a permissão de câmera quando o navegador solicitar (ou testar num
   navegador/contexto sem suporte).
2. Confirmar que a opção de câmera fica claramente indisponível — nenhum
   botão quebrado — e que importar por URL/chave e por foto/PDF continuam
   funcionando exatamente como antes (SC-002).

## 5. Validação com amostra real (Princípio V — distinta dos testes acima)

Antes de promover para produção: escanear ao vivo pelo menos um QR Code
real por dimensão de variação identificada em research.md #7 — captura em
ângulo/distância variável, o frame comprimido gerado pelo navegador (não um
arquivo de foto original), e pelo menos os dois celulares reais da casa —
confirmando que a nota resultante bate com a mesma nota que o método de
colar a URL manualmente já produz para o mesmo QR Code.

## 6. Funciona sem internet

1. Desconectar o Raspberry Pi da internet.
2. Confirmar que o certificado HTTPS continua válido (gerado localmente
   pelo Caddy, sem depender de uma autoridade certificadora online) e que
   a leitura por câmera continua funcionando por completo.

## Critério de aceite (liga com Success Criteria da spec)

- SC-001: importar apontando a câmera, sem copiar/colar.
- SC-002: câmera indisponível não quebra as opções já existentes.
- SC-003: 100% dos QR Codes válidos e legíveis resultam na mesma importação
  do método manual.
- SC-004: cancelar a leitura sem recarregar a página.
- SC-005: financiALL acessível pelo celular por um endereço que o
  navegador reconhece como seguro o suficiente para liberar a câmera.
