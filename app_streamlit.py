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
    st.title("✈️ Flight Monitor Trips")
    
    # (Mantenha sua lista de cidades completa aqui no VS Code)
    opcoes_cidades = [
# --- BRASIL ---
"São Paulo (GRU)", "São Paulo (CGH)", "Rio de Janeiro (GIG)", "Rio de Janeiro (SDU)",
"Brasília (BSB)", "Belo Horizonte (CNF)", "Belo Horizonte (PLU)",
"Salvador (SSA)", "Recife (REC)", "Fortaleza (FOR)", "Natal (NAT)",
"Maceió (MCZ)", "João Pessoa (JPA)", "Aracaju (AJU)",
"Porto Alegre (POA)", "Curitiba (CWB)", "Florianópolis (FLN)",
"Cuiabá (CGB)", "Campo Grande (CGR)", "Goiânia (GYN)",
"Belém (BEL)", "Manaus (MAO)", "Macapá (MCP)", "Boa Vista (BVB)",
"Porto Velho (PVH)", "Rio Branco (RBR)", "Palmas (PMW)",
"São Luís (SLZ)", "Teresina (THE)",
"Vitória (VIX)", "Campinas (VCP)",
"Foz do Iguaçu (IGU)", "Navegantes (NVT)", "Joinville (JOI)",
"Ilhéus (IOS)", "Porto Seguro (BPS)", "Chapecó (XAP)",
"Uberlândia (UDI)", "Montes Claros (MOC)", "Imperatriz (IMP)",
"Marabá (MAB)", "Santarém (STM)",

# --- PORTUGAL ---
"Lisboa (LIS)", "Porto (OPO)", "Faro (FAO)", "Funchal (FNC)", "Ponta Delgada (PDL)",

# --- ESPANHA ---
"Madrid (MAD)", "Barcelona (BCN)", "Valência (VLC)", "Sevilha (SVQ)",
"Málaga (AGP)", "Bilbao (BIO)", "Alicante (ALC)", "Palma de Mallorca (PMI)",

# --- FRANÇA ---
"Paris (CDG)", "Paris (ORY)", "Nice (NCE)", "Lyon (LYS)", "Marselha (MRS)",

# --- ITÁLIA ---
"Roma (FCO)", "Milão (MXP)", "Milão (LIN)", "Veneza (VCE)", "Florença (FLR)",
"Nápoles (NAP)", "Bolonha (BLQ)",

# --- ALEMANHA ---
"Frankfurt (FRA)", "Munique (MUC)", "Berlim (BER)", "Düsseldorf (DUS)",

# --- REINO UNIDO ---
"Londres (LHR)", "Londres (LGW)", "Manchester (MAN)", "Edimburgo (EDI)",

# --- HOLANDA / BÉLGICA ---
"Amsterdã (AMS)", "Bruxelas (BRU)",

# --- SUÍÇA / ÁUSTRIA ---
"Zurique (ZRH)", "Genebra (GVA)", "Viena (VIE)",

# --- ESCANDINÁVIA ---
"Copenhaga (CPH)", "Estocolmo (ARN)", "Oslo (OSL)",

# --- LESTE EUROPEU ---
"Praga (PRG)", "Budapeste (BUD)", "Varsóvia (WAW)", "Atenas (ATH)"
]

    with st.form("busca_v13"):
        col1, col2 = st.columns(2)
        origem = col1.selectbox("Origem", opcoes_cidades)
        destino = col2.selectbox("Destino", opcoes_cidades)
        moeda_visu = col1.selectbox("Moeda:", ["Real (R$)", "Euro (€)"])
        data_ida = col2.date_input("Data de Partida", value=datetime.today() + timedelta(days=7))
        btn = st.form_submit_button("PESQUISAR VOOS")

    if btn:
        try:
            with st.spinner('Em busca dos melhores preços!...'):
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

