import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# 1. Configuração da Página
st.set_page_config(page_title="Flight Monitor GDS", page_icon="✈️", layout="wide")

# Função para pegar cotação ao vivo (Conversão de Moeda)
def get_exchange_rate():
    try:
        res = requests.get("https://open.er-api.com/v6/latest/EUR")
        data = res.json()
        return data["rates"]["BRL"]
    except:
        return 6.15 # Fallback caso a API de câmbio falhe

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #007bff; color: white; font-weight: bold; }
    .main { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

# 2. Configurações e Base de Dados
api_token = st.secrets.get("DUFFEL_TOKEN")

SITES_BASE = {
    "TAP Air Portugal": {"pt": "https://www.flytap.com/pt-pt", "br": "https://www.flytap.com/pt-br"},
    "Iberia": {"pt": "https://www.iberia.com/pt/", "br": "https://www.iberia.com/br/"},
    "LATAM": {"pt": "https://www.latamairlines.com/py/pt", "br": "https://www.latamairlines.com/br/pt"},
    "Air Europa": {"pt": "https://www.aireuropa.com/pt/pt/home", "br": "https://www.aireuropa.com/br/pt/home"},
    "Lufthansa": {"pt": "https://www.lufthansa.com/pt/pt/homepage", "br": "https://www.lufthansa.com/br/pt/homepage"},
    "British Airways": {"pt": "https://www.britishairways.com/travel/home/public/pt_pt/", "br": "https://www.britishairways.com/travel/home/public/pt_br/"}
}

cidades = {
    "Brasil - Sudeste": {
        "São Paulo (GRU)": "GRU", "São Paulo (CGH)": "CGH", "Campinas (VCP)": "VCP",
        "Rio de Janeiro (GIG)": "GIG", "Rio de Janeiro (SDU)": "SDU", "Belo Horizonte (CNF)": "CNF", "Vitória (VIX)": "VIX"
    },
    "Brasil - Sul": {
        "Curitiba (CWB)": "CWB", "Porto Alegre (POA)": "POA", "Florianópolis (FLN)": "FLN", "Foz do Iguaçu (IGU)": "IGU"
    },
    "Brasil - Nordeste/Norte/Centro": {
        "Salvador (SSA)": "SSA", "Recife (REC)": "REC", "Fortaleza (FOR)": "FOR", "Natal (NAT)": "NAT",
        "Brasília (BSB)": "BSB", "Manaus (MAO)": "MAO", "Belém (BEL)": "BEL", "Goiânia (GYN)": "GYN"
    },
    "Portugal e Ilhas": {
        "Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO", "Faro (FAO)": "FAO", 
        "Funchal (FNC)": "FNC", "Ponta Delgada (PDL)": "PDL", "Terceira (TER)": "TER"
    },
    "Europa - Principais Hubs": {
        "Madrid (MAD)": "MAD", "Barcelona (BCN)": "BCN", "Paris (CDG)": "CDG", "Londres (LHR)": "LHR", 
        "Roma (FCO)": "FCO", "Milão (MXP)": "MXP", "Frankfurt (FRA)": "FRA", "Munique (MUC)": "MUC",
        "Amesterdão (AMS)": "AMS", "Bruxelas (BRU)": "BRU", "Zurique (ZRH)": "ZRH", "Viena (VIE)": "VIE"
    }
}

opcoes = []
mapa_iata = {}
for regiao, items in cidades.items():
    for nome, iata in items.items():
        opcoes.append(nome)
        mapa_iata[nome] = iata

# 3. Interface de Utilizador
st.title("🌍 Flight Monitor - Buscador GDS")

col_tipo, col_moeda = st.columns([3, 1])
with col_tipo:
    tipo_viagem = st.radio("Tipo de Viagem", ["Só Ida/Volta", "Ida e Volta"], horizontal=True)
with col_moeda:
    moeda_pref = st.selectbox("Moeda e Região", ["Euro (€) - (Site .PT)", "Real (R$) - (Site .BR)"])

col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
with col1:
    origem_sel = st.selectbox("Origem:", options=opcoes, index=18) # Lisboa
with col2:
    destino_sel = st.selectbox("Destino:", options=opcoes, index=0)  # GRU
with col3:
    data_ida = st.date_input("Data de Ida", min_value=datetime.today())
with col4:
    if tipo_viagem == "Ida e Volta":
        data_volta = st.date_input("Data de Volta", min_value=data_ida + timedelta(days=1))
    else:
        data_volta = None

# 4. Busca e Lógica de Preços
if st.button("Pesquisar"):
    if not api_token:
        st.error("ERRO: Token não encontrado!")
    else:
        try:
            with st.spinner('A localizar voos e verificar câmbio ao vivo...'):
                cotacao_atual = get_exchange_rate()
                url = "https://api.duffel.com/air/offer_requests"
                headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}

                is_br = "Real" in moeda_pref
                moeda_busca = "BRL" if is_br else "EUR"

                slices = [{"origin": mapa_iata[origem_sel], "destination": mapa_iata[destino_sel], "departure_date": str(data_ida)}]
                if tipo_viagem == "Ida e Volta" and data_volta:
                    slices.append({"origin": mapa_iata[destino_sel], "destination": mapa_iata[origem_sel], "departure_date": str(data_volta)})

                # Payload com solicitação de moeda específica para tentar tarifas de mercado local
                payload = {
                    "data": {
                        "slices": slices, 
                        "passengers": [{"type": "adult"}], 
                        "cabin_class": "economy",
                        "requested_currencies": [moeda_busca]
                    }
                }
                
                res = requests.post(url, headers=headers, json=payload)
                
                if res.status_code == 201:
                    req_id = res.json()["data"]["id"]
                    offers_res = requests.get(f"https://api.duffel.com/air/offers?offer_request_id={req_id}&sort=total_amount", headers=headers)
                    offers_data = offers_res.json().get("data", [])

                    if offers_data:
                        voos_finais = []
                        for o in offers_data:
                            cia_nome = o["owner"]["name"]
                            preco_base = float(o["total_amount"])
                            moeda_api = o["total_currency"]

                            # Lógica de Conversão Dinâmica
                            if is_br:
                                preco_exibicao = preco_base if moeda_api == "BRL" else preco_base * cotacao_atual
                                simbolo = "R$"
                            else:
                                preco_exibicao = preco_base if moeda_api == "EUR" else preco_base / cotacao_atual
                                simbolo = "€"

                            # Lógica de Link Regional e Moeda no Skyscanner
                            if cia_nome in SITES_BASE:
                                link_final = SITES_BASE[cia_nome]["br" if is_br else "pt"]
                            else:
                                iata_orig, iata_dest = mapa_iata[origem_sel], mapa_iata[destino_sel]
                                data_str = data_ida.strftime("%y%m%d")
                                if is_br:
                                    link_sky = f"https://www.skyscanner.com.br/transport/flights/{iata_orig}/{iata_dest}/{data_str}/?curr=BRL"
                                else:
                                    link_sky = f"https://www.skyscanner.pt/transport/flights/{iata_orig}/{iata_dest}/{data_str}/?curr=EUR"
                                
                                if data_volta:
                                    link_sky = link_sky.replace(f"/{data_str}/", f"/{data_str}/{data_volta.strftime('%y%m%d')}/")
                                link_final = link_sky

                            voos_finais.append({"Companhia": cia_nome, "Preço": preco_exibicao, "Link": link_final})

                        st.balloons()
                        df = pd.DataFrame(voos_finais).drop_duplicates(subset=['Companhia', 'Preço'])
                        
                        st.dataframe(
                            df,
                            column_config={
                                "Preço": st.column_config.NumberColumn(f"Preço ({simbolo})", format=f"{simbolo} %.2f"),
                                "Link": st.column_config.LinkColumn("Reservar 🔗", display_text="Ver Preço Real no Skyscanner" if is_br else "Ver Oferta Oficial")
                            },
                            hide_index=True, use_container_width=True
                        )
                        if is_br:
                            st.info("💡 **Dica para Voos Domésticos:** APIs internacionais podem mostrar tarifas mais caras para o Brasil. Clique em 'Ver Preço Real' para abrir o Skyscanner Brasil com as tarifas locais.")
                            st.caption(f"ℹ️ Câmbio utilizado: 1€ = R$ {cotacao_atual:.2f}")
                    else:
                        st.warning("Sem voos disponíveis para estas datas.")
                else:
                    st.error(f"Erro na API Duffel: {res.text}")
        except Exception as e:
            st.error(f"Erro inesperado: {e}")