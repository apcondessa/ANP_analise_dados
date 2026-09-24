"""Funções para carregamento e preparação dos dados da ANP."""
from pathlib import Path

import pandas as pd

# Colunas do CSV da ANP (nome original, sem BOM) -> nome padronizado
COLUNAS = {
    "Regiao - Sigla": "regiao",
    "Estado - Sigla": "estado",
    "Municipio": "municipio",
    "Produto": "produto",
    "Data da Coleta": "data_coleta",
    "Valor de Venda": "valor_venda",
    "Bandeira": "bandeira",
}
COLUNAS_ANALISE = ["data_coleta", "regiao", "estado", "municipio", "bandeira", "produto", "valor_venda"]

# Marca de ordem de bytes (BOM) em UTF-8, ou como aparece quando lida como latin1
_BOM = ("\ufeff", "ï»¿")


def _limpar_nome(nome: str) -> str:
    """Remove BOM e espaços do nome de uma coluna."""
    for bom in _BOM:
        nome = nome.replace(bom, "")
    return nome.strip()


def _ler_csv(caminho: Path) -> pd.DataFrame:
    """Lê um CSV da ANP (separador ';'), tratando variações de encoding.

    Lê apenas as colunas usadas na análise, como texto, para economizar memória.
    """
    for encoding in ("utf-8-sig", "latin1"):
        try:
            df = pd.read_csv(
                caminho,
                sep=";",
                encoding=encoding,
                dtype=str,
                usecols=lambda coluna: _limpar_nome(coluna) in COLUNAS,
            )
        except UnicodeDecodeError:
            continue
        df.columns = [_limpar_nome(coluna) for coluna in df.columns]
        return df
    raise ValueError(f"Não foi possível decodificar o arquivo: {caminho}")


def padronizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza os nomes das colunas e mantém os campos usados na análise."""
    df = df.rename(columns=lambda coluna: COLUNAS.get(_limpar_nome(coluna), coluna)).copy()
    ausentes = [col for col in COLUNAS_ANALISE if col not in df.columns]
    if ausentes:
        raise ValueError(f"Colunas obrigatórias ausentes: {ausentes}")
    return df[COLUNAS_ANALISE].copy()


def preparar_dados(df: pd.DataFrame) -> pd.DataFrame:
    """Converte tipos, remove registros sem campos essenciais e cria ano/mês."""
    df = padronizar_colunas(df)
    df["data_coleta"] = pd.to_datetime(df["data_coleta"], errors="coerce", dayfirst=True)
    df["valor_venda"] = (
        df["valor_venda"].astype(str).str.replace(",", ".", regex=False)
    )
    df["valor_venda"] = pd.to_numeric(df["valor_venda"], errors="coerce")
    df["produto"] = df["produto"].astype("string").str.strip().str.upper()
    df["estado"] = df["estado"].astype("string").str.strip().str.upper()
    df["bandeira"] = df["bandeira"].astype("string").str.strip()
    df = df.dropna(subset=["data_coleta", "produto", "valor_venda"])
    df["ano"] = df["data_coleta"].dt.year
    df["mes"] = df["data_coleta"].dt.month
    return df.reset_index(drop=True)


def carregar_csvs(pasta_raw: str | Path, verbose: bool = True) -> pd.DataFrame:
    """Carrega todos os CSVs da pasta raw e devolve uma base tratada."""
    pasta = Path(pasta_raw)
    arquivos = sorted(pasta.glob("*.csv"))
    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum CSV encontrado em: {pasta.resolve()}\n"
            "Baixe os arquivos da ANP e coloque-os nessa pasta (veja o README)."
        )
    dados = []
    for arquivo in arquivos:
        parcial = _ler_csv(arquivo)
        if verbose:
            print(f"  lido: {arquivo.name} ({len(parcial):,} linhas)")
        dados.append(parcial)
    bruto = pd.concat(dados, ignore_index=True)
    del dados
    tratado = preparar_dados(bruto)
    if verbose:
        descartadas = len(bruto) - len(tratado)
        print(
            f"  {len(bruto):,} linhas lidas em {len(arquivos)} arquivos | "
            f"{descartadas:,} descartadas (linhas vazias ou sem data/produto/valor)"
        )
    return tratado


def salvar_pickle(df: pd.DataFrame, caminho: str | Path) -> None:
    """Salva a base tratada em formato Pickle."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_pickle(caminho)


def carregar_pickle(caminho: str | Path) -> pd.DataFrame:
    """Carrega uma base tratada previamente salva em Pickle."""
    return pd.read_pickle(caminho)
