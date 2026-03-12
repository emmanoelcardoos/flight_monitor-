import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from streamlit_gsheets import GSheetsConnection

# 1. Configuração da Página
st.set_page_config(page_title="Flight Monitor GDS", page_icon="✈️", layout="wide")

# --- ESTILO CSS COM FUNDO DE MONTANHAS E GLASSMORPHISM ---
st.markdown("""
    <style>
    /* 1. Fundo com Imagem de Montanhas */
    .stApp {
        background: url('https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1920&q=80') no-repeat center center fixed;
        background-size: cover;
    }

    /* 2. Card Glassmorphism (efeito líquido Apple) */
    [data-testid="stVerticalBlock"] > div:has(div.stButton) {
        background: rgba(255, 255, 255, 0.2) !important;
        backdrop-filter: blur(20px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 20px !important;
        padding: 40px !important;
        max-width: 1100px !important;
        margin: auto !important;
        margin-top: 50px !important;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2) !important;
    }

    /* 3. INPUTS BRANCOS com texto preto */
    div[data-baseweb="select"], div[data-baseweb="input"], .stDateInput div, .stNumberInput div, div[data-testid="stPopover"] > button {
        background-color: white !important;
        border: none !important;
        border-radius: 12px !important;
        color: #000000 !important;
        height: 48px !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05) !important;
    }

    /* Texto dentro dos inputs - PRETO */
    input, select, [data-baseweb="select"] * {
        color: #000000 !important;
        font-weight: 500 !important;
    }
    
    /* Labels em branco para contrastar com o fundo */
    .stSelectbox label, .stDateInput label, .stNumberInput label, div[data-testid="stPopover"] label {
        color: white !important;
        font-weight: 500 !important;
        text-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
        font-size: 0.9rem !important;
        margin-bottom: 4px !important;
    }

    /* Placeholders em cinza claro */
    input::placeholder {
        color: #666666 !important;
        opacity: 1 !important;
    }

    /* 4. BOTÃO DE BUSCA - Azul Apple */
    div.stButton > button {
        background: #0071e3 !important;
        color: white !important;
        border-radius: 12px !important;
        height: 48px !important;
        width: 100% !important;
        border: none !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        letter-spacing: 0.3px !important;
        box-shadow: 0 4px 12px rgba(0, 113, 227, 0.3) !important;
        transition: all 0.2s ease !important;
        margin-top: 24px !important;
    }
    
    div.stButton > button:hover {
        background: #0077ed !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 16px rgba(0, 113, 227, 0.4) !important;
    }

    /* 5. TÍTULO PRINCIPAL - Branco com sombra */
    .main-title {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-size: 3.5rem;
        font-weight: 700;
        text-align: center;
        color: white;
        text-shadow: 0 4px 20px rgba(0,0,0,0.3);
        margin-bottom: 8px;
        letter-spacing: -0.5px;
    }
    
    .sub-title {
        text-align: center;
        color: rgba(255, 255, 255, 0.9);
        font-size: 1.1rem;
        margin-bottom: 30px;
        font-weight: 400;
        text-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }

    /* 6. BOTÃO DE MOEDA */
    .currency-container {
        position: fixed;
        top: 20px;
        right: 30px;
        z-index: 9999;
    }
    
    .currency-container button {
        background: rgba(255, 255, 255, 0.2) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        color: white !important;
        border-radius: 12px !important;
        width: 48px !important;
        height: 48px !important;
        font-weight: 600 !important;
        font-size: 1.2rem !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
    }

    /* 7. CARD DE RESULTADOS - Glassmorphism */
    .results-card {
        background: rgba(255, 255, 255, 0.15) !important;
        backdrop-filter: blur(20px) saturate(180%) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 20px !important;
        padding: 30px !important;
        max-width: 1100px !important;
        margin: 30px auto !important;
        color: white !important;
    }
    
    .results-card * {
        color: white !important;
    }

    /* 8. Esconder elementos padrão */
    header, footer, #MainMenu {visibility: hidden;}
    
    /* 9. Ajuste de espaçamento */
    .stColumn {
        gap: 16px !important;
    }
    
    /* 10. Popover de passageiros */
    div[data-testid="stPopover"] > button {
        text-align: left !important;
        color: #000000 !important;
        background-color: white !important;
    }
    
    div[data-testid="stPopover"] > button:hover {
        background-color: #f5f5f5 !important;
    }
    
    /* 11. Botão de troca */
    .swap-button {
        background: rgba(255, 255, 255, 0.3) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.4) !important;
        border-radius: 50% !important;
        width: 36px !important;
        height: 36px !important;
        padding: 0 !important;
        margin: 0 auto !important;
        color: white !important;
        font-size: 1.2rem !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin-top: 24px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- MOEDA NO CANTO SUPERIOR DIREITO ---
if 'moeda_simbolo' not in st.session_state:
    st.session_state.moeda_simbolo = "€"

st.markdown('<div class="currency-container">', unsafe_allow_html=True)
if st.button(st.session_state.moeda_simbolo, key="curr_btn"):
    st.session_state.moeda_simbolo = "R$" if st.session_state.moeda_simbolo == "€" else "€"
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# --- TÍTULO ---
st.markdown('<h1 class="main-title">Flight Monitor</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Encontre e monitorize os seus voos em tempo real</p>', unsafe_allow_html=True)

# --- FUNÇÕES ---
def get_exchange_rate():
    try:
        res = requests.get("https://open.er-api.com/v6/latest/EUR")
        return res.json()["rates"]["BRL"]
    except: return 6.15

def guardar_alerta_planilha(dados):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        colunas_certas = ["email", "itinerario", "origem", "destino", "data", "data_volta", "adultos", "criancas", "bebes", "preco_inicial", "moeda"]
        df_atual = conn.read(worksheet="Página1", ttl=0)
        df_atual = df_atual.reindex(columns=colunas_certas) if not df_atual.empty else pd.DataFrame(columns=colunas_certas)
        novo_dado = pd.DataFrame([dados]).reindex(columns=colunas_certas)
        df_final = pd.concat([df_atual, novo_dado], ignore_index=True)
        conn.update(worksheet="Página1", data=df_final)
        st.cache_data.clear() 
        return True
    except: return False

# --- DADOS ---
cidades = {
    "Portugal": {"Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO"},
    "Brasil": {"São Paulo (GRU)": "GRU", "Rio de Janeiro (GIG)": "GIG", "Brasília (BSB)": "BSB"},
    "Mundo": {"Madrid (MAD)": "MAD", "Paris (CDG)": "CDG", "Miami (MIA)": "MIA", "Londres (LHR)": "LHR"}
}
mapa_iata = {}
opcoes_origem = ["De..."]
opcoes_destino = ["Para..."]
for regiao, items in cidades.items():
    for nome, iata in items.items():
        mapa_iata[nome] = iata
        opcoes_origem.append(nome)
        opcoes_destino.append(nome)

# --- CARD DE BUSCA COM DISPOSIÇÃO EXATA DA IMAGEM ---
with st.container():
    # PRIMEIRA LINHA: Origem e Destino (sem botão de troca como na imagem)
    col1, col2 = st.columns(2)
    
    with col1:
        origem_sel = st.selectbox("Origem", opcoes_origem, key="origem")
    
    with col2:
        destino_sel = st.selectbox("Destino", opcoes_destino, key="destino")
    
    # SEGUNDA LINHA: Tipo de viagem (radio horizontal) e Datas
    tipo_v = st.radio("", ["Ida e volta", "Somente ida"], horizontal=True, label_visibility="collapsed")
    
    col_data1, col_data2 = st.columns(2)
    
    with col_data1:
        data_ida = st.date_input("Ida", value=datetime.today())
    
    with col_data2:
        if tipo_v == "Ida e volta":
            data_volta = st.date_input("Volta", value=datetime.today() + timedelta(days=7))
        else:
            st.text_input("Volta", value="---", disabled=True)
            data_volta = None
    
    # TERCEIRA LINHA: Passageiros (como popover)
    with st.popover("Passageiros"):
        st.markdown("### Passageiros")
        adultos = st.number_input("Adultos", 1, 9, 1)
        criancas = st.number_input("Crianças", 0, 9, 0)
        bebes = st.number_input("Bebés", 0, adultos, 0)
    
    # BOTÃO DE PESQUISA
    btn_pesquisar = st.button("PESQUISAR VOOS", use_container_width=True)

# --- LÓGICA DE BUSCA ---
if btn_pesquisar:
    if "..." in origem_sel or "..." in destino_sel:
        st.warning("Por favor, selecione origem e destino.")
    else:
        try:
            with st.spinner('Buscando voos...'):
                api_token = st.secrets["DUFFEL_TOKEN"]
                headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                is_br = st.session_state.moeda_simbolo == "R$"
                cotacao = get_exchange_rate()
                pax_list = [{"type": "adult"}] * adultos + [{"type": "child"}] * criancas + [{"type": "infant"}] * bebes
                iata_origem, iata_dest = mapa_iata[origem_sel], mapa_iata[destino_sel]
                slices = [{"origin": iata_origem, "destination": iata_dest, "departure_date": str(data_ida)}]
                if data_volta: slices.append({"origin": iata_dest, "destination": iata_origem, "departure_date": str(data_volta)})

                payload = {"data": {"slices": slices, "passengers": pax_list, "requested_currencies": ["BRL" if is_br else "EUR"]}}
                res = requests.post("https://api.duffel.com/air/offer_requests", headers=headers, json=payload)
                if res.status_code == 201:
                    offers = requests.get(f"https://api.duffel.com/air/offers?offer_request_id={res.json()['data']['id']}&sort=total_amount", headers=headers).json().get("data", [])
                    if offers:
                        o = offers[0]
                        st.session_state.voos = [{
                            "Companhia": o["owner"]["name"],
                            "Preço": float(o["total_amount"]),
                            "Símbolo": st.session_state.moeda_simbolo,
                            "Link": f"https://www.skyscanner.pt/transport/flights/{iata_origem}/{iata_dest}/{data_ida.strftime('%y%m%d')}"
                        }]
                        st.session_state.itinerario = f"{origem_sel} para {destino_sel}"
                    else:
                        st.info("Nenhum voo encontrado.")
        except Exception as e: st.error(f"Erro: {e}")

# --- RESULTADOS ---
if "voos" in st.session_state:
    st.markdown('<div class="results-card">', unsafe_allow_html=True)
    
    st.subheader("✈️ Ofertas Encontradas")
    df = pd.DataFrame(st.session_state.voos)
    st.dataframe(df, column_config={
        "Preço": st.column_config.NumberColumn("Preço", format=f"{st.session_state.moeda_simbolo} %.2f"),
        "Link": st.column_config.LinkColumn("Reservar", display_text="Ver Oferta ✈️")
    }, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("📬 Ativar Alerta")
    email_user = st.text_input("E-mail para vigilância:", placeholder="seu@email.com")
    if st.button("ATIVAR ALERTA", use_container_width=True):
        if "@" in email_user:
            dados = {"email": email_user, "itinerario": st.session_state.itinerario, "origem": mapa_iata[origem_sel], "destino": mapa_iata[destino_sel], "data": str(data_ida), "data_volta": str(data_volta) if data_volta else "", "adultos": adultos, "criancas": criancas, "bebes": bebes, "preco_inicial": st.session_state.voos[0]["Preço"], "moeda": st.session_state.moeda_simbolo}
            if guardar_alerta_planilha(dados): 
                st.success("Alerta ativado!")
    
    st.markdown('</div>', unsafe_allow_html=True)