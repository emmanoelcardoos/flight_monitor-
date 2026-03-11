import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# 1. Configuração da Página
st.set_page_config(page_title="Flight Monitor DGS", page_icon="✈️", layout="wide")

# Estilo Profissional
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #007bff; color: white; font-weight: bold; }
    .main { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

# 2. Token e Configurações
api_token = st.secrets.get("DUFFEL_TOKEN")

# Mapeamento de Sites Oficiais
SITES_OFICIAIS = {
    "TAP Air Portugal": "https://www.flytap.com",
    "Iberia": "https://www.iberia.com",
    "LATAM": "https://www.latamairlines.com",
    "Air Europa": "https://www.aireuropa.com",
    "Lufthansa": "https://www.lufthansa.com",
    "British Airways": "https://www.britishairways.com",
    "Aeromexico": "https://www.aeromexico.com",
    "ITA Airways": "https://www.ita-airways.com"
}

cidades = {
    "Brasil": {"São Paulo (GRU)": "GRU", "Rio (GIG)": "GIG", "Brasília (BSB)": "BSB"},
    "Europa": {"Madrid (MAD)": "MAD", "Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO", "Paris (CDG)": "CDG", "Londres (LHR)": "LHR"},
    "EUA": {"Nova York (JFK)": "JFK", "Miami (MIA)": "MIA"}
}

opcoes = []
mapa_iata = {}
for regiao, items in cidades.items():
    for nome, iata in items.items():
        opcoes.append(nome)
        mapa_iata[nome] = iata

# 3. Interface de Utilizador
st.title("🌍 Flight Monitor - Buscador DGS")

tipo_viagem = st.radio("Tipo de Viagem", ["Só Ida", "Ida e Volta"], horizontal=True)

col1, col2, col3, col4 = st.columns([2, 2, 2, 2])

with col1:
    origem_sel = st.selectbox("✈️ De Onde?", options=opcoes, index=0)
with col2:
    destino_sel = st.selectbox("📍 Para Onde?", options=opcoes, index=3)

with col3:
    data_ida = st.date_input("📅 Data de Ida", min_value=datetime.today())

with col4:
    if tipo_viagem == "Ida e Volta":
        data_volta = st.date_input("📅 Data de Volta", min_value=data_ida + timedelta(days=1))
    else:
        data_volta = None

# 4. Lógica de Busca
if st.button("🔍 PROCURAR MELHORES PREÇOS"):
    if not api_token:
        st.error("ERRO: Token não encontrado nos Secrets!")
    else:
        try:
            with st.spinner('A analisar ofertas reais...'):
                url = "https://api.duffel.com/air/offer_requests"
                headers = {
                    "Authorization": f"Bearer {api_token}",
                    "Duffel-Version": "v2",
                    "Content-Type": "application/json"
                }

                # Construção dos trechos (slices)
                slices = [{"origin": mapa_iata[origem_sel], "destination": mapa_iata[destino_sel], "departure_date": str(data_ida)}]
                
                if tipo_viagem == "Ida e Volta" and data_volta:
                    slices.append({"origin": mapa_iata[destino_sel], "destination": mapa_iata[origem_sel], "departure_date": str(data_volta)})

                payload = {
                    "data": {
                        "slices": slices,
                        "passengers": [{"type": "adult"}],
                        "cabin_class": "economy"
                    }
                }

                res = requests.post(url, headers=headers, json=payload)
                
                if res.status_code == 201:
                    req_id = res.json()["data"]["id"]
                    offers_url = f"https://api.duffel.com/air/offers?offer_request_id={req_id}&sort=total_amount"
                    offers_res = requests.get(offers_url, headers=headers)
                    offers_data = offers_res.json().get("data", [])

                    if offers_data:
                        voos_finais = []
                        for o in offers_data:
                            cia_nome = o["owner"]["name"]
                            preco = float(o["total_amount"])
                            
                            # Lógica de Link Inteligente
                            if cia_nome in SITES_OFICIAIS:
                                link_final = SITES_OFICIAIS[cia_nome]
                            else:
                                # Gerar link Skyscanner
                                iata_orig = mapa_iata[origem_sel]
                                iata_dest = mapa_iata[destino_sel]
                                data_str = data_ida.strftime("%y%m%d")
                                if data_volta:
                                    volta_str = data_volta.strftime("%y%m%d")
                                    link_final = f"https://www.skyscanner.pt/transport/flights/{iata_orig}/{iata_dest}/{data_str}/{volta_str}/"
                                else:
                                    link_final = f"https://www.skyscanner.pt/transport/flights/{iata_orig}/{iata_dest}/{data_str}/"

                            voos_finais.append({
                                "Companhia": cia_nome,
                                "Preço Total": preco,
                                "Moeda": "EUR",
                                "Link": link_final
                            })

                        st.balloons()
                        df = pd.DataFrame(voos_finais).drop_duplicates(subset=['Companhia', 'Preço Total'])
                        
                        st.dataframe(
                            df,
                            column_config={
                                "Preço Total": st.column_config.NumberColumn("Preço Total (€)", format="%.2f €"),
                                "Link": st.column_config.LinkColumn("Reservar 🔗", display_text="Ver Oferta")
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                    else:
                        st.warning("Não encontrámos voos diretos ou disponíveis para estas datas.")
                else:
                    st.error(f"Erro na API Duffel: {res.text}")
        except Exception as e:
            st.error(f"Erro inesperado: {e}")