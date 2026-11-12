import json
import math
import pandas as pd

def carregar_csv(caminho):
    # Detecta o separador (; ou ,)
    with open(caminho, 'r', encoding='utf-8-sig', errors='replace') as f:
        primeira_linha = f.readline()
    sep = ';' if primeira_linha.count(';') > primeira_linha.count(',') else ','
    
    try:
        df = pd.read_csv(caminho, sep=sep, low_memory=False)
    except UnicodeDecodeError:
        df = pd.read_csv(caminho, sep=sep, encoding='latin1', low_memory=False)
        
    df.columns = df.columns.str.strip()
    df = df.loc[:, ~df.columns.str.startswith('Unnamed')]
    return df

# 1. Carregar as bases de dados
df_municipios = carregar_csv('Municipios_SC_limpo.csv')
df_caged = carregar_csv('Novo_Caged_MOV_Limpo.csv')

# 2. Renomear e padronizar chaves relacionais
df_municipios = df_municipios.rename(columns={
    'Código [-]': 'municipio_codigo',
    'Município [-]': 'nome_municipio',
    'População no último censo - pessoas [2022]': 'populacao'
})

df_caged = df_caged.rename(columns={
    'município': 'municipio_codigo',
    'saldomovimentação': 'saldomovimentacao'
})

# Limpar e converter coluna de população
if df_municipios['populacao'].dtype == object:
    df_municipios['populacao'] = df_municipios['populacao'].astype(str).str.replace('.', '', regex=False)
df_municipios['populacao'] = pd.to_numeric(df_municipios['populacao'], errors='coerce')

# Converter chaves do município para inteiro
df_caged['municipio_codigo'] = pd.to_numeric(df_caged['municipio_codigo'], errors='coerce')
df_municipios['municipio_codigo'] = pd.to_numeric(df_municipios['municipio_codigo'], errors='coerce')

df_caged = df_caged.dropna(subset=['municipio_codigo'])
df_municipios = df_municipios.dropna(subset=['municipio_codigo'])

df_caged['municipio_codigo'] = df_caged['municipio_codigo'].astype(int)
df_municipios['municipio_codigo'] = df_municipios['municipio_codigo'].astype(int)

# Igualar códigos IBGE (6 dígitos no CAGED vs 7 dígitos no IBGE)
if df_municipios['municipio_codigo'].astype(str).str.len().mode()[0] == 7 and \
   df_caged['municipio_codigo'].astype(str).str.len().mode()[0] == 6:
    df_municipios['municipio_codigo'] = df_municipios['municipio_codigo'] // 10

# --- PASSO 2: LIMPEZA DE INCONSISTÊNCIAS E DUPLICATAS ---
colunas_essenciais = ['salário', 'graudeinstrução', 'cbo2002ocupação', 'seção']
colunas_presentes = [col for col in colunas_essenciais if col in df_caged.columns]

if colunas_presentes:
    df_caged = df_caged.dropna(subset=colunas_presentes)

df_caged = df_caged.drop_duplicates()

# --- PASSO 3: CRUZAMENTO RELACIONAL (MERGE) E VALIDAÇÃO ---
df_completo = pd.merge(
    df_caged,
    df_municipios,
    on='municipio_codigo',
    how='left',
    validate='many_to_one'
)

df_completo = df_completo.dropna(subset=['nome_municipio', 'populacao'])
df_completo['saldomovimentacao'] = pd.to_numeric(df_completo['saldomovimentacao'], errors='coerce').fillna(0)

# --- PASSO 4: AGREGAÇÃO E NORMALIZAÇÃO DA MÉTRICA PRINCIPAL ---
mapa_secoes = {
    'A': 'Agropecuária, Florestal e Pesca',
    'B': 'Indústrias Extrativas',
    'C': 'Indústrias de Transformação',
    'D': 'Eletricidade e Gás',
    'E': 'Água, Esgoto e Resíduos',
    'F': 'Construção',
    'G': 'Comércio e Reparação de Veículos',
    'H': 'Transporte, Armazenagem e Correio',
    'I': 'Alojamento e Alimentação',
    'J': 'Informação e Comunicação',
    'K': 'Atividades Financeiras e Seguros',
    'L': 'Atividades Imobiliárias',
    'M': 'Atividades Profissionais e Técnicas',
    'N': 'Atividades Administrativas',
    'O': 'Administração Pública e Seguridade',
    'P': 'Educação',
    'Q': 'Saúde Humana e Serviços Sociais',
    'R': 'Artes, Cultura, Esporte e Recreação',
    'S': 'Outras Atividades de Serviços',
    'T': 'Serviços Domésticos',
    'U': 'Organismos Internacionais'
}

df_completo['seção'] = df_completo['seção'].astype(str).str.strip().str.upper()
df_completo['nome_setor'] = df_completo['seção'].map(mapa_secoes).fillna(df_completo['seção'])

df_resumo_setor = df_completo.groupby(
    ['municipio_codigo', 'nome_municipio', 'populacao', 'seção', 'nome_setor'],
    as_index=False
).agg(
    admissoes=('saldomovimentacao', lambda x: (x == 1).sum()),
    demissoes=('saldomovimentacao', lambda x: (x == -1).sum())
)
df_resumo_setor['saldo_vagas'] = df_resumo_setor['admissoes'] - df_resumo_setor['demissoes']
df_resumo_setor['saldo_por_10k_hab'] = (df_resumo_setor['saldo_vagas'] / df_resumo_setor['populacao']) * 10000
df_resumo_setor = df_resumo_setor.sort_values(by='saldo_por_10k_hab', ascending=False)
df_resumo_setor.to_csv('Agregado_Municipio_Setor.csv', sep=';', index=False, encoding='utf-8-sig')

