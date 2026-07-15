# Data Model: Gráficos no Resumo de Gastos

Nenhuma tabela ou coluna nova — esta feature adiciona uma agregação nova
sobre `nota_fiscal`/`categoria` (já existentes) e uma forma nova de
exibir dado que `resumo.py` já sabe calcular (histórico mensal).

## Agregação nova: `gasto_por_categoria`

```python
@dataclass(frozen=True)
class GastoCategoria:
    categoria_id: int | None   # None = "sem categoria"
    nome: str                  # nome da categoria, ou "Sem categoria"
    total_gasto: int           # centavos

def gasto_por_categoria(mes: str, db_path: str = ...) -> list[GastoCategoria]:
    ...
```

**Consulta** (conceitual):

```sql
SELECT
    categoria.id AS categoria_id,
    COALESCE(categoria.nome, 'Sem categoria') AS nome,
    SUM(nota_fiscal.valor_total) AS total_gasto
FROM nota_fiscal
LEFT JOIN categoria ON categoria.id = nota_fiscal.categoria_id
WHERE <mesmo filtro de mês já usado em listar_notas/resumo>
  AND nota_fiscal.valor_total IS NOT NULL
GROUP BY categoria.id
ORDER BY total_gasto DESC
```

**Regras** (FR-002, FR-006):

- Notas sem `categoria_id` (`NULL`) agrupam sob `categoria_id = None`,
  nome `"Sem categoria"` — nunca excluídas do resultado.
- Notas com `valor_total IS NULL` (dados incompletos, pendente de
  revisão) não entram na soma — mesma regra já aplicada por
  `_query_resumo_por_mes` no resumo em texto atual, garantindo que a
  soma das fatias bate com o total já exibido (FR-006/SC-003).
- Resultado ordenado do maior para o menor gasto (facilita tanto a
  legenda quanto a decisão de dobrar a cauda em "Outros" no frontend).

## Atribuição de cor (calculada no frontend, não persistida)

Não há coluna de cor no banco — cor não é dado, é apresentação
(research.md #4). O template recebe `categoria_id` e calcula
`slot = categoria_id % 8` em JS para escolher a cor entre as 8 da paleta
categórica de referência; `categoria_id is None` (Sem categoria) e a
cauda dobrada em "Outros" (mais de 8 categorias com gasto no mês) usam
o tom neutro fixo, nunca um slot categórico.

## Reaproveitado sem alteração

- `ResumoMes` / `historico_meses_anteriores()` / `gasto_mes_corrente()`
  (já existentes) — fonte de dados do gráfico de barras e dos números em
  texto já exibidos.
- `listar_categorias()` (feature 003) — usada para popular o seletor de
  mês não precisa dela diretamente, mas a legenda da pizza usa os nomes
  já resolvidos pela própria consulta de `gasto_por_categoria`.

## Estados

Não há estado novo — é uma visão derivada, recalculada a cada request, sem
persistência própria.
