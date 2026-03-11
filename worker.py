import os
import requests
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configurações via Environment Variables (GitHub Secrets)
DUFFEL_TOKEN = os.getenv("DUFFEL_TOKEN")
SHEET_URL = os.getenv("SHEET_URL")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

def enviar_alerta_mudanca(email_destino, itinerario, preco_antigo, preco_novo, moeda, link):
    print(f"📧 A preparar e-mail para {email_destino}...")
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = email_destino
    
    # Lógica de variação de preço
    if preco_novo < preco_antigo:
        msg['Subject'] = f"📉 BAIXOU! {itinerario}"
        status = "Boas notícias! O preço do teu voo baixou! 😍"
    elif preco_novo > preco_antigo:
        msg['Subject'] = f"📈 SUBIU: {itinerario}"
        status = "Aviso: O preço do teu voo aumentou. 😬"
    else:
        print("ℹ️ Preço sem alteração significativa.")
        return

    corpo = (f"Olá!\n\n{status}\n"
             f"📍 Itinerário: {itinerario}\n"
             f"💰 Antes: {moeda} {preco_antigo:.2f}\n"
             f"💰 Agora: {moeda} {preco_novo:.2f}\n\n"
             f"🔗 Ver no site e reservar: {link}\n\n"
             f"Bons voos,\nEquipa Flight Monitor")
    
    msg.attach(MIMEText(corpo, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ Notificação enviada para {email_destino}!")
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")

def monitorar():
    print("🤖 Robô Flight Monitor acordou!")
    try:
        df = pd.read_csv(SHEET_URL)
        # Limpar nomes de colunas (remover espaços invisíveis)
        df.columns = df.columns.str.strip()
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
            # 1. Limpeza e conversão do Preço Inicial
            preco_limpo = str(row['preco_inicial']).replace(' ', '').replace(',', '.')
            preco_base = float(preco_limpo)
            
            # 2. Configuração Dinâmica de Passageiros
            # Se a coluna não existir ou estiver vazia, assume 1 adulto
            n_adultos = int(row['adultos']) if pd.notnull(row.get('adultos')) else 1
            n_criancas = int(row['criancas']) if pd.notnull(row.get('criancas')) else 0
            n_bebes = int(row['bebes']) if pd.notnull(row.get('bebes')) else 0
            
            pax_list = []
            for _ in range(n_adultos): pax_list.append({"type": "adult"})
            for _ in range(n_criancas): pax_list.append({"type": "child"})
            for _ in range(n_bebes): pax_list.append({"type": "infant"})

            print(f"🔎 A verificar: {row['itinerario']} ({n_adultos} Ad, {n_criancas} Cr, {n_bebes} Be)")
            
            # 3. Payload para a API
            payload = {
                "data": {
                    "slices": [{"origin": row['origem'], "destination": row['destino'], "departure_date": row['data']}],
                    "passengers": pax_list,
                    "requested_currencies": ["BRL" if row['moeda'] == "R$" else "EUR"]
                }
            }
            
            # Criar requisição de oferta
            res = requests.post("https://api.duffel.com/air/offer_requests", headers=headers, json=payload)
            
            if res.status_code == 201:
                res_json = res.json()
                offer_id = res_json['data']['id']
                
                # Buscar as ofertas reais ordenadas por preço
                offers_res = requests.get(
                    f"https://api.duffel.com/air/offers?offer_request_id={offer_id}&sort=total_amount", 
                    headers=headers
                )
                offers = offers_res.json().get("data", [])
                
                if offers:
                    preco_atual = float(offers[0]["total_amount"])
                    link_site = f"https://flightmonitorec.streamlit.app/?origem={row['origem']}&destino={row['destino']}&data={row['data']}"
                    
                    enviar_alerta_mudanca(
                        row['email'], 
                        row['itinerario'], 
                        preco_base, 
                        preco_atual, 
                        row['moeda'], 
                        link_site
                    )
                else:
                    print(f"⚠️ Sem voos disponíveis para este grupo em {row['itinerario']}")
            else:
                print(f"❌ Erro API Duffel ({res.status_code}) para {row['itinerario']}")

        except Exception as e:
            print(f"⚠️ Pulei uma linha devido a erro: {e}")
            continue

if __name__ == "__main__":
    monitorar()