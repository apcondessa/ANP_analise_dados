"""Correção dos preços pela inflação (IPCA).

O IPCA é o índice oficial de inflação do Brasil, calculado pelo IBGE. Para
comparar preços de anos diferentes, cada preço é convertido para reais de um
mês de referência (por padrão, o último mês da série):

    preço real = preço nominal x IPCA(mês de referência) / IPCA(mês do preço)

O índice mensal fica em data/referencia/ipca_mensal.csv (versionado, cerca de
60 linhas), para que o projeto funcione sem internet. Para atualizá-lo:

    python src/inflacao.py                     # jan/2021 a dez/2025
    python src/inflacao.py --inicio 202101 --fim 202612
"""
import argparse
import json
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ARQUIVO_IPCA = ROOT / "data" / "referencia" / "ipca_mensal.csv"

# API SIDRA do IBGE: tabela 1737, variável 2266 = IPCA número-índice (dez/1993 = 100)
URL_SIDRA = "https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/2266/p/{inicio}-{fim}?formato=json"


def baixar_ipca(inicio: str = "202101", fim: str = "202512") -> pd.DataFrame:
    """Baixa o número-índice mensal do IPCA (períodos no formato AAAAMM)."""
    pedido = urllib.request.Request(
        URL_SIDRA.format(inicio=inicio, fim=fim), headers={"User-Agent": "projeto-anp/1.0"}
    )
    with urllib.request.urlopen(pedido, timeout=60) as resposta:
        linhas = json.load(resposta)[1:]  # a primeira linha é o cabeçalho
    return ipca_de_linhas_sidra(linhas)


def ipca_de_linhas_sidra(linhas: list[dict]) -> pd.DataFrame:
    """Converte as linhas da API SIDRA em uma tabela mes / indice."""
    ipca = pd.DataFrame(
        {
            "mes": [pd.Timestamp(f"{linha['D3C'][:4]}-{linha['D3C'][4:]}-01") for linha in linhas],
            "indice": [float(linha["V"]) for linha in linhas],
        }
    )
    if ipca.empty:
        raise ValueError("A API do IBGE não devolveu nenhum mês para o período pedido.")
    return ipca.sort_values("mes").reset_index(drop=True)


def salvar_ipca(ipca: pd.DataFrame, caminho: str | Path = ARQUIVO_IPCA) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    ipca.to_csv(caminho, index=False, date_format="%Y-%m")


def carregar_ipca(caminho: str | Path = ARQUIVO_IPCA) -> pd.DataFrame:
    """Lê o IPCA salvo (colunas mes e indice)."""
    return pd.read_csv(caminho, parse_dates=["mes"], date_format="%Y-%m")


def fatores_correcao(ipca: pd.DataFrame, base: str | pd.Timestamp | None = None) -> pd.Series:
    """Fator que converte cada mês para reais do mês ``base`` (padrão: o último mês)."""
    indices = ipca.set_index("mes")["indice"]
    base = indices.index.max() if base is None else pd.Timestamp(base)
    if base not in indices.index:
        raise ValueError(f"O mês de referência {base:%m/%Y} não está no IPCA carregado.")
    return (indices[base] / indices).rename("fator")


def deflacionar(
    df: pd.DataFrame, ipca: pd.DataFrame, base: str | pd.Timestamp | None = None
) -> pd.DataFrame:
    """Acrescenta a coluna ``valor_real``: o preço em reais do mês de referência.

    Dá erro se algum mês da base não estiver no IPCA, para não deixar preços sem
    correção passarem despercebidos.
    """
    fatores = fatores_correcao(ipca, base)
    meses = df["data_coleta"].dt.to_period("M").dt.to_timestamp()
    faltando = sorted(set(meses.unique()) - set(fatores.index))
    if faltando:
        lista = ", ".join(f"{mes:%m/%Y}" for mes in faltando[:5])
        raise ValueError(
            f"IPCA ausente para {len(faltando)} mês(es) da base (ex.: {lista}). "
            "Atualize com `python src/inflacao.py`."
        )
    resultado = df.copy()
    resultado["valor_real"] = df["valor_venda"].to_numpy() * meses.map(fatores).to_numpy()
    return resultado


def inflacao_acumulada(ipca: pd.DataFrame, inicio=None, fim=None) -> float:
    """Inflação acumulada (%) entre dois meses (padrão: o primeiro e o último)."""
    indices = ipca.set_index("mes")["indice"]
    inicio = indices.index.min() if inicio is None else pd.Timestamp(inicio)
    fim = indices.index.max() if fim is None else pd.Timestamp(fim)
    return (indices[fim] / indices[inicio] - 1) * 100


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Baixa o IPCA mensal do IBGE")
    parser.add_argument("--inicio", default="202101", help="primeiro mês, AAAAMM")
    parser.add_argument("--fim", default="202512", help="último mês, AAAAMM")
    args = parser.parse_args(argv)
    ipca = baixar_ipca(args.inicio, args.fim)
    salvar_ipca(ipca)
    print(
        f"IPCA de {ipca['mes'].min():%m/%Y} a {ipca['mes'].max():%m/%Y} salvo em {ARQUIVO_IPCA} "
        f"(inflação acumulada: {inflacao_acumulada(ipca):.1f}%)"
    )


if __name__ == "__main__":
    main()
