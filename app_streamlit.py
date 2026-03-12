import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURAÇÃO DE NEGÓCIO ---
COMISSAO_PERCENTUAL = 0.10  
WHATSAPP_SUPORTE = "351936797003" 
CHAVE_PIX_REAL = "936797003" 

st.set_page_config(page_title="Flight Monitor GDS", page_icon="✈️", layout="wide")

# --- FUNÇÃO: ENVIO DE EMAIL COM LINK DE REGISTRO ---
def enviar_email_confirmacao(pax_nome, pax_email, voo, pnr):
    try:
        email_origem = st.secrets["EMAIL_USER"]
        senha_origem = st.secrets["EMAIL_PASSWORD"]
        msg = MIMEMultipart()
        msg['From'] = f"Flight Monitor GDS <{email_origem}>"
        msg['To'] = pax_email
        msg['Subject'] = f"✈️ Reserva Confirmada: {pnr}"

        html = f"""
        <html>
            <body style="font-family: sans-serif; padding: 20px;">
                <h2 style="color: #1a73e8;">Sua reserva foi emitida com sucesso!</h2>
                <p>Olá <strong>{pax_nome}</strong>, seu localizador oficial é: <strong>{pnr}</strong></p>
                <div style="background: #f8f9fa; padding: 15px; border-left: 5px solid #1a73e8;">
                    <p>Voo: {voo['Companhia']} | Total Pago: {voo['Moeda']} {voo['Preço']:.2f}</p>
                </div>
                <p><strong>Ação Necessária:</strong> Para acessar sua área privada, gerir seus dados e ver suas reservas futuras, registre sua senha no link abaixo:</p>
                <p><a href="https://flightmonitor.streamlit.app/" style="background:#1a73e8; color:white; padding:10px 20px; text-decoration:none; border-radius:5px;">DEFINIR MINHA SENHA</a></p>
                <p>Dúvidas? <a href="https://wa.me/{WHATSAPP_SUPORTE}">Fale conosco no WhatsApp</a></p>
            </body>
        </html>
        """
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(email_origem, senha_origem)
            server.sendmail(email_origem, pax_email, msg.as_string())
        return True
    except: return False

# --- INICIALIZAÇÃO DE ESTADOS ---
if 'pagina' not in st.session_state: st.session_state.pagina = "busca"
if 'voo_selecionado' not in st.session_state: st.session_state.voo_selecionado = None
if 'resultados_voos' not in st.session_state: st.session_state.resultados_voos = []

# --- SIDEBAR ---
with st.sidebar:
    st.title("📌 Flight Monitor")
    if st.button("🔍 Procurar Voos"): st.session_state.pagina = "busca"
    if st.button("👤 Área do Cliente (Login)"): st.session_state.pagina = "login"
    st.divider()
    st.markdown(f"**Suporte 24h:** [WhatsApp](https://wa.me/{WHATSAPP_SUPORTE})")

# --- PÁGINA 1: BUSCA ---
if st.session_state.pagina == "busca":
    st.title("✈️ Portal de Reservas GDS")
    
    cidades = {
        "Brasil": {"São Paulo (GRU)": "GRU", "Rio de Janeiro (GIG)": "GIG", "Brasília (BSB)": "BSB", "Recife (REC)": "REC", "Fortaleza (FOR)": "FOR", "Salvador (SSA)": "SSA"},
        "Portugal": {"Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO", "Funchal (FNC)": "FNC"},
        "Internacional": {"Madrid (MAD)": "MAD", "Paris (CDG)": "CDG", "Londres (LHR)": "LHR", "Miami (MIA)": "MIA"}
    }
    # (Simplificado aqui para brevidade, mas mantenha sua lista completa no VS Code)

    mapa_iata = {}
    opcoes = ["Selecione..."]
    for regiao, items in cidades.items():
        for nome, iata in items.items():
            mapa_iata[nome] = iata
            opcoes.append(nome)

    with st.form("busca_v10"):
        col1, col2 = st.columns(2)
        origem = col1.selectbox("Origem", opcoes)
        destino = col2.selectbox("Destino", opcoes)
        col3, col4 = st.columns(2)
        data = col3.date_input("Data de Partida", value=datetime.today() + timedelta(days=7))
        moeda_pref = col4.selectbox("Moeda Preferencial", ["Real (BRL)", "Euro (EUR)", "Dólar (USD)"])
        submit = st.form_submit_button("PESQUISAR VOOS REAIS")

    if submit:
        try:
            with st.spinner('Consultando inventário vivo...'):
                api_token = st.secrets["DUFFEL_TOKEN"]
                headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                
                moeda_api = "BRL" if "Real" in moeda_pref else ("EUR" if "Euro" in moeda_pref else "USD")
                
                payload = {"data": {"slices": [{"origin": mapa_iata[origem], "destination": mapa_iata[destino], "departure_date": str(data)}], "passengers": [{"type": "adult"}], "requested_currencies": [moeda_api]}}
                res = requests.post("https://api.duffel.com/air/offer_requests", headers=headers, json=payload)
                
                if res.status_code == 201:
                    offers = res.json()["data"].get("offers", [])
                    st.session_state.resultados_voos = []
                    for o in offers[:5]:
                        itinerario = []
                        for s_slice in o["slices"]:
                            for seg in s_slice["segments"]:
                                itinerario.append({
                                    "de": seg["origin"]["iata_code"], "para": seg["destination"]["iata_code"],
                                    "saida": seg["departing_at"], "chegada": seg["arriving_at"],
                                    "cia": seg["marketing_carrier"]["name"], "aviao": seg["aircraft"]["name"] if seg["aircraft"] else "N/D"
                                })
                        
                        # CORREÇÃO DE MOEDA: Usar o que a Duffel respondeu
                        valor_final = float(o["total_amount"]) * (1 + COMISSAO_PERCENTUAL)
                        moeda_real = o["total_currency"] 
                        
                        st.session_state.resultados_voos.append({
                            "id_offer": o["id"], "pax_ids": [p["id"] for p in res.json()["data"]["passengers"]],
                            "Companhia": o["owner"]["name"], "Preço": valor_final, "Moeda": moeda_real, "Segmentos": itinerario
                        })
                    st.success("Tarifas atualizadas.")
        except Exception as e: st.error(f"Erro: {e}")

    if st.session_state.resultados_voos:
        for v in st.session_state.resultados_voos:
            with st.expander(f"✈️ {v['Companhia']} - {v['Moeda']} {v['Preço']:.2f}"):
                for s in v["Segmentos"]:
                    st.write(f"📍 **{s['de']} ➔ {s['para']}**")
                    st.caption(f"🕒 Saída: {s['saida'].replace('T', ' ')} | Chegada: {s['chegada'].replace('T', ' ')}")
                    st.divider()
                if st.button("Selecionar", key=v['id_offer']):
                    st.session_state.voo_selecionado = v
                    st.session_state.pagina = "reserva"
                    st.rerun()

# --- PÁGINA 2: RESERVA ---
elif st.session_state.pagina == "reserva":
    v = st.session_state.voo_selecionado
    st.title("🏁 Finalizar Compra")
    st.info(f"Voo Selecionado: {v['Companhia']} | Valor Total: {v['Moeda']} {v['Preço']:.2f}")

    with st.form("checkout"):
        st.subheader("👤 Dados do Passageiro")
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome Próprio")
        sobrenome = c2.text_input("Apelido")
        email_p = st.text_input("E-mail para recebimento do PNR")
        tel_p = st.text_input("Telefone (com DDI)")
        dn = st.date_input("Data de Nascimento", value=datetime(1990,1,1))

        st.divider()
        st.subheader("💳 Pagamento")
        metodo = st.radio("Forma de Pagamento", ["Cartão de Crédito", "PIX"])
        
        if metodo == "Cartão de Crédito":
            st.text_input("Número do Cartão")
            col_c1, col_c2, col_c3 = st.columns([2,1,1])
            col_c1.text_input("Nome no Cartão")
            col_c2.text_input("Validade (MM/AA)")
            col_c3.text_input("CVV")
            if v['Moeda'] == "BRL":
                st.selectbox("Parcelamento (Cartões Brasileiros)", ["1x à vista", "2x (com juros)", "3x (com juros)"])
        
        elif metodo == "PIX":
            st.warning("💠 **Atenção:** Pagamentos via PIX requerem atendimento humano para emissão imediata.")
            st.markdown(f"[💬 Clique aqui para pagar via PIX no WhatsApp](https://wa.me/{WHATSAPP_SUPORTE}?text=Olá,%20quero%20pagar%20a%20reserva%20de%20{v['Preço']}%20via%20PIX)")

        if st.form_submit_button("CONFIRMAR E PAGAR AGORA"):
            try:
                with st.spinner('Emitindo bilhete real...'):
                    api_token = st.secrets["DUFFEL_TOKEN"]
                    headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                    payload = {
                        "data": {
                            "type": "instant", "selected_offers": [v['id_offer']],
                            "passengers": [{"id": v['pax_ids'][0], "given_name": nome, "family_name": sobrenome, "gender": "m", "born_on": str(dn), "email": email_p, "phone_number": tel_p}],
                            "payments": [{"type": "balance", "currency": v['Moeda'], "amount": str(round(v['Preço'], 2))}]
                        }
                    }
                    res = requests.post("https://api.duffel.com/air/orders", headers=headers, json=payload)
                    if res.status_code == 201:
                        pnr = res.json()["data"]["booking_reference"]
                        enviar_email_confirmacao(nome, email_p, v, pnr)
                        st.balloons()
                        st.success(f"✅ BILHETE EMITIDO! PNR: {pnr}")
                    else:
                        st.error(f"Erro na Cia Aérea: {res.json()['errors'][0]['message']}")
            except Exception as e: st.error(f"Erro técnico: {e}")

# --- PÁGINA 3: LOGIN ---
elif st.session_state.pagina == "login":
    st.title("👤 Área Privada do Passageiro")
    st.write("Acesse suas reservas e dados pessoais.")
    login_email = st.text_input("E-mail registrado")
    login_pass = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        st.info("Funcionalidade em integração com banco de dados. Suas reservas aparecerão aqui em instantes.")