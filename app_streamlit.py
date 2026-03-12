import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from streamlit_gsheets import GSheetsConnection

# 1. Configuração da Página (Simples e Direta)
st.set_page_config(page_title="Flight Monitor GDS", page_icon="✈️", layout="centered")

# --- FUNÇÕES DE LÓGICA (SEM ALTERAÇÕES) ---
def get_exchange_rate():
    try:
        res = requests.get("https://open.er-api.com/v6/latest/EUR")
        return res.json()["rates"]["BRL"]
    except: return 6.15

def guardar_alerta_planilha(dados):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        colunas_certas = ["email", "itinerario", "origem", "destino", "data", "data_volta", "adultos", "criancas", "bebes", "preco_inicial", "moeda"]
        df_atual = conn.read(worksheet="Página1", ttl=0)
        df_atual = df_atual.reindex(columns=colunas_certas) if not df_atual.empty else pd.DataFrame(columns=colunas_certas)
        novo_dado = pd.DataFrame([dados]).reindex(columns=colunas_certas)
        df_final = pd.concat([df_atual, novo_dado], ignore_index=True)
        conn.update(worksheet="Página1", data=df_final)
        st.cache_data.clear() 
        return True
    except: return False

# --- INTERFACE BÁSICA (PRETO NATIVO) ---
st.title("✈️ Flight Monitor GDS")
st.write("Buscador de voos e monitorização de preços.")

# Dados
cidades = {
    "Portugal": {"Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO"},
    "Brasil": {"São Paulo (GRU)": "GRU", "Rio de Janeiro (GIG)": "GIG"},
    "Mundo": {"Madrid (MAD)": "MAD", "Paris (CDG)": "CDG", "Miami (MIA)": "MIA"}
}
mapa_iata = {}
opcoes = ["Selecione..."]
for regiao, items in cidades.items():
    for nome, iata in items.items():
        mapa_iata[nome] = iata
        opcoes.append(nome)

# --- FORMULÁRIO DE BUSCA ---
with st.form("busca_voos"):
    tipo_v = st.radio("Tipo de Viagem", ["Ida e volta", "Somente ida"], horizontal=True)
    
    col1, col2 = st.columns(2)
    with col1:
        origem_sel = st.selectbox("Origem", opcoes)
    with col2:
        destino_sel = st.selectbox("Destino", opcoes)
        
    col3, col4 = st.columns(2)
    with col3:
        data_ida = st.date_input("Data de Ida", value=datetime.today())
    with col4:
        data_volta = st.date_input("Data de Volta", value=datetime.today() + timedelta(days=7)) if tipo_v == "Ida e volta" else None

    st.write("Passageiros")
    c_ad, c_cr, c_be = st.columns(3)
    adultos = c_ad.number_input("Adultos", 1, 9, 1)
    criancas = c_cr.number_input("Crianças", 0, 9, 0)
    bebes = c_be.number_input("Bebés", 0, adultos, 0)

    moeda_pref = st.selectbox("Moeda de Preferência", ["Euro (€)", "Real (R$)"])
    
    btn_pesquisar = st.form_submit_button("PESQUISAR VOOS")

# --- LÓGICA DE EXECUÇÃO ---
if btn_pesquisar:
    if "Selecione" in origem_sel or "Selecione" in destino_sel:
        st.error("Por favor, selecione origem e destino.")
    else:
        try:
            with st.spinner('A pesquisar ofertas...'):
                api_token = st.secrets.get("DUFFEL_TOKEN")
                headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                is_br = "Real" in moeda_pref
                cotacao = get_exchange_rate()
                
                pax_list = [{"type": "adult"}] * adultos + [{"type": "child"}] * criancas + [{"type": "infant"}] * bebes
                iata_origem, iata_dest = mapa_iata[origem_sel], mapa_iata[destino_sel]
                
                slices = [{"origin": iata_origem, "destination": iata_dest, "departure_date": str(data_ida)}]
                if data_volta:
                    slices.append({"origin": iata_dest, "destination": iata_origem, "departure_date": str(data_volta)})

                payload = {"data": {"slices": slices, "passengers": pax_list, "requested_currencies": ["BRL" if is_br else "EUR"]}}
                res = requests.post("https://api.duffel.com/air/offer_requests", headers=headers, json=payload)
                
                if res.status_code == 201:
                    offers = requests.get(f"https://api.duffel.com/air/offers?offer_request_id={res.json()['data']['id']}&sort=total_amount", headers=headers).json().get("data", [])
                    if offers:
                        o = offers[0]
                        st.session_state.voos = [{
                            "Companhia": o["owner"]["name"],
                            "Preço": float(o["total_amount"]),
                            "Símbolo": "R$" if is_br else "€",
                            "Link": f"https://www.skyscanner.pt/transport/flights/{iata_origem}/{iata_dest}/{data_ida.strftime('%y%m%d')}"
                        }]
                        st.session_state.itinerario = f"{origem_sel} para {destino_sel}"
                        st.success("Voos encontrados!")
                    else:
                        st.warning("Nenhum voo encontrado para esta data.")
        except Exception as e:
            st.error(f"Erro na pesquisa: {e}")

# --- RESULTADOS ---
if "voos" in st.session_state:
    st.divider()
    st.subheader("Melhor Oferta")
    df = pd.DataFrame(st.session_state.voos)
    simb = st.session_state.voos[0]["Símbolo"]
    
    st.dataframe(df, column_config={
        "Preço": st.column_config.NumberColumn("Preço", format=f"{simb} %.2f"),
        "Link": st.column_config.LinkColumn("Reservar", display_text="Abrir Skyscanner ✈️")
    }, use_container_width=True, hide_index=True)

    # Alerta
    with st.expander("🔔 Ativar Alerta de Preço"):
        email = st.text_input("Teu E-mail")
        if st.button("Guardar Alerta"):
            if "@" in email:
                dados = {
                    "email": email, "itinerario": st.session_state.itinerario,
                    "origem": mapa_iata[origem_sel], "destino": mapa_iata[destino_sel],
                    "data": str(data_ida), "data_volta": str(data_volta) if data_volta else "",
                    "adultos": adultos, "criancas": criancas, "bebes": bebes,
                    "preco_inicial": st.session_state.voos[0]["Preço"], "moeda": simb
                }
                if guardar_alerta_planilha(dados):
                    st.success("Alerta guardado com sucesso!")
            else:
                st.error("E-mail inválido.")