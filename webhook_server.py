import os
from datetime import datetime

import stripe
from fastapi import FastAPI, Header, HTTPException, Request
from supabase import create_client

app = FastAPI()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)


def marcar_pagamento_como_pago(session_id: str, stripe_payment_status: str = "paid"):
    supabase.table("pagamentos").update({
        "status_pagamento": "PAGO",
        "stripe_payment_status": stripe_payment_status,
        "data_confirmacao": datetime.utcnow().isoformat(),
    }).eq("session_id", session_id).execute()


def obter_pagamento_por_session_id(session_id: str):
    resp = (
        supabase.table("pagamentos")
        .select("*")
        .eq("session_id", session_id)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


@app.get("/")
def home():
    return {"status": "ok", "service": "stripe-webhook-server"}


@app.post("/stripe-webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature")
):
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Stripe-Signature em falta")

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=stripe_webhook_secret,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Payload inválido")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Assinatura inválida")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session.get("id")
        payment_status = session.get("payment_status", "")
        customer_email = session.get("customer_email", "")

        if session_id and payment_status == "paid":
            marcar_pagamento_como_pago(session_id, payment_status)

            pagamento = obter_pagamento_por_session_id(session_id)

            # por enquanto só confirma no banco
            # depois vamos adicionar:
            # 1) email automático
            # 2) emissão automática
            print("Pagamento confirmado:", session_id, customer_email, pagamento)

    return {"received": True}