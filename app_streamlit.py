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

# --- ESTILO CSS: APPLE GLASSMORPHISM REFINADO ---
st.markdown("""
    <style>
    /* 1. Fundo com Imagem */
    .stApp {
        background: url('https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1920&q=80') no-repeat center center fixed;
        background-size: cover;
    }

    /* 2. Card de Vidro Líquido (Glassmorphism) */
    [data-testid="stVerticalBlock"] > div:has(div.stButton) {
        background: rgba(255, 255, 255, 0.22) !important;
        backdrop-filter: blur(25px) !important;
        -webkit-backdrop-filter: blur(25px) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 20px !important;
        padding: 35px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2) !important;
        max-width: 1100px !important;
        margin: auto !important;
        margin-top: 40px !important;
    }

    /* 3. Inputs Unificados (Brancos/Translúcidos - Sem Preto) */
    div[data-baseweb="select"], div[data-baseweb="input"], .stDateInput div, .stNumberInput div, div[data-testid="stPopover"] > button {
        background-color: rgba(255, 255, 255, 0.7) !important;
        border: none !important;
        border-radius: 10px !important;
        color: #334155 !important;
        height: 44px !important;
    }

    /* Tipografia Suave (Grafite) */
    input, select, span, p, label {
        color: #334155 !important;
        font-weight: 500 !important;
    }
    
    label p { font-size: 0.9rem !important; margin-bottom: 2px !important; }

    /* 4. Botão de Pesquisa Compacto (Sem camadas extras) */
    div.stButton > button {
        background: #0071e3 !important;
        color: white !important;
        border-radius: 10px !important;
        height: 44px !important;
        width: 100% !important;
        border: none !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        margin-top: 25px !important;
        box-shadow: none !important;
    }
    div.stButton > button:hover {
        background: #0077ed !important;
        transform: translateY(-1px);
    }

    /* 5. Seletor de Moeda Subtil no Canto */
    .currency-trigger {
        position: absolute;
        top: 20px;
        right: 40px;
        z-index: 1000;
    }
    .currency-trigger button {
        background: rgba(255,255,255,0.3) !important;
        border: 1px solid rgba(255,255,255,0.4) !important;
        color: white !important;
        border-radius: 50% !important;
        width: 40px !important;
        height: 40px !important;
    }

    header, footer, #MainMenu {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

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
        try:
            df_atual = conn.read(worksheet="Página1", ttl=0)
            df_atual = df_atual.reindex(columns=colunas_certas) if not df_atual.empty else pd.DataFrame(columns=colunas_certas)
        except: df_atual = pd.DataFrame(columns=colunas_certas)
        novo_dado = pd.DataFrame([dados]).reindex(columns=colunas_certas)
        df_final = pd.concat([df_atual, novo_dado], ignore_index=True)
        conn.update(worksheet="Página1", data=df_final)
        st.cache_data.clear() 
        return True
    except: return False

# --- GESTÃO DE MOEDA (SÍMBOLO DISCRETO) ---
if 'moeda_simbolo' not in st.session_state:
    st.session_state.moeda_simbolo = "€"

st.markdown('<div class="currency-trigger">', unsafe_allow_html=True)
if st.button(st.session_state.moeda_simbolo):
    st.session_state.moeda_simbolo = "R$" if st.session_state.moeda_simbolo == "€" else "€"
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# --- HEADER ---
st.markdown('<h1 style="text-align: center; color: white; text-shadow: 0 4px 10px rgba(0,0,0,0.3); margin-top: -20px;">Flight Monitor</h1>', unsafe_allow_html=True)

# --- BASE DE DADOS DE CIDADES (REDUZIDA PARA O EXEMPLO) ---
cidades = {
    "Portugal": {"Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO"},
    "Brasil": {"São Paulo (GRU)": "GRU", "Rio de Janeiro (GIG)": "GIG", "Brasília (BSB)": "BSB"},
    "Mundo": {"Madrid (MAD)": "MAD", "Paris (CDG)": "CDG", "Miami (MIA)": "MIA", "Londres (LHR)": "LHR"}
}
mapa_iata = {}
opcoes_origem = ["De..."]
opcoes_destino = ["Para...", "🌍 EXPLORAR QUALQUER LUGAR"]
for regiao, items in cidades.items():
    for nome, iata in items.items():
        mapa_iata[nome] = iata
        opcoes_origem.append(nome)
        opcoes_destino.append(nome)

# --- CARD DE BUSCA REORGANIZADO ---
with st.container():
    tipo_v = st.radio("Tipo", ["Ida e volta", "Somente ida"], horizontal=True, label_visibility="collapsed")
    
    # PRIMEIRA LINHA: De, Para e Passageiros
    col_de, col_para, col_pax = st.columns([8, 8, 4])
    with col_de:
        origem_sel = st.selectbox("Origem", opcoes_origem, label_visibility="collapsed")
    with col_para:
        destino_sel = st.selectbox("Destino", opcoes_destino, label_visibility="collapsed")
    with col_pax:
        pax_pop = st.popover("👤 Passageiros")
        with pax_pop:
            adultos = st.number_input("Adultos", 1, 9, 1)
            criancas = st.number_input("Crianças", 0, 9, 0)
            bebes = st.number_input("Bebés", 0, adultos, 0)

    # SEGUNDA LINHA: Datas e Botão
    col_ida, col_volta, col_busca = st.columns([5, 5, 4])
    with col_ida:
        data_ida = st.date_input("Ida", value=datetime.today())
    with col_volta:
        if tipo_v == "Ida e volta":
            data_volta = st.date_input("Volta", value=datetime.today() + timedelta(days=7))
        else:
            st.text_input("Volta", value="---", disabled=True)
            data_volta = None
    with col_busca:
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
        except Exception as e: st.error(f"Erro: {e}")

# --- RESULTADOS E ALERTA (DENTRO DO VIDRO) ---
if "voos" in st.session_state:
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container():
        st.markdown('<div style="background: rgba(255,255,255,0.2); backdrop-filter: blur(15px); padding: 25px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.2);">', unsafe_allow_html=True)
        st.subheader("✈️ Ofertas Encontradas")
        df = pd.DataFrame(st.session_state.voos)
        st.dataframe(df, column_config={
            "Preço": st.column_config.NumberColumn(f"Preço", format=f"{st.session_state.moeda_simbolo} %.2f"),
            "Link": st.column_config.LinkColumn("Reservar", display_text="Ver Oferta ✈️")
        }, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("📬 Ativar Alerta")
        email_user = st.text_input("E-mail para vigilância:", placeholder="teu@email.com")
        if st.button("ATIVAR ALERTA"):
            if "@" in email_user:
                dados = {
                    "email": email_user, "itinerario": st.session_state.itinerario,
                    "origem": mapa_iata[origem_sel], "destino": mapa_iata[destino_sel],
                    "data": str(data_ida), "data_volta": str(data_volta) if data_volta else "",
                    "adultos": adultos, "criancas": criancas, "bebes": bebes,
                    "preco_inicial": st.session_state.voos[0]["Preço"], "moeda": st.session_state.moeda_simbolo
                }
                if guardar_alerta_planilha(dados): st.success("Alerta ativado com sucesso!")
        st.markdown("</div>", unsafe_allow_html=True)