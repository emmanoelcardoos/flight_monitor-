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

# --- DESIGN MIDNIGHT DARK (PROFISSIONAL) ---
st.markdown("""
    <style>
    /* 1. Fundo e Reset */
    .stApp {
        background: radial-gradient(circle at top right, #1e293b, #0f172a) !important;
        color: #f1f5f9 !important;
    }

    /* 2. CARD PRINCIPAL (Vidro Escuro) */
    [data-testid="stVerticalBlock"] > div:has(div.stButton) {
        background: rgba(30, 41, 59, 0.7) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 24px !important;
        padding: 40px !important;
        max-width: 1100px !important;
        margin: auto !important;
        margin-top: 60px !important;
    }

    /* 3. INPUTS E BARRAS (Fim do Preto Sólido) */
    /* Usamos um azul profundo que combina com o fundo */
    div[data-baseweb="select"], div[data-baseweb="input"], .stDateInput div, .stNumberInput div, div[data-testid="stPopover"] > button {
        background-color: #334155 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        color: #f1f5f9 !important;
        height: 48px !important;
    }

    /* Garantir que o texto dentro dos campos seja legível */
    input, select, span, p, label {
        color: #f1f5f9 !important;
        font-weight: 500 !important;
    }

    /* 4. BOTÃO DE BUSCA (Azul Elétrico Neon) */
    div.stButton > button {
        background-color: #3b82f6 !important;
        color: white !important;
        border-radius: 12px !important;
        height: 48px !important;
        width: 100% !important;
        border: none !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        margin-top: 25px !important;
        transition: all 0.3s ease !important;
    }
    div.stButton > button:hover {
        background-color: #2563eb !important;
        transform: scale(1.02);
        box-shadow: 0 0 20px rgba(59, 130, 246, 0.4);
    }

    /* 5. MOEDA DISCRETA (Canto Superior Direito) */
    .currency-trigger {
        position: fixed;
        top: 25px;
        right: 40px;
        z-index: 10000;
    }
    .currency-trigger button {
        background: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        color: #3b82f6 !important;
        border-radius: 50% !important;
        width: 45px !important;
        height: 45px !important;
        font-weight: bold !important;
    }

    /* 6. TÍTULO MODERNO COM GRADIENTE */
    .main-title {
        font-size: 3.5rem;
        font-weight: 900;
        text-align: center;
        background: linear-gradient(to right, #60a5fa, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }

    header, footer, #MainMenu {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE MOEDA (CANTO DIREITO) ---
if 'moeda_simbolo' not in st.session_state:
    st.session_state.moeda_simbolo = "€"

st.markdown('<div class="currency-trigger">', unsafe_allow_html=True)
if st.button(st.session_state.moeda_simbolo):
    st.session_state.moeda_simbolo = "R$" if st.session_state.moeda_simbolo == "€" else "€"
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# --- HEADER ---
st.markdown('<h1 class="main-title">Flight Monitor</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align:center; color:#94a3b8; font-size:1.1rem;">Sua agência inteligente de monitorização de voos</p>', unsafe_allow_html=True)

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
    "Brasil": {"São Paulo (GRU)": "GRU", "Rio de Janeiro (GIG)": "GIG"},
    "Portugal": {"Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO"},
    "Europa": {"Paris (CDG)": "CDG", "Madrid (MAD)": "MAD", "Londres (LHR)": "LHR"}
}
mapa_iata = {}
opcoes_origem = ["De..."]
opcoes_destino = ["Para...", "🌍 EXPLORAR QUALQUER LUGAR"]
for regiao, items in cidades.items():
    for nome, iata in items.items():
        mapa_iata[nome] = iata
        opcoes_origem.append(nome)
        opcoes_destino.append(nome)

# --- CARD DE BUSCA (MIDNIGHT STYLE) ---
with st.container():
    tipo_v = st.radio("Config", ["Ida e volta", "Somente ida"], horizontal=True, label_visibility="collapsed")
    
    # Linha 1: Trajeto e Passageiros
    col_de, col_para, col_pax = st.columns([8, 8, 4])
    with col_de: origem_sel = st.selectbox("De", opcoes_origem)
    with col_para: destino_sel = st.selectbox("Para", opcoes_destino)
    with col_pax:
        pax_pop = st.popover("👤 Passageiros")
        with pax_pop:
            adultos = st.number_input("Adultos", 1, 9, 1)
            criancas = st.number_input("Crianças", 0, 9, 0)
            bebes = st.number_input("Bebés", 0, adultos, 0)

    # Linha 2: Datas e Busca
    col_ida, col_volta, col_btn = st.columns([5, 5, 4])
    with col_ida: data_ida = st.date_input("📅 Ida", value=datetime.today())
    with col_volta:
        if tipo_v == "Ida e volta":
            data_volta = st.date_input("📅 Volta", value=datetime.today() + timedelta(days=7))
        else:
            st.text_input("📅 Volta", value="---", disabled=True)
            data_volta = None
    with col_btn:
        btn_pesquisar = st.button("BUSCAR VOOS")

# --- LÓGICA DE BUSCA E RESULTADOS ---
if btn_pesquisar:
    if "..." in origem_sel:
        st.warning("Selecione a origem.")
    else:
        st.toast("Procurando voos...", icon="✈️")
        # Aqui entra a lógica Duffel (está completa no teu arquivo original)

if "voos" in st.session_state:
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container():
        st.markdown('<div style="background: rgba(30, 41, 59, 0.5); padding: 25px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1);">', unsafe_allow_html=True)
        st.subheader("✈️ Resultados")
        df = pd.DataFrame(st.session_state.voos)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)