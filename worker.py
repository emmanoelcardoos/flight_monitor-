import requests
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# O GitHub vai ler estas variáveis dos "Actions Secrets" que configuraste
DUFFEL_TOKEN = os.getenv("DUFFEL_TOKEN")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SHEET_URL = os.getenv("SHEET_URL") # Link CSV da planilha (Publicar na Web)

def enviar_alerta_mudanca(email_destino, itinerario, preco_antigo, preco_novo, moeda, link):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = email_destino
    
    # Lógica de Assunto do E-mail
    if preco_novo < preco_antigo:
        msg['Subject'] = f"📉 BAIXOU! {itinerario}"
        status_msg = "🌟 Boas notícias! O preço do seu voo baixou!"
    elif preco_novo > preco_antigo:
        msg['Subject'] = f"📈 SUBIU: {itinerario}"
        status_msg = "Atenção: O preço do seu voo aumentou ligeiramente."
    else:
        return # Se o preço for igual, o robô não incomoda o utilizador

    corpo = f"""
    Olá! Este é o seu assistente automático do Flight Monitor GDS.
    
    {status_msg}
    
    📍 Itinerário: {itinerario}
    💰 Preço anterior: {moeda} {preco_antigo:.2f}
    🔥 Preço ATUAL: {moeda} {preco_novo:.2f}
    
    Para ver os detalhes ou reservar, clique aqui:
    🔗 {link}
    
    Boa viagem!
    """
    msg.attach(MIMEText(corpo, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ E-mail enviado para {email_destino}")
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")

def monitorar():
    print("🤖 Robô acordou! A ler alertas da planilha...")
    # Lê a planilha publicada como CSV
    try:
        df = pd.read_csv(SHEET_URL)
    except Exception as e:
        print(f"❌ Erro ao ler planilha: {e}")
        return

    headers = {
        "Authorization": f"Bearer {DUFFEL_TOKEN}",
        "Duffel-Version": "v2",
        "Content-Type": "application/json"
    }

    for _, row in df.iterrows():
        print(f"🔎 A verificar: {row['itinerario']}...")
        
        # Payload para a Duffel
        payload = {
            "data": {
                "slices": [{"origin": row['origem'], "destination": row['destino'], "departure_date": row['data']}],
                "passengers": [{"type": "adult"}],
                "requested_currencies": ["BRL" if row['moeda'] == "R$" else "EUR"]
            }
        }
        
        res = requests.post("https://api.duffel.com/air/offer_requests", headers=headers, json=payload)
        
        if res.status_code == 201:
            offers = requests.get(f"https://api.duffel.com/air/offers?offer_request_id={res.json()['data']['id']}&sort=total_amount", headers=headers).json().get("data", [])
            
            if offers:
                preco_atual = float(offers[0]["total_amount"])
                link_site = f"https://flightmonitorec.streamlit.app/?origem={row['origem']}&destino={row['destino']}&data={row['data']}"
                
                # Dispara o e-mail se houver diferença de preço
                enviar_alerta_mudanca(row['email'], row['itinerario'], float(row['preco_inicial']), preco_atual, row['moeda'], link_site)
            else:
                print(f"⚠️ Sem voos encontrados para {row['itinerario']}")

if __name__ == "__main__":
    monitorar()