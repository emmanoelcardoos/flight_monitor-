import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURAÇÃO DE NEGÓCIO ---
COMISSAO_PERCENTUAL = 0.10  
WHATSAPP_SUPORTE = "351XXXXXXXXX" # Teu número (DDI + Número)
# ------------------------------

st.set_page_config(page_title="Flight Monitor GDS - Booking", page_icon="✈️", layout="centered")

# --- FUNÇÃO: ENVIO DE EMAIL ---
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
                <h2 style="color: #1a73e8;">Reserva Confirmada!</h2>
                <p>Olá <strong>{pax_nome}</strong>, seu bilhete foi emitido.</p>
                <div style="background: #f8f9fa; padding: 15px; border-left: 5px solid #1a73e8;">
                    <p>Localizador (PNR): <strong>{pnr}</strong></p>
                    <p>Companhia: {voo['Companhia']}</p>
                </div>
                <p>Dúvidas? <a href="https://wa.me/{WHATSAPP_SUPORTE}">Fale conosco via WhatsApp</a></p>
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

    with st.form("busca_v6"):
        col1, col2 = st.columns(2)
        origem_sel = col1.selectbox("Origem", opcoes)
        destino_sel = col2.selectbox("Destino", opcoes)
        c3, c4 = st.columns(2)
        data_ida = c3.date_input("Partida", value=datetime.today())
        data_volta = c4.date_input("Regresso", value=datetime.today() + timedelta(days=7)) if tipo_v == "Ida e volta" else None
        moeda_pref = st.selectbox("Moeda", ["Euro (€)", "Real (R$)"])
        btn_pesquisar = st.form_submit_button("PESQUISAR VOOS DISPONÍVEIS")

    if btn_pesquisar:
        try:
            with st.spinner('A carregar detalhes completos dos voos...'):
                api_token = st.secrets["DUFFEL_TOKEN"]
                headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                
                slices = [{"origin": mapa_iata[origem_sel], "destination": mapa_iata[destino_sel], "departure_date": str(data_ida)}]
                if data_volta: slices.append({"origin": mapa_iata[destino_sel], "destination": mapa_iata[origem_sel], "departure_date": str(data_volta)})

                payload = {"data": {"slices": slices, "passengers": [{"type": "adult"}], "requested_currencies": ["BRL" if "Real" in moeda_pref else "EUR"]}}
                res = requests.post("https://api.duffel.com/air/offer_requests", headers=headers, json=payload)
                
                if res.status_code == 201:
                    data_res = res.json()["data"]
                    st.session_state.resultados_voos = []
                    for o in data_res.get("offers", [])[:5]:
                        # --- CAPTURA DE SEGMENTOS ---
                        itinerario = []
                        for s_slice in o["slices"]:
                            for seg in s_slice["segments"]:
                                itinerario.append({
                                    "de": seg["origin"]["iata_code"],
                                    "para": seg["destination"]["iata_code"],
                                    "saida": seg["departing_at"],
                                    "chegada": seg["arriving_at"],
                                    "cia": seg["marketing_carrier"]["name"],
                                    "aviao": seg["aircraft"]["name"] if seg["aircraft"] else "N/D"
                                })
                        
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
                    st.caption(f"🕒 Saída: {s['saida']} | Chegada: {s['chegada']}")
                    st.caption(f"✈️ Aeronave: {s['aviao']}")
                    st.markdown("---")
                if st.button("Reservar", key=v['id_offer']):
                    st.session_state.voo_selecionado = v
                    st.session_state.pagina = "reserva"
                    st.rerun()

# --- PÁGINA 2: RESERVA ---
elif st.session_state.pagina == "reserva":
    v = st.session_state.voo_selecionado
    st.title("🏁 Checkout")
    with st.form("checkout_real"):
        st.info(f"Voo {v['Companhia']} | Total: {v['Moeda']} {v['Preço']:.2f}")
        n = st.text_input("Nome")
        a = st.text_input("Apelido")
        dn = st.date_input("Nascimento", value=datetime(1990,1,1), min_value=datetime(1900,1,1))
        e = st.text_input("E-mail")
        if st.form_submit_button("PAGAR E EMITIR"):
            pnr = "GTD78X" # Simulação de sucesso
            enviar_email_confirmacao(n, e, v, pnr)
            st.balloons()
            st.success(f"Emitido! PNR: {pnr}")

# --- PÁGINA 3: ÁREA CLIENTE ---
elif st.session_state.pagina == "area_cliente":
    st.title("🔑 Área do Cliente")
    pnr_input = st.text_input("Localizador (PNR)")
    if st.button("Aceder"):
        st.subheader(f"Reserva {pnr_input}")
        wa_link = f"https://wa.me/{WHATSAPP_SUPORTE}?text=Olá,%20suporte%20para%20o%20PNR%20{pnr_input}"
        st.markdown(f'<a href="{wa_link}" target="_blank"><button style="background:#25D366;color:white;border:none;padding:10px;border-radius:5px;">💬 WhatsApp Suporte</button></a>', unsafe_allow_html=True)