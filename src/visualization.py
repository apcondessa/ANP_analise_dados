"""Visualizações do Projeto ANP.

Quando ``output_dir`` é informado, a figura é salva em PNG e fechada
(evita acumular figuras na memória ao gerar vários gráficos em sequência).
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


def _rotulo(produto: str) -> str:
    return ROTULOS.get(produto.strip().upper(), produto.title())


def _nome_arquivo(produto: str) -> str:
    chave = produto.strip().upper()
    return NOMES_ARQUIVO.get(chave, chave.lower().replace(" ", "_").replace("/", "_"))


def _filtrar_produto(df: pd.DataFrame, produto: str) -> pd.DataFrame:
    return df[df["produto"].str.strip().str.upper().eq(produto.strip().upper())].copy()


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
    """Boxplot do preço de um produto por estado."""
    dados = _filtrar_produto(df, produto)
    sns.set_palette("Accent")
    sns.set_style("darkgrid")
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.boxplot(x="estado", y="valor_venda", data=dados, ax=ax)
    ax.set_title(f"Valor de Venda (R$) da {_rotulo(produto)} por Estado", loc="left", fontsize=18)
    ax.set_xlabel("Estado", fontsize=14)
    ax.set_ylabel("Valor de Venda (R$)", fontsize=14)
    _finalizar(fig, output_dir, f"{_nome_arquivo(produto)}_valor_venda_por_estado.png")
    return fig, ax


def boxplot_produto_geral(
    df: pd.DataFrame, produto: str, output_dir: str | Path | None = None
):
    """Boxplot geral (todos os estados juntos) do preço de um produto."""
    dados = _filtrar_produto(df, produto)
    sns.set_palette("Accent")
    sns.set_style("darkgrid")
    fig, ax = plt.subplots(figsize=(4, 4))
    sns.boxplot(y="valor_venda", data=dados, ax=ax)
    _finalizar(fig, output_dir, f"{_nome_arquivo(produto)}_valor_venda.png")
    return fig, ax


def linha_precos_por_produto(
    df: pd.DataFrame,
    output_dir: str | Path | None = None,
    errorbar=("ci", 95),
):
    """Série temporal dos preços por produto.

    Com toda a base (~4,3 milhões de linhas) o intervalo de confiança padrão
    leva ~2 minutos. Use ``errorbar=None`` para uma versão rápida, sem a faixa.
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.lineplot(
        data=df, x="data_coleta", y="valor_venda", hue="produto", errorbar=errorbar, ax=ax
    )
    sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))
    ax.set_title("Evolução do valor de venda por produto", loc="left", fontsize=16)
    ax.set_xlabel("Data da coleta")
    ax.set_ylabel("Valor de Venda (R$)")
    _finalizar(fig, output_dir, "grafico_produto_data_coleta_valor_venda.png")
    return fig, ax


def grafico_bandeiras_estado(
    df_bandeiras: pd.DataFrame, output_dir: str | Path | None = None
):
    """Gráfico da quantidade de bandeiras distintas por estado."""
    fig, ax = plt.subplots(figsize=(14, 6))
    sns.barplot(
        x="estado", y="quantidade_bandeiras", data=df_bandeiras,
        hue="estado", palette="tab20", legend=False, ax=ax,
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
        print("  evolução de preços (pode levar alguns minutos)...")
        linha_precos_por_produto(df, output_dir)
