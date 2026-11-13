import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(
    page_title="Datathon SC | Mercado de Trabalho & Gargalos",
    page_icon="📊",
    layout="wide"
)

@st.cache_data
def carregar_dados():
    df = pd.read_csv('Base_Dashboard_Otimizada.csv.gz', sep=';', compression='gzip')
    df['nome_setor'] = df['nome_setor'].replace({'Z': 'Não Identificado'})
    return df

try:
    df = carregar_dados()
except FileNotFoundError:
    st.error("Arquivo 'Base_Dashboard_Otimizada.csv.gz' não encontrado. Rode primeiro 'python otimizar_base.py'.")
    st.stop()

# =====================================================================
# BARRA LATERAL (FILTROS INTERATIVOS)
# =====================================================================
st.sidebar.header("Filtros Analíticos")

sel_municipios = st.sidebar.multiselect("Municípios (SC)", sorted(df['nome_municipio'].dropna().unique()))
sel_setores = st.sidebar.multiselect("Setor Econômico (CNAE)", sorted(df['nome_setor'].dropna().unique()))
sel_macro = st.sidebar.multiselect("Macrofamília de Cargo (IA/CBO)", sorted(df['macrofamilia'].dropna().unique()))
sel_qualif = st.sidebar.multiselect("Nível de Qualificação", sorted(df['nivel_qualificacao'].dropna().unique()))

df_filtrado = df.copy()
if sel_municipios:
    df_filtrado = df_filtrado[df_filtrado['nome_municipio'].isin(sel_municipios)]
if sel_setores:
    df_filtrado = df_filtrado[df_filtrado['nome_setor'].isin(sel_setores)]
if sel_macro:
    df_filtrado = df_filtrado[df_filtrado['macrofamilia'].isin(sel_macro)]
if sel_qualif:
    df_filtrado = df_filtrado[df_filtrado['nivel_qualificacao'].isin(sel_qualif)]

if df_filtrado.empty:
    st.warning("Nenhum registro encontrado para a combinação de filtros selecionada.")
    st.stop()

# =====================================================================
# CABEÇALHO E KPIs ESTRATÉGICOS ESSENCIAIS (4 KPIs)
# =====================================================================
st.title("Monitor Estratégico de Emprego e Gargalos — Santa Catarina")
st.caption("Análise integrada Novo CAGED + IBGE + Enriquecimento de CBOs por Macrofamílias")

admissoes = int(df_filtrado['admissoes'].sum())
demissoes = int(df_filtrado['demissoes'].sum())
saldo_liquido = admissoes - demissoes

pop_total = df_filtrado[['municipio_codigo', 'populacao']].drop_duplicates()['populacao'].sum()
saldo_10k = (saldo_liquido / pop_total * 10000) if pop_total > 0 else 0

qtd_adm = df_filtrado['qtd_sal_adm'].sum()
qtd_dem = df_filtrado['qtd_sal_dem'].sum()
salario_adm = (df_filtrado['soma_sal_adm'].sum() / qtd_adm) if qtd_adm > 0 else 0
salario_dem = (df_filtrado['soma_sal_dem'].sum() / qtd_dem) if qtd_dem > 0 else 0
gap_salarial = ((salario_adm - salario_dem) / salario_dem * 100) if salario_dem > 0 else 0
turnover_pct = (demissoes / admissoes * 100) if admissoes > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Saldo Líquido de Vagas",
    f"{saldo_liquido:+,.0f}".replace(",", "."),
    f"{admissoes:,} adm / {demissoes:,} dem".replace(",", ".")
)
col2.metric(
    "Saldo / 10 mil Habitantes",
    f"{saldo_10k:,.1f}".replace(",", "."),
    "Métrica normalizada por porte"
)
col3.metric(
    "Salário Médio de Admissão",
    f"R$ {salario_adm:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
    f"{gap_salarial:+.1f}% vs. demissão"
)
col4.metric(
    "Índice de Rotatividade (Turnover)",
    f"{turnover_pct:.1f}%",
    "Demissões / Admissões"
)

st.divider()

