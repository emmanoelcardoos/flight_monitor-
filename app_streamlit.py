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

# --- DESIGN MIDNIGHT DARK BLINDADO ---
st.markdown("""
    <style>
    /* Fundo Gradiente */
    .stApp {
        background: radial-gradient(circle at top right, #1e293b, #0f172a) !important;
    }

    /* Card de Vidro */
    [data-testid="stVerticalBlock"] > div:has(div.stButton) {
        background: rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(20px) !important;
        border-radius: 20px !important;
        padding: 40px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        max-width: 1100px !important;
        margin: auto !important;
    }

    /* FORÇAR BARRAS CLARAS (ORIGEM, DESTINO, PASSAGEIROS) */
    /* Usamos seletores universais para garantir que o tema escuro não vença */
    div[data-baseweb="select"], div[data-baseweb="input"], .stDateInput div, 
    div[data-testid="stPopover"] > button, .stSelectbox div {
        background-color: rgba(255, 255, 255, 0.9) !important;
        border: none !important;
        border-radius: 10px !important;
        height: 45px !important;
    }

    /* Cor do texto dentro de todos os campos */
    input, select, span, p, label, div[role="listbox"] {
        color: #1e293b !important;
        font-weight: 600 !important;
    }

    /* Botão de Busca Limpo e Alinhado */
    div.stButton > button[kind="primary"] {
        background-color: #3b82f6 !important;
        color: white !important;
        border-radius: 10px !important;
        height: 45px !important;
        width: 100% !important;
        border: none !important;
        font-weight: 700 !important;
        margin-top: 0px !important;
    }

    /* Título Moderno */
    .main-title {
        font-size: 4rem;
        font-weight: 900;
        text-align: center;
        color: white;
        text-shadow: 0 4px 10px rgba(0,0,0,0.3);
        margin-bottom: 30px;
    }

    header, footer, #MainMenu {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE APOIO ---
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

# --- TÍTULO ---
st.markdown('<h1 class="main-title">Flight Monitor</h1>', unsafe_allow_html=True)

# --- DADOS ---
cidades = {
    "Portugal": {"Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO"},
    "Brasil": {"São Paulo (GRU)": "GRU", "Rio de Janeiro (GIG)": "GIG"},
    "Mundo": {"Madrid (MAD)": "MAD", "Paris (CDG)": "CDG", "Miami (MIA)": "MIA"}
}
mapa_iata = {}
opcoes = ["Pesquisar..."]
for regiao, items in cidades.items():
    for nome, iata in items.items():
        mapa_iata[nome] = iata
        opcoes.append(nome)

# --- CARD DE BUSCA (ALINHAMENTO TOTAL) ---
with st.container():
    tipo_v = st.radio("Config", ["Ida e volta", "Somente ida"], horizontal=True, label_visibility="collapsed")
    
    # LINHA 1: De | Para | Passageiros | Moeda (Integrada)
    c1, c2, c3, c4 = st.columns([7, 7, 4, 2])
    with c1: origem_sel = st.selectbox("De", opcoes, label_visibility="collapsed", key="o_fix")
    with c2: destino_sel = st.selectbox("Para", opcoes, label_visibility="collapsed", key="d_fix")
    with c3:
        pax_pop = st.popover("👤 Passageiros", use_container_width=True)
        with pax_pop:
            adultos = st.number_input("Adultos", 1, 9, 1)
            criancas = st.number_input("Crianças", 0, 9, 0)
            bebes = st.number_input("Bebés", 0, adultos, 0)
    with c4:
        # Mudança para Selectbox discreta para evitar o erro de Traceback
        moeda_simbolo = st.selectbox("M", ["€", "R$"], label_visibility="collapsed")

    st.markdown("<div style='margin: 10px;'></div>", unsafe_allow_html=True)

    # LINHA 2: Ida | Volta | Botão Buscar (Alinhados)
    c5, c6, c7 = st.columns([7, 7, 6])
    with c5: data_ida = st.date_input("Ida", value=datetime.today(), label_visibility="collapsed")
    with c6:
        if tipo_v == "Ida e volta":
            data_volta = st.date_input("Volta", value=datetime.today() + timedelta(days=7), label_visibility="collapsed")
        else:
            st.text_input("Volta", value="---", disabled=True, label_visibility="collapsed")
            data_volta = None
    with c7:
        btn_pesquisar = st.button("BUSCAR VOOS", kind="primary", use_container_width=True)

# --- LÓGICA DE RESULTADOS ---
if btn_pesquisar:
    if "Pesquisar" in origem_sel or "Pesquisar" in destino_sel:
        st.warning("⚠️ Selecione a origem e o destino.")
    else:
        try:
            with st.spinner('🔎 Procurando ofertas...'):
                api_token = st.secrets.get("DUFFEL_TOKEN")
                headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                cotacao = get_exchange_rate()
                
                pax_list = [{"type": "adult"}] * adultos + [{"type": "child"}] * criancas + [{"type": "infant"}] * bebes
                iata_origem, iata_dest = mapa_iata[origem_sel], mapa_iata[destino_sel]
                
                slices = [{"origin": iata_origem, "destination": iata_dest, "departure_date": str(data_ida)}]
                if data_volta: slices.append({"origin": iata_dest, "destination": iata_origem, "departure_date": str(data_volta)})

                payload = {"data": {"slices": slices, "passengers": pax_list, "requested_currencies": ["BRL" if moeda_simbolo == "R$" else "EUR"]}}
                res = requests.post("https://api.duffel.com/air/offer_requests", headers=headers, json=payload)
                
                if res.status_code == 201:
                    offers = requests.get(f"https://api.duffel.com/air/offers?offer_request_id={res.json()['data']['id']}&sort=total_amount", headers=headers).json().get("data", [])
                    if offers:
                        o = offers[0]
                        st.session_state.voos = [{
                            "Companhia": o["owner"]["name"],
                            "Preço": float(o["total_amount"]),
                            "Símbolo": moeda_simbolo,
                            "Link": f"https://www.skyscanner.pt/transport/flights/{iata_origem}/{iata_dest}/{data_ida.strftime('%y%m%d')}"
                        }]
                        st.session_state.itinerario = f"{origem_sel} para {destino_sel}"
                    else: st.warning("Nenhum voo encontrado.")
        except Exception as e: st.error(f"Erro: {e}")

# --- EXIBIÇÃO DE RESULTADOS ---
if "voos" in st.session_state and st.session_state.voos:
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container():
        st.markdown('<div style="background: rgba(255,255,255,0.1); padding: 25px; border-radius: 15px;">', unsafe_allow_html=True)
        st.subheader("✈️ Resultados")
        df = pd.DataFrame(st.session_state.voos)
        st.dataframe(df, column_config={
            "Preço": st.column_config.NumberColumn("Preço", format=f"{moeda_simbolo} %.2f"),
            "Link": st.column_config.LinkColumn("Reservar", display_text="Ver Oferta ✈️")
        }, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)