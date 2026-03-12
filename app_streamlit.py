import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# 1. Configuração da Página
st.set_page_config(page_title="Flight Monitor GDS", page_icon="✈️", layout="centered")

# --- FUNÇÕES DE LÓGICA ---
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

def gerar_info_reserva(companhia, origem, destino, data_ida, is_br):
    suffix = "com.br" if is_br else "pt"
    data_sky = data_ida.strftime("%y%m%d")
    
    links_cia = {
        "TAP Air Portugal": f"https://www.flytap.com/{suffix}",
        "Azul Brazilian Airlines": "https://www.voeazul.com.br",
        "LATAM Airlines": f"https://www.latamairlines.com/{suffix}",
        "Gol Linhas Aéreas": "https://www.voegol.com.br",
        "Lufthansa": f"https://www.lufthansa.com/{suffix}",
        "Air France": f"https://www.airfrance.{suffix}",
        "Iberia": f"https://www.iberia.com/{suffix}",
        "British Airways": "https://www.britishairways.com"
    }
    
    if companhia in links_cia:
        return links_cia[companhia], "✅ Site Oficial"
    else:
        return f"https://www.skyscanner.{suffix}/transport/flights/{origem}/{destino}/{data_sky}", "✈️ Ir para Skyscanner"

# --- INTERFACE ---
st.title("✈️ Flight Monitor GDS")

cidades = {
    "Brasil - Sudeste": {"São Paulo (GRU)": "GRU", "São Paulo (CGH)": "CGH", "Campinas (VCP)": "VCP", "Rio de Janeiro (GIG)": "GIG", "Rio de Janeiro (SDU)": "SDU", "Belo Horizonte (CNF)": "CNF", "Vitória (VIX)": "VIX"},
    "Brasil - Sul": {"Curitiba (CWB)": "CWB", "Florianópolis (FLN)": "FLN", "Porto Alegre (POA)": "POA", "Foz do Iguaçu (IGU)": "IGU"},
    "Brasil - Centro-Oeste": {"Brasília (BSB)": "BSB", "Goiânia (GYN)": "GYN", "Cuiabá (CGB)": "CGB"},
    "Brasil - Nordeste": {"Salvador (SSA)": "SSA", "Recife (REC)": "REC", "Fortaleza (FOR)": "FOR", "Natal (NAT)": "NAT", "Maceió (MCZ)": "MCZ"},
    "Brasil - Norte": {"Manaus (MAO)": "MAO", "Belém (BEL)": "BEL", "Porto Velho (PVH)": "PVH", "Marabá (MAB)": "MAB", "Macapá (MCP)": "MCP"},
    "Portugal": {"Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO", "Funchal (FNC)": "FNC", "Ponta Delgada (PDL)": "PDL"},
    "Europa": {"Madrid (MAD)": "MAD", "Barcelona (BCN)": "BCN", "Paris (CDG)": "CDG", "Londres (LHR)": "LHR", "Roma (FCO)": "FCO", "Frankfurt (FRA)": "FRA", "Istambul (IST)": "IST"},
    "Estados Unidos": {"Miami (MIA)": "MIA", "Orlando (MCO)": "MCO", "Nova York (JFK)": "JFK", "Boston (BOS)": "BOS"},
    "África": {"Luanda (LAD)": "LAD", "Joanesburgo (JNB)": "JNB", "Casablanca (CMN)": "CMN"}
}

mapa_iata = {}
opcoes = ["Selecione..."]
for regiao, items in cidades.items():
    for nome, iata in items.items():
        mapa_iata[nome] = iata
        opcoes.append(nome)

with st.form("busca_voos"):
    tipo_v = st.radio("Tipo de Viagem", ["Ida e volta", "Somente ida"], horizontal=True)
    
    col1, col2 = st.columns(2)
    with col1: origem_sel = st.selectbox("Origem", opcoes)
    with col2: destino_sel = st.selectbox("Destino", opcoes)
    
    col3, col4 = st.columns(2)
    with col3:
        data_ida = st.date_input("Data de Partida", value=datetime.today())
    with col4:
        # CORREÇÃO: Bloqueia ou esconde a data de volta conforme a escolha do utilizador
        if tipo_v == "Ida e volta":
            data_volta = st.date_input("Data de Regresso", value=datetime.today() + timedelta(days=7))
        else:
            st.info("Somente ida selecionado")
            data_volta = None

    st.write("Passageiros")
    p1, p2, p3 = st.columns(3)
    adultos = p1.number_input("Adultos", 1, 9, 1)
    criancas = p2.number_input("Crianças", 0, 9, 0)
    bebes = p3.number_input("Bebés", 0, adultos, 0)

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
                        resultados = []
                        for o in offers[:5]:
                            cia_nome = o["owner"]["name"]
                            link, label = gerar_info_reserva(cia_nome, iata_origem, iata_dest, data_ida, is_br)
                            resultados.append({
                                "Companhia": cia_nome,
                                "Preço": float(o["total_amount"]),
                                "Símbolo": "R$" if is_br else "€",
                                "Link": link,
                                "Botão": label
                            })
                        st.session_state.voos = resultados
                        st.session_state.itinerario = f"{origem_sel} para {destino_sel}"
                        st.success("Voos encontrados!")
                    else: st.warning("Nenhum voo encontrado.")
        except Exception as e: st.error(f"Erro: {e}")

# --- EXIBIÇÃO ---
if "voos" in st.session_state:
    st.divider()
    st.subheader("Melhores Ofertas")
    df = pd.DataFrame(st.session_state.voos)
    simb = st.session_state.voos[0]["Símbolo"]
    
    # Exibição da tabela com link dinâmico usando a label (Site Oficial ou Skyscanner)
    st.dataframe(df, column_config={
        "Preço": st.column_config.NumberColumn("Preço", format=f"{simb} %.2f"),
        "Link": st.column_config.LinkColumn("Reservar", display_text=r"(.+)"), 
        "Botão": None 
    }, use_container_width=True, hide_index=True)

    with st.expander("🔔 Ativar Alerta de Preço"):
        email = st.text_input("Teu E-mail")
        if st.button("Guardar Alerta"):
            if "@" in email:
                dados = {"email": email, "itinerario": st.session_state.itinerario, "origem": mapa_iata[origem_sel], "destino": mapa_iata[destino_sel], "data": str(data_ida), "data_volta": str(data_volta) if data_volta else "", "adultos": adultos, "criancas": criancas, "bebes": bebes, "preco_inicial": st.session_state.voos[0]["Preço"], "moeda": simb}
                if guardar_alerta_planilha(dados): st.success("Alerta guardado!")