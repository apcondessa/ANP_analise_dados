# Projeto ANP — Análise de Preços de Combustíveis

Projeto de **Data Analytics** desenvolvido para explorar dados de preços de combustíveis comercializados no Brasil, com foco em análise exploratória, estatística descritiva e visualização.

A base utilizada é composta por arquivos disponibilizados pela **Agência Nacional do Petróleo, Gás Natural e Biocombustíveis (ANP)**. O projeto organiza os dados brutos, prepara uma base para análise e gera indicadores e visualizações sobre preços, produtos, estados e bandeiras.

## Objetivos

- Organizar e tratar os dados de preços de combustíveis.
- Analisar a distribuição dos valores de venda.
- Comparar preços entre estados e produtos.
- Avaliar a evolução dos preços ao longo do período disponível.
- Identificar a quantidade de bandeiras distintas por estado.
- Criar visualizações que facilitem a interpretação dos dados.

## Resultados

| Evolução do preço por produto | Bandeiras por estado |
|---|---|
| ![Evolução dos preços](outputs/grafico_produto_data_coleta_valor_venda.png) | ![Bandeiras por estado](outputs/quantidade_bandeiras_por_estado.png) |

## Produtos analisados

- Gasolina (comum)
- Gasolina aditivada
- Diesel
- Diesel S10
- Etanol
- GNV

> A disponibilidade de cada produto depende dos registros presentes nos arquivos da ANP utilizados no projeto.

## Tecnologias

- Python
- Pandas
- Matplotlib
- Seaborn
- PostgreSQL (apenas no notebook `Geracao_insights.ipynb`)
- Jupyter Notebook
- Git/GitHub

## Estrutura do projeto

```text
ANP_analise_dados/
│
├── data/
│   ├── raw/                         # CSVs originais da ANP (não versionados)
│   └── processed/                   # Base tratada (gerada pelo src, não versionada)
│       └── dados_anp_tratados.pkl
│
├── notebooks/
│   ├── Geracao_insights.ipynb       # Análise exploratória e indicadores
│   └── Tecnicas_visualizacao.ipynb  # Visualizações
│
├── outputs/                         # Gráficos gerados (PNG)
│
├── sql/                             # Reservada para scripts SQL (ainda vazia)
│
├── src/                             # Código Python reutilizável
│   ├── __init__.py
│   ├── analysis.py                  # Estatísticas descritivas
│   ├── data_processing.py           # Leitura e tratamento dos CSVs
│   ├── main.py                      # Executa o fluxo completo
│   └── visualization.py             # Gráficos
│
├── requirements/
│   └── requirements.txt
│
├── .env.example                 # Modelo das variáveis do banco (copie para .env)
├── .gitignore
└── README.md
```

## Requisitos

- **Python 3.11 ou superior** (o projeto foi desenvolvido com Python 3.14).
- Cerca de **2,5 GB de memória RAM livre** (pico medido: 2,0 GB) e **1 GB de disco** para os dados brutos.

## Obtendo os dados

Os CSVs da ANP **não estão neste repositório** (somam cerca de 750 MB). Para reproduzir o projeto:

1. Acesse a série histórica de preços de combustíveis da ANP:
   <https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis>
2. Baixe os **10 arquivos semestrais de 2021 a 2025** (1º e 2º semestre de cada ano), na seção de combustíveis automotivos. A partir de 2022 os arquivos vêm compactados (`.zip`): extraia o CSV de cada um. Atenção: o link do **1º semestre de 2022** se chama `precos-semestrais-ca.zip` (e não `ca-2022-01`).
3. Coloque os arquivos, sem alterar o conteúdo, na pasta `data/raw/`. O nome dos arquivos não importa: o código lê todos os `*.csv` da pasta.

> Os números deste projeto foram obtidos com esses 10 arquivos. Usar outro período, ou repetir um semestre, altera os resultados.

