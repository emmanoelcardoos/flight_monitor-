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
        # Adicionamos o parâmetro decimal=',' para ajudar o pandas, 
        # mas faremos a limpeza manual por segurança abaixo.
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
        try:
            # --- CORREÇÃO DO PREÇO ---
            # Remove espaços, troca vírgula por ponto e converte para número
            preco_limpo = str(row['preco_inicial']).replace(' ', '').replace(',', '.')
            preco_base = float(preco_limpo)
            
            print(f"🔎 A verificar: {row['itinerario']} (Preço base: {preco_base})")
            
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
                offers_data = requests.get(
                    f"https://api.duffel.com/air/offers?offer_request_id={res.json()['data']['id']}&sort=total_amount", 
                    headers=headers
                ).json().get("data", [])
                
                if offers_data:
                    preco_atual = float(offers_data[0]["total_amount"])
                    link_site = f"https://flightmonitorec.streamlit.app/?origem={row['origem']}&destino={row['destino']}&data={row['data']}"
                    
                    # Dispara o e-mail comparando com o preco_base já convertido
                    enviar_alerta_mudanca(
                        row['email'], 
                        row['itinerario'], 
                        preco_base, 
                        preco_atual, 
                        row['moeda'], 
                        link_site
                    )
                else:
                    print(f"⚠️ Sem voos encontrados para {row['itinerario']}")
            else:
                print(f"❌ Erro na API Duffel para {row['itinerario']}: {res.status_code}")

        except ValueError as ve:
            print(f"⚠️ Erro de formato no preço da linha: {row['itinerario']}. Valor recebido: {row['preco_inicial']}")
            continue # Pula para a próxima linha da planilha
        except Exception as e:
            print(f"⚠️ Erro inesperado ao processar linha: {e}")
            continue

if __name__ == "__main__":
    monitorar()