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

# --- BASE DE DADOS DE CIDADES (Tua lista completa corrigida) ---
cidades = {
    "Brasil - Sudeste": {"São Paulo (GRU)": "GRU", "São Paulo (CGH)": "CGH", "Campinas (VCP)": "VCP", "Rio de Janeiro (GIG)": "GIG", "Rio de Janeiro (SDU)": "SDU", "Belo Horizonte (CNF)": "CNF", "Belo Horizonte (PLU)": "PLU", "Vitória (VIX)": "VIX"},
    "Brasil - Sul": {"Curitiba (CWB)": "CWB", "Florianópolis (FLN)": "FLN", "Porto Alegre (POA)": "POA", "Foz do Iguaçu (IGU)": "IGU", "Navegantes (NVT)": "NVT", "Londrina (LDB)": "LDB"},
    "Brasil - Centro-Oeste": {"Brasília (BSB)": "BSB", "Goiânia (GYN)": "GYN", "Cuiabá (CGB)": "CGB", "Campo Grande (CGR)": "CGR"},
    "Brasil - Nordeste": {"Salvador (SSA)": "SSA", "Recife (REC)": "REC", "Fortaleza (FOR)": "FOR", "Natal (NAT)": "NAT", "Maceió (MCZ)": "MCZ", "João Pessoa (JPA)": "JPA", "Aracaju (AJU)": "AJU", "Porto Seguro (BPS)": "BPS", "Ilhéus (IOS)": "IOS"},
    "Brasil - Norte": {"Manaus (MAO)": "MAO", "Belém (BEL)": "BEL", "Porto Velho (PVH)": "PVH", "Rio Branco (RBR)": "RBR", "Macapá (MCP)": "MCP", "Boa Vista (BVB)": "BVB", "Palmas (PMW)": "PMW", "Marabá (MAB)": "MAB", "Parauapebas (Carajás)": "CKS"},
    "Portugal": {"Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO", "Funchal (FNC)": "FNC", "Ponta Delgada (PDL)": "PDL"},
    "Europa": {"Madrid (MAD)": "MAD", "Barcelona (BCN)": "BCN", "Paris (CDG)": "CDG", "Paris Orly (ORY)": "ORY", "Londres Heathrow (LHR)": "LHR", "Londres Gatwick (LGW)": "LGW", "Roma (FCO)": "FCO", "Milão (MXP)": "MXP", "Frankfurt (FRA)": "FRA", "Munique (MUC)": "MUC", "Zurique (ZRH)": "ZRH", "Amsterdã (AMS)": "AMS", "Bruxelas (BRU)": "BRU", "Copenhaga (CPH)": "CPH", "Istambul (IST)": "IST"},
    "Estados Unidos": {"Miami (MIA)": "MIA", "Orlando (MCO)": "MCO", "Fort Lauderdale (FLL)": "FLL", "Nova York JFK (JFK)": "JFK", "Nova York Newark (EWR)": "EWR", "Atlanta (ATL)": "ATL", "Dallas (DFW)": "DFW", "Houston (IAH)": "IAH", "Chicago (ORD)": "ORD", "Los Angeles (LAX)": "LAX", "San Francisco (SFO)": "SFO", "Washington (IAD)": "IAD", "Boston (BOS)": "BOS"},
    "África": {"Luanda (NBJ)": "NBJ", "Joanesburgo (JNB)": "JNB", "Cidade do Cabo (CPT)": "CPT", "Casablanca (CMN)": "CMN", "Addis Abeba (ADD)": "ADD"}
}

# Lista de destinos para o "Modo Explorar" (Capitais e Hubs mundiais)
destinos_explorar_lista = ["LIS", "OPO", "MAD", "BCN", "PAR", "LHR", "FCO", "FRA", "AMS", "GRU", "GIG", "BSB", "MIA", "JFK", "LAD", "CMN"]

mapa_iata = {}
opcoes_origem = ["Cidade ou Aeroporto..."]
opcoes_destino = ["Cidade ou Aeroporto...", "🌍 EXPLORAR QUALQUER LUGAR"]

for regiao, items in cidades.items():
    for nome, iata in items.items():
        mapa_iata[nome] = iata
        opcoes_origem.append(nome)
        opcoes_destino.append(nome)

# --- INTERFACE ---
st.title("🌍 Flight Monitor - Buscador GDS")

col_tipo, col_moeda = st.columns([3, 1])
with col_tipo:
    tipo_viagem = st.radio("Tipo de Viagem", ["Só Ida/Volta", "Ida e Volta"], horizontal=True)
