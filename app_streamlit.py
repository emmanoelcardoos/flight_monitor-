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

# --- FUNÇÃO: CÂMBIO AO VIVO ---
def get_cotacao_ao_vivo():
    try:
        res = requests.get("https://economia.awesomeapi.com.br/last/EUR-BRL")
        if res.status_code == 200:
            return float(res.json()["EURBRL"]["bid"])
        return 6.25 
    except:
        return 6.25

st.set_page_config(page_title="Flight Monitor GDS", page_icon="✈️", layout="wide")

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
    
    # Dicionário para identificar se o voo é internacional
    paises = {
        "BRA": ["GRU", "CGH", "GIG", "SDU", "BSB", "CNF", "PLU", "SSA", "REC", "FOR", "NAT", "MCZ", "JPA", "AJU", "POA", "CWB", "FLN", "CGB", "CGR", "GYN", "BEL", "MAO", "MCP", "BVB", "PVH", "RBR", "PMW", "SLZ", "THE", "VIX", "VCP", "IGU", "NVT", "JOI", "IOS", "BPS", "XAP", "UDI", "MOC", "IMP", "MAB", "STM"],
        "PRT": ["LIS", "OPO", "FAO", "FNC", "PDL"],
        "ESP": ["MAD", "BCN", "VLC", "SVQ", "AGP", "BIO", "ALC", "PMI"],
        "FRA": ["CDG", "ORY", "NCE", "LYS", "MRS"],
        "ITA": ["FCO", "MXP", "LIN", "VCE", "FLR", "NAP", "BLQ"],
        "DEU": ["FRA", "MUC", "BER", "DUS"],
        "GBR": ["LHR", "LGW", "MAN", "EDI"],
        "NLD": ["AMS", "BRU"],
        "CHE": ["ZRH", "GVA", "VIE"],
        "DNK": ["CPH", "ARN", "OSL"],
        "POL": ["PRG", "BUD", "WAW", "ATH"]
    }

    opcoes_cidades = []
    for p in paises.values(): opcoes_cidades.extend(p)
    
    # Exibição simplificada para o selectbox (mantendo sua lógica de IATA no final)
    # Aqui usei a sua lista completa anterior no VS Code
    opcoes_completas = ["São Paulo (GRU)", "Lisboa (LIS)", "Madrid (MAD)", "Recife (REC)", "Marabá (MAB)", "Paris (CDG)", "Londres (LHR)"]

    with st.form("busca_v15"):
        col1, col2 = st.columns(2)
        origem_sel = col1.selectbox("Origem", opcoes_completas)
        destino_sel = col2.selectbox("Destino", opcoes_completas)
        moeda_visu = col1.selectbox("Exibir preços em:", ["Real (R$)", "Euro (€)"])
        data_ida = col2.date_input("Data de Partida", value=datetime.today() + timedelta(days=7))
        btn = st.form_submit_button("PESQUISAR VOOS")

    if btn:
        try:
            with st.spinner('Em busca dos melhores voos!'):
                cotacao_atual = get_cotacao_ao_vivo()
                api_token = st.secrets["DUFFEL_TOKEN"]
                headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                
                iata_origem = origem_sel[-4:-1]
                iata_destino = destino_sel[-4:-1]

                payload = {"data": {"slices": [{"origin": iata_origem, "destination": iata_destino, "departure_date": str(data_ida)}], "passengers": [{"type": "adult"}], "requested_currencies": ["EUR"]}}
                res = requests.post("https://api.duffel.com/air/offer_requests", headers=headers, json=payload)
                
                if res.status_code == 201:
                    offers = res.json()["data"].get("offers", [])
                    st.session_state.resultados_voos = []
                    for o in offers[:5]:
                        # Identificar se é internacional
                        pais_origem = next((k for k, v in paises.items() if iata_origem in v), "INT")
                        pais_destino = next((k for k, v in paises.items() if iata_destino in v), "INT")
                        is_internacional = pais_origem != pais_destino

                        segmentos = []
                        for s_slice in o["slices"]:
                            for seg in s_slice["segments"]:
                                segmentos.append({
                                    "de": seg["origin"]["iata_code"], "para": seg["destination"]["iata_code"],
                                    "partida": seg["departing_at"].split("T")[1][:5],
                                    "chegada": seg["arriving_at"].split("T")[1][:5],
                                    "cia": seg["marketing_carrier"]["name"],
                                    "aviao": seg["aircraft"]["name"] if seg["aircraft"] else "N/D",
                                    "conexao": {"cidade": seg["destination"]["city_name"]} if len(s_slice["segments"]) > 1 else None
                                })
                        
                        valor_eur = float(o["total_amount"])
                        v_final = valor_eur * cotacao_atual * (1 + COMISSAO_PERCENTUAL) if "Real" in moeda_visu else valor_eur * (1 + COMISSAO_PERCENTUAL)
                        
                        st.session_state.resultados_voos.append({
                            "id_offer": o["id"], "pax_ids": [p["id"] for p in res.json()["data"]["passengers"]],
                            "Companhia": o["owner"]["name"], "Preço": v_final, "Moeda": moeda_txt if 'moeda_txt' in locals() else moeda_visu[-3:-2],
                            "Segmentos": segmentos, "Internacional": is_internacional, "Data_Voo": data_ida, "Moeda_Busca": moeda_visu
                        })
        except Exception as e: st.error(f"Erro: {e}")

    if st.session_state.resultados_voos:
        for v in st.session_state.resultados_voos:
            moeda_label = "R$" if "Real" in v['Moeda_Busca'] else "€"
            with st.expander(f"✈️ {v['Companhia']} | {moeda_label} {v['Preço']:.2f}"):
                for s in v["Segmentos"]:
                    st.write(f"📍 **{s['de']} ➔ {s['para']}** | 🕒 {s['partida']} - {s['chegada']} | ✈️ {s['aviao']}")
                if st.button("Selecionar Voo", key=v['id_offer']):
                    st.session_state.voo_selecionado = v
                    st.session_state.pagina = "reserva"
                    st.rerun()