# =====================================================================
# ABAS DOS 3 EIXOS ANALÍTICOS + DIAGNÓSTICO DE GARGALOS
# =====================================================================
aba1, aba2, aba3 = st.tabs([
    "1. Territorial e Setorial",
    "2. Perfil Socioeconômico (Salário & Turnover)",
    "3. Qualificação e Gargalos (IA / CBO)"
])

# --- EIXO 1: TERRITORIAL E SETORIAL ---
with aba1:
    qtd_mun = df_filtrado['nome_municipio'].nunique()
    comparar_cidades = st.toggle(
        "Modo Comparativo entre Municípios (separa setores e curvas mensais por cidade)",
        value=(1 < qtd_mun <= 6),
        help="Quando ativado, exibe barras agrupadas por município no gráfico de setores e linhas individuais na evolução mensal."
    )

    c1, c2 = st.columns(2)
    with c1:
        df_mun = df_filtrado.groupby(['municipio_codigo', 'nome_municipio', 'populacao'], as_index=False).agg(
            admissoes=('admissoes', 'sum'),
            demissoes=('demissoes', 'sum')
        )
        df_mun['saldo_vagas'] = df_mun['admissoes'] - df_mun['demissoes']
        df_mun['saldo_10k'] = (df_mun['saldo_vagas'] / df_mun['populacao']) * 10000

        if qtd_mun == 1:
            titulo_mun = f"Saldo por 10k Habitantes — {df_mun['nome_municipio'].iloc[0]}"
            top_mun = df_mun
        elif qtd_mun <= 15:
            titulo_mun = f"Comparativo ({qtd_mun} Municípios) — Saldo por 10k Hab"
            top_mun = df_mun.sort_values('saldo_10k', ascending=False)
        else:
            titulo_mun = "Top 15 Municípios — Saldo por 10k Habitantes"
            top_mun = df_mun.sort_values('saldo_10k', ascending=False).head(15)

        st.subheader(titulo_mun)
        fig_mun = px.bar(
            top_mun.sort_values('saldo_10k', ascending=True),
            x='saldo_10k',
            y='nome_municipio',
            orientation='h',
            color='saldo_vagas',
            color_continuous_scale='Blues',
            labels={'saldo_10k': 'Saldo / 10k Hab', 'nome_municipio': 'Município', 'saldo_vagas': 'Saldo Absoluto'}
        )
        if qtd_mun > 1:
            media_10k = df_mun['saldo_10k'].mean()
            fig_mun.add_vline(
                x=media_10k,
                line_dash="dash",
                line_color="#ff7f0e",
                annotation_text=f"Média: {media_10k:.1f}",
                annotation_position="top right"
            )
        st.plotly_chart(fig_mun, width='stretch')

    with c2:
        if comparar_cidades:
            st.subheader("Comparativo Setorial por Município (Saldo Líquido)")
            cidades_comp = (
                df_mun.sort_values('saldo_vagas', ascending=False).head(5)['nome_municipio'].tolist()
                if qtd_mun > 6 else df_mun['nome_municipio'].tolist()
            )
            df_set = df_filtrado[df_filtrado['nome_municipio'].isin(cidades_comp)].groupby(
                ['nome_setor', 'nome_municipio'], as_index=False
            ).agg(admissoes=('admissoes', 'sum'), demissoes=('demissoes', 'sum'))
            df_set['saldo_vagas'] = df_set['admissoes'] - df_set['demissoes']
            df_set = df_set.sort_values('saldo_vagas', ascending=True)

            fig_set = px.bar(
                df_set,
                x='saldo_vagas',
                y='nome_setor',
                color='nome_municipio',
                barmode='group',
                orientation='h',
                labels={'saldo_vagas': 'Saldo Líquido', 'nome_setor': 'Setor Econômico', 'nome_municipio': 'Município'}
            )
        else:
            st.subheader("Expansão vs. Encolhimento por Setor (CNAE)")
            df_set = df_filtrado.groupby('nome_setor', as_index=False).agg(
                admissoes=('admissoes', 'sum'),
                demissoes=('demissoes', 'sum')
            )
            df_set['saldo_vagas'] = df_set['admissoes'] - df_set['demissoes']
            df_set['status'] = df_set['saldo_vagas'].apply(lambda x: 'Expansão' if x >= 0 else 'Encolhimento')
            df_set = df_set.sort_values('saldo_vagas', ascending=True)

            fig_set = px.bar(
                df_set,
                x='saldo_vagas',
                y='nome_setor',
                orientation='h',
                color='status',
                color_discrete_map={'Expansão': '#1f77b4', 'Encolhimento': '#d62728'},
                labels={'saldo_vagas': 'Saldo Líquido de Vagas', 'nome_setor': 'Setor Econômico'}
            )
        st.plotly_chart(fig_set, width='stretch')

    st.divider()
    st.subheader("Projeção de Sazonalidade: Evolução Mensal (Janela de 12 Meses)")

    if 'competênciamov' in df_filtrado.columns:
        st.info(
            "**Nota Metodológica e Limite da Análise:** Como a base fornecida contempla apenas os últimos 12 meses de movimentações, "
            "a curva abaixo representa uma **projeção/indicativo de comportamento sazonal** (oscilações intranuais). "
            "Para validar estatisticamente um padrão sazonal recorrente, seria necessária a incorporação de séries históricas de anos anteriores."
        )

        if comparar_cidades:
            cidades_comp = (
                df_mun.sort_values('saldo_vagas', ascending=False).head(5)['nome_municipio'].tolist()
                if qtd_mun > 6 else df_mun['nome_municipio'].tolist()
            )
            df_tempo = df_filtrado[df_filtrado['nome_municipio'].isin(cidades_comp)].dropna(
                subset=['competênciamov']
            ).groupby(['competênciamov', 'nome_municipio'], as_index=False).agg(
                Admissões=('admissoes', 'sum'),
                Demissões=('demissoes', 'sum')
            )
            df_tempo['Saldo Líquido'] = df_tempo['Admissões'] - df_tempo['Demissões']
            comp_str = df_tempo['competênciamov'].astype(str).str.replace(r'\.0$', '', regex=True)
            df_tempo['Competência'] = pd.to_datetime(comp_str, format='%Y%m').dt.strftime('%Y-%m')
            df_tempo = df_tempo.sort_values('Competência')

            fig_tempo = px.line(
                df_tempo,
                x='Competência',
                y='Saldo Líquido',
                color='nome_municipio',
                markers=True,
                labels={'Competência': 'Mês de Referência', 'Saldo Líquido': 'Saldo Líquido de Vagas', 'nome_municipio': 'Município'}
            )
        else:
            df_tempo = df_filtrado.dropna(subset=['competênciamov']).groupby('competênciamov', as_index=False).agg(
                Admissões=('admissoes', 'sum'),
                Demissões=('demissoes', 'sum')
            )
            df_tempo['Saldo Líquido'] = df_tempo['Admissões'] - df_tempo['Demissões']
            comp_str = df_tempo['competênciamov'].astype(str).str.replace(r'\.0$', '', regex=True)
            df_tempo['Competência'] = pd.to_datetime(comp_str, format='%Y%m').dt.strftime('%Y-%m')
            df_tempo = df_tempo.sort_values('Competência')

            fig_tempo = px.line(
                df_tempo,
                x='Competência',
                y=['Admissões', 'Demissões', 'Saldo Líquido'],
                markers=True,
                color_discrete_map={
                    'Admissões': '#1f77b4',
                    'Demissões': '#d62728',
                    'Saldo Líquido': '#2ca02c'
                },
                labels={'Competência': 'Mês de Referência', 'value': 'Quantidade de Vínculos', 'variable': 'Indicador'}
            )

        fig_tempo.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.6)
        st.plotly_chart(fig_tempo, width='stretch')

# --- EIXO 2: PERFIL SOCIOECONÔMICO ---
with aba2:
    st.subheader("Diagnóstico de Atratividade: Salário Médio vs. Rotatividade (Turnover)")
    st.caption("Setores no quadrante inferior direito sofrem com baixa atratividade salarial e alta rotatividade.")

    df_socio = df_filtrado.groupby('nome_setor', as_index=False).agg(
        admissoes=('admissoes', 'sum'),
        demissoes=('demissoes', 'sum'),
        soma_sal=('soma_sal_total', 'sum'),
        qtd_sal=('qtd_sal_total', 'sum')
    )
    df_socio = df_socio[df_socio['admissoes'] > 0]
    df_socio['salario_medio'] = np.where(df_socio['qtd_sal'] > 0, df_socio['soma_sal'] / df_socio['qtd_sal'], 0)
    df_socio['turnover'] = (df_socio['demissoes'] / df_socio['admissoes']) * 100
    df_socio['movimentacao_total'] = df_socio['admissoes'] + df_socio['demissoes']

    fig_scatter = px.scatter(
        df_socio,
        x='turnover',
        y='salario_medio',
        size='movimentacao_total',
        color='nome_setor',
        hover_name='nome_setor',
        labels={
            'turnover': 'Índice de Rotatividade — Demissões/Admissões (%)',
            'salario_medio': 'Salário Médio (R$)',
            'movimentacao_total': 'Volume Total'
        }
    )
    fig_scatter.add_hline(y=df_socio['salario_medio'].median(), line_dash="dash", line_color="gray")
    fig_scatter.add_vline(x=df_socio['turnover'].median(), line_dash="dash", line_color="gray")
    st.plotly_chart(fig_scatter, width='stretch')

    st.subheader("Saldo Líquido e Salário Médio por Escolaridade")
    df_esc = df_filtrado.groupby('escolaridade_desc', as_index=False).agg(
        admissoes=('admissoes', 'sum'),
        demissoes=('demissoes', 'sum'),
        soma_sal=('soma_sal_total', 'sum'),
        qtd_sal=('qtd_sal_total', 'sum')
    )
    df_esc['salario_medio'] = np.where(df_esc['qtd_sal'] > 0, df_esc['soma_sal'] / df_esc['qtd_sal'], 0)
    df_esc['saldo_vagas'] = df_esc['admissoes'] - df_esc['demissoes']
    df_esc = df_esc.sort_values('saldo_vagas', ascending=False)
    st.dataframe(
        df_esc[['escolaridade_desc', 'admissoes', 'demissoes', 'saldo_vagas', 'salario_medio']].style.format({
            'salario_medio': 'R$ {:,.2f}',
            'admissoes': '{:,}',
            'demissoes': '{:,}',
            'saldo_vagas': '{:+,}'
        }),
        width='stretch',
        hide_index=True
    )

