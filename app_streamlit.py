import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DE NEGÓCIO ---
COMISSAO_PERCENTUAL = 0.10  
# ------------------------------

st.set_page_config(page_title="Flight Monitor GDS - REAL BOOKING", page_icon="✈️", layout="centered")

# --- INICIALIZAÇÃO DE ESTADOS ---
if 'pagina' not in st.session_state:
    st.session_state.pagina = "busca"
if 'voo_selecionado' not in st.session_state:
    st.session_state.voo_selecionado = None
if 'resultados_voos' not in st.session_state:
    st.session_state.resultados_voos = []

# --- PÁGINA 1: BUSCA E RESULTADOS ---
if st.session_state.pagina == "busca":
    st.title("✈️ Flight Monitor GDS")
    st.markdown("##### Reservas Reais via Duffel API")

    # LISTA DE CIDADES COMPLETA (Mantida conforme solicitado)
    cidades = {
        "Brasil - Sudeste": {"São Paulo (GRU)": "GRU", "São Paulo (CGH)": "CGH", "Campinas (VCP)": "VCP", "Rio de Janeiro (GIG)": "GIG", "Rio de Janeiro (SDU)": "SDU", "Belo Horizonte (CNF)": "CNF", "Vitória (VIX)": "VIX"},
        "Brasil - Sul": {"Curitiba (CWB)": "CWB", "Florianópolis (FLN)": "FLN", "Porto Alegre (POA)": "POA", "Foz do Iguaçu (IGU)": "IGU", "Navegantes (NVT)": "NVT", "Londrina (LDB)": "LDB"},
        "Brasil - Centro-Oeste": {"Brasília (BSB)": "BSB", "Goiânia (GYN)": "GYN", "Cuiabá (CGB)": "CGB", "Campo Grande (CGR)": "CGR"},
        "Brasil - Nordeste": {"Salvador (SSA)": "SSA", "Recife (REC)": "REC", "Fortaleza (FOR)": "FOR", "Natal (NAT)": "NAT", "Maceió (MCZ)": "MCZ", "João Pessoa (JPA)": "JPA", "Aracaju (AJU)": "AJU", "Porto Seguro (BPS)": "BPS", "Ilhéus (IOS)": "IOS"},
        "Brasil - Norte": {"Manaus (MAO)": "MAO", "Belém (BEL)": "BEL", "Porto Velho (PVH)": "PVH", "Rio Branco (RBR)": "RBR", "Macapá (MCP)": "MCP", "Boa Vista (BVB)": "BVB", "Palmas (PMW)": "PMW", "Marabá (MAB)": "MAB", "Parauapebas / Carajás (CKS)": "CKS", "Araguaína (AUX)": "AUX"},
        "Portugal": {"Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO", "Funchal (FNC)": "FNC", "Ponta Delgada (PDL)": "PDL"},
        "Europa": {"Madrid (MAD)": "MAD", "Barcelona (BCN)": "BCN", "Paris (CDG)": "CDG", "Londres (LHR)": "LHR", "Roma (FCO)": "FCO", "Frankfurt (FRA)": "FRA", "Istambul (IST)": "IST"},
        "Estados Unidos": {"Miami (MIA)": "MIA", "Orlando (MCO)": "MCO", "Nova York (JFK)": "JFK", "Boston (BOS)": "BOS"},
        "África": {"Luanda (LAD)": "LAD", "Joanesburgo (JNB)": "JNB", "Cidade do Cabo (CPT)": "CPT", "Casablanca (CMN)": "CMN"}
    }

    mapa_iata = {}
    opcoes_lista = ["Selecione..."]
    for regiao, items in cidades.items():
        for nome, iata in items.items():
            mapa_iata[nome] = iata
            opcoes_lista.append(nome)

    tipo_v = st.radio("Tipo de Viagem", ["Ida e volta", "Somente ida"], horizontal=True)

    with st.form("busca_voos_v4"):
        col1, col2 = st.columns(2)
        origem_sel = col1.selectbox("Origem", opcoes_lista)
        destino_sel = col2.selectbox("Destino", opcoes_lista)
        
        col3, col4 = st.columns(2)
        data_ida = col3.date_input("Data de Partida", value=datetime.today())
        if tipo_v == "Ida e volta":
            data_volta = col4.date_input("Data de Regresso", value=datetime.today() + timedelta(days=7))
        else:
            col4.write("📅 Regresso: N/A")
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
            st.error("Selecione origem e destino.")
        else:
            try:
                with st.spinner('A processar tarifas reais...'):
                    api_token = st.secrets.get("DUFFEL_TOKEN")
                    headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                    is_br = "Real" in moeda_pref
                    
                    pax_list = [{"type": "adult"}] * adultos + [{"type": "child"}] * criancas + [{"type": "infant"}] * bebes
                    iata_origem, iata_dest = mapa_iata[origem_sel], mapa_iata[destino_sel]
                    
                    slices = [{"origin": iata_origem, "destination": iata_dest, "departure_date": str(data_ida)}]
                    if data_volta:
                        slices.append({"origin": iata_dest, "destination": iata_origem, "departure_date": str(data_volta)})

                    payload = {"data": {"slices": slices, "passengers": pax_list, "requested_currencies": ["BRL" if is_br else "EUR"]}}
                    res = requests.post("https://api.duffel.com/air/offer_requests", headers=headers, json=payload)
                    
                    if res.status_code == 201:
                        data_res = res.json()["data"]
                        offers = data_res.get("offers", [])
                        pax_ids_res = [p["id"] for p in data_res.get("passengers", [])]
                        
                        st.session_state.resultados_voos = []
                        for o in offers[:5]:
                            detalhes_voo = []
                            for slice_obj in o["slices"]:
                                for segment in slice_obj["segments"]:
                                    detalhes_voo.append({
                                        "origem": segment["origin"]["iata_code"],
                                        "destino": segment["destination"]["iata_code"],
                                        "saida": segment["departing_at"],
                                        "chegada": segment["arriving_at"],
                                        "cia": segment["marketing_carrier"]["name"],
                                        "aviao": segment["aircraft"]["name"] if segment["aircraft"] else "N/D"
                                    })
                            
                            bagagem_info = "Só mala de mão"
                            if o["passengers"][0].get("baggages"):
                                malas_porao = [b for b in o["passengers"][0]["baggages"] if b["type"] == "checked"]
                                if malas_porao:
                                    bagagem_info = f"Inclui {malas_porao[0]['quantity']} mala(s) de porão"

                            preco_venda = float(o["total_amount"]) * (1 + COMISSAO_PERCENTUAL)

                            st.session_state.resultados_voos.append({
                                "id_offer": o["id"],
                                "pax_ids": pax_ids_res,
                                "Companhia": o["owner"]["name"],
                                "Preço": preco_venda,
                                "Moeda": "R$" if is_br else "€",
                                "Segmentos": detalhes_voo,
                                "Bagagem": bagagem_info
                            })
                        st.success("Tarifas atualizadas.")
            except Exception as e: st.error(f"Erro: {e}")

    if st.session_state.resultados_voos:
        st.divider()
        for v in st.session_state.resultados_voos:
            with st.expander(f"✈️ {v['Companhia']} - {v['Moeda']} {v['Preço']:.2f}"):
                st.info(f"💼 **Bagagem:** {v['Bagagem']}")
                for seg in v["Segmentos"]:
                    st.write(f"📍 **{seg['origem']} → {seg['destino']}** ({seg['cia']})")
                    st.caption(f"🕒 Saída: {seg['saida']} | Chegada: {seg['chegada']}")
                    st.markdown("---")
                
                if st.button("Reservar este Voo", key=v['id_offer']):
                    st.session_state.voo_selecionado = v
                    st.session_state.pagina = "reserva"
                    st.rerun()

