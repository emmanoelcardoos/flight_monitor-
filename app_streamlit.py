import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURAÇÃO DE NEGÓCIO ---
COMISSAO_PERCENTUAL = 0.12 
WHATSAPP_SUPORTE = "351936797003" 

def get_cotacao_ao_vivo():
    try:
        res = requests.get("https://economia.awesomeapi.com.br/last/EUR-BRL")
        if res.status_code == 200:
            return float(res.json()["EURBRL"]["bid"])
        return 6.25
    except:
        return 6.25

st.set_page_config(page_title="Flight Monitor GDS", page_icon="✈️", layout="wide")

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
    
    # Adicionei IDs de países para lógica internacional
    paises_br = ["GRU", "CGH", "GIG", "SDU", "BSB", "CNF", "SSA", "REC", "FOR", "MAO", "BEL", "MAB"]
    
    opcoes_cidades = ["São Paulo (GRU)", "Lisboa (LIS)", "Madrid (MAD)", "Recife (REC)", "Marabá (MAB)", "Paris (CDG)"]

    with st.form("busca_v14"):
        col1, col2 = st.columns(2)
        origem = col1.selectbox("Origem", opcoes_cidades)
        destino = col2.selectbox("Destino", opcoes_cidades)
        moeda_visu = col1.selectbox("Exibir preços em:", ["Real (R$)", "Euro (€)"])
        data_ida = col2.date_input("Data de Partida", value=datetime.today() + timedelta(days=7))
        btn = st.form_submit_button("PESQUISAR VOOS")

    if btn:
        try:
            with st.spinner('Buscando voos...'):
                cotacao_atual = get_cotacao_ao_vivo()
                api_token = st.secrets["DUFFEL_TOKEN"]
                headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                
                iata_o = origem[-4:-1]
                iata_d = destino[-4:-1]
                
                # Lógica Internacional: Se um não for BR ou destinos diferentes de PT para PT, etc.
                is_intl = not (iata_o in paises_br and iata_d in paises_br)

                payload = {"data": {"slices": [{"origin": iata_o, "destination": iata_d, "departure_date": str(data_ida)}], "passengers": [{"type": "adult"}], "requested_currencies": ["EUR"]}}
                res = requests.post("https://api.duffel.com/air/offer_requests", headers=headers, json=payload)
                
                if res.status_code == 201:
                    offers = res.json()["data"].get("offers", [])
                    st.session_state.resultados_voos = []
                    for o in offers[:5]:
                        # ... (lógica de segmentos mantida)
                        valor_eur = float(o["total_amount"])
                        v_final = valor_eur * cotacao_atual * (1 + COMISSAO_PERCENTUAL) if "Real" in moeda_visu else valor_eur * (1 + COMISSAO_PERCENTUAL)
                        
                        st.session_state.resultados_voos.append({
                            "id_offer": o["id"],
                            "pax_ids": [p["id"] for p in res.json()["data"]["passengers"]],
                            "Companhia": o["owner"]["name"],
                            "Preço": v_final,
                            "Moeda": "R$" if "Real" in moeda_visu else "€",
                            "Segmentos": [], # Simplificado para o exemplo
                            "Internacional": is_intl,
                            "Moeda_Busca": moeda_visu,
                            "Data_Voo": data_ida
                        })
                st.success(f"Cotação: 1€ = R$ {cotacao_atual:.2f}")
        except Exception as e: st.error(f"Erro: {e}")

    if st.session_state.resultados_voos:
        for v in st.session_state.resultados_voos:
            with st.expander(f"✈️ {v['Companhia']} | {v['Moeda']} {v['Preço']:.2f}"):
                if st.button("Selecionar", key=v['id_offer']):
                    st.session_state.voo_selecionado = v
                    st.session_state.pagina = "reserva"
                    st.rerun()

# --- PÁGINA 2: RESERVA ---
elif st.session_state.pagina == "reserva":
    v = st.session_state.voo_selecionado
    st.title("🏁 Checkout")
    st.divider()

    # O rádio do método deve ficar fora ou dentro do form? 
    # Para ser reativo (esconder campos), melhor fora.
    metodo = st.radio("Método de pagamento:", ["Cartão de Crédito", "PIX"], horizontal=True)

    with st.form("form_final"):
        st.subheader("👤 Dados do Passageiro")
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        apelido = c2.text_input("Apelido")
        email = st.text_input("E-mail")
        
        c3, c4 = st.columns(2)
        dn = c3.date_input("Data de Nascimento", value=datetime(1995,1,1), max_value=datetime(2026,12,31))
        documento = c4.text_input("CPF ou CC (Documento de Identidade)")

        # --- VALIDAÇÃO PASSAPORTE ---
        bloqueio_emissao = False
        if v.get("Internacional"):
            st.warning("✈️ Voo Internacional: Passaporte Obrigatório")
            cp1, cp2 = st.columns(2)
            pass_num = cp1.text_input("Número do Passaporte")
            pass_val = cp2.date_input("Vencimento do Passaporte")
            
            limite_6m = v["Data_Voo"] + timedelta(days=180)
            if pass_val < limite_6m:
                st.error(f"❌ Passaporte vence antes de {limite_6m.strftime('%d/%m/%Y')}. Não permitido.")
                bloqueio_emissao = True

        st.divider()
        st.subheader("🏠 Morada Fiscal")
        
        if "Real" in v["Moeda_Busca"]:
            m1, m2, m3 = st.columns([3, 1, 1])
            rua = m1.text_input("Rua/Logradouro")
            num = m2.text_input("Nº")
            apt = m3.text_input("Apto/Bloco")
            m4, m5, m6 = st.columns([2, 2, 1])
            bairro = m4.text_input("Bairro")
            cidade = m5.text_input("Cidade")
            estado = m6.text_input("Estado (UF)")
            cep = st.text_input("CEP")
        else:
            morada = st.text_input("Morada / Address Line")
            ce1, ce2 = st.columns(2)
            distrito = ce1.text_input("Distrito")
            cp_intl = ce2.text_input("Código Postal")
            pais = st.text_input("País")

        if metodo == "Cartão de Crédito":
            st.markdown("### 💳 Cartão")
            st.text_input("Número do Cartão")
            if v['Moeda'] == "R$":
                st.selectbox("Parcelas", [f"{i}x sem juros" for i in range(1, 11)] + ["12x com taxas"])
        else:
            st.info("💠 Pagamento via PIX: Utilize o suporte abaixo.")
            st.markdown(f"[💬 WhatsApp Suporte](https://wa.me/{WHATSAPP_SUPORTE})")

        # ÚNICO BOTÃO DE EMISSÃO
        btn_emitir = st.form_submit_button("CONFIRMAR E EMITIR BILHETE")
        
        if btn_emitir:
            if bloqueio_emissao:
                st.error("Verifique a validade do passaporte.")
            elif not nome or not email:
                st.error("Preencha os campos obrigatórios.")
            else:
                st.balloons()
                st.success("Reserva enviada!")

# --- PÁGINA 3: LOGIN ---
elif st.session_state.pagina == "login":
    st.title("🔑 Área do Cliente")
    with st.container(border=True):
        st.text_input("PNR")
        st.text_input("E-mail")
        if st.button("Consultar"): st.success("Localizando...")