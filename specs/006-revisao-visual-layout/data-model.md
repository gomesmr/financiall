# Data Model: Revisão Visual do Layout

Não se aplica — feature puramente de apresentação (spec.md → Key
Entities: "Nenhuma"). Nenhuma tabela, coluna, model Python ou contrato de
dado muda. O que muda é só a camada de `templates/`/`static/` sobre os
dados que a aplicação já expõe.

## Mapeamento página existente → estrutura visual Argon

Referência para a fase de implementação — qual componente do Argon cada
template já existente passa a usar, sem mudar os dados que cada um
recebe do backend (as mesmas variáveis Jinja continuam sendo passadas
pelas mesmas rotas, inalteradas por esta feature):

| Template existente | Dados recebidos (inalterados) | Estrutura Argon equivalente |
|---|---|---|
| `upload.html` | — (formulário, sem dado de entrada) | Card de formulário |
| `notas.html` | `notas`, `categorias_por_id`, `titular_filtro` | Card com tabela estilizada + badges de status |
| `nota_detalhe.html` | `nota`, `itens`, `categorias` | Card de detalhe + tabela de itens |
| `categorias.html` | `categorias` | Card com tabela + formulário inline |
| `resumo.html` | `mes_corrente`, `historico`, `historico_json`, `meses_disponiveis` | Cards de estatística (mês corrente) + cards contendo os gráficos Plotly já existentes (feature 005) |
| `envio.html` | `envio`, `nota`, `itens` | Card de status simples |

## Estados

Não se aplica — nenhuma entidade nova, nenhuma transição de estado.
