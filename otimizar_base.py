import os
import pandas as pd

print("Verificando estrutura de Base_Consolidada_Datathon.csv...")
cols_cons = pd.read_csv('Base_Consolidada_Datathon.csv', sep=';', nrows=1).columns.tolist()

if 'competênciamov' in cols_cons:
    df = pd.read_csv('Base_Consolidada_Datathon.csv', sep=';', low_memory=False)
    df['adm'] = (df['saldomovimentacao'] == 1).astype(int)
    df['dem'] = (df['saldomovimentacao'] == -1).astype(int)
    df['sal_adm'] = df['salario_num'].where(df['saldomovimentacao'] == 1)
    df['sal_dem'] = df['salario_num'].where(df['saldomovimentacao'] == -1)
    df['nome_setor'] = df['nome_setor'].replace({'Z': 'Não Identificado'})
else:
    print("'competênciamov' não estava na base consolidada. Resgatando de Novo_Caged_MOV_Limpo.csv...")
    col_cbo_cons = 'cbo_padronizado' if 'cbo_padronizado' in cols_cons else 'cbo2002ocupação'

    # 1. Extrai dicionários já tratados (Municípios e CBOs enriquecidos por IA)
    df_ref = pd.read_csv(
        'Base_Consolidada_Datathon.csv',
        sep=';',
        usecols=['municipio_codigo', 'nome_municipio', 'populacao', col_cbo_cons, 'macrofamilia', 'nivel_qualificacao'],
        low_memory=False
    )
    df_ref['mun_6'] = df_ref['municipio_codigo'].astype(str).str.replace(r'\.0$', '', regex=True).str[:6]
    map_mun = df_ref[['mun_6', 'municipio_codigo', 'nome_municipio', 'populacao']].drop_duplicates('mun_6')

    df_ref['cbo_padronizado'] = df_ref[col_cbo_cons].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(6)
    map_cbo = df_ref[['cbo_padronizado', 'macrofamilia', 'nivel_qualificacao']].drop_duplicates('cbo_padronizado')
    del df_ref

    # 2. Lê Novo_Caged_MOV_Limpo.csv com competênciamov
    with open('Novo_Caged_MOV_Limpo.csv', 'r', encoding='utf-8', errors='replace') as f:
        sep_mov = ';' if ';' in f.readline() else ','

    cols_mov = ['competênciamov', 'município', 'seção', 'saldomovimentação', 'cbo2002ocupação', 'graudeinstrução', 'salário']
    df = pd.read_csv('Novo_Caged_MOV_Limpo.csv', sep=sep_mov, usecols=cols_mov, low_memory=False)
    df = df[df['saldomovimentação'].isin([1, -1])].copy()

    # Chaves padronizadas e cruzamento
    df['mun_6'] = df['município'].astype(str).str.replace(r'\.0$', '', regex=True).str[:6]
    df['cbo_padronizado'] = df['cbo2002ocupação'].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(6)

    df = df.merge(map_mun, on='mun_6', how='inner')
    df = df.merge(map_cbo, on='cbo_padronizado', how='left')
    df['macrofamilia'] = df['macrofamilia'].fillna('Outras Ocupações')
    df['nivel_qualificacao'] = df['nivel_qualificacao'].fillna('Operacional / Base')

    # Tradução de Setor CNAE (já incluindo Z) e Escolaridade
    mapa_secoes = {
        'A': 'Agropecuária e Pesca', 'B': 'Indústrias Extrativas', 'C': 'Indústrias de Transformação',
        'D': 'Eletricidade e Gás', 'E': 'Água, Esgoto e Resíduos', 'F': 'Construção',
        'G': 'Comércio e Reparação de Veículos', 'H': 'Transporte, Armazenagem e Correio',
        'I': 'Alojamento e Alimentação', 'J': 'Informação e Comunicação',
        'K': 'Atividades Financeiras e Seguros', 'L': 'Atividades Imobiliárias',
        'M': 'Atividades Profissionais e Técnicas', 'N': 'Atividades Administrativas',
        'O': 'Administração Pública e Defesa', 'P': 'Educação',
        'Q': 'Saúde Humana e Serviços Sociais', 'R': 'Artes, Cultura e Esporte',
        'S': 'Outras Atividades de Serviços', 'T': 'Serviços Domésticos',
        'U': 'Organismos Internacionais', 'Z': 'Não Identificado'
    }
    mapa_esc = {
        1: 'Analfabeto', 2: 'Até 5ª Incompleto', 3: '5ª Completo Fundamental',
        4: '6ª a 9ª Fundamental', 5: 'Fundamental Completo', 6: 'Médio Incompleto',
        7: 'Médio Completo', 8: 'Superior Incompleto', 9: 'Superior Completo',
        10: 'Mestrado', 11: 'Doutorado', 80: 'Pós-Graduação Completa', 99: 'Não Identificado'
    }
    df['nome_setor'] = df['seção'].astype(str).str.strip().map(mapa_secoes).fillna('Não Identificado')
    df['escolaridade_desc'] = pd.to_numeric(df['graudeinstrução'], errors='coerce').map(mapa_esc).fillna('Não Identificado')

    df['salario_num'] = pd.to_numeric(df['salário'].astype(str).str.replace(',', '.'), errors='coerce')
    df['adm'] = (df['saldomovimentação'] == 1).astype(int)
    df['dem'] = (df['saldomovimentação'] == -1).astype(int)
    df['sal_adm'] = df['salario_num'].where(df['saldomovimentação'] == 1)
    df['sal_dem'] = df['salario_num'].where(df['saldomovimentação'] == -1)

dimensoes = [
    'competênciamov', 'municipio_codigo', 'nome_municipio', 'populacao',
    'nome_setor', 'macrofamilia', 'nivel_qualificacao', 'escolaridade_desc'
]

print("Agrupando cubo analítico mensal...")
df_cubo = df.groupby(dimensoes, as_index=False, dropna=False).agg(
    admissoes=('adm', 'sum'),
    demissoes=('dem', 'sum'),
    soma_sal_adm=('sal_adm', 'sum'),
    qtd_sal_adm=('sal_adm', 'count'),
    soma_sal_dem=('sal_dem', 'sum'),
    qtd_sal_dem=('sal_dem', 'count'),
    soma_sal_total=('salario_num', 'sum'),
    qtd_sal_total=('salario_num', 'count')
)

arquivo_saida = 'Base_Dashboard_Otimizada.csv.gz'
df_cubo.to_csv(arquivo_saida, sep=';', index=False, compression='gzip')

tamanho_mb = os.path.getsize(arquivo_saida) / (1024 * 1024)
print(f"Concluído! '{arquivo_saida}' gerado com {tamanho_mb:.2f} MB ({len(df_cubo):,} linhas).")