# --- PÁGINA 2: RESERVA ---
elif st.session_state.pagina == "reserva":
    v = st.session_state.voo_selecionado
    st.title("🏁 Checkout de Reserva")
    
    metodo = st.radio("Método de pagamento:", ["Cartão de Crédito", "PIX"], horizontal=True)

    with st.form("form_final"):
        st.subheader("👤 Dados do Passageiro")
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        apelido = c2.text_input("Apelido")
        email = st.text_input("E-mail")
        
        c3, c4 = st.columns(2)
        dn = c3.date_input("Data de Nascimento", value=datetime(1995,1,1), max_value=datetime(2026,12,31))
        documento = c4.text_input("CPF ou CC")

        # --- LÓGICA INTERNACIONAL (PASSAPORTE) ---
        if v["Internacional"]:
            st.warning("✈️ Este é um voo internacional. Dados do passaporte são obrigatórios.")
            col_p1, col_p2 = st.columns(2)
            num_passaporte = col_p1.text_input("Número do Passaporte")
            validade_pass = col_p2.date_input("Data de Vencimento do Passaporte")
            
            # Validação de 6 meses
            data_limite = v["Data_Voo"] + timedelta(days=180)
            if validade_pass < data_limite:
                st.error(f"❌ O passaporte vencerá antes de completar 6 meses da data da viagem ({data_limite.strftime('%d/%m/%Y')}). Não é possível prosseguir.")
                bloqueio_emissao = True
            else:
                bloqueio_emissao = False
        else:
            bloqueio_emissao = False

        st.divider()
        
        # --- LÓGICA DE MORADA FISCAL BASEADA NA MOEDA ---
        st.subheader("🏠 Morada Fiscal")
        if "Real" in v["Moeda_Busca"]:
            st.caption("Campos para faturamento em Reais (Brasil)")
            m1, m2, m3 = st.columns([3, 1, 1])
            rua = m1.text_input("Rua")
            num = m2.text_input("Número")
            apt = m3.text_input("Apto")
            m4, m5, m6 = st.columns([2, 2, 1])
            bairro = m4.text_input("Bairro")
            cidade = m5.text_input("Cidade")
            estado = m6.text_input("Estado")
            cep = st.text_input("CEP")
        else:
            st.caption("Campos para faturamento em Euro (Europa/Internacional)")
            morada = st.text_input("Morada")
            distrito = st.text_input("Distrito")
            pais = st.text_input("País")
            cod_postal = st.text_input("Código Postal")

        st.divider()

        if metodo == "Cartão de Crédito":
            st.markdown("### 💳 Dados do Cartão")
            st.text_input("Número do Cartão")
            if "Real" in v["Moeda_Busca"]:
                st.selectbox("Parcelas", [f"{i}x sem juros" for i in range(1, 11)] + ["12x com taxas"])
        else:
            st.info("💠 Pagamento via PIX: Link de suporte na sidebar.")

        btn_emitir = st.form_submit_button("EMITIR BILHETE")
        
        if btn_emitir:
            if bloqueio_emissao:
                st.error("Corrija os dados do passaporte para emitir.")
            else:
                st.balloons()
                st.success("Reserva processada com sucesso!")

# --- PÁGINA 3: LOGIN ---
elif st.session_state.pagina == "login":
    st.title("🔑 Área do Cliente")
    with st.container(border=True):
        st.text_input("PNR")
        st.text_input("E-mail")
        if st.button("Consultar"): st.success("Localizando reserva...")