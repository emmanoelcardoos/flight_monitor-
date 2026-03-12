import smtplib
import streamlit as st

def testar():
    print("Iniciando teste...")
    try:
        usuario = st.secrets["EMAIL_USER"]
        senha = st.secrets["EMAIL_PASSWORD"]
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(usuario, senha)
        print("✅ CONEXÃO COM GOOGLE OK!")
        server.quit()
    except Exception as e:
        print(f"❌ ERRO: {e}")

testar()