import os
import json
import time
import pandas as pd

# =====================================================================
# 1. FUNÇÕES DE CARREGAMENTO E PADRONIZAÇÃO
# =====================================================================
def carregar_csv(caminho):
    with open(caminho, 'r', encoding='utf-8-sig', errors='replace') as f:
        primeira_linha = f.readline()
    sep = ';' if primeira_linha.count(';') > primeira_linha.count(',') else ','
    try:
        df = pd.read_csv(caminho, sep=sep, low_memory=False)
    except UnicodeDecodeError:
        df = pd.read_csv(caminho, sep=sep, encoding='latin1', low_memory=False)
    df.columns = df.columns.str.strip()
    return df.loc[:, ~df.columns.str.startswith('Unnamed')]

def formatar_cbo(valor):
    s = str(valor).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s.zfill(6) if s.isdigit() else s

def limpar_salario(serie):
    s = serie.astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    valores = pd.to_numeric(s, errors='coerce')
    # Filtra distorções extremas comuns em registros incorretos do CAGED
    return valores.where((valores > 0) & (valores <= 150000))

# =====================================================================
# 2. CARGA, LIMPEZA E CRUZAMENTO (PASSOS 1 A 4 CONSOLIDADOS)
# =====================================================================
print("1/4 - Carregando e cruzando bases do Novo CAGED e Municípios de SC...")
df_municipios = carregar_csv('Municipios_SC_limpo.csv').rename(columns={
    'Código [-]': 'municipio_codigo',
    'Município [-]': 'nome_municipio',
    'População no último censo - pessoas [2022]': 'populacao'
})

df_caged = carregar_csv('Novo_Caged_MOV_Limpo.csv').rename(columns={
    'município': 'municipio_codigo',
    'saldomovimentação': 'saldomovimentacao'
})

if df_municipios['populacao'].dtype == object:
    df_municipios['populacao'] = df_municipios['populacao'].astype(str).str.replace('.', '', regex=False)
df_municipios['populacao'] = pd.to_numeric(df_municipios['populacao'], errors='coerce')

df_caged['municipio_codigo'] = pd.to_numeric(df_caged['municipio_codigo'], errors='coerce')
df_municipios['municipio_codigo'] = pd.to_numeric(df_municipios['municipio_codigo'], errors='coerce')
df_caged = df_caged.dropna(subset=['municipio_codigo'])
df_municipios = df_municipios.dropna(subset=['municipio_codigo'])

df_caged['municipio_codigo'] = df_caged['municipio_codigo'].astype(int)
df_municipios['municipio_codigo'] = df_municipios['municipio_codigo'].astype(int)

if df_municipios['municipio_codigo'].astype(str).str.len().mode()[0] == 7 and \
   df_caged['municipio_codigo'].astype(str).str.len().mode()[0] == 6:
    df_municipios['municipio_codigo'] = df_municipios['municipio_codigo'] // 10

colunas_essenciais = ['salário', 'graudeinstrução', 'cbo2002ocupação', 'seção']
df_caged = df_caged.dropna(subset=[c for c in colunas_essenciais if c in df_caged.columns]).drop_duplicates()

df_completo = pd.merge(
    df_caged,
    df_municipios[['municipio_codigo', 'nome_municipio', 'populacao']],
    on='municipio_codigo',
    how='inner'
)

df_completo['saldomovimentacao'] = pd.to_numeric(df_completo['saldomovimentacao'], errors='coerce').fillna(0).astype(int)
df_completo['salario_num'] = limpar_salario(df_completo['salário'])
df_completo['cbo_padronizado'] = df_completo['cbo2002ocupação'].apply(formatar_cbo)

# Decodificação da Seção CNAE
mapa_secoes = {
    'A': 'Agropecuária e Pesca', 'B': 'Indústrias Extrativas',
    'C': 'Indústria de Transformação', 'D': 'Eletricidade e Gás',
    'E': 'Água, Esgoto e Resíduos', 'F': 'Construção Civil',
    'G': 'Comércio e Reparação', 'H': 'Transporte e Armazenagem',
    'I': 'Alojamento e Alimentação', 'J': 'Informação e Comunicação',
    'K': 'Atividades Financeiras', 'L': 'Atividades Imobiliárias',
    'M': 'Atividades Profissionais/Técnicas', 'N': 'Atividades Administrativas',
    'O': 'Administração Pública', 'P': 'Educação',
    'Q': 'Saúde e Serviços Sociais', 'R': 'Artes, Cultura e Esporte',
    'S': 'Outras Atividades de Serviços', 'T': 'Serviços Domésticos',
   'U': 'Organismos Internacionais',
    'Z': 'Não Identificado'
}
df_completo['seção'] = df_completo['seção'].astype(str).str.strip().str.upper()
df_completo['nome_setor'] = df_completo['seção'].map(mapa_secoes).fillna(df_completo['seção'])

# Decodificação do Grau de Instrução oficial do CAGED
mapa_escolaridade = {
    1: 'Analfabeto', 2: 'Até 5º Incompleto', 3: '5º Completo Fundamental',
    4: '6º ao 9º Fundamental', 5: 'Fundamental Completo', 6: 'Médio Incompleto',
    7: 'Médio Completo', 8: 'Superior Incompleto', 9: 'Superior Completo',
    10: 'Mestrado', 11: 'Doutorado', 80: 'Pós-Graduação Completa', 99: 'Não Identificado'
}
df_completo['graudeinstrução'] = pd.to_numeric(df_completo['graudeinstrução'], errors='coerce').fillna(99).astype(int)
df_completo['escolaridade_desc'] = df_completo['graudeinstrução'].map(mapa_escolaridade).fillna('Não Identificado')

# =====================================================================
# 3. ENRIQUECIMENTO DE CBOs VIA IA GENERATIVA (COM FALLBACK ESTRUTURAL)
# =====================================================================
print("2/4 - Extraindo CBOs únicas para classificação...")
df_cbos = df_completo.groupby('cbo_padronizado', as_index=False).agg(
    total_mov=('saldomovimentacao', 'count'),
    setor_predominante=('nome_setor', lambda x: x.mode().iloc[0] if not x.mode().empty else 'Geral')
).sort_values(by='total_mov', ascending=False)

def classificar_fallback_cbo2002(cbo):
    """Classificação determinística baseada nos Grandes Grupos oficiais da CBO 2002."""
    prefixo = cbo[:2] if len(cbo) >= 2 else "00"
    g1 = cbo[0] if len(cbo) >= 1 else "0"
    
    if g1 == '1':
        return f"CBO {cbo} (Gestão)", "Gestão, Liderança e Diretoria", "Alta Qualificação (Gestão/Superior)"
    elif prefixo in ['20', '21']:
        return f"CBO {cbo} (Engenharia/TI/Ciências)", "Tecnologia, Dados e Engenharia", "Alta Qualificação (Engenharia/Superior)"
    elif prefixo == '22':
        return f"CBO {cbo} (Saúde Superior)", "Saúde, Educação e Serviços Sociais", "Alta Qualificação (Engenharia/Superior)"
    elif prefixo == '23':
        return f"CBO {cbo} (Educação/Ensino)", "Saúde, Educação e Serviços Sociais", "Alta Qualificação (Engenharia/Superior)"
    elif g1 == '2':
        return f"CBO {cbo} (Especialista Superior)", "Administrativo, Financeiro e Jurídico", "Alta Qualificação (Engenharia/Superior)"
    elif prefixo in ['30', '31']:
        return f"CBO {cbo} (Técnico Industrial/TI)", "Tecnologia, Dados e Engenharia", "Técnico / Especializado"
    elif g1 == '3':
        return f"CBO {cbo} (Técnico Nível Médio)", "Técnicos de Nível Médio e Apoio", "Técnico / Especializado"
    elif g1 == '4':
        return f"CBO {cbo} (Administrativo)", "Administrativo, Financeiro e Jurídico", "Operacional / Base"
    elif prefixo == '51':
        return f"CBO {cbo} (Serviços/Turismo)", "Turismo, Hotelaria e Serviços Gerais", "Operacional / Base"
    elif prefixo == '52':
        return f"CBO {cbo} (Comércio/Vendas)", "Comércio, Vendas e Atendimento", "Operacional / Base"
    elif g1 == '6':
        return f"CBO {cbo} (Agropecuária)", "Agropecuária e Extrativismo", "Operacional / Base"
    elif prefixo == '71':
        return f"CBO {cbo} (Construção Civil)", "Construção Civil e Manutenção", "Operacional / Base"
    elif prefixo == '78':
        return f"CBO {cbo} (Logística/Transporte)", "Logística, Transporte e Armazenagem", "Operacional / Base"
    elif g1 in ['7', '8', '9']:
        return f"CBO {cbo} (Operação/Manutenção)", "Operações Industriais e Produção", "Operacional / Base"
    return f"CBO {cbo} (Outros)", "Serviços Gerais e Apoio Operacional", "Operacional / Base"

resultados_ia = {}
api_key = os.environ.get("GEMINI_API_KEY")

