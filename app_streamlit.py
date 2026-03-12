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

# --- ESTILO CSS MODERNO E PROFISSIONAL ---
st.markdown("""
    <style>
    /* 1. Fundo com gradiente suave */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        background-attachment: fixed;
    }

    /* 2. Card Central Branco */
    .main-card {
        background: white !important;
        border-radius: 16px !important;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1) !important;
        padding: 32px !important;
        max-width: 900px !important;
        margin: 0 auto !important;
        margin-top: 40px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }

    /* 3. Inputs estilizados */
    div[data-baseweb="select"], div[data-baseweb="input"], .stDateInput div, .stNumberInput div {
        background-color: white !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 10px !important;
        min-height: 44px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    }

    div[data-baseweb="select"]:hover, div[data-baseweb="input"]:hover, .stDateInput div:hover {
        border-color: #2563eb !important;
    }

    /* Labels dos campos */
    .stSelectbox label, .stDateInput label, .stNumberInput label, div[data-testid="stPopover"] label {
        color: #4b5563 !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        margin-bottom: 4px !important;
    }

    input, select, textarea {
        color: #1f2937 !important;
        font-weight: 400 !important;
    }

    /* Placeholders */
    input::placeholder {
        color: #9ca3af !important;
        opacity: 1 !important;
    }

    /* 4. Botão de pesquisa principal */
    div.stButton > button {
        background: #2563eb !important;
        color: white !important;
        border-radius: 12px !important;
        height: 48px !important;
        width: 100% !important;
        border: none !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        letter-spacing: 0.5px !important;
        box-shadow: 0 4px 6px rgba(37, 99, 235, 0.25) !important;
        transition: all 0.2s ease !important;
        margin-top: 24px !important;
    }
    
    div.stButton > button:hover {
        background: #1d4ed8 !important;
        box-shadow: 0 6px 8px rgba(37, 99, 235, 0.3) !important;
        transform: translateY(-1px) !important;
    }

    /* 5. Botão de troca (pequeno) */
    .swap-button {
        background: white !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 50% !important;
        width: 32px !important;
        height: 32px !important;
        padding: 0 !important;
        min-width: 32px !important;
        margin: 0 auto !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
    }
    
    .swap-button:hover {
        background: #f9fafb !important;
        border-color: #2563eb !important;
    }

    /* 6. Botão segmentado para tipo de viagem */
    div[data-testid="stRadio"] > div {
        background: #f3f4f6 !important;
        border-radius: 10px !important;
        padding: 4px !important;
        gap: 4px !important;
    }
    
    div[data-testid="stRadio"] label {
        background: transparent !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        color: #6b7280 !important;
        font-weight: 500 !important;
        transition: all 0.2s !important;
    }
    
    div[data-testid="stRadio"] label[data-checked="true"] {
        background: white !important;
        color: #2563eb !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
    }

    /* 7. Popover de passageiros */
    div[data-testid="stPopover"] > button {
        background: white !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 10px !important;
        height: 44px !important;
        width: 100% !important;
        color: #1f2937 !important;
        font-weight: 400 !important;
        text-align: left !important;
        padding: 0 12px !important;
    }

    /* 8. Título principal */
    .main-title {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-size: 2.5rem;
        font-weight: 600;
        text-align: center;
        color: white;
        margin-bottom: 4px;
        letter-spacing: -0.5px;
    }
    
    .sub-title {
        text-align: center;
        color: rgba(255, 255, 255, 0.9);
        font-size: 1rem;
        margin-bottom: 0;
        font-weight: 400;
    }

    /* 9. Logo container */
    .logo-container {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        margin-bottom: 16px;
    }
    
    .logo-icon {
        font-size: 2rem;
    }

    /* 10. Ícones nos inputs */
    .input-icon {
        position: relative;
    }
    
    .input-icon i {
        position: absolute;
        left: 12px;
        top: 50%;
        transform: translateY(-50%);
        color: #9ca3af;
    }

    /* 11. Resultados */
    .results-card {
        background: white !important;
        border-radius: 16px !important;
        padding: 24px !important;
        margin-top: 32px !important;
        max-width: 900px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1) !important;
    }

    /* 12. Moeda no canto */
    .currency-container {
        position: fixed;
        top: 20px;
        right: 30px;
        z-index: 9999;
    }
    
    .currency-container button {
        background: rgba(255, 255, 255, 0.2) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        color: white !important;
        border-radius: 12px !important;
        width: 44px !important;
        height: 44px !important;
        font-weight: 600 !important;
        backdrop-filter: blur(10px);
        font-size: 1.1rem !important;
    }

    /* 13. Esconder elementos padrão */
    header, footer, #MainMenu {visibility: hidden;}
    
    /* 14. Espaçamentos */
    .stColumn {
        gap: 16px !important;
    }
    
    div[data-testid="column"] {
        gap: 0px !important;
    }
    
    /* 15. Input desabilitado */
    .stTextInput input:disabled {
        background: #f3f4f6 !important;
        border-color: #e5e7eb !important;
        color: #9ca3af !important;
    }
    </style>
    
    <!-- Font Awesome para ícones -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    """, unsafe_allow_html=True)

# --- MOEDA NO CANTO SUPERIOR DIREITO ---
if 'moeda_simbolo' not in st.session_state:
    st.session_state.moeda_simbolo = "€"

st.markdown('<div class="currency-container">', unsafe_allow_html=True)
if st.button(st.session_state.moeda_simbolo, key="curr_btn"):
    st.session_state.moeda_simbolo = "R$" if st.session_state.moeda_simbolo == "€" else "€"
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# --- HEADER COM LOGO ---
st.markdown("""
    <div class="logo-container">
        <span class="logo-icon">✈️</span>
        <h1 class="main-title">Flight Monitor</h1>
    </div>
    <p class="sub-title">Encontre e monitorize voos em tempo real</p>
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

# --- DADOS ---
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

# --- CARD DE BUSCA PRINCIPAL ---
with st.container():
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    
    # Primeira Linha: Origem e Destino com botão de troca
    col1, col_swap, col2 = st.columns([5, 1, 5])
    
    with col1:
        origem_sel = st.selectbox("📍 Origem", opcoes_origem, key="origem")
    
    with col_swap:
        st.markdown('<div style="margin-top: 24px;">', unsafe_allow_html=True)
        if st.button("⇄", key="swap_btn"):
            # Lógica para trocar origem/destino
            if 'origem_sel' in locals() and 'destino_sel' in locals():
                temp = origem_sel
                origem_sel = destino_sel if destino_sel not in ["Para...", "🌍 EXPLORAR QUALQUER LUGAR"] else "De..."
                destino_sel = temp if temp not in ["De..."] else "Para..."
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        destino_sel = st.selectbox("📍 Destino", opcoes_destino, key="destino")
    
    # Segunda Linha: Tipo de viagem e Datas
    tipo_v = st.radio("", ["Ida e volta", "Somente ida"], horizontal=True, label_visibility="collapsed")
    
    col_data1, col_data2 = st.columns(2)
    
    with col_data1:
        data_ida = st.date_input("📅 Ida", value=datetime.today())
    
    with col_data2:
        if tipo_v == "Ida e volta":
            data_volta = st.date_input("📅 Volta", value=datetime.today() + timedelta(days=7))
        else:
            st.text_input("📅 Volta", value="---", disabled=True)
            data_volta = None
    
    # Terceira Linha: Passageiros
    with st.popover("👥 Passageiros"):
        st.markdown("### Passageiros")
        adultos = st.number_input("Adultos (12+ anos)", 1, 9, 1)
        criancas = st.number_input("Crianças (2-11 anos)", 0, 9, 0)
        bebes = st.number_input("Bebés (0-23 meses)", 0, adultos, 0)
    
    # Botão de pesquisa
    btn_pesquisar = st.button("🔍 PESQUISAR VOOS", use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- LÓGICA DE BUSCA ---
if btn_pesquisar:
    if "..." in origem_sel or "..." in destino_sel or destino_sel == "🌍 EXPLORAR QUALQUER LUGAR":
        st.warning("Por favor, selecione origem e destino válidos.")
    else:
        try:
            with st.spinner('Buscando as melhores ofertas...'):
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
                        st.info("Nenhum voo encontrado para esta rota.")
        except Exception as e: st.error(f"Erro na busca: {e}")

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
    st.subheader("📬 Ativar Alerta de Preço")
    email_user = st.text_input("Seu e-mail", placeholder="exemplo@email.com")
    if st.button("ATIVAR ALERTA", use_container_width=True):
        if "@" in email_user:
            dados = {"email": email_user, "itinerario": st.session_state.itinerario, "origem": mapa_iata[origem_sel], "destino": mapa_iata[destino_sel], "data": str(data_ida), "data_volta": str(data_volta) if data_volta else "", "adultos": adultos, "criancas": criancas, "bebes": bebes, "preco_inicial": st.session_state.voos[0]["Preço"], "moeda": st.session_state.moeda_simbolo}
            if guardar_alerta_planilha(dados): 
                st.success("✅ Alerta ativado com sucesso! Você será notificado sobre mudanças de preço.")
        else:
            st.error("Por favor, insira um e-mail válido.")
    
    st.markdown('</div>', unsafe_allow_html=True)