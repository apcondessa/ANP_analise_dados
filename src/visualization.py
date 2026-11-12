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


def gerar_todos_graficos(
    df: pd.DataFrame, output_dir: str | Path, incluir_linha: bool = True
) -> None:
    """Gera todos os gráficos do projeto na pasta ``output_dir``."""
    from src.analysis import bandeiras_por_estado

    for produto in PRODUTOS:
        print(f"  gráficos de {_rotulo(produto)}...")
        boxplot_produto_geral(df, produto, output_dir)
        boxplot_produto_estado(df, produto, output_dir)
    print("  bandeiras por estado...")
    grafico_bandeiras_estado(bandeiras_por_estado(df), output_dir)
    if incluir_linha:
        print("  evolução de preços...")
        linha_precos_por_produto(df, output_dir)