Formato esperado dos CSVs: separador `;`, decimal com vírgula, datas `dd/mm/aaaa`. O código aceita arquivos em UTF-8 (com ou sem BOM) e em latin1.

## Como executar

### 1. Clonar o repositório

```bash
git clone https://github.com/apcondessa/ANP_analise_dados.git
cd ANP_analise_dados
```

### 2. Criar e ativar o ambiente virtual

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Windows (CMD):

```cmd
python -m venv .venv
.venv\Scripts\activate
```

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar as dependências

```bash
pip install -r requirements/requirements.txt
```

### 4. Colocar os dados

Siga a seção [Obtendo os dados](#obtendo-os-dados) e deixe os CSVs em `data/raw/`.

### 5. Executar

Na raiz do projeto:

```bash
python src/main.py
```

O script irá:

1. ler os CSVs presentes em `data/raw/`;
2. tratar os dados;
3. salvar a base em `data/processed/dados_anp_tratados.pkl`;
4. apresentar estatísticas por produto e ano;
5. apresentar a quantidade de bandeiras por estado.

Para **também gerar todos os gráficos** em `outputs/`:

```bash
python src/main.py --graficos
```

O fluxo completo, com os gráficos, leva cerca de 1 minuto. Ele gera 14 imagens PNG:

- `<produto>_valor_venda.png`: boxplot geral de cada um dos 6 produtos;
- `<produto>_valor_venda_por_estado.png`: boxplot por estado de cada produto;
- `quantidade_bandeiras_por_estado.png`;
- `grafico_produto_data_coleta_valor_venda.png`.

### Resultado esperado

Ao final da etapa de preparação, o script informa algo como:

```text
4,331,306 linhas lidas em 10 arquivos | 9,114 descartadas (linhas vazias ou sem data/produto/valor) | 10 duplicadas removidas
Base tratada: 4,322,182 linhas x 11 colunas
```

As 9.114 linhas descartadas são linhas totalmente vazias no final de um dos arquivos da ANP. As 10 duplicadas são registros idênticos (mesmo posto, produto, data e preço) que aparecem duas vezes. Se você obtiver esses mesmos totais, a base foi reproduzida corretamente.

## Fluxo de dados

```text
Dados brutos da ANP (CSV)
        ↓
data/raw/
        ↓
src/data_processing.py   (leitura, tratamento e padronização)
        ↓
data/processed/dados_anp_tratados.pkl
        ↓
src/analysis.py          (estatísticas descritivas)
        ↓
src/visualization.py     (gráficos)
        ↓
outputs/
```

## Preparação dos dados

O módulo `src/data_processing.py` concentra as etapas de preparação da base:

- leitura dos arquivos CSV (apenas as colunas necessárias, para economizar memória);
- tratamento de diferentes encodings e remoção do BOM;
- padronização dos nomes das colunas;
- seleção das variáveis utilizadas na análise;
- conversão da data de coleta;
- conversão do valor de venda para formato numérico;
- padronização de produto, estado e bandeira;
- remoção de registros sem informações essenciais;
- remoção de registros duplicados;
- padronização da unidade de medida (o GNV é vendido em R$/m³; os demais combustíveis, em R$/litro);
- criação das variáveis `ano` e `mes`;
- armazenamento da base tratada em Pickle.

Exemplo de uso no Python (a partir da raiz do projeto):

```python
from src.data_processing import carregar_csvs, salvar_pickle

df = carregar_csvs("data/raw")
salvar_pickle(df, "data/processed/dados_anp_tratados.pkl")
```

Colunas da base tratada: `data_coleta`, `regiao`, `estado`, `municipio`, `cnpj` (do posto), `bandeira`, `produto`, `valor_venda`, `unidade`, `ano`, `mes`.

## Análises realizadas

O módulo `src/analysis.py` disponibiliza funções para:

### Estatística por produto e ano

Calcula valor mínimo, máximo e médio.

```python
from src.analysis import estatistica_por_produto

resultado = estatistica_por_produto(df)
```

### Estatística por estado

Permite comparar mínimo, máximo e média dos preços por produto, ano e estado.

```python
from src.analysis import estatistica_por_estado

resultado = estatistica_por_estado(df)
```

### Bandeiras por estado

Conta a quantidade de bandeiras distintas identificadas em cada estado.

```python
from src.analysis import bandeiras_por_estado

resultado = bandeiras_por_estado(df)
```

## Visualizações

O módulo `src/visualization.py` reúne funções para geração de gráficos:

- evolução do preço médio mensal por produto, com o GNV (R$/m³) em painel separado dos combustíveis líquidos (R$/litro);
- boxplot geral e por estado de cada produto, com a unidade no título, os estados ordenados pela mediana do preço e o número de coletas de cada estado;
- quantidade de bandeiras por estado.

Quando uma pasta de saída é informada, o gráfico é salvo em PNG e a figura é fechada.

```python
from src.analysis import bandeiras_por_estado
from src.visualization import (
    boxplot_produto_estado,
    boxplot_produto_geral,
    grafico_bandeiras_estado,
    linha_precos_por_produto,
)

boxplot_produto_estado(df, "DIESEL S10", "outputs")
boxplot_produto_geral(df, "DIESEL S10", "outputs")
grafico_bandeiras_estado(bandeiras_por_estado(df), "outputs")
linha_precos_por_produto(df, "outputs")
```

## Notebooks

Os notebooks documentam a exploração original. **O fluxo reproduzível está no `src/`**; os notebooks são material de apoio e têm particularidades do ambiente onde foram criados:

### `Geracao_insights.ipynb`

Exploração dos dados e geração de indicadores: dimensão da base, tipos das variáveis, valores ausentes, produtos disponíveis, anos e meses, estatística descritiva, preços por produto e por estado e quantidade de bandeiras.

Este notebook lê os dados de um banco **PostgreSQL 17** local (banco `ANP`, tabela `anp.preco_combustivel`), e não diretamente dos CSVs. O banco não faz parte do repositório e os scripts de criação/carga ainda não foram adicionados à pasta `sql/`. Para executá-lo é preciso montar esse banco e definir as variáveis de ambiente `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` e `DB_PORT` (veja o modelo em `.env.example`). A senha (`DB_PASSWORD`) é obrigatória e nunca fica escrita no notebook. Execute o notebook a partir da pasta `notebooks/`: a base tratada é salva em `data/processed/`. **Quem apenas quer reproduzir a base e as análises não precisa de PostgreSQL:** o `src/` faz o mesmo a partir dos CSVs.

### `Tecnicas_visualizacao.ipynb`

Técnicas de visualização: séries temporais, boxplots, comparações por estado, gráficos de barras e análise da quantidade de bandeiras. Lê o arquivo `data/processed/dados_anp_tratados.pkl`, que é gerado por `python src/main.py`. Para executá-lo, é necessário instalar o Jupyter (`pip install jupyter`) e abrir o notebook a partir da pasta `notebooks/` (os caminhos são relativos a ela).

## Possíveis próximos passos

- Adicionar à pasta `sql/` os scripts de criação do banco e de carga dos CSVs;
- criar uma camada de ingestão automatizada dos arquivos da ANP;
- separar configuração e credenciais do código;
- criar pipeline ETL/ELT;
- adicionar testes de qualidade dos dados;
- criar análises de variação percentual dos preços;
- analisar médias por região;
- identificar estados com maior amplitude de preços;
- criar um dashboard em Power BI ou Streamlit;
- automatizar a atualização dos dados.

## Projeto para portfólio

Este projeto demonstra competências em:

**Python | Pandas | Análise Exploratória | Estatística Descritiva | Data Visualization | Seaborn | Matplotlib | PostgreSQL | Jupyter Notebook | Organização de código**

O objetivo da organização em `src/` é separar a lógica reutilizável dos notebooks, tornando o projeto mais próximo de uma estrutura utilizada em projetos profissionais de dados.
