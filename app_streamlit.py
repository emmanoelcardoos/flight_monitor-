import streamlit as st
import requests
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import stripe
import gspread
from oauth2client.service_account import ServiceAccountCredentials


# =========================
# CONFIG
# =========================
COMISSAO_PERCENTUAL = 0.12
WHATSAPP_SUPORTE = "351936797003"

AEROPORTOS = {
    "São Paulo (GRU)": "GRU",
    "São Paulo (CGH)": "CGH",
    "Rio de Janeiro (GIG)": "GIG",
    "Rio de Janeiro (SDU)": "SDU",
    "Brasília (BSB)": "BSB",
    "Belo Horizonte (CNF)": "CNF",
    "Salvador (SSA)": "SSA",
    "Recife (REC)": "REC",
    "Fortaleza (FOR)": "FOR",
    "Natal (NAT)": "NAT",
    "Maceió (MCZ)": "MCZ",
    "João Pessoa (JPA)": "JPA",
    "Aracaju (AJU)": "AJU",
    "Porto Alegre (POA)": "POA",
    "Curitiba (CWB)": "CWB",
    "Florianópolis (FLN)": "FLN",
    "Cuiabá (CGB)": "CGB",
    "Campo Grande (CGR)": "CGR",
    "Goiânia (GYN)": "GYN",
    "Belém (BEL)": "BEL",
    "Manaus (MAO)": "MAO",
    "Macapá (MCP)": "MCP",
    "Boa Vista (BVB)": "BVB",
    "Porto Velho (PVH)": "PVH",
    "Rio Branco (RBR)": "RBR",
    "Palmas (PMW)": "PMW",
    "São Luís (SLZ)": "SLZ",
    "Teresina (THE)": "THE",
    "Vitória (VIX)": "VIX",
    "Campinas (VCP)": "VCP",
    "Foz do Iguaçu (IGU)": "IGU",
    "Navegantes (NVT)": "NVT",
    "Joinville (JOI)": "JOI",
    "Ilhéus (IOS)": "IOS",
    "Porto Seguro (BPS)": "BPS",
    "Chapecó (XAP)": "XAP",
    "Uberlândia (UDI)": "UDI",
    "Montes Claros (MOC)": "MOC",
    "Imperatriz (IMP)": "IMP",
    "Marabá (MAB)": "MAB",
    "Santarém (STM)": "STM",
    "Lisboa (LIS)": "LIS",
    "Porto (OPO)": "OPO",
    "Faro (FAO)": "FAO",
    "Funchal (FNC)": "FNC",
    "Ponta Delgada (PDL)": "PDL",
    "Madrid (MAD)": "MAD",
    "Barcelona (BCN)": "BCN",
    "Valência (VLC)": "VLC",
    "Sevilha (SVQ)": "SVQ",
    "Paris (CDG)": "CDG",
    "Roma (FCO)": "FCO",
    "Milão (MXP)": "MXP",
    "Frankfurt (FRA)": "FRA",
    "Londres (LHR)": "LHR",
}

AEROPORTOS_BRASIL = {
    "GRU", "CGH", "GIG", "SDU", "BSB", "CNF", "SSA", "REC", "FOR", "NAT",
    "MCZ", "JPA", "AJU", "POA", "CWB", "FLN", "CGB", "CGR", "GYN", "BEL",
    "MAO", "MCP", "BVB", "PVH", "RBR", "PMW", "SLZ", "THE", "VIX", "VCP",
    "IGU", "NVT", "JOI", "IOS", "BPS", "XAP", "UDI", "MOC", "IMP", "MAB", "STM"
}


# =========================
# GOOGLE SHEETS
# =========================
def conectar_sheets():
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds_dict = st.secrets["gspread"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("Alertas_Flight_Monitor")
    except Exception as e:
        st.error(f"Erro ao conectar ao Google Sheets: {e}")
        return None


def salvar_reserva_sheets(nome_completo, email, pnr, itinerario, valor, link_pdf=""):
    planilha = conectar_sheets()
    if not planilha:
        return False

    try:
        aba = planilha.worksheet("Reservas_Confirmadas")
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
        aba.append_row([email, pnr, nome_completo, data_hora, itinerario, valor, "Emitido", link_pdf])
        return True
    except Exception as e:
        st.error(f"Erro ao gravar no Sheets: {e}")
        return False


def buscar_reserva_por_pnr(email_cliente, pnr_cliente):
    planilha = conectar_sheets()
    if not planilha:
        return None

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

            if (
                email_planilha == email_cliente.strip().lower()
                and pnr_planilha == pnr_cliente.strip().upper()
            ):
                return {
                    "Email": linha[0],
                    "PNR": linha[1],
                    "Passageiro": linha[2] if len(linha) > 2 else "Passageiro",
                    "Data": linha[3] if len(linha) > 3 else "",
                    "Itinerário": linha[4] if len(linha) > 4 else "",
                    "Valor": linha[5] if len(linha) > 5 else "€ 0.00",
                    "Status": linha[6] if len(linha) > 6 else "Confirmado",
                    "PDF": linha[7] if len(linha) > 7 else "",
                }

        return None
    except Exception as e:
        st.error(f"Erro ao buscar na base de dados: {e}")
        return None


def salvar_alerta_preco(email, itinerario, origem, destino, data_ida, preco_inicial, moeda):
    planilha = conectar_sheets()
    if not planilha:
        return False

    try:
        aba = planilha.get_worksheet(0)
        nova_linha = [
            email, itinerario, origem, destino, str(data_ida),
            "", 1, 0, 0, preco_inicial, moeda
        ]
        aba.append_row(nova_linha)
        return True
    except Exception as e:
        st.error(f"Erro ao gravar alerta: {e}")
        return False


# =========================
# EMAIL
# =========================
def enviar_email(destinatario, assunto, corpo_html):
    try:
        remetente = st.secrets["EMAIL_USER"]
        senha = st.secrets["EMAIL_PASSWORD"]

        msg = MIMEMultipart()
        msg["From"] = remetente
        msg["To"] = destinatario
        msg["Subject"] = assunto
        msg.attach(MIMEText(corpo_html, "html"))

        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=30)
        server.starttls()
        server.login(remetente, senha)
        server.sendmail(remetente, destinatario, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False


def montar_email_confirmacao(nome, pnr, companhia, trechos, valor_total):
    blocos_trechos = []

    for idx_fatia, fatia in enumerate(trechos, start=1):
        for seg in fatia:
            blocos_trechos.append(f"""
                <div style="padding: 12px; border: 1px solid #eee; border-radius: 8px; margin-bottom: 10px; background-color: #fafafa;">
                    <strong>{seg['cia']}</strong><br>
                    <span><b>{seg['de']}</b> ➔ <b>{seg['para']}</b></span><br>
                    <span>Partida: {seg['partida']} | Chegada: {seg['chegada']}</span><br>
                    <span>Aeronave: {seg['aviao']}</span>
                </div>
            """)

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; background-color: #f4f4f4; margin: 0; padding: 20px;">
        <div style="max-width: 650px; margin: auto; background: white; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #003580; padding: 30px 20px; text-align: center; color: white;">
                <h1 style="margin: 0;">Bilhete emitido com sucesso</h1>
                <p style="margin-top: 8px;">Olá, {nome}.</p>
            </div>

            <div style="padding: 20px;">
                <p><strong>PNR:</strong> {pnr}</p>
                <p><strong>Companhia:</strong> {companhia}</p>
                <p><strong>Valor pago:</strong> {valor_total}</p>

                <h3>Detalhes do itinerário</h3>
                {''.join(blocos_trechos)}

                <p style="margin-top: 20px;">
                    Chegue ao aeroporto com antecedência e tenha os seus documentos em mãos.
                </p>
            </div>

            <div style="padding: 20px; background: #f8f8f8; text-align: center; font-size: 12px; color: #666;">
                © {datetime.now().year} Flight Monitor
            </div>
        </div>
    </body>
    </html>
    """
    return html


# =========================
# APIs EXTERNAS
# =========================
def get_cotacao_ao_vivo():
    try:
        res = requests.get("https://economia.awesomeapi.com.br/last/EUR-BRL", timeout=20)
        if res.status_code == 200:
            return float(res.json()["EURBRL"]["bid"])
        return 6.02
    except Exception:
        return 6.02


def criar_checkout_stripe(valor_eur, nome_pax, email_pax, itinerario):
    stripe.api_key = st.secrets.get("STRIPE_SECRET_KEY")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "eur",
                    "product_data": {"name": f"Voo: {itinerario}"},
                    "unit_amount": int(float(valor_eur) * 100),
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"https://flightmonitorec.streamlit.app/?pagamento=sucesso&email={email_pax}&nome={nome_pax}",
            cancel_url="https://flightmonitorec.streamlit.app/?pagamento=cancelado",
            customer_email=email_pax,
        )
        return session.url
    except Exception as e:
        st.error(f"Erro na Stripe: {e}")
        return None


# =========================
# STREAMLIT STATE
# =========================
st.set_page_config(page_title="Flight Monitor GDS", page_icon="✈️", layout="wide")

if "pagina" not in st.session_state:
    st.session_state.pagina = "busca"

if "voo_selecionado" not in st.session_state:
    st.session_state.voo_selecionado = None

if "busca_feita" not in st.session_state:
    st.session_state.busca_feita = False

if "resultados_voos" not in st.session_state:
    st.session_state.resultados_voos = []

if "reserva_ativa" not in st.session_state:
    st.session_state.reserva_ativa = None

if st.query_params.get("pagamento") == "sucesso":
    st.session_state.pagina = "sucesso"


# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.title("📌 Flight Monitor")
    if st.button("🔍 Procurar Voos"):
        st.session_state.pagina = "busca"
    if st.button("👤 Área do Cliente"):
        st.session_state.pagina = "login"

    st.divider()
    st.markdown(f"**Suporte:** [WhatsApp](https://wa.me/{WHATSAPP_SUPORTE})")


# =========================
# PÁGINA BUSCA
# =========================
if st.session_state.pagina == "busca":
    st.title("✈️ Flight Monitor Trips")

    if st.button("Limpar Cache e Nova Busca"):
        st.session_state.resultados_voos = []
        st.session_state.busca_feita = False
        st.session_state.voo_selecionado = None
        st.rerun()

    opcoes_cidades = list(AEROPORTOS.keys())
    tipo_v = st.radio("Tipo de Viagem", ["Apenas Ida", "Ida e Volta"], horizontal=True)

    with st.form("busca_voos"):
        col1, col2 = st.columns(2)
        origem = col1.selectbox("Origem", opcoes_cidades)
        destino = col2.selectbox("Destino", opcoes_cidades)

        col3, col4 = st.columns(2)
        data_ida = col3.date_input("Data de Partida", value=datetime.today() + timedelta(days=7))

        data_volta = None
        if tipo_v == "Ida e Volta":
            data_volta = col4.date_input("Data de Retorno", value=datetime.today() + timedelta(days=14))
        else:
            col4.info("Viagem só de ida")

        moeda_visu = col1.selectbox("Exibir preços em:", ["Real (R$)", "Euro (€)"])
        btn = st.form_submit_button("PESQUISAR VOOS", use_container_width=True)

    if btn:
        if origem == destino:
            st.error("Origem e destino não podem ser iguais.")
        elif tipo_v == "Ida e Volta" and data_volta and data_volta <= data_ida:
            st.error("A data de retorno deve ser posterior à data de ida.")
        else:
            st.session_state.busca_feita = True

            try:
                with st.spinner("Em busca dos melhores voos..."):
                    cotacao_atual = get_cotacao_ao_vivo()
                    api_token = st.secrets["DUFFEL_TOKEN"]

                    headers = {
                        "Authorization": f"Bearer {api_token}",
                        "Duffel-Version": "v2",
                        "Content-Type": "application/json",
                    }

                    iata_o = AEROPORTOS[origem]
                    iata_d = AEROPORTOS[destino]

                    fatias = [{
                        "origin": iata_o,
                        "destination": iata_d,
                        "departure_date": str(data_ida),
                    }]

                    if tipo_v == "Ida e Volta" and data_volta:
                        fatias.append({
                            "origin": iata_d,
                            "destination": iata_o,
                            "departure_date": str(data_volta),
                        })

                    is_intl = not (iata_o in AEROPORTOS_BRASIL and iata_d in AEROPORTOS_BRASIL)

                    payload = {
                        "data": {
                            "slices": fatias,
                            "passengers": [{"type": "adult"}],
                            "requested_currencies": ["EUR"],
                        }
                    }

                    res = requests.post(
                        "https://api.duffel.com/air/offer_requests",
                        headers=headers,
                        json=payload,
                        timeout=60,
                    )

                    if res.status_code == 201:
                        resposta = res.json()["data"]
                        offers = resposta.get("offers", [])
                        passageiros = resposta.get("passengers", [])

                        st.session_state.resultados_voos = []

                        for o in offers[:15]:
                            fatias_voo = []

                            for slice_data in o.get("slices", []):
                                segs_fatia = []

                                for seg in slice_data.get("segments", []):
                                    segs_fatia.append({
                                        "de": seg["origin"]["iata_code"],
                                        "para": seg["destination"]["iata_code"],
                                        "partida": seg["departing_at"].split("T")[1][:5],
                                        "chegada": seg["arriving_at"].split("T")[1][:5],
                                        "cia": seg["marketing_carrier"]["name"],
                                        "aviao": seg["aircraft"]["name"] if seg.get("aircraft") else "N/D",
                                    })

                                fatias_voo.append(segs_fatia)

                            valor_eur = float(o["total_amount"])
                            preco_final = valor_eur * (1 + COMISSAO_PERCENTUAL)

                            if "Real" in moeda_visu:
                                preco_exibicao = preco_final * cotacao_atual
                                moeda = "R$"
                            else:
                                preco_exibicao = preco_final
                                moeda = "€"

                            st.session_state.resultados_voos.append({
                                "id_offer": o["id"],
                                "Companhia": o["owner"]["name"],
                                "Preço": preco_exibicao,
                                "Moeda": moeda,
                                "Trechos": fatias_voo,
                                "Internacional": is_intl,
                                "valor_bruto_duffel": o["total_amount"],
                                "pax_ids": [p["id"] for p in passageiros],
                            })
                    else:
                        erro = res.json()
                        st.error(f"Erro na Duffel: {erro}")

            except Exception as e:
                st.error(f"Erro durante a busca: {e}")

    if st.session_state.busca_feita and st.session_state.resultados_voos:
        resultados = sorted(st.session_state.resultados_voos, key=lambda x: x["Preço"])
        st.markdown(f"### 🔍 Encontramos {len(resultados)} opções")

        for idx, v in enumerate(resultados):
            trechos = v.get("Trechos", [])
            if not trechos:
                continue

            with st.container(border=True):
                col_logo, col_info, col_preco = st.columns([1, 3, 1.5])

                col_logo.subheader(v["Companhia"])

                with col_info:
                    ida = trechos[0]
                    st.markdown(f"**🛫 Ida:** {ida[0]['de']} ({ida[0]['partida']}) ➔ {ida[-1]['para']} ({ida[-1]['chegada']})")

                    if len(trechos) > 1:
                        volta = trechos[1]
                        st.markdown(f"**🛬 Volta:** {volta[0]['de']} ({volta[0]['partida']}) ➔ {volta[-1]['para']} ({volta[-1]['chegada']})")

                    with st.expander("Ver escalas e aeronaves"):
                        for i, fatia in enumerate(trechos, start=1):
                            st.caption(f"TRECHO {i}")
                            for s in fatia:
                                st.write(f"✈️ {s['cia']} | {s['de']} ➔ {s['para']} ({s['aviao']})")

                with col_preco:
                    st.subheader(f"{v['Moeda']} {v['Preço']:.2f}")
                    if st.button("SELECIONAR", key=f"sel_{idx}", use_container_width=True, type="primary"):
                        st.session_state.voo_selecionado = v
                        st.session_state.pagina = "reserva"
                        st.rerun()

        st.divider()
        st.subheader("🔔 Não encontrou o preço que queria?")

        with st.expander("Criar Alerta de Preço"):
            email_alerta = st.text_input("Seu e-mail para o alerta")

            menor_preco = resultados[0]["Preço"]
            moeda_txt = resultados[0]["Moeda"]

            if st.button("Ativar Alerta de Preço", use_container_width=True):
                if not email_alerta:
                    st.error("Informe um e-mail.")
                else:
                    itinerario_txt = f"{origem} para {destino}"
                    sucesso = salvar_alerta_preco(
                        email_alerta,
                        itinerario_txt,
                        origem,
                        destino,
                        data_ida,
                        menor_preco,
                        moeda_txt,
                    )

                    if sucesso:
                        st.success(f"✅ Alerta guardado. Avisaremos em {email_alerta}")
                    else:
                        st.error("Erro ao gravar alerta.")


# =========================
# PÁGINA LOGIN
# =========================
elif st.session_state.pagina == "login":
    st.title("✈️ Área do Passageiro")
    st.subheader("Aceda à sua reserva e itinerários")

    with st.container(border=True):
        col_l1, col_l2 = st.columns(2)
        email_input = col_l1.text_input("E-mail utilizado na compra")
        pnr_input = col_l2.text_input("Código da Reserva (PNR)")

        if st.button("Procurar Minha Viagem", use_container_width=True, type="primary"):
            with st.spinner("A consultar base de dados..."):
                reserva_encontrada = buscar_reserva_por_pnr(email_input, pnr_input)

                if reserva_encontrada:
                    st.session_state.reserva_ativa = reserva_encontrada
                    st.success("Reserva localizada com sucesso!")
                else:
                    st.session_state.reserva_ativa = None
                    st.error("Não encontramos nenhuma reserva com estes dados.")

    if st.session_state.get("reserva_ativa"):
        res = st.session_state.reserva_ativa
        st.divider()

        st.markdown(f"### Olá, {res['Passageiro']}! 👋")

        c1, c2, c3 = st.columns(3)
        c1.metric("Localizador (PNR)", res["PNR"])
        c2.metric("Status", res["Status"])
        c3.metric("Total Pago", res.get("Valor", "€ 0.00"))

        st.info(f"📍 **Itinerário:** {res.get('Itinerário', 'Consultar Bilhete')}")

        st.subheader("🛠️ Gestão da Reserva")
        col_btn1, col_btn2, col_btn3 = st.columns(3)

        with col_btn1:
            url_pdf = res.get("PDF", "").strip()
            if url_pdf and url_pdf.startswith("http"):
                st.link_button("📄 Baixar Itinerário (PDF)", url_pdf, use_container_width=True)
            else:
                st.button("📄 PDF em Processamento", disabled=True, use_container_width=True)

        with col_btn2:
            st.link_button("🔄 Alterar Dados", f"https://wa.me/{WHATSAPP_SUPORTE}", use_container_width=True)

        with col_btn3:
            if st.button("❌ Cancelar Viagem", type="secondary", use_container_width=True):
                st.warning("Pedidos de cancelamento são analisados pelo suporte em até 24h.")


# =========================
# PÁGINA RESERVA
# =========================
elif st.session_state.pagina == "reserva":
    v = st.session_state.get("voo_selecionado")

    if not v:
        st.session_state.pagina = "busca"
        st.rerun()

    st.title("🏁 Finalizar Reserva")

    trechos = v.get("Trechos", [])
    if not trechos:
        st.error("Não foi possível carregar os trechos do voo.")
        st.stop()

    ida = trechos[0]
    origem_p = ida[0]["de"]
    destino_p = ida[-1]["para"]

    st.info(f"✈️ **Voo:** {v.get('Companhia')} | **Resumo:** {origem_p} ➔ {destino_p}")
    st.metric(label="Valor Total a Pagar", value=f"{v['Moeda']} {v['Preço']:.2f}")

    col_dados, col_resumo = st.columns([2, 1])

    with col_dados:
        with st.form("form_pax"):
            st.subheader("👤 Detalhes do Passageiro")

            c_tit, c_gen = st.columns(2)
            titulo_input = c_tit.selectbox("Título", ["Senhor", "Senhora"])
            genero_input = c_gen.selectbox("Gênero", ["Masculino", "Feminino"])

            c1, c2 = st.columns(2)
            nome_pax = c1.text_input("Nome", value=st.session_state.get("pax_nome", ""))
            apelido_pax = c2.text_input("Apelido / Sobrenome", value=st.session_state.get("pax_apelido", ""))

            email_pax = st.text_input("E-mail", value=st.session_state.get("pax_email", ""))

            c3, c4 = st.columns(2)
            documento_id = c3.text_input("CPF / Cartão de Cidadão")
            nasc_pax = c4.date_input(
                "Data de Nascimento",
                value=datetime(1995, 1, 1),
                min_value=datetime(1920, 1, 1),
                max_value=datetime.today(),
            )

            precisa_passaporte = v.get("Internacional", False)
            passaporte = ""
            validade_passaporte = None

            if precisa_passaporte:
                st.warning("⚠️ Voo internacional: passaporte obrigatório")
                cp1, cp2 = st.columns(2)
                passaporte = cp1.text_input("Número do Passaporte")
                validade_passaporte = cp2.date_input(
                    "Validade do Passaporte",
                    value=datetime.today() + timedelta(days=365),
                )

            submitted = st.form_submit_button("✅ VALIDAR DADOS")

            if submitted:
                if not nome_pax or not apelido_pax or not email_pax:
                    st.error("Preencha nome, apelido e e-mail.")
                else:
                    st.session_state["pax_titulo"] = "mr" if titulo_input == "Senhor" else "mrs"
                    st.session_state["pax_genero"] = "m" if genero_input == "Masculino" else "f"
                    st.session_state["pax_nome"] = nome_pax
                    st.session_state["pax_apelido"] = apelido_pax
                    st.session_state["pax_email"] = email_pax
                    st.session_state["pax_documento"] = documento_id
                    st.session_state["pax_nascimento"] = str(nasc_pax)
                    st.session_state["pax_passaporte"] = passaporte
                    st.session_state["pax_validade_passaporte"] = str(validade_passaporte) if validade_passaporte else ""
                    st.success("Dados validados com sucesso.")

    with col_resumo:
        st.subheader("💳 Pagamento")

        if st.session_state.get("pax_email"):
            itinerario_pagamento = f"{origem_p} ➔ {destino_p}"
            url_checkout = criar_checkout_stripe(
                v["valor_bruto_duffel"],
                st.session_state["pax_nome"],
                st.session_state["pax_email"],
                itinerario_pagamento,
            )
            if url_checkout:
                st.link_button("🚀 PAGAR AGORA", url_checkout, type="primary", use_container_width=True)
        else:
            st.warning("Valide os dados do passageiro ao lado primeiro.")

    st.divider()

    if st.button("EMITIR BILHETE", type="primary", use_container_width=True):
        if not st.session_state.get("pax_email"):
            st.error("Valide os dados do passageiro antes de emitir.")
        else:
            try:
                with st.spinner("Emitindo bilhete..."):
                    api_token = st.secrets["DUFFEL_TOKEN"]
                    headers = {
                        "Authorization": f"Bearer {api_token}",
                        "Duffel-Version": "v2",
                        "Content-Type": "application/json",
                    }

                    nome = st.session_state["pax_nome"]
                    apelido = st.session_state["pax_apelido"]
                    email = st.session_state["pax_email"]
                    dn = st.session_state["pax_nascimento"]
                    tit_code = st.session_state["pax_titulo"]
                    gen_code = st.session_state["pax_genero"]

                    payload = {
                        "data": {
                            "type": "instant",
                            "selected_offers": [v["id_offer"]],
                            "passengers": [{
                                "id": v["pax_ids"][0],
                                "title": tit_code,
                                "given_name": nome,
                                "family_name": apelido,
                                "gender": gen_code,
                                "born_on": dn,
                                "email": email,
                                "phone_number": f"+{WHATSAPP_SUPORTE}",
                            }],
                            "payments": [{
                                "type": "balance",
                                "currency": "EUR",
                                "amount": v["valor_bruto_duffel"],
                            }],
                        }
                    }

                    res_ordem = requests.post(
                        "https://api.duffel.com/air/orders",
                        headers=headers,
                        json=payload,
                        timeout=60,
                    )

                    if res_ordem.status_code == 201:
                        dados_reserva = res_ordem.json()["data"]
                        pnr = dados_reserva["booking_reference"]

                        documentos = dados_reserva.get("documents", [])
                        link_pdf_oficial = documentos[0]["url"] if documentos else ""

                        itinerario_venda = f"{origem_p} ➔ {destino_p}"
                        valor_venda = f"{v['Moeda']} {v['Preço']:.2f}"

                        sucesso_sheets = salvar_reserva_sheets(
                            f"{nome} {apelido}",
                            email,
                            pnr,
                            itinerario_venda,
                            valor_venda,
                            link_pdf_oficial,
                        )

                        if sucesso_sheets:
                            st.toast("Dados guardados na base de dados! ✅")

                        html_design = montar_email_confirmacao(
                            nome=f"{nome} {apelido}",
                            pnr=pnr,
                            companhia=v["Companhia"],
                            trechos=trechos,
                            valor_total=valor_venda,
                        )

                        enviar_email(
                            destinatario=email,
                            assunto=f"Seu bilhete foi emitido! PNR: {pnr}",
                            corpo_html=html_design,
                        )

                        st.success(f"✅ Bilhete emitido com sucesso! PNR: {pnr}")

                    else:
                        try:
                            erro_msg = res_ordem.json()["errors"][0]["message"]
                        except Exception:
                            erro_msg = res_ordem.text
                        st.error(f"Erro na Duffel: {erro_msg}")

            except Exception as e:
                st.error(f"Erro técnico na emissão: {e}")

    if st.button("⬅️ Voltar"):
        st.session_state.pagina = "busca"
        st.rerun()


# =========================
# PÁGINA SUCESSO
# =========================
elif st.session_state.pagina == "sucesso":
    st.balloons()
    st.success("### 🎉 Pagamento Confirmado com Sucesso!")

    nome_pax = st.query_params.get("nome", "Passageiro")
    email_pax = st.query_params.get("email", "seu e-mail")

    with st.container(border=True):
        st.markdown(f"""
        **Olá {nome_pax},**

        Recebemos o seu pagamento. A emissão do seu bilhete está a ser processada.

        **O que verificar agora?**
        1. Receberá um e-mail de confirmação em **{email_pax}**.
        2. Depois receberá o bilhete com o PNR e detalhes do embarque.
        3. Se precisar de ajuda, use o suporte abaixo.
        """)

        st.link_button(
            "💬 Falar com Suporte (WhatsApp)",
            f"https://wa.me/{WHATSAPP_SUPORTE}",
            use_container_width=True,
        )

    st.divider()
    if st.button("Voltar ao Início", use_container_width=True):
        st.session_state.pagina = "busca"
        st.session_state.busca_feita = False
        st.session_state.resultados_voos = []
        st.session_state.voo_selecionado = None
        st.rerun()