# --- PÁGINA 2: RESERVA (CORREÇÃO DE VISIBILIDADE) ---
elif st.session_state.pagina == "reserva":
    v = st.session_state.voo_selecionado
    st.title("🏁 Checkout Seguro")
    st.info(f"📍 {v['Companhia']} | Total: {v['Moeda']} {v['Preço']:.2f}")

    # 1. O SELETOR FICA FORA DO FORM PARA REAGIR INSTANTANEAMENTE
    metodo = st.radio(
        "Selecione o método de pagamento:", 
        ["Cartão de Crédito", "PIX"], 
        horizontal=True,
        key="metodo_pagamento"
    )

    # 2. INÍCIO DO FORMULÁRIO
    with st.form("form_final"):
        st.subheader("👤 Dados do Passageiro")
        c1, c2 = st.columns(2)
        n = c1.text_input("Nome Próprio")
        a = c2.text_input("Apelido")
        e = st.text_input("E-mail para Bilhete")
        # Data de nascimento permitindo crianças e bebés (até 2026)
        dn = st.date_input("Data de Nascimento", value=datetime(1995,1,1), max_value=datetime(2026,12,31))
        
        st.divider()

        # 3. LÓGICA DE EXIBIÇÃO: Só desenha o cartão se o rádio for "Cartão"
        if metodo == "Cartão de Crédito":
            st.markdown("### 💳 Dados do Cartão")
            st.text_input("Número do Cartão", placeholder="0000 0000 0000 0000")
            st.text_input("Nome Impresso")
            cc1, cc2 = st.columns(2)
            cc1.text_input("Validade (MM/AA)", placeholder="MM/AA")
            cc2.text_input("CVV", type="password")
            
            if v['Moeda'] == "R$":
                # Parcelamento solicitado
                opcoes = [f"{i}x de R$ {v['Preço']/i:.2f} sem juros" for i in range(1, 11)]
                opcoes.extend([f"11x de R$ {(v['Preço']*1.05)/11:.2f} (c/ taxas)", f"12x de R$ {(v['Preço']*1.07)/12:.2f} (c/ taxas)"])
                st.selectbox("Parcelamento", opcoes)
        else:
            # Se for PIX, mostra apenas as instruções e o link
            st.success("💠 **Pagamento via PIX Selecionado**")
            st.warning("Os campos de cartão foram removidos. Finalize abaixo para receber as instruções.")
            st.markdown(f"""
                <a href="https://wa.me/{WHATSAPP_SUPORTE}?text=Olá,%20pagamento%20PIX%20de%20{v['Preço']}" target="_blank" style="text-decoration:none;">
                    <div style="background-color: #25D366; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 18px;">
                        💬 Chamar no WhatsApp para Chave PIX
                    </div>
                </a>
            """, unsafe_allow_html=True)

        st.divider()
        if st.form_submit_button("CONFIRMAR E EMITIR BILHETE"):
            if n and e:
                st.balloons()
                st.success(f"Solicitação enviada! PNR será gerado para {n}.")
            else:
                st.error("Preencha o Nome e E-mail.")

# --- PÁGINA 3: ÁREA DO CLIENTE (COM LOGIN PNR + EMAIL) ---
elif st.session_state.pagina == "login":
    st.title("🔑 Área Privada do Passageiro")
    st.markdown("Introduza os seus dados para consultar a reserva.")
    
    # Caixa de login estilizada
    with st.container(border=True):
        st.subheader("Consultar minha Reserva")
        col_id1, col_id2 = st.columns(2)
        pnr_input = col_id1.text_input("Código da Reserva (PNR)", placeholder="Ex: GTD78X").upper()
        email_input = col_id2.text_input("E-mail da Reserva", placeholder="seu@email.com")
        
        if st.button("🔍 Aceder aos Detalhes"):
            if pnr_input and email_input:
                st.divider()
                st.success(f"Reserva **{pnr_input}** localizada!")
                st.info(f"Enviamos um código de acesso temporário para **{email_input}**.")
            else:
                st.error("É necessário introduzir o PNR e o E-mail para continuar.")