with col_moeda:
    moeda_pref = st.selectbox("Moeda e Região", ["Euro (€) - (Site .PT)", "Real (R$) - (Site .BR)"])

col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
with col1: origem_sel = st.selectbox("Origem:", options=opcoes_origem, index=0)
with col2: destino_sel = st.selectbox("Destino:", options=opcoes_destino, index=0)
with col3: data_ida = st.date_input("Data de Ida", min_value=datetime.today())
with col4: data_volta = st.date_input("Data de Volta", min_value=data_ida + timedelta(days=1)) if tipo_viagem == "Ida e Volta" else None

# --- LÓGICA DE BUSCA ---
# --- LÓGICA DE BUSCA ---
if st.button("Pesquisar"):
    if origem_sel == "Cidade ou Aeroporto..." or destino_sel == "Cidade ou Aeroporto...":
        st.warning("⚠️ Selecione a Origem e o Destino (ou 'Explorar').")
    else:
        try:
            # Criar mapa inverso para traduzir IATA de volta para Nome (ex: JFK -> Nova York JFK)
            mapa_nomes = {v: k for k, v in mapa_iata.items()}
            
            with st.spinner('A analisar as melhores rotas para si...'):
                api_token = st.secrets.get("DUFFEL_TOKEN")
                headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                cotacao = get_exchange_rate()
                is_br = "Real" in moeda_pref
                iata_origem = mapa_iata[origem_sel]
                
                if destino_sel == "🌍 EXPLORAR QUALQUER LUGAR":
                    lista_destinos = [d for d in destinos_explorar_lista if d != iata_origem]
                else:
                    lista_destinos = [mapa_iata[destino_sel]]

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
                            preco_base = float(o["total_amount"])
                            moeda_api = o["total_currency"]
                            
                            # Tradução do Código IATA para Nome Amigável
                            nome_cidade_destino = mapa_nomes.get(iata_dest, iata_dest)
                            
                            if is_br:
                                preco_exibicao = preco_base if moeda_api == "BRL" else preco_base * cotacao
                                simb = "R$"
                            else:
                                preco_exibicao = preco_base if moeda_api == "EUR" else preco_base / cotacao
                                simb = "€"

                            resultados.append({
                                "Destino": nome_cidade_destino, # Agora aparece o nome!
                                "Companhia": o["owner"]["name"],
                                "Preço": preco_exibicao,
                                "Símbolo": simb,
                                "Link": f"https://www.skyscanner.{'com.br' if is_br else 'pt'}/transport/flights/{iata_origem}/{iata_dest}/{data_ida.strftime('%y%m%d')}/?curr={'BRL' if is_br else 'EUR'}"
                            })

                if resultados:
                    st.session_state.voos = sorted(resultados, key=lambda x: x['Preço'])
                    st.session_state.is_br = is_br
                    st.session_state.cotacao = cotacao
                    st.session_state.itinerario = f"Saindo de {origem_sel}"
                else:
                    st.warning("Não foram encontrados voos.")
        except Exception as e: st.error(f"Erro: {e}")

# --- EXIBIÇÃO ---
if "voos" in st.session_state:
    # st.balloons() # Removi os balões para ficar mais limpo
    st.toast("Resultados atualizados!", icon="✈️") # Uma notificação pequena no canto
    
    simb = st.session_state.voos[0]["Símbolo"]
    df = pd.DataFrame(st.session_state.voos)
    
    st.dataframe(df, column_config={
        "Preço": st.column_config.NumberColumn(f"Preço ({simb})", format=f"{simb} %.2f"),
        "Link": st.column_config.LinkColumn("Reservar", display_text="Ver Oferta ✈️")
    }, hide_index=True, use_container_width=True)
    
    # ... resto do código de e-mail ...

    if st.session_state.is_br:
        st.caption(f"ℹ️ Câmbio ao vivo: 1€ = R$ {st.session_state.cotacao:.2f}")

    st.write("---")
    st.subheader("📬 Alerta de Preço por E-mail")
    email_user = st.text_input("Teu e-mail:", key="email_input")
    if st.button("Ativar Alerta"):
        if "@" in email_user:
            preco_alerta = st.session_state.voos[0]["Preço"]
            enviar_alerta_email(email_user, st.session_state.itinerario, preco_alerta, simb)
            st.success(f"✅ Alerta ativado para {email_user}")