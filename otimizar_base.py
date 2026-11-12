import os
import pandas as pd

print("Lendo Base_Consolidada_Datathon.csv (aguarde alguns segundos)...")
df = pd.read_csv('Base_Consolidada_Datathon.csv', sep=';', low_memory=False)

# Colunas auxiliares para manter médias ponderadas 100% exatas após o agrupamento
df['adm'] = (df['saldomovimentacao'] == 1).astype(int)
df['dem'] = (df['saldomovimentacao'] == -1).astype(int)
df['sal_adm'] = df['salario_num'].where(df['saldomovimentacao'] == 1)
df['sal_dem'] = df['salario_num'].where(df['saldomovimentacao'] == -1)

dimensoes = [
    'municipio_codigo', 'nome_municipio', 'populacao',
    'nome_setor', 'macrofamilia', 'nivel_qualificacao', 'escolaridade_desc'
]

print("Agrupando dimensões do dashboard...")
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