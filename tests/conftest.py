"""Dados de exemplo pequenos, no mesmo formato dos CSVs da ANP."""
import pytest

CABECALHO = (
    "Regiao - Sigla;Estado - Sigla;Municipio;Revenda;CNPJ da Revenda;Nome da Rua;"
    "Numero Rua;Complemento;Bairro;Cep;Produto;Data da Coleta;Valor de Venda;"
    "Valor de Compra;Unidade de Medida;Bandeira"
)

LINHAS = [
    # regiao;uf;municipio;revenda;cnpj;rua;num;compl;bairro;cep;produto;data;venda;compra;unid;bandeira
    "SE;SP;SAO PAULO;POSTO A;00.000.000/0001-01;RUA X;1;;CENTRO;01000-000;GASOLINA;02/01/2024;5,79;;R$ / litro;RAIZEN",
    # duplicata exata da linha anterior
    "SE;SP;SAO PAULO;POSTO A;00.000.000/0001-01;RUA X;1;;CENTRO;01000-000;GASOLINA;02/01/2024;5,79;;R$ / litro;RAIZEN",
    "SE;SP;SAO PAULO;POSTO A;00.000.000/0001-01;RUA X;1;;CENTRO;01000-000;ETANOL;02/01/2024;3,49;;R$ / litro;RAIZEN",
    "S;PR;CURITIBA;POSTO B;00.000.000/0001-02;RUA Y;2;;CENTRO;80000-000;GNV;15/02/2024;4,99;;R$ / m3;BRANCA",
    "S;PR;CURITIBA;POSTO C;00.000.000/0001-03;RUA Z;3;;CENTRO;80000-001;GNV;20/02/2024;5,09;;R$ / m³;IPIRANGA",
    " NE ; ba ;SALVADOR;POSTO D;00.000.000/0001-04;RUA W;4;;CENTRO;40000-000; diesel s10 ;10/03/2024;6,10;;R$ / litro;VIBRA ",
    # sem valor de venda: deve ser descartada
    "SE;RJ;RIO DE JANEIRO;POSTO E;00.000.000/0001-05;RUA V;5;;CENTRO;20000-000;GASOLINA;11/03/2024;;;R$ / litro;SHELL",
    # data inválida: deve ser descartada
    "SE;RJ;RIO DE JANEIRO;POSTO E;00.000.000/0001-05;RUA V;5;;CENTRO;20000-000;GASOLINA;99/99/2024;6,00;;R$ / litro;SHELL",
    # linha totalmente vazia (como no final de um dos arquivos da ANP)
    ";;;;;;;;;;;;;;;",
]

# Após o tratamento: 9 lidas - 3 descartadas - 1 duplicada = 5
TOTAL_LIDAS = len(LINHAS)
TOTAL_FINAL = 5


@pytest.fixture
def pasta_raw(tmp_path):
    """Pasta com dois CSVs: um em UTF-8 com BOM e outro em latin1."""
    pasta = tmp_path / "raw"
    pasta.mkdir()
    texto_a = "\n".join([CABECALHO, *LINHAS[:4]]) + "\n"
    texto_b = "\n".join([CABECALHO, *LINHAS[4:]]) + "\n"
    (pasta / "a.csv").write_text(texto_a, encoding="utf-8-sig")
    (pasta / "b.csv").write_text(texto_b, encoding="latin1")
    return pasta


@pytest.fixture
def base(pasta_raw):
    """Base tratada a partir dos CSVs de exemplo."""
    from src.data_processing import carregar_csvs

    return carregar_csvs(pasta_raw, verbose=False)
