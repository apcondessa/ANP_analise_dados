import io
import urllib.error
import zipfile

import pytest

from src import download


def test_urls():
    assert download.url_semestre(2021, 2).endswith("/ca-2021-02.csv")
    assert download.url_semestre(2024, 1).endswith("/ca-2024-01.zip")
    # exceção do site da ANP
    assert download.url_semestre(2022, 1).endswith("/precos-semestrais-ca.zip")


def test_semestres():
    assert download.semestres(2021, 2022) == [(2021, 1), (2021, 2), (2022, 1), (2022, 2)]
    assert len(download.semestres(2021, 2025)) == 10
    with pytest.raises(ValueError):
        download.semestres(2025, 2021)


def test_extrair_csv(tmp_path):
    arquivo_zip = tmp_path / "x.zip"
    with zipfile.ZipFile(arquivo_zip, "w") as pacote:
        pacote.writestr("Preços semestrais.csv", "a;b\n1;2\n")
    destino = tmp_path / "ca-2024-01.csv"
    download.extrair_csv(arquivo_zip, destino)
    assert destino.read_text() == "a;b\n1;2\n"


def test_arquivo_existente_e_pulado(tmp_path, monkeypatch):
    (tmp_path / "ca-2023-01.csv").write_text("já baixado")

    def falha(*args, **kwargs):
        raise AssertionError("não deveria baixar")

    monkeypatch.setattr(download, "baixar_arquivo", falha)
    assert download.baixar_semestre(2023, 1, tmp_path).read_text() == "já baixado"


class _RespostaFalsa(io.BytesIO):
    def __init__(self, conteudo, status, cair_apos=None):
        super().__init__(conteudo)
        self.status = status
        self._cair_apos = cair_apos

    def read(self, n=-1):
        if self._cair_apos is not None and self.tell() >= self._cair_apos:
            raise ConnectionResetError("conexão encerrada pelo servidor")
        limite = n if self._cair_apos is None else min(n, self._cair_apos - self.tell())
        return super().read(limite)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_download_retoma_apos_queda(tmp_path, monkeypatch):
    conteudo = b"0123456789" * 100
    pedidos = []

    def urlopen_falso(pedido, timeout):
        intervalo = pedido.get_header("Range")
        pedidos.append(intervalo)
        if intervalo is None:
            return _RespostaFalsa(conteudo, 200, cair_apos=300)
        inicio = int(intervalo.split("=")[1].rstrip("-"))
        return _RespostaFalsa(conteudo[inicio:], 206)

    monkeypatch.setattr(download.urllib.request, "urlopen", urlopen_falso)
    monkeypatch.setattr(download.time, "sleep", lambda s: None)
    destino = tmp_path / "arquivo.csv"
    download.baixar_arquivo("https://exemplo/arquivo.csv", destino)

    assert destino.read_bytes() == conteudo
    assert pedidos == [None, "bytes=300-"]
    assert not (tmp_path / "arquivo.csv.part").exists()


def test_erro_404_nao_tenta_de_novo(tmp_path, monkeypatch):
    chamadas = []

    def urlopen_falso(pedido, timeout):
        chamadas.append(1)
        raise urllib.error.HTTPError(pedido.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(download.urllib.request, "urlopen", urlopen_falso)
    with pytest.raises(urllib.error.HTTPError):
        download.baixar_arquivo("https://exemplo/x.csv", tmp_path / "x.csv")
    assert len(chamadas) == 1
