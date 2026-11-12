import pandas as pd
import pytest

from src import inflacao
from src.analysis import variacao_anual_real, variacao_no_periodo


@pytest.fixture
def ipca():
    """IPCA fictício para os meses da base de exemplo (jan a mar/2024)."""
    return pd.DataFrame(
        {
            "mes": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"]),
            "indice": [100.0, 110.0, 125.0],
        }
    )


def test_fatores_correcao(ipca):
    fatores = inflacao.fatores_correcao(ipca)
    assert fatores.tolist() == pytest.approx([1.25, 125 / 110, 1.0])
    # outro mês de referência
    assert inflacao.fatores_correcao(ipca, "2024-01-01").tolist() == pytest.approx(
        [1.0, 100 / 110, 0.8]
    )
    with pytest.raises(ValueError, match="não está no IPCA"):
        inflacao.fatores_correcao(ipca, "2030-01-01")


def test_deflacionar(base, ipca):
    real = inflacao.deflacionar(base, ipca)
    gasolina = real[real["produto"] == "GASOLINA"].iloc[0]  # janeiro: fator 1,25
    assert gasolina["valor_real"] == pytest.approx(5.79 * 1.25)
    diesel = real[real["produto"] == "DIESEL S10"].iloc[0]  # março: fator 1
    assert diesel["valor_real"] == pytest.approx(diesel["valor_venda"])
    assert "valor_real" not in base.columns  # não altera a base original


def test_deflacionar_sem_ipca_do_mes(base, ipca):
    with pytest.raises(ValueError, match="IPCA ausente"):
        inflacao.deflacionar(base, ipca.iloc[1:])


def test_inflacao_acumulada(ipca):
    assert inflacao.inflacao_acumulada(ipca) == pytest.approx(25.0)
    assert inflacao.inflacao_acumulada(ipca, fim="2024-02-01") == pytest.approx(10.0)


def test_linhas_sidra():
    linhas = [
        {"D3C": "202502", "V": "7300.5"},
        {"D3C": "202501", "V": "7250.0"},
    ]
    ipca = inflacao.ipca_de_linhas_sidra(linhas)
    assert ipca["mes"].tolist() == [pd.Timestamp("2025-01-01"), pd.Timestamp("2025-02-01")]
    assert ipca["indice"].tolist() == [7250.0, 7300.5]
    with pytest.raises(ValueError):
        inflacao.ipca_de_linhas_sidra([])


def test_salvar_e_carregar(ipca, tmp_path):
    caminho = tmp_path / "ipca.csv"
    inflacao.salvar_ipca(ipca, caminho)
    pd.testing.assert_frame_equal(inflacao.carregar_ipca(caminho), ipca, check_dtype=False)


def test_arquivo_do_repositorio_bate_com_o_ipca_oficial():
    """O IPCA versionado reproduz a inflação anual oficial divulgada pelo IBGE."""
    ipca = inflacao.carregar_ipca()
    assert ipca["mes"].min() == pd.Timestamp("2021-01-01")
    assert ipca["mes"].max() == pd.Timestamp("2025-12-01")
    assert len(ipca) == 60
    oficial = {2022: 5.79, 2023: 4.62, 2024: 4.83}  # IPCA de dezembro a dezembro (%)
    for ano, taxa in oficial.items():
        calculado = inflacao.inflacao_acumulada(ipca, f"{ano - 1}-12-01", f"{ano}-12-01")
        assert calculado == pytest.approx(taxa, abs=0.006), ano


def test_variacao_anual_real():
    dados = pd.DataFrame(
        {
            "produto": ["GNV", "GNV"],
            "ano": [2024, 2025],
            "valor_venda": [4.0, 5.0],
            "valor_real": [5.0, 5.0],
        }
    )
    resultado = variacao_anual_real(dados)
    assert resultado["variacao_nominal_pct"].tolist()[1] == 25.0
    assert resultado["variacao_real_pct"].tolist()[1] == 0.0
    periodo = variacao_no_periodo(dados)
    assert periodo.iloc[0].to_dict() == {
        "produto": "GNV", "ano_inicial": 2024, "ano_final": 2025,
        "variacao_nominal_pct": 25.0, "variacao_real_pct": 0.0,
    }


def test_grafico_nominal_vs_real(base, ipca, tmp_path):
    import matplotlib

    matplotlib.use("Agg")
    from src.visualization import gerar_todos_graficos

    gerar_todos_graficos(base, tmp_path, ipca=ipca)
    assert (tmp_path / "precos_nominais_vs_reais.png").exists()
