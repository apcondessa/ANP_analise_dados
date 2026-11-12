"""Dashboard interativo de preços de combustíveis (dados da ANP, 2021–2025).

Para rodar, a partir da raiz do projeto:
    streamlit run dashboard/app.py
"""
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))  # permite importar logica.py

import logica  # noqa: E402

# Paleta categórica (ordem fixa, validada para daltonismo); a cor segue a entidade
CORES_REGIOES = {
    "Norte": "#2a78d6",
    "Nordeste": "#eb6834",
    "Centro-Oeste": "#1baf7a",
    "Sudeste": "#eda100",
    "Sul": "#e87ba4",
}
CORES_SERIE = [
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948",
]
COR_PRINCIPAL = "#2a78d6"
COR_COMPENSA = "#008300"
COR_NEUTRA = "#a3a29b"
MAX_ESTADOS_NO_GRAFICO = 8
ALTURA_LINHA = 26  # px por estado nos gráficos de barras
EIXO_CATEGORIAS = alt.Axis(labelOverlap=False, ticks=False, domain=False)

st.set_page_config(page_title="Preços de Combustíveis no Brasil", page_icon="⛽", layout="wide")


@st.cache_data
def carregar(pasta: str):
    return logica.carregar_precos(pasta), logica.carregar_bandeiras(pasta)


