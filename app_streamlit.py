import streamlit as st
import requests
import pandas as pd
import os

# 1. Configuração da Página
st.set_page_config(page_title="Flight Monitor DGS", page_icon="✈️")

st.markdown("""
    <style>
    .stButton>button {width: 100%; background-color: #007bff; color: white; font-weight: bold; border-radius: 8px;}
    </style>
    """, unsafe_allow_html=True)

# 2. Token (Lendo dos Secrets do Streamlit)
api_token = st.secrets.get("DUFFEL_TOKEN")

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

# 4. Interface
st.title("🌍 Flight Monitor - Buscador DGS")

col1, col2 = st.columns(2)
with col1:
    origem_sel = st.selectbox("Saindo de:", options=opcoes, index=0)
with col2:
    destino_sel = st.selectbox("Indo para:", options=opcoes, index=2)
    
data_voo = st.date_input("Data da viagem:")

# 5. Busca Direta
if st.button("🔍 Procurar Voos Agora"):
    if not api_token:
        st.error("Erro: DUFFEL_TOKEN não configurado!")
    else:
        try:
            with st.spinner('Acedendo aos sistemas...'):
                url = "https://api.duffel.com/air/offer_requests"
                
                # REMOVEMOS A LINHA DA VERSÃO: A Duffel usará a padrão da tua conta
                headers = {
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "data": {
                        "slices": [{"origin": mapa_iata[origem_sel], "destination": mapa_iata[destino_sel], "departure_date": str(data_voo)}],
                        "passengers": [{"type": "adult"}],
                        "cabin_class": "economy"
                    }
                }

                # Criar pedido
                res = requests.post(url, headers=headers, json=payload)
                
                if res.status_code == 201:
                    req_id = res.json()["data"]["id"]
                    
                    # Buscar ofertas
                    offers_url = f"https://api.duffel.com/air/offers?offer_request_id={req_id}&sort=total_amount"
                    offers_res = requests.get(offers_url, headers=headers)
                    offers_data = offers_res.json().get("data", [])

                    if offers_data:
                        voos = []
                        for o in offers_data:
                            voos.append({
                                "Companhia": o["owner"]["name"],
                                "Preço": float(o["total_amount"]),
                                "Moeda": o["total_currency"],
                                "Link": f"https://www.google.com/travel/flights?q=Flights%20to%20{mapa_iata[destino_sel]}%20from%20{mapa_iata[origem_sel]}%20on%20{data_voo}"
                            })
                        
                        st.balloons()
                        st.table(pd.DataFrame(voos).sort_values("Preço"))
                    else:
                        st.warning("Nenhum voo encontrado no modo de teste para esta rota.")
                else:
                    # Se der erro de versão de novo, o erro aparecerá aqui detalhado
                    st.error(f"Erro na API: {res.text}")

        except Exception as e:
            st.error(f"Erro inesperado: {e}")