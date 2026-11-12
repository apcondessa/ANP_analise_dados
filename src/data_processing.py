"""Funções para carregamento e preparação dos dados da ANP."""
from pathlib import Path

import pandas as pd

# Colunas do CSV da ANP (nome original, sem BOM) -> nome padronizado
COLUNAS = {
    "Regiao - Sigla": "regiao",
    "Estado - Sigla": "estado",
    "Municipio": "municipio",
    "CNPJ da Revenda": "cnpj",
    "Produto": "produto",
    "Data da Coleta": "data_coleta",
    "Valor de Venda": "valor_venda",
    "Unidade de Medida": "unidade",
    "Bandeira": "bandeira",
}
COLUNAS_ANALISE = [
    "data_coleta", "regiao", "estado", "municipio", "cnpj",
    "bandeira", "produto", "valor_venda", "unidade",
]

# Colunas de texto com poucos valores distintos: guardadas como "category",
# o que reduz bastante a memória (cada texto é armazenado uma única vez).
COLUNAS_CATEGORICAS = ["regiao", "estado", "municipio", "cnpj", "bandeira", "produto", "unidade"]

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
    df["regiao"] = df["regiao"].str.strip().str.upper()
    df["municipio"] = df["municipio"].str.strip()
    df["cnpj"] = df["cnpj"].str.strip()
    df["produto"] = df["produto"].str.strip().str.upper()
    df["estado"] = df["estado"].str.strip().str.upper()
    df["bandeira"] = df["bandeira"].str.strip()
    # A ANP grafa a unidade do GNV de duas formas ("R$ / m3" e "R$ / m³")
    df["unidade"] = df["unidade"].str.strip().str.replace("m3", "m³", regex=False)
    df = df.dropna(subset=["data_coleta", "produto", "valor_venda"])
    df["ano"] = df["data_coleta"].dt.year.astype("int16")
    df["mes"] = df["data_coleta"].dt.month.astype("int8")
    return df.reset_index(drop=True)


def otimizar_tipos(df: pd.DataFrame) -> pd.DataFrame:
    """Converte as colunas de texto repetitivo para o tipo ``category``."""
    df = df.copy()
    for coluna in COLUNAS_CATEGORICAS:
        if coluna in df.columns:
            df[coluna] = df[coluna].astype("category")
    return df


def remover_duplicatas(df: pd.DataFrame) -> pd.DataFrame:
    """Remove registros repetidos (mesmo posto, produto, data, preço e demais campos)."""
    return df.drop_duplicates().reset_index(drop=True)


def carregar_csvs(pasta_raw: str | Path, verbose: bool = True) -> pd.DataFrame:
    """Carrega todos os CSVs da pasta raw e devolve uma base tratada.

    Cada arquivo é tratado logo após a leitura (antes de juntar todos), para
    que os textos brutos de um arquivo sejam liberados antes de ler o próximo.
    """
    pasta = Path(pasta_raw)
    arquivos = sorted(pasta.glob("*.csv"))
    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum CSV encontrado em: {pasta.resolve()}\n"
            "Baixe os arquivos da ANP e coloque-os nessa pasta (veja o README)."
        )
    dados = []
    total_bruto = 0
    for arquivo in arquivos:
        bruto = _ler_csv(arquivo)
        total_bruto += len(bruto)
        if verbose:
            print(f"  lido: {arquivo.name} ({len(bruto):,} linhas)")
        dados.append(preparar_dados(bruto))
        del bruto
    tratado = otimizar_tipos(pd.concat(dados, ignore_index=True))
    del dados
    total_validas = len(tratado)
    tratado = remover_duplicatas(tratado)
    if verbose:
        print(
            f"  {total_bruto:,} linhas lidas em {len(arquivos)} arquivos | "
            f"{total_bruto - total_validas:,} descartadas "
            "(linhas vazias ou sem data/produto/valor) | "
            f"{total_validas - len(tratado):,} duplicadas removidas"
        )
    return tratado


def salvar_parquet(df: pd.DataFrame, caminho: str | Path) -> None:
    """Salva a base tratada em Parquet (formato colunar, compacto e portável)."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(caminho, index=False)


def carregar_parquet(caminho: str | Path) -> pd.DataFrame:
    """Carrega uma base tratada previamente salva em Parquet."""
    return pd.read_parquet(caminho)


def salvar_pickle(df: pd.DataFrame, caminho: str | Path) -> None:
    """Salva a base tratada em formato Pickle (formato antigo; prefira Parquet)."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_pickle(caminho)


def carregar_pickle(caminho: str | Path) -> pd.DataFrame:
    """Carrega uma base em Pickle (formato antigo; prefira Parquet).

    Atenção: só abra arquivos Pickle de origem confiável, pois carregá-los
    pode executar código.
    """
    return pd.read_pickle(caminho)
