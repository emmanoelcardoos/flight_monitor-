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
            # Pegamos todos os valores brutos para evitar erro de cabeçalho
            dados = aba.get_all_values() 
            
            # Se a planilha tiver apenas o cabeçalho ou estiver vazia
            if len(dados) <= 1:
                return None
                
            # Percorremos as linhas ignorando o cabeçalho (linha 1)
            for linha in dados[1:]:
                # Ordem esperada na planilha:
                # A=Email, B=PNR, C=Passageiro, D=Data, E=Itinerário, F=Valor, G=Status, H=PDF
                
                # Verificamos se a linha tem pelo menos Email e PNR antes de comparar
                if len(linha) < 2:
                    continue
                    
                email_planilha = str(linha[0]).strip().lower()
                pnr_planilha = str(linha[1]).strip().upper()

                if email_planilha == email_cliente.strip().lower() and \
                   pnr_planilha == pnr_cliente.strip().upper():
                    
                    # Retornamos o dicionário com todos os campos, incluindo o PDF (índice 7)
                    return {
                        "Email": linha[0],
                        "PNR": linha[1],
                        "Passageiro": linha[2] if len(linha) > 2 else "Passageiro",
                        "Data": linha[3] if len(linha) > 3 else "",
                        "Itinerário": linha[4] if len(linha) > 4 else "",
                        "Valor": linha[5] if len(linha) > 5 else "€ 0.00",
                        "Status": linha[6] if len(linha) > 6 else "Confirmado",
                        "PDF": linha[7] if len(linha) > 7 else "" # Coluna H
                    }
            return None
        except Exception as e:
            st.error(f"Erro ao buscar na base de dados: {e}")
            return None

def conectar_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Certifica-te que 'gspread' está configurado nos Secrets do Streamlit
        creds_dict = st.secrets["gspread"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        # USA O NOME EXATO DA TUA FOLHA
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
            
            # Adicionamos o link_pdf na última coluna (Coluna H)
            aba.append_row([
                email,           # A
                pnr,             # B
                nome_completo,   # C
                data_hora,       # D
                itinerario,      # E
                valor,           # F
                "Emitido",       # G
                link_pdf         # H (NOVA COLUNA)
            ])
            return True
        except Exception as e:
            st.error(f"Erro ao gravar no Sheets: {e}")
            return False

def salvar_alerta_preco(email, itinerario, origem, destino, data_ida, preco_inicial, moeda):
    planilha = conectar_sheets()
    if planilha:
        try:
            # Pega a primeira aba (aba 1)
            aba = planilha.get_worksheet(0) 
            # Segue a ordem das colunas da sua foto: 
            # email, itinerario, origem, destino, data, data_volta, adultos, criancas, bebes, preco_inicial, moeda
            nova_linha = [email, itinerario, origem, destino, str(data_ida), "", 1, 0, 0, preco_inicial, moeda]
            aba.append_row(nova_linha)
            return True
        except Exception as e:
            st.error(f"Erro ao gravar: {e}")
            return False

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
            # AQUI: Adicionamos o e-mail e o nome na URL de retorno
            success_url=f"https://flightmonitorec.streamlit.app/?pagamento=sucesso&email={email_pax}&nome={nome_pax}",
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

if 'busca_feita' not in st.session_state:
    st.session_state.busca_feita = False

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

    paises_br = ["BR", "PT", "FR", "US", "ES", "GB"]

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

    tipo_v= st.radio("Tipo de Viagem", ["Apenas Ida", "Ida e Volta"], horizontal=True, key="tipo_viagem_radio")
    
    with st.form("busca_v17"):
        # 1. Escolha do Tipo de Viagem

        col1, col2 = st.columns(2)
        origem = col1.selectbox("Origem", opcoes_cidades)
        destino = col2.selectbox("Destino", opcoes_cidades)

        col3, col4 = st.columns(2)
        data_ida = col3.date_input("Data de Partida", value=datetime.today() + timedelta(days=7))
    
    # 2. Data de Volta condicional
        data_volta = None
        if tipo_v == "Ida e Volta":
            data_volta = col4.date_input("Data de Retorno", value=datetime.today() + timedelta(days=14), key="data_volta_input" )
        else:
            col4.info("Viagem só de ida")
            data_volta = None

        moeda_visu = col1.selectbox("Exibir preços em:", ["Real (R$)", "Euro (€)"])
        btn = st.form_submit_button("PESQUISAR VOOS", use_container_width=True)


    if btn:
        st.session_state.busca_feita = True

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

                fatias = [{
                    "origin": iata_o,
                    "destination": iata_d,
                    "departure_date": str(data_ida)
                }]

                if tipo_v == "Ida e Volta" and data_volta:
                    fatias.append({
                        "origin": iata_d,
                        "destination": iata_o,
                        "departure_date": str(data_volta)
                    })

                is_intl = not (iata_o in paises_br and iata_d in paises_br)


                payload = {
                    "data": {
                        "slices": fatias, # Agora usa a lista dinâmica
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

                    for o in offers[:15]:

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

    # --- EXIBIÇÃO DOS RESULTADOS (DENTRO DA PÁGINA 1) ---
if st.session_state.resultados_voos:
    st.markdown(f"### 🔍 Encontramos {len(st.session_state.resultados_voos)} opções para você")
    
    # Ordenar por preço para garantir o melhor negócio no topo
    st.session_state.resultados_voos.sort(key=lambda x: x['Preço'])

    for idx, v in enumerate(st.session_state.resultados_voos):
        with st.container(border=True):
            col_logo, col_info, col_preco = st.columns([1, 3, 1.5])

            # Coluna 1: Companhia
            col_logo.subheader(v['Companhia'])
            
            # Coluna 2: Resumo dos Horários
            with col_info:
                # Ida
                ida = v['Trechos'][0]
                st.markdown(f"**🛫 Ida:** {ida[0]['de']} ({ida[0]['partida']}) ➔ {ida[-1]['para']} ({ida[-1]['chegada']})")
                
                # Volta (se houver)
                if len(v['Trechos']) > 1:
                    volta = v['Trechos'][1]
                    st.markdown(f"**🛬 Volta:** {volta[0]['de']} ({volta[0]['partida']}) ➔ {volta[-1]['para']} ({volta[-1]['chegada']})")
                
                # Detalhes escondidos em um Expander
                with st.expander("Ver detalhes das escalas e aeronaves"):
                    st.write("---")
                    st.caption("TRECHO DE IDA")
                    for s in ida:
                        st.write(f"✈️ {s['cia']} | {s['de']} ➔ {s['para']} ({s['aviao']})")
                    
                    if len(v['Trechos']) > 1:
                        st.write("---")
                        st.caption("TRECHO DE VOLTA")
                        for s in v['Trechos'][1]:
                            st.write(f"✈️ {s['cia']} | {s['de']} ➔ {s['para']} ({s['aviao']})")

            # Coluna 3: Preço e Seleção
            with col_preco:
                st.subheader(f"{v['Moeda']} {v['Preço']:.2f}")
                if st.button("SELECIONAR", key=f"sel_{v['id_offer']}_{idx}", use_container_width=True, type="primary"):
                    st.session_state.voo_selecionado = v
                    st.session_state.pagina = "reserva"
                    st.rerun()
        # --- BLOCO DE ALERTA DE PREÇO NA PÁGINA 1 ---
        st.divider()
        st.subheader("🔔 Não Encontrou o Preço que Querias?\n Inscreva-se nos nossos alertas e receba notificaçoes no teu email sempre que o preco do teu voo baixar!")
        with st.expander("Criar Alerta de Preço"):
            col_al1, col_al2 = st.columns([2, 1])
            email_alerta = col_al1.text_input("Seu e-mail para o alerta", key="email_alerta_input")
            
            # Pegamos o menor preço da busca atual
            menor_preco = st.session_state.resultados_voos[0]['Preço']
            moeda_txt = st.session_state.resultados_voos[0]['Moeda']
            
            if st.button("Ativar Alerta de Preço", use_container_width=True):
                if email_alerta:
                    itinerario_txt = f"{origem} para {destino}"
                    # Chamada da função com os dados da sua planilha
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
                        st.success(f"✅ Alerta Guardado! Avisaremos quando o preço do seu voo baixar para o seguinte email: {email_alerta}")
                    else:
                        st.error("Erro ao gravar na folha. Verifique as permissões.")
        # =========================================================

    elif st.session_state.get('busca_feita'): 
        st.warning("Nenhum voo encontrado para estes critérios.")
        
        
        


# --- PÁGINA 2: RESERVA ---
elif st.session_state.pagina == "reserva":
    v = st.session_state.get('voo_selecionado')
    params = st.query_params

    # 1. RECUPERAÇÃO DE DADOS DA URL (Evita o reset da sessão)
    status_pagamento = params.get("pagamento")
    email_url = params.get("email")
    nome_url = params.get("nome")

    # 2. SEÇÃO DE E-MAIL 1: IMEDIATO PÓS-PAGAMENTO
    if status_pagamento == "sucesso" and "email_1_enviado" not in st.session_state:
        destinatario = email_url if email_url else st.session_state.get('pax_email')
        nome_pax = nome_url if nome_url else st.session_state.get('pax_nome', 'Passageiro')

        if destinatario:
            with st.spinner("Confirmando pagamento e enviando e-mail..."):
                assunto = "Recebemos seu pagamento! ✈️ - Flight Monitor"
                corpo = f"""
                <div style="font-family: sans-serif; border: 1px solid #ddd; padding: 20px; border-radius: 10px;">
                    <h2 style="color: #003580;">Olá {nome_pax}, recebemos o seu pagamento!</h2>
                    <p>Obrigado por escolher a <b>Flight Monitor</b>.</p>
                    <p>Seu pagamento foi aprovado com sucesso via Stripe. Agora, nossa equipe está processando a emissão do seu bilhete junto à companhia aérea.</p>
                    <p><b>O que acontece agora?</b> Em instantes, após a emissão ser concluída, você receberá um <b>segundo e-mail</b> contendo o seu código de reserva (PNR) e os detalhes do embarque.</p>
                    <hr>
                    <p style="font-size: 12px; color: #666;">Este é um e-mail automático de confirmação de transação.</p>
                </div>
                """
                if enviar_email(destinatario, assunto, corpo):
                    st.session_state["email_1_enviado"] = True
                    st.session_state["pago"] = True
                    st.balloons()
                    st.success(f"✅ Pagamento confirmado! E-mail de processamento enviado para {destinatario}")

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

# --- PÁGINA 3: LOGIN (ADMIN / EMISSÃO MANUAL) ---

elif st.session_state.pagina == "login":
    st.title("✈️ Área do Passageiro")
    st.subheader("Aceda à sua reserva e itinerários")

    # Painel de Login
    with st.container(border=True):
        col_l1, col_l2 = st.columns(2)
        email_input = col_l1.text_input("E-mail utilizado na compra")
        pnr_input = col_l2.text_input("Código da Reserva (PNR)")
        
        if st.button("Procurar Minha Viagem", use_container_width=True):
            with st.spinner("A consultar base de dados..."):
                reserva_encontrada = buscar_reserva_por_pnr(email_input, pnr_input)
                
                if reserva_encontrada:
                    st.session_state.reserva_ativa = reserva_encontrada
                    st.success("Reserva localizada com sucesso!")
                else:
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
        c3.metric("Total Pago", res['Valor'])

        st.info(f"📍 **Itinerário:** {res['Itinerário']}")

        # Ações do Cliente
        st.subheader("🛠️ Gestão da Reserva")
        col_btn1, col_btn2, col_btn3 = st.columns(3)

        with col_btn1:
            # Pega o link da coluna H (que na nossa função de busca seria o índice 7 ou chave 'PDF')
            # Se você atualizou a função buscar_reserva_por_pnr, adicione a chave 'PDF': linha[7]
            url_pdf = res.get('PDF', "")
            if url_pdf:
                st.link_button("📄 Baixar Itinerário (PDF)", url_pdf, use_container_width=True)
            else:
                st.button("📄 PDF em Processamento", disabled=True, use_container_width=True)
        
        with col_btn1:
            if st.button("📄 Ver Itinerário (PDF)", use_container_width=True):
                st.info("O link para o PDF oficial será gerado aqui.")
        
        with col_btn2:
            if st.button("🔄 Alterar Voo", use_container_width=True):
                st.warning("Para alterações, contacte o suporte via WhatsApp.")
        
        with col_btn3:
            if st.button("❌ Cancelar Viagem", type="secondary", use_container_width=True):
                st.error("Atenção: Cancelamentos dependem das regras da companhia aérea.")