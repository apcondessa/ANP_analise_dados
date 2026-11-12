-- =============================================================================
-- 01_criar_tabelas.sql
-- Cria o esquema "anp", a tabela de staging (dados brutos, como vêm do CSV)
-- e a tabela final tratada, usada pelas análises e pelo notebook
-- Geracao_insights.ipynb.
--
-- Pode ser executado mais de uma vez: a staging é recriada e a tabela final só
-- é criada se ainda não existir.
-- Testado no PostgreSQL 16 e compatível com o 17.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS anp;

-- -----------------------------------------------------------------------------
-- Staging: uma coluna de texto para cada coluna do CSV da ANP, sem tratamento.
-- Recebe os arquivos via COPY (veja src/carregar_banco.py).
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS anp.stg_preco_combustivel;

CREATE TABLE anp.stg_preco_combustivel (
    regiao_sigla    text,
    estado_sigla    text,
    municipio       text,
    revenda         text,
    cnpj_revenda    text,
    nome_rua        text,
    numero_rua      text,
    complemento     text,
    bairro          text,
    cep             text,
    produto         text,
    data_coleta     text,
    valor_venda     text,
    valor_compra    text,
    unidade_medida  text,
    bandeira        text
);

-- -----------------------------------------------------------------------------
-- Tabela final: tipos corretos, textos padronizados e sem duplicatas.
-- As colunas ano e mes são calculadas automaticamente a partir da data.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS anp.preco_combustivel (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    data_coleta  date          NOT NULL,
    regiao       varchar(2),
    estado       varchar(2),
    municipio    text,
    cnpj         varchar(18),
    bandeira     text,
    produto      text          NOT NULL,
    valor_venda  numeric(7, 3) NOT NULL CHECK (valor_venda > 0),
    unidade      text,
    ano          smallint GENERATED ALWAYS AS (EXTRACT(YEAR FROM data_coleta)::smallint) STORED,
    mes          smallint GENERATED ALWAYS AS (EXTRACT(MONTH FROM data_coleta)::smallint) STORED
);

COMMENT ON TABLE anp.preco_combustivel IS
    'Preços de venda de combustíveis coletados pela ANP, tratados (ver sql/02_transformar.sql).';
COMMENT ON COLUMN anp.preco_combustivel.unidade IS
    'R$ / litro para os combustíveis líquidos; R$ / m³ para o GNV.';

-- Índices para os filtros e agrupamentos mais usados nas análises
CREATE INDEX IF NOT EXISTS ix_preco_produto_data ON anp.preco_combustivel (produto, data_coleta);
CREATE INDEX IF NOT EXISTS ix_preco_estado_produto ON anp.preco_combustivel (estado, produto);
CREATE INDEX IF NOT EXISTS ix_preco_regiao ON anp.preco_combustivel (regiao);

-- -----------------------------------------------------------------------------
-- Converte texto dd/mm/aaaa em data; devolve NULL se a data for inválida
-- (ex.: 31/02/2024), em vez de interromper a carga.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION anp.para_data(texto text)
RETURNS date
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    IF texto IS NULL OR btrim(texto) !~ '^\d{2}/\d{2}/\d{4}$' THEN
        RETURN NULL;
    END IF;
    RETURN make_date(
        substr(btrim(texto), 7, 4)::int,
        substr(btrim(texto), 4, 2)::int,
        substr(btrim(texto), 1, 2)::int
    );
EXCEPTION
    WHEN datetime_field_overflow OR invalid_datetime_format THEN
        RETURN NULL;
END;
$$;

-- Converte "5,79" em 5.79; devolve NULL se o texto não for um número válido
CREATE OR REPLACE FUNCTION anp.para_numero(texto text)
RETURNS numeric
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT CASE
        WHEN replace(btrim(texto), ',', '.') ~ '^\d+(\.\d+)?$'
        THEN replace(btrim(texto), ',', '.')::numeric
    END;
$$;
