# Monitor Estratégico de Emprego e Gargalos — Santa Catarina (Novo CAGED + IBGE)

Solução analítica desenvolvida para diagnosticar sinais de **apagão de mão de obra** e **polos de expansão acelerada** em Santa Catarina, integrando microdados do **Novo CAGED**, dados demográficos do **IBGE** e enriquecimento ocupacional via **IA Generativa (Gemini API + CBO 2002)**.

> **Dashboard Interativo Online:** [Acessar Painel no Streamlit Cloud](https://datathon-senaisc.streamlit.app/)

---

## Eixos Analíticos e Indicadores

O painel conta com **4 KPIs estratégicos** no topo (Saldo Líquido, Saldo por 10 mil Habitantes, Salário Médio de Admissão e Índice de Rotatividade) e **3 abas de investigação**:

1. **Territorial e Setorial:** Ranking proporcional dos municípios com linha de referência (média do recorte), **modo comparativo entre municípios** (lado a lado por setor e na linha do tempo), balanço de expansão vs. encolhimento por setor econômico (CNAE) e curva mensal de movimentações.
2. **Perfil Socioeconômico:** Matriz de atratividade cruzando **Salário Médio** e **Índice de Rotatividade (Turnover)** por setor para identificar gargalos de retenção, além do comparativo por grau de instrução.
3. **Qualificação e Gargalos (IA / CBO 2002):** Classificação das ocupações em **11 macrofamílias de cargos** e **3 níveis de qualificação** (*Alta Qualificação*, *Técnico/Especializado* e *Operacional/Base*).

### Premissas e Limites da Análise
* **Janela Temporal (Projeção de Sazonalidade):** A base disponibilizada contempla os últimos 12 meses de movimentações. Portanto, a curva mensal apresentada no painel funciona como um **indicativo/projeção de comportamento sazonal** (oscilações intranuais); a confirmação estatística de ciclos recorrentes exigiria séries históricas de anos anteriores.
* **Tratamento de Setores (CNAE):** Registros originalmente classificados sob o código `'Z'` no layout do Novo CAGED foram padronizados como **`Não Identificado`** para maior clareza na leitura executiva.

### Fórmulas Principais
* **Saldo Líquido de Vagas:** $\text{Admissões} - \text{Demissões}$
* **Saldo por 10.000 Habitantes:** $\left(\frac{\text{Saldo de Vagas}}{\text{População Municipal}}\right) \times 10.000$
* **Índice de Rotatividade (Turnover):** $\left(\frac{\text{Demissões}}{\text{Admissões}}\right) \times 100$

---

## Estrutura do Repositório

* `app.py` — Aplicação web interativa desenvolvida em **Streamlit** e **Plotly**.
* `script.py` — Pipeline inicial de limpeza, validação relacional, agregação municipal/setorial e extração de CBOs únicas.
* `ia_generativa.py` — Enriquecimento das ocupações via **Gemini API** (com *fallback* determinístico baseado nos Grandes Grupos da CBO 2002).
* `otimizar_base.py` — Geração do cubo analítico compactado (`Base_Dashboard_Otimizada.csv.gz`) preservando somas, contagens exatas e competência mensal para deploy em nuvem.
* `Base_Dashboard_Otimizada.csv.gz` — Base tratada e otimizada consumida pelo dashboard.
* `Dicionario_CBO_Enriquecido.csv` & `Prompt_Macrofamilias_CBO.txt` — Dicionário de mapeamento ocupacional e prompt estruturado utilizado na etapa de IA.
* `Agregado_Municipio_Setor.csv` & `Top_10_Municipios_Saldo.csv` — Tabelas analíticas intermediárias exportadas pelo pipeline.
* `requirements.txt` — Dependências Python necessárias para execução.

---

## Equipe e Divisão de Responsabilidades

* **Vicente Trilha — Arquitetura de Dados, IA Generativa e Deploy:** Estruturação do pipeline ETL e limpeza das bases (`script.py`), cruzamento relacional e normalização métrica (Novo CAGED + IBGE), engenharia de prompts e enriquecimento ocupacional via Gemini API (`ia_generativa.py`), otimização do cubo de dados (`otimizar_base.py`) e deploy em nuvem (GitHub + Streamlit Cloud).
* **Heitor — Desenvolvimento Back-end e Engenharia de Software:** Apoio na codificação, depuração e refatoração dos scripts Python, validação das regras de agregação, estruturação do mecanismo de *fallback* da CBO 2002 e integração lógica entre o processamento de dados e o painel.
* **Maria — Front-end, UI/UX e Visualização de Dados:** Desenvolvimento da interface interativa no Streamlit (`app.py`), configuração dos filtros dinâmicos na barra lateral, construção dos gráficos interativos em Plotly e organização visual dos KPIs estratégicos.
* **Arthur — Front-end, Análise Exploratória e Storytelling Visual:** Estruturação das abas dos 3 Eixos Analíticos, validação visual das métricas de gargalo e *turnover* no painel e alinhamento da narrativa de dados para a apresentação.

---

## Execução Local (Plano de Contingência)

```bash
git clone <URL-DO-REPOSITORIO>
cd Datathon
pip install -r requirements.txt
streamlit run app.py
```