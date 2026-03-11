import streamlit as st
from duffel_api import Duffel
import pandas as pd
import os

# 1. FORÇAR A VERSÃO NO NÍVEL DO SISTEMA
os.environ["DUFFEL_API_VERSION"] = "v1"

st.set_page_config(page_title="Flight Monitor DGS", page_icon="✈️")

# 2. Credenciais
api_token = st.secrets.get("DUFFEL_TOKEN") or os.getenv("DUFFEL_TOKEN")

# 3. Cidades
cidades = {
    "Brasil": {"São Paulo (GRU)": "GRU", "Rio (GIG)": "GIG"},
    "Europa": {"Madrid (MAD)": "MAD", "Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO", "Paris (CDG)": "CDG"},
    "EUA": {"Nova York (JFK)": "JFK", "Miami (MIA)": "MIA"}
}
opcoes = []
mapa_iata = {}
for regiao, items in cidades.items():
    for nome, iata in items.items():
        opcoes.append(nome)
        mapa_iata[nome] = iata

st.title("🌍 Flight Monitor - Buscador DGS")

col1, col2 = st.columns(2)
with col1:
    origem_sel = st.selectbox("Saindo de:", options=opcoes, index=0)
with col2:
    destino_sel = st.selectbox("Indo para:", options=opcoes, index=2)
    
data_voo = st.date_input("Data:")

if st.button("🔍 Procurar Voos"):
    if not api_token:
        st.error("Token não encontrado!")
    else:
        try:
            # AQUI ESTÁ O TRUQUE: api_version="v1" (com underline) 
            # é o que a biblioteca Python da Duffel espera internamente
            client = Duffel(access_token=api_token, api_version="v1")
            
            with st.spinner('Buscando...'):
                slices = [{"origin": mapa_iata[origem_sel], "destination": mapa_iata[destino_sel], "departure_date": str(data_voo)}]
                offer_request = client.offer_requests.create().slices(slices).passengers([{"type": "adult"}]).execute()
                offers = client.offers.list(offer_request.id)
                
                voos = []
                for o in offers:
                    voos.append({
                        "Companhia": o.owner.name,
                        "Preço": float(o.total_amount),
                        "Moeda": o.total_currency
                    })

                if voos:
                    st.balloons()
                    st.table(pd.DataFrame(voos).sort_values("Preço"))
                else:
                    st.warning("Nenhum voo encontrado no modo de teste.")
        except Exception as e:
            # Se o erro de versão persistir, vamos mostrar exatamente o que a API diz
            st.error(f"Erro detalhado: {e}")