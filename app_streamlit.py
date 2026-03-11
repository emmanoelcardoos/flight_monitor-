import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from streamlit_gsheets import GSheetsConnection

# 1. Configuração da Página (DEVE ser a primeira linha de comando Streamlit)
st.set_page_config(page_title="Flight Monitor GDS", page_icon="✈️", layout="centered")

# --- ESTILO CSS PREMIUM (GOOGLE FLIGHTS STYLE) ---
st.markdown("""
    <style>
    /* Fundo e Reset */
    .stApp {
        background-color: #f5f7fb !important;
    }
    
    /* Card Central de Busca */
    [data-testid="stVerticalBlock"] > div:has(div.stButton) {
        background-color: white !important;
        padding: 32px !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05) !important;
    }

    /* Inputs e Selects Modernos */
    div[data-baseweb="select"], div[data-baseweb="input"], .stDateInput div, .stNumberInput div {
        background-color: #ffffff !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 10px !important;
        color: #1f2937 !important;
    }
    
    input {
        color: #1f2937 !important;
        font-weight: 500 !important;
    }

    /* Labels de inputs */
    label p {
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        color: #6b7280 !important;
    }

    /* Botão Pesquisar Azul */
    .stButton > button {
        width: 100% !important;
        background-color: #2563eb !important;
        color: white !important;
        border-radius: 12px !important;
        height: 52px !important;
        font-weight: 600 !important;
        border: none !important;
    }
    .stButton > button:hover {
        background-color: #1d4ed8 !important;
        box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3) !important;
    }

    /* Esconder Menu Streamlit */
    #MainMenu, header, footer {visibility: hidden;}
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
        colunas_certas = [
            "email", "itinerario", "origem", "destino", "data", "data_volta",
            "adultos", "criancas", "bebes", "preco_inicial", "moeda"
        ]
        try:
            df_atual = conn.read(worksheet="Página1", ttl=0)
            df_atual = df_atual.reindex(columns=colunas_certas) if not df_atual.empty else pd.DataFrame(columns=colunas_certas)
        except:
            df_atual = pd.DataFrame(columns=colunas_certas)

        novo_dado = pd.DataFrame([dados]).reindex(columns=colunas_certas)
        df_final = pd.concat([df_atual, novo_dado], ignore_index=True)
        conn.update(worksheet="Página1", data=df_final)
        st.cache_data.clear() 
        return True
    except Exception as e:
        st.error(f"Erro na planilha: {e}")
        return False

def enviar_alerta_email(email_destino, itinerario, preco, moeda, origem_cod, destino_cod, data_ida):
    email_remetente = st.secrets.get("EMAIL_USER")
    senha_app = st.secrets.get("EMAIL_PASSWORD")
    if not email_remetente or not senha_app: return False

    msg = MIMEMultipart()
    msg['From'] = email_remetente
    msg['To'] = email_destino
    msg['Subject'] = f"✈️ Alerta de Preço: {itinerario}"

    corpo = f"📍 Itinerário: {itinerario}\n💰 Melhor Preço: {moeda} {preco:.2f}\n\nAbra o site para reservar!"
    msg.attach(MIMEText(corpo, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_remetente, senha_app)
        server.send_message(msg)
        server.quit()
        return True
    except: return False

# --- DADOS E PARÂMETROS ---
cidades = {
    "Portugal": {"Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO"},
    "Brasil": {"São Paulo (GRU)": "GRU", "Rio de Janeiro (GIG)": "GIG", "Brasília (BSB)": "BSB"},
    "Europa/EUA": {"Madrid (MAD)": "MAD", "Paris (CDG)": "CDG", "Londres (LHR)": "LHR", "Miami (MIA)": "MIA", "Nova York (JFK)": "JFK"}
}
mapa_iata = {}
opcoes_origem = ["Cidade ou Aeroporto..."]
opcoes_destino = ["Cidade ou Aeroporto...", "🌍 EXPLORAR QUALQUER LUGAR"]

for regiao, items in cidades.items():
    for nome, iata in items.items():
        mapa_iata[nome] = iata
        opcoes_origem.append(nome)
        opcoes_destino.append(nome)

query_params = st.query_params
idx_o = 0 # Lógica de index simplificada para o exemplo
idx_d = 0
default_date = datetime.today()

# --- INTERFACE ---
st.markdown("<h1 style='text-align: center; color: #111827;'>✈️ Flight Monitor</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #6b7280;'>Sua agência digital de monitorização de voos</p>", unsafe_allow_html=True)

# 1. Configuração de Voo
col_tipo, col_moeda = st.columns([2, 1])
with col_tipo:
    tipo_viagem = st.radio("Tipo:", ["Só Ida", "Ida e Volta"], horizontal=True, label_visibility="collapsed")
with col_moeda:
    moeda_pref = st.selectbox("Moeda", ["Euro (€)", "Real (R$)"], label_visibility="collapsed")

# 2. Card de Busca
with st.container():
    c1, c2 = st.columns(2)
    with c1: origem_sel = st.selectbox("🛫 Origem", opcoes_origem, index=idx_o)
    with c2: destino_sel = st.selectbox("🛬 Destino", opcoes_destino, index=idx_d)

    c3, c4, c5 = st.columns([1, 1, 1])
    with c3: data_ida = st.date_input("📅 Ida", value=default_date)
    with c4: 
        if tipo_viagem == "Ida e Volta":
            data_volta = st.date_input("📅 Volta", value=default_date + timedelta(days=7))
        else:
            st.text_input("📅 Volta", value="---", disabled=True)
            data_volta = None
    with c5:
        pax_pop = st.popover("👤 Passageiros")
        with pax_pop:
            adultos = st.number_input("Adultos", 1, 9, 1)
            criancas = st.number_input("Crianças", 0, 9, 0)
            bebes = st.number_input("Bebés", 0, adultos, 0)

    btn_pesquisar = st.button("Pesquisar Voos")

# --- LÓGICA DE BUSCA ---
if btn_pesquisar:
    if "Cidade" in origem_sel or "Cidade" in destino_sel:
        st.warning("Selecione origem e destino.")
    else:
        try:
            with st.spinner('Buscando as melhores ofertas...'):
                api_token = st.secrets["DUFFEL_TOKEN"]
                headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                is_br = "Real" in moeda_pref
                cotacao = get_exchange_rate()
                
                # Montar passageiros
                pax_list = [{"type": "adult"}] * adultos + [{"type": "child"}] * criancas + [{"type": "infant"}] * bebes
                
                iata_origem = mapa_iata[origem_sel]
                iata_dest = mapa_iata[destino_sel]
                
                slices = [{"origin": iata_origem, "destination": iata_dest, "departure_date": str(data_ida)}]
                if data_volta:
                    slices.append({"origin": iata_dest, "destination": iata_origem, "departure_date": str(data_volta)})

                payload = {"data": {"slices": slices, "passengers": pax_list, "requested_currencies": ["BRL" if is_br else "EUR"]}}
                res = requests.post("https://api.duffel.com/air/offer_requests", headers=headers, json=payload)
                
                if res.status_code == 201:
                    offers = requests.get(f"https://api.duffel.com/air/offers?offer_request_id={res.json()['data']['id']}&sort=total_amount", headers=headers).json().get("data", [])
                    if offers:
                        o = offers[0]
                        st.session_state.voos = [{
                            "Destino": destino_sel,
                            "Companhia": o["owner"]["name"],
                            "Preço": float(o["total_amount"]),
                            "Símbolo": "R$" if is_br else "€",
                            "Link": "https://www.skyscanner.pt" # Exemplo
                        }]
                        st.session_state.itinerario = f"{origem_sel} para {destino_sel}"
        except Exception as e: st.error(f"Erro: {e}")

# --- EXIBIÇÃO E ALERTA ---
if "voos" in st.session_state:
    st.write("### ✈️ Melhores Ofertas Encontradas")
    df_view = pd.DataFrame(st.session_state.voos)
    st.dataframe(df_view[["Companhia", "Preço", "Link"]], use_container_width=True, hide_index=True)

    st.markdown("---")
    st.write("### 📬 Ativar Alerta de Preço")
    st.info(f"Monitorando para: {adultos} Ad, {criancas} Cr, {bebes} Be")
    
    c_mail, c_btn = st.columns([3, 1])
    with c_mail: email_user = st.text_input("E-mail para alertas:", placeholder="seu@email.com")
    with c_btn:
        if st.button("Ativar Alerta"):
            if "@" in email_user:
                dados = {
                    "email": email_user, "itinerario": st.session_state.itinerario,
                    "origem": mapa_iata[origem_sel], "destino": mapa_iata[destino_sel],
                    "data": str(data_ida), "data_volta": str(data_volta) if data_volta else "",
                    "adultos": adultos, "criancas": criancas, "bebes": bebes,
                    "preco_inicial": st.session_state.voos[0]["Preço"], "moeda": st.session_state.voos[0]["Símbolo"]
                }
                if guardar_alerta_planilha(dados):
                    st.success("Alerta ativado com sucesso!")
            else: st.error("E-mail inválido.")
     