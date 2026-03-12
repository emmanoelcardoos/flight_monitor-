import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DE NEGÓCIO ---
COMISSAO_PERCENTUAL = 0.10  # Adiciona 10% de lucro sobre o custo da Duffel
# ------------------------------

st.set_page_config(page_title="Flight Monitor GDS - Booking", page_icon="✈️", layout="centered")

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
    st.markdown("##### Encontre e reserve voos com as melhores tarifas do mercado")

    # TODAS AS TUAS CIDADES REPOSTAS INTEGRALMENTE
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
        with col3: data_ida = st.date_input("Data de Partida", value=datetime.today())
        with col4:
            if tipo_v == "Ida e volta":
                data_volta = st.date_input("Data de Regresso", value=datetime.today() + timedelta(days=7))
            else:
                st.write("📅 Regresso: N/A (Somente ida)")
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
            st.error("Selecione origem e destino.")
        else:
            try:
                with st.spinner('A calcular as melhores tarifas...'):
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
                        data = res.json()["data"]
                        offers = data.get("offers", [])
                        pax_ids = [p["id"] for p in data.get("passengers", [])]
                        
                        st.session_state.resultados_voos = []
                        for o in offers[:8]:
                            # CÁLCULO DE PREÇO COM COMISSÃO
                            preco_custo = float(o["total_amount"])
                            preco_venda = preco_custo * (1 + COMISSAO_PERCENTUAL)
                            
                            # Detalhes de Bagagem
                            bagagem = o["passengers"][0].get("baggages", [])
                            franquia = "Só mala de mão"
                            for b in bagagem:
                                if b["type"] == "checked": franquia = f"Inclui {b['quantity']} mala(s) de porão"

                            st.session_state.resultados_voos.append({
                                "id_offer": o["id"],
                                "pax_ids": pax_ids,
                                "Companhia": o["owner"]["name"],
                                "Preço": preco_venda,
                                "Moeda": "R$" if is_br else "€",
                                "Bagagem": franquia
                            })
                        st.success(f"Encontrámos {len(offers)} voos disponíveis.")
            except Exception as e: st.error(f"Erro: {e}")

    # EXIBIÇÃO DE RESULTADOS COM BOTÃO DE RESERVA
    if st.session_state.resultados_voos:
        st.divider()
        for v in st.session_state.resultados_voos:
            with st.expander(f"✈️ {v['Companhia']} - {v['Moeda']} {v['Preço']:.2f}"):
                st.write(f"💼 Bagagem: {v['Bagagem']}")
                if st.button("Reservar Agora", key=v['id_offer']):
                    st.session_state.voo_selecionado = v
                    st.session_state.pagina = "reserva"
                    st.rerun()

# --- PÁGINA 2: CHECKOUT E PAGAMENTO ---
elif st.session_state.pagina == "reserva":
    v = st.session_state.voo_selecionado
    st.title("🏁 Finalizar Reserva")
    st.info(f"Voo: **{v['Companhia']}** | Total a Pagar: **{v['Moeda']} {v['Preço']:.2f}**")
    
    if st.button("⬅️ Alterar Escolha"):
        st.session_state.pagina = "busca"
        st.rerun()

    with st.form("checkout_final"):
        st.subheader("1. Dados do Passageiro")
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome Próprio")
        apelido = c2.text_input("Apelido")
        email = st.text_input("E-mail para envio do bilhete")
        
        st.subheader("2. Pagamento com Cartão")
        n_cartao = st.text_input("Número do Cartão", placeholder="0000 0000 0000 0000")
        col_c1, col_c2, col_c3 = st.columns([2, 1, 1])
        titular = col_c1.text_input("Nome no Cartão")
        validade = col_c2.text_input("MM/AA")
        cvv = col_c3.text_input("CVV", type="password")

        # --- DENTRO DO st.form("checkout_final") ---
        if st.form_submit_button("CONFIRMAR RESERVA E PAGAR"):
            if not nome or not email or not n_cartao:
                st.error("Preencha todos os campos obrigatórios.")
            else:
                try:
                    with st.spinner('A emitir o seu bilhete eletrónico...'):
                        api_token = st.secrets.get("DUFFEL_TOKEN")
                        headers = {
                            "Authorization": f"Bearer {api_token}",
                            "Duffel-Version": "v2",
                            "Content-Type": "application/json"
                        }

                        # 1. Montar o passageiro (seguindo a estrutura da Duffel)
                        # Nota: No modo real, teríamos de preencher todos os IDs de pax_ids
                        pax_data = [
                            {
                                "id": v['pax_ids'][0],
                                "given_name": nome,
                                "family_name": apelido,
                                "gender": "m", # Pode ser dinâmico
                                "born_on": "1990-01-01", # Pode ser dinâmico
                                "email": email,
                                "phone_number": "+351910000000"
                            }
                        ]

                        # 2. Criar a Order (Reserva Instantânea)
                        payload_order = {
                            "data": {
                                "type": "instant",
                                "selected_offers": [v['id_offer']],
                                "passengers": pax_data,
                                "payments": [
                                    {
                                        "type": "balance", # No Sandbox usamos 'balance' ou 'arc_bsp_cash'
                                        "currency": v['Moeda'].replace("€", "EUR").replace("R$", "BRL"),
                                        "amount": str(v['Preço'])
                                    }
                                ]
                            }
                        }

                        res_order = requests.post("https://api.duffel.com/air/orders", headers=headers, json=payload_order)
                        
                        if res_order.status_code == 201:
                            order = res_order.json()["data"]
                            st.balloons()
                            st.success(f"✅ Reserva Confirmada! Localizador (PNR): **{order['booking_reference']}**")
                            st.write(f"Companhia: {order['owner']['name']}")
                            st.info("No modo real, o bilhete seria agora enviado para o seu e-mail.")
                        else:
                            erro = res_order.json().get("errors", [{}])[0].get("message", "Erro desconhecido")
                            st.error(f"A companhia aérea recusou a reserva: {erro}")
                            
                except Exception as e:
                    st.error(f"Erro técnico no processamento: {e}")