import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit.components.v1 as components

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

# --- LOGO ABAIXO DAS SUAS OUTRAS FUNÇÕES ---

def criar_intencao_pagamento(valor_eur):
    try:
        api_token = st.secrets["DUFFEL_TOKEN"]
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Duffel-Version": "v2",
            "Content-Type": "application/json"
        }
        payload = {
            "data": {
                "amount": f"{valor_eur:.2f}",
                "currency": "EUR"
            }
        }
        res = requests.post("https://api.duffel.com/payments/payment_intents", headers=headers, json=payload)
        return res.json()
    except Exception as e:
        return {"errors": [{"message": str(e)}]}

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
                            "valor_bruto_duffel": o["total_amount"],
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

    if st.session_state.resultados_voos:
        st.write("### ✈️ Voos Encontrados")
        for idx, v in enumerate(st.session_state.resultados_voos):
            with st.expander(f"{v['Companhia']} - {v['Moeda']} {v['Preço']:.2f}", expanded=True):
                for seg in v["Segmentos"]:
                    col_a, col_b, col_c = st.columns(3)
                    col_a.markdown(f"**🛫 {seg['de']}**\n{seg['partida']}")
                    col_b.markdown(f"**🛬 {seg['para']}**\n{seg['chegada']}")
                    col_c.markdown(f"**✈️ Aeronave**\n{seg['aviao']}")

                if st.button("Selecionar Voo", key=f"sel_{v['id_offer']}_{idx}"):
                    st.session_state.voo_selecionado = v
                    st.session_state.pagina = "reserva"
                    st.rerun()

