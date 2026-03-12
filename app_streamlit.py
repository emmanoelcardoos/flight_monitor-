import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit.components.v1 as components
from email.mime.application import MIMEApplication
import stripe

def criar_checkout_stripe(valor_eur, nome_pax, email_pax, itinerario, offer_id):
    import stripe
    stripe.api_key = st.secrets.get("STRIPE_SECRET_KEY")
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {'name': f"Voo: {itinerario}"},
                    'unit_amount': int(float(valor_eur) * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            # AQUI ESTÁ O SEGREDO: Passamos o offer_id e o email de volta na URL
            success_url=f"https://flightmonitorec.streamlit.app/?pagamento=sucesso&offer_id={offer_id}&email={email_pax}",
            cancel_url="https://flightmonitorec.streamlit.app/?pagamento=cancelado",
            customer_email=email_pax,
        )
        return session.url
    except Exception as e:
        st.error(f"Erro na Stripe: {e}")
        return None
    
def enviar_email(destinatario, assunto, corpo_html):
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    try:
        # ATENÇÃO: Verifique se esses nomes batem com suas Secrets
        remetente = st.secrets["EMAIL_USER"]
        senha = st.secrets["EMAIL_PASSWORD"]
        
        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = destinatario
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo_html, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remetente, senha)
        server.sendmail(remetente, destinatario, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False


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

# --- RASTREADOR GLOBAL DE RETORNO DO STRIPE ---
if st.query_params.get("pagamento") in ["sucesso", "cancelado"]:
    st.session_state.pagina = "reserva"
    if st.query_params.get("pagamento") == "sucesso":
        st.session_state.pago = True

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
        "Brasília (BSB)", "Belo Horizonte (CNF)",
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

# --- PÁGINA 2: RESERVA ---
elif st.session_state.pagina == "reserva":
    # 1. Recuperamos o voo e tratamos se ele estiver vazio (evita a tela vermelha)
    v = st.session_state.get('voo_selecionado')
    
    # Se o usuário voltou da Stripe, forçamos a página a ser 'reserva'
    if st.query_params.get("pagamento"):
        st.session_state.pagina = "reserva"

    # Se não houver voo na memória (reset de sessão), avisamos amigavelmente
    if v is None:
        st.warning("⚠️ A sessão expirou ou o voo não foi encontrado.")
        if st.button("Voltar para a busca"):
            st.session_state.pagina = "busca"
            st.rerun()
        st.stop() # Interrompe o código aqui para não chegar na linha que dá erro

    # =========================================================
    # --- DAQUI PARA BAIXO SEGUE O SEU BLOCO DE AUTOMAÇÃO E CHECKOUT ---
    # =========================================================
    
        # ... (seu código de automação que já está lá)

    # =========================================================
    # --- BLOCO DE AUTOMATIZAÇÃO ---
    # =========================================================
    params = st.query_params
    if params.get("pagamento") == "sucesso":
        if "reserva_concluida" not in st.session_state:
            st.success("🎉 Pagamento Confirmado! Estamos a emitir o seu bilhete...")
            with st.spinner("A processar reserva e a enviar e-mail de confirmação..."):
                try:
                    # Busca dados salvos na sessão
                    pax_nome = st.session_state.get('pax_nome', 'Passageiro')
                    pax_email = st.session_state.get('pax_email')
                    itinerario = f"{v['Segmentos'][0]['de']} ➔ {v['Segmentos'][-1]['para']}"
                    
                    if pax_email:
                        corpo_email = f"<h1>Sua reserva está confirmada! ✈️</h1><p>Olá <b>{pax_nome}</b>, seu pagamento para o voo {itinerario} foi recebido!</p>"
                        enviar_email(pax_email, f"Reserva Confirmada - {itinerario} ✈️", corpo_email)
                        st.balloons()
                        st.session_state["reserva_concluida"] = True
                        st.session_state["pago"] = True
                except Exception as e:
                    st.error(f"Erro no automático: {e}")
    # =========================================================

    # Exibição dos dados do voo
    st.info(f"✈️ **Voo:** {v['Companhia']} | **Trecho:** {v['Segmentos'][0]['de']} ➔ {v['Segmentos'][-1]['para']}")
    st.metric(label="Valor a Pagar", value=f"{v['Moeda']} {v['Preço']:.2f}")
    st.title("🏁 Checkout")
    st.divider()

    # --- MORADA FISCAL (DE VOLTA!) ---
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
        titulo_pax = c_tit1.selectbox("Título", ["Sr.", "Sra.", "Srta."], key="pax_title_v16")
        
        c1, c2 = st.columns(2)
        # CORREÇÃO: Adicionado 'value' para recuperar os dados após o redirecionamento
        nome = c1.text_input("Nome", value=st.session_state.get('pax_nome', ''))
        apelido = c2.text_input("Apelido", value=st.session_state.get('pax_apelido', ''))
        email = st.text_input("E-mail", value=st.session_state.get('pax_email', ''))
        
        c3, c4 = st.columns(2)
        dn = c3.date_input("Data de Nascimento", value=datetime(1995, 1, 1))
        documento = c4.text_input("Documento")
        genero_pax = st.selectbox("Gênero", ["Masculino", "Feminino"], key="pax_gender_v16")

        if st.form_submit_button("1. Salvar Dados do Passageiro"):
            st.session_state['pax_nome'] = nome
            st.session_state['pax_apelido'] = apelido
            st.session_state['pax_email'] = email
            st.success("Dados salvos com sucesso!")

    # --- PAGAMENTO ---
    valor_exato_duffel = v.get("valor_bruto_duffel")
    if metodo == "Cartão de Crédito":
        if not st.session_state.get("pago", False):
            if st.button("2. GERAR LINK DE PAGAMENTO", use_container_width=True):
                if not st.session_state.get('pax_email'):
                    st.warning("⚠️ Salve os dados do passageiro (botão acima) antes de pagar.")
                else:
                    url = criar_checkout_stripe(valor_exato_duffel, st.session_state['pax_nome'], st.session_state['pax_email'], f"{v['Companhia']}")
                    if url:
                        st.link_button("👉 CLIQUE PARA PAGAR AGORA", url, type="primary", use_container_width=True)
        else:
            st.success("✅ Pagamento confirmado.")

    st.divider()
    # O seu botão original de emissão manual segue abaixo...
    # O seu botão original continua aqui
    
        # ... (restante do seu código de emissão Duffel)
    # --- BOTÃO FINAL DE EMISSÃO ---
    st.divider()
    if st.button("2. CONFIRMAR E EMITIR BILHETE", type="primary", use_container_width=True):
        if metodo == "Cartão de Crédito" and not st.session_state.get("pago", False):
            st.error("❌ Erro: O pagamento ainda não foi confirmado pela Stripe.")
        elif not nome or not email:
            st.error("❌ Erro: Preencha os dados do passageiro.")
        else:
            try:
                with st.spinner('Emitindo bilhete e gerando confirmação...'):
                    # Configurações API Duffel
                    api_token = st.secrets["DUFFEL_TOKEN"]
                    headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                    
                    valor_exato_duffel = v.get("valor_bruto_duffel")
                    gen_code = "m" if genero_pax == "Masculino" else "f"
                    tit_code = "mr" if titulo_pax == "Sr." else "mrs"

                    # Criar Ordem na Duffel
                    payload = {
                        "data": {
                            "type": "instant",
                            "selected_offers": [v['id_offer']],
                            "passengers": [{
                                "id": v['pax_ids'][0], "title": tit_code, "given_name": nome,
                                "family_name": apelido, "gender": gen_code, "born_on": str(dn),
                                "email": email, "phone_number": "+351936797003"
                            }],
                            "payments": [{"type": "balance", "currency": "EUR", "amount": valor_exato_duffel}],
                            "metadata": {"pagamento": "stripe_concluido"}
                        }
                    }

                    res_ordem = requests.post("https://api.duffel.com/air/orders", headers=headers, json=payload)

                    if res_ordem.status_code == 201:
                        dados_reserva = res_ordem.json()['data']
                        pnr = dados_reserva['booking_reference']
                        destino_f = v['Segmentos'][-1]['para']
                        logo_cia = f"https://images.duffel.com/airlines/{v['Segmentos'][0]['companhia_iata']}.png"

                        # --- MONTAGEM DO DESIGN DO EMAIL (PADRÃO DECOLAR) ---
                        html_design = f"""
                        <html>
                        <body style="font-family: Arial, sans-serif; color: #333; background-color: #f4f4f4; margin: 0; padding: 20px;">
                            <div style="max-width: 600px; margin: auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                                
                                <div style="background-color: #003580; padding: 40px 20px; text-align: center; color: white;">
                                    <div style="font-size: 50px; margin-bottom: 10px;">✈️</div>
                                    <h1 style="margin: 0; font-size: 24px;">Hey {nome}!</h1>
                                    <p style="font-size: 18px; opacity: 0.9;">O seu voo para {destino_f} foi emitido!</p>
                                </div>

                                <div style="padding: 20px; border-bottom: 2px solid #f4f4f4; display: flex; align-items: center;">
                                    <div style="flex-grow: 1;">
                                        <span style="color: #888; font-size: 12px; text-transform: uppercase; font-weight: bold;">Número da Reserva</span><br>
                                        <strong style="font-size: 28px; color: #003580; letter-spacing: 1px;">{pnr}</strong>
                                    </div>
                                    <img src="{logo_cia}" width="70" style="margin-left: 20px; border-radius: 5px;">
                                </div>

                                <div style="padding: 20px;">
                                    <h3 style="color: #003580; margin-bottom: 15px;">📍 Detalhes do Itinerário</h3>
                                    {"".join([f'''
                                    <div style="padding: 15px; border: 1px solid #eee; border-radius: 8px; margin-bottom: 10px; background-color: #fafafa;">
                                        <strong style="color: #333;">{s['companhia']} - Voo {s['voo']}</strong><br>
                                        <div style="margin-top: 8px; font-size: 15px;">
                                            <span style="color: #003580; font-weight: bold;">{s['de']}</span> ➔ <span style="color: #003580; font-weight: bold;">{s['para']}</span>
                                        </div>
                                        <div style="margin-top: 5px; font-size: 13px; color: #666;">
                                            📅 Partida: {s['saida']} | Chegada: {s['chegada']}
                                        </div>
                                    </div>
                                    ''' for s in v['Segmentos']])}
                                </div>

                                <div style="padding: 20px; background-color: #fcfcfc; border-top: 1px solid #eee;">
                                    <h3 style="margin-top: 0;">💰 Resumo do Pagamento</h3>
                                    <table width="100%" style="font-size: 15px;">
                                        <tr><td style="padding: 5px 0; color: #666;">Tarifa Aérea e Taxas</td><td align="right">EUR {valor_exato_duffel}</td></tr>
                                        <tr><td style="padding: 10px 0; font-size: 18px; font-weight: bold;">TOTAL</td><td align="right" style="font-size: 20px; font-weight: bold; color: #28a745;">EUR {valor_exato_duffel}</td></tr>
                                    </table>
                                    <p style="font-size: 12px; color: #999;">Forma de pagamento: Cartão de Crédito via Stripe</p>
                                </div>

                                <div style="padding: 30px 20px; text-align: center; background-color: #fff;">
                                    <a href="https://flightmonitorec.streamlit.app/" style="background-color: #003580; color: white; padding: 15px 25px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block; margin: 10px;">Acessar Área do Cliente</a>
                                    <br>
                                    <a href="https://www.google.com/search?q=site+oficial+{v['Segmentos'][0]['companhia'].replace(' ', '+')}" style="color: #003580; text-decoration: underline; font-size: 14px;">Ir para site oficial da Cia Aérea</a>
                                </div>

                                <div style="padding: 20px; background-color: #333; color: #ccc; font-size: 12px; text-align: center;">
                                    <strong>Informações Importantes:</strong><br>
                                    Chegue ao aeroporto com 3h de antecedência. <br>
                                    Apresente seu PNR {pnr} e passaporte no balcão da cia aérea.<br>
                                    © {datetime.now().year} Sua Agência de Viagens
                                </div>
                            </div>
                        </body>
                        </html>
                        """

                        enviar_email(destinatario=email, assunto=f"Eba! Sua viagem para {destino_f} está confirmada!", corpo_html=html_design)
                        
                        st.balloons()
                        st.success(f"Bilhete Emitido com Sucesso! PNR: {pnr}")
                    else:
                        st.error(f"Erro na Duffel: {res_ordem.json()['errors'][0]['message']}")

            except Exception as e:
                st.error(f"Erro técnico: {e}")

# --- PÁGINA 3: LOGIN ---
elif st.session_state.pagina == "login":

    st.title("🔑 Área do Cliente")

    with st.container(border=True):

        st.text_input("PNR")
        st.text_input("E-mail")

        if st.button("Consultar"):
            st.success("Localizando reserva...")