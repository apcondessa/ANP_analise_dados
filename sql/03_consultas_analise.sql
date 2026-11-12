-- =============================================================================
-- 03_consultas_analise.sql
-- As análises do projeto escritas em SQL, sobre anp.preco_combustivel.
-- Cada consulta equivale a uma função de src/analysis.py (mesmo nome) e os
-- testes conferem que as duas dão o mesmo resultado.
--
-- As linhas "-- nome: ..." identificam cada consulta para os testes.
-- Para escolher o ano nas consultas que usam :ano, rode no psql com:
--   psql -v ano=2025 -f sql/03_consultas_analise.sql
-- =============================================================================

-- nome: estatistica_por_produto
-- Preço mínimo, máximo e médio por produto e ano.
SELECT
    produto,
    ano,
    round(min(valor_venda), 2)  AS min,
    round(max(valor_venda), 2)  AS max,
    round(avg(valor_venda), 2)  AS media
FROM anp.preco_combustivel
GROUP BY produto, ano
ORDER BY produto, ano;

-- nome: estatistica_por_estado
-- Preço mínimo, máximo e médio por produto, ano e estado.
SELECT
    produto,
    ano,
    estado,
    round(min(valor_venda), 2)  AS min,
    round(max(valor_venda), 2)  AS max,
    round(avg(valor_venda), 2)  AS media
FROM anp.preco_combustivel
GROUP BY produto, ano, estado
ORDER BY produto, ano, estado;

-- nome: bandeiras_por_estado
-- Quantidade de bandeiras (distribuidoras) diferentes em cada estado.
SELECT
    estado,
    count(DISTINCT bandeira) AS quantidade_bandeiras
FROM anp.preco_combustivel
WHERE bandeira IS NOT NULL
GROUP BY estado
ORDER BY quantidade_bandeiras DESC, estado;

-- nome: variacao_anual
-- Preço médio por produto e ano e a variação (%) em relação ao ano anterior.
-- LAG busca a média do ano anterior do mesmo produto.
WITH medias AS (
    SELECT produto, ano, avg(valor_venda) AS media
    FROM anp.preco_combustivel
    GROUP BY produto, ano
)
SELECT
    produto,
    ano,
    round(media, 2) AS media,
    round(
        (media / LAG(media) OVER (PARTITION BY produto ORDER BY ano) - 1) * 100, 1
    ) AS variacao_pct
FROM medias
ORDER BY produto, ano;

-- nome: media_por_regiao
-- Preço médio por região e produto no ano escolhido (:ano).
SELECT
    regiao,
    produto,
    round(avg(valor_venda), 2) AS media
FROM anp.preco_combustivel
WHERE ano = :ano
GROUP BY regiao, produto
ORDER BY regiao, produto;

-- nome: razao_etanol_gasolina
-- Preço médio do etanol dividido pelo da gasolina comum em cada estado, no ano
-- escolhido (:ano). O etanol compensa quando a razão fica abaixo de 70%.
WITH medias AS (
    SELECT
        estado,
        avg(valor_venda) FILTER (WHERE produto = 'ETANOL')   AS etanol,
        avg(valor_venda) FILTER (WHERE produto = 'GASOLINA') AS gasolina
    FROM anp.preco_combustivel
    WHERE ano = :ano
      AND produto IN ('ETANOL', 'GASOLINA')
    GROUP BY estado
)
SELECT
    estado,
    round(etanol, 2)               AS etanol,
    round(gasolina, 2)             AS gasolina,
    round(etanol / gasolina, 3)    AS razao,
    etanol / gasolina < 0.70       AS compensa_etanol
FROM medias
WHERE etanol IS NOT NULL
  AND gasolina IS NOT NULL
ORDER BY razao, estado;

-- nome: precos_medios_mensais
-- Preço médio por produto e mês (base do gráfico de evolução de preços).
SELECT
    produto,
    date_trunc('month', data_coleta)::date AS mes,
    round(avg(valor_venda), 2)             AS media,
    count(*)                               AS coletas
FROM anp.preco_combustivel
GROUP BY produto, date_trunc('month', data_coleta)
ORDER BY produto, mes;
