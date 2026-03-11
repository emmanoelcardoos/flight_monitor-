import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 1. Configuração da Página
st.set_page_config(page_title="Flight Monitor GDS", page_icon="✈️", layout="wide")

# Função para enviar E-mail
def enviar_alerta_email(email_destino, itinerario, preco, moeda):
    email_remetente = st.secrets.get("EMAIL_USER")
    senha_app = st.secrets.get("EMAIL_PASSWORD")
    if not email_remetente or not senha_app: return False

    msg = MIMEMultipart()
    msg['From'] = email_remetente
    msg['To'] = email_destino
    msg['Subject'] = f"✈️ Alerta de Preço: {itinerario}"

    corpo = f"Olá!\n\nO melhor preço encontrado para {itinerario} é {moeda} {preco:.2f}.\nVerifica no teu site para reservar!"
    msg.attach(MIMEText(corpo, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_remetente, senha_app)
        server.send_message(msg)
        server.quit()
        return True
    except: return False

# Função para cotação ao vivo
def get_exchange_rate():
    try:
        res = requests.get("https://open.er-api.com/v6/latest/EUR")
        return res.json()["rates"]["BRL"]
    except: return 6.15

st.markdown("""<style>.stButton>button { width: 100%; border-radius: 8px; background-color: #007bff; color: white; font-weight: bold; }</style>""", unsafe_allow_html=True)

# 2. Configurações e Base de Dados
api_token = st.secrets.get("DUFFEL_TOKEN")

SITES_BASE = {
    "TAP Air Portugal": {"pt": "https://www.flytap.com/pt-pt", "br": "https://www.flytap.com/pt-br"},
    "Iberia": {"pt": "https://www.iberia.com/pt/", "br": "https://www.iberia.com/br/"},
    "LATAM": {"pt": "https://www.latamairlines.com/py/pt", "br": "https://www.latamairlines.com/br/pt"},
    "Air Europa": {"pt": "https://www.aireuropa.com/pt/pt/home", "br": "https://www.aireuropa.com/br/pt/home"},
    "Lufthansa": {"pt": "https://www.lufthansa.com/pt/pt/homepage", "br": "https://www.lufthansa.com/br/pt/homepage"},
    "British Airways": {"pt": "https://www.britishairways.com/travel/home/public/pt_pt/", "br": "https://www.britishairways.com/travel/home/public/pt_br/"},
    "Azul Linhas Aéreas": {"pt": "https://www.voeazul.com.br", "br": "https://www.voeazul.com.br"}
}

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
        "Palmas (PMW)": "PMW"
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

opcoes = ["Cidade ou Aeroporto..."]
mapa_iata = {}
for regiao, items in cidades.items():
    for nome, iata in items.items():
        opcoes.append(nome)
        mapa_iata[nome] = iata

# 3. Interface
st.title("🌍 Flight Monitor - Buscador GDS")

col_tipo, col_moeda = st.columns([3, 1])
with col_tipo:
    tipo_viagem = st.radio("Tipo de Viagem", ["Só Ida/Volta", "Ida e Volta"], horizontal=True)
with col_moeda:
    moeda_pref = st.selectbox("Moeda e Região", ["Euro (€) - (Site .PT)", "Real (R$) - (Site .BR)"])

col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
with col1: origem_sel = st.selectbox("Origem:", options=opcoes, index=0)
with col2: destino_sel = st.selectbox("Destino:", options=opcoes, index=0)
with col3: data_ida = st.date_input("Data de Ida", min_value=datetime.today())
with col4: data_volta = st.date_input("Data de Volta", min_value=data_ida + timedelta(days=1)) if tipo_viagem == "Ida e Volta" else None

# 4. Lógica de Busca
if st.button("Pesquisar"):
    if origem_sel == "Cidade ou Aeroporto..." or destino_sel == "Cidade ou Aeroporto...":
        st.warning("Por favor, Selecione a Origem e o Destino.")
    else:
        try:
            with st.spinner('A localizar voos e encontrar as melhores opções...'):
                cotacao_atual = get_exchange_rate()
                headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                is_br = "Real" in moeda_pref
                moeda_busca = "BRL" if is_br else "EUR"
                
                slices = [{"origin": mapa_iata[origem_sel], "destination": mapa_iata[destino_sel], "departure_date": str(data_ida)}]
                if data_volta:
                    slices.append({"origin": mapa_iata[destino_sel], "destination": mapa_iata[origem_sel], "departure_date": str(data_volta)})

                payload = {"data": {"slices": slices, "passengers": [{"type": "adult"}], "requested_currencies": [moeda_busca]}}
                res = requests.post("https://api.duffel.com/air/offer_requests", headers=headers, json=payload)
                
                if res.status_code == 201:
                    req_id = res.json()["data"]["id"]
                    offers_res = requests.get(f"https://api.duffel.com/air/offers?offer_request_id={req_id}&sort=total_amount", headers=headers)
                    offers_data = offers_res.json().get("data", [])

                    if offers_data:
                        st.session_state.voos = []
                        st.session_state.is_br = is_br
                        st.session_state.cotacao = cotacao_atual
                        st.session_state.itinerario = f"{origem_sel} para {destino_sel}"

                        for o in offers_data:
                            cia_nome = o["owner"]["name"]
                            preco_base = float(o["total_amount"])
                            moeda_api = o["total_currency"]

                            # Conversão de Moeda
                            if is_br:
                                preco_exibicao = preco_base if moeda_api == "BRL" else preco_base * cotacao_atual
                                simb = "R$"
                            else:
                                preco_exibicao = preco_base if moeda_api == "EUR" else preco_base / cotacao_atual
                                simb = "€"

                            # LÓGICA DE LINK PRIORITÁRIO
                            if cia_nome in SITES_BASE:
                                link_f = SITES_BASE[cia_nome]["br" if is_br else "pt"]
                                display_text = "Site Oficial ✅"
                            else:
                                tld = "com.br" if is_br else "pt"
                                cur_param = "BRL" if is_br else "EUR"
                                data_fmt = data_ida.strftime('%y%m%d')
                                link_f = f"https://www.skyscanner.{tld}/transport/flights/{mapa_iata[origem_sel]}/{mapa_iata[destino_sel]}/{data_fmt}/?curr={cur_param}"
                                if data_volta:
                                    link_f = link_f.replace(f"/{data_fmt}/", f"/{data_fmt}/{data_volta.strftime('%y%m%d')}/")
                                display_text = "Ver no Skyscanner 🔗"

                            st.session_state.voos.append({
                                "Companhia": cia_nome, 
                                "Preço": preco_exibicao, 
                                "Simbolo": simb, 
                                "Link": link_f,
                                "Botao": display_text
                            })
                    else:
                        st.warning("Sem voos para estas datas.")
                else:
                    st.error(f"Erro na API Duffel: {res.text}")
        except Exception as e: st.error(f"Erro: {e}")

# 5. Exibição dos Resultados
if "voos" in st.session_state:
    st.balloons()
    simb = st.session_state.voos[0]["Simbolo"]
    df = pd.DataFrame(st.session_state.voos).drop_duplicates(subset=['Companhia', 'Preço'])
    
    st.dataframe(df, column_config={
        "Preço": st.column_config.NumberColumn(f"Preço ({simb})", format=f"{simb} %.2f"),
        "Link": st.column_config.LinkColumn("Reservar", display_text="Aceder à Oferta"),
        "Botao": "Tipo de Link",
        "Simbolo": None # Esconde a coluna símbolo
    }, hide_index=True, use_container_width=True)
    
    if st.session_state.is_br:
        st.caption(f"ℹCâmbio ao vivo: 1€ = R$ {st.session_state.cotacao:.2f}")

    st.write("---")
    st.subheader("Receba Alerta de Preço por E-mail Sempre que Houver Alteração no Preço!")
    email_user = st.text_input("Teu e-mail:", key="email_input", placeholder="exemplo@gmail.com")
    if st.button("Enviar Confirmação"):
        if "@" in email_user:
            with st.spinner('A enviar...'):
                preco_final = st.session_state.voos[0]["Preço"]
                sucesso = enviar_alerta_email(email_user, st.session_state.itinerario, preco_final, simb)
                if sucesso: st.success(f"✅ Serás Avisado Sempre que Houver Alteração no email: {email_user}!")
                else: st.error("❌ Erro técnico no envio.")
        else: st.error("E-mail inválido.")