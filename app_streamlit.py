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
if 'pagina' not in st.session_state:
    st.session_state.pagina = "busca"

if 'voo_selecionado' not in st.session_state:
    st.session_state.voo_selecionado = None

if 'resultados_voos' not in st.session_state:
    st.session_state.resultados_voos = []

# --- SIDEBAR ---
with st.sidebar:
    st.title("📌 Flight Monitor")
    if st.button("🔍 Procurar Voos"):
        st.session_state.pagina = "busca"

    if st.button("👤 Área do Cliente"):
        st.session_state.pagina = "login"

    st.divider()
    st.markdown(f"**Suporte:** [WhatsApp](https://wa.me/{WHATSAPP_SUPORTE})")

# --- PÁGINA 1: BUSCA ---
if st.session_state.pagina == "busca":

    st.title("✈️ Flight Monitor Trips")

    opcoes_cidades = [
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
        "Uberlândia (UDI)", "Montes Claros (MOC)",
        "Imperatriz (IMP)", "Marabá (MAB)", "Santarém (STM)",
        "Lisboa (LIS)", "Porto (OPO)", "Faro (FAO)", "Funchal (FNC)", "Ponta Delgada (PDL)",
        "Madrid (MAD)", "Barcelona (BCN)", "Valência (VLC)", "Sevilha (SVQ)",
        "Paris (CDG)", "Roma (FCO)", "Milão (MXP)", "Frankfurt (FRA)", "Londres (LHR)"
    ]

    with st.form("busca_v14"):

        col1, col2 = st.columns(2)

        origem = col1.selectbox("Origem", opcoes_cidades)
        destino = col2.selectbox("Destino", opcoes_cidades)

        moeda_visu = col1.selectbox("Exibir preços em:", ["Real (R$)", "Euro (€)"])

        data_ida = col2.date_input(
            "Data de Partida",
            value=datetime.today() + timedelta(days=7)
        )

        btn = st.form_submit_button("PESQUISAR VOOS")

    if btn:

        try:
            with st.spinner('Em busca dos melhores voos!'):

                cotacao_atual = get_cotacao_ao_vivo()

                api_token = st.secrets["DUFFEL_TOKEN"]

                headers = {
                    "Authorization": f"Bearer {api_token}",
                    "Duffel-Version": "v2",
                    "Content-Type": "application/json"
                }

                payload = {
                    "data": {
                        "slices": [{
                            "origin": origem[-4:-1],
                            "destination": destino[-4:-1],
                            "departure_date": str(data_ida)
                        }],
                        "passengers": [{"type": "adult"}],
                        "requested_currencies": ["EUR"]
                    }
                }

                res = requests.post(
                    "https://api.duffel.com/air/offer_requests",
                    headers=headers,
                    json=payload
                )

                if res.status_code == 201:

                    offers = res.json()["data"].get("offers", [])
                    st.session_state.resultados_voos = []

                    for o in offers[:5]:

                        bagagem = "Verificar no Checkout"

                        if "passenger_conditions" in o:
                            bagagem = "Incluída" if o["passenger_conditions"].get("baggage_allowance") else "Apenas item pessoal"

                        segmentos = []

                        for s_slice in o["slices"]:
                            segs = s_slice["segments"]

                            for i, seg in enumerate(segs):

                                conexao = {"cidade": seg["destination"]["city_name"]} if i < len(segs) - 1 else None

                                segmentos.append({
                                    "de": seg["origin"]["iata_code"],
                                    "para": seg["destination"]["iata_code"],
                                    "partida": seg["departing_at"].split("T")[1][:5],
                                    "chegada": seg["arriving_at"].split("T")[1][:5],
                                    "cia": seg["marketing_carrier"]["name"],
                                    "aviao": seg["aircraft"]["name"] if seg["aircraft"] else "N/D",
                                    "conexao": conexao
                                })

                        valor_eur = float(o["total_amount"])

                        if "Real" in moeda_visu:
                            v_final = valor_eur * cotacao_atual * (1 + COMISSAO_PERCENTUAL)
                            moeda_txt = "R$"
                        else:
                            v_final = valor_eur * (1 + COMISSAO_PERCENTUAL)
                            moeda_txt = "€"

                        st.session_state.resultados_voos.append({
                            "id_offer": o["id"],
                            "pax_ids": [p["id"] for p in res.json()["data"]["passengers"]],
                            "Companhia": o["owner"]["name"],
                            "Preço": v_final,
                            "Moeda": moeda_txt,
                            "Bagagem": bagagem,
                            "Segmentos": segmentos,
                            "Cotacao_Usada": cotacao_atual
                        })

                st.success(f"Cotação aplicada: 1€ = R$ {cotacao_atual:.2f}")

        except Exception as e:
            st.error(f"Erro: {e}")

