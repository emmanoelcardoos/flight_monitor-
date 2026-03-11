import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from streamlit_gsheets import GSheetsConnection

# 1. Configuração da Página (WIDE para a imagem de fundo ocupar tudo)
st.set_page_config(page_title="Flight Monitor GDS", page_icon="✈️", layout="wide")

# --- ESTILO CSS PORTAL DE VIAGENS (GOTOGATE STYLE) ---
st.markdown("""
    <style>
    /* 1. Imagem de Fundo Hero */
    .stApp {
        background: linear-gradient(rgba(0,0,0,0.3), rgba(0,0,0,0.3)), 
                    url('https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1920&q=80');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    
    /* 2. Centralizar Card de Busca */
    [data-testid="stVerticalBlock"] > div:has(div.stButton) {
        background-color: rgba(255, 255, 255, 0.98) !important;
        padding: 40px !important;
        border-radius: 12px !important;
        box-shadow: 0 12px 40px rgba(0,0,0,0.4) !important;
        max-width: 1050px !important;
        margin: auto !important;
        margin-top: 50px !important;
    }

    /* 3. Inputs Suaves (Fim do Preto) */
    div[data-baseweb="select"], div[data-baseweb="input"], .stDateInput div, .stNumberInput div, div[data-testid="stPopover"] > button {
        background-color: #F8FAFC !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 6px !important;
        color: #334155 !important;
    }

    /* Forçar cores de texto */
    input, select, span, p, label {
        color: #334155 !important;
        font-weight: 500 !important;
    }

    /* 4. Botão "Gotogate Blue" */
    .stButton > button {
        background-color: #40D1FB !important; 
        color: white !important;
        border-radius: 6px !important;
        height: 52px !important;
        font-weight: 700 !important;
        font-size: 18px !important;
        border: none !important;
        text-transform: uppercase;
        width: 100% !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button:hover {
        background-color: #00B4EB !important;
        transform: scale(1.02);
    }

    /* 5. Títulos Hero */
    .hero-container {
        text-align: center;
        padding: 40px 0;
        color: white;
    }

    /* Esconder Menu e Footer */
    header, footer, #MainMenu {visibility: hidden;}
    </style>

    <div class="hero-container">
        <h1 style="font-size: 4rem; font-weight: 900; text-shadow: 2px 2px 8px rgba(0,0,0,0.5);">Reserve Voos Baratos</h1>
        <p style="font-size: 1.5rem; text-shadow: 1px 1px 4px rgba(0,0,0,0.5);">Sua agência digital de monitorização de voos</p>
    </div>
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
        try:
            df_atual = conn.read(worksheet="Página1", ttl=0)
            df_atual = df_atual.reindex(columns=colunas_certas) if not df_atual.empty else pd.DataFrame(columns=colunas_certas)
        except: df_atual = pd.DataFrame(columns=colunas_certas)
        novo_dado = pd.DataFrame([dados]).reindex(columns=colunas_certas)
        df_final = pd.concat([df_atual, novo_dado], ignore_index=True)
        conn.update(worksheet="Página1", data=df_final)
        st.cache_data.clear() 
        return True
    except Exception as e:
        st.error(f"Erro na planilha: {e}")
        return False

# --- DADOS ---
cidades = {

    "Brasil - Sudeste": {
        "São Paulo (GRU)": "GRU",
        "São Paulo (CGH)": "CGH",
        "Campinas (VCP)": "VCP",
        "Rio de Janeiro (GIG)": "GIG",
        "Rio de Janeiro (SDU)": "SDU",
        "Belo Horizonte (CNF)": "CNF",
        "Belo Horizonte (PLU)": "PLU",
        "Vitória (VIX)": "VIX"
    },

    "Brasil - Sul": {
        "Curitiba (CWB)": "CWB",
        "Florianópolis (FLN)": "FLN",
        "Porto Alegre (POA)": "POA",
        "Foz do Iguaçu (IGU)": "IGU",
        "Navegantes (NVT)": "NVT",
        "Londrina (LDB)": "LDB"
    },

    "Brasil - Centro-Oeste": {
        "Brasília (BSB)": "BSB",
        "Goiânia (GYN)": "GYN",
        "Cuiabá (CGB)": "CGB",
        "Campo Grande (CGR)": "CGR"
    },

    "Brasil - Nordeste": {
        "Salvador (SSA)": "SSA",
        "Recife (REC)": "REC",
        "Fortaleza (FOR)": "FOR",
        "Natal (NAT)": "NAT",
        "Maceió (MCZ)": "MCZ",
        "João Pessoa (JPA)": "JPA",
        "Aracaju (AJU)": "AJU",
        "Porto Seguro (BPS)": "BPS",
        "Ilhéus (IOS)": "IOS"
    },

    "Brasil - Norte": {
        "Manaus (MAO)": "MAO",
        "Belém (BEL)": "BEL",
        "Porto Velho (PVH)": "PVH",
        "Rio Branco (RBR)": "RBR",
        "Macapá (MCP)": "MCP",
        "Boa Vista (BVB)": "BVB",
        "Palmas (PMW)": "PMW",
        "Marabá (MAB)": "MAB",
        "Parauapebas / Carajás (CKS)": "CKS",
        "Araguaína (AUX)": "AUX"

    },

    "Portugal": {
        "Lisboa (LIS)": "LIS",
        "Porto (OPO)": "OPO",
        "Funchal (FNC)": "FNC",
        "Ponta Delgada (PDL)": "PDL"
    },

    "Europa": {
        "Madrid (MAD)": "MAD",
        "Barcelona (BCN)": "BCN",
        "Paris (CDG)": "CDG",
        "Paris Orly (ORY)": "ORY",
        "Londres Heathrow (LHR)": "LHR",
        "Londres Gatwick (LGW)": "LGW",
        "Roma (FCO)": "FCO",
        "Milão (MXP)": "MXP",
        "Frankfurt (FRA)": "FRA",
        "Munique (MUC)": "MUC",
        "Zurique (ZRH)": "ZRH",
        "Amsterdã (AMS)": "AMS",
        "Bruxelas (BRU)": "BRU",
        "Copenhaga (CPH)": "CPH",
        "Istambul (IST)": "IST",
        "Lisboa (LIS)": "LIS",
        "Porto (OPO)": "OPO"
    },

    "Estados Unidos": {
        "Miami (MIA)": "MIA",
        "Orlando (MCO)": "MCO",
        "Fort Lauderdale (FLL)": "FLL",
        "Nova York JFK (JFK)": "JFK",
        "Nova York Newark (EWR)": "EWR",
        "Atlanta (ATL)": "ATL",
        "Dallas (DFW)": "DFW",
        "Houston (IAH)": "IAH",
        "Chicago (ORD)": "ORD",
        "Los Angeles (LAX)": "LAX",
        "San Francisco (SFO)": "SFO",
        "Washington (IAD)": "IAD",
        "Boston (BOS)": "BOS"
    },

    "África": {
        "Luanda (LAD)": "LAD",
        "Joanesburgo (JNB)": "JNB",
        "Cidade do Cabo (CPT)": "CPT",
        "Casablanca (CMN)": "CMN",
        "Addis Abeba (ADD)": "ADD"
    }
}
mapa_iata = {}
opcoes_origem = ["De..."]
opcoes_destino = ["Para...", "🌍 EXPLORAR QUALQUER LUGAR"]
for regiao, items in cidades.items():
    for nome, iata in items.items():
        mapa_iata[nome] = iata
        opcoes_origem.append(nome)
        opcoes_destino.append(nome)

# --- INTERFACE DE BUSCA ---
with st.container():
    # Tipo de Viagem
    tipo_viagem = st.radio("Tipo", ["Ida e volta", "Somente ida"], horizontal=True, label_visibility="collapsed")
    
    # Origem e Destino
    c1, c_swap, c2 = st.columns([10, 1, 10])
    with c1: origem_sel = st.selectbox("De", opcoes_origem)
    with c_swap: st.markdown("<div style='text-align: center; margin-top: 35px;'>⇄</div>", unsafe_allow_html=True)
    with c2: destino_sel = st.selectbox("Para", opcoes_destino)

    # Datas, Passageiros e Moeda
    c3, c4, c5, c6 = st.columns([4, 4, 4, 4])
    with c3: data_ida = st.date_input("Ida", value=datetime.today())
    with c4:
        if tipo_viagem == "Ida e volta":
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
    with c6:
        moeda_pref = st.selectbox("Moeda", ["Euro (€)", "Real (R$)"])

    btn_pesquisar = st.button("Buscar voos")

# --- LÓGICA DE BUSCA ---
if btn_pesquisar:
    if "..." in origem_sel or "..." in destino_sel:
        st.warning("Selecione origem e destino.")
    else:
        try:
            with st.spinner('Procurando as melhores tarifas...'):
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

# --- EXIBIÇÃO DE RESULTADOS ---
if "voos" in st.session_state:
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container():
        st.markdown("<div style='background-color: white; padding: 25px; border-radius: 12px; border: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
        st.subheader("✈️ Ofertas Encontradas")
        df = pd.DataFrame(st.session_state.voos)
        simb = st.session_state.voos[0]["Símbolo"]
        st.dataframe(df[["Companhia", "Preço", "Link"]], column_config={
            "Preço": st.column_config.NumberColumn(f"Preço ({simb})", format=f"{simb} %.2f"),
            "Link": st.column_config.LinkColumn("Reservar", display_text="Ver Oferta ✈️")
        }, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("📬 Ativar Alerta")
        st.info(f"Vigilância ativa para {adultos} Adulto(s) e {criancas+bebes} Criança(s)")
        c_mail, c_btn = st.columns([3, 1])
        with c_mail: email_user = st.text_input("Teu e-mail:", placeholder="exemplo@gmail.com")
        with c_btn:
            if st.button("Ativar"):
                if "@" in email_user:
                    dados = {"email": email_user, "itinerario": st.session_state.itinerario, "origem": mapa_iata[origem_sel], "destino": mapa_iata[destino_sel], "data": str(data_ida), "data_volta": str(data_volta) if data_volta else "", "adultos": adultos, "criancas": criancas, "bebes": bebes, "preco_inicial": st.session_state.voos[0]["Preço"], "moeda": simb}
                    if guardar_alerta_planilha(dados): st.success("Alerta ativo!")
        st.markdown("</div>", unsafe_allow_html=True)