# --- PÁGINA 2: RESERVA REAL ---
elif st.session_state.pagina == "reserva":
    v = st.session_state.voo_selecionado
    st.title("🏁 Finalizar Compra Real")
    st.info(f"Voo: **{v['Companhia']}** | Total: **{v['Moeda']} {v['Preço']:.2f}**")
    
    if st.button("⬅️ Alterar Voo"):
        st.session_state.pagina = "busca"
        st.rerun()

    with st.form("final_real_checkout"):
        st.subheader("👤 Dados do Passageiro")
        c1, c2 = st.columns(2)
        p_nome = c1.text_input("Primeiro Nome")
        p_sobrenome = c2.text_input("Apelido / Sobrenome")
        
        c3, c4 = st.columns(2)
        # AJUSTE DA DATA DE NASCIMENTO (1900 até 2026)
        data_nasc = c3.date_input("Data de Nascimento", 
                                  value=datetime(1990, 1, 1),
                                  min_value=datetime(1900, 1, 1),
                                  max_value=datetime.today())
        p_genero = c4.selectbox("Género", ["m", "f"])

        c5, c6 = st.columns(2)
        p_doc_tipo = c5.selectbox("Tipo de Documento", ["passport", "id_card"])
        p_doc_num = c6.text_input("Número do Documento")

        email_pax = st.text_input("E-mail para Bilhete Eletrónico")
        tel_pax = st.text_input("Telefone (com DDI, ex: +351...)")

        st.markdown("---")
        st.subheader("💳 Detalhes de Pagamento")
        num_cartao = st.text_input("Número do Cartão")
        
        col_c1, col_c2, col_c3 = st.columns([2, 1, 1])
        titular_cartao = col_c1.text_input("Nome no Cartão")
        validade_cartao = col_c2.text_input("Validade (MM/AA)")
        cvv_cartao = col_c3.text_input("CVV", type="password")

        st.caption("🔒 Ao clicar, a transação será processada via Duffel Payments.")

        if st.form_submit_button("CONFIRMAR RESERVA E PAGAR"):
            if not p_nome or not email_pax or not num_cartao:
                st.error("Todos os campos de identificação e pagamento são obrigatórios.")
            else:
                try:
                    with st.spinner('A comunicar com a companhia aérea...'):
                        api_token = st.secrets.get("DUFFEL_TOKEN")
                        headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                        
                        # MONTAGEM DA RESERVA REAL
                        pax_data = [{
                            "id": v['pax_ids'][0],
                            "given_name": p_nome,
                            "family_name": p_sobrenome,
                            "gender": p_genero,
                            "born_on": str(data_nasc),
                            "email": email_pax,
                            "phone_number": tel_pax
                        }]

                        payload_order = {
                            "data": {
                                "type": "instant",
                                "selected_offers": [v['id_offer']],
                                "passengers": pax_data,
                                "payments": [{
                                    "type": "balance", 
                                    "currency": v['Moeda'].replace("€", "EUR").replace("R$", "BRL"),
                                    "amount": str(v['Preço'])
                                }]
                            }
                        }

                        res_order = requests.post("https://api.duffel.com/air/orders", headers=headers, json=payload_order)
                        
                        if res_order.status_code == 201:
                            order = res_order.json()["data"]
                            st.balloons()
                            st.success(f"✅ BILHETE EMITIDO! PNR: **{order['booking_reference']}**")
                            st.markdown(f"Enviado para: **{email_pax}**")
                        else:
                            erro_msg = res_order.json().get("errors", [{}])[0].get("message", "Erro na emissão")
                            st.error(f"Falha na Reserva: {erro_msg}")
                except Exception as e: st.error(f"Erro técnico: {e}")