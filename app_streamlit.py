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
CHAVE_PIX_REAL = "936797003" # Coloque aqui sua chave (Telemóvel, E-mail ou CPF)
# ------------------------------

st.set_page_config(page_title="Flight Monitor GDS - Booking", page_icon="✈️", layout="centered")

# --- FUNÇÃO: ENVIO DE EMAIL ---
def enviar_email_confirmacao(pax_nome, pax_email, voo, pnr, metodo_pagamento="Cartão"):
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
                <h2 style="color: #1a73e8;">Sua reserva foi processada com sucesso!</h2>
                <p>Olá <strong>{pax_nome}</strong>, seu bilhete eletrônico foi gerado.</p>
                <div style="background: #f8f9fa; padding: 15px; border-left: 5px solid #1a73e8;">
                    <p style="font-size: 18px;">Localizador (PNR): <strong>{pnr}</strong></p>
                    <p>Companhia: {voo['Companhia']}</p>
                    <p>Método de Pagamento: {metodo_pagamento}</p>
                    <p>Total: {voo['Moeda']} {voo['Preço']:.2f}</p>
                </div>
                <p>Já pode consultar sua reserva no site da companhia aérea com o código acima.</p>
                <p>Dúvidas? <a href="https://wa.me/{WHATSAPP_SUPORTE}">Fale connosco via WhatsApp</a></p>
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

# --- ESTADOS ---
if 'pagina' not in st.session_state: st.session_state.pagina = "busca"
if 'voo_selecionado' not in st.session_state: st.session_state.voo_selecionado = None
if 'resultados_voos' not in st.session_state: st.session_state.resultados_voos = []

# --- SIDEBAR ---
with st.sidebar:
    st.title("📌 Menu GDS")
    if st.button("🔍 Procurar Voos"): st.session_state.pagina = "busca"
    if st.button("🔑 Área do Cliente"): st.session_state.pagina = "area_cliente"
    st.divider()
    st.markdown(f"[💬 WhatsApp Suporte](https://wa.me/{WHATSAPP_SUPORTE})")

