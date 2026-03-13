import os
import smtplib
from pathlib import Path
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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

    if event_type == "checkout.session.completed":
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

        if str(pagamento.get("status_pagamento", "")).upper() == "PAGO":
            print(f"[INFO] Pagamento já confirmado anteriormente: {session_id}")
            return {"received": True, "status": "already_paid"}

        if payment_status == "paid":
            ok = marcar_pagamento_como_pago(session_id, payment_status)

            if ok:
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
            else:
                print("[ERRO] Falha ao atualizar pagamento no Supabase")
                raise HTTPException(status_code=500, detail="Falha ao atualizar pagamento")
        else:
            print(f"[INFO] Evento recebido mas payment_status={payment_status}")

    else:
        print(f"[INFO] Evento ignorado: {event_type}")

    return {"received": True}