"""Ponto de entrada do projeto: prepara os dados, mostra as análises e (opcional) gera os gráficos.

Uso, a partir da raiz do projeto:
    python src/main.py               # prepara a base e mostra as análises
    python src/main.py --graficos    # também gera todos os gráficos em outputs/
    python -m src.main               # equivalente
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # permite rodar `python src/main.py`
    sys.path.insert(0, str(ROOT))

from src.analysis import (  # noqa: E402
    bandeiras_por_estado,
    estatistica_por_produto,
    media_por_regiao,
    razao_etanol_gasolina,
    variacao_anual,
    variacao_anual_real,
    variacao_no_periodo,
)
from src.dashboard_dados import PASTA_DASHBOARD, gerar_dados_dashboard  # noqa: E402
from src.data_processing import carregar_csvs, salvar_parquet  # noqa: E402
from src.inflacao import ARQUIVO_IPCA, carregar_ipca, deflacionar, fatores_correcao  # noqa: E402

RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed" / "dados_anp_tratados.parquet"
OUTPUTS = ROOT / "outputs"


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline do Projeto ANP")
    parser.add_argument(
        "--graficos", action="store_true", help="gera todos os gráficos em outputs/"
    )
    args = parser.parse_args()

    print(f"Lendo CSVs de {RAW} ...")
    df = carregar_csvs(RAW)
    salvar_parquet(df, PROCESSED)
    print(f"Base tratada salva em {PROCESSED}")
    ipca = carregar_ipca() if ARQUIVO_IPCA.exists() else None
    gerar_dados_dashboard(df, ipca=ipca)
    print(f"Dados do dashboard salvos em {PASTA_DASHBOARD}")

    print(f"\nBase tratada: {df.shape[0]:,} linhas x {df.shape[1]} colunas")
    print("\nEstatística por produto e ano:")
    print(estatistica_por_produto(df).to_string(index=False))
    print("\nQuantidade de bandeiras por estado:")
    print(bandeiras_por_estado(df).to_string(index=False))

    ultimo_ano = int(df["ano"].max())
    print("\nPreço médio por produto e ano, com variação (%) em relação ao ano anterior:")
    print(variacao_anual(df).to_string(index=False))
    print(f"\nPreço médio por região em {ultimo_ano} (GNV em R$/m³; demais em R$/litro):")
    print(media_por_regiao(df, ultimo_ano).to_string())
    razao = razao_etanol_gasolina(df, ultimo_ano)
    print(
        f"\nEtanol como fração do preço da gasolina em {ultimo_ano} "
        f"(compensa abaixo de 0,70; {int(razao['compensa_etanol'].sum())} estados):"
    )
    print(razao.to_string(index=False))

    if ipca is None:
        print(f"\nIPCA não encontrado em {ARQUIVO_IPCA}: análise real pulada.")
    else:
        base = fatores_correcao(ipca).index.max()
        df_real = deflacionar(df, ipca)
        print(f"\nPreço médio anual nominal e real (corrigido pelo IPCA, em R$ de {base:%m/%Y}):")
        print(variacao_anual_real(df_real).to_string(index=False))
        print("\nVariação da média anual no período, nominal x real (%):")
        print(variacao_no_periodo(df_real).to_string(index=False))

    if args.graficos:
        import matplotlib

        matplotlib.use("Agg")  # não abre janelas; apenas salva os PNGs
        from src.visualization import gerar_todos_graficos

        print(f"\nGerando gráficos em {OUTPUTS} ...")
        gerar_todos_graficos(df, OUTPUTS, ipca=ipca)
        print("Gráficos gerados.")


if __name__ == "__main__":
    main()