# --- PÁGINA 1: BUSCA ---
if st.session_state.pagina == "busca":
    st.title("✈️ Flight Monitor GDS")
    
    cidades = {
        "Brasil - Sudeste": {"São Paulo (GRU)": "GRU", "São Paulo (CGH)": "CGH", "Campinas (VCP)": "VCP", "Rio de Janeiro (GIG)": "GIG", "Rio de Janeiro (SDU)": "SDU", "Belo Horizonte (CNF)": "CNF", "Vitória (VIX)": "VIX"},
        "Brasil - Sul": {"Curitiba (CWB)": "CWB", "Florianópolis (FLN)": "FLN", "Porto Alegre (POA)": "POA", "Foz do Iguaçu (IGU)": "IGU", "Navegantes (NVT)": "NVT", "Londrina (LDB)": "LDB"},
        "Brasil - Centro-Oeste": {"Brasília (BSB)": "BSB", "Goiânia (GYN)": "GYN", "Cuiabá (CGB)": "CGB", "Campo Grande (CGR)": "CGR"},
        "Brasil - Nordeste": {"Salvador (SSA)": "SSA", "Recife (REC)": "REC", "Fortaleza (FOR)": "FOR", "Natal (NAT)": "NAT", "Maceió (MCZ)": "MCZ", "João Pessoa (JPA)": "JPA", "Aracaju (AJU)": "AJU", "Porto Seguro (BPS)": "BPS", "Ilhéus (IOS)": "IOS"},
        "Brasil - Norte": {"Manaus (MAO)": "MAO", "Belém (BEL)": "BEL", "Porto Velho (PVH)": "PVH", "Rio Branco (RBR)": "RBR", "Macapá (MCP)": "MCP", "Boa Vista (BVB)": "BVB", "Palmas (PMW)": "PMW", "Marabá (MAB)": "MAB", "Parauapebas / Carajás (CKS)": "CKS", "Araguaína (AUX)": "AUX"},
        "Portugal": {"Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO", "Funchal (FNC)": "FNC", "Ponta Delgada (PDL)": "PDL"},
        "Europa": {"Madrid (MAD)": "MAD", "Barcelona (BCN)": "BCN", "Paris (CDG)": "CDG", "Londres (LHR)": "LHR", "Roma (FCO)": "FCO", "Frankfurt (FRA)": "FRA", "Istambul (IST)": "IST"},
        "Estados Unidos": {"Miami (MIA)": "MIA", "Orlando (MCO)": "MCO", "Nova York (JFK)": "JFK", "Boston (BOS)": "BOS"},
        "África": {"Luanda (LAD)": "LAD", "Joanesburgo (JNB)": "JNB", "Cidade do Cabo (CPT)": "CPT", "Casablanca (CMN)": "CMN"}
    }

    mapa_iata = {}
    opcoes = ["Selecione..."]
    for regiao, items in cidades.items():
        for nome, iata in items.items():
            mapa_iata[nome] = iata
            opcoes.append(nome)

    tipo_v = st.radio("Tipo de Viagem", ["Ida e volta", "Somente ida"], horizontal=True)

    with st.form("busca_v8"):
        col1, col2 = st.columns(2)
        origem_sel = col1.selectbox("Origem", opcoes)
        destino_sel = col2.selectbox("Destino", opcoes)
        c3, c4 = st.columns(2)
        data_ida = c3.date_input("Partida", value=datetime.today())
        data_volta = c4.date_input("Regresso", value=datetime.today() + timedelta(days=7)) if tipo_v == "Ida e volta" else None
        moeda_pref = st.selectbox("Moeda", ["Euro (€)", "Real (R$)"])
        btn_pesquisar = st.form_submit_button("PESQUISAR VOOS")

    if btn_pesquisar:
        try:
            with st.spinner('A carregar detalhes reais...'):
                api_token = st.secrets["DUFFEL_TOKEN"]
                headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                
                payload = {"data": {"slices": [{"origin": mapa_iata[origem_sel], "destination": mapa_iata[destino_sel], "departure_date": str(data_ida)}], "passengers": [{"type": "adult"}], "requested_currencies": ["BRL" if "Real" in moeda_pref else "EUR"]}}
                res = requests.post("https://api.duffel.com/air/offer_requests", headers=headers, json=payload)
                
                if res.status_code == 201:
                    data_res = res.json()["data"]
                    st.session_state.resultados_voos = []
                    for o in data_res.get("offers", [])[:5]:
                        itinerario = []
                        for s_slice in o["slices"]:
                            for seg in s_slice["segments"]:
                                itinerario.append({"de": seg["origin"]["iata_code"], "para": seg["destination"]["iata_code"], "saida": seg["departing_at"], "chegada": seg["arriving_at"], "cia": seg["marketing_carrier"]["name"], "aviao": seg["aircraft"]["name"] if seg["aircraft"] else "N/D"})
                        
                        preco_venda = float(o["total_amount"]) * (1 + COMISSAO_PERCENTUAL)
                        st.session_state.resultados_voos.append({
                            "id_offer": o["id"], "pax_ids": [p["id"] for p in data_res.get("passengers", [])],
                            "Companhia": o["owner"]["name"], "Preço": preco_venda, 
                            "Moeda": "R$" if "Real" in moeda_pref else "€", "Segmentos": itinerario
                        })
                    st.success("Voos encontrados!")
        except Exception as e: st.error(f"Erro: {e}")

    if st.session_state.resultados_voos:
        for v in st.session_state.resultados_voos:
            with st.expander(f"✈️ {v['Companhia']} - {v['Moeda']} {v['Preço']:.2f}"):
                for s in v["Segmentos"]:
                    st.write(f"📍 **{s['de']} → {s['para']}** ({s['cia']})")
                    st.caption(f"🕒 Saída: {s['saida']} | Aeronave: {s['aviao']}")
                    st.markdown("---")
                if st.button("Reservar", key=v['id_offer']):
                    st.session_state.voo_selecionado = v
                    st.session_state.pagina = "reserva"
                    st.rerun()

