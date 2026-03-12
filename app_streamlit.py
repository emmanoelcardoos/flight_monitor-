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
        return 6.02
    except:
        return 6.02

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

    paises_br = ["GRU", "CGH", "GIG", "SDU", "BSB", "CNF", "SSA", "REC", "FOR", "MAO", "BEL", "MAB", "STM", "CWB", "POA", "FLN"]

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

                iata_o = origem[-4:-1]
                iata_d = destino[-4:-1]

                is_intl = not (iata_o in paises_br and iata_d in paises_br)

                payload = {
                    "data": {
                        "slices": [{
                            "origin": iata_o,
                            "destination": iata_d,
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
                            "Cotacao_Usada": cotacao_atual,
                            "Internacional": is_intl,
                            "Moeda_Busca": moeda_visu,
                            "Data_Voo": data_ida
                        })

                    st.success(f"Cotação aplicada: 1€ = R$ {cotacao_atual:.2f}")
                else:
                    st.error("Erro na API da Duffel. Verifique seu Token.")

        except Exception as e:
            st.error(f"Erro: {e}")

# --- PÁGINA 2: RESERVA ---
elif st.session_state.pagina == "reserva":

    v = st.session_state.voo_selecionado

    st.title("🏁 Checkout")
    st.divider()

    metodo = st.radio("Método de pagamento:", ["Cartão de Crédito", "PIX"], horizontal=True)

    with st.form("form_final"):

        nome = st.text_input("Nome")
        apelido = st.text_input("Apelido")
        email = st.text_input("E-mail")

        dn = st.date_input("Data de Nascimento", value=datetime(1995,1,1))

        documento = st.text_input("Documento")

        if st.form_submit_button("CONFIRMAR E EMITIR BILHETE"):

            try:

                with st.spinner('Comunicando com o emissor do cartão (Visa/Mastercard)...'):

                    api_token = st.secrets["DUFFEL_TOKEN"]

                    headers = {
                        "Authorization": f"Bearer {api_token}",
                        "Duffel-Version": "v2",
                        "Content-Type": "application/json"
                    }

                    moeda_pagamento = "BRL" if v["Moeda"] == "R$" else "EUR"

                    payload = {
                        "data": {
                            "type": "instant",
                            "selected_offers": [v['id_offer']],
                            "passengers": [{
                                "id": v['pax_ids'][0],
                                "given_name": nome,
                                "family_name": apelido,
                                "gender": "Masculino" "Feminino",
                                "born_on": str(dn),
                                "email": email,
                                "phone_number": "+351936797003"
                            }],
                            "payments": [{
                                "type": "payment_intent",
                                "currency": moeda_pagamento,
                                "amount": str(round(v['Preço'], 2))
                            }]
                        }
                    }

                    res = requests.post(
                        "https://api.duffel.com/air/orders",
                        headers=headers,
                        json=payload
                    )

                    if res.status_code == 201:
                        st.success("Bilhete Emitido!")
                    else:
                        erro_json = res.json()
                        mensagem_erro = erro_json.get("errors", [{}])[0].get("message", "")
                        st.error(f"Erro: {mensagem_erro}")

            except Exception as ex:
                st.error(f"Falha técnica: {ex}")

# --- PÁGINA 3: LOGIN ---
elif st.session_state.pagina == "login":

    st.title("🔑 Área do Cliente")

    with st.container(border=True):

        st.text_input("PNR")
        st.text_input("E-mail")

        if st.button("Consultar"):
            st.success("Localizando reserva...")