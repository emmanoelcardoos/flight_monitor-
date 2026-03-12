import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURAÇÃO DE NEGÓCIO ---
COMISSAO_PERCENTUAL = 0.10  # 10% de lucro
# ------------------------------

st.set_page_config(page_title="Flight Monitor GDS - REAL BOOKING", page_icon="✈️", layout="centered")

# --- FUNÇÕES DE APOIO (EMAIL E SUPORTE) ---
def enviar_email_confirmacao(pax_nome, pax_email, voo, pnr):
    try:
        email_origem = st.secrets["EMAIL_USER"]
        senha_origem = st.secrets["EMAIL_PASSWORD"]
        
        msg = MIMEMultipart()
        msg['From'] = f"Flight Monitor GDS <{email_origem}>"
        msg['To'] = pax_email
        msg['Subject'] = f"✈️ Reserva Confirmada: {pnr} ({voo['Companhia']})"

        html = f"""
        <html>
            <body style="font-family: sans-serif; border: 1px solid #ddd; padding: 20px; border-radius: 10px;">
                <h2 style="color: #1a73e8;">Sua viagem está confirmada!</h2>
                <p>Olá <strong>{pax_nome}</strong>, sua reserva foi emitida com sucesso.</p>
                <div style="background: #f8f9fa; padding: 15px; border-left: 5px solid #1a73e8;">
                    <p style="font-size: 20px; margin: 0;">Localizador (PNR): <strong>{pnr}</strong></p>
                    <p style="margin: 5px 0;">Companhia: {voo['Companhia']}</p>
                    <p style="margin: 5px 0;">Total Pago: {voo['Moeda']} {voo['Preço']:.2f}</p>
                </div>
                <p>Para gerir a sua reserva ou cancelar, aceda à <strong>Área do Cliente</strong> no nosso site.</p>
            </body>
        </html>
        """
        msg.attach(MIMEText(html, 'html'))
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(email_origem, senha_origem)
            server.sendmail(email_origem, pax_email, msg.as_string())
        return True
    except:
        return False

# --- INICIALIZAÇÃO DE ESTADOS ---
if 'pagina' not in st.session_state: st.session_state.pagina = "busca"
if 'voo_selecionado' not in st.session_state: st.session_state.voo_selecionado = None
if 'resultados_voos' not in st.session_state: st.session_state.resultados_voos = []

# --- MENU LATERAL (NAVEGAÇÃO) ---
with st.sidebar:
    st.title("📌 Menu GDS")
    if st.button("🔍 Procurar Voos"): st.session_state.pagina = "busca"
    if st.button("🔑 Área do Cliente"): st.session_state.pagina = "area_cliente"
    st.divider()
    st.caption("Suporte: suporte@flightmonitor.com")

# --- PÁGINA 1: BUSCA E RESULTADOS ---
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
    opcoes_lista = ["Selecione..."]
    for regiao, items in cidades.items():
        for nome, iata in items.items():
            mapa_iata[nome] = iata
            opcoes_lista.append(nome)

    tipo_v = st.radio("Tipo de Viagem", ["Ida e volta", "Somente ida"], horizontal=True)

    with st.form("busca_voos_real"):
        col1, col2 = st.columns(2)
        origem_sel = col1.selectbox("Origem", opcoes_lista)
        destino_sel = col2.selectbox("Destino", opcoes_lista)
        
        col3, col4 = st.columns(2)
        data_ida = col3.date_input("Data de Partida", value=datetime.today())
        data_volta = col4.date_input("Data de Regresso", value=datetime.today() + timedelta(days=7)) if tipo_v == "Ida e volta" else None

        p1, p2, p3 = st.columns(3)
        adultos = p1.number_input("Adultos", 1, 9, 1)
        criancas = p2.number_input("Crianças", 0, 9, 0)
        bebes = p3.number_input("Bebés", 0, adultos, 0)

        moeda_pref = st.selectbox("Moeda", ["Euro (€)", "Real (R$)"])
        btn_pesquisar = st.form_submit_button("PESQUISAR TARIFAS REAIS")

    if btn_pesquisar:
        try:
            with st.spinner('A consultar a Duffel API...'):
                api_token = st.secrets.get("DUFFEL_TOKEN")
                headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                is_br = "Real" in moeda_pref
                
                pax_list = [{"type": "adult"}] * adultos + [{"type": "child"}] * criancas + [{"type": "infant"}] * bebes
                slices = [{"origin": mapa_iata[origem_sel], "destination": mapa_iata[destino_sel], "departure_date": str(data_ida)}]
                if data_volta: slices.append({"origin": mapa_iata[destino_sel], "destination": mapa_iata[origem_sel], "departure_date": str(data_volta)})

                payload = {"data": {"slices": slices, "passengers": pax_list, "requested_currencies": ["BRL" if is_br else "EUR"]}}
                res = requests.post("https://api.duffel.com/air/offer_requests", headers=headers, json=payload)
                
                if res.status_code == 201:
                    data_res = res.json()["data"]
                    st.session_state.resultados_voos = []
                    for o in data_res.get("offers", [])[:5]:
                        preco_venda = float(o["total_amount"]) * (1 + COMISSAO_PERCENTUAL)
                        st.session_state.resultados_voos.append({
                            "id_offer": o["id"], "pax_ids": [p["id"] for p in data_res.get("passengers", [])],
                            "Companhia": o["owner"]["name"], "Preço": preco_venda, "Moeda": "R$" if is_br else "€"
                        })
                    st.success("Voos encontrados!")
        except Exception as e: st.error(f"Erro: {e}")

    if st.session_state.resultados_voos:
        for v in st.session_state.resultados_voos:
            with st.expander(f"✈️ {v['Companhia']} - {v['Moeda']} {v['Preço']:.2f}"):
                if st.button("Escolher Voo", key=v['id_offer']):
                    st.session_state.voo_selecionado = v
                    st.session_state.pagina = "reserva"
                    st.rerun()