# --- PÁGINA 2: RESERVA ---
elif st.session_state.pagina == "reserva":

    v = st.session_state.voo_selecionado

    st.title("🏁 Checkout")
    st.divider()

    st.subheader("🏠 Morada Fiscal / Endereço de Faturamento")

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

        col_e1, col_e2 = st.columns(2)
        distrito = col_e1.text_input("Distrito / Província")
        cod_postal = col_e2.text_input("Código Postal / Zip Code")

        pais = st.text_input("País")

    metodo = st.radio(
        "Método de pagamento:",
        ["Cartão de Crédito", "PIX"],
        horizontal=True
    )

    with st.form("form_final"):

        st.subheader("👤 Dados do Passageiro")

        bloqueio_emissao = False

        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        apelido = c2.text_input("Apelido")

        email = st.text_input("E-mail")

        c3, c4 = st.columns(2)
        dn = c3.date_input(
            "Data de Nascimento",
            value=datetime(1995, 1, 1),
            max_value=datetime(2026, 12, 31)
        )

        documento = c4.text_input("CPF ou CC (Documento de Identidade)")

        if v.get("Internacional", False):
            st.warning("✈️ Voo Internacional: Dados do passaporte obrigatórios.")
            col_p1, col_p2 = st.columns(2)
            num_passaporte = col_p1.text_input("Número do Passaporte")
            validade_pass = col_p2.date_input(
                "Data de Vencimento do Passaporte",
                key="pass_val"
            )

            data_limite_6meses = v["Data_Voo"] + timedelta(days=180)
            if validade_pass < data_limite_6meses:
                st.error(
                    f"❌ Erro: O passaporte deve ter validade mínima até "
                    f"{data_limite_6meses.strftime('%d/%m/%Y')} "
                    f"(6 meses após a viagem)."
                )
                bloqueio_emissao = True

        if metodo == "Cartão de Crédito":

            st.markdown("### 💳 Cartão")
            st.text_input("Número")

            if v['Moeda'] == "R$":
                st.selectbox(
                    "Parcelas",
                    [f"{i}x sem juros" for i in range(1, 11)] + ["12x com taxas"]
                )

        else:

            st.info("💠 Pagamento via PIX: Link de suporte abaixo.")
            st.markdown(f"[💬 Chamar no WhatsApp](https://wa.me/{WHATSAPP_SUPORTE})")

        if st.form_submit_button("CONFIRMAR E EMITIR BILHETE"):
            if bloqueio_emissao:
                st.error("Não é possível prosseguir: Verifique a validade do seu passaporte.")
            elif not nome or not email:
                st.error("Por favor, preencha os campos obrigatórios.")
            else:
                st.balloons()
                st.success("Reserva enviada com sucesso!")

# --- PÁGINA 3: LOGIN ---
elif st.session_state.pagina == "login":

    st.title("🔑 Área do Cliente")

    with st.container(border=True):

        st.text_input("PNR")
        st.text_input("E-mail")

        if st.button("Consultar"):
            st.success("Localizando reserva...")