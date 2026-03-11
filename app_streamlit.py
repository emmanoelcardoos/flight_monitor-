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
    # CONFIGURAÇÃO DO TEU E-MAIL (Sugiro guardares isto no st.secrets depois)
    email_remetente = st.secrets.get("EMAIL_USER") # Teu gmail
    senha_app = st.secrets.get("EMAIL_PASSWORD")   # Tua senha de app do Google
    
    if not email_remetente or not senha_app:
        return False

    msg = MIMEMultipart()
    msg['From'] = email_remetente
    msg['To'] = email_destino
    msg['Subject'] = f"✈️ Alerta de Preço: {itinerario}"

    corpo = f"""
    Olá! 
    
    O Flight Monitor GDS detetou uma atualização para o itinerário: {itinerario}.
    Melhor preço encontrado no momento: {moeda} {preco:.2f}
    
    Podes verificar novamente no teu site a qualquer momento.
    
    Boas viagens!
    """
    msg.attach(MIMEText(corpo, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_remetente, senha_app)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")
        return False

# Função para pegar cotação ao vivo
def get_exchange_rate():
    try:
        res = requests.get("https://open.er-api.com/v6/latest/EUR")
        return res.json()["rates"]["BRL"]
    except:
        return 6.15

# Estilos
st.markdown("""<style>.stButton>button { width: 100%; border-radius: 8px; background-color: #007bff; color: white; font-weight: bold; }</style>""", unsafe_allow_html=True)

# 2. Configurações e Base de Dados
api_token = st.secrets.get("DUFFEL_TOKEN")

# (Dicionários SITES_BASE e CIDADES mantêm-se iguais aos anteriores)
SITES_BASE = {
    "TAP Air Portugal": {"pt": "https://www.flytap.com/pt-pt", "br": "https://www.flytap.com/pt-br"},
    "Iberia": {"pt": "https://www.iberia.com/pt/", "br": "https://www.iberia.com/br/"},
    "LATAM": {"pt": "https://www.latamairlines.com/py/pt", "br": "https://www.latamairlines.com/br/pt"},
    "Azul Linhas Aéreas": {"pt": "https://www.voeazul.com.br", "br": "https://www.voeazul.com.br"}
}

cidades = {
    "Brasil": {"São Paulo (GRU)": "GRU", "Rio (GIG)": "GIG", "Brasília (BSB)": "BSB", "Goiânia (GYN)": "GYN"},
    "Europa": {"Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO", "Madrid (MAD)": "MAD", "Paris (CDG)": "CDG"}
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
with col1:
    origem_sel = st.selectbox("Origem:", options=opcoes, index=0)
with col2:
    destino_sel = st.selectbox("Destino:", options=opcoes, index=0)
with col3:
    data_ida = st.date_input("Data de Ida", min_value=datetime.today())
with col4:
    data_volta = st.date_input("Data de Volta", min_value=data_ida + timedelta(days=1)) if tipo_viagem == "Ida e Volta" else None

# 4. Busca e Lógica de Processamento
if st.button("Pesquisar"):
    if origem_sel == "Cidade ou Aeroporto..." or destino_sel == "Cidade ou Aeroporto...":
        st.warning("⚠️ Selecione a Origem e o Destino.")
    else:
        try:
            with st.spinner('A analisar voos...'):
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
                        # GUARDAR RESULTADOS NA MEMÓRIA (Session State)
                        st.session_state.voos = []
                        st.session_state.melhor_preco = float(offers_data[0]["total_amount"])
                        st.session_state.simbolo = "R$" if is_br else "€"
                        st.session_state.itinerario = f"{origem_sel} para {destino_sel}"

                        for o in offers_data:
                            st.session_state.voos.append({
                                "Companhia": o["owner"]["name"],
                                "Preço": float(o["total_amount"]),
                                "Link": "https://www.skyscanner.pt" # Exemplo simplificado
                            })
                    else:
                        st.warning("Sem voos.")
        except Exception as e:
            st.error(f"Erro: {e}")

# EXIBIR RESULTADOS DA MEMÓRIA (Evita que desapareçam ao clicar no e-mail)
if "voos" in st.session_state:
    st.balloons()
    df = pd.DataFrame(st.session_state.voos).drop_duplicates()
    st.dataframe(df, use_container_width=True)
    
    st.write("---")
    st.subheader("📬 Receber este preço por e-mail")
    
    email_user = st.text_input("Teu e-mail:", key="email_input")
    if st.button("Enviar Confirmação"):
        if "@" in email_user:
            with st.spinner('A enviar e-mail...'):
                sucesso = enviar_alerta_email(
                    email_user, 
                    st.session_state.itinerario, 
                    st.session_state.melhor_preco, 
                    st.session_state.simbolo
                )
                if sucesso:
                    st.success(f"✅ Sucesso! E-mail enviado para {email_user}")
                else:
                    st.error("❌ Erro técnico. Verifica se a EMAIL_PASSWORD nos Secrets está correta.")
        else:
            st.error("Por favor, introduz um e-mail válido.")