# --- EIXO 3: QUALIFICAÇÃO E GARGALOS (IA / CBO 2002) ---
with aba3:
    c1, c2 = st.columns([3, 2])

    with c1:
        st.subheader("Saldo Líquido por Macrofamília de Ocupação (IA)")
        df_macro = df_filtrado.groupby(['macrofamilia', 'nivel_qualificacao'], as_index=False).agg(
            admissoes=('admissoes', 'sum'),
            demissoes=('demissoes', 'sum')
        )
        df_macro['saldo_vagas'] = df_macro['admissoes'] - df_macro['demissoes']
        df_macro = df_macro.sort_values('saldo_vagas', ascending=True)

        fig_macro = px.bar(
            df_macro,
            x='saldo_vagas',
            y='macrofamilia',
            color='nivel_qualificacao',
            orientation='h',
            labels={
                'saldo_vagas': 'Saldo Líquido de Vagas',
                'macrofamilia': 'Macrofamília (CBO 2002)',
                'nivel_qualificacao': 'Nível de Qualificação'
            }
        )
        fig_macro.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.6)
        st.plotly_chart(fig_macro, width='stretch')

    with c2:
        st.subheader("Balanço por Nível de Qualificação")
        df_niv = df_filtrado.groupby('nivel_qualificacao', as_index=False).agg(
            Admissões=('admissoes', 'sum'),
            Demissões=('demissoes', 'sum')
        )
        df_niv['Saldo Líquido'] = df_niv['Admissões'] - df_niv['Demissões']
        df_niv = df_niv.sort_values('Saldo Líquido', ascending=False)

        fig_niv = px.bar(
            df_niv,
            x='nivel_qualificacao',
            y=['Admissões', 'Demissões', 'Saldo Líquido'],
            barmode='group',
            color_discrete_map={
                'Admissões': '#1f77b4',
                'Demissões': '#d62728',
                'Saldo Líquido': '#2ca02c'
            },
            labels={
                'nivel_qualificacao': 'Nível de Qualificação',
                'value': 'Quantidade de Vínculos',
                'variable': 'Indicador'
            }
        )
        st.plotly_chart(fig_niv, width='stretch')

    st.divider()
    st.subheader("Diagnóstico Executivo e Recomendações Práticas (IA / CBO 2002)")

    df_rec = df_filtrado.groupby(['macrofamilia', 'nivel_qualificacao'], as_index=False).agg(
        admissoes=('admissoes', 'sum'),
        demissoes=('demissoes', 'sum'),
        soma_sal=('soma_sal_adm', 'sum'),
        qtd_sal=('qtd_sal_adm', 'sum')
    )
    df_rec['saldo'] = df_rec['admissoes'] - df_rec['demissoes']
    df_rec['turnover'] = (df_rec['demissoes'] / df_rec['admissoes'].replace(0, float('nan'))) * 100
    df_rec['salario_medio'] = df_rec['soma_sal'] / df_rec['qtd_sal'].replace(0, float('nan'))

    if not df_rec.empty and df_rec['admissoes'].sum() > 0:
        # 1. Macrofamília com maior geração líquida de vagas
        top_demanda = df_rec.sort_values('saldo', ascending=False).iloc[0]

        # 2. Macrofamília com maior rotatividade (entre as que têm volume relevante)
        corte_vol = df_rec['admissoes'].median()
        df_vol = df_rec[df_rec['admissoes'] >= corte_vol]
        top_turn = df_vol.sort_values('turnover', ascending=False).iloc[0] if not df_vol.empty else top_demanda

        # 3. Nível de qualificação predominante no saldo positivo
        df_nivel = df_rec[df_rec['saldo'] > 0].groupby('nivel_qualificacao', as_index=False)['saldo'].sum()
        top_nivel = (
            df_nivel.sort_values('saldo', ascending=False).iloc[0]['nivel_qualificacao']
            if not df_nivel.empty else "Operacional / Base"
        )

        with st.container(border=True):
            col_r1, col_r2, col_r3 = st.columns(3)

            with col_r1:
                st.markdown("#### Gargalo de Expansão")
                st.success(
                    f"**Foco:** {top_demanda['macrofamilia']} ({top_demanda['nivel_qualificacao']})\n\n"
                    f"**Evidência:** Saldo líquido de **{int(top_demanda['saldo']):+,}** vagas no recorte.\n\n"
                    f"**Ação:** Priorizar trilhas rápidas de qualificação técnica (SENAI) e parcerias locais para suprir a demanda."
                )

            with col_r2:
                st.markdown("#### Alerta de Rotatividade")
                sal_txt = f"R$ {top_turn['salario_medio']:,.2f}" if pd.notna(top_turn['salario_medio']) else "N/D"
                turn_txt = f"{top_turn['turnover']:.1f}%" if pd.notna(top_turn['turnover']) else "N/D"
                st.warning(
                    f"**Foco:** {top_turn['macrofamilia']}\n\n"
                    f"**Evidência:** Turnover de **{turn_txt}** com salário médio de admissão de **{sal_txt}**.\n\n"
                    f"**Ação:** Revisar atratividade salarial, benefícios e integração (*onboarding*) nos primeiros 90 dias."
                )

            with col_r3:
                st.markdown("#### Estratégia de Formação")
                st.info(
                    f"**Nível Predominante:** {top_nivel}\n\n"
                    f"**Evidência:** Concentra a maior parcela da geração líquida de empregos ativos no filtro.\n\n"
                    f"**Ação:** Direcionar vagas de aprendizagem industrial e programas de requalificação para esse perfil."
                )