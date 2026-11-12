# Monitor Estratégico de Emprego e Gargalos — Santa Catarina (Novo CAGED + IBGE)

Projeto desenvolvido para análise do mercado de trabalho formal em Santa Catarina, integrando microdados de movimentações do **Novo CAGED** com dados demográficos municipais do **IBGE (Censo 2022)** e enriquecimento ocupacional via **IA Generativa (Gemini API + CBO 2002)**.

> **Dashboard Interativo Online:** [Acessar Painel no Streamlit Cloud](https://datathon-senaisc.streamlit.app/)

---

## Eixos Analíticos e Indicadores

O painel interativo foi estruturado em **4 KPIs estratégicos** e **3 eixos de investigação**:

1. **Territorial e Setorial:** Comparação justa entre municípios de diferentes portes por meio do saldo normalizado e identificação de setores econômicos (CNAE) em expansão ou retração.
2. **Perfil Socioeconômico:** Matriz de atratividade cruzando **Salário Médio** e **Índice de Rotatividade (Turnover)** por setor e escolaridade para diagnosticar gargalos de retenção.
3. **Qualificação e Gargalos (IA / CBO 2002):** Agrupamento das ocupações em **11 macrofamílias de cargos** e classificação em **3 níveis de qualificação** (*Alta Qualificação*, *Técnico/Especializado* e *Operacional/Base*).

### Fórmulas Principais
* **Saldo Absoluto de Vagas:** $\text{Admissões} - \text{Demissões}$
* **Saldo por 10.000 Habitantes:** $\left(\frac{\text{Saldo de Vagas}}{\text{População Municipal}}\right) \times 10.000$
* **Índice de Rotatividade (Turnover):** $\left(\frac{\text{Demissões}}{\text{Admissões}}\right) \times 100$

---

## Estrutura do Repositório

* `app.py` — Aplicação web interativa desenvolvida em **Streamlit** e **Plotly**.
* `script.py` — Pipeline inicial de limpeza, validação relacional (`many_to_one`), agregação municipal/setorial e extração de CBOs únicas.
* `ia_generativa.py` — Enriquecimento das ocupações via **Gemini API** (com *fallback* determinístico baseado nos Grandes Grupos da CBO 2002) e consolidação da base.
* `otimizar_base.py` — Geração do cubo analítico compactado (`Base_Dashboard_Otimizada.csv.gz`) preservando somas e contagens exatas para deploy em nuvem.
* `Base_Dashboard_Otimizada.csv.gz` — Base tratada e otimizada consumida pelo dashboard.
* `Dicionario_CBO_Enriquecido.csv` & `Prompt_Macrofamilias_CBO.txt` — Dicionário de mapeamento ocupacional e prompt estruturado utilizado na etapa de IA.
* `Agregado_Municipio_Setor.csv` & `Top_10_Municipios_Saldo.csv` — Tabelas analíticas intermediárias exportadas pelo pipeline.
* `requirements.txt` — Dependências Python necessárias para execução local e na nuvem.

---

## Como Executar Localmente

1. Clone o repositório e acesse a pasta do projeto:
   ```bash
   git clone [https://github.com/SEU-USUARIO/SEU-REPOSITORIO.git](https://github.com/SEU-USUARIO/SEU-REPOSITORIO.git)
   cd SEU-REPOSITORIO
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Inicie o dashboard:
   ```bash
   streamlit run app.py
   ```

---

## Equipe
* Arthur Rupolo Da Costa — Front-end, Análise Exploratória e Storytelling Visual:** Estruturação das abas dos 3 Eixos Analíticos (Territorial/Setorial, Socioeconômico e Qualificação/Gargalos), validação visual das métricas de gargalo e *turnover* no painel e alinhamento da narrativa de dados para a apresentação.

* Heitor Ávila Fochesato — Desenvolvimento Back-end e Engenharia de Software:** Apoio na codificação, depuração e refatoração dos scripts Python, validação das regras de agregação, estruturação do mecanismo de *fallback* da CBO 2002 e integração lógica entre o processamento de dados e o painel.

* Maria Vitoria Silveira Da Silva — Front-end, UI/UX e Visualização de Dados:** Desenvolvimento da interface interativa no Streamlit (`app.py`), configuração dos filtros dinâmicos na barra lateral, construção dos gráficos interativos em Plotly e organização visual dos KPIs estratégicos.

* Vicente Lemos trilha — Arquitetura de Dados, IA Generativa e Deploy:** Estruturação do pipeline ETL e limpeza das bases (`script.py`), cruzamento relacional e normalização métrica (Novo CAGED + IBGE), engenharia de prompts e enriquecimento ocupacional via Gemini API (`ia_generativa.py`), otimização do cubo de dados (`otimizar_base.py`) e deploy em nuvem (GitHub + Streamlit Cloud).