# --- PÁGINA 2: RESERVA REAL (SEM SIMULAÇÃO) ---
elif st.session_state.pagina == "reserva":
    v = st.session_state.voo_selecionado
    st.title("🏁 Checkout Real")
    st.info(f"Voo: {v['Companhia']} | Total: {v['Moeda']} {v['Preço']:.2f}")
    
    with st.form("checkout_v8"):
        st.subheader("Dados do Passageiro")
        col_n1, col_n2 = st.columns(2)
        n = col_n1.text_input("Nome")
        a = col_n2.text_input("Apelido")
        col_n3, col_n4 = st.columns(2)
        dn = col_n3.date_input("Data de Nascimento", value=datetime(1990,1,1), min_value=datetime(1900,1,1))
        genero = col_n4.selectbox("Gênero", ["m", "f"])
        
        e = st.text_input("E-mail para Bilhete")
        tel = st.text_input("Telemóvel (ex: +351...)")
        
        st.divider()
        st.subheader("Pagamento")
        
        if v['Moeda'] == "R$":
            metodo = st.radio("Método", ["PIX (Gera QR Code)", "Cartão de Crédito"])
        else:
            metodo = "Cartão de Crédito"
            st.write("💳 Pagamento via Cartão de Crédito Internacional")

        if st.form_submit_button("CONFIRMAR E EMITIR"):
            if not n or not e:
                st.error("Campos obrigatórios em falta.")
            else:
                try:
                    with st.spinner('A comunicar com a Companhia Aérea...'):
                        api_token = st.secrets["DUFFEL_TOKEN"]
                        headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                        
                        # PAYLOAD PARA EMISSÃO REAL
                        payload = {
                            "data": {
                                "type": "instant",
                                "selected_offers": [v['id_offer']],
                                "passengers": [{
                                    "id": v['pax_ids'][0], "given_name": n, "family_name": a,
                                    "gender": genero, "born_on": str(dn), "email": e, "phone_number": tel
                                }],
                                "payments": [{
                                    "type": "balance", 
                                    "currency": v['Moeda'].replace("€", "EUR").replace("R$", "BRL"),
                                    "amount": str(round(v['Preço'], 2))
                                }]
                            }
                        }
                        
                        res = requests.post("https://api.duffel.com/air/orders", headers=headers, json=payload)
                        
                        if res.status_code == 201:
                            pnr_real = res.json()["data"]["booking_reference"]
                            enviar_email_confirmacao(n, e, v, pnr_real, metodo)
                            st.balloons()
                            st.success(f"✅ BILHETE EMITIDO! Localizador Iberia: {pnr_real}")
                            if metodo == "PIX (Gera QR Code)": st.session_state.pix_ativo = True
                        else:
                            msg_erro = res.json().get("errors", [{}])[0].get("message", "Erro na API")
                            st.error(f"Falha na emissão: {msg_erro}")
                except Exception as ex: st.error(f"Erro técnico: {ex}")

    if st.session_state.get('pix_ativo'):
        st.markdown("### 💠 PAGAMENTO PIX")
        st.write(f"Valor a transferir: **{v['Moeda']} {v['Preço']:.2f}**")
        st.code(CHAVE_PIX_REAL, language="text")
        url_qr = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={CHAVE_PIX_REAL}"
        st.image(url_qr, caption="Escaneie para pagar agora")

# --- PÁGINA 3: ÁREA CLIENTE ---
elif st.session_state.pagina == "area_cliente":
    st.title("🔑 Área do Cliente")
    pnr_input = st.text_input("Localizador (PNR)")
    if st.button("Aceder"):
        st.subheader(f"Reserva {pnr_input}")
        st.info("Status: Consultando base de dados da agência...")
        wa_link = f"https://wa.me/{WHATSAPP_SUPORTE}?text=Olá,%20ajuda%20com%20o%20PNR%20{pnr_input}"
        st.markdown(f'<a href="{wa_link}" target="_blank"><button style="background:#25D366;color:white;border:none;padding:10px;border-radius:5px;cursor:pointer;">💬 WhatsApp Suporte</button></a>', unsafe_allow_html=True)