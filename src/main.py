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

from src.analysis import bandeiras_por_estado, estatistica_por_produto  # noqa: E402
from src.data_processing import carregar_csvs, salvar_pickle  # noqa: E402

RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed" / "dados_anp_tratados.pkl"
OUTPUTS = ROOT / "outputs"


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline do Projeto ANP")
    parser.add_argument(
        "--graficos", action="store_true", help="gera todos os gráficos em outputs/"
    )
    args = parser.parse_args()

    print(f"Lendo CSVs de {RAW} ...")
    df = carregar_csvs(RAW)
    salvar_pickle(df, PROCESSED)
    print(f"Base tratada salva em {PROCESSED}")

    print(f"\nBase tratada: {df.shape[0]:,} linhas x {df.shape[1]} colunas")
    print("\nEstatística por produto e ano:")
    print(estatistica_por_produto(df).to_string(index=False))
    print("\nQuantidade de bandeiras por estado:")
    print(bandeiras_por_estado(df).to_string(index=False))

    if args.graficos:
        import matplotlib

        matplotlib.use("Agg")  # não abre janelas; apenas salva os PNGs
        from src.visualization import gerar_todos_graficos

        print(f"\nGerando gráficos em {OUTPUTS} ...")
        gerar_todos_graficos(df, OUTPUTS)
        print("Gráficos gerados.")


if __name__ == "__main__":
    main()