# --- PÁGINA 2: RESERVA E CHECKOUT ---
elif st.session_state.pagina == "reserva":
    v = st.session_state.voo_selecionado
    st.title("🏁 Checkout Seguro")
    
    with st.form("final_real_checkout"):
        st.subheader("👤 Passageiro")
        c1, c2 = st.columns(2)
        nome = c1.text_input("Primeiro Nome")
        sobrenome = c2.text_input("Apelido")
        data_nasc = st.date_input("Nascimento", value=datetime(1990,1,1), min_value=datetime(1900,1,1), max_value=datetime.today())
        
        c3, c4 = st.columns(2)
        doc_n = c3.text_input("Nº Documento")
        email_p = c4.text_input("E-mail para Bilhete")
        tel_p = st.text_input("Telemóvel (+351... ou +55...)")

        st.subheader("💳 Pagamento")
        n_cartao = st.text_input("Número do Cartão")
        
        if st.form_submit_button("EMITIR BILHETE AGORA"):
            try:
                with st.spinner('A processar emissão...'):
                    api_token = st.secrets["DUFFEL_TOKEN"]
                    headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                    
                    payload = {
                        "data": {
                            "type": "instant", "selected_offers": [v['id_offer']],
                            "passengers": [{
                                "id": v['pax_ids'][0], "given_name": nome, "family_name": sobrenome,
                                "gender": "m", "born_on": str(data_nasc), "email": email_p, "phone_number": tel_p
                            }],
                            "payments": [{"type": "balance", "currency": "EUR" if "€" in v['Moeda'] else "BRL", "amount": str(v['Preço'])}]
                        }
                    }
                    res = requests.post("https://api.duffel.com/air/orders", headers=headers, json=payload)
                    
                    if res.status_code == 201:
                        pnr = res.json()["data"]["booking_reference"]
                        enviar_email_confirmacao(nome, email_p, v, pnr)
                        st.balloons()
                        st.success(f"✅ SUCESSO! PNR: {pnr}. Bilhete enviado para o e-mail.")
                    else:
                        st.error(f"Erro na Emissão: {res.json()['errors'][0]['message']}")
            except Exception as e: st.error(f"Erro Técnico: {e}")

# --- PÁGINA 3: ÁREA DO CLIENTE ---
elif st.session_state.pagina == "area_cliente":
    st.title("🔑 Área de Gestão de Reserva")
    st.write("Consulte os seus voos, peça cancelamentos ou fale com o suporte.")
    
    login_email = st.text_input("E-mail da reserva")
    login_pnr = st.text_input("Localizador (PNR)")
    
    if st.button("Aceder à Minha Viagem"):
        if login_pnr:
            st.divider()
            st.markdown(f"### Olá! Reserva `{login_pnr}` encontrada.")
            st.info("Voo: Lisboa (LIS) ➡️ São Paulo (GRU) | Status: Confirmado")
            
            c_sup1, c_sup2 = st.columns(2)
            if c_sup1.button("❌ Solicitar Cancelamento"):
                st.warning("O seu pedido de cancelamento foi enviado. Analisaremos as taxas da companhia aérea.")
            if c_sup2.button("💬 Chat com Consultor"):
                st.success("Consultor Emmanoel entrará em contacto via WhatsApp em instantes.")
        else:
            st.error("PNR não encontrado.")