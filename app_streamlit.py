import json
import re
from datetime import datetime, timedelta
import requests
import smtplib
import streamlit as st
import stripe
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from supabase import create_client
from supabase.lib.client_options import ClientOptions


# =========================================================
# CONFIG GERAL
# =========================================================
COMISSAO_PERCENTUAL = 0.12
WHATSAPP_SUPORTE = "351936797003"
NOME_PLANILHA = "Alertas_Flight_Monitor"
NOME_AGENCIA = "Flight Monitor Premium"

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


# =========================================================
# TEMAS
# =========================================================
def obter_temas():
    return {
        "Sky Light": {
            "bg": "#f5f9ff",
            "card": "#ffffff",
            "text": "#0f172a",
            "muted": "#667085",
            "border": "#dbe7f5",
            "primary": "#0a66c2",
            "secondary": "#003580",
            "accent": "#38bdf8",
            "success_bg": "#ecfdf3",
            "success_text": "#027a48",
            "hero_grad_1": "#003580",
            "hero_grad_2": "#0057b8",
            "sidebar_bg": "#eef5ff",
            "warning_bg": "#fff7ed",
            "warning_text": "#c2410c",
        },
        "Midnight Luxury": {
            "bg": "#0b0b0f",
            "card": "#151821",
            "text": "#f3f4f6",
            "muted": "#9ca3af",
            "border": "#272b36",
            "primary": "#b91c1c",
            "secondary": "#7f1d1d",
            "accent": "#ef4444",
            "success_bg": "#13261c",
            "success_text": "#86efac",
            "hero_grad_1": "#111111",
            "hero_grad_2": "#7f1d1d",
            "sidebar_bg": "#111318",
            "warning_bg": "#2a1812",
            "warning_text": "#fdba74",
        },
        "Executive Dark Blue": {
            "bg": "#0f172a",
            "card": "#162033",
            "text": "#f8fafc",
            "muted": "#cbd5e1",
            "border": "#263247",
            "primary": "#2563eb",
            "secondary": "#1d4ed8",
            "accent": "#60a5fa",
            "success_bg": "#0f2c22",
            "success_text": "#6ee7b7",
            "hero_grad_1": "#0f172a",
            "hero_grad_2": "#1d4ed8",
            "sidebar_bg": "#131d31",
            "warning_bg": "#332701",
            "warning_text": "#fcd34d",
        },
        "Classic Agency": {
            "bg": "#fcfcfd",
            "card": "#ffffff",
            "text": "#111827",
            "muted": "#6b7280",
            "border": "#e5e7eb",
            "primary": "#1d4ed8",
            "secondary": "#1e3a8a",
            "accent": "#c8a96b",
            "success_bg": "#eefbf3",
            "success_text": "#15803d",
            "hero_grad_1": "#1e3a8a",
            "hero_grad_2": "#1d4ed8",
            "sidebar_bg": "#f8fafc",
            "warning_bg": "#fff7ed",
            "warning_text": "#c2410c",
        },
    }


def aplicar_estilo(tema_nome="Sky Light"):
    temas = obter_temas()
    tema = temas.get(tema_nome, temas["Sky Light"])

    st.markdown(f"""
    <style>
    .stApp {{
        background: {tema['bg']};
        color: {tema['text']};
    }}

    [data-testid="stSidebar"] {{
        background: {tema['sidebar_bg']};
        border-right: 1px solid {tema['border']};
    }}

    .block-container {{
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1280px;
    }}

    .agency-hero {{
        background: linear-gradient(135deg, {tema['hero_grad_1']}, {tema['hero_grad_2']});
        color: white;
        padding: 30px;
        border-radius: 22px;
        margin-bottom: 18px;
        box-shadow: 0 12px 30px rgba(0,0,0,0.16);
    }}

    .agency-hero h1 {{
        margin: 0 0 8px 0;
        font-size: 2rem;
    }}

    .agency-hero p {{
        margin: 0;
        opacity: 0.95;
        font-size: 1rem;
    }}

    .agency-card {{
        background: {tema['card']};
        border: 1px solid {tema['border']};
        border-radius: 20px;
        padding: 18px;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
        margin-bottom: 14px;
        color: {tema['text']};
    }}

    .small-muted {{
        color: {tema['muted']};
        font-size: 0.92rem;
    }}

    .price-big {{
        font-size: 2rem;
        font-weight: 700;
        color: {tema['text']};
    }}

    .badge-ok {{
        display: inline-block;
        padding: 7px 12px;
        background: {tema['success_bg']};
        color: {tema['success_text']};
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 700;
        margin-bottom: 8px;
    }}

    .badge-warning {{
        display: inline-block;
        padding: 7px 12px;
        background: {tema['warning_bg']};
        color: {tema['warning_text']};
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 700;
        margin-bottom: 8px;
    }}

    .box-soft {{
        background: {tema['card']};
        border: 1px solid {tema['border']};
        border-radius: 16px;
        padding: 14px;
        color: {tema['text']};
    }}

    div[data-testid="stMetric"] {{
        background: {tema['card']};
        border: 1px solid {tema['border']};
        padding: 12px;
        border-radius: 16px;
    }}

    div[data-testid="stForm"] {{
        background: {tema['card']};
        border: 1px solid {tema['border']};
        padding: 18px;
        border-radius: 18px;
    }}

    .stButton > button {{
        background: {tema['primary']};
        color: white;
        border: none;
        border-radius: 12px;
        font-weight: 600;
    }}

    .stButton > button:hover {{
        background: {tema['secondary']};
        color: white;
    }}

    .stDownloadButton > button {{
        background: {tema['primary']};
        color: white;
        border-radius: 12px;
        border: none;
    }}

    .stTextInput input,
    .stDateInput input,
    .stTextArea textarea,
    .stNumberInput input {{
        background: {tema['card']} !important;
        color: {tema['text']} !important;
        border-radius: 12px !important;
    }}

    .stSelectbox div[data-baseweb="select"] > div {{
        background: {tema['card']} !important;
        color: {tema['text']} !important;
        border-radius: 12px !important;
    }}

    h1, h2, h3, h4, h5, h6, p, label, span, div {{
        color: inherit;
    }}
    </style>
    """, unsafe_allow_html=True)


# =========================================================
# VALIDAÇÕES E HELPERS
# =========================================================
def email_valido(email: str) -> bool:
    padrao = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return re.match(padrao, email.strip()) is not None


def nome_valido(nome: str) -> bool:
    return len(nome.strip()) >= 2


def documento_valido(doc: str) -> bool:
    return len(doc.strip()) >= 5


def money_fmt(moeda: str, valor: float) -> str:
    return f"{moeda} {valor:.2f}"


# =========================================================
# SUPABASE
# =========================================================
@st.cache_resource(show_spinner=False)
def conectar_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(
        url,
        key,
        options=ClientOptions(
            auto_refresh_token=False,
            persist_session=False,
        ),
    )


def salvar_reserva_db(nome_completo, email, pnr, itinerario, valor, link_pdf=""):
    try:
        supabase = conectar_supabase()
        payload = {
            "email": email.strip().lower(),
            "pnr": pnr.strip().upper(),
            "passageiro": nome_completo,
            "itinerario": itinerario,
            "valor": valor,
            "status": "Emitido",
            "pdf_url": link_pdf,
        }
        supabase.table("reservas").insert(payload).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao gravar reserva: {e}")
        return False


def buscar_reserva_por_pnr(email_cliente, pnr_cliente):
    try:
        supabase = conectar_supabase()
        resp = (
            supabase.table("reservas")
            .select("*")
            .eq("email", email_cliente.strip().lower())
            .eq("pnr", pnr_cliente.strip().upper())
            .limit(1)
            .execute()
        )

        if not resp.data:
            return None

        r = resp.data[0]
        return {
            "Email": r.get("email", ""),
            "PNR": r.get("pnr", ""),
            "Passageiro": r.get("passageiro", "Passageiro"),
            "Data": r.get("data_criacao", ""),
            "Itinerário": r.get("itinerario", ""),
            "Valor": r.get("valor", "€ 0.00"),
            "Status": r.get("status", "Confirmado"),
            "PDF": r.get("pdf_url", ""),
        }
    except Exception as e:
        st.error(f"Erro ao buscar reserva: {e}")
        return None


def salvar_alerta_preco(email, itinerario, origem, destino, data_ida, preco_inicial, moeda):
    try:
        supabase = conectar_supabase()
        payload = {
            "email": email.strip().lower(),
            "itinerario": itinerario,
            "origem": origem,
            "destino": destino,
            "data_ida": str(data_ida),
            "preco_inicial": preco_inicial,
            "moeda": moeda,
            "ativo": True,
            "disparos": 0,
        }
        supabase.table("alertas_preco").insert(payload).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao gravar alerta: {e}")
        return False


def registrar_pagamento_pendente(
    session_id, checkout_url, email, nome, apelido, offer_id, itinerario,
    companhia, preco_exibido, moeda_exibida, valor_duffel_eur, trechos, pax_ids
):
    try:
        supabase = conectar_supabase()

        payload = {
            "session_id": session_id,
            "checkout_url": checkout_url,
            "email": email.strip().lower(),
            "nome": nome,
            "apelido": apelido,
            "offer_id": offer_id,
            "itinerario": itinerario,
            "companhia": companhia,
            "preco_exibido": preco_exibido,
            "moeda_exibida": moeda_exibida,
            "valor_duffel_eur": valor_duffel_eur,
            "status_pagamento": "PENDENTE",
            "stripe_payment_status": "unpaid",
            "trechos_json": trechos,
            "pax_ids_json": pax_ids,
        }

        existente = (
            supabase.table("pagamentos")
            .select("id")
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )

        if existente.data:
            supabase.table("pagamentos").update(payload).eq("session_id", session_id).execute()
        else:
            supabase.table("pagamentos").insert(payload).execute()

        return True
    except Exception as e:
        st.error(f"Erro ao registrar pagamento pendente: {e}")
        return False


def marcar_pagamento_como_pago(session_id, stripe_payment_status="paid"):
    try:
        supabase = conectar_supabase()
        supabase.table("pagamentos").update({
            "status_pagamento": "PAGO",
            "stripe_payment_status": stripe_payment_status,
            "data_confirmacao": datetime.utcnow().isoformat(),
        }).eq("session_id", session_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao marcar pagamento como pago: {e}")
        return False


def obter_pagamento_por_session_id(session_id):
    try:
        supabase = conectar_supabase()
        resp = (
            supabase.table("pagamentos")
            .select("*")
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        st.error(f"Erro ao obter pagamento: {e}")
        return None


def pagamento_confirmado(email, offer_id):
    try:
        supabase = conectar_supabase()
        resp = (
            supabase.table("pagamentos")
            .select("id")
            .eq("email", email.strip().lower())
            .eq("offer_id", offer_id)
            .eq("status_pagamento", "PAGO")
            .limit(1)
            .execute()
        )
        return len(resp.data) > 0
    except Exception:
        return False


def reconstruir_voo_por_session_id(session_id):
    pagamento = obter_pagamento_por_session_id(session_id)
    if not pagamento:
        return None

    return {
        "id_offer": pagamento.get("offer_id", ""),
        "Companhia": pagamento.get("companhia", ""),
        "Preço": float(pagamento.get("preco_exibido") or 0),
        "Moeda": pagamento.get("moeda_exibida", "€"),
        "Trechos": pagamento.get("trechos_json", []) or [],
        "Internacional": False,
        "valor_bruto_duffel": float(pagamento.get("valor_duffel_eur") or 0),
        "pax_ids": pagamento.get("pax_ids_json", []) or [],
    }

# =========================================================
# EMAIL
# =========================================================
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


def montar_email_confirmacao(nome, pnr, companhia, trechos, valor_total, itinerario):
    blocos = []

    for idx_fatia, fatia in enumerate(trechos, start=1):
        blocos.append(f"""
        <div style="margin: 0 0 12px 0; font-weight: bold; color: #003580;">Trecho {idx_fatia}</div>
        """)

        for seg in fatia:
            blocos.append(f"""
            <div style="padding: 14px; border: 1px solid #eee; border-radius: 10px; margin-bottom: 10px; background: #fafafa;">
                <div style="font-weight: bold;">{seg['cia']}</div>
                <div style="margin-top: 6px;"><b>{seg['de']}</b> ➔ <b>{seg['para']}</b></div>
                <div style="margin-top: 4px; color: #666;">Partida: {seg['partida']} | Chegada: {seg['chegada']}</div>
                <div style="margin-top: 4px; color: #666;">Aeronave: {seg['aviao']}</div>
            </div>
            """)

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; background-color: #f4f4f4; margin: 0; padding: 20px;">
        <div style="max-width: 680px; margin: auto; background: white; border-radius: 12px; overflow: hidden;">
            <div style="background: linear-gradient(135deg, #003580, #0057b8); color: white; padding: 26px;">
                <h1 style="margin:0;">✈️ Bilhete emitido com sucesso</h1>
                <p style="margin-top:8px;">Olá, {nome}. A sua viagem está confirmada.</p>
            </div>

            <div style="padding: 24px;">
                <p><strong>PNR:</strong> {pnr}</p>
                <p><strong>Itinerário:</strong> {itinerario}</p>
                <p><strong>Companhia:</strong> {companhia}</p>
                <p><strong>Valor pago:</strong> {valor_total}</p>

                <h3 style="color:#003580;">Detalhes do voo</h3>
                {''.join(blocos)}

                <div style="margin-top: 20px; padding: 16px; background:#f8fafc; border-radius:10px; border:1px solid #e2e8f0;">
                    <strong>Informações importantes:</strong><br>
                    Chegue ao aeroporto com antecedência mínima de 3 horas em voos internacionais e 2 horas em voos domésticos.<br>
                    Tenha os seus documentos em mãos no momento do embarque.
                </div>
            </div>

            <div style="padding: 18px; text-align:center; background:#111827; color:#d1d5db; font-size: 12px;">
                © {datetime.now().year} {NOME_AGENCIA}
            </div>
        </div>
    </body>
    </html>
    """


# =========================================================
# APIS EXTERNAS
# =========================================================
def get_cotacao_ao_vivo():
    try:
        res = requests.get("https://economia.awesomeapi.com.br/last/EUR-BRL", timeout=20)
        if res.status_code == 200:
            return float(res.json()["EURBRL"]["bid"])
        return 6.02
    except Exception:
        return 6.02


def criar_checkout_stripe(
    valor_eur, nome_pax, apelido_pax, email_pax, itinerario, offer_id,
    companhia, preco_exibido, moeda_exibida, trechos, pax_ids
):
    stripe.api_key = st.secrets.get("STRIPE_SECRET_KEY")
    base_url = st.secrets.get("APP_BASE_URL", "https://flightmonitorec.streamlit.app")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "eur",
                    "product_data": {
                        "name": f"Voo: {itinerario}",
                        "description": f"Reserva aérea - {nome_pax} {apelido_pax}"
                    },
                    "unit_amount": int(float(valor_eur) * 100),
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{base_url}/?pagamento=sucesso&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base_url}/?pagamento=cancelado",
            customer_email=email_pax,
            metadata={
                "nome_pax": nome_pax,
                "apelido_pax": apelido_pax,
                "email_pax": email_pax,
                "itinerario": itinerario,
                "offer_id": offer_id,
                "companhia": companhia,
            }
        )

        registrar_pagamento_pendente(
            session_id=session.id,
            checkout_url=session.url,
            email=email_pax,
            nome=nome_pax,
            apelido=apelido_pax,
            offer_id=offer_id,
            itinerario=itinerario,
            companhia=companhia,
            preco_exibido=preco_exibido,
            moeda_exibida=moeda_exibida,
            valor_duffel_eur=valor_eur,
            trechos=trechos,
            pax_ids=pax_ids,
        )
        return session.url
    except Exception as e:
        st.error(f"Erro na Stripe: {e}")
        return None


def verificar_pagamento_stripe_por_session(session_id):
    stripe.api_key = st.secrets.get("STRIPE_SECRET_KEY")
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return {
            "id": session.id,
            "payment_status": session.payment_status,
            "status": session.status,
            "customer_email": session.customer_email,
        }
    except Exception as e:
        return {"erro": str(e)}


def criar_ordem_duffel(offer_id, pax_id, titulo, nome, apelido, genero, nascimento, email):
    api_token = st.secrets["DUFFEL_TOKEN"]
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Duffel-Version": "v2",
        "Content-Type": "application/json",
    }

    payload = {
        "data": {
            "type": "instant",
            "selected_offers": [offer_id],
            "passengers": [{
                "id": pax_id,
                "title": titulo,
                "given_name": nome,
                "family_name": apelido,
                "gender": genero,
                "born_on": nascimento,
                "email": email,
                "phone_number": f"+{WHATSAPP_SUPORTE}",
            }],
            "payments": []
        }
    }

    return requests.post(
        "https://api.duffel.com/air/orders",
        headers=headers,
        json=payload,
        timeout=60,
    )


# =========================================================
# UI HELPERS
# =========================================================
def hero_home():
    st.markdown(f"""
    <div class="agency-hero">
        <h1>✈️ {NOME_AGENCIA}</h1>
        <p>Tarifas em tempo real, pagamento seguro e apoio especializado para a sua próxima viagem.</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown('<div class="badge-ok">Pagamento Seguro</div>', unsafe_allow_html=True)
    c2.markdown('<div class="badge-ok">Atendimento Humanizado</div>', unsafe_allow_html=True)
    c3.markdown('<div class="badge-ok">Emissão Assistida</div>', unsafe_allow_html=True)
    c4.markdown('<div class="badge-ok">Suporte Pós-Venda</div>', unsafe_allow_html=True)


def mostrar_blocos_confianca():
    st.markdown("### Por que reservar connosco?")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("""
        <div class="agency-card">
            <h4>🔐 Pagamento Protegido</h4>
            <p class="small-muted">Processamento seguro via Stripe, com validação antes da emissão.</p>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <div class="agency-card">
            <h4>📩 Confirmação por E-mail</h4>
            <p class="small-muted">Receba o localizador, itinerário e detalhes do voo no seu e-mail.</p>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown("""
        <div class="agency-card">
            <h4>💬 Apoio Especializado</h4>
            <p class="small-muted">Suporte via WhatsApp para alterações, dúvidas e acompanhamento.</p>
        </div>
        """, unsafe_allow_html=True)


def render_card_voo(v, idx):
    trechos = v.get("Trechos", [])
    if not trechos:
        return

    ida = trechos[0]
    ida_origem = ida[0]["de"]
    ida_destino = ida[-1]["para"]
    ida_partida = ida[0]["partida"]
    ida_chegada = ida[-1]["chegada"]

    st.markdown('<div class="agency-card">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([2, 4, 2])

    with col1:
        st.markdown(f"**{v['Companhia']}**")
        st.markdown('<span class="small-muted">Tarifa disponível no momento</span>', unsafe_allow_html=True)
        st.caption("🌍 Voo internacional" if v.get("Internacional") else "✈️ Voo doméstico/regional")

    with col2:
        st.markdown(f"### {ida_origem} ➔ {ida_destino}")
        st.markdown(
            f'<div class="small-muted">Partida às {ida_partida} • Chegada às {ida_chegada}</div>',
            unsafe_allow_html=True
        )

        if len(trechos) > 1:
            volta = trechos[1]
            st.markdown(
                f'<div class="small-muted" style="margin-top: 6px;">Retorno: {volta[0]["de"]} ({volta[0]["partida"]}) ➔ {volta[-1]["para"]} ({volta[-1]["chegada"]})</div>',
                unsafe_allow_html=True
            )

        with st.expander("Ver escalas, companhia e aeronaves"):
            for i, fatia in enumerate(trechos, start=1):
                st.write(f"**Trecho {i}**")
                for seg in fatia:
                    st.write(
                        f"✈️ {seg['cia']} | {seg['de']} ➔ {seg['para']} | {seg['partida']} → {seg['chegada']} | {seg['aviao']}"
                    )

    with col3:
        st.markdown(f'<div class="price-big">{v["Moeda"]} {v["Preço"]:.2f}</div>', unsafe_allow_html=True)
        st.markdown('<div class="small-muted">Taxas incluídas</div>', unsafe_allow_html=True)
        st.caption("Sujeito à disponibilidade")

        if st.button("SELECIONAR", key=f"sel_{idx}", type="primary", use_container_width=True):
            st.session_state.voo_selecionado = v
            st.session_state.pagina = "reserva"
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# APP CONFIG
# =========================================================
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
if "pagamento_confirmado_atual" not in st.session_state:
    st.session_state.pagamento_confirmado_atual = False
if "tema_visual" not in st.session_state:
    st.session_state.tema_visual = "Sky Light"


tema_url = st.query_params.get("tema")
if tema_url in obter_temas():
    st.session_state.tema_visual = tema_url

aplicar_estilo(st.session_state.tema_visual)

if st.query_params.get("pagamento") == "sucesso":
    st.session_state.pagina = "sucesso"

with st.sidebar:
    st.title("📌 Flight Monitor")

    tema_escolhido = st.selectbox(
        "🎨 Estilo visual",
        options=list(obter_temas().keys()),
        index=list(obter_temas().keys()).index(st.session_state.tema_visual)
    )
    st.session_state.tema_visual = tema_escolhido

    if st.button("🔍 Procurar Voos", use_container_width=True):
        st.session_state.pagina = "busca"

    if st.button("👤 Área do Cliente", use_container_width=True):
        st.session_state.pagina = "login"

    st.divider()
    st.caption("Pagamento seguro • emissão rápida • apoio humanizado")
    st.markdown(f"**Suporte:** [WhatsApp](https://wa.me/{WHATSAPP_SUPORTE})")


# =========================================================
# PÁGINA BUSCA
# =========================================================
if st.session_state.pagina == "busca":
    hero_home()
    mostrar_blocos_confianca()

    if st.button("Limpar Cache e Nova Busca"):
        st.session_state.resultados_voos = []
        st.session_state.busca_feita = False
        st.session_state.voo_selecionado = None
        st.session_state.pagamento_confirmado_atual = False
        st.cache_data.clear()
        st.rerun()

    st.markdown("## Pesquisar voos")
    opcoes_cidades = list(AEROPORTOS.keys())
    tipo_v = st.radio("Tipo de viagem", ["Apenas Ida", "Ida e Volta"], horizontal=True)

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
                with st.spinner("Em busca das melhores opções..."):
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
                            preco_final_eur = valor_eur * (1 + COMISSAO_PERCENTUAL)

                            if "Real" in moeda_visu:
                                preco_exibicao = preco_final_eur * cotacao_atual
                                moeda = "R$"
                            else:
                                preco_exibicao = preco_final_eur
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
                        try:
                            st.error(f"Erro na Duffel: {res.json()}")
                        except Exception:
                            st.error(f"Erro na Duffel: {res.text}")

            except Exception as e:
                st.error(f"Erro durante a busca: {e}")

    if st.session_state.busca_feita and st.session_state.resultados_voos:
        resultados = sorted(st.session_state.resultados_voos, key=lambda x: x["Preço"])
        st.markdown(f"## 🔍 Encontrámos {len(resultados)} opções")
        st.caption("Tarifas sujeitas à disponibilidade e alteração até à emissão.")

        for idx, v in enumerate(resultados):
            render_card_voo(v, idx)

        st.divider()
        st.subheader("🔔 Alerta de preço")

        with st.expander("Criar alerta para esta pesquisa"):
            email_alerta = st.text_input("Seu e-mail para receber alerta")
            menor_preco = resultados[0]["Preço"]
            moeda_txt = resultados[0]["Moeda"]

            if st.button("Ativar Alerta de Preço", use_container_width=True):
                if not email_valido(email_alerta):
                    st.error("Informe um e-mail válido.")
                else:
                    itinerario_txt = f"{origem} para {destino}"
                    sucesso = salvar_alerta_preco(
                        email_alerta, itinerario_txt, origem, destino, data_ida, menor_preco, moeda_txt
                    )

                    if sucesso:
                        st.success(f"✅ Alerta guardado. Avisaremos em {email_alerta}")
                    else:
                        st.error("Erro ao gravar alerta.")


# =========================================================
# PÁGINA LOGIN / ÁREA DO PASSAGEIRO
# =========================================================
elif st.session_state.pagina == "login":
    st.markdown("""
    <div class="agency-hero">
        <h1>👤 Área do Passageiro</h1>
        <p>Aceda à sua reserva, veja o itinerário e acompanhe o estado da emissão.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        col_l1, col_l2 = st.columns(2)
        email_input = col_l1.text_input("E-mail utilizado na compra")
        pnr_input = col_l2.text_input("Código da Reserva (PNR)")

        if st.button("Procurar Minha Viagem", use_container_width=True, type="primary"):
            with st.spinner("A consultar base de dados..."):
                if not email_valido(email_input):
                    st.error("Informe um e-mail válido.")
                elif not pnr_input.strip():
                    st.error("Informe o PNR.")
                else:
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
        st.markdown(f"### Olá, {res['Passageiro']} 👋")

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
            st.link_button("🔄 Alterações / Suporte", f"https://wa.me/{WHATSAPP_SUPORTE}", use_container_width=True)

        with col_btn3:
            if st.button("❌ Solicitar Cancelamento", type="secondary", use_container_width=True):
                st.warning("Pedidos de cancelamento são analisados pelo suporte em até 24h.")


# =========================================================
# PÁGINA RESERVA
# =========================================================
elif st.session_state.pagina == "reserva":
    v = st.session_state.get("voo_selecionado")

    if not v:
        st.session_state.pagina = "busca"
        st.rerun()

    trechos = v.get("Trechos", [])
    if not trechos:
        st.error("Não foi possível carregar os trechos do voo.")
        st.stop()

    ida = trechos[0]
    origem_p = ida[0]["de"]
    destino_p = ida[-1]["para"]
    itinerario_curto = f"{origem_p} ➔ {destino_p}"

    st.markdown(f"""
    <div class="agency-hero">
        <h1>🏁 Finalizar Reserva</h1>
        <p>{v.get("Companhia")} • {itinerario_curto} • Processo assistido e pagamento seguro.</p>
    </div>
    """, unsafe_allow_html=True)

    top1, top2, top3 = st.columns(3)
    top1.metric("Companhia", v["Companhia"])
    top2.metric("Itinerário", itinerario_curto)
    top3.metric("Valor Total", money_fmt(v["Moeda"], v["Preço"]))

    col_dados, col_resumo = st.columns([2, 1])

    with col_dados:
        st.markdown("### 👤 Dados do Passageiro")
        with st.form("form_pax"):
            c_tit, c_gen = st.columns(2)
            titulo_input = c_tit.selectbox("Título", ["Senhor", "Senhora"])
            genero_input = c_gen.selectbox("Gênero", ["Masculino", "Feminino"])

            c1, c2 = st.columns(2)
            nome_pax = c1.text_input("Nome", value=st.session_state.get("pax_nome", ""))
            apelido_pax = c2.text_input("Apelido / Sobrenome", value=st.session_state.get("pax_apelido", ""))

            email_pax = st.text_input("E-mail", value=st.session_state.get("pax_email", ""))

            c3, c4 = st.columns(2)
            documento_id = c3.text_input("CPF / Cartão de Cidadão", value=st.session_state.get("pax_documento", ""))
            nasc_pax = c4.date_input(
                "Data de Nascimento",
                value=datetime(1995, 1, 1),
                min_value=datetime(1920, 1, 1),
                max_value=datetime.today(),
            )

            precisa_passaporte = v.get("Internacional", False)
            passaporte = st.session_state.get("pax_passaporte", "")
            validade_passaporte = None

            if precisa_passaporte:
                st.warning("⚠️ Voo internacional: passaporte obrigatório")
                cp1, cp2 = st.columns(2)
                passaporte = cp1.text_input("Número do Passaporte", value=st.session_state.get("pax_passaporte", ""))
                validade_passaporte = cp2.date_input(
                    "Validade do Passaporte",
                    value=datetime.today() + timedelta(days=365),
                )

            submitted = st.form_submit_button("✅ VALIDAR DADOS", use_container_width=True)

            if submitted:
                erros = []

                if not nome_valido(nome_pax):
                    erros.append("Nome inválido.")
                if not nome_valido(apelido_pax):
                    erros.append("Apelido inválido.")
                if not email_valido(email_pax):
                    erros.append("E-mail inválido.")
                if not documento_valido(documento_id):
                    erros.append("Documento inválido.")
                if precisa_passaporte and not passaporte.strip():
                    erros.append("Passaporte obrigatório para voo internacional.")

                if erros:
                    for erro in erros:
                        st.error(erro)
                else:
                    st.session_state["pax_titulo"] = "mr" if titulo_input == "Senhor" else "mrs"
                    st.session_state["pax_genero"] = "m" if genero_input == "Masculino" else "f"
                    st.session_state["pax_nome"] = nome_pax.strip()
                    st.session_state["pax_apelido"] = apelido_pax.strip()
                    st.session_state["pax_email"] = email_pax.strip()
                    st.session_state["pax_documento"] = documento_id.strip()
                    st.session_state["pax_nascimento"] = str(nasc_pax)
                    st.session_state["pax_passaporte"] = passaporte.strip()
                    st.session_state["pax_validade_passaporte"] = str(validade_passaporte) if validade_passaporte else ""
                    st.success("Dados validados com sucesso.")

    with col_resumo:
        st.markdown("### 💳 Resumo e Pagamento")
        st.markdown('<div class="box-soft">', unsafe_allow_html=True)
        st.write(f"**Rota:** {itinerario_curto}")
        st.write(f"**Companhia:** {v['Companhia']}")
        st.write(f"**Preço final:** {money_fmt(v['Moeda'], v['Preço'])}")
        st.caption("Pagamento processado com segurança pela Stripe.")
        st.markdown('</div>', unsafe_allow_html=True)

        dados_ok = all([
            st.session_state.get("pax_nome"),
            st.session_state.get("pax_apelido"),
            st.session_state.get("pax_email"),
        ])

        email_pax_atual = st.session_state.get("pax_email", "")
        pagamento_ok = pagamento_confirmado(email_pax_atual, v["id_offer"])

        if not dados_ok:
            st.warning("Valide os dados do passageiro para gerar o link de pagamento.")
        else:
            if not pagamento_ok:
                if st.button("🔐 GERAR LINK DE PAGAMENTO", use_container_width=True, type="primary"):
                    url_checkout = criar_checkout_stripe(
                        valor_eur=float(v["valor_bruto_duffel"]),
                        nome_pax=st.session_state["pax_nome"],
                        apelido_pax=st.session_state["pax_apelido"],
                        email_pax=st.session_state["pax_email"],
                        itinerario=itinerario_curto,
                        offer_id=v["id_offer"],
                        companhia=v["Companhia"],
                        preco_exibido=v["Preço"],
                        moeda_exibida=v["Moeda"],
                        trechos=trechos,
                        pax_ids=v.get("pax_ids", []),
                    )
                    if url_checkout:
                        st.success("Link de pagamento gerado com sucesso.")
                        st.link_button("🚀 PAGAR AGORA", url_checkout, use_container_width=True)
            else:
                st.success("✅ Pagamento confirmado.")
                st.session_state.pagamento_confirmado_atual = True

    st.divider()
    st.markdown("### ✈️ Emissão do Bilhete")

    email_atual = st.session_state.get("pax_email", "")
    pode_emitir = pagamento_confirmado(email_atual, v["id_offer"])

    if not pode_emitir:
        st.info("A emissão será liberada assim que o pagamento for confirmado pela Stripe.")
    else:
        st.success("Pagamento validado. Já é possível emitir o bilhete.")

        if st.button("EMITIR BILHETE", type="primary", use_container_width=True):
            try:
                with st.spinner("Emitindo bilhete com a companhia aérea..."):
                    nome = st.session_state["pax_nome"]
                    apelido = st.session_state["pax_apelido"]
                    email = st.session_state["pax_email"]
                    dn = st.session_state["pax_nascimento"]
                    tit_code = st.session_state["pax_titulo"]
                    gen_code = st.session_state["pax_genero"]

                    if not v.get("pax_ids"):
                        st.error("Não foi possível localizar o passageiro da oferta. Faça uma nova busca.")
                        st.stop()

                    res_ordem = criar_ordem_duffel(
                        offer_id=v["id_offer"],
                        pax_id=v["pax_ids"][0],
                        titulo=tit_code,
                        nome=nome,
                        apelido=apelido,
                        genero=gen_code,
                        nascimento=dn,
                        email=email,
                    )

                    if res_ordem.status_code == 201:
                        dados_reserva = res_ordem.json()["data"]
                        pnr = dados_reserva["booking_reference"]

                        documentos = dados_reserva.get("documents", [])
                        link_pdf_oficial = documentos[0]["url"] if documentos else ""

                        itinerario_venda = itinerario_curto
                        valor_venda = money_fmt(v["Moeda"], v["Preço"])

                        salvar_reserva_db(
                            f"{nome} {apelido}",
                            email,
                            pnr,
                            itinerario_venda,
                            valor_venda,
                            link_pdf_oficial
                        )

                        html_design = montar_email_confirmacao(
                            nome=f"{nome} {apelido}",
                            pnr=pnr,
                            companhia=v["Companhia"],
                            trechos=trechos,
                            valor_total=valor_venda,
                            itinerario=itinerario_venda
                        )

                        enviar_email(
                            destinatario=email,
                            assunto=f"Bilhete emitido com sucesso • PNR {pnr}",
                            corpo_html=html_design,
                        )

                        st.success(f"✅ Bilhete emitido com sucesso! PNR: {pnr}")
                        st.balloons()
                    else:
                        try:
                            erro_msg = res_ordem.json()["errors"][0]["message"]
                        except Exception:
                            erro_msg = res_ordem.text
                        st.error(f"Erro na Duffel: {erro_msg}")

            except Exception as e:
                st.error(f"Erro técnico na emissão: {e}")

    if st.button("⬅️ Voltar", use_container_width=True):
        st.session_state.pagina = "busca"
        st.rerun()


# =========================================================
# PÁGINA SUCESSO PÓS-PAGAMENTO
# =========================================================
elif st.session_state.pagina == "sucesso":
    st.markdown("""
    <div class="agency-hero">
        <h1>🎉 Pagamento Recebido</h1>
        <p>Estamos a validar a transação e a preparar a próxima etapa da sua reserva.</p>
    </div>
    """, unsafe_allow_html=True)

    session_id = st.query_params.get("session_id", "")

    if not session_id:
        st.error("Sessão de pagamento não encontrada na URL.")
    else:
        with st.spinner("A validar pagamento junto da Stripe..."):
            dados_stripe = verificar_pagamento_stripe_por_session(session_id)

        if dados_stripe.get("erro"):
            st.error(f"Erro ao validar a Stripe: {dados_stripe['erro']}")
        else:
            payment_status = dados_stripe.get("payment_status", "")
            checkout_status = dados_stripe.get("status", "")
            email_cliente = dados_stripe.get("customer_email", "")

            pagamento = obter_pagamento_por_session_id(session_id)

            if payment_status == "paid":
                marcar_pagamento_como_pago(session_id, stripe_payment_status=payment_status)
                st.session_state.pagamento_confirmado_atual = True

                st.success("✅ Pagamento confirmado com sucesso.")
                st.write(f"**Estado Stripe:** {checkout_status}")
                if email_cliente:
                    st.write(f"**E-mail do cliente:** {email_cliente}")

                if pagamento:
                    st.markdown('<div class="box-soft">', unsafe_allow_html=True)
                    st.write(f"**Itinerário:** {pagamento.get('Itinerario', '')}")
                    st.write(f"**Companhia:** {pagamento.get('Companhia', '')}")
                    st.write(f"**Preço:** {pagamento.get('Moeda_Exibida', '')} {pagamento.get('Preco_Exibido', '')}")
                    st.markdown('</div>', unsafe_allow_html=True)

                st.info("Volte para a página da reserva para concluir a emissão do bilhete.")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Ir para emissão", use_container_width=True, type="primary"):
                        voo_reconstruido = reconstruir_voo_por_session_id(session_id)
                        if voo_reconstruido:
                            st.session_state.voo_selecionado = voo_reconstruido
                            st.session_state.pagina = "reserva"
                            st.rerun()
                        else:
                            st.error("Não foi possível recuperar os dados da reserva para continuar a emissão.")

                with col2:
                    if st.button("Voltar ao início", use_container_width=True):
                        st.session_state.pagina = "busca"
                        st.rerun()

            else:
                st.warning("O pagamento ainda não aparece como confirmado na Stripe.")
                st.write(f"**Estado Stripe:** {checkout_status}")
                st.write(f"**Payment status:** {payment_status}")

                if st.button("Atualizar verificação", use_container_width=True):
                    st.rerun()