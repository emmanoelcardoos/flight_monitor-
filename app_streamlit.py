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
import gspread
from oauth2client.service_account import ServiceAccountCredentials


def buscar_reserva_por_pnr(email_cliente, pnr_cliente):
    planilha = conectar_sheets()
    if planilha:
        try:
            aba = planilha.worksheet("Reservas_Confirmadas")
            dados = aba.get_all_values() 
            if len(dados) <= 1:
                return None
            for linha in dados[1:]:
                if len(linha) < 2:
                    continue
                email_planilha = str(linha[0]).strip().lower()
                pnr_planilha = str(linha[1]).strip().upper()
                if email_planilha == email_cliente.strip().lower() and \
                   pnr_planilha == pnr_cliente.strip().upper():
                    return {
                        "Email": linha[0],
                        "PNR": linha[1],
                        "Passageiro": linha[2] if len(linha) > 2 else "Passageiro",
                        "Data": linha[3] if len(linha) > 3 else "",
                        "Itinerário": linha[4] if len(linha) > 4 else "",
                        "Valor": linha[5] if len(linha) > 5 else "€ 0.00",
                        "Status": linha[6] if len(linha) > 6 else "Confirmado",
                        "PDF": linha[7] if len(linha) > 7 else "" 
                    }
            return None
        except Exception as e:
            st.error(f"Erro ao buscar na base de dados: {e}")
            return None

def conectar_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gspread"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("Alertas_Flight_Monitor")
    except Exception as e:
        st.error(f"Erro ao conectar ao Google Sheets: {e}")
        return None

def salvar_reserva_sheets(nome_completo, email, pnr, itinerario, valor, link_pdf=""):
    planilha = conectar_sheets()
    if planilha:
        try:
            aba = planilha.worksheet("Reservas_Confirmadas")
            data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
            aba.append_row([email, pnr, nome_completo, data_hora, itinerario, valor, "Emitido", link_pdf])
            return True
        except Exception as e:
            st.error(f"Erro ao gravar no Sheets: {e}")
            return False

def salvar_alerta_preco(email, itinerario, origem, destino, data_ida, preco_inicial, moeda):
    planilha = conectar_sheets()
    if planilha:
        try:
            aba = planilha.get_worksheet(0) 
            nova_linha = [email, itinerario, origem, destino, str(data_ida), "", 1, 0, 0, preco_inicial, moeda]
            aba.append_row(nova_linha)
            return True
        except Exception as e:
            st.error(f"Erro ao gravar: {e}")
            return False

def criar_checkout_stripe(valor_eur, nome_pax, email_pax, itinerario, offer_id):
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
            success_url=f"https://flightmonitorec.streamlit.app/?pagamento=sucesso&email={email_pax}&nome={nome_pax}",
            cancel_url="https://flightmonitorec.streamlit.app/?pagamento=cancelado",
            customer_email=email_pax,
        )
        return session.url
    except Exception as e:
        st.error(f"Erro na Stripe: {e}")
        return None
    
def enviar_email(destinatario, assunto, corpo_html):
    try:
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

COMISSAO_PERCENTUAL = 0.12 
WHATSAPP_SUPORTE = "351936797003" 

def get_cotacao_ao_vivo():
    try:
        res = requests.get("https://economia.awesomeapi.com.br/last/EUR-BRL")
        if res.status_code == 200:
            return float(res.json()["EURBRL"]["bid"])
        return 6.02
    except:
        return 6.02

st.set_page_config(page_title="Flight Monitor GDS", page_icon="✈️", layout="wide")
if st.query_params.get("pagamento") == "sucesso":
    st.session_state.pagina = "sucesso"

def criar_intencao_pagamento(valor_eur):
    try:
        api_token = st.secrets["DUFFEL_TOKEN"]
        headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
        payload = {"data": {"amount": f"{valor_eur:.2f}", "currency": "EUR"}}
        res = requests.post("https://api.duffel.com/payments/payment_intents", headers=headers, json=payload)
        return res.json()
    except Exception as e:
        return {"errors": [{"message": str(e)}]}

if 'pagina' not in st.session_state:
    st.session_state.pagina = "busca"

# --- RASTREADOR DE RETORNO DO STRIPE (TOPO DO CÓDIGO) ---
if st.query_params.get("pagamento") == "sucesso":
    st.session_state.pagina = "sucesso"

if 'voo_selecionado' not in st.session_state:
    st.session_state.voo_selecionado = None
if 'busca_feita' not in st.session_state:
    st.session_state.busca_feita = False
if 'resultados_voos' not in st.session_state:
    st.session_state.resultados_voos = []

with st.sidebar:
    st.title("📌 Flight Monitor")
    if st.button("🔍 Procurar Voos"):
        st.session_state.pagina = "busca"
    if st.button("👤 Área do Cliente"):
        st.session_state.pagina = "login"
    st.divider()
    st.markdown(f"**Suporte:** [WhatsApp](https://wa.me/{WHATSAPP_SUPORTE})")

if st.session_state.pagina == "busca":
    if st.button("Limpar Cache e Nova Busca"):
        st.session_state.resultados_voos = []
        st.session_state.busca_feita = False
        st.rerun()

    st.title("✈️ Flight Monitor Trips")
    paises_br = ["BR", "PT", "FR", "US", "ES", "GB"]
    opcoes_cidades = ["São Paulo (GRU)", "São Paulo (CGH)", "Rio de Janeiro (GIG)", "Rio de Janeiro (SDU)", "Brasília (BSB)", "Belo Horizonte (CNF)", "Salvador (SSA)", "Recife (REC)", "Fortaleza (FOR)", "Natal (NAT)", "Maceió (MCZ)", "João Pessoa (JPA)", "Aracaju (AJU)", "Porto Alegre (POA)", "Curitiba (CWB)", "Florianópolis (FLN)", "Cuiabá (CGB)", "Campo Grande (CGR)", "Goiânia (GYN)", "Belém (BEL)", "Manaus (MAO)", "Macapá (MCP)", "Boa Vista (BVB)", "Porto Velho (PVH)", "Rio Branco (RBR)", "Palmas (PMW)", "São Luís (SLZ)", "Teresina (THE)", "Vitória (VIX)", "Campinas (VCP)", "Foz do Iguaçu (IGU)", "Navegantes (NVT)", "Joinville (JOI)", "Ilhéus (IOS)", "Porto Seguro (BPS)", "Chapecó (XAP)", "Uberlândia (UDI)", "Montes Claros (MOC)", "Imperatriz (IMP)", "Marabá (MAB)", "Santarém (STM)", "Lisboa (LIS)", "Porto (OPO)", "Faro (FAO)", "Funchal (FNC)", "Ponta Delgada (PDL)", "Madrid (MAD)", "Barcelona (BCN)", "Valência (VLC)", "Sevilha (SVQ)", "Paris (CDG)", "Roma (FCO)", "Milão (MXP)", "Frankfurt (FRA)", "Londres (LHR)"]

    tipo_v = st.radio("Tipo de Viagem", ["Apenas Ida", "Ida e Volta"], horizontal=True, key="tipo_viagem_radio")
    with st.form("busca_v17"):
        col1, col2 = st.columns(2)
        origem = col1.selectbox("Origem", opcoes_cidades)
        destino = col2.selectbox("Destino", opcoes_cidades)
        col3, col4 = st.columns(2)
        data_ida = col3.date_input("Data de Partida", value=datetime.today() + timedelta(days=7))
        data_volta = None
        if tipo_v == "Ida e Volta":
            data_volta = col4.date_input("Data de Retorno", value=datetime.today() + timedelta(days=14), key="data_volta_input")
        else:
            col4.info("Viagem só de ida")
        moeda_visu = col1.selectbox("Exibir preços em:", ["Real (R$)", "Euro (€)"])
        btn = st.form_submit_button("PESQUISAR VOOS", use_container_width=True)

    if btn:
        st.session_state.busca_feita = True
        try:
            with st.spinner('Em busca dos melhores voos!'):
                cotacao_atual = get_cotacao_ao_vivo()
                api_token = st.secrets["DUFFEL_TOKEN"]
                headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                iata_o, iata_d = origem[-4:-1], destino[-4:-1]
                fatias = [{"origin": iata_o, "destination": iata_d, "departure_date": str(data_ida)}]
                if tipo_v == "Ida e Volta" and data_volta:
                    fatias.append({"origin": iata_d, "destination": iata_o, "departure_date": str(data_volta)})
                is_intl = not (iata_o in paises_br and iata_d in paises_br)
                payload = {"data": {"slices": fatias, "passengers": [{"type": "adult"}], "requested_currencies": ["EUR"]}}
                res = requests.post("https://api.duffel.com/air/offer_requests", headers=headers, json=payload)
                if res.status_code == 201:
                    offers = res.json()["data"].get("offers", [])
                    st.session_state.resultados_voos = []
                    for o in offers[:15]:
                        fatias_voo = []
                        for slice_data in o["slices"]:
                            segs_fatia = []
                            for seg in slice_data["segments"]:
                                segs_fatia.append({
                                    "de": seg["origin"]["iata_code"], "para": seg["destination"]["iata_code"],
                                    "partida": seg["departing_at"].split("T")[1][:5], "chegada": seg["arriving_at"].split("T")[1][:5],
                                    "cia": seg["marketing_carrier"]["name"], "aviao": seg["aircraft"]["name"] if seg["aircraft"] else "N/D"
                                })
                            fatias_voo.append(segs_fatia)
                        
                        valor_eur = float(o["total_amount"])
                        v_final = valor_eur * cotacao_atual * (1.12) if "Real" in moeda_visu else valor_eur * (1.12)
                        st.session_state.resultados_voos.append({
                            "id_offer": o["id"], "Companhia": o["owner"]["name"], "Preço": v_final,
                            "Moeda": "R$" if "Real" in moeda_visu else "€", "Trechos": fatias_voo,
                            "valor_bruto_duffel": o["total_amount"], "pax_ids": [p["id"] for p in res.json()["data"]["passengers"]]
                        })
                    st.rerun()
        except Exception as e:
            st.error(f"Erro: {e}")

    if st.session_state.busca_feita and st.session_state.resultados_voos:
        st.markdown(f"### 🔍 Encontramos {len(st.session_state.resultados_voos)} opções")
        st.session_state.resultados_voos.sort(key=lambda x: x['Preço'])
        for idx, v in enumerate(st.session_state.resultados_voos):
            trechos = v.get('Trechos')
            if not trechos: continue
            with st.container(border=True):
                col_logo, col_info, col_preco = st.columns([1, 3, 1.5])
                col_logo.subheader(v['Companhia'])
                with col_info:
                    ida = trechos[0]
                    st.markdown(f"**🛫 Ida:** {ida[0]['de']} ({ida[0]['partida']}) ➔ {ida[-1]['para']} ({ida[-1]['chegada']})")
                    if len(trechos) > 1:
                        volta = trechos[1]
                        st.markdown(f"**🛬 Volta:** {volta[0]['de']} ({volta[0]['partida']}) ➔ {volta[-1]['para']} ({volta[-1]['chegada']})")
                    with st.expander("Ver escalas e aeronaves"):
                        for i, t in enumerate(trechos):
                            st.caption(f"TRECHO {i+1}")
                            for s in t: st.write(f"✈️ {s['cia']} | {s['de']} ➔ {s['para']} ({s['aviao']})")
                with col_preco:
                    st.subheader(f"{v['Moeda']} {v['Preço']:.2f}")
                    if st.button("SELECIONAR", key=f"sel_{idx}", use_container_width=True, type="primary"):
                        st.session_state.voo_selecionado, st.session_state.pagina = v, "reserva"
                        st.rerun()

                        # --- BLOCO DE ALERTA DE PREÇO (REINTEGRADO) ---
        st.divider()
        st.subheader("🔔 Não Encontrou o Preço que Querias?")
        st.write("Inscreva-se nos nossos alertas e receba notificações no teu email sempre que o preço do teu voo baixar!")
        
        with st.expander("Criar Alerta de Preço"):
            col_al1, col_al2 = st.columns([2, 1])
            email_alerta = col_al1.text_input("Seu e-mail para o alerta", key="email_alerta_input_final")
            
            # Pegamos o menor preço da busca atual (o primeiro da lista ordenada)
            menor_preco = st.session_state.resultados_voos[0]['Preço']
            moeda_txt = st.session_state.resultados_voos[0]['Moeda']
            
            if st.button("Ativar Alerta de Preço", use_container_width=True):
                if email_alerta:
                    itinerario_txt = f"{origem} para {destino}"
                    sucesso = salvar_alerta_preco(
                        email_alerta, 
                        itinerario_txt, 
                        origem, 
                        destino, 
                        data_ida, 
                        menor_preco, 
                        moeda_txt
                    )
                    if sucesso:
                        st.success(f"✅ Alerta Guardado! Avisaremos em {email_alerta}")
                    else:
                        st.error("Erro ao gravar na folha de Alertas.")



elif st.session_state.pagina == "login":
    st.title("✈️ Área do Passageiro")
    email_l = st.text_input("E-mail")
    pnr_l = st.text_input("PNR")
    if st.button("Buscar"):
        res = buscar_reserva_por_pnr(email_l, pnr_l)
        if res: st.write(res)
        else: st.error("Não encontrado")


# --- PÁGINA 2: RESERVA ---
elif st.session_state.pagina == "reserva":
    v = st.session_state.get('voo_selecionado')
    if not v: 
        st.session_state.pagina = "busca"
        st.rerun()

    st.title("🏁 Finalizar Reserva")
    
    # --- CORREÇÃO DO ERRO DE SEGMENTOS ---
    trechos = v.get('Trechos', [])
    if trechos:
        # Pegamos a ida (primeiro trecho) para mostrar o resumo
        ida = trechos[0]
        origem_p = ida[0]['de']
        destino_p = ida[-1]['para']
        st.info(f"✈️ **Voo:** {v.get('Companhia')} | **Resumo:** {origem_p} ➔ {destino_p}")
    else:
        # Caso o voo tenha vindo do formato antigo por cache
        st.info(f"✈️ **Voo:** {v.get('Companhia')}")
    
    st.metric(label="Valor Total a Pagar", value=f"{v['Moeda']} {v['Preço']:.2f}")
    
    col_dados, col_resumo = st.columns([2, 1])

    with col_dados:
        # --- DADOS DA MORADA FISCAL ---
        st.subheader("🏠 Morada Fiscal")
        rua = st.text_input("Rua/Logradouro")
        c_bairro, c_cid = st.columns(2)
        bairro = c_bairro.text_input("Bairro")
        cidade_f = c_cid.text_input("Cidade")
        c_cep, c_est = st.columns(2)
        cep_f = c_cep.text_input("CEP")
        estado_f = c_est.text_input("Estado (UF)")

        st.divider()

        # --- DADOS DO PASSAGEIRO ---
        st.subheader("👤 Detalhes do Passageiro")
        with st.form("form_pax_v21"):
            c_tit, c_gen = st.columns(2)
            titulo_input = c_tit.selectbox("Título", ["Senhor", "Senhora"])
            genero_input = c_gen.selectbox("Gênero", ["Masculino", "Feminino"])
            
            c1, c2 = st.columns(2)
            nome_pax = c1.text_input("Nome", value=st.session_state.get('pax_nome', ''))
            apelido_pax = c2.text_input("Apelido / Sobrenome", value=st.session_state.get('pax_apelido', ''))
            
            email_pax = st.text_input("E-mail", value=st.session_state.get('pax_email', ''))
            
            c3, c4 = st.columns(2)
            documento_id = c3.text_input("CPF / Cartão de Cidadão")
            
            # --- CORREÇÃO DO CALENDÁRIO (1920 até Hoje) ---
            nasc_pax = c4.date_input(
                "Data de Nascimento", 
                value=datetime(1995, 1, 1),
                min_value=datetime(1920, 1, 1),
                max_value=datetime.now()
            )
            
            # Restante do código (Passaporte e Botão Salvar)...
            
            # CORREÇÃO DO CALENDÁRIO: min_value e max_value expandidos
            nasc_pax = c4.date_input(
                "Data de Nascimento", 
                value=datetime(1995, 1, 1),
                min_value=datetime(1920, 1, 1),
                max_value=datetime.today()
            )
            
            precisa_passaporte = v.get("Internacional", False)
            if precisa_passaporte:
                st.warning("⚠️ Voo Internacional: Passaporte Obrigatório")
                cp1, cp2 = st.columns(2)
                passaporte = cp1.text_input("Número do Passaporte")
                val_passaporte = cp2.date_input("Validade", value=datetime.today() + timedelta(days=365))
            else:
                passaporte, val_passaporte = "N/A", None

            if st.form_submit_button("✅ VALIDAR DADOS"):
                st.session_state['pax_titulo'] = "mr" if titulo_input == "Senhor" else "mrs"
                st.session_state['pax_genero'] = "m" if genero_input == "Masculino" else "f"
                st.session_state['pax_nome'] = nome_pax
                st.session_state['pax_email'] = email_pax
                st.success("Dados validados!")

    with col_resumo:
        st.subheader("💳 Pagamento")
        if st.session_state.get('pax_email'):
            url_checkout = criar_checkout_stripe(v['valor_bruto_duffel'], nome_pax, email_pax, v['Companhia'], v['id_offer'])
            if url_checkout:
                st.link_button("🚀 PAGAR AGORA", url_checkout, type="primary", use_container_width=True)
        else:
            st.warning("Valide os dados ao lado.")

    if st.button("⬅️ Voltar"):
        st.session_state.pagina = "busca"
        st.rerun()
    # 3. PROTEÇÃO CONTRA TELA VERMELHA (NoneType)
    if v is None:
        v = {
            "Companhia": "Voo em Processamento",
            "Segmentos": [{"de": "---", "para": "---"}],
            "Moeda": "EUR",
            "Preço": 0.00
        }

    # 4. EXIBIÇÃO DOS DADOS DO VOO
    st.info(f"✈️ **Voo:** {v['Companhia']} | **Trecho:** {v['Segmentos'][0]['de']} ➔ {v['Segmentos'][-1]['para']}")
    st.metric(label="Valor a Pagar", value=f"{v['Moeda']} {v['Preço']:.2f}")
    st.title("🏁 Checkout")
    st.divider()

    # 5. MORADA FISCAL (Mantido original)
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

    # 6. FORMULÁRIO DE DADOS DO PASSAGEIRO
    with st.form("form_final_v16"):
        st.subheader("👤 Dados do Passageiro")
        c_tit1, c_tit2 = st.columns([1, 3])
        titulo_pax = c_tit1.selectbox("Título", ["Sr.", "Sra.", "Srta."], key="pax_title_v16")
        
        c1, c2 = st.columns(2)
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

    # 7. SEÇÃO DE PAGAMENTO
    valor_exato_duffel = v.get("valor_bruto_duffel")
    if metodo == "Cartão de Crédito":
        if not st.session_state.get("pago", False):
            if st.button("2. GERAR LINK DE PAGAMENTO", use_container_width=True):
                if not st.session_state.get('pax_email'):
                    st.warning("⚠️ Salve os dados do passageiro acima primeiro.")
                else:
                    url = criar_checkout_stripe(
                        valor_exato_duffel, 
                        st.session_state['pax_nome'], 
                        st.session_state['pax_email'], 
                        v['Companhia'],
                        v.get('id_offer', 'N/A')
                    )
                    if url:
                        st.link_button("👉 CLIQUE PARA PAGAR AGORA", url, type="primary", use_container_width=True)
        else:
            st.success("✅ Pagamento já confirmado.")

    # 8. BOTÃO FINAL DE EMISSÃO (E-MAIL 2)
    st.divider()
    if st.button("3. CONFIRMAR E EMITIR BILHETE FINAL", type="primary", use_container_width=True):
        if metodo == "Cartão de Crédito" and not st.session_state.get("pago", False):
            st.error("❌ Erro: O pagamento ainda não foi confirmado pela Stripe.")
        elif not nome or not email:
            st.error("❌ Erro: Preencha os dados do passageiro.")
        else:
            try:
                with st.spinner('Emitindo bilhete e gerando e-mail final...'):
                    # Lógica de emissão Duffel (Payload)
                    api_token = st.secrets["DUFFEL_TOKEN"]
                    headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                    
                    gen_code = "m" if genero_pax == "Masculino" else "f"
                    tit_code = "mr" if titulo_pax == "Sr." else "mrs"

                    payload = {
                        "data": {
                            "type": "instant",
                            "selected_offers": [v['id_offer']],
                            "passengers": [{
                                "id": v['pax_ids'][0], "title": tit_code, "given_name": nome,
                                "family_name": apelido, "gender": gen_code, "born_on": str(dn),
                                "email": email, "phone_number": "+351936797003"
                            }],
                            "payments": [{"type": "balance", "currency": "EUR", "amount": valor_exato_duffel}]
                        }
                    }

                    res_ordem = requests.post("https://api.duffel.com/air/orders", headers=headers, json=payload)

                    if res_ordem.status_code == 201:
                        dados_reserva = res_ordem.json()['data']
                        pnr = res_ordem.json()['data']['booking_reference']
                        itinerario_venda = f"{v['Segmentos'][0]['de']} ➔ {v['Segmentos'][-1]['para']}"
                        salvar_reserva_sheets(f"{nome} {apelido}", email, pnr, itinerario_venda, v['Preço'])
                        nome_completo = f"{nome} {apelido}"
                        valor_venda = f"€ {v['Preço']:.2f}"

                        documentos = dados_reserva.get('documents', [])
                        link_pdf_oficial = documentos[0]['url'] if documentos else ""

                        nome_completo = f"{nome} {apelido}"
                        itinerario_venda = f"{v['Segmentos'][0]['de']} ➔ {v['Segmentos'][-1]['para']}"
                        url_bilhete_individual = documentos[0]['url'] if documentos else ""

                        # CHAMADA ATUALIZADA COM O LINK DO PDF
                        salvar_reserva_sheets(
                            f"{nome} {apelido}", 
                            email, 
                            pnr_gerado, 
                            itinerario_venda, 
                            f"€ {v['Preço']:.2f}", 
                            url_bilhete_individual # <--- Link único guardado aqui
                        )


                        try:
                            sucesso_sheets = salvar_reserva_sheets(
                                nome_completo, 
                                email, 
                                pnr, 
                                itinerario_venda, 
                                valor_venda
                            )
                            if sucesso_sheets:
                                st.toast("Dados guardados na base de dados! ✅")
                        except Exception as e:      
                            st.error(f"Erro ao registar na base de dados: {e}")
                        # 3. Segue para o envio do e-mail com o bilhete
                        enviar_email(email, f"Seu bilhete foi emitido! PNR: {pnr}", html_design)


                        # Design do E-mail 2 (O seu design estilo Decolar que já estava no código)
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

                        # --- DISPARO DO E-MAIL FINAL (O BILHETE) ---
                        enviar_email(
                            destinatario=email, 
                            assunto=f"Eba! Sua viagem para {destino_f} está confirmada! PNR: {pnr}", 
                            corpo_html=html_design
                        )
                        
                        st.success(f"✅ Bilhete Emitido com Sucesso! PNR: {pnr}")
                        
            
                    else:
                        st.error(f"Erro na Duffel: {res_ordem.json()['errors'][0]['message']}")
            except Exception as e:
                st.error(f"Erro técnico na emissão: {e}")

# --- PÁGINA 3: LOGIN (ÁREA DO PASSAGEIRO) ---
elif st.session_state.pagina == "login":
    st.title("✈️ Área do Passageiro")
    st.subheader("Aceda à sua reserva e itinerários")

    # Painel de Login
    with st.container(border=True):
        col_l1, col_l2 = st.columns(2)
        email_input = col_l1.text_input("E-mail utilizado na compra", key="login_email")
        pnr_input = col_l2.text_input("Código da Reserva (PNR)", key="login_pnr")
        
        if st.button("Procurar Minha Viagem", use_container_width=True, type="primary"):
            with st.spinner("A consultar base de dados..."):
                reserva_encontrada = buscar_reserva_por_pnr(email_input, pnr_input)
                
                if reserva_encontrada:
                    st.session_state.reserva_ativa = reserva_encontrada
                    st.success("Reserva localizada com sucesso!")
                else:
                    st.session_state.reserva_ativa = None # Limpa se não encontrar
                    st.error("Não encontramos nenhuma reserva com estes dados.")

    # Se o cliente estiver "logado" (reserva encontrada)
    if st.session_state.get("reserva_ativa"):
        res = st.session_state.reserva_ativa
        st.divider()
        
        st.markdown(f"### Olá, {res['Passageiro']}! 👋")
        
        # Dashboard de Informações
        c1, c2, c3 = st.columns(3)
        c1.metric("Localizador (PNR)", res['PNR'])
        c2.metric("Status", res['Status'])
        # Usamos .get para evitar erro caso a chave 'Valor' mude na busca
        c3.metric("Total Pago", res.get('Valor', '€ 0.00'))

        st.info(f"📍 **Itinerário:** {res.get('Itinerário', 'Consultar Bilhete')}")

        # Ações do Cliente
        st.subheader("🛠️ Gestão da Reserva")
        col_btn1, col_btn2, col_btn3 = st.columns(3)

        with col_btn1:
            # Botão Único de PDF - Verifica se o link existe na Coluna H
            url_pdf = res.get('PDF', "").strip()
            if url_pdf and url_pdf.startswith("http"):
                st.link_button("📄 Baixar Itinerário (PDF)", url_pdf, use_container_width=True)
            else:
                st.button("📄 PDF em Processamento", disabled=True, use_container_width=True)
        
        with col_btn2:
            st.link_button("🔄 Alterar Dados", f"https://wa.me/{WHATSAPP_SUPORTE}", use_container_width=True)
        
        with col_btn3:
            if st.button("❌ Cancelar Viagem", type="secondary", use_container_width=True):
                st.warning("Pedidos de cancelamento são analisados pelo suporte em até 24h.")

# --- PÁGINA 4: SUCESSO PÓS-PAGAMENTO ---
# --- PÁGINA 4: SUCESSO PÓS-PAGAMENTO (FIM DO ARQUIVO) ---
elif st.session_state.pagina == "sucesso":
    st.balloons()
    st.success("### 🎉 Pagamento Confirmado com Sucesso!")
    
    # Captura os dados que a Stripe envia de volta na URL
    nome_pax = st.query_params.get('nome', 'Passageiro')
    email_pax = st.query_params.get('email', 'seu e-mail')
    
    with st.container(border=True):
        st.markdown(f"""
        **Olá {nome_pax},**
        
        Recebemos o seu pagamento. A nossa equipa e os sistemas da companhia aérea estão a processar a emissão do seu bilhete definitivo.
        
        ✈️ **O que verificar agora?**
        1. Enviámos um e-mail de confirmação de pagamento para **{email_pax}**.
        2. Em instantes, você receberá um **segundo e-mail** contendo o seu código de reserva (PNR) e os detalhes do embarque.
        3. Caso tenha dúvidas, utilize o botão de suporte abaixo.
        """)
        
        st.link_button("💬 Falar com Suporte (WhatsApp)", f"https://wa.me/{WHATSAPP_SUPORTE}", use_container_width=True)
    
    st.divider()
    if st.button("Voltar ao Início", use_container_width=True):
        st.session_state.pagina = "busca"
        st.session_state.busca_feita = False
        st.session_state.resultados_voos = []
        st.rerun()