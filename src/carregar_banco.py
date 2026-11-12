"""Carrega os CSVs da ANP em um banco PostgreSQL usando os scripts da pasta sql/.

Etapas:
    1. sql/01_criar_tabelas.sql  -> cria o esquema, a staging e a tabela final;
    2. COPY de cada CSV de data/raw/ para a staging (texto bruto);
    3. sql/02_transformar.sql    -> trata os dados e grava na tabela final.

A conexão usa as mesmas variáveis de ambiente do notebook Geracao_insights.ipynb
(veja .env.example): DB_NAME, DB_USER, DB_PASSWORD, DB_HOST e DB_PORT.

Uso, a partir da raiz do projeto:
    python src/carregar_banco.py
    python src/carregar_banco.py --pasta data/raw
"""
import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "sql"
RAW = ROOT / "data" / "raw"

COPY_STAGING = (
    "COPY anp.stg_preco_combustivel FROM STDIN "
    "WITH (FORMAT csv, DELIMITER ';', HEADER true)"
)


def conectar():
    """Abre a conexão com o PostgreSQL a partir das variáveis de ambiente."""
    import psycopg2

    if "DB_PASSWORD" not in os.environ:
        sys.exit("Defina a variável de ambiente DB_PASSWORD (veja o .env.example).")
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "ANP"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.environ["DB_PASSWORD"],
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
    )


def executar_script(conexao, nome: str) -> list[tuple]:
    """Executa um arquivo da pasta sql/ e devolve as linhas do último SELECT, se houver."""
    with conexao.cursor() as cursor:
        cursor.execute((SQL / nome).read_text(encoding="utf-8"))
        linhas = cursor.fetchall() if cursor.description else []
    conexao.commit()
    return linhas


def detectar_encoding(arquivo: Path) -> str:
    """Devolve "utf-8-sig" se o arquivo inteiro for UTF-8 válido; senão, "latin1".

    O latin1 aceita qualquer sequência de bytes, por isso é a alternativa final.
    """
    import codecs

    decodificador = codecs.getincrementaldecoder("utf-8-sig")()
    try:
        with open(arquivo, "rb") as entrada:
            while bloco := entrada.read(1024 * 1024):
                decodificador.decode(bloco)
            decodificador.decode(b"", final=True)
    except UnicodeDecodeError:
        return "latin1"
    return "utf-8-sig"


def copiar_csv(conexao, arquivo: Path) -> int:
    """Copia um CSV da ANP para a staging e devolve a quantidade de linhas copiadas."""
    with open(arquivo, encoding=detectar_encoding(arquivo), newline="") as entrada:
        with conexao.cursor() as cursor:
            cursor.copy_expert(COPY_STAGING, entrada)
            linhas = cursor.rowcount
    conexao.commit()
    return linhas


def carregar(conexao, pasta_raw: Path, verbose: bool = True) -> tuple[int, int]:
    """Executa a carga completa. Devolve (linhas lidas, linhas na base tratada)."""
    arquivos = sorted(Path(pasta_raw).glob("*.csv"))
    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum CSV encontrado em: {Path(pasta_raw).resolve()}\n"
            "Baixe os arquivos com `python src/download.py` (veja o README)."
        )
    executar_script(conexao, "01_criar_tabelas.sql")
    for arquivo in arquivos:
        linhas = copiar_csv(conexao, arquivo)
        if verbose:
            print(f"  copiado: {arquivo.name} ({linhas:,} linhas)")
    lidas, tratadas = executar_script(conexao, "02_transformar.sql")[0]
    if verbose:
        print(
            f"  {lidas:,} linhas lidas | {lidas - tratadas:,} descartadas ou duplicadas | "
            f"{tratadas:,} linhas em anp.preco_combustivel"
        )
    return lidas, tratadas


def ler_consultas(caminho: Path = SQL / "03_consultas_analise.sql") -> dict[str, str]:
    """Lê o arquivo de consultas e devolve {nome: sql}, usando as linhas "-- nome: ...".

    O parâmetro ``:ano`` do psql vira ``%(ano)s``, o formato do psycopg2, e os
    sinais de % já existentes (ex.: "70%" nos comentários) viram %%, como o
    psycopg2 exige quando a consulta recebe parâmetros.
    """
    texto = caminho.read_text(encoding="utf-8")
    partes = re.split(r"^-- nome: (\w+)\s*$", texto, flags=re.MULTILINE)
    consultas = {}
    for nome, corpo in zip(partes[1::2], partes[2::2], strict=True):
        consultas[nome] = re.sub(r":ano\b", "%(ano)s", corpo.strip().replace("%", "%%"))
    return consultas


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Carrega os CSVs da ANP no PostgreSQL")
    parser.add_argument("--pasta", type=Path, default=RAW, help="pasta com os CSVs")
    args = parser.parse_args(argv)

    conexao = conectar()
    try:
        print(f"Carregando CSVs de {args.pasta} no PostgreSQL ...")
        carregar(conexao, args.pasta)
    finally:
        conexao.close()
    print("Carga concluída.")


if __name__ == "__main__":
    main()
