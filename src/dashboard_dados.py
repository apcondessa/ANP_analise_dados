"""Gera os dados resumidos usados pelo dashboard (dashboard/app.py).

O dashboard não usa a base completa (4,3 milhões de linhas): usa somas e
contagens por mês, estado e produto (cerca de 10 mil linhas). Com elas, a média
de qualquer combinação de filtros é exata: soma dos preços / número de coletas.

O arquivo é pequeno (menos de 1 MB) e fica no repositório, para que o
dashboard funcione online sem precisar baixar os dados da ANP.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PASTA_DASHBOARD = ROOT / "dashboard" / "dados"
ARQUIVO_PRECOS = PASTA_DASHBOARD / "precos_mensais.parquet"
ARQUIVO_BANDEIRAS = PASTA_DASHBOARD / "bandeiras_por_estado_ano.parquet"


def resumo_mensal(df: pd.DataFrame, ipca: pd.DataFrame | None = None) -> pd.DataFrame:
    """Soma, quantidade, mínimo e máximo do preço por mês, região, estado e produto.

    Com ``ipca``, inclui a coluna ``fator_ipca``: multiplicando soma, mínimo e
    máximo por ela, os valores ficam em reais do último mês do IPCA.
    """
    resumo = (
        df.assign(mes=df["data_coleta"].dt.to_period("M").dt.to_timestamp())
        .groupby(["mes", "regiao", "estado", "produto", "unidade"], observed=True)["valor_venda"]
        .agg(soma="sum", coletas="size", minimo="min", maximo="max")
        .reset_index()
    )
    for coluna in ["regiao", "estado", "produto", "unidade"]:
        resumo[coluna] = resumo[coluna].astype(str)
    resumo["coletas"] = resumo["coletas"].astype("int32")
    if ipca is not None:
        from src.inflacao import fatores_correcao

        fatores = fatores_correcao(ipca)
        resumo["fator_ipca"] = resumo["mes"].map(fatores)
        if resumo["fator_ipca"].isna().any():
            raise ValueError("IPCA ausente para algum mês da base. Rode `python src/inflacao.py`.")
    return resumo.sort_values(["mes", "estado", "produto"]).reset_index(drop=True)


def bandeiras_por_estado_ano(df: pd.DataFrame) -> pd.DataFrame:
    """Quantidade de bandeiras distintas por estado e ano (não dá para somar entre anos)."""
    return (
        df.dropna(subset=["bandeira"])
        .groupby(["ano", "estado"], observed=True)["bandeira"]
        .nunique()
        .reset_index(name="quantidade_bandeiras")
        .astype({"estado": str, "ano": "int16", "quantidade_bandeiras": "int16"})
        .sort_values(["ano", "estado"])
        .reset_index(drop=True)
    )


def gerar_dados_dashboard(
    df: pd.DataFrame, pasta: str | Path = PASTA_DASHBOARD, ipca: pd.DataFrame | None = None
) -> None:
    """Grava os arquivos do dashboard na pasta indicada."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    resumo_mensal(df, ipca).to_parquet(pasta / ARQUIVO_PRECOS.name, index=False)
    bandeiras_por_estado_ano(df).to_parquet(pasta / ARQUIVO_BANDEIRAS.name, index=False)
