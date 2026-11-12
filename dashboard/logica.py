"""Cálculos do dashboard, separados da interface para poderem ser testados.

Trabalha com o resumo mensal gerado por src/dashboard_dados.py: cada linha tem a
soma dos preços e o número de coletas de um mês, estado e produto. A média de
qualquer recorte é soma / coletas, o que dá exatamente a mesma média da base
completa.
"""
import os
from pathlib import Path

import pandas as pd

PASTA_PADRAO = Path(__file__).resolve().parent / "dados"

PRODUTOS = {
    "GASOLINA": "Gasolina Comum",
    "GASOLINA ADITIVADA": "Gasolina Aditivada",
    "ETANOL": "Etanol",
    "DIESEL": "Diesel",
    "DIESEL S10": "Diesel S10",
    "GNV": "GNV",
}
UNIDADES = {"GNV": "R$/m³"}
UNIDADE_PADRAO = "R$/litro"
REGIOES = {"N": "Norte", "NE": "Nordeste", "CO": "Centro-Oeste", "SE": "Sudeste", "S": "Sul"}
LIMITE_ETANOL_GASOLINA = 0.70


def unidade(produto: str) -> str:
    return UNIDADES.get(produto, UNIDADE_PADRAO)


def pasta_dados() -> Path:
    """Pasta dos dados resumidos; pode ser trocada pela variável ANP_DASHBOARD_DADOS."""
    return Path(os.getenv("ANP_DASHBOARD_DADOS", PASTA_PADRAO))


def carregar_precos(pasta: Path | None = None) -> pd.DataFrame:
    return pd.read_parquet(Path(pasta or pasta_dados()) / "precos_mensais.parquet")


def carregar_bandeiras(pasta: Path | None = None) -> pd.DataFrame:
    return pd.read_parquet(Path(pasta or pasta_dados()) / "bandeiras_por_estado_ano.parquet")


def filtrar(
    precos: pd.DataFrame,
    produtos: list[str] | None = None,
    estados: list[str] | None = None,
    inicio: pd.Timestamp | None = None,
    fim: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Filtra o resumo mensal. ``None`` em um filtro significa "todos"."""
    filtro = pd.Series(True, index=precos.index)
    if produtos is not None:
        filtro &= precos["produto"].isin(produtos)
    if estados is not None:
        filtro &= precos["estado"].isin(estados)
    if inicio is not None:
        filtro &= precos["mes"] >= inicio
    if fim is not None:
        filtro &= precos["mes"] <= fim
    return precos[filtro]


def media_por(dados: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    """Média exata (soma / coletas), mínimo, máximo e coletas por grupo."""
    resultado = (
        dados.groupby(colunas, observed=True)
        .agg(soma=("soma", "sum"), coletas=("coletas", "sum"),
             minimo=("minimo", "min"), maximo=("maximo", "max"))
        .reset_index()
    )
    resultado["media"] = resultado["soma"] / resultado["coletas"]
    return resultado.drop(columns="soma")


def serie_mensal(dados: pd.DataFrame, agrupar_por: str | None = None) -> pd.DataFrame:
    """Preço médio por mês, para o conjunto todo ou separado por região/estado.

    A coluna ``grupo`` traz o nome da linha do gráfico ("Selecionados",
    o nome da região ou a sigla do estado).
    """
    if agrupar_por is None:
        serie = media_por(dados, ["mes"])
        serie["grupo"] = "Selecionados"
    else:
        serie = media_por(dados, ["mes", agrupar_por])
        serie["grupo"] = serie[agrupar_por]
        if agrupar_por == "regiao":
            serie["grupo"] = serie["grupo"].map(REGIOES).fillna(serie["grupo"])
    return serie[["mes", "grupo", "media", "coletas"]]


def indicadores(dados: pd.DataFrame) -> dict:
    """Números de destaque do recorte filtrado (um único produto)."""
    if dados.empty:
        return {}
    mensal = media_por(dados, ["mes"]).sort_values("mes")
    por_estado = media_por(dados, ["estado"]).sort_values("media")
    primeiro, ultimo = mensal.iloc[0], mensal.iloc[-1]
    return {
        "media": dados["soma"].sum() / dados["coletas"].sum(),
        "coletas": int(dados["coletas"].sum()),
        "mes_inicial": primeiro["mes"],
        "mes_final": ultimo["mes"],
        "media_inicial": primeiro["media"],
        "media_final": ultimo["media"],
        "variacao_pct": (ultimo["media"] / primeiro["media"] - 1) * 100,
        "mais_barato": (por_estado.iloc[0]["estado"], por_estado.iloc[0]["media"]),
        "mais_caro": (por_estado.iloc[-1]["estado"], por_estado.iloc[-1]["media"]),
    }


def razao_etanol_gasolina(dados: pd.DataFrame) -> pd.DataFrame:
    """Etanol / gasolina comum por estado no recorte (que deve incluir os dois produtos)."""
    medias = (
        media_por(dados[dados["produto"].isin(["ETANOL", "GASOLINA"])], ["estado", "produto"])
        .pivot(index="estado", columns="produto", values="media")
        .dropna()
    )
    if medias.empty:
        return pd.DataFrame(columns=["estado", "etanol", "gasolina", "razao", "compensa"])
    resultado = pd.DataFrame(
        {"etanol": medias["ETANOL"], "gasolina": medias["GASOLINA"]}
    ).reset_index()
    resultado["razao"] = resultado["etanol"] / resultado["gasolina"]
    resultado["compensa"] = resultado["razao"] < LIMITE_ETANOL_GASOLINA
    return resultado.sort_values("razao").reset_index(drop=True)


def tabela_estados(dados: pd.DataFrame, bandeiras: pd.DataFrame, anos: list[int]) -> pd.DataFrame:
    """Tabela por estado: média, mínimo, máximo, coletas e bandeiras (no último ano)."""
    tabela = media_por(dados, ["regiao", "estado"])
    ultimo_ano = max(anos)
    qtd = bandeiras[bandeiras["ano"] == ultimo_ano][["estado", "quantidade_bandeiras"]]
    tabela = tabela.merge(qtd, on="estado", how="left")
    tabela["regiao"] = tabela["regiao"].map(REGIOES).fillna(tabela["regiao"])
    return (
        tabela[["estado", "regiao", "media", "minimo", "maximo", "coletas", "quantidade_bandeiras"]]
        .rename(columns={"quantidade_bandeiras": f"bandeiras_{ultimo_ano}"})
        .sort_values("media", ascending=False)
        .reset_index(drop=True)
    )


def tem_ipca(precos: pd.DataFrame) -> bool:
    """Indica se o resumo traz o fator de correção pelo IPCA."""
    return "fator_ipca" in precos.columns and precos["fator_ipca"].notna().all()


def mes_base_ipca(precos: pd.DataFrame) -> pd.Timestamp:
    """Mês de referência dos valores reais (o mês em que o fator vale 1)."""
    return pd.Timestamp(precos.loc[precos["fator_ipca"].sub(1).abs() < 1e-12, "mes"].max())


def em_reais_corrigidos(precos: pd.DataFrame) -> pd.DataFrame:
    """Converte soma, mínimo e máximo para reais do mês de referência do IPCA.

    O fator é o mesmo para todas as coletas de um mês, então soma x fator dá
    exatamente a soma dos preços corrigidos.
    """
    if not tem_ipca(precos):
        raise ValueError("O resumo não tem a coluna fator_ipca. Rode `python src/main.py`.")
    corrigido = precos.copy()
    for coluna in ["soma", "minimo", "maximo"]:
        corrigido[coluna] = corrigido[coluna] * corrigido["fator_ipca"]
    return corrigido
