"""Baixa os CSVs semestrais de preços de combustíveis automotivos da ANP.

Uso, a partir da raiz do projeto:
    python src/download.py                       # 2021 a 2025 (padrão do projeto)
    python src/download.py --inicio 2023 --fim 2024

Os arquivos são salvos em ``data/raw/`` com nomes padronizados
(``ca-AAAA-SS.csv``). Arquivos que já existem são pulados.
A partir de 2022 a ANP publica os arquivos compactados (.zip); o CSV é
extraído automaticamente.
"""
import argparse
import http.client
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

BASE_URL = (
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsas/ca"
)

# Exceções aos nomes padrão no site da ANP (conferido em nov/2026)
URLS_ESPECIAIS = {
    (2022, 1): f"{BASE_URL}/precos-semestrais-ca.zip",
}

TENTATIVAS = 5
TAMANHO_BLOCO = 1024 * 1024  # 1 MB


def url_semestre(ano: int, semestre: int) -> str:
    """Endereço do arquivo da ANP para um semestre (CSV até 2021, ZIP a partir de 2022)."""
    if (ano, semestre) in URLS_ESPECIAIS:
        return URLS_ESPECIAIS[(ano, semestre)]
    extensao = "csv" if ano <= 2021 else "zip"
    return f"{BASE_URL}/ca-{ano}-{semestre:02d}.{extensao}"


def nome_destino(ano: int, semestre: int) -> str:
    """Nome padronizado do CSV salvo em data/raw."""
    return f"ca-{ano}-{semestre:02d}.csv"


def semestres(inicio: int, fim: int) -> list[tuple[int, int]]:
    """Lista (ano, semestre) de ``inicio`` a ``fim``, inclusive."""
    if inicio > fim:
        raise ValueError("O ano inicial deve ser menor ou igual ao final.")
    return [(ano, semestre) for ano in range(inicio, fim + 1) for semestre in (1, 2)]


def baixar_arquivo(url: str, destino: Path) -> None:
    """Baixa ``url`` para ``destino``, retomando de onde parou se a conexão cair.

    O servidor da ANP às vezes encerra downloads grandes no meio; nesse caso o
    download continua a partir do último byte recebido (cabeçalho HTTP Range).
    """
    parcial = destino.with_name(destino.name + ".part")
    for tentativa in range(1, TENTATIVAS + 1):
        recebido = parcial.stat().st_size if parcial.exists() else 0
        pedido = urllib.request.Request(url, headers={"User-Agent": "projeto-anp/1.0"})
        if recebido:
            pedido.add_header("Range", f"bytes={recebido}-")
        try:
            with urllib.request.urlopen(pedido, timeout=60) as resposta:
                # 200 = servidor ignorou o Range e mandou o arquivo inteiro
                modo = "ab" if recebido and resposta.status == 206 else "wb"
                with open(parcial, modo) as saida:
                    while bloco := resposta.read(TAMANHO_BLOCO):
                        saida.write(bloco)
            parcial.replace(destino)
            return
        except urllib.error.HTTPError as erro:
            if erro.code == 416:  # já recebemos tudo
                parcial.replace(destino)
                return
            if erro.code < 500:
                raise
            motivo = erro
        except (
            urllib.error.URLError, http.client.HTTPException, ConnectionError, TimeoutError
        ) as erro:
            motivo = erro
        espera = 2 * tentativa
        print(f"    conexão interrompida ({motivo}); nova tentativa em {espera}s...")
        time.sleep(espera)
    raise RuntimeError(f"Não foi possível baixar {url} após {TENTATIVAS} tentativas.")


def extrair_csv(arquivo_zip: Path, destino: Path) -> None:
    """Extrai o único CSV de ``arquivo_zip`` para ``destino``."""
    with zipfile.ZipFile(arquivo_zip) as pacote:
        csvs = [nome for nome in pacote.namelist() if nome.lower().endswith(".csv")]
        if len(csvs) != 1:
            raise ValueError(f"Esperado 1 CSV em {arquivo_zip.name}, encontrados: {csvs}")
        with pacote.open(csvs[0]) as origem, open(destino, "wb") as saida:
            while bloco := origem.read(TAMANHO_BLOCO):
                saida.write(bloco)


def baixar_semestre(ano: int, semestre: int, pasta: Path) -> Path:
    """Baixa (e extrai, se for ZIP) um semestre. Devolve o caminho do CSV."""
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / nome_destino(ano, semestre)
    if destino.exists():
        print(f"  {destino.name}: já existe, pulando")
        return destino
    url = url_semestre(ano, semestre)
    print(f"  {destino.name}: baixando {url}")
    if url.endswith(".zip"):
        temporario = pasta / f"{destino.stem}.zip"
        baixar_arquivo(url, temporario)
        extrair_csv(temporario, destino)
        temporario.unlink()
    else:
        baixar_arquivo(url, destino)
    return destino


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Baixa os CSVs semestrais da ANP")
    parser.add_argument("--inicio", type=int, default=2021, help="ano inicial (padrão: 2021)")
    parser.add_argument("--fim", type=int, default=2025, help="ano final (padrão: 2025)")
    parser.add_argument("--pasta", type=Path, default=RAW, help="pasta de destino")
    args = parser.parse_args(argv)

    for ano, semestre in semestres(args.inicio, args.fim):
        try:
            baixar_semestre(ano, semestre, args.pasta)
        except Exception as erro:  # noqa: BLE001 - mostra o erro e encerra com código 1
            sys.exit(f"Erro ao baixar {ano}/{semestre}: {erro}")
    print(f"Pronto. Arquivos em {args.pasta}")


if __name__ == "__main__":
    main()
