"""Testes do dashboard: dados resumidos, cálculos (logica.py) e a interface (app.py)."""
from pathlib import Path

import pandas as pd
import pytest

from dashboard import logica
from src import analysis
from src.dashboard_dados import bandeiras_por_estado_ano, gerar_dados_dashboard, resumo_mensal

APP = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"


@pytest.fixture
def resumo(base):
    return resumo_mensal(base)


def test_resumo_preserva_totais(base, resumo):
    assert resumo["coletas"].sum() == len(base)
    assert resumo["soma"].sum() == pytest.approx(base["valor_venda"].sum())


def test_media_do_resumo_igual_a_base(base, resumo):
    """Média por soma/coletas tem de bater com a média da base completa."""
    do_resumo = logica.media_por(resumo, ["produto"]).set_index("produto")["media"]
    da_base = base.groupby("produto", observed=True)["valor_venda"].mean()
    for produto, media in da_base.items():
        assert do_resumo[str(produto)] == pytest.approx(media)


def test_filtrar(resumo):
    so_gnv = logica.filtrar(resumo, produtos=["GNV"])
    assert set(so_gnv["produto"]) == {"GNV"}
    assert logica.filtrar(resumo, estados=["SP"])["estado"].unique().tolist() == ["SP"]
    fevereiro = pd.Timestamp("2024-02-01")
    assert set(logica.filtrar(resumo, inicio=fevereiro, fim=fevereiro)["mes"]) == {fevereiro}
    assert len(logica.filtrar(resumo)) == len(resumo)


def test_serie_mensal_por_regiao(resumo):
    serie = logica.serie_mensal(logica.filtrar(resumo, ["GNV"]), "regiao")
    assert serie["grupo"].tolist() == ["Sul"]
    assert serie["media"].iloc[0] == pytest.approx(5.04)


def test_indicadores(resumo):
    ind = logica.indicadores(logica.filtrar(resumo, ["GNV"]))
    assert ind["coletas"] == 2
    assert ind["media"] == pytest.approx(5.04)
    assert ind["variacao_pct"] == pytest.approx(0)  # um único mês
    assert logica.indicadores(resumo.iloc[0:0]) == {}


def test_razao_igual_a_analise(base, resumo):
    painel = logica.razao_etanol_gasolina(resumo)
    oficial = analysis.razao_etanol_gasolina(base)
    assert painel["estado"].tolist() == oficial["estado"].tolist()
    assert painel["razao"].round(3).tolist() == oficial["razao"].tolist()
    assert painel["compensa"].tolist() == oficial["compensa_etanol"].tolist()


def test_bandeiras_por_estado_ano(base):
    resultado = bandeiras_por_estado_ano(base)
    assert dict(zip(resultado["estado"], resultado["quantidade_bandeiras"], strict=True)) == {
        "BA": 1, "PR": 2, "SP": 1,
    }


def test_arquivos_do_repositorio_estao_completos():
    """Os arquivos versionados em dashboard/dados cobrem 2021-2025 e os 27 estados."""
    precos = logica.carregar_precos()
    assert precos["mes"].min() == pd.Timestamp("2021-01-01")
    assert precos["mes"].max() == pd.Timestamp("2025-12-01")
    assert precos["estado"].nunique() == 27
    assert set(precos["produto"]) == set(logica.PRODUTOS)
    assert precos["coletas"].sum() == 4_322_182


# --------------------------------------------------------------------------- interface
@pytest.fixture
def app(base, tmp_path, monkeypatch):
    """Roda o app com os dados de exemplo, sem depender dos arquivos reais."""
    from streamlit.testing.v1 import AppTest

    gerar_dados_dashboard(base, tmp_path)
    monkeypatch.setenv("ANP_DASHBOARD_DADOS", str(tmp_path))
    teste = AppTest.from_file(str(APP), default_timeout=60)
    return teste.run()


def test_app_abre_sem_erros(app):
    assert not app.exception
    assert app.title[0].value.endswith("Preços de Combustíveis no Brasil")
    assert app.metric[0].value == "R$ 5,79"  # gasolina comum na base de exemplo


@pytest.mark.parametrize("opcao", ["Por região", "Por estado"])
def test_app_agrupamentos(app, opcao):
    app.radio[0].set_value(opcao).run()
    assert not app.exception


def test_app_troca_de_produto(app):
    app.selectbox[0].set_value("GNV").run()
    assert not app.exception
    assert app.metric[0].value == "R$ 5,04"
    legenda = app.caption[0].value.replace("\\$", "$")  # o app escapa o "$"
    assert "R$/m³" in legenda
    assert "valores nominais" in legenda


def test_app_sem_estados(app):
    app.multiselect[1].set_value([]).run()
    assert not app.exception
    assert app.warning


# --------------------------------------------------------------------------- inflação
def test_resumo_com_ipca_e_correcao(base):
    ipca = pd.DataFrame(
        {"mes": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"]),
         "indice": [100.0, 110.0, 125.0]}
    )
    resumo = resumo_mensal(base, ipca)
    assert logica.tem_ipca(resumo)
    assert logica.mes_base_ipca(resumo) == pd.Timestamp("2024-03-01")
    corrigido = logica.em_reais_corrigidos(resumo)
    gasolina = logica.media_por(logica.filtrar(corrigido, ["GASOLINA"]), ["produto"])
    assert gasolina["media"].iloc[0] == pytest.approx(5.79 * 1.25)  # janeiro: fator 1,25
    with pytest.raises(ValueError):
        logica.em_reais_corrigidos(resumo_mensal(base))


def test_arquivo_do_repositorio_tem_ipca():
    precos = logica.carregar_precos()
    assert logica.tem_ipca(precos)
    assert logica.mes_base_ipca(precos) == pd.Timestamp("2025-12-01")


def test_app_com_correcao_pela_inflacao(base, tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    ipca = pd.DataFrame(
        {"mes": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"]),
         "indice": [100.0, 110.0, 125.0]}
    )
    gerar_dados_dashboard(base, tmp_path, ipca=ipca)
    monkeypatch.setenv("ANP_DASHBOARD_DADOS", str(tmp_path))
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    assert app.metric[0].value == "R$ 5,79"
    app.toggle[0].set_value(True).run()
    assert not app.exception
    assert app.metric[0].value == "R$ 7,24"  # 5,79 x 1,25
    assert "corrigidos pelo IPCA" in app.caption[0].value

