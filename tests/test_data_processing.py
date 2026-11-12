import pandas as pd
import pytest

from src.data_processing import (
    COLUNAS_ANALISE,
    carregar_csvs,
    carregar_parquet,
    padronizar_colunas,
    salvar_parquet,
)
from tests.conftest import TOTAL_FINAL, TOTAL_LIDAS


def test_totais_e_mensagem(pasta_raw, capsys):
    df = carregar_csvs(pasta_raw)
    assert len(df) == TOTAL_FINAL
    saida = capsys.readouterr().out
    assert f"{TOTAL_LIDAS:,} linhas lidas em 2 arquivos" in saida
    assert "3 descartadas" in saida
    assert "1 duplicadas removidas" in saida


def test_colunas(base):
    assert list(base.columns) == [*COLUNAS_ANALISE, "ano", "mes"]


def test_tipos(base):
    assert pd.api.types.is_datetime64_any_dtype(base["data_coleta"])
    assert pd.api.types.is_float_dtype(base["valor_venda"])
    for coluna in ["estado", "produto", "unidade", "bandeira", "cnpj"]:
        assert isinstance(base[coluna].dtype, pd.CategoricalDtype), coluna


def test_valor_com_virgula_vira_numero(base):
    gasolina = base[base["produto"] == "GASOLINA"]
    assert gasolina["valor_venda"].tolist() == [5.79]


def test_data_dia_mes_ano(base):
    gnv = base[base["produto"] == "GNV"].sort_values("data_coleta")
    assert gnv["data_coleta"].iloc[0] == pd.Timestamp("2024-02-15")
    assert gnv["mes"].tolist() == [2, 2]
    assert set(base["ano"]) == {2024}


def test_textos_padronizados(base):
    diesel = base[base["produto"] == "DIESEL S10"]
    assert len(diesel) == 1
    assert diesel["estado"].iloc[0] == "BA"
    assert diesel["bandeira"].iloc[0] == "VIBRA"


def test_unidade_do_gnv_padronizada(base):
    gnv = base[base["produto"] == "GNV"]
    assert set(gnv["unidade"]) == {"R$ / m³"}


def test_sem_nulos_nos_campos_essenciais(base):
    assert base[["data_coleta", "produto", "valor_venda"]].notna().all().all()


def test_pasta_sem_csv(tmp_path):
    with pytest.raises(FileNotFoundError, match="Nenhum CSV"):
        carregar_csvs(tmp_path)


def test_coluna_obrigatoria_ausente():
    with pytest.raises(ValueError, match="ausentes"):
        padronizar_colunas(pd.DataFrame({"Produto": ["GASOLINA"]}))


def test_parquet_ida_e_volta(base, tmp_path):
    caminho = tmp_path / "processed" / "base.parquet"
    salvar_parquet(base, caminho)
    lida = carregar_parquet(caminho)
    pd.testing.assert_frame_equal(lida, base)