def reais(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def sem_formula(texto: str) -> str:
    """Escapa o "$": o Streamlit lê o texto entre dois "$" como fórmula matemática."""
    return texto.replace("$", "\\$")


def mes_ano(data) -> str:
    return pd.Timestamp(data).strftime("%m/%Y")


precos, bandeiras = carregar(str(logica.pasta_dados()))
meses = sorted(precos["mes"].unique())

# --------------------------------------------------------------------------- filtros
with st.sidebar:
    st.header("Filtros")
    produto = st.selectbox(
        "Combustível", list(logica.PRODUTOS), format_func=logica.PRODUTOS.get, index=0
    )
    nomes_regioes = st.multiselect(
        "Regiões", list(logica.REGIOES.values()), default=list(logica.REGIOES.values())
    )
    siglas_regioes = [s for s, nome in logica.REGIOES.items() if nome in nomes_regioes]
    estados_disponiveis = sorted(
        precos.loc[precos["regiao"].isin(siglas_regioes), "estado"].unique()
    )
    estados = st.multiselect("Estados", estados_disponiveis, default=estados_disponiveis)
    inicio, fim = st.select_slider(
        "Período", options=meses, value=(meses[0], meses[-1]), format_func=mes_ano
    )
    corrigir = False
    if logica.tem_ipca(precos):
        base_ipca = logica.mes_base_ipca(precos)
        corrigir = st.toggle(
            "Corrigir pela inflação (IPCA)",
            help=(
                f"Mostra todos os preços em reais de {mes_ano(base_ipca)}, para comparar "
                "períodos diferentes sem o efeito da inflação."
            ),
        )
        if corrigir:
            precos = logica.em_reais_corrigidos(precos)
    st.caption(
        "Fonte: ANP, série histórica de preços de combustíveis (2021–2025). "
        "Médias simples dos preços coletados. Inflação: IPCA (IBGE)."
    )

unidade = logica.unidade(produto)
descricao_valores = (
    f"preços em {unidade}, corrigidos pelo IPCA (R$ de {mes_ano(base_ipca)})"
    if corrigir
    else f"preços em {unidade} (valores nominais)"
)
nome_produto = logica.PRODUTOS[produto]
recorte = logica.filtrar(precos, [produto], estados, inicio, fim)

st.title("⛽ Preços de Combustíveis no Brasil")
st.caption(
    sem_formula(
        f"{nome_produto} · {len(estados)} estado(s) · {mes_ano(inicio)} a {mes_ano(fim)} · "
        f"{descricao_valores}"
    )
)

if recorte.empty:
    st.warning("Nenhum dado para os filtros escolhidos. Selecione ao menos um estado.")
    st.stop()

# --------------------------------------------------------------------------- indicadores
ind = logica.indicadores(recorte)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Preço médio no período", reais(ind["media"]), help=f"{ind['coletas']:,} coletas")
c2.metric(
    f"Variação {mes_ano(ind['mes_inicial'])} → {mes_ano(ind['mes_final'])}",
    reais(ind["media_final"]),
    f"{ind['variacao_pct']:+.1f}%".replace(".", ","),
    delta_color="inverse",
    help=(
        f"Média do primeiro mês: {reais(ind['media_inicial'])}. "
        "Alta de preço aparece em vermelho."
    ),
)
c3.metric(
    "Estado mais caro", ind["mais_caro"][0], reais(ind["mais_caro"][1]),
    delta_color="off", delta_arrow="off", help="Maior preço médio no período",
)
c4.metric(
    "Estado mais barato", ind["mais_barato"][0], reais(ind["mais_barato"][1]),
    delta_color="off", delta_arrow="off", help="Menor preço médio no período",
)

aba_evolucao, aba_estados, aba_etanol, aba_regioes, aba_dados = st.tabs(
    ["Evolução", "Estados", "Etanol x Gasolina", "Regiões", "Dados"]
)

eixo_mes = alt.X("mes:T", title="Mês", axis=alt.Axis(format="%m/%Y", grid=False))
tooltip_mes = alt.Tooltip("mes:T", title="Mês", format="%m/%Y")

# --------------------------------------------------------------------------- evolução
with aba_evolucao:
    opcao = st.radio(
        "Mostrar", ["Média dos estados selecionados", "Por região", "Por estado"],
        horizontal=True,
    )
    agrupar = {"Por região": "regiao", "Por estado": "estado"}.get(opcao)
    if agrupar == "estado" and len(estados) > MAX_ESTADOS_NO_GRAFICO:
        st.info(
            f"Selecione até {MAX_ESTADOS_NO_GRAFICO} estados no filtro para comparar por estado. "
            "Mostrando a média dos selecionados."
        )
        agrupar = None
    serie = logica.serie_mensal(recorte, agrupar)
    if agrupar == "regiao":
        dominio = [r for r in CORES_REGIOES if r in set(serie["grupo"])]
        escala = alt.Scale(domain=dominio, range=[CORES_REGIOES[r] for r in dominio])
    else:
        dominio = sorted(serie["grupo"].unique())
        escala = alt.Scale(domain=dominio, range=CORES_SERIE[: len(dominio)])
    legenda = alt.Legend(title=None, orient="top") if len(dominio) > 1 else None

    base = alt.Chart(serie).encode(
        x=eixo_mes,
        y=alt.Y("media:Q", title=f"Preço médio ({unidade})", scale=alt.Scale(zero=False)),
        color=alt.Color("grupo:N", scale=escala, legend=legenda),
    )
    hover = alt.selection_point(fields=["mes"], nearest=True, on="pointerover", empty=False)
    linhas = base.mark_line(strokeWidth=2)
    pontos = base.mark_point(size=60, filled=True).encode(
        opacity=alt.condition(hover, alt.value(1), alt.value(0)),
        tooltip=[
            tooltip_mes,
            alt.Tooltip("grupo:N", title=""),
            alt.Tooltip("media:Q", title=f"Preço médio ({unidade})", format=".2f"),
            alt.Tooltip("coletas:Q", title="Coletas", format=","),
        ],
    ).add_params(hover)
    regra = (
        alt.Chart(serie).mark_rule(color=COR_NEUTRA)
        .encode(x="mes:T").transform_filter(hover)
    )
    st.altair_chart((linhas + regra + pontos).properties(height=420), width="stretch")

# --------------------------------------------------------------------------- estados
with aba_estados:
    por_estado = logica.media_por(recorte, ["estado"]).sort_values("media", ascending=False)
    altura = max(260, ALTURA_LINHA * len(por_estado))
    barras = alt.Chart(por_estado).mark_bar(
        color=COR_PRINCIPAL, cornerRadiusEnd=4, height={"band": 0.8}
    ).encode(
        x=alt.X("media:Q", title=f"Preço médio ({unidade})", axis=alt.Axis(tickCount=8)),
        y=alt.Y("estado:N", sort=por_estado["estado"].tolist(), title=None, axis=EIXO_CATEGORIAS),
        tooltip=[
            alt.Tooltip("estado:N", title="Estado"),
            alt.Tooltip("media:Q", title="Preço médio", format=".2f"),
            alt.Tooltip("minimo:Q", title="Mínimo", format=".2f"),
            alt.Tooltip("maximo:Q", title="Máximo", format=".2f"),
            alt.Tooltip("coletas:Q", title="Coletas", format=","),
        ],
    )
    rotulos = barras.mark_text(align="left", dx=4, color="gray").encode(
        text=alt.Text("media:Q", format=".2f")
    )
    media_geral = alt.Chart(pd.DataFrame({"media": [ind["media"]]})).mark_rule(
        color=COR_NEUTRA, strokeDash=[4, 4]
    ).encode(x="media:Q")
    st.altair_chart(
        (barras + rotulos + media_geral).properties(height=altura), width="stretch"
    )
    st.caption(
        sem_formula(
            f"Linha tracejada: média dos estados selecionados ({reais(ind['media'])}). "
            "Estados com poucas coletas (veja na aba Dados) têm médias menos confiáveis."
        )
    )

# --------------------------------------------------------------------------- etanol x gasolina
with aba_etanol:
    razao = logica.razao_etanol_gasolina(
        logica.filtrar(precos, ["ETANOL", "GASOLINA"], estados, inicio, fim)
    )
    if razao.empty:
        st.info("Não há preços de etanol e gasolina para os filtros escolhidos.")
    else:
        compensa = int(razao["compensa"].sum())
        st.markdown(
            f"Pela regra prática, o etanol compensa quando custa **menos de 70%** do preço da "
            f"gasolina comum. No período escolhido, isso acontece em **{compensa} de "
            f"{len(razao)}** estados selecionados."
        )
        razao["situacao"] = razao["compensa"].map(
            {True: "Etanol compensa", False: "Gasolina compensa"}
        )
        razao["percentual"] = razao["razao"] * 100
        barras = alt.Chart(razao).mark_bar(cornerRadiusEnd=4, height={"band": 0.8}).encode(
            x=alt.X(
                "percentual:Q", title="Preço do etanol como % da gasolina",
                scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(tickCount=10),
            ),
            y=alt.Y("estado:N", sort=razao["estado"].tolist(), title=None, axis=EIXO_CATEGORIAS),
            color=alt.Color(
                "situacao:N", title=None, legend=alt.Legend(orient="top"),
                scale=alt.Scale(
                    domain=["Etanol compensa", "Gasolina compensa"],
                    range=[COR_COMPENSA, COR_NEUTRA],
                ),
            ),
            tooltip=[
                alt.Tooltip("estado:N", title="Estado"),
                alt.Tooltip("etanol:Q", title="Etanol (R$/litro)", format=".2f"),
                alt.Tooltip("gasolina:Q", title="Gasolina (R$/litro)", format=".2f"),
                alt.Tooltip("percentual:Q", title="Etanol / gasolina (%)", format=".1f"),
                alt.Tooltip("situacao:N", title="Situação"),
            ],
        )
        rotulos = barras.mark_text(align="left", dx=4, color="gray").encode(
            text=alt.Text("percentual:Q", format=".1f"), color=alt.value("gray")
        )
        limite = alt.Chart(pd.DataFrame({"x": [70]})).mark_rule(
            color="#e34948", strokeDash=[4, 4], strokeWidth=2
        ).encode(x="x:Q")
        st.altair_chart(
            (barras + rotulos + limite).properties(height=max(260, ALTURA_LINHA * len(razao))),
            width="stretch",
        )
        st.caption(
            "Linha tracejada vermelha: limite de 70%. "
            "O resultado não depende do combustível escolhido no filtro."
        )

# --------------------------------------------------------------------------- regiões
with aba_regioes:
    regioes = logica.media_por(recorte, ["regiao"])
    regioes["nome"] = regioes["regiao"].map(logica.REGIOES)
    regioes = regioes.sort_values("media", ascending=False)
    dominio = [r for r in CORES_REGIOES if r in set(regioes["nome"])]
    barras = alt.Chart(regioes).mark_bar(cornerRadiusEnd=4, height={"band": 0.7}).encode(
        x=alt.X("media:Q", title=f"Preço médio ({unidade})", axis=alt.Axis(tickCount=8)),
        y=alt.Y("nome:N", sort=regioes["nome"].tolist(), title=None, axis=EIXO_CATEGORIAS),
        color=alt.Color(
            "nome:N", legend=None,
            scale=alt.Scale(domain=dominio, range=[CORES_REGIOES[r] for r in dominio]),
        ),
        tooltip=[
            alt.Tooltip("nome:N", title="Região"),
            alt.Tooltip("media:Q", title="Preço médio", format=".2f"),
            alt.Tooltip("coletas:Q", title="Coletas", format=","),
        ],
    )
    rotulos = barras.mark_text(align="left", dx=4, color="gray").encode(
        text=alt.Text("media:Q", format=".2f"), color=alt.value("gray")
    )
    st.altair_chart((barras + rotulos).properties(height=260), width="stretch")

# --------------------------------------------------------------------------- dados
with aba_dados:
    anos = sorted({pd.Timestamp(m).year for m in (inicio, fim)})
    tabela = logica.tabela_estados(recorte, bandeiras, anos)
    st.dataframe(
        tabela,
        hide_index=True,
        width="stretch",
        column_config={
            "estado": "Estado",
            "regiao": "Região",
            "media": st.column_config.NumberColumn(f"Média ({unidade})", format="%.2f"),
            "minimo": st.column_config.NumberColumn("Mínimo", format="%.2f"),
            "maximo": st.column_config.NumberColumn("Máximo", format="%.2f"),
            "coletas": st.column_config.NumberColumn("Coletas", format="%d"),
            tabela.columns[-1]: st.column_config.NumberColumn(
                f"Bandeiras ({max(anos)})", format="%d"
            ),
        },
    )
    st.download_button(
        "Baixar tabela (CSV)",
        tabela.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        file_name=f"precos_{produto.lower().replace(' ', '_')}_por_estado.csv",
        mime="text/csv",
    )