if api_key:
    print("3/4 - Chave GEMINI_API_KEY detectada. Classificando Top CBOs via Gemini API...")
    cache_arquivo = "cache_ia_cbos.json"
    if os.path.exists(cache_arquivo):
        with open(cache_arquivo, "r", encoding="utf-8") as f:
            resultados_ia = json.load(f)
        print(f"   -> {len(resultados_ia)} CBOs recuperadas do cache local.")

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        lote_ia = df_cbos.head(250)[['cbo_padronizado', 'setor_predominante']].to_dict(orient='records')
        pendentes = [item for item in lote_ia if item['cbo_padronizado'] not in resultados_ia]
        tamanho_bloco = 50

        for i in range(0, len(pendentes), tamanho_bloco):
            bloco = pendentes[i:i + tamanho_bloco]
            prompt = f"""Classifique cada código CBO 2002 abaixo.
Para cada item, retorne:
- "cbo": código de 6 dígitos
- "descricao_cbo": título oficial resumido da ocupação na CBO 2002
- "macrofamilia": escolha EXATAMENTE UMA entre:
  ["Gestão, Liderança e Diretoria", "Tecnologia, Dados e Engenharia", "Administrativo, Financeiro e Jurídico", "Comércio, Vendas e Atendimento", "Operações Industriais e Produção", "Construção Civil e Manutenção", "Logística, Transporte e Armazenagem", "Agropecuária e Extrativismo", "Saúde, Educação e Serviços Sociais", "Turismo, Hotelaria e Serviços Gerais", "Técnicos de Nível Médio e Apoio"]
- "nivel_qualificacao": escolha EXATAMENTE UMA entre:
  ["Alta Qualificação (Engenharia/Superior)", "Técnico / Especializado", "Operacional / Base"]

Entrada: {json.dumps(bloco, ensure_ascii=False)}"""

            sucesso_bloco = False
            for tentativa in range(1, 5):
                try:
                    response = client.models.generate_content(
                        model="gemini-3.8-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.1
                        )
                    )
                    lista_resp = json.loads(response.text)
                    for item in lista_resp:
                        cbo_cod = formatar_cbo(item.get("cbo", ""))
                        resultados_ia[cbo_cod] = [
                            item.get("descricao_cbo", f"CBO {cbo_cod}"),
                            item.get("macrofamilia", "Operações Industriais e Produção"),
                            item.get("nivel_qualificacao", "Operacional / Base")
                        ]
                    with open(cache_arquivo, "w", encoding="utf-8") as f:
                        json.dump(resultados_ia, f, ensure_ascii=False, indent=2)
                    print(f"   -> Lote {i + 1} a {min(i + tamanho_bloco, len(pendentes))} salvo com sucesso.")
                    sucesso_bloco = True
                    time.sleep(2)
                    break
                except Exception as err_req:
                    if "503" in str(err_req) or "429" in str(err_req):
                        espera = tentativa * 5
                        print(f"   [Servidor ocupado - tentativa {tentativa}/4] Aguardando {espera}s...")
                        time.sleep(espera)
                    else:
                        raise err_req

            if not sucesso_bloco:
                print("   [Aviso] Servidor seguiu congestionado neste lote. Usando fallback para o restante.")
                break
    except Exception as e:
        print(f"   [Aviso] Interrupção na API ({e}). Aplicando fallback CBO 2002 para os restantes.")
else:
    print("3/4 - GEMINI_API_KEY não definida. Aplicando classificação estrutural CBO 2002 (100% offline)...")

# Consolidar dicionário final para 100% das CBOs
registros_dicionario = []
for cbo in df_cbos['cbo_padronizado']:
    if cbo in resultados_ia:
        desc, macro, qualif = resultados_ia[cbo]
    else:
        desc, macro, qualif = classificar_fallback_cbo2002(cbo)
    registros_dicionario.append({
        'cbo_padronizado': cbo,
        'descricao_cbo': desc,
        'macrofamilia': macro,
        'nivel_qualificacao': qualif
    })

df_dicionario_cbo = pd.DataFrame(registros_dicionario)
df_dicionario_cbo.to_csv('Dicionario_CBO_Enriquecido.csv', sep=';', index=False, encoding='utf-8-sig')

# =====================================================================
# 4. INTEGRAR ENRIQUECIMENTO À BASE COMPLETA E EXPORTAR PARA O DASHBOARD
# =====================================================================
print("4/4 - Consolidando base analítica final para o Dashboard...")
df_final = pd.merge(df_completo, df_dicionario_cbo, on='cbo_padronizado', how='left')

colunas_dashboard = [
    'municipio_codigo', 'nome_municipio', 'populacao',
    'seção', 'nome_setor', 'cbo_padronizado', 'descricao_cbo',
    'macrofamilia', 'nivel_qualificacao', 'escolaridade_desc',
    'saldomovimentacao', 'salario_num', 'idade'
]
df_final = df_final[[c for c in colunas_dashboard if c in df_final.columns]]
df_final.to_csv('Base_Consolidada_Datathon.csv', sep=';', index=False, encoding='utf-8-sig')

print("\nConcluído! Arquivos gerados:")
print("- Dicionario_CBO_Enriquecido.csv")
print("- Base_Consolidada_Datathon.csv (pronta para o Streamlit)")