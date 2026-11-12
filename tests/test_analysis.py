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
