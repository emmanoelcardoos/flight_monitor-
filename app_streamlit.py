import streamlit as st
from duffel_api import Duffel
import pandas as pd
import os

# 1. FORÇAR VERSÃO DA API (Isto resolve o erro de 'Unsupported Version')
os.environ["DUFFEL_API_VERSION"] = "v1"

# 2. Configuração Visual
st.set_page_config(page_title="Flight Monitor DGS", page_icon="✈️", layout="centered")

st.markdown("""
    <style>
    .stButton>button {width: 100%; background-color: #007bff; color: white; font-weight: bold; border-radius: 8px; height: 3em;}
    .main {background-color: #f5f7f9;}
    </style>
    """, unsafe_allow_html=True)

# 3. Credenciais
api_token = os.getenv('DUFFEL_TOKEN')

# 4. Dicionário de Cidades e IATAs
cidades = {
    "Brasil": {"São Paulo (GRU)": "GRU", "Rio (GIG)": "GIG", "Brasília (BSB)": "BSB"},
    "Europa": {"Madrid (MAD)": "MAD", "Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO", "Paris (CDG)": "CDG", "Londres (LHR)": "LHR"},
    "EUA": {"Nova York (JFK)": "JFK", "Miami (MIA)": "MIA", "Orlando (MCO)": "MCO"}
}

opcoes = []
mapa_iata = {}
for regiao, items in cidades.items():
    for nome, iata in items.items():
        opcoes.append(nome)
        mapa_iata[nome] = iata

# 5. Interface do Utilizador
st.title("🌍 Flight Monitor - Buscador DGS")
st.write("Pesquisa voos em tempo real com a tecnologia Duffel.")

with st.container():
    col1, col2 = st.columns(2)
    with col1:
        origem_sel = st.selectbox("Saindo de:", options=opcoes, index=0)
    with col2:
        destino_sel = st.selectbox("Indo para:", options=opcoes, index=3) # Madrid
    
    data_voo = st.date_input("Data da viagem:", help="Selecione uma data futura")

# 6. Lógica de Busca
if st.button("🔍 Procurar Melhores Preços"):
    if not api_token:
        st.error("Erro: Token DUFFEL_TOKEN não encontrado nos Secrets do Streamlit!")
    else:
        try:
            # Inicializa o cliente de forma limpa
            client = Duffel(access_token=api_token)
            
            with st.spinner('A aceder aos sistemas das companhias aéreas...'):
                # Criar a requisição de oferta
                slices = [
                    {
                        "origin": mapa_iata[origem_sel],
                        "destination": mapa_iata[destino_sel],
                        "departure_date": str(data_voo)
                    }
                ]
                
                # Executa a busca
                offer_request = client.offer_requests.create() \
                    .slices(slices) \
                    .passengers([{"type": "adult"}]) \
                    .execute()
                
                # Obtém as ofertas
                offers = client.offers.list(offer_request.id)
                
                dados_voos = []
                for o in offers:
                    dados_voos.append({
                        "Companhia": o.owner.name,
                        "Preço": float(o.total_amount),
                        "Moeda": o.total_currency,
                        "Link": f"https://www.google.com/travel/flights?q=Flights%20to%20{mapa_iata[destino_sel]}%20from%20{mapa_iata[origem_sel]}%20on%20{data_voo}"
                    })

                if dados_voos:
                    df = pd.DataFrame(dados_voos).sort_values(by="Preço")
                    st.balloons()
                    st.success(f"Encontrámos {len(df)} voos disponíveis!")
                    
                    # Exibição Profissional
                    st.dataframe(
                        df,
                        column_config={
                            "Preço": st.column_config.NumberColumn(format="%.2f"),
                            "Link": st.column_config.LinkColumn("Reservar 🔗", display_text="Ver no Google Flights")
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.warning("Nenhum voo disponível para esta rota/data no modo de teste.")
                    
        except Exception as e:
            st.error(f"Ocorreu um erro na API: {e}")

st.markdown("---")
st.caption("Desenvolvido para uso familiar por Emmanoel.")