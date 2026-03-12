import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# 1. Configuração da Página
st.set_page_config(page_title="Flight Monitor GDS - Reservas", page_icon="✈️", layout="centered")

# --- INICIALIZAÇÃO DE ESTADOS ---
if 'pagina' not in st.session_state:
    st.session_state.pagina = "busca"
if 'voo_selecionado' not in st.session_state:
    st.session_state.voo_selecionado = None
if 'resultados_voos' not in st.session_state:
    st.session_state.resultados_voos = []

# --- PÁGINA DE BUSCA ---
if st.session_state.pagina == "busca":
    st.title("✈️ Reserva Direta GDS")
    
    # MANTENDO A TUA LISTA DE CIDADES COMPLETA
    cidades = {

    "Brasil - Sudeste": {
        "São Paulo (GRU)": "GRU",
        "São Paulo (CGH)": "CGH",
        "Campinas (VCP)": "VCP",
        "Rio de Janeiro (GIG)": "GIG",
        "Rio de Janeiro (SDU)": "SDU",
        "Belo Horizonte (CNF)": "CNF",
        "Belo Horizonte (PLU)": "PLU",
        "Vitória (VIX)": "VIX"
    },

    "Brasil - Sul": {
        "Curitiba (CWB)": "CWB",
        "Florianópolis (FLN)": "FLN",
        "Porto Alegre (POA)": "POA",
        "Foz do Iguaçu (IGU)": "IGU",
        "Navegantes (NVT)": "NVT",
        "Londrina (LDB)": "LDB"
    },

    "Brasil - Centro-Oeste": {
        "Brasília (BSB)": "BSB",
        "Goiânia (GYN)": "GYN",
        "Cuiabá (CGB)": "CGB",
        "Campo Grande (CGR)": "CGR"
    },

    "Brasil - Nordeste": {
        "Salvador (SSA)": "SSA",
        "Recife (REC)": "REC",
        "Fortaleza (FOR)": "FOR",
        "Natal (NAT)": "NAT",
        "Maceió (MCZ)": "MCZ",
        "João Pessoa (JPA)": "JPA",
        "Aracaju (AJU)": "AJU",
        "Porto Seguro (BPS)": "BPS",
        "Ilhéus (IOS)": "IOS"
    },

    "Brasil - Norte": {
        "Manaus (MAO)": "MAO",
        "Belém (BEL)": "BEL",
        "Porto Velho (PVH)": "PVH",
        "Rio Branco (RBR)": "RBR",
        "Macapá (MCP)": "MCP",
        "Boa Vista (BVB)": "BVB",
        "Palmas (PMW)": "PMW",
        "Marabá (MAB)": "MAB",
        "Parauapebas / Carajás (CKS)": "CKS",
        "Araguaína (AUX)": "AUX"
    },

    "Portugal": {
        "Lisboa (LIS)": "LIS",
        "Porto (OPO)": "OPO",
        "Funchal (FNC)": "FNC",
        "Ponta Delgada (PDL)": "PDL"
    },

    "Europa": {
        "Madrid (MAD)": "MAD",
        "Barcelona (BCN)": "BCN",
        "Paris (CDG)": "CDG",
        "Paris Orly (ORY)": "ORY",
        "Londres Heathrow (LHR)": "LHR",
        "Londres Gatwick (LGW)": "LGW",
        "Roma (FCO)": "FCO",
        "Milão (MXP)": "MXP",
        "Frankfurt (FRA)": "FRA",
        "Munique (MUC)": "MUC",
        "Zurique (ZRH)": "ZRH",
        "Amsterdã (AMS)": "AMS",
        "Bruxelas (BRU)": "BRU",
        "Copenhaga (CPH)": "CPH",
        "Istambul (IST)": "IST",
        "Lisboa (LIS)": "LIS",
        "Porto (OPO)": "OPO"
    },

    "Estados Unidos": {
        "Miami (MIA)": "MIA",
        "Orlando (MCO)": "MCO",
        "Fort Lauderdale (FLL)": "FLL",
        "Nova York JFK (JFK)": "JFK",
        "Nova York Newark (EWR)": "EWR",
        "Atlanta (ATL)": "ATL",
        "Dallas (DFW)": "DFW",
        "Houston (IAH)": "IAH",
        "Chicago (ORD)": "ORD",
        "Los Angeles (LAX)": "LAX",
        "San Francisco (SFO)": "SFO",
        "Washington (IAD)": "IAD",
        "Boston (BOS)": "BOS"
    },

    "África": {
        "Luanda (LAD)": "LAD",
        "Joanesburgo (JNB)": "JNB",
        "Cidade do Cabo (CPT)": "CPT",
        "Casablanca (CMN)": "CMN",
        "Addis Abeba (ADD)": "ADD"
    }
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
        btn_pesquisar = st.form_submit_button("PESQUISAR VOOS")

    if btn_pesquisar:
        if "Selecione" in origem_sel or "Selecione" in destino_sel:
            st.error("Selecione os aeroportos.")
        else:
            try:
                with st.spinner('A consultar detalhes dos voos e bagagens...'):
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
                        pax_ids = [p["id"] for p in data.get("passengers", [])]
                        
                        st.session_state.resultados_voos = []
                        for o in offers[:5]:
                            # EXTRAÇÃO DE DETALHES DE SEGMENTOS E BAGAGENS
                            itinerarios = []
                            for s_slice in o["slices"]:
                                for seg in s_slice["segments"]:
                                    itinerarios.append({
                                        "de": seg["origin"]["iata_code"],
                                        "para": seg["destination"]["iata_code"],
                                        "saida": seg["departing_at"],
                                        "chegada": seg["arriving_at"],
                                        "aviao": seg["aircraft"]["name"] if seg["aircraft"] else "N/D",
                                        "cia": seg["marketing_carrier"]["name"]
                                    })
                            
                            # Bagagem (Pegamos a do primeiro passageiro como referência)
                            bagagens = o["passengers"][0].get("baggages", [])
                            franquia = "Só mala de mão"
                            for b in bagagens:
                                if b["type"] == "checked":
                                    franquia = f"Inclui {b['quantity']} mala(s) de porão"

                            st.session_state.resultados_voos.append({
                                "id_offer": o["id"],
                                "pax_ids": pax_ids,
                                "Companhia": o["owner"]["name"],
                                "Preço": float(o["total_amount"]),
                                "Moeda": "R$" if is_br else "€",
                                "Detalhes": itinerarios,
                                "Bagagem": franquia
                            })
                        st.success("Voos encontrados com sucesso!")
            except Exception as e: st.error(f"Erro: {e}")

    # EXIBIÇÃO DOS RESULTADOS COM DETALHES
    if st.session_state.resultados_voos:
        st.divider()
        for voo in st.session_state.resultados_voos:
            with st.expander(f"✈️ {voo['Companhia']} - {voo['Moeda']} {voo['Preço']:.2f}"):
                st.write(f"💼 **Bagagem:** {voo['Bagagem']}")
                
                # Gerar linha do tempo dos trechos
                for trecho in voo["Detalhes"]:
                    st.write(f"📍 **{trecho['de']} → {trecho['para']}** ({trecho['cia']})")
                    st.caption(f"📅 Saída: {trecho['saida']} | Chegada: {trecho['chegada']}")
                    st.caption(f"✈️ Aeronave: {trecho['aviao']}")
                    st.markdown("---")
                
                if st.button("Reservar este voo", key=voo['id_offer']):
                    st.session_state.voo_selecionado = voo
                    st.session_state.pagina = "reserva"
                    st.rerun()

# --- PÁGINA DE RESERVA (CHECKOUT) ---
elif st.session_state.pagina == "reserva":
    v = st.session_state.voo_selecionado
    st.title("🏁 Checkout de Reserva")
    
    st.info(f"Voo: {v['Companhia']} | Bagagem: {v['Bagagem']}")
    
    if st.button("⬅️ Voltar"):
        st.session_state.pagina = "busca"
        st.rerun()

    with st.form("form_final"):
        st.write("Dados do Passageiro")
        col1, col2 = st.columns(2)
        p_nome = col1.text_input("Nome")
        u_nome = col2.text_input("Apelido")
        
        email = st.text_input("E-mail para Bilhete Eletrónico")
        
        if st.form_submit_button("FINALIZAR E EMITIR"):
            st.success("Reserva enviada! O seu PNR está a ser gerado.")