-- =============================================================================
-- 02_transformar.sql
-- Trata os dados da staging e grava na tabela final anp.preco_combustivel.
-- Aplica as mesmas regras de src/data_processing.py:
--   - datas dd/mm/aaaa e valores com vírgula convertidos;
--   - produto e estado sem espaços e em maiúsculas; bandeira sem espaços;
--   - unidade do GNV padronizada ("R$ / m3" -> "R$ / m³");
--   - descarte de linhas sem data, produto ou valor de venda
--     (inclui as linhas totalmente vazias do final de alguns arquivos);
--   - remoção de registros duplicados.
--
-- A tabela final é esvaziada e recarregada a cada execução.
-- =============================================================================

BEGIN;

TRUNCATE anp.preco_combustivel RESTART IDENTITY;

INSERT INTO anp.preco_combustivel (
    data_coleta, regiao, estado, municipio, cnpj, bandeira, produto, valor_venda, unidade
)
SELECT DISTINCT
    data_coleta, regiao, estado, municipio, cnpj, bandeira, produto, valor_venda, unidade
FROM (
    SELECT
        anp.para_data(data_coleta)                          AS data_coleta,
        NULLIF(upper(btrim(regiao_sigla)), '')              AS regiao,
        NULLIF(upper(btrim(estado_sigla)), '')              AS estado,
        NULLIF(btrim(municipio), '')                        AS municipio,
        NULLIF(btrim(cnpj_revenda), '')                     AS cnpj,
        NULLIF(btrim(bandeira), '')                         AS bandeira,
        NULLIF(upper(btrim(produto)), '')                   AS produto,
        anp.para_numero(valor_venda)                        AS valor_venda,
        NULLIF(replace(btrim(unidade_medida), 'm3', 'm³'), '') AS unidade
    FROM anp.stg_preco_combustivel
) AS tratado
WHERE data_coleta IS NOT NULL
  AND produto IS NOT NULL
  AND valor_venda > 0;

COMMIT;

ANALYZE anp.preco_combustivel;

-- Resumo da carga
SELECT
    (SELECT count(*) FROM anp.stg_preco_combustivel) AS linhas_lidas,
    (SELECT count(*) FROM anp.preco_combustivel)     AS linhas_na_base_tratada;