# --- PÁGINA 2: RESERVA (VERSÃO FINAL SEM ERROS) ---
elif st.session_state.pagina == "reserva":
    v = st.session_state.voo_selecionado
    # Adicione isso para mostrar os dados do voo
    st.info(f"✈️ **Voo:** {v['Companhia']} | **Trecho:** {v['Segmentos'][0]['de']} ➔ {v['Segmentos'][-1]['para']}")
    st.metric(label="Valor a Pagar", value=f"{v['Moeda']} {v['Preço']:.2f}")
    st.title("🏁 Checkout")
    st.divider()

    # Morada Fiscal
    st.subheader("🏠 Morada Fiscal / Faturamento")
    if "Real" in v.get("Moeda_Busca", "Real"):
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
        cod_postal = ce2.text_input("Código Postal")
        pais_fiscal = st.text_input("País")

    metodo = st.radio("Método de pagamento:", ["Cartão de Crédito", "PIX"], horizontal=True)

    # FORMULÁRIO PRINCIPAL
    with st.form("form_final_v16"):
        st.subheader("👤 Dados do Passageiro")
        
        c_tit1, c_tit2 = st.columns([1, 3])
        # RESOLVE O ERRO DE 'TITLE'
        titulo_pax = c_tit1.selectbox("Título", ["Sr.", "Sra.", "Srta."], key="pax_title_v16")
        
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        apelido = c2.text_input("Apelido")
        
        email = st.text_input("E-mail")
        
        c3, c4 = st.columns(2)
        dn = c3.date_input("Data de Nascimento", value=datetime(1995, 1, 1), max_value=datetime(2026, 2, 28))
        documento = c4.text_input("CPF ou CC (Documento de Identidade)")

        # RESOLVE O ERRO DE 'GENDER'
        genero_pax = st.selectbox("Gênero", ["Masculino", "Feminino"], key="pax_gender_v16")

        bloqueio_emissao = False
        if v.get("Internacional", False):
            st.warning("✈️ Voo Internacional: Passaporte obrigatório.")
            col_p1, col_p2 = st.columns(2)
            num_passaporte = col_p1.text_input("Número do Passaporte")
            validade_pass = col_p2.date_input("Vencimento Passaporte", key="pass_val_v16")
            data_limite_6meses = v["Data_Voo"] + timedelta(days=180)
            if validade_pass < data_limite_6meses:
                st.error("❌ Passaporte com validade inferior a 6 meses.")
                bloqueio_emissao = True

    # 1. FECHE O FORMULÁRIO (Certifique-se que o 'with st.form' terminou antes)
    # 2. O IF DO CARTÃO DEVE ESTAR ALINHADO À ESQUERDA (fora do form)

    # Este botão fecha o formulário 'form_final_v16' antes do pagamento
        st.form_submit_button("1. Salvar Dados do Passageiro")

    # --- FORA DO FORMULÁRIO ---
    if metodo == "Cartão de Crédito":
        st.markdown("### 💳 Pagamento Seguro")

        # Geramos a Intenção
        res_intencao = criar_intencao_pagamento(float(valor_exato_duffel))
        
        if "data" in res_intencao:
            client_token = res_intencao["data"]["client_token"]
            pit_id = res_intencao["data"]["id"]
            
            # Componente HTML
            duffel_card_html = f"""
            <script src="https://js.duffel.com/v2/duffel.js"></script>
            <div id="card-element" style="margin-bottom: 15px;"></div>
            <button id="pay-button" style="background-color: #007BFF; color: white; border: none; padding: 12px; border-radius: 5px; cursor: pointer; width: 100%; font-weight: bold;">
                AUTORIZAR PAGAMENTO
            </button>
            <p id="status-msg" style="color: #666; font-size: 14px; margin-top: 10px; font-family: sans-serif;"></p>

            <script>
                const duffel = new Duffel("{st.secrets["DUFFEL_TOKEN"]}");
                const cardElement = duffel.elements.create('card');
                cardElement.mount('#card-element');

                const btn = document.getElementById('pay-button');
                btn.addEventListener('click', async () => {{
                    btn.disabled = true;
                    btn.innerText = "Processando...";
                    document.getElementById('status-msg').innerText = "Consultando o banco...";

                    const result = await duffel.confirmPaymentIntent("{client_token}", {{
                        payment_method: {{ card: cardElement }}
                    }});

                    if (result.error) {{
                        document.getElementById('status-msg').style.color = "red";
                        document.getElementById('status-msg').innerText = result.error.message;
                        btn.disabled = false;
                        btn.innerText = "AUTORIZAR PAGAMENTO";
                    }} else {{
                        document.getElementById('status-msg').style.color = "green";
                        document.getElementById('status-msg').innerText = "Sucesso! Pagamento aprovado.";
                        btn.innerText = "PAGO";
                    }}
                }});
            </script>
            <style>
                #card-element {{ border: 1px solid #ced4da; padding: 12px; border-radius: 4px; background: white; }}
            </style>
            """
            components.html(duffel_card_html, height=200)

            # Parcelamento (Apenas visual)
            if v['Moeda'] == "R$":
                parcelas_list = [f"{i}x sem juros" for i in range(1, 11)] + ["11x com acréscimo", "12x com acréscimo"]
                st.selectbox("Parcelamento", parcelas_list, key="card_install_v17")
        else:
            st.error("Não foi possível iniciar o gateway de pagamento.")

    # --- BOTÃO FINAL DE EMISSÃO ---
    st.divider()
    if st.button("2. CONFIRMAR E EMITIR BILHETE FINAL", type="primary", use_container_width=True):
        if not nome or not email:
            st.error("Por favor, preencha os dados do passageiro acima e clique em 'Salvar'.")
        elif bloqueio_emissao:
            st.error("Verifique os dados do passaporte.")
        else:
            try:
                with st.spinner('Iniciando processo de emissão...'):
                    api_token = st.secrets["DUFFEL_TOKEN"]
                    headers = {
                        "Authorization": f"Bearer {api_token}", 
                        "Duffel-Version": "v2", 
                        "Content-Type": "application/json"
                    }
                    
                    # 1. Converte dados para a API
                    gen_code = "m" if genero_pax == "Masculino" else "f"
                    tit_code = "mr" if titulo_pax == "Sr." else ("mrs" if titulo_pax == "Sra." else "ms")
                    moeda_pg = "EUR"
                    valor_exato_duffel = v.get("valor_bruto_duffel")

                    # 2. PASSO NOVO: Criar a Intenção de Pagamento
                    res_intencao = criar_intencao_pagamento(float(valor_exato_duffel))
                    
                    if "errors" in res_intencao:
                        st.error(f"Erro na Intenção: {res_intencao['errors'][0]['message']}")
                    else:
                        pit_id = res_intencao["data"]["id"]
                        
                        # 3. CRIAR O PEDIDO
                        payload = {
                            "data": {
                                "type": "instant",
                                "selected_offers": [v['id_offer']],
                                "passengers": [{
                                    "id": v['pax_ids'][0],
                                    "title": tit_code,
                                    "given_name": nome,
                                    "family_name": apelido,
                                    "gender": gen_code,
                                    "born_on": str(dn),
                                    "email": email,
                                    "phone_number": "+351936797003"
                                }],
                                "payments": [{
                                    "type": "balance",
                                    "currency": "EUR",
                                    "amount": valor_exato_duffel
                                }],
                                "metadata": {
                                    "payment_intent_id": pit_id
                                }
                            }
                        }

                        res_ordem = requests.post("https://api.duffel.com/air/orders", headers=headers, json=payload)

                        if res_ordem.status_code == 201:
                            st.balloons()
                            st.success(f"Bilhete Emitido! PNR: {res_ordem.json()['data']['booking_reference']}")
                        else:
                            erro_msg = res_ordem.json()['errors'][0]['message']
                            st.error(f"❌ Erro na Emissão: {erro_msg}")
                            if "insufficient_balance" in str(res_ordem.json()):
                                st.info("O pagamento ainda não foi confirmado no cartão do cliente.")

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