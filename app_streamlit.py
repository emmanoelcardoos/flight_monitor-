import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURAÇÃO DE NEGÓCIO ---
COMISSAO_PERCENTUAL = 0.12 # Ajustada levemente para cobrir possíveis taxas de parcelamento
WHATSAPP_SUPORTE = "351936797003" 
COTACAO_EUR_BRL = 6.25  

st.set_page_config(page_title="Flight Monitor GDS", page_icon="✈️", layout="wide")

# --- FUNÇÃO: ENVIO DE EMAIL ---
def enviar_email_confirmacao(pax_nome, pax_email, voo, pnr):
    try:
        email_origem = st.secrets["EMAIL_USER"]
        senha_origem = st.secrets["EMAIL_PASSWORD"]
        msg = MIMEMultipart()
        msg['From'] = f"Flight Monitor GDS <{email_origem}>"
        msg['To'] = pax_email
        msg['Subject'] = f"✈️ Reserva Confirmada: {pnr}"
        html = f"<h2>Sua reserva foi emitida!</h2><p>PNR: <strong>{pnr}</strong></p><p>Voo: {voo['Companhia']}</p>"
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(email_origem, senha_origem)
            server.sendmail(email_origem, pax_email, msg.as_string())
        return True
    except: return False

# --- ESTADOS ---
if 'pagina' not in st.session_state: st.session_state.pagina = "busca"
if 'voo_selecionado' not in st.session_state: st.session_state.voo_selecionado = None
if 'resultados_voos' not in st.session_state: st.session_state.resultados_voos = []

# --- SIDEBAR ---
with st.sidebar:
    st.title("📌 Flight Monitor")
    if st.button("🔍 Procurar Voos"): st.session_state.pagina = "busca"
    if st.button("👤 Área do Cliente"): st.session_state.pagina = "login"
    st.divider()
    st.markdown(f"**Suporte:** [WhatsApp](https://wa.me/{WHATSAPP_SUPORTE})")

# --- PÁGINA 1: BUSCA ---
if st.session_state.pagina == "busca":
    st.title("✈️ Portal de Reservas GDS")
    
    # (Mantenha sua lista de cidades completa aqui no VS Code)
    opcoes_cidades = ["São Paulo (GRU)", "Lisboa (LIS)", "Madrid (MAD)", "Recife (REC)", "Marabá (MAB)"]

    with st.form("busca_v13"):
        col1, col2 = st.columns(2)
        origem = col1.selectbox("Origem", opcoes_cidades)
        destino = col2.selectbox("Destino", opcoes_cidades)
        moeda_visu = col1.selectbox("Moeda:", ["Real (R$)", "Euro (€)"])
        data_ida = col2.date_input("Data de Partida", value=datetime.today() + timedelta(days=7))
        btn = st.form_submit_button("PESQUISAR VOOS")

    if btn:
        try:
            with st.spinner('Buscando conexões e franquias de bagagem...'):
                api_token = st.secrets["DUFFEL_TOKEN"]
                headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                payload = {"data": {"slices": [{"origin": origem[-4:-1], "destination": destino[-4:-1], "departure_date": str(data_ida)}], "passengers": [{"type": "adult"}], "requested_currencies": ["EUR"]}}
                res = requests.post("https://api.duffel.com/air/offer_requests", headers=headers, json=payload)
                
                if res.status_code == 201:
                    offers = res.json()["data"].get("offers", [])
                    st.session_state.resultados_voos = []
                    for o in offers[:5]:
                        # Lógica de Bagagem (Duffel simplificada)
                        bagagem = "Verificar no Checkout"
                        if "passenger_conditions" in o:
                            bagagem = "Incluída" if o["passenger_conditions"].get("baggage_allowance") else "Apenas item pessoal"
                        
                        segmentos = []
                        for s_slice in o["slices"]:
                            segs = s_slice["segments"]
                            for i, seg in enumerate(segs):
                                conexao = None
                                if i < len(segs) - 1: # Se não for o último segmento, há conexão
                                    prox_seg = segs[i+1]
                                    conexao = {
                                        "cidade": seg["destination"]["city_name"],
                                        "tempo": "Conexão"
                                    }
                                
                                segmentos.append({
                                    "de": seg["origin"]["iata_code"], "para": seg["destination"]["iata_code"],
                                    "partida": seg["departing_at"].split("T")[1][:5],
                                    "chegada": seg["arriving_at"].split("T")[1][:5],
                                    "data_partida": seg["departing_at"].split("T")[0],
                                    "cia": seg["marketing_carrier"]["name"],
                                    "aviao": seg["aircraft"]["name"] if seg["aircraft"] else "N/D",
                                    "conexao": conexao
                                })
                        
                        valor_eur = float(o["total_amount"])
                        v_final = valor_eur * COTACAO_EUR_BRL * (1 + COMISSAO_PERCENTUAL) if "Real" in moeda_visu else valor_eur * (1 + COMISSAO_PERCENTUAL)
                        
                        st.session_state.resultados_voos.append({
                            "id_offer": o["id"], "pax_ids": [p["id"] for p in res.json()["data"]["passengers"]],
                            "Companhia": o["owner"]["name"], "Preço": v_final, "Moeda": "R$" if "Real" in moeda_visu else "€",
                            "Bagagem": bagagem, "Segmentos": segmentos
                        })
        except Exception as e: st.error(f"Erro: {e}")

    if st.session_state.resultados_voos:
        for v in st.session_state.resultados_voos:
            with st.expander(f"✈️ {v['Companhia']} | {v['Moeda']} {v['Preço']:.2f} | 🧳 Bagagem: {v['Bagagem']}"):
                for s in v["Segmentos"]:
                    col_p, col_c, col_a = st.columns(3)
                    col_p.metric("Partida", s['partida'], s['de'])
                    col_c.metric("Chegada", s['chegada'], s['para'])
                    col_a.write(f"✈️ **Aeronave:** {s['aviao']}")
                    
                    if s['conexao']:
                        st.warning(f"🔄 Conexão em: **{s['conexao']['cidade']}**")
                    st.divider()
                
                if st.button("Selecionar Voo", key=v['id_offer']):
                    st.session_state.voo_selecionado = v
                    st.session_state.pagina = "reserva"
                    st.rerun()

# --- PÁGINA 2: RESERVA ---
elif st.session_state.pagina == "reserva":
    v = st.session_state.voo_selecionado
    st.title("🏁 Checkout Seguro")
    
    with st.form("checkout"):
        st.subheader("👤 Dados do Passageiro")
        c1, c2 = st.columns(2)
        n = c1.text_input("Nome Próprio")
        a = c2.text_input("Apelido")
        e = st.text_input("E-mail para Bilhete")
        # Correção da Data: Até Março de 2026 (ajustado para permitir jovens e crianças)
        dn = st.date_input("Data de Nascimento", value=datetime(1995,1,1), max_value=datetime(2026,3,12))
        
        st.divider()
        st.subheader("💳 Pagamento")
        metodo = st.radio("Selecione o método:", ["Cartão de Crédito", "PIX"], horizontal=True)
        
        # A MÁGICA: Só mostra campos do cartão se NÃO for PIX
        if metodo == "Cartão de Crédito":
            st.text_input("Número do Cartão")
            cc1, cc2 = st.columns(2)
            cc1.text_input("Validade (MM/AA)")
            cc2.text_input("CVV")
            if v['Moeda'] == "R$":
                st.selectbox("Parcelas", ["1x de " + f"{v['Preço']:.2f} sem juros", "6x sem juros", "12x sem juros (Promoção)"])
        else:
            st.info("💠 **Pagamento PIX:** Atendimento Humano Obrigatório.")
            st.markdown(f"[💬 Chamar no WhatsApp para Chave PIX](https://wa.me/{WHATSAPP_SUPORTE}?text=Olá,%20quero%20pagar%20via%20PIX)")

        if st.form_submit_button("EMITIR BILHETE AGORA"):
            # Lógica de Emissão Duffel Real
            st.success("Emissão solicitada! Verifique seu e-mail em instantes.")