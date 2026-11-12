from src.analysis import (
    bandeiras_por_estado,
    estatistica_por_estado,
    estatistica_por_produto,
    resumo_produto,
)


def test_estatistica_por_produto(base):
    resultado = estatistica_por_produto(base)
    gnv = resultado[resultado["produto"] == "GNV"].iloc[0]
    assert (gnv["min"], gnv["max"], gnv["media"]) == (4.99, 5.09, 5.04)
    # só aparecem combinações que existem nos dados
    assert len(resultado) == base["produto"].nunique()


def test_estatistica_por_estado(base):
    resultado = estatistica_por_estado(base)
    assert set(resultado.columns) == {"produto", "ano", "estado", "min", "max", "media"}
    assert len(resultado) == 4  # SP gasolina, SP etanol, PR GNV, BA diesel S10


def test_bandeiras_por_estado(base):
    resultado = bandeiras_por_estado(base)
    assert resultado.iloc[0].to_dict() == {"estado": "PR", "quantidade_bandeiras": 2}
    assert dict(zip(resultado["estado"], resultado["quantidade_bandeiras"], strict=True)) == {
        "PR": 2, "SP": 1, "BA": 1,
    }


def test_resumo_produto_ignora_maiusculas_e_espacos(base):
    assert resumo_produto(base, " gnv ")["count"] == 2


import pandas as pd  # noqa: E402

from src.analysis import (  # noqa: E402
    amplitude_por_estado,
    media_por_regiao,
    razao_etanol_gasolina,
    variacao_anual,
)


def _base_dois_anos():
    return pd.DataFrame(
        {
            "produto": ["GASOLINA", "GASOLINA", "GASOLINA", "ETANOL"],
            "ano": [2024, 2024, 2025, 2025],
            "valor_venda": [5.00, 6.00, 6.05, 4.00],
        }
    )


def test_variacao_anual():
    resultado = variacao_anual(_base_dois_anos())
    gasolina = resultado[resultado["produto"] == "GASOLINA"]
    assert gasolina["media"].tolist() == [5.5, 6.05]
    assert pd.isna(gasolina["variacao_pct"].iloc[0])
    assert gasolina["variacao_pct"].iloc[1] == 10.0  # 5,50 -> 6,05


def test_media_por_regiao(base):
    resultado = media_por_regiao(base, 2024)
    assert resultado.loc["S", "GNV"] == 5.04
    assert resultado.loc["SE", "GASOLINA"] == 5.79
    assert media_por_regiao(base, 1999).empty


def test_amplitude_por_estado(base):
    resultado = amplitude_por_estado(base, "gnv")
    assert resultado.iloc[0]["estado"] == "PR"
    assert resultado.iloc[0]["coletas"] == 2
    assert resultado.iloc[0]["amplitude"] == 0.09  # p95 - p5 entre 4,99 e 5,09


def test_razao_etanol_gasolina(base):
    resultado = razao_etanol_gasolina(base, 2024)
    # só SP tem etanol e gasolina na base de exemplo
    assert resultado["estado"].tolist() == ["SP"]
    linha = resultado.iloc[0]
    assert linha["razao"] == round(3.49 / 5.79, 3)
    assert bool(linha["compensa_etanol"]) is True


def test_razao_acima_de_70_nao_compensa():
    dados = pd.DataFrame(
        {
            "estado": ["AP", "AP"],
            "produto": ["ETANOL", "GASOLINA"],
            "ano": [2025, 2025],
            "valor_venda": [5.40, 6.00],
        }
    )
    linha = razao_etanol_gasolina(dados).iloc[0]
    assert linha["razao"] == 0.9
    assert bool(linha["compensa_etanol"]) is False