# =====================================================================
# --- PASSO 5: PREPARAÇÃO PARA ENRIQUECIMENTO VIA IA GENERATIVA ---
# =====================================================================

# 1. Padronizar o código CBO (preservando 6 dígitos com zeros à esquerda, se numérico)
def formatar_cbo(valor):
    s = str(valor).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s.zfill(6) if s.isdigit() else s

df_completo['cbo_padronizado'] = df_completo['cbo2002ocupação'].apply(formatar_cbo)

# Extrair CBOs únicas enriquecidas com volume de movimentações e setor predominante
df_cbos_unicas = df_completo.groupby('cbo_padronizado', as_index=False).agg(
    total_movimentacoes=('saldomovimentacao', 'count'),
    saldo_vagas=('saldomovimentacao', 'sum'),
    setor_predominante=('nome_setor', lambda x: x.mode().iloc[0] if not x.mode().empty else 'Não informado')
).sort_values(by='total_movimentacoes', ascending=False)

# Calcular representatividade acumulada (Pareto)
total_geral_mov = df_cbos_unicas['total_movimentacoes'].sum()
df_cbos_unicas['pct_acumulado'] = (df_cbos_unicas['total_movimentacoes'].cumsum() / total_geral_mov * 100).round(2)

# Salvar tabela completa de CBOs únicas para referência e cruzamento futuro (Passo 6)
df_cbos_unicas.to_csv('CBOs_Unicas_Base_Tratada.csv', sep=';', index=False, encoding='utf-8-sig')

# 2. Estruturar amostra JSON para envio via API ou Interface de LLM
registros_para_ia = df_cbos_unicas[['cbo_padronizado', 'setor_predominante', 'total_movimentacoes']].rename(
    columns={'cbo_padronizado': 'cbo'}
).to_dict(orient='records')

# Salvar JSON completo (ideal para consumo via script/API)
with open('CBOs_Payload_API.json', 'w', encoding='utf-8') as f:
    json.dump(registros_para_ia, f, ensure_ascii=False, indent=2)

# Gerar arquivo de Prompt pronto para copiar e colar em interface de LLM (lote com as Top 250 CBOs)
amostra_prompt = registros_para_ia[:250]
cobertura_amostra = df_cbos_unicas.iloc[min(249, len(df_cbos_unicas)-1)]['pct_acumulado']

prompt_texto = f"""Atue como um especialista em Economia do Trabalho e Classificação Brasileira de Ocupações (CBO 2002).
Abaixo está uma lista JSON contendo códigos CBO presentes nas movimentações do Novo CAGED em Santa Catarina, acompanhados do setor econômico predominante e do volume de registros.

TAREFA:
1. Identifique o título oficial de cada código CBO 2002.
2. Classifique cada ocupação em UMA das seguintes macrofamílias padronizadas:
   - "Gestão, Liderança e Diretoria"
   - "Tecnologia, Dados e Engenharia"
   - "Administrativo, Financeiro e Escritório"
   - "Comércio, Vendas e Atendimento"
   - "Operações Industriais e Produção"
   - "Construção Civil e Manutenção"
   - "Logística, Transporte e Armazenagem"
   - "Agropecuária e Extrativismo"
   - "Saúde, Educação e Serviços Sociais"
   - "Turismo, Hotelaria e Alimentação"
   - "Serviços Gerais e Apoio Operacional"

FORMATO DE SAÍDA OBRIGATÓRIO:
Retorne EXCLUSIVAMENTE um array JSON válido (sem blocos de texto explicativo antes ou depois) no seguinte formato:
[
  {{"cbo": "521110", "descricao_cbo": "Vendedor de comércio varejista", "macrofamilia": "Comércio, Vendas e Atendimento"}}
]

DADOS DE ENTRADA (CBOs):
{json.dumps(amostra_prompt, ensure_ascii=False, indent=2)}
"""

with open('Prompt_Macrofamilias_CBO.txt', 'w', encoding='utf-8') as f:
    f.write(prompt_texto)

# Relatório no terminal
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

print("=== RESUMO DA EXTRAÇÃO DE CBOs (PASSO 5) ===")
print(f"Total de CBOs únicas encontradas na base tratada: {len(df_cbos_unicas)}")
print(f"Cobertura das Top 250 CBOs sobre o total de movimentações de SC: {cobertura_amostra}%\n")

print("=== TOP 15 CBOs MAIS FREQUENTES EM SANTA CATARINA ===")
print(df_cbos_unicas.head(15).to_string(index=False))

print("\nArquivos gerados na pasta do projeto:")
print("1. CBOs_Unicas_Base_Tratada.csv  -> Tabela completa de CBOs únicas e representatividade")
print("2. CBOs_Payload_API.json         -> Lista estruturada completa para envio via API")
print("3. Prompt_Macrofamilias_CBO.txt  -> Prompt pronto para colar no ChatGPT/Gemini/Claude")