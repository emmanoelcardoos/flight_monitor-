import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 1. Configuração da Página
st.set_page_config(page_title="Flight Monitor GDS", page_icon="✈️", layout="wide")

# --- FUNÇÕES DE APOIO ---
def enviar_alerta_email(email_destino, itinerario, preco, moeda):
    email_remetente = st.secrets.get("EMAIL_USER")
    senha_app = st.secrets.get("EMAIL_PASSWORD")
    if not email_remetente or not senha_app: return False
    msg = MIMEMultipart()
    msg['From'] = email_remetente
    msg['To'] = email_destino
    msg['Subject'] = f"✈️ Alerta de Preço: {itinerario}"
    corpo = f"Olá!\n\nEncontrámos uma oferta para {itinerario} por {moeda} {preco:.2f}.\nVerifica no teu site!"
    msg.attach(MIMEText(corpo, 'plain'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_remetente, senha_app)
        server.send_message(msg)
        server.quit()
        return True
    except: return False

def get_exchange_rate():
    try:
        res = requests.get("https://open.er-api.com/v6/latest/EUR")
        return res.json()["rates"]["BRL"]
    except: return 6.15

# --- BASE DE DADOS DE CIDADES ---
cidades = {
    "Brasil - Sudeste": {"São Paulo (GRU)": "GRU", "São Paulo (CGH)": "CGH", "Campinas (VCP)": "VCP", "Rio de Janeiro (GIG)": "GIG", "Rio de Janeiro (SDU)": "SDU", "Belo Horizonte (CNF)": "CNF", "Belo Horizonte (PLU)": "PLU", "Vitória (VIX)": "VIX"},
    "Brasil - Sul": {"Curitiba (CWB)": "CWB", "Florianópolis (FLN)": "FLN", "Porto Alegre (POA)": "POA", "Foz do Iguaçu (IGU)": "IGU", "Navegantes (NVT)": "NVT", "Londrina (LDB)": "LDB"},
    "Brasil - Centro-Oeste": {"Brasília (BSB)": "BSB", "Goiânia (GYN)": "GYN", "Cuiabá (CGB)": "CGB", "Campo Grande (CGR)": "CGR"},
    "Brasil - Nordeste": {"Salvador (SSA)": "SSA", "Recife (REC)": "REC", "Fortaleza (FOR)": "FOR", "Natal (NAT)": "NAT", "Maceió (MCZ)": "MCZ", "João Pessoa (JPA)": "JPA", "Aracaju (AJU)": "AJU", "Porto Seguro (BPS)": "BPS", "Ilhéus (IOS)": "IOS"},
    "Brasil - Norte": {"Manaus (MAO)": "MAO", "Belém (BEL)": "BEL", "Porto Velho (PVH)": "PVH", "Rio Branco (RBR)": "RBR", "Macapá (MCP)": "MCP", "Boa Vista (BVB)": "BVB", "Palmas (PMW)": "PMW", "Marabá (MAB)": "MAB", "Parauapebas (Carajás)": "CKS"},
    "Portugal": {"Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO", "Funchal (FNC)": "FNC", "Ponta Delgada (PDL)": "PDL"},
    "Europa": {"Madrid (MAD)": "MAD", "Barcelona (BCN)": "BCN", "Paris (CDG)": "CDG", "Paris Orly (ORY)": "ORY", "Londres Heathrow (LHR)": "LHR", "Londres Gatwick (LGW)": "LGW", "Roma (FCO)": "FCO", "Milão (MXP)": "MXP", "Frankfurt (FRA)": "FRA", "Munique (MUC)": "MUC", "Zurique (ZRH)": "ZRH", "Amsterdã (AMS)": "AMS", "Bruxelas (BRU)": "BRU", "Copenhaga (CPH)": "CPH", "Istambul (IST)": "IST"},
    "Estados Unidos": {"Miami (MIA)": "MIA", "Orlando (MCO)": "MCO", "Fort Lauderdale (FLL)": "FLL", "Nova York JFK (JFK)": "JFK", "Nova York Newark (EWR)": "EWR", "Atlanta (ATL)": "ATL", "Dallas (DFW)": "DFW", "Houston (IAH)": "IAH", "Chicago (ORD)": "ORD", "Los Angeles (LAX)": "LAX", "San Francisco (SFO)": "SFO", "Washington (IAD)": "IAD", "Boston (BOS)": "BOS"},
    "África": {"Luanda (LAD)": "LAD", "Joanesburgo (JNB)": "JNB", "Cidade do Cabo (CPT)": "CPT", "Casablanca (CMN)": "CMN", "Addis Abeba (ADD)": "ADD"}
}

destinos_explorar_lista = ["LIS", "OPO", "MAD", "BCN", "PAR", "LHR", "FCO", "FRA", "AMS", "GRU", "GIG", "BSB", "MIA", "JFK", "LAD", "CMN"]

mapa_iata = {}
opcoes_origem = ["Cidade ou Aeroporto..."]
opcoes_destino = ["Cidade ou Aeroporto...", "🌍 EXPLORAR QUALQUER LUGAR"]

for regiao, items in cidades.items():
    for nome, iata in items.items():
        mapa_iata[nome] = iata
        opcoes_origem.append(nome)
        opcoes_destino.append(nome)

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    [data-testid="stSelectbox"] svg { display: none; }
    .stSelectbox div[data-baseweb="select"] { border-radius: 20px; }
    /* Estilo para diminuir o espaço entre elementos */
    .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

# --- INTERFACE (CABEÇALHO) ---
# Dividimos o topo em 2: Título e Moeda
header_col1, header_col2 = st.columns([4, 1])

with header_col1:
    st.title("🌍 Flight Monitor - Buscador GDS")
    tipo_viagem = st.radio("Configuração:", ["Só Ida/Volta", "Ida e Volta"], horizontal=True, label_visibility="collapsed")

with header_col2:
    st.write("") # Espaçamento
    moeda_pref = st.selectbox("Moeda", ["Euro (€) - (.PT)", "Real (R$) - (.BR)"], key="moeda_header")

st.write("---")

# --- BARRA DE PESQUISA (LINHA ÚNICA ALINHADA) ---
col1, col2, col3, col4, col5 = st.columns([2.5, 2.5, 1.5, 1.5, 1])

with col1:
    origem_sel = st.selectbox("Origem", options=opcoes_origem, index=0, key="origem", label_visibility="collapsed")
with col2:
    destino_sel = st.selectbox("Destino", options=opcoes_destino, index=0, key="destino", label_visibility="collapsed")
with col3:
    data_ida = st.date_input("Ida", min_value=datetime.today(), label_visibility="collapsed")
with col4:
    if tipo_viagem == "Ida e Volta":
        data_volta = st.date_input("Volta", min_value=data_ida + timedelta(days=1), label_visibility="collapsed")
    else:
        data_volta = None
        st.button("Calendário", disabled=True, use_container_width=True) # Apenas para manter o alinhamento visual
with col5:
    btn_pesquisar = st.button("Pesquisar", use_container_width=True)

# --- LÓGICA DE BUSCA ---
if btn_pesquisar:
    if origem_sel == "Cidade ou Aeroporto..." or destino_sel == "Cidade ou Aeroporto...":
        st.warning("⚠️ Selecione a Origem e o Destino.")
    else:
        try:
            mapa_nomes = {v: k for k, v in mapa_iata.items()}
            with st.spinner('A pesquisar...'):
                api_token = st.secrets.get("DUFFEL_TOKEN")
                headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                cotacao = get_exchange_rate()
                is_br = "Real" in moeda_pref
                iata_origem = mapa_iata[origem_sel]
                
                lista_destinos = [d for d in destinos_explorar_lista if d != iata_origem] if destino_sel == "🌍 EXPLORAR QUALQUER LUGAR" else [mapa_iata[destino_sel]]

                resultados = []
                for iata_dest in lista_destinos:
                    slices = [{"origin": iata_origem, "destination": iata_dest, "departure_date": str(data_ida)}]
                    if data_volta:
                        slices.append({"origin": iata_dest, "destination": iata_origem, "departure_date": str(data_volta)})
                    
                    payload = {"data": {"slices": slices, "passengers": [{"type": "adult"}], "requested_currencies": ["BRL" if is_br else "EUR"]}}
                    res = requests.post("https://api.duffel.com/air/offer_requests", headers=headers, json=payload)
                    
                    if res.status_code == 201:
                        offers = requests.get(f"https://api.duffel.com/air/offers?offer_request_id={res.json()['data']['id']}&sort=total_amount", headers=headers).json().get("data", [])
                        if offers:
                            o = offers[0]
                            preco_exibicao = float(o["total_amount"])
                            if not is_br and o["total_currency"] == "BRL": preco_exibicao /= cotacao
                            if is_br and o["total_currency"] == "EUR": preco_exibicao *= cotacao

                            resultados.append({
                                "Destino": mapa_nomes.get(iata_dest, iata_dest),
                                "Companhia": o["owner"]["name"],
                                "Preço": preco_exibicao,
                                "Símbolo": "R$" if is_br else "€",
                                "Link": f"https://www.skyscanner.{'com.br' if is_br else 'pt'}/transport/flights/{iata_origem}/{iata_dest}/{data_ida.strftime('%y%m%d')}/?curr={'BRL' if is_br else 'EUR'}"
                            })

                if resultados:
                    st.session_state.voos = sorted(resultados, key=lambda x: x['Preço'])
                    st.session_state.is_br = is_br
                    st.session_state.cotacao = cotacao
                    st.session_state.itinerario = f"{origem_sel} para {destino_sel}"
                    st.toast("Resultados atualizados!", icon="✈️")
                else:
                    st.warning("Não foram encontrados voos.")
        except Exception as e: st.error(f"Erro: {e}")

# --- EXIBIÇÃO ---
if "voos" in st.session_state:
    simb = st.session_state.voos[0]["Símbolo"]
    df = pd.DataFrame(st.session_state.voos)
    
    st.dataframe(df, column_config={
        "Preço": st.column_config.NumberColumn(f"Preço ({simb})", format=f"{simb} %.2f"),
        "Link": st.column_config.LinkColumn("Reservar", display_text="Ver Oferta ✈️")
    }, hide_index=True, use_container_width=True)
    
    if st.session_state.is_br:
        st.caption(f"ℹ️ Câmbio ao vivo: 1€ = R$ {st.session_state.cotacao:.2f}")

    st.write("---")
    st.subheader("📬 Alerta de Preço por E-mail")
    col_mail, col_btn = st.columns([3, 1])
    with col_mail:
        email_user = st.text_input("Teu e-mail:", key="email_input", label_visibility="collapsed", placeholder="exemplo@gmail.com")
    with col_btn:
        if st.button("Ativar Alerta", use_container_width=True):
            if "@" in email_user:
                enviar_alerta_email(email_user, st.session_state.itinerario, st.session_state.voos[0]["Preço"], simb)
                st.success("✅ Alerta ativado!")