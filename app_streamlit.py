import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# 1. Configuração da Página
st.set_page_config(page_title="Flight Monitor GDS", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #007bff; color: white; font-weight: bold; }
    .main { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

# 2. Configurações
api_token = st.secrets.get("DUFFEL_TOKEN")
COTACAO_EUR_BRL = 6.15 

# Base de sites (ajustamos o sufixo dinamicamente)
SITES_BASE = {
    "TAP Air Portugal": {"pt": "https://www.flytap.com/pt-pt", "br": "https://www.flytap.com/pt-br"},
    "Iberia": {"pt": "https://www.iberia.com/pt/", "br": "https://www.iberia.com/br/"},
    "LATAM": {"pt": "https://www.latamairlines.com/py/pt", "br": "https://www.latamairlines.com/br/pt"},
    "Air Europa": {"pt": "https://www.aireuropa.com/pt/pt/home", "br": "https://www.aireuropa.com/br/pt/home"},
    "Lufthansa": {"pt": "https://www.lufthansa.com/pt/pt/homepage", "br": "https://www.lufthansa.com/br/pt/homepage"},
    "British Airways": {"pt": "https://www.britishairways.com/travel/home/public/pt_pt/", "br": "https://www.britishairways.com/travel/home/public/pt_br/"}
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

# 3. Interface
st.title("🌍 Flight Monitor - Buscador GDS")

col_tipo, col_moeda = st.columns([3, 1])
with col_tipo:
    tipo_viagem = st.radio("Tipo de Viagem", ["Só Ida", "Ida e Volta"], horizontal=True)
with col_moeda:
    moeda_pref = st.selectbox("💰 Moeda e Região", ["Euro (€) - Site .PT", "Real (R$) - Site .BR"])

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

# 4. Busca
if st.button("🔍 PROCURAR MELHORES PREÇOS"):
    if not api_token:
        st.error("ERRO: Token não encontrado!")
    else:
        try:
            with st.spinner('A localizar voos e ajustar links regionais...'):
                url = "https://api.duffel.com/air/offer_requests"
                headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}

                slices = [{"origin": mapa_iata[origem_sel], "destination": mapa_iata[destino_sel], "departure_date": str(data_ida)}]
                if tipo_viagem == "Ida e Volta" and data_volta:
                    slices.append({"origin": mapa_iata[destino_sel], "destination": mapa_iata[origem_sel], "departure_date": str(data_volta)})

                payload = {"data": {"slices": slices, "passengers": [{"type": "adult"}], "cabin_class": "economy"}}
                res = requests.post(url, headers=headers, json=payload)
                
                if res.status_code == 201:
                    req_id = res.json()["data"]["id"]
                    offers_res = requests.get(f"https://api.duffel.com/air/offers?offer_request_id={req_id}&sort=total_amount", headers=headers)
                    offers_data = offers_res.json().get("data", [])

                    if offers_data:
                        voos_finais = []
                        is_br = "Real" in moeda_pref
                        
                        for o in offers_data:
                            cia_nome = o["owner"]["name"]
                            preco_base = float(o["total_amount"])
                            
                            # Conversão e Símbolo
                            preco_exibicao = preco_base * COTACAO_EUR_BRL if is_br else preco_base
                            simbolo = "R$" if is_br else "€"

                            # Lógica de Link Regional
                            if cia_nome in SITES_BASE:
                                link_final = SITES_BASE[cia_nome]["br" if is_br else "pt"]
                            else:
                                # Skyscanner Regional
                                iata_orig, iata_dest = mapa_iata[origem_sel], mapa_iata[destino_sel]
                                data_str = data_ida.strftime("%y%m%d")
                                tld = "com.br" if is_br else "pt"
                                link_sky = f"https://www.skyscanner.{tld}/transport/flights/{iata_orig}/{iata_dest}/{data_str}/"
                                if data_volta:
                                    link_sky += f"{data_volta.strftime('%y%m%d')}/"
                                link_final = link_sky

                            voos_finais.append({
                                "Companhia": cia_nome,
                                "Preço": preco_exibicao,
                                "Moeda": simbolo,
                                "Link": link_final
                            })

                        st.balloons()
                        df = pd.DataFrame(voos_finais).drop_duplicates(subset=['Companhia', 'Preço'])
                        
                        st.dataframe(
                            df,
                            column_config={
                                "Preço": st.column_config.NumberColumn(f"Preço ({simbolo})", format=f"{simbolo} %.2f"),
                                "Link": st.column_config.LinkColumn("Reservar 🔗", display_text="Ver no Site Oficial/BR" if is_br else "Ver no Site Oficial/PT")
                            },
                            hide_index=True, use_container_width=True
                        )
                    else:
                        st.warning("Sem voos para estas datas.")
                else:
                    st.error(f"Erro na API: {res.text}")
        except Exception as e:
            st.error(f"Erro: {e}")