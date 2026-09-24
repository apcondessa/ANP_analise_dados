"""Análises descritivas utilizadas no Projeto ANP."""
import pandas as pd


def estatistica_por_produto(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula mínimo, máximo e média do preço por produto e ano."""
    return (
        df.groupby(["produto", "ano"])["valor_venda"]
        .agg(min="min", max="max", media="mean")
        .round(2)
        .reset_index()
    )


def estatistica_por_estado(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula estatísticas de preço por produto, ano e estado."""
    return (
        df.groupby(["produto", "ano", "estado"])["valor_venda"]
        .agg(min="min", max="max", media="mean")
        .round(2)
        .reset_index()
    )


def bandeiras_por_estado(df: pd.DataFrame) -> pd.DataFrame:
    """Conta quantas bandeiras distintas aparecem em cada estado."""
    return (
        df.dropna(subset=["bandeira"])
        .groupby("estado")["bandeira"]
        .nunique()
        .reset_index(name="quantidade_bandeiras")
        .sort_values("quantidade_bandeiras", ascending=False)
        .reset_index(drop=True)
    )


def resumo_produto(df: pd.DataFrame, produto: str) -> pd.Series:
    """Retorna estatística descritiva do preço de um produto."""
    filtro = df["produto"].str.strip().str.upper().eq(produto.strip().upper())
    return df.loc[filtro, "valor_venda"].describe().round(2)
