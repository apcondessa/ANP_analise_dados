"""Análises descritivas utilizadas no Projeto ANP."""
import pandas as pd


def estatistica_por_produto(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula mínimo, máximo e média do preço por produto e ano."""
    return (
        df.groupby(["produto", "ano"], observed=True)["valor_venda"]
        .agg(min="min", max="max", media="mean")
        .round(2)
        .reset_index()
    )


def estatistica_por_estado(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula estatísticas de preço por produto, ano e estado."""
    return (
        df.groupby(["produto", "ano", "estado"], observed=True)["valor_venda"]
        .agg(min="min", max="max", media="mean")
        .round(2)
        .reset_index()
    )


def bandeiras_por_estado(df: pd.DataFrame) -> pd.DataFrame:
    """Conta quantas bandeiras distintas aparecem em cada estado."""
    return (
        df.dropna(subset=["bandeira"])
        .groupby("estado", observed=True)["bandeira"]
        .nunique()
        .reset_index(name="quantidade_bandeiras")
        .astype({"estado": str})  # texto simples, sem a ordem alfabética da categoria
        .sort_values("quantidade_bandeiras", ascending=False, kind="stable")
        .reset_index(drop=True)
    )


def resumo_produto(df: pd.DataFrame, produto: str) -> pd.Series:
    """Retorna estatística descritiva do preço de um produto."""
    filtro = df["produto"].str.strip().str.upper().eq(produto.strip().upper())
    return df.loc[filtro, "valor_venda"].describe().round(2)


# Regra prática: o etanol rende cerca de 70% da gasolina por litro, então
# compensa abastecer com etanol quando ele custa menos de 70% do preço dela.
LIMITE_ETANOL_GASOLINA = 0.70


def _filtrar_ano(df: pd.DataFrame, ano: int | None) -> pd.DataFrame:
    return df if ano is None else df[df["ano"] == ano]


def variacao_anual(df: pd.DataFrame) -> pd.DataFrame:
    """Preço médio por produto e ano e a variação (%) em relação ao ano anterior."""
    medias = (
        df.groupby(["produto", "ano"], observed=True)["valor_venda"]
        .mean()
        .reset_index(name="media")
        .astype({"produto": str})
        .sort_values(["produto", "ano"])
    )
    medias["variacao_pct"] = medias.groupby("produto")["media"].pct_change() * 100
    return medias.round({"media": 2, "variacao_pct": 1}).reset_index(drop=True)


def media_por_regiao(df: pd.DataFrame, ano: int | None = None) -> pd.DataFrame:
    """Preço médio por região (linhas) e produto (colunas), opcionalmente de um ano."""
    return (
        _filtrar_ano(df, ano)
        .groupby(["regiao", "produto"], observed=True)["valor_venda"]
        .mean()
        .unstack("produto")
        .round(2)
        .rename_axis(index="regiao", columns=None)
    )


def amplitude_por_estado(
    df: pd.DataFrame, produto: str, ano: int | None = None
) -> pd.DataFrame:
    """Dispersão do preço de um produto em cada estado.

    A amplitude usa os percentis 5 e 95 (e não o mínimo e o máximo), para não
    ser dominada por poucos valores extremos. Inclui o número de coletas.
    """
    dados = _filtrar_ano(df, ano)
    filtro = dados["produto"].str.strip().str.upper().eq(produto.strip().upper())
    resultado = (
        dados.loc[filtro]
        .groupby("estado", observed=True)["valor_venda"]
        .agg(
            coletas="size",
            p5=lambda s: s.quantile(0.05),
            p95=lambda s: s.quantile(0.95),
        )
        .reset_index()
        .astype({"estado": str})
    )
    resultado["amplitude"] = resultado["p95"] - resultado["p5"]
    return (
        resultado.round({"p5": 2, "p95": 2, "amplitude": 2})
        .sort_values(["amplitude", "estado"], ascending=[False, True])
        .reset_index(drop=True)
    )


def razao_etanol_gasolina(df: pd.DataFrame, ano: int | None = None) -> pd.DataFrame:
    """Razão entre o preço médio do etanol e o da gasolina comum em cada estado.

    ``compensa_etanol`` é verdadeiro quando a razão fica abaixo de 70%.
    """
    dados = _filtrar_ano(df, ano)
    dados = dados[dados["produto"].isin(["ETANOL", "GASOLINA"])]
    precos = (
        dados.groupby(["estado", "produto"], observed=True)["valor_venda"]
        .mean()
        .unstack("produto")
        .dropna()
        .rename(columns={"ETANOL": "etanol", "GASOLINA": "gasolina"})
    )
    resultado = precos[["etanol", "gasolina"]].reset_index().rename_axis(columns=None)
    resultado["estado"] = resultado["estado"].astype(str)
    resultado["razao"] = resultado["etanol"] / resultado["gasolina"]
    resultado["compensa_etanol"] = resultado["razao"] < LIMITE_ETANOL_GASOLINA
    return (
        resultado.round({"etanol": 2, "gasolina": 2, "razao": 3})
        .sort_values(["razao", "estado"])
        .reset_index(drop=True)
    )


def variacao_anual_real(df: pd.DataFrame) -> pd.DataFrame:
    """Médias anuais nominal e real (corrigida pelo IPCA) e suas variações (%) anuais.

    ``df`` precisa da coluna ``valor_real`` (veja ``inflacao.deflacionar``).
    """
    medias = (
        df.groupby(["produto", "ano"], observed=True)[["valor_venda", "valor_real"]]
        .mean()
        .reset_index()
        .rename(columns={"valor_venda": "media_nominal", "valor_real": "media_real"})
        .astype({"produto": str})
        .sort_values(["produto", "ano"])
    )
    por_produto = medias.groupby("produto")
    medias["variacao_nominal_pct"] = por_produto["media_nominal"].pct_change() * 100
    medias["variacao_real_pct"] = por_produto["media_real"].pct_change() * 100
    return medias.round(
        {"media_nominal": 2, "media_real": 2, "variacao_nominal_pct": 1, "variacao_real_pct": 1}
    ).reset_index(drop=True)


def variacao_no_periodo(df: pd.DataFrame) -> pd.DataFrame:
    """Variação (%) da média anual entre o primeiro e o último ano, nominal e real.

    ``df`` precisa da coluna ``valor_real`` (veja ``inflacao.deflacionar``).
    """
    medias = df.groupby(["produto", "ano"], observed=True)[["valor_venda", "valor_real"]].mean()
    primeiro, ultimo = int(df["ano"].min()), int(df["ano"].max())
    inicio = medias.xs(primeiro, level="ano")
    fim = medias.xs(ultimo, level="ano")
    resultado = pd.DataFrame(
        {
            "ano_inicial": primeiro,
            "ano_final": ultimo,
            "variacao_nominal_pct": (fim["valor_venda"] / inicio["valor_venda"] - 1) * 100,
            "variacao_real_pct": (fim["valor_real"] / inicio["valor_real"] - 1) * 100,
        }
    ).dropna()
    resultado.index = resultado.index.astype(str)
    return (
        resultado.round({"variacao_nominal_pct": 1, "variacao_real_pct": 1})
        .rename_axis("produto")
        .reset_index()
        .sort_values("variacao_real_pct", ascending=False)
        .reset_index(drop=True)
    )
