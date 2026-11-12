import matplotlib

matplotlib.use("Agg")

import pytest  # noqa: E402

from src.visualization import (  # noqa: E402
    PRODUTOS,
    _do_produto,
    _unidade,
    gerar_todos_graficos,
    precos_medios_mensais,
)


def test_unidades():
    assert _unidade("GNV") == "R$/m³"
    assert _unidade("gasolina") == "R$/litro"


@pytest.mark.parametrize(
    ("produto", "esperado"),
    [("GNV", "do GNV"), ("DIESEL", "do Diesel"), ("GASOLINA", "da Gasolina Comum")],
)
def test_artigo_no_titulo(produto, esperado):
    assert _do_produto(produto) == esperado


def test_precos_medios_mensais(base):
    mensal = precos_medios_mensais(base)
    gnv = mensal[mensal["produto"] == "GNV"]
    assert len(gnv) == 1
    assert gnv["valor_venda"].iloc[0] == pytest.approx(5.04)


def test_gerar_todos_graficos(base, tmp_path):
    gerar_todos_graficos(base, tmp_path)
    gerados = {arquivo.name for arquivo in tmp_path.glob("*.png")}
    # 2 boxplots por produto + bandeiras + evolução + razão etanol/gasolina + regiões
    # (a base de exemplo tem um único ano, então a variação anual é pulada)
    assert len(gerados) == 2 * len(PRODUTOS) + 4
    assert "gnv_valor_venda_por_estado.png" in gerados
    assert "grafico_produto_data_coleta_valor_venda.png" in gerados
    assert "razao_etanol_gasolina_por_estado.png" in gerados
    assert "preco_medio_por_regiao.png" in gerados
    assert "variacao_anual_precos.png" not in gerados


def test_grafico_variacao_anual(tmp_path):
    import pandas as pd

    from src.analysis import variacao_anual
    from src.visualization import grafico_variacao_anual

    dados = pd.DataFrame(
        {"produto": ["GNV", "GNV", "ETANOL", "ETANOL"], "ano": [2024, 2025, 2024, 2025],
         "valor_venda": [4.0, 5.0, 4.0, 3.0]}
    )
    fig, ax = grafico_variacao_anual(variacao_anual(dados))
    textos = sorted(texto.get_text() for texto in ax.texts)
    assert textos == ["+25.0", "-25.0"]
    with pytest.raises(ValueError, match="dois anos"):
        grafico_variacao_anual(variacao_anual(dados[dados["ano"] == 2025]))


def test_barras_de_bandeiras_alinhadas_aos_rotulos(base):
    """Cada barra deve ficar sobre o seu estado, na ordem do DataFrame."""
    from src.analysis import bandeiras_por_estado
    from src.visualization import grafico_bandeiras_estado

    dados = bandeiras_por_estado(base)
    dados["estado"] = dados["estado"].astype("category")  # caso que já causou erro
    fig, ax = grafico_bandeiras_estado(dados)
    rotulos = [rotulo.get_text() for rotulo in ax.get_xticklabels()]
    assert rotulos == dados["estado"].astype(str).tolist()
    barras = sorted(
        (barra for barra in ax.patches if barra.get_height() > 0), key=lambda b: b.get_x()
    )
    assert [barra.get_height() for barra in barras] == dados["quantidade_bandeiras"].tolist()
    assert all(barra.get_width() > 0.5 for barra in barras)  # barras largas, não "fatiadas"
