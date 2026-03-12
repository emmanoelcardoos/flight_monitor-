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

# --- DESIGN DARK MODERNO COM MOEDA INTEGRADA ---
st.markdown("""
    <style>
    /* Fundo Gradiente Midnight */
    .stApp {
        background: radial-gradient(circle at top right, #1e293b, #0f172a) !important;
        color: #f1f5f9 !important;
    }

    /* Card de Vidro Principal */
    [data-testid="stVerticalBlock"] > div:has(div.stButton) {
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 20px !important;
        padding: 40px !important;
        max-width: 1200px !important;
        margin: auto !important;
        margin-top: 30px !important;
    }

    /* Inputs, Selects, Popover e Botão Moeda (Cores Claras e Alinhadas) */
    div[data-baseweb="select"], div[data-baseweb="input"], .stDateInput div, 
    div[data-testid="stPopover"] > button, .stButton > button[kind="secondary"] {
        background-color: rgba(255, 255, 255, 0.9) !important;
        border: none !important;
        border-radius: 10px !important;
        height: 45px !important;
        color: #1e293b !important;
    }

    /* Cor do texto global para inputs */
    input, select, span, p, label {
        color: #1e293b !important;
        font-weight: 500 !important;
    }

    /* Botão BUSCAR VOOS (Azul Limpo e Alinhado) */
    div.stButton > button[kind="primary"] {
        background-color: #3b82f6 !important;
        color: white !important;
        border-radius: 10px !important;
        height: 45px !important;
        width: 100% !important;
        border: none !important;
        font-weight: 700 !important;
        margin-top: 0px !important;
        box-shadow: none !important;
    }

    div.stButton > button[kind="primary"]:hover {
        background-color: #2563eb !important;
    }

    /* Título Moderno */
    .main-title {
        font-size: 3.5rem;
        font-weight: 900;
        text-align: center;
        background: linear-gradient(to right, #60a5fa, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-top: 20px;
    }

    /* Esconder Menu e Rodapé */
    header, footer, #MainMenu {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO DE ESTADO ---
if 'moeda_simbolo' not in st.session_state:
    st.session_state.moeda_simbolo = "€"
if 'voos' not in st.session_state:
    st.session_state.voos = None

# --- FUNÇÕES DE LÓGICA ---
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

def enviar_alerta_email(email_destino, itinerario, preco, moeda, orig, dest, data_ida):
    email_remetente = st.secrets.get("EMAIL_USER")
    senha_app = st.secrets.get("EMAIL_PASSWORD")
    if not email_remetente or not senha_app: return False
    msg = MIMEMultipart()
    msg['From'] = email_remetente
    msg['To'] = email_destino
    msg['Subject'] = f"✈️ Alerta Ativado: {itinerario}"
    corpo = f"O seu alerta para {itinerario} foi configurado com o preço base de {moeda} {preco:.2f}."
    msg.attach(MIMEText(corpo, 'plain'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_remetente, senha_app)
        server.send_message(msg)
        server.quit()
        return True
    except: return False

# --- TÍTULO ---
st.markdown('<h1 class="main-title">Flight Monitor</h1>', unsafe_allow_html=True)

# --- DADOS DE CIDADES ---
cidades = {
    "Brasil": {"São Paulo (GRU)": "GRU", "Rio de Janeiro (GIG)": "GIG", "Brasília (BSB)": "BSB"},
    "Portugal": {"Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO"},
    "Mundo": {"Paris (CDG)": "CDG", "Madrid (MAD)": "MAD", "Londres (LHR)": "LHR", "Miami (MIA)": "MIA"}
}
mapa_iata = {}
opcoes = ["De/Para..."]
for regiao, items in cidades.items():
    for nome, iata in items.items():
        mapa_iata[nome] = iata
        opcoes.append(nome)

# --- CARD DE BUSCA REORGANIZADO ---
with st.container():
    tipo_v = st.radio("Config", ["Ida e volta", "Somente ida"], horizontal=True, label_visibility="collapsed")
    
    # LINHA 1: De | Para | Passageiros | Moeda
    c1, c2, c3, c4 = st.columns([7, 7, 4, 2])
    with c1: origem_sel = st.selectbox("De", opcoes, label_visibility="collapsed")
    with c2: destino_sel = st.selectbox("Para", opcoes, label_visibility="collapsed")
    with c3:
        pax_pop = st.popover("👤 Passageiros", use_container_width=True)
        with pax_pop:
            adultos = st.number_input("Adultos", 1, 9, 1)
            criancas = st.number_input("Crianças", 0, 9, 0)
            bebes = st.number_input("Bebés", 0, adultos, 0)
    with c4:
        # Botão de Moeda Subtil e Alinhado
        if st.button(st.session_state.moeda_simbolo, kind="secondary", use_container_width=True):
            st.session_state.moeda_simbolo = "R$" if st.session_state.moeda_simbolo == "€" else "€"
            st.rerun()

    st.markdown("<div style='margin: 10px;'></div>", unsafe_allow_html=True)

    # LINHA 2: Ida | Volta | Botão Buscar (Alinhamento Perfeito)
    c5, c6, c7 = st.columns([7, 7, 6])
    with c5: data_ida = st.date_input("Data Ida", value=datetime.today(), label_visibility="collapsed")
    with c6:
        if tipo_v == "Ida e volta":
            data_volta = st.date_input("Data Volta", value=datetime.today() + timedelta(days=7), label_visibility="collapsed")
        else:
            st.text_input("Volta", value="---", disabled=True, label_visibility="collapsed")
            data_volta = None
    with c7:
        btn_pesquisar = st.button("BUSCAR VOOS", kind="primary", use_container_width=True)

# --- LÓGICA DE BUSCA ---
if btn_pesquisar:
    if "..." in origem_sel or "..." in destino_sel:
        st.warning("⚠️ Selecione a origem e o destino.")
    else:
        try:
            with st.spinner('🔎 Procurando ofertas...'):
                api_token = st.secrets.get("DUFFEL_TOKEN")
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
                    else: st.warning("Nenhum voo encontrado.")
        except Exception as e: st.error(f"Erro: {e}")

# --- RESULTADOS E ALERTA ---
if st.session_state.voos:
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container():
        st.markdown('<div style="background: rgba(255,255,255,0.1); backdrop-filter: blur(15px); padding: 25px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1);">', unsafe_allow_html=True)
        st.subheader("✈️ Resultados da Pesquisa")
        df = pd.DataFrame(st.session_state.voos)
        st.dataframe(df, column_config={
            "Preço": st.column_config.NumberColumn("Preço", format=f"{st.session_state.moeda_simbolo} %.2f"),
            "Link": st.column_config.LinkColumn("Reservar", display_text="Ver Oferta ✈️")
        }, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("📬 Ativar Alerta de Preço")
        email_user = st.text_input("O teu e-mail:", placeholder="exemplo@gmail.com", key="email_alert")
        if st.button("ATIVAR ALERTA", kind="primary"):
            if "@" in email_user:
                dados = {
                    "email": email_user, "itinerario": st.session_state.itinerario,
                    "origem": mapa_iata[origem_sel], "destino": mapa_iata[destino_sel],
                    "data": str(data_ida), "data_volta": str(data_volta) if data_volta else "",
                    "adultos": adultos, "criancas": criancas, "bebes": bebes,
                    "preco_inicial": st.session_state.voos[0]["Preço"], "moeda": st.session_state.moeda_simbolo
                }
                if guardar_alerta_planilha(dados):
                    enviar_alerta_email(email_user, st.session_state.itinerario, st.session_state.voos[0]["Preço"], st.session_state.moeda_simbolo, mapa_iata[origem_sel], mapa_iata[destino_sel], data_ida)
                    st.success("✅ Alerta ativo! Receberá um e-mail se o preço baixar.")
        st.markdown('</div>', unsafe_allow_html=True)