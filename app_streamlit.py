import streamlit as st
import requests
import pandas as pd
import os

# 1. Configuração da Página
st.set_page_config(page_title="Flight Monitor DGS", page_icon="✈️", layout="centered")

# Estilização Profissional
st.markdown("""
    <style>
    .stButton>button {width: 100%; background-color: #007bff; color: white; font-weight: bold; border-radius: 8px; height: 3em;}
    .main {background-color: #f5f7f9;}
    </style>
    """, unsafe_allow_html=True)

# 2. Token da Duffel (Pegando dos Secrets do Streamlit)
api_token = st.secrets.get("DUFFEL_TOKEN")

# 3. Cidades e Aeroportos
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

# 4. Interface do Utilizador
st.title("🌍 Flight Monitor - Buscador DGS")
st.write("Pesquisa direta via API Duffel (Versão Estável 2026).")

col1, col2 = st.columns(2)
with col1:
    origem_sel = st.selectbox("Saindo de:", options=opcoes, index=0)
with col2:
    destino_sel = st.selectbox("Indo para:", options=opcoes, index=3) # Madrid

data_voo = st.date_input("Data da viagem:", help="Selecione uma data futura")

# 5. Lógica de Busca Direta (Sem bibliotecas instáveis)
if st.button("🔍 Procurar Melhores Preços"):
    if not api_token:
        st.error("Erro: Token DUFFEL_TOKEN não configurado no Streamlit Cloud!")
    else:
        try:
            with st.spinner('A consultar os sistemas de reserva...'):
                url = "https://api.duffel.com/air/offer_requests"
                headers = {
                    "Authorization": f"Bearer {api_token}",
                    "Duffel-Version": "v1",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "data": {
                        "slices": [{
                            "origin": mapa_iata[origem_sel],
                            "destination": mapa_iata[destino_sel],
                            "departure_date": str(data_voo)
                        }],
                        "passengers": [{"type": "adult"}],
                        "cabin_class": "economy"
                    }
                }

                # Criar requisição
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code == 201:
                    request_id = response.json()["data"]["id"]
                    
                    # Buscar as ofertas geradas
                    offers_url = f"https://api.duffel.com/air/offers?offer_request_id={request_id}&sort=total_amount"
                    offers_res = requests.get(offers_url, headers=headers)
                    offers_data = offers_res.json()["data"]

                    voos_list = []
                    for offer in offers_data:
                        voos_list.append({
                            "Companhia": offer["owner"]["name"],
                            "Preço": float(offer["total_amount"]),
                            "Moeda": offer["total_currency"],
                            "Link": f"https://www.google.com/travel/flights?q=Flights%20to%20{mapa_iata[destino_sel]}%20from%20{mapa_iata[origem_sel]}%20on%20{data_voo}"
                        })

                    if voos_list:
                        df = pd.DataFrame(voos_list)
                        st.balloons()
                        st.success(f"Encontramos {len(df)} voos!")
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
                        st.warning("Nenhum voo disponível para esta rota no modo de teste.")
                else:
                    st.error(f"Erro na API Duffel: {response.text}")

        except Exception as e:
            st.error(f"Ocorreu um erro inesperado: {e}")

st.markdown("---")
st.caption("Desenvolvido por Emmanoel.")