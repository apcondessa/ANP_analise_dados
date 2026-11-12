"""Testes dos scripts SQL e da carga no PostgreSQL.

Os testes que usam o banco só rodam com ANP_TESTE_BANCO=1 e as variáveis DB_*
apontando para um banco de TESTE (eles apagam e recriam anp.preco_combustivel).
No GitHub Actions isso é feito com um PostgreSQL temporário (veja ci.yml).
"""
import os

import pandas as pd
import pytest

from src import analysis
from src.carregar_banco import detectar_encoding, ler_consultas

NOMES_CONSULTAS = {
    "estatistica_por_produto",
    "estatistica_por_estado",
    "bandeiras_por_estado",
    "variacao_anual",
    "media_por_regiao",
    "razao_etanol_gasolina",
    "precos_medios_mensais",
}


def test_ler_consultas():
    consultas = ler_consultas()
    assert set(consultas) == NOMES_CONSULTAS
    assert "%(ano)s" in consultas["razao_etanol_gasolina"]
    assert ":ano" not in consultas["razao_etanol_gasolina"]
    # "70%" no comentário precisa virar "70%%" para o psycopg2
    assert "70%%" in consultas["razao_etanol_gasolina"]


def test_detectar_encoding(pasta_raw):
    assert detectar_encoding(pasta_raw / "a.csv") == "utf-8-sig"
    assert detectar_encoding(pasta_raw / "b.csv") == "latin1"


# ---------------------------------------------------------------------------
# Testes com banco de dados
# ---------------------------------------------------------------------------
usa_banco = pytest.mark.skipif(
    os.getenv("ANP_TESTE_BANCO") != "1",
    reason="defina ANP_TESTE_BANCO=1 e as variáveis DB_* de um banco de teste",
)


@pytest.fixture
def conexao(pasta_raw):
    from src.carregar_banco import carregar, conectar

    conexao = conectar()
    carregar(conexao, pasta_raw, verbose=False)
    yield conexao
    conexao.close()


def _consulta(conexao, nome, **parametros):
    with conexao.cursor() as cursor:
        cursor.execute(ler_consultas()[nome], parametros or None)
        colunas = [coluna.name for coluna in cursor.description]
        return pd.DataFrame(cursor.fetchall(), columns=colunas)


def _como_texto_e_numero(df):
    """Padroniza tipos para comparar resultados do SQL e do pandas."""
    df = df.copy()
    for coluna in df.columns:
        if coluna in {"produto", "estado", "regiao"}:
            df[coluna] = df[coluna].astype(str)
        elif coluna in {"ano", "quantidade_bandeiras"}:
            df[coluna] = df[coluna].astype(int)
        elif coluna != "compensa_etanol":
            df[coluna] = df[coluna].astype(float)
    return df.reset_index(drop=True)


@usa_banco
def test_carga_tem_mesmas_linhas_que_o_pandas(conexao, base):
    with conexao.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM anp.stg_preco_combustivel")
        assert cursor.fetchone()[0] == 9  # todas as linhas dos CSVs de exemplo
        cursor.execute("SELECT count(*) FROM anp.preco_combustivel")
        assert cursor.fetchone()[0] == len(base)


@usa_banco
def test_tratamento_igual_ao_pandas(conexao, base):
    with conexao.cursor() as cursor:
        cursor.execute(
            "SELECT data_coleta, estado, produto, valor_venda, unidade, bandeira, ano, mes "
            "FROM anp.preco_combustivel ORDER BY produto, data_coleta"
        )
        banco = pd.DataFrame(
            cursor.fetchall(),
            columns=["data_coleta", "estado", "produto", "valor_venda", "unidade",
                     "bandeira", "ano", "mes"],
        )
    esperado = base.sort_values(["produto", "data_coleta"]).reset_index(drop=True)
    assert banco["produto"].tolist() == esperado["produto"].astype(str).tolist()
    assert banco["estado"].tolist() == esperado["estado"].astype(str).tolist()
    assert banco["unidade"].tolist() == esperado["unidade"].astype(str).tolist()
    assert banco["bandeira"].tolist() == esperado["bandeira"].astype(str).tolist()
    assert banco["valor_venda"].astype(float).tolist() == esperado["valor_venda"].tolist()
    assert pd.to_datetime(banco["data_coleta"]).tolist() == esperado["data_coleta"].tolist()
    assert banco["mes"].tolist() == esperado["mes"].astype(int).tolist()


@usa_banco
@pytest.mark.parametrize(
    ("nome", "funcao", "parametros"),
    [
        ("estatistica_por_produto", analysis.estatistica_por_produto, {}),
        ("estatistica_por_estado", analysis.estatistica_por_estado, {}),
        ("variacao_anual", analysis.variacao_anual, {}),
        ("razao_etanol_gasolina", analysis.razao_etanol_gasolina, {"ano": 2024}),
    ],
)
def test_consulta_igual_a_funcao_python(conexao, base, nome, funcao, parametros):
    sql = _como_texto_e_numero(_consulta(conexao, nome, **parametros))
    python = _como_texto_e_numero(funcao(base, **parametros))[list(sql.columns)]
    # tolerância de 1 centavo: o PostgreSQL arredonda 2,805 para 2,81; o pandas, para 2,80
    pd.testing.assert_frame_equal(sql, python, check_dtype=False, atol=0.0101)


@usa_banco
def test_bandeiras_por_estado_sql(conexao, base):
    sql = _como_texto_e_numero(_consulta(conexao, "bandeiras_por_estado"))
    python = _como_texto_e_numero(
        analysis.bandeiras_por_estado(base).sort_values(
            ["quantidade_bandeiras", "estado"], ascending=[False, True]
        )
    )
    pd.testing.assert_frame_equal(sql, python, check_dtype=False)


@usa_banco
def test_media_por_regiao_sql(conexao, base):
    sql = _consulta(conexao, "media_por_regiao", ano=2024)
    python = (
        analysis.media_por_regiao(base, 2024)
        .rename_axis(columns="produto")
        .stack()
        .dropna()  # combinações região/produto sem coletas
        .rename("media")
        .reset_index()
    )
    juntos = sql.merge(python.astype({"regiao": str, "produto": str}), on=["regiao", "produto"])
    assert len(juntos) == len(sql) == len(python)
    assert (juntos["media_x"].astype(float) - juntos["media_y"]).abs().max() < 0.0101


@usa_banco
def test_carga_pode_ser_repetida(conexao, pasta_raw, base):
    from src.carregar_banco import carregar

    _, tratadas = carregar(conexao, pasta_raw, verbose=False)
    assert tratadas == len(base)
