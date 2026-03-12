import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# 1. Configuração da Página
st.set_page_config(page_title="Flight Monitor GDS - Reserva Direta", page_icon="✈️", layout="centered")

# --- INICIALIZAÇÃO DE ESTADOS ---
if 'pagina' not in st.session_state:
    st.session_state.pagina = "busca"
if 'voo_selecionado' not in st.session_state:
    st.session_state.voo_selecionado = None
if 'resultados_voos' not in st.session_state:
    st.session_state.resultados_voos = []

# --- INTERFACE DE BUSCA ---
if st.session_state.pagina == "busca":
    st.title("✈️ Reserva de Voos GDS")
    st.markdown("##### Reserve o seu voo diretamente connosco via Duffel")

    # TODAS AS CIDADES MANTIDAS
    cidades = {
        "Brasil - Sudeste": {"São Paulo (GRU)": "GRU", "São Paulo (CGH)": "CGH", "Campinas (VCP)": "VCP", "Rio de Janeiro (GIG)": "GIG", "Rio de Janeiro (SDU)": "SDU", "Belo Horizonte (CNF)": "CNF", "Vitória (VIX)": "VIX"},
        "Brasil - Sul": {"Curitiba (CWB)": "CWB", "Florianópolis (FLN)": "FLN", "Porto Alegre (POA)": "POA", "Foz do Iguaçu (IGU)": "IGU", "Navegantes (NVT)": "NVT"},
        "Brasil - Centro-Oeste": {"Brasília (BSB)": "BSB", "Goiânia (GYN)": "GYN", "Cuiabá (CGB)": "CGB"},
        "Brasil - Nordeste": {"Salvador (SSA)": "SSA", "Recife (REC)": "REC", "Fortaleza (FOR)": "FOR", "Natal (NAT)": "NAT", "Maceió (MCZ)": "MCZ"},
        "Brasil - Norte": {"Manaus (MAO)": "MAO", "Belém (BEL)": "BEL", "Porto Velho (PVH)": "PVH", "Marabá (MAB)": "MAB", "Macapá (MCP)": "MCP"},
        "Portugal": {"Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO", "Funchal (FNC)": "FNC", "Ponta Delgada (PDL)": "PDL"},
        "Europa": {"Madrid (MAD)": "MAD", "Barcelona (BCN)": "BCN", "Paris (CDG)": "CDG", "Londres (LHR)": "LHR", "Roma (FCO)": "FCO", "Frankfurt (FRA)": "FRA"},
        "Estados Unidos": {"Miami (MIA)": "MIA", "Orlando (MCO)": "MCO", "Nova York (JFK)": "JFK", "Boston (BOS)": "BOS"},
        "África": {"Luanda (LAD)": "LAD", "Joanesburgo (JNB)": "JNB", "Casablanca (CMN)": "CMN"}
    }

    mapa_iata = {}
    opcoes = ["Selecione..."]
    for regiao, items in cidades.items():
        for nome, iata in items.items():
            mapa_iata[nome] = iata
            opcoes.append(nome)

    tipo_v = st.radio("Tipo de Viagem", ["Ida e volta", "Somente ida"], horizontal=True)

    with st.form("busca_voos"):
        col1, col2 = st.columns(2)
        with col1: origem_sel = st.selectbox("Origem", opcoes)
        with col2: destino_sel = st.selectbox("Destino", opcoes)
        
        col3, col4 = st.columns(2)
        with col3: data_ida = st.date_input("Partida", value=datetime.today())
        with col4:
            if tipo_v == "Ida e volta":
                data_volta = st.date_input("Regresso", value=datetime.today() + timedelta(days=7))
            else:
                st.write("📅 Regresso: N/A")
                data_volta = None

        st.write("Passageiros")
        p1, p2, p3 = st.columns(3)
        adultos = p1.number_input("Adultos", 1, 9, 1)
        criancas = p2.number_input("Crianças", 0, 9, 0)
        bebes = p3.number_input("Bebés", 0, adultos, 0)

        moeda_pref = st.selectbox("Moeda", ["Euro (€)", "Real (R$)"])
        btn_pesquisar = st.form_submit_button("PESQUISAR VOOS DISPONÍVEIS")

    if btn_pesquisar:
        if "Selecione" in origem_sel or "Selecione" in destino_sel:
            st.error("Por favor, selecione os aeroportos.")
        else:
            try:
                with st.spinner('A consultar disponibilidade em tempo real...'):
                    api_token = st.secrets.get("DUFFEL_TOKEN")
                    headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                    is_br = "Real" in moeda_pref
                    
                    pax_list = [{"type": "adult"}] * adultos + [{"type": "child"}] * criancas + [{"type": "infant"}] * bebes
                    
                    slices = [{"origin": mapa_iata[origem_sel], "destination": mapa_iata[destino_sel], "departure_date": str(data_ida)}]
                    if data_volta:
                        slices.append({"origin": mapa_iata[destino_sel], "destination": mapa_iata[origem_sel], "departure_date": str(data_volta)})

                    payload = {"data": {"slices": slices, "passengers": pax_list, "requested_currencies": ["BRL" if is_br else "EUR"]}}
                    res = requests.post("https://api.duffel.com/air/offer_requests", headers=headers, json=payload)
                    
                    if res.status_code == 201:
                        data = res.json().get("data", {})
                        offers = data.get("offers", [])
                        # Guardamos o ID dos passageiros criado pela Duffel para a reserva posterior
                        pax_ids = [p["id"] for p in data.get("passengers", [])]
                        
                        if offers:
                            st.session_state.resultados_voos = []
                            for o in offers[:8]: # Mostra até 8 opções
                                st.session_state.resultados_voos.append({
                                    "id_offer": o["id"],
                                    "pax_ids": pax_ids,
                                    "Companhia": o["owner"]["name"],
                                    "Preço": float(o["total_amount"]),
                                    "Moeda": "R$" if is_br else "€"
                                })
                            st.success(f"Encontrámos {len(offers)} opções de reserva direta.")
            except Exception as e: st.error(f"Erro na conexão: {e}")

    # RESULTADOS APENAS COM BOTÃO DE RESERVA
    if st.session_state.resultados_voos:
        st.divider()
        for voo in st.session_state.resultados_voos:
            with st.container():
                c1, c2 = st.columns([4, 1])
                c1.write(f"✈️ **{voo['Companhia']}**")
                c1.write(f"Preço Final: {voo['Moeda']} {voo['Preço']:.2f}")
                if c2.button("Reservar", key=voo['id_offer']):
                    st.session_state.voo_selecionado = voo
                    st.session_state.pagina = "reserva"
                    st.rerun()
                st.divider()

# --- PÁGINA DE CHECKOUT (DADOS DO PASSAGEIRO) ---
elif st.session_state.pagina == "reserva":
    v = st.session_state.voo_selecionado
    st.title("🏁 Finalizar a sua Reserva")
    st.subheader(f"Voo {v['Companhia']} - Total: {v['Moeda']} {v['Preço']}")
    
    if st.button("⬅️ Alterar Voo"):
        st.session_state.pagina = "busca"
        st.rerun()

    with st.form("checkout_duffel"):
        st.info("Insira os dados exatamente como constam no passaporte.")
        
        # Exemplo para 1 passageiro (pode ser expandido com um loop para v['pax_ids'])
        col1, col2 = st.columns(2)
        with col1:
            primeiro_nome = st.text_input("Primeiro Nome")
            ultimo_nome = st.text_input("Apelido (Sobrenome)")
        with col2:
            data_nasc = st.date_input("Data de Nascimento", value=datetime(1990, 1, 1))
            genero = st.selectbox("Género", ["Masculino", "Feminino"])

        email_contato = st.text_input("E-mail para envio do bilhete")
        tel_contato = st.text_input("Telefone de contacto")

        st.warning("⚠️ Ao confirmar, a reserva será processada oficialmente.")
        if st.form_submit_button("CONFIRMAR E PAGAR"):
            # Aqui entrará o código final: requests.post("https://api.duffel.com/air/orders"...)
            st.balloons()
            st.success("Reserva enviada com sucesso! O seu localizador PNR será gerado em instantes.")