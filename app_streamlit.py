import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from streamlit_gsheets import GSheetsConnection

# 1. Configuração da Página (WIDE para o efeito de vidro ocupar o ecrã)
st.set_page_config(page_title="Flight Monitor GDS", page_icon="✈️", layout="wide")

# --- ESTILO APPLE GLASSMORPHISM COM TEXTO SUAVE ---
st.markdown("""
    <style>
    /* 1. Papel de Parede e Fundo */
    .stApp {
        background: url('https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1920&q=80') no-repeat center center fixed;
        background-size: cover;
    }

    /* 2. O Card de Vidro (Glassmorphism) */
    [data-testid="stVerticalBlock"] > div:has(div.stButton) {
        background: rgba(255, 255, 255, 0.25) !important;
        backdrop-filter: blur(25px) !important;
        -webkit-backdrop-filter: blur(25px) !important;
        border: 1px solid rgba(255, 255, 255, 0.4) !important;
        border-radius: 24px !important;
        padding: 45px !important;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1) !important;
        max-width: 1050px !important;
        margin: auto !important;
        margin-top: 50px !important;
    }

    /* 3. TIPOGRAFIA: Cores Suaves e Leitura Clara */
    /* Removemos o preto e usamos cinzas "Barrocos" suaves */
    h1, h2, h3, p, label, .stMarkdown {
        color: #4A4A4A !important;
        font-family: 'Segoe UI', Roboto, Helvetica, sans-serif !important;
    }
    
    /* Inputs: Fundo translúcido e texto nítido */
    div[data-baseweb="select"], div[data-baseweb="input"], .stDateInput div, .stNumberInput div, div[data-testid="stPopover"] > button {
        background-color: rgba(255, 255, 255, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 12px !important;
    }

    /* Ajuste específico para o texto dentro dos campos de pesquisa */
    input, select, span {
        color: #4A4A4A !important; /* Cinza suave de alto contraste */
        font-weight: 500 !important;
    }

    /* 4. O Botão de Pesquisa (Apple Blue) */
    div.stButton > button {
        background: #0071e3 !important;
        color: white !important;
        border-radius: 20px !important;
        height: 50px !important;
        width: 220px !important;
        margin: 0 auto !important;
        display: block !important;
        border: none !important;
        font-weight: 600 !important;
        font-size: 17px !important;
        box-shadow: 0 4px 15px rgba(0, 113, 227, 0.3) !important;
    }
    div.stButton > button:hover {
        background: #0077ed !important;
        transform: scale(1.02);
    }

    /* 5. Moeda Discreta no Topo Direito */
    .currency-container {
        position: absolute;
        top: 25px;
        right: 50px;
        z-index: 1000;
        width: 160px;
    }

    header, footer, #MainMenu {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- HEADER SOBRE O VIDRO ---
st.markdown("""
    <div style="text-align: center; color: white; margin-bottom: 30px;">
        <h1 style="font-size: 3.5rem; font-weight: 800; text-shadow: 0 4px 12px rgba(0,0,0,0.3); color: white !important;">Flight Monitor</h1>
        <p style="font-size: 1.2rem; opacity: 0.9; color: white !important;">Sua agência digital de monitorização de voos</p>
    </div>
    """, unsafe_allow_html=True)

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

# --- MOEDA DISCRETA ---
st.markdown('<div class="currency-container">', unsafe_allow_html=True)
moeda_pref = st.selectbox("Moeda", ["Euro (€)", "Real (R$)"], label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

# --- DADOS ---
# (Mantendo o dicionário 'cidades' igual ao que tens)
cidades = {
    "Portugal": {"Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO"},
    "Brasil": {"São Paulo (GRU)": "GRU", "Rio de Janeiro (GIG)": "GIG", "Brasília (BSB)": "BSB"},
    "Mundo": {"Madrid (MAD)": "MAD", "Paris (CDG)": "CDG", "Miami (MIA)": "MIA"}
}
mapa_iata = {}
opcoes_origem = ["De..."]
opcoes_destino = ["Para...", "🌍 EXPLORAR QUALQUER LUGAR"]
for regiao, items in cidades.items():
    for nome, iata in items.items():
        mapa_iata[nome] = iata
        opcoes_origem.append(nome)
        opcoes_destino.append(nome)

# --- CARD DE BUSCA (ESTILO VIDRO) ---
with st.container():
    tipo_v = st.radio("Tipo", ["Ida e volta", "Somente ida"], horizontal=True, label_visibility="collapsed")
    
    c1, c_swap, c2 = st.columns([10, 1, 10])
    with c1: origem_sel = st.selectbox("De", opcoes_origem)
    with c_swap: st.markdown("<div style='text-align: center; margin-top: 35px; opacity: 0.5;'>⇄</div>", unsafe_allow_html=True)
    with c2: destino_sel = st.selectbox("Para", opcoes_destino)

    c3, c4, c5 = st.columns([5, 5, 5])
    with c3: data_ida = st.date_input("Ida", value=datetime.today())
    with c4:
        if tipo_v == "Ida e volta":
            data_volta = st.date_input("Volta", value=datetime.today() + timedelta(days=7))
        else:
            st.text_input("Volta", value="---", disabled=True)
            data_volta = None
    with c5:
        pax_pop = st.popover("👤 Passageiros")
        with pax_pop:
            adultos = st.number_input("Adultos", 1, 9, 1)
            criancas = st.number_input("Crianças", 0, 9, 0)
            bebes = st.number_input("Bebés", 0, adultos, 0)

    st.markdown("<br>", unsafe_allow_html=True)
    btn_pesquisar = st.button("BUSCAR VOOS")

# --- LÓGICA DE BUSCA ---
if btn_pesquisar:
    if "..." in origem_sel or "..." in destino_sel:
        st.warning("Selecione origem e destino.")
    else:
        try:
            with st.spinner('A processar...'):
                api_token = st.secrets["DUFFEL_TOKEN"]
                headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                is_br = "Real" in moeda_pref
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
                            "Destino": destino_sel, "Companhia": o["owner"]["name"],
                            "Preço": float(o["total_amount"]), "Símbolo": "R$" if is_br else "€",
                            "Link": f"https://www.skyscanner.pt/transport/flights/{iata_origem}/{iata_dest}/{data_ida.strftime('%y%m%d')}"
                        }]
                        st.session_state.itinerario = f"{origem_sel} para {destino_sel}"
        except Exception as e: st.error(f"Erro: {e}")

# --- RESULTADOS (TAMBÉM EM VIDRO) ---
if "voos" in st.session_state:
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container():
        st.markdown("""<div style="background: rgba(255,255,255,0.3); backdrop-filter: blur(15px); padding: 25px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.2);">""", unsafe_allow_html=True)
        st.subheader("✈️ Ofertas Encontradas")
        df = pd.DataFrame(st.session_state.voos)
        simb = st.session_state.voos[0]["Símbolo"]
        st.dataframe(df[["Companhia", "Preço", "Link"]], column_config={
            "Preço": st.column_config.NumberColumn(f"Preço ({simb})", format=f"{simb} %.2f"),
            "Link": st.column_config.LinkColumn("Reservar", display_text="Ver Oferta ✈️")
        }, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("📬 Ativar Alerta")
        email_user = st.text_input("E-mail:", placeholder="teu@email.com")
        if st.button("Ativar"):
            if "@" in email_user:
                dados = {"email": email_user, "itinerario": st.session_state.itinerario, "origem": mapa_iata[origem_sel], "destino": mapa_iata[destino_sel], "data": str(data_ida), "data_volta": str(data_volta) if data_volta else "", "adultos": adultos, "criancas": criancas, "bebes": bebes, "preco_inicial": st.session_state.voos[0]["Preço"], "moeda": simb}
                if guardar_alerta_planilha(dados): st.success("Alerta ativo!")
        st.markdown("</div>", unsafe_allow_html=True)