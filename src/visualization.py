"""Visualizações do Projeto ANP.

Quando ``output_dir`` é informado, a figura é salva em PNG e fechada
(evita acumular figuras na memória ao gerar vários gráficos em sequência).

O estilo é aplicado só dentro de cada gráfico (``sns.axes_style``), sem alterar
as configurações globais do Matplotlib/Seaborn de quem importa este módulo.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

PRODUTOS = ["GASOLINA", "GASOLINA ADITIVADA", "DIESEL", "DIESEL S10", "ETANOL", "GNV"]

# Nomes de exibição e de arquivo (mantêm os nomes já usados na pasta outputs/)
ROTULOS = {
    "GASOLINA": "Gasolina Comum",
    "GASOLINA ADITIVADA": "Gasolina Aditivada",
    "DIESEL": "Diesel",
    "DIESEL S10": "Diesel S10",
    "ETANOL": "Etanol",
    "GNV": "GNV",
}
NOMES_ARQUIVO = {"GASOLINA": "gasolina_comum"}
# Artigo usado nos títulos ("da Gasolina", "do Diesel")
ARTIGOS = {"GASOLINA": "da", "GASOLINA ADITIVADA": "da"}

# O GNV é vendido por metro cúbico; os demais, por litro.
# Por isso o GNV não deve ser comparado no mesmo eixo que os combustíveis líquidos.
UNIDADES = {"GNV": "R$/m³"}
UNIDADE_PADRAO = "R$/litro"

# Uma cor fixa e bem distinta para cada produto, igual em todos os gráficos
CORES = {
    "GASOLINA": "#1f77b4",
    "GASOLINA ADITIVADA": "#17becf",
    "DIESEL": "#8c564b",
    "DIESEL S10": "#ff7f0e",
    "ETANOL": "#2ca02c",
    "GNV": "#d62728",
}
ESTILO = "darkgrid"


def _chave(produto: str) -> str:
    return produto.strip().upper()


def _rotulo(produto: str) -> str:
    return ROTULOS.get(_chave(produto), produto.title())


def _do_produto(produto: str) -> str:
    """Ex.: 'da Gasolina Comum', 'do Diesel S10'."""
    return f"{ARTIGOS.get(_chave(produto), 'do')} {_rotulo(produto)}"


def _contagem(n: int) -> str:
    """Formata a quantidade de coletas de forma curta (ex.: 850, 12k)."""
    return f"{n / 1000:.0f}k" if n >= 1000 else str(n)


def _unidade(produto: str) -> str:
    return UNIDADES.get(_chave(produto), UNIDADE_PADRAO)


def _cor(produto: str) -> str:
    return CORES.get(_chave(produto), "#7f7f7f")


def _nome_arquivo(produto: str) -> str:
    chave = _chave(produto)
    return NOMES_ARQUIVO.get(chave, chave.lower().replace(" ", "_").replace("/", "_"))


def _filtrar_produto(df: pd.DataFrame, produto: str) -> pd.DataFrame:
    return df[df["produto"].str.strip().str.upper().eq(_chave(produto))]


def _finalizar(fig, output_dir, nome: str) -> None:
    """Salva a figura (se houver pasta de saída) e a fecha."""
    if output_dir:
        pasta = Path(output_dir)
        pasta.mkdir(parents=True, exist_ok=True)
        fig.savefig(pasta / nome, dpi=300, bbox_inches="tight")
        plt.close(fig)


def boxplot_produto_estado(
    df: pd.DataFrame, produto: str, output_dir: str | Path | None = None
):
    """Boxplot do preço de um produto por estado, ordenado pela mediana.

    Abaixo de cada estado aparece o número de coletas (n): estados com poucas
    coletas têm caixas pouco confiáveis.
    """
    dados = _filtrar_produto(df, produto)
    por_estado = dados.groupby("estado", observed=True)["valor_venda"]
    ordem = por_estado.median().sort_values().index
    coletas = por_estado.size()
    with sns.axes_style(ESTILO):
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.boxplot(
            x="estado", y="valor_venda", data=dados, order=ordem,
            color=_cor(produto), fliersize=2, ax=ax,
        )
        ax.set_title(
            f"Valor de Venda {_do_produto(produto)} por Estado ({_unidade(produto)})",
            loc="left", fontsize=18,
        )
        ax.set_xticks(
            range(len(ordem)),
            [f"{uf}\n{_contagem(coletas[uf])}" for uf in ordem], fontsize=9,
        )
        ax.set_xlabel(
            "Estado (ordenado pela mediana do preço) e número de coletas", fontsize=14
        )
        ax.set_ylabel(f"Valor de Venda ({_unidade(produto)})", fontsize=14)
    _finalizar(fig, output_dir, f"{_nome_arquivo(produto)}_valor_venda_por_estado.png")
    return fig, ax


def boxplot_produto_geral(
    df: pd.DataFrame, produto: str, output_dir: str | Path | None = None
):
    """Boxplot geral (todos os estados juntos) do preço de um produto."""
    dados = _filtrar_produto(df, produto)
    with sns.axes_style(ESTILO):
        fig, ax = plt.subplots(figsize=(4, 5))
        sns.boxplot(y="valor_venda", data=dados, color=_cor(produto), fliersize=2, ax=ax)
        ax.set_title(f"{_rotulo(produto)} — Brasil", loc="left", fontsize=13)
        ax.set_ylabel(f"Valor de Venda ({_unidade(produto)})")
    _finalizar(fig, output_dir, f"{_nome_arquivo(produto)}_valor_venda.png")
    return fig, ax


def precos_medios_mensais(df: pd.DataFrame) -> pd.DataFrame:
    """Preço médio de venda por produto e mês (uma linha por produto/mês)."""
    return (
        df.groupby(["produto", pd.Grouper(key="data_coleta", freq="MS")], observed=True)[
            "valor_venda"
        ]
        .mean()
        .reset_index()
    )


def linha_precos_por_produto(df: pd.DataFrame, output_dir: str | Path | None = None):
    """Evolução do preço médio mensal por produto.

    Usa a média mensal (em vez de cada dia) para remover o ruído diário.
    Os combustíveis líquidos (R$/litro) e o GNV (R$/m³) ficam em painéis
    separados, porque têm unidades diferentes.
    """
    mensal = precos_medios_mensais(df)
    eh_gnv = mensal["produto"].map(_unidade).ne(UNIDADE_PADRAO)
    paineis = [
        (mensal[~eh_gnv], f"Combustíveis líquidos ({UNIDADE_PADRAO})"),
        (mensal[eh_gnv], f"GNV ({UNIDADES['GNV']})"),
    ]
    with sns.axes_style(ESTILO):
        fig, eixos = plt.subplots(
            2, 1, figsize=(12, 8), sharex=True, gridspec_kw={"height_ratios": [3, 1.3]}
        )
        for ax, (dados, titulo) in zip(eixos, paineis, strict=True):
            for produto in [p for p in PRODUTOS if p in set(dados["produto"])]:
                serie = dados[dados["produto"] == produto]
                ax.plot(
                    serie["data_coleta"], serie["valor_venda"],
                    color=_cor(produto), label=_rotulo(produto), linewidth=2,
                )
            ax.set_title(titulo, loc="left", fontsize=13)
            ax.set_ylabel("Preço médio (R$)")
            ax.legend(loc="upper left", bbox_to_anchor=(1, 1), frameon=False)
        eixos[-1].set_xlabel("Mês da coleta")
        fig.suptitle(
            "Evolução do preço médio mensal de venda por produto",
            x=0.01, ha="left", fontsize=16,
        )
        fig.tight_layout()
    _finalizar(fig, output_dir, "grafico_produto_data_coleta_valor_venda.png")
    return fig, eixos


def grafico_bandeiras_estado(
    df_bandeiras: pd.DataFrame, output_dir: str | Path | None = None
):
    """Gráfico da quantidade de bandeiras distintas por estado."""
    # Ordem explícita (a do DataFrame): sem ela, uma coluna "category" seria
    # desenhada em ordem alfabética e os rótulos ficariam fora do lugar.
    ordem = df_bandeiras["estado"].astype(str).tolist()
    dados = df_bandeiras.assign(estado=df_bandeiras["estado"].astype(str))
    with sns.axes_style(ESTILO):
        fig, ax = plt.subplots(figsize=(14, 6))
        sns.barplot(
            x="estado", y="quantidade_bandeiras", data=dados, order=ordem,
            hue="estado", hue_order=ordem, palette="tab20", legend=False, ax=ax,
        )
        ax.set_title("Quantidade de Bandeiras por Estado")
        ax.set_xlabel("Estado")
        ax.set_ylabel("Quantidade de Bandeiras")
        ax.tick_params(axis="x", rotation=45)
        for rotulo in ax.get_xticklabels():
            rotulo.set_horizontalalignment("right")
        for i, valor in enumerate(df_bandeiras["quantidade_bandeiras"]):
            ax.annotate(str(valor), xy=(i, valor), ha="center", va="bottom")
        fig.tight_layout()
    _finalizar(fig, output_dir, "quantidade_bandeiras_por_estado.png")
    return fig, ax


def grafico_razao_etanol_gasolina(
    df_razao: pd.DataFrame, ano: int | None = None, output_dir: str | Path | None = None
):
    """Barras com a razão etanol/gasolina por estado e a linha de 70%.

    ``df_razao`` é o resultado de ``analysis.razao_etanol_gasolina``.
    """
    from src.analysis import LIMITE_ETANOL_GASOLINA

    dados = df_razao.sort_values("razao", ascending=False)
    cores = [
        CORES["ETANOL"] if compensa else "#b0b0b0" for compensa in dados["compensa_etanol"]
    ]
    with sns.axes_style(ESTILO):
        fig, ax = plt.subplots(figsize=(9, 9))
        ax.barh(dados["estado"].astype(str), dados["razao"] * 100, color=cores)
        ax.axvline(LIMITE_ETANOL_GASOLINA * 100, color="#d62728", linestyle="--", linewidth=1.5)
        ax.text(
            LIMITE_ETANOL_GASOLINA * 100, len(dados) - 0.4, " 70%: limite da regra prática",
            color="#d62728", va="bottom", fontsize=10,
        )
        for posicao, razao in enumerate(dados["razao"]):
            ax.text(
                razao * 100 + 0.3, posicao, f"{razao:.0%}", va="center", fontsize=9,
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 1, "alpha": 0.8},
            )
        periodo = f" em {ano}" if ano else ""
        ax.set_title(
            f"Preço do etanol como % do preço da gasolina comum{periodo}",
            loc="left", fontsize=14,
        )
        ax.set_xlabel("Etanol / Gasolina (%) — em verde, estados onde o etanol compensa")
        ax.set_ylabel("Estado")
        ax.set_xlim(50, max(dados["razao"].max() * 100 + 5, 80))
        ax.set_ylim(-0.6, len(dados) + 0.4)
    _finalizar(fig, output_dir, "razao_etanol_gasolina_por_estado.png")
    return fig, ax


def grafico_variacao_anual(df_variacao: pd.DataFrame, output_dir: str | Path | None = None):
    """Mapa de calor da variação (%) do preço médio de cada produto em relação ao ano anterior.

    ``df_variacao`` é o resultado de ``analysis.variacao_anual``. É preciso ter
    pelo menos dois anos na base.
    """
    if df_variacao["variacao_pct"].isna().all():
        raise ValueError("A variação anual precisa de pelo menos dois anos de dados.")
    tabela = (
        df_variacao.dropna(subset=["variacao_pct"])
        .pivot(index="produto", columns="ano", values="variacao_pct")
        .reindex([p for p in PRODUTOS if p in set(df_variacao["produto"])])
    )
    tabela.index = [_rotulo(p) for p in tabela.index]
    limite = max(abs(tabela.min().min()), abs(tabela.max().max()))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.heatmap(
        tabela, annot=True, fmt="+.1f", cmap="RdBu_r", center=0, vmin=-limite, vmax=limite,
        linewidths=1, cbar_kws={"label": "Variação (%)"}, ax=ax,
    )
    ax.set_title("Variação do preço médio em relação ao ano anterior (%)", loc="left")
    ax.set_xlabel("Ano")
    ax.set_ylabel("")
    _finalizar(fig, output_dir, "variacao_anual_precos.png")
    return fig, ax


def grafico_media_por_regiao(
    df_regiao: pd.DataFrame, ano: int | None = None, output_dir: str | Path | None = None
):
    """Barras agrupadas com o preço médio dos combustíveis líquidos por região.

    ``df_regiao`` é o resultado de ``analysis.media_por_regiao``. O GNV fica de
    fora por ter outra unidade (R$/m³).
    """
    nomes_regioes = {
        "N": "Norte", "NE": "Nordeste", "CO": "Centro-Oeste", "SE": "Sudeste", "S": "Sul",
    }
    produtos = [p for p in PRODUTOS if p in df_regiao.columns and _unidade(p) == UNIDADE_PADRAO]
    dados = (
        df_regiao[produtos]
        .reset_index()
        .melt(id_vars="regiao", var_name="produto", value_name="media")
    )
    dados["regiao"] = dados["regiao"].astype(str).map(lambda r: nomes_regioes.get(r, r))
    dados["produto"] = dados["produto"].map(_rotulo)
    ordem_regioes = [r for r in nomes_regioes.values() if r in set(dados["regiao"])]
    with sns.axes_style(ESTILO):
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.barplot(
            data=dados, x="regiao", y="media", hue="produto", order=ordem_regioes,
            hue_order=[_rotulo(p) for p in produtos],
            palette={_rotulo(p): _cor(p) for p in produtos}, ax=ax,
        )
        for barras in ax.containers:
            ax.bar_label(barras, fmt="%.2f", fontsize=8, padding=2)
        periodo = f" em {ano}" if ano else ""
        ax.set_title(
            f"Preço médio dos combustíveis líquidos por região{periodo} ({UNIDADE_PADRAO})",
            loc="left", fontsize=14,
        )
        ax.set_xlabel("Região")
        ax.set_ylabel(f"Preço médio ({UNIDADE_PADRAO})")
        ax.set_ylim(0, dados["media"].max() * 1.12)
        sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1), frameon=False, title=None)
    _finalizar(fig, output_dir, "preco_medio_por_regiao.png")
    return fig, ax


def grafico_nominal_vs_real(
    df_real: pd.DataFrame,
    base: pd.Timestamp,
    output_dir: str | Path | None = None,
    produtos: tuple[str, ...] = ("GASOLINA", "ETANOL", "DIESEL S10"),
):
    """Preço médio mensal nominal e corrigido pelo IPCA, um painel por produto.

    ``df_real`` precisa da coluna ``valor_real`` (veja ``inflacao.deflacionar``) e
    ``base`` é o mês de referência dos valores reais.
    """
    mensal = (
        df_real[df_real["produto"].isin(produtos)]
        .groupby(["produto", pd.Grouper(key="data_coleta", freq="MS")], observed=True)[
            ["valor_venda", "valor_real"]
        ]
        .mean()
        .reset_index()
    )
    with sns.axes_style(ESTILO):
        fig, eixos = plt.subplots(1, len(produtos), figsize=(16, 5), sharey=True)
        for ax, produto in zip(eixos, produtos, strict=True):
            serie = mensal[mensal["produto"] == produto]
            ax.plot(serie["data_coleta"], serie["valor_venda"], color="#8a8a8a",
                    linewidth=2, label="Nominal (preço da época)")
            ax.plot(serie["data_coleta"], serie["valor_real"], color=_cor(produto),
                    linewidth=2.5, label=f"Real (R$ de {base:%m/%Y})")
            ax.set_title(f"{_rotulo(produto)} ({_unidade(produto)})", loc="left", fontsize=13)
            ax.set_xlabel("")
            ax.tick_params(axis="x", rotation=45)
            ax.legend(loc="upper right", frameon=False, fontsize=9)
        eixos[0].set_ylabel("Preço médio (R$)")
        fig.suptitle(
            f"Preço médio mensal: nominal x corrigido pelo IPCA (em reais de {base:%m/%Y})",
            x=0.01, ha="left", fontsize=16,
        )
        fig.tight_layout()
    _finalizar(fig, output_dir, "precos_nominais_vs_reais.png")
    return fig, eixos


def gerar_todos_graficos(
    df: pd.DataFrame,
    output_dir: str | Path,
    incluir_linha: bool = True,
    ipca: pd.DataFrame | None = None,
) -> None:
    """Gera todos os gráficos do projeto na pasta ``output_dir``.

    Os gráficos de razão etanol/gasolina e de preço por região usam o ano
    mais recente da base. Com ``ipca`` (veja ``inflacao.carregar_ipca``), gera também o
    gráfico de preços nominais x corrigidos pela inflação.
    """
    from src.analysis import (
        bandeiras_por_estado,
        media_por_regiao,
        razao_etanol_gasolina,
        variacao_anual,
    )

    for produto in PRODUTOS:
        print(f"  gráficos de {_rotulo(produto)}...")
        boxplot_produto_geral(df, produto, output_dir)
        boxplot_produto_estado(df, produto, output_dir)
    print("  bandeiras por estado...")
    grafico_bandeiras_estado(bandeiras_por_estado(df), output_dir)
    if incluir_linha:
        print("  evolução de preços...")
        linha_precos_por_produto(df, output_dir)
    ultimo_ano = int(df["ano"].max())
    print(f"  razão etanol/gasolina e preço por região ({ultimo_ano})...")
    grafico_razao_etanol_gasolina(razao_etanol_gasolina(df, ultimo_ano), ultimo_ano, output_dir)
    grafico_media_por_regiao(media_por_regiao(df, ultimo_ano), ultimo_ano, output_dir)
    variacao = variacao_anual(df)
    if variacao["variacao_pct"].notna().any():
        print("  variação anual...")
        grafico_variacao_anual(variacao, output_dir)
    else:
        print("  variação anual: pulada (a base tem um único ano)")
    if ipca is not None:
        from src.inflacao import deflacionar, fatores_correcao

        base = fatores_correcao(ipca).index.max()
        print(f"  preços nominais x reais (IPCA, R$ de {base:%m/%Y})...")
        grafico_nominal_vs_real(deflacionar(df, ipca), base, output_dir)
