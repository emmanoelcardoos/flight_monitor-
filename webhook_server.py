import os
import smtplib
from pathlib import Path
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
import stripe
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from supabase import create_client

# =========================================================
# CARREGAR .env
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

app = FastAPI()

# =========================================================
# ENV
# =========================================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

if not SUPABASE_URL:
    raise RuntimeError(f"Falta a variável SUPABASE_URL no .env ({ENV_PATH})")

if not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError(f"Falta a variável SUPABASE_SERVICE_ROLE_KEY no .env ({ENV_PATH})")

if not STRIPE_SECRET_KEY:
    raise RuntimeError(f"Falta a variável STRIPE_SECRET_KEY no .env ({ENV_PATH})")

if not STRIPE_WEBHOOK_SECRET:
    raise RuntimeError(f"Falta a variável STRIPE_WEBHOOK_SECRET no .env ({ENV_PATH})")

if not EMAIL_USER:
    raise RuntimeError(f"Falta a variável EMAIL_USER no .env ({ENV_PATH})")

if not EMAIL_PASSWORD:
    raise RuntimeError(f"Falta a variável EMAIL_PASSWORD no .env ({ENV_PATH})")

stripe.api_key = STRIPE_SECRET_KEY
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# =========================================================
# HELPERS
# =========================================================
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def enviar_email(destinatario: str, assunto: str, corpo_html: str):
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = destinatario
        msg["Subject"] = assunto
        msg.attach(MIMEText(corpo_html, "html"))

        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=30)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USER, destinatario, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"[ERRO] enviar_email: {e}")
        return False


def marcar_email_pagamento_enviado(session_id: str):
    try:
        (
            supabase.table("pagamentos")
            .update({"email_pagamento_enviado": True})
            .eq("session_id", session_id)
            .execute()
        )
        return True
    except Exception as e:
        print(f"[ERRO] marcar_email_pagamento_enviado: {e}")
        return False

def montar_email_pagamento_recebido(nome_cliente: str, itinerario: str, companhia: str, valor_total: str):
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; background-color: #f4f4f4; margin: 0; padding: 20px;">
        <div style="max-width: 680px; margin: auto; background: white; border-radius: 12px; overflow: hidden;">
            <div style="background: linear-gradient(135deg, #003580, #0057b8); color: white; padding: 26px;">
                <h1 style="margin:0;">✅ Pagamento Recebido</h1>
                <p style="margin-top:8px;">Olá, {nome_cliente}. O seu pagamento foi confirmado com sucesso.</p>
            </div>

            <div style="padding: 24px;">
                <p><strong>Itinerário:</strong> {itinerario}</p>
                <p><strong>Companhia:</strong> {companhia}</p>
                <p><strong>Valor:</strong> {valor_total}</p>

                <div style="margin-top: 20px; padding: 16px; background:#f8fafc; border-radius:10px; border:1px solid #e2e8f0;">
                    Recebemos o seu pagamento e a sua reserva está agora em processamento.<br><br>
                    O seu bilhete e o localizador (PNR) serão enviados por e-mail assim que a emissão for concluída.
                </div>
            </div>

            <div style="padding: 18px; text-align:center; background:#111827; color:#d1d5db; font-size: 12px;">
                © {datetime.now().year} Flight Monitor Premium
            </div>
        </div>
    </body>
    </html>
    """


def obter_pagamento_por_session_id(session_id: str):
    try:
        resp = (
            supabase.table("pagamentos")
            .select("*")
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        print(f"[ERRO] obter_pagamento_por_session_id: {e}")
        return None


def marcar_pagamento_como_pago(session_id: str, stripe_payment_status: str = "paid"):
    try:
        (
            supabase.table("pagamentos")
            .update(
                {
                    "status_pagamento": "PAGO",
                    "stripe_payment_status": stripe_payment_status,
                    "data_confirmacao": utc_now_iso(),
                }
            )
            .eq("session_id", session_id)
            .execute()
        )
        return True
    except Exception as e:
        print(f"[ERRO] marcar_pagamento_como_pago: {e}")
        return False

def marcar_emissao_status(session_id: str, status: str, pnr: str | None = None, pdf_url: str | None = None):
    try:
        payload = {"emissao_status": status}

        if pnr is not None:
            payload["pnr"] = pnr

        if pdf_url is not None:
            payload["pdf_url"] = pdf_url

        (
            supabase.table("pagamentos")
            .update(payload)
            .eq("session_id", session_id)
            .execute()
        )
        return True
    except Exception as e:
        print(f"[ERRO] marcar_emissao_status: {e}")
        return False


def marcar_email_bilhete_enviado(session_id: str):
    try:
        (
            supabase.table("pagamentos")
            .update({"email_bilhete_enviado": True})
            .eq("session_id", session_id)
            .execute()
        )
        return True
    except Exception as e:
        print(f"[ERRO] marcar_email_bilhete_enviado: {e}")
        return False


def salvar_reserva_db(nome_completo, email, pnr, itinerario, valor, link_pdf=""):
    try:
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
        print(f"[ERRO] salvar_reserva_db: {e}")
        return False


def montar_email_bilhete_emitido(
    nome_passageiro,
    pnr,
    companhia,
    itinerario,
    valor_total,
    trechos,
    bagagem_info=None,
    pdf_url="",
):
    blocos_trechos = []

    for idx_fatia, fatia in enumerate(trechos, start=1):
        blocos_trechos.append(
            f"""
            <div style="margin: 0 0 12px 0; font-weight: bold; color: #003580; font-size: 16px;">
                Trecho {idx_fatia}
            </div>
            """
        )

        for seg in fatia:
            blocos_trechos.append(
                f"""
                <div style="padding: 14px; border: 1px solid #e5e7eb; border-radius: 10px; margin-bottom: 10px; background: #fafafa;">
                    <div style="font-weight: bold; font-size: 15px;">{seg.get('cia', 'Companhia aérea')}</div>
                    <div style="margin-top: 8px; font-size: 18px;">
                        <strong>{seg.get('de', '---')}</strong> ➔ <strong>{seg.get('para', '---')}</strong>
                    </div>
                    <div style="margin-top: 6px; color: #555; font-size: 14px;">
                        Partida: {seg.get('partida', '--:--')} &nbsp;|&nbsp;
                        Chegada: {seg.get('chegada', '--:--')}
                    </div>
                    <div style="margin-top: 6px; color: #666; font-size: 13px;">
                        Aeronave: {seg.get('aviao', 'N/D')}
                    </div>
                </div>
                """
            )

    if bagagem_info:
        bagagem_html = f"""
        <div style="margin-top: 20px; padding: 16px; background:#f8fafc; border-radius:10px; border:1px solid #dbeafe;">
            <h3 style="margin-top:0; color:#003580;">🧳 Bagagem</h3>
            <p style="margin:0; font-size:15px; color:#333;">{bagagem_info}</p>
        </div>
        """
    else:
        bagagem_html = """
        <div style="margin-top: 20px; padding: 16px; background:#f8fafc; border-radius:10px; border:1px solid #dbeafe;">
            <h3 style="margin-top:0; color:#003580;">🧳 Bagagem</h3>
            <p style="margin:0; font-size:15px; color:#333;">
                A franquia de bagagem pode variar conforme a tarifa. Consulte as regras completas no bilhete emitido.
            </p>
        </div>
        """

    botao_pdf = ""
    if pdf_url:
        botao_pdf = f"""
        <div style="margin-top: 24px; text-align:center;">
            <a href="{pdf_url}" style="background:#003580; color:white; text-decoration:none; padding:14px 22px; border-radius:8px; display:inline-block; font-weight:bold;">
                Baixar Bilhete / Itinerário
            </a>
        </div>
        """

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; background-color: #f4f4f4; margin: 0; padding: 20px;">
        <div style="max-width: 700px; margin: auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.08);">
            <div style="background: linear-gradient(135deg, #003580, #0057b8); color: white; padding: 28px;">
                <h1 style="margin:0; font-size: 32px;">✈️ Bilhete Emitido</h1>
                <p style="margin-top:10px; font-size:18px;">Olá, {nome_passageiro}. A sua viagem está confirmada.</p>
            </div>

            <div style="padding: 24px;">
                <div style="padding: 16px; border: 1px solid #e5e7eb; border-radius: 10px; background: #fcfcfc;">
                    <p style="margin: 0 0 10px 0; font-size:15px;"><strong>Passageiro:</strong> {nome_passageiro}</p>
                    <p style="margin: 0 0 10px 0; font-size:15px;"><strong>PNR:</strong> {pnr}</p>
                    <p style="margin: 0 0 10px 0; font-size:15px;"><strong>Companhia:</strong> {companhia}</p>
                    <p style="margin: 0 0 10px 0; font-size:15px;"><strong>Itinerário:</strong> {itinerario}</p>
                    <p style="margin: 0; font-size:15px;"><strong>Valor pago:</strong> {valor_total}</p>
                </div>

                <h3 style="margin-top:24px; color:#003580;">📍 Detalhes do Voo</h3>
                {''.join(blocos_trechos)}

                {bagagem_html}

                <div style="margin-top: 20px; padding: 16px; background:#fff7ed; border-radius:10px; border:1px solid #fed7aa;">
                    <h3 style="margin-top:0; color:#9a3412;">📌 Próximos passos</h3>
                    <ul style="padding-left:18px; margin:0; color:#333; line-height:1.6;">
                        <li>Verifique os documentos necessários para embarque.</li>
                        <li>Chegue ao aeroporto com antecedência.</li>
                        <li>Consulte o check-in diretamente com a companhia aérea.</li>
                    </ul>
                </div>

                {botao_pdf}
            </div>

            <div style="padding: 18px; text-align:center; background:#0f172a; color:#d1d5db; font-size: 12px;">
                © {datetime.now().year} Flight Monitor Premium
            </div>
        </div>
    </body>
    </html>
    """


def emitir_bilhete_duffel(pagamento: dict):
    try:
        api_token = os.getenv("DUFFEL_TOKEN")
        if not api_token:
            print("[ERRO] DUFFEL_TOKEN não definido no .env")
            return None, "DUFFEL_TOKEN não definido"

        headers = {
            "Authorization": f"Bearer {api_token}",
            "Duffel-Version": "v2",
            "Content-Type": "application/json",
        }

        pax_ids = pagamento.get("pax_ids_json") or []
        if not pax_ids:
            return None, "pax_ids_json ausente"

        payload = {
            "data": {
                "type": "instant",
                "selected_offers": [pagamento["offer_id"]],
                "passengers": [{
                    "id": pax_ids[0],
                    "title": pagamento.get("titulo"),
                    "given_name": pagamento.get("nome"),
                    "family_name": pagamento.get("apelido"),
                    "gender": pagamento.get("genero"),
                    "born_on": pagamento.get("data_nascimento"),
                    "email": pagamento.get("email"),
                    "phone_number": "+351936797003",
                }],
                "payments": []
            }
        }

        resposta = requests.post(
            "https://api.duffel.com/air/orders",
            headers=headers,
            json=payload,
            timeout=60,
        )

        if resposta.status_code != 201:
            try:
                erro_msg = resposta.json()["errors"][0]["message"]
            except Exception:
                erro_msg = resposta.text
            return None, erro_msg

        return resposta.json()["data"], None

    except Exception as e:
        return None, str(e)
# =========================================================
# ROTAS
# =========================================================
@app.get("/")
def home():
    return {"status": "ok", "service": "stripe-webhook-server"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "env_path": str(ENV_PATH),
        "supabase_url_loaded": bool(SUPABASE_URL),
        "supabase_key_loaded": bool(SUPABASE_SERVICE_ROLE_KEY),
        "stripe_key_loaded": bool(STRIPE_SECRET_KEY),
        "stripe_webhook_secret_loaded": bool(STRIPE_WEBHOOK_SECRET),
        "email_user_loaded": bool(EMAIL_USER),
        "email_password_loaded": bool(EMAIL_PASSWORD),
    }


@app.post("/stripe-webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
):
    if not stripe_signature:
        print("[ERRO] Stripe-Signature em falta")
        raise HTTPException(status_code=400, detail="Stripe-Signature em falta")

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=STRIPE_WEBHOOK_SECRET,
        )
    except ValueError as e:
        print(f"[ERRO] Payload inválido: {e}")
        raise HTTPException(status_code=400, detail="Payload inválido")
    except stripe.error.SignatureVerificationError as e:
        print(f"[ERRO] Assinatura inválida: {e}")
        raise HTTPException(status_code=400, detail="Assinatura inválida")
    except Exception as e:
        print(f"[ERRO] Erro ao validar webhook: {e}")
        raise HTTPException(status_code=400, detail=f"Erro ao validar webhook: {e}")

    event_type = event.get("type", "")
    obj = event.get("data", {}).get("object", {})

    print(f"[WEBHOOK] Evento recebido: {event_type}")

    if event_type != "checkout.session.completed":
        print(f"[INFO] Evento ignorado: {event_type}")
        return {"received": True}

    session_id = obj.get("id")
    payment_status = obj.get("payment_status", "")
    customer_email = obj.get("customer_email", "")

    if not session_id:
        print("[ERRO] session_id ausente no evento")
        raise HTTPException(status_code=400, detail="session_id ausente")

    pagamento = obter_pagamento_por_session_id(session_id)

    if not pagamento:
        print(f"[INFO] Pagamento não encontrado no banco para session_id={session_id}")
        return {"received": True, "warning": "pagamento não encontrado no banco"}

    if payment_status != "paid":
        print(f"[INFO] Evento recebido mas payment_status={payment_status}")
        return {"received": True}

    ok = marcar_pagamento_como_pago(session_id, payment_status)
    if not ok:
        print("[ERRO] Falha ao atualizar pagamento no Supabase")
        raise HTTPException(status_code=500, detail="Falha ao atualizar pagamento")

    print(f"[OK] Pagamento confirmado: {session_id} | email={customer_email}")

    nome_cliente = f"{pagamento.get('nome', '')} {pagamento.get('apelido', '')}".strip()
    email_cliente = pagamento.get("email", "")
    itinerario_pg = pagamento.get("itinerario", "")
    companhia_pg = pagamento.get("companhia", "")
    moeda_pg = pagamento.get("moeda_exibida", "€")
    preco_pg = pagamento.get("preco_exibido", "0")

    html_pagamento = montar_email_pagamento_recebido(
        nome_cliente=nome_cliente if nome_cliente else "Cliente",
        itinerario=itinerario_pg,
        companhia=companhia_pg,
        valor_total=f"{moeda_pg} {preco_pg}",
    )

    enviado = enviar_email(
        destinatario=email_cliente,
        assunto="Pagamento confirmado • Reserva em processamento",
        corpo_html=html_pagamento,
    )

    if enviado:
        print(f"[OK] Email de pagamento enviado para {email_cliente}")
    else:
        print(f"[ERRO] Falha ao enviar email de pagamento para {email_cliente}")

    emissao_status = (pagamento.get("emissao_status") or "pendente").lower()
    if emissao_status == "emitido":
        print(f"[INFO] Bilhete já emitido anteriormente para session_id={session_id}")
        return {"received": True}

    data_nascimento = pagamento.get("data_nascimento")
    if not data_nascimento:
        marcar_emissao_status(session_id, "erro")
        print("[ERRO] data_nascimento ausente no pagamento")
        return {"received": True, "emissao": "erro", "detalhe": "data_nascimento ausente"}

    marcar_emissao_status(session_id, "processando")

    dados_ordem, erro_emissao = emitir_bilhete_duffel(pagamento)

    if erro_emissao:
        marcar_emissao_status(session_id, "erro")
        print(f"[ERRO] Falha na emissão Duffel: {erro_emissao}")
        return {"received": True, "emissao": "erro", "detalhe": erro_emissao}

    pnr = dados_ordem.get("booking_reference", "")
    documentos = dados_ordem.get("documents", [])
    pdf_url = documentos[0]["url"] if documentos else ""

    marcar_emissao_status(session_id, "emitido", pnr=pnr, pdf_url=pdf_url)

    salvar_reserva_db(
        nome_completo=f"{pagamento.get('nome', '')} {pagamento.get('apelido', '')}".strip(),
        email=pagamento.get("email", ""),
        pnr=pnr,
        itinerario=pagamento.get("itinerario", ""),
        valor=f"{moeda_pg} {preco_pg}",
        link_pdf=pdf_url,
    )

    email_bilhete_ja_enviado = bool(pagamento.get("email_bilhete_enviado", False))
    if email_bilhete_ja_enviado:
        print(f"[INFO] Email de bilhete já tinha sido enviado para {email_cliente}")
        return {"received": True}

    trechos = pagamento.get("trechos_json") or []
    bagagem_info = None

    html_bilhete = montar_email_bilhete_emitido(
        nome_passageiro=f"{pagamento.get('nome', '')} {pagamento.get('apelido', '')}".strip(),
        pnr=pnr,
        companhia=companhia_pg,
        itinerario=itinerario_pg,
        valor_total=f"{moeda_pg} {preco_pg}",
        trechos=trechos,
        bagagem_info=bagagem_info,
        pdf_url=pdf_url,
    )

    enviado_bilhete = enviar_email(
        destinatario=email_cliente,
        assunto=f"Bilhete emitido com sucesso • PNR {pnr}",
        corpo_html=html_bilhete,
    )

    if enviado_bilhete:
        marcar_email_bilhete_enviado(session_id)
        print(f"[OK] Email de bilhete enviado para {email_cliente}")
    else:
        print(f"[ERRO] Falha ao enviar email de bilhete para {email_cliente}")

    return {"received": True}
