import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# 1. Configuração da Página
st.set_page_config(page_title="Flight Monitor GDS", page_icon="✈️", layout="centered")

# --- INICIALIZAÇÃO DE ESTADOS ---
if 'pagina' not in st.session_state:
    st.session_state.pagina = "busca" # Controla se mostra busca ou reserva
if 'voo_selecionado' not in st.session_state:
    st.session_state.voo_selecionado = None

# --- FUNÇÕES DE LÓGICA ---
def get_exchange_rate():
    try:
        res = requests.get("https://open.er-api.com/v6/latest/EUR")
        return res.json()["rates"]["BRL"]
    except: return 6.15

# --- PÁGINA 1: BUSCA E RESULTADOS ---
if st.session_state.pagina == "busca":
    st.title("✈️ Flight Monitor GDS")
    
    tipo_v = st.radio("Tipo de Viagem", ["Ida e volta", "Somente ida"], horizontal=True)

    with st.form("busca_voos"):
        # (Mantendo a tua lista de cidades e colunas aqui...)
        col1, col2 = st.columns(2)
        with col1: origem_sel = st.selectbox("Origem", ["LIS", "OPO", "GRU", "GIG", "BSB"]) # Exemplo simplificado
        with col2: destino_sel = st.selectbox("Destino", ["LIS", "OPO", "GRU", "GIG", "BSB"])
        
        col3, col4 = st.columns(2)
        with col3: data_ida = st.date_input("Partida", value=datetime.today())
        with col4:
            if tipo_v == "Ida e volta":
                data_volta = st.date_input("Regresso", value=datetime.today() + timedelta(days=7))
            else:
                data_volta = None
                st.write("📅 Regresso: N/A")

        btn_pesquisar = st.form_submit_button("PESQUISAR VOOS")

    if btn_pesquisar:
        # Aqui fazemos a chamada à Duffel (simplificada para o exemplo)
        # IMPORTANTE: Guardar o offer_id real para a reserva
        st.session_state.resultados = [
            {"id": "off_123", "Companhia": "TAP Air Portugal", "Preço": 450.00, "Símbolo": "€"},
            {"id": "off_456", "Companhia": "Azul Airlines", "Preço": 2800.00, "Símbolo": "R$"}
        ]

    if "resultados" in st.session_state:
        st.divider()
        st.subheader("Melhores Ofertas")
        
        for voo in st.session_state.resultados:
            col_info, col_btn = st.columns([4, 1])
            with col_info:
                st.write(f"**{voo['Companhia']}** - {voo['Símbolo']} {voo['Preço']}")
            with col_btn:
                if st.button(f"Escolher", key=voo['id']):
                    st.session_state.voo_selecionado = voo
                    st.session_state.pagina = "reserva" # MUDA A PÁGINA
                    st.rerun()

# --- PÁGINA 2: FORMULÁRIO DE DADOS (RESERVA) ---
elif st.session_state.pagina == "reserva":
    st.title("📝 Detalhes da Reserva")
    voo = st.session_state.voo_selecionado
    
    st.info(f"Voo selecionado: **{voo['Companhia']}** | Total: **{voo['Símbolo']} {voo['Preço']}**")
    
    if st.button("⬅️ Voltar aos resultados"):
        st.session_state.pagina = "busca"
        st.rerun()

    with st.form("dados_passageiro"):
        st.subheader("Dados do Passageiro Principal")
        c1, c2 = st.columns(2)
        with c1:
            nome = st.text_input("Nome próprio")
            apelido = st.text_input("Apelido")
        with c2:
            email = st.text_input("E-mail")
            telefone = st.text_input("Telefone")
        
        data_nasc = st.date_input("Data de Nascimento", value=datetime(1990, 1, 1))
        genero = st.selectbox("Género", ["m", "f", "u"])

        st.warning("⚠️ Ao clicar em confirmar, a reserva será processada via Duffel API.")
        confirmar = st.form_submit_button("FINALIZAR E EMITIR RESERVA")

    if confirmar:
        # Lógica final de st.secrets e requests.post("https://api.duffel.com/air/orders"...)
        st.success("🎉 Reserva concluída com sucesso! Verifique o seu e-mail.")
        if st.button("Fazer nova busca"):
            st.session_state.pagina = "busca"
            st.rerun()