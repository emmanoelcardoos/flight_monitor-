import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from streamlit_gsheets import GSheetsConnection

import streamlit as st
# ... teus outros imports ...

# Configuração da página (deve ser a primeira coisa do Streamlit)
st.set_page_config(page_title="Flight Monitor GDS", page_icon="✈️", layout="wide")

# --- ESTILO CSS PERSONALIZADO ---
st.markdown("""
    <style>
    /* 1. Reset Total e Fundo Neutro */
    .stApp {
        background: #FFFFFF !important;
    }
    
    /* 2. Esconder Elementos de 'Ruído' do Streamlit */
    header, footer, #MainMenu {visibility: hidden;}
    
    /* 3. Tipografia Profissional */
    h1, h2, h3, p, span, label {
        color: #1A1C1E !important;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
    }

    /* 4. Estilização dos Inputs (Estilo Clean) */
    /* Remove o preto e coloca um cinza bem leve */
    div[data-baseweb="select"], div[data-baseweb="input"], .stNumberInput div {
        background-color: #F7F9FC !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important;
        color: #1A1C1E !important;
    }
    
    /* Ajuste específico para o texto dentro dos inputs */
    input {
        color: #1A1C1E !important;
        background-color: transparent !important;
    }

    /* 5. Botão de Pesquisa (Moderno e Centralizado) */
    div.stButton > button {
        background-color: #0066FF !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 0.6rem 2rem !important;
        transition: all 0.2s ease;
    }
    
    div.stButton > button:hover {
        background-color: #0052CC !important;
        box-shadow: 0 4px 12px rgba(0, 102, 255, 0.2);
    }

    /* 6. Tabela de Resultados */
    div.stDataFrame {
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        overflow: hidden;
    }

    /* 7. Alinhamento dos Labels */
    label p {
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        color: #64748B !important; /* Cinza suave para labels */
    }
    </style>
    """, unsafe_allow_html=True)

# --- CABEÇALHO ---
st.title("✈️ Flight Monitor GDS")
st.markdown("<p style='color: #64748b; font-size: 1.2em;'>A tua agência digital de monitorização de voos em tempo real.</p>", unsafe_allow_html=True)
# 1. Configuração da Página
st.set_page_config(page_title="Flight Monitor GDS", page_icon="✈️", layout="wide")

# --- LER PARÂMETROS DA URL (Auto-preenchimento) ---
query_params = st.query_params
url_origem = query_params.get("origem")
url_destino = query_params.get("destino")
url_data = query_params.get("data")

# --- FUNÇÕES DE APOIO ---
def enviar_alerta_email(email_destino, itinerario, preco, moeda, origem_cod, destino_cod, data_ida):
    email_remetente = st.secrets.get("EMAIL_USER")
    senha_app = st.secrets.get("EMAIL_PASSWORD")
    
    link_base = "https://flightmonitorec.streamlit.app"
    link_direto = f"{link_base}/?origem={origem_cod}&destino={destino_cod}&data={data_ida}"

    if not email_remetente or not senha_app: return False

    msg = MIMEMultipart()
    msg['From'] = email_remetente
    msg['To'] = email_destino
    msg['Subject'] = f"✈️ Alerta de Preço: {itinerario}"

    corpo = f"""
    Olá!
    
    Encontrámos o preço que procurava para o seu itinerário:
    
    📍 Itinerário: {itinerario}
    💰 Melhor Preço: {moeda} {preco:.2f}
    
    Clique no link abaixo para abrir o buscador com estes dados já preenchidos:
    🔗 {link_direto}
    
    Boa viagem,
    Equipa Flight Monitor GDS
    """
    msg.attach(MIMEText(corpo, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_remetente, senha_app)
        server.send_message(msg)
        server.quit()
        return True
    except: return False

def guardar_alerta_planilha(dados):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # O segredo está no ttl=0 para leitura fresca
        # Adicionamos as novas colunas à lista oficial
        colunas_certas = [
            "email", "itinerario", "origem", "destino", "data", 
            "adultos", "criancas", "bebes", "preco_inicial", "moeda"
        ]
        
        try:
            df_atual = conn.read(worksheet="Página1", ttl=0)
            if not df_atual.empty:
                # Reindexamos para garantir que o DF lido tenha as colunas certas
                df_atual = df_atual.reindex(columns=colunas_certas)
            else:
                df_atual = pd.DataFrame(columns=colunas_certas)
        except:
            df_atual = pd.DataFrame(columns=colunas_certas)

        # Criar a nova linha com os dados dos passageiros
        novo_dado = pd.DataFrame([dados])
        novo_dado = novo_dado.reindex(columns=colunas_certas)

        # Juntar tudo
        df_final = pd.concat([df_atual, novo_dado], ignore_index=True)

        # Atualizar a planilha
        conn.update(worksheet="Página1", data=df_final)
        st.cache_data.clear() 
        
        return True
    except Exception as e:
        st.error(f"Erro ao guardar alerta: {e}")
        return False

def get_exchange_rate():
    try:
        res = requests.get("https://open.er-api.com/v6/latest/EUR")
        return res.json()["rates"]["BRL"]
    except: return 6.15

# --- BASE DE DADOS DE CIDADES ---
cidades = {
    "Brasil - Sudeste": {"São Paulo (GRU)": "GRU", "São Paulo (CGH)": "CGH", "Campinas (VCP)": "VCP", "Rio de Janeiro (GIG)": "GIG", "Rio de Janeiro (SDU)": "SDU", "Belo Horizonte (CNF)": "CNF", "Belo Horizonte (PLU)": "PLU", "Vitória (VIX)": "VIX"},
    "Brasil - Sul": {"Curitiba (CWB)": "CWB", "Florianópolis (FLN)": "FLN", "Porto Alegre (POA)": "POA", "Foz do Iguaçu (IGU)": "IGU", "Navegantes (NVT)": "NVT", "Londrina (LDB)": "LDB"},
    "Brasil - Centro-Oeste": {"Brasília (BSB)": "BSB", "Goiânia (GYN)": "GYN", "Cuiabá (CGB)": "CGB", "Campo Grande (CGR)": "CGR"},
    "Brasil - Nordeste": {"Salvador (SSA)": "SSA", "Recife (REC)": "REC", "Fortaleza (FOR)": "FOR", "Natal (NAT)": "NAT", "Maceió (MCZ)": "MCZ", "João Pessoa (JPA)": "JPA", "Aracaju (AJU)": "AJU", "Porto Seguro (BPS)": "BPS", "Ilhéus (IOS)": "IOS"},
    "Brasil - Norte": {"Manaus (MAO)": "MAO", "Belém (BEL)": "BEL", "Porto Velho (PVH)": "PVH", "Rio Branco (RBR)": "RBR", "Macapá (MCP)": "MCP", "Boa Vista (BVB)": "BVB", "Palmas (PMW)": "PMW", "Marabá (MAB)": "MAB", "Parauapebas (Carajás)": "CKS"},
    "Portugal": {"Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO", "Funchal (FNC)": "FNC", "Ponta Delgada (PDL)": "PDL"},
    "Europa": {"Madrid (MAD)": "MAD", "Barcelona (BCN)": "BCN", "Paris (CDG)": "CDG", "Paris Orly (ORY)": "ORY", "Londres Heathrow (LHR)": "LHR", "Londres Gatwick (LGW)": "LGW", "Roma (FCO)": "FCO", "Milão (MXP)": "MXP", "Frankfurt (FRA)": "FRA", "Munique (MUC)": "MUC", "Zurique (ZRH)": "ZRH", "Amsterdã (AMS)": "AMS", "Bruxelas (BRU)": "BRU", "Copenhaga (CPH)": "CPH", "Istambul (IST)": "IST"},
    "Estados Unidos": {"Miami (MIA)": "MIA", "Orlando (MCO)": "MCO", "Fort Lauderdale (FLL)": "FLL", "Nova York JFK (JFK)": "JFK", "Nova York Newark (EWR)": "EWR", "Atlanta (ATL)": "ATL", "Dallas (DFW)": "DFW", "Houston (IAH)": "IAH", "Chicago (ORD)": "ORD", "Los Angeles (LAX)": "LAX", "San Francisco (SFO)": "SFO", "Washington (IAD)": "IAD", "Boston (BOS)": "BOS"},
    "África": {"Luanda (LAD)": "LAD", "Joanesburgo (JNB)": "JNB", "Cidade do Cabo (CPT)": "CPT", "Casablanca (CMN)": "CMN", "Addis Abeba (ADD)": "ADD"}
}

destinos_explorar_lista = ["LIS", "OPO", "MAD", "BCN", "PAR", "LHR", "FCO", "FRA", "AMS", "GRU", "GIG", "BSB", "MIA", "JFK", "LAD", "CMN"]

mapa_iata = {}
opcoes_origem = ["Cidade ou Aeroporto..."]
opcoes_destino = ["Cidade ou Aeroporto...", "🌍 EXPLORAR QUALQUER LUGAR"]

for regiao, items in cidades.items():
    for nome, iata in items.items():
        mapa_iata[nome] = iata
        opcoes_origem.append(nome)
        opcoes_destino.append(nome)

# --- LÓGICA DE ÍNDICE DINÂMICO (PARA O LINK FUNCIONAR) ---
def get_index(lista, valor_iata):
    if not valor_iata: return 0
    for i, nome in enumerate(lista):
        if valor_iata in nome: return i
    return 0

idx_o = get_index(opcoes_origem, url_origem)
idx_d = get_index(opcoes_destino, url_destino)
default_date = datetime.strptime(url_data, "%Y-%m-%d") if url_data else datetime.today()

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    [data-testid="stSelectbox"] svg { display: none; }
    .stSelectbox div[data-baseweb="select"] { border-radius: 20px; }
    .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

# --- INTERFACE (CABEÇALHO) ---
header_col1, header_col2 = st.columns([3, 1])
with header_col1:
    st.title("🌍 Flight Monitor - Buscador GDS")
    tipo_viagem = st.radio("Configuração:", ["Só Ida/Volta", "Ida e Volta"], horizontal=True, label_visibility="collapsed")
with header_col2:
    st.markdown("<p style='margin-bottom: -10px; font-weight: bold; color: white;'>Moeda</p>", unsafe_allow_html=True)
    moeda_pref = st.selectbox("Moeda", ["Euro (€) - (.PT)", "Real (R$) - (.BR)"], key="moeda_header", label_visibility="collapsed")

st.write("") 

# --- TÍTULOS ---
t_col1, t_col2, t_col3, t_col4, t_col5 = st.columns([2.5, 2.5, 1.5, 1.5, 1])
estilo_titulo = "margin-bottom: -30px; font-weight: bold; color: white; font-size: 14px;"
t_col1.markdown(f"<p style='{estilo_titulo}'>🛫 Origem</p>", unsafe_allow_html=True)
t_col2.markdown(f"<p style='{estilo_titulo}'>🛬 Destino</p>", unsafe_allow_html=True)
t_col3.markdown(f"<p style='{estilo_titulo}'>📅 Ida</p>", unsafe_allow_html=True)
if tipo_viagem == "Ida e Volta":
    t_col4.markdown(f"<p style='{estilo_titulo}'>📅 Volta</p>", unsafe_allow_html=True)

st.write("") 

# --- BARRA DE PESQUISA ATUALIZADA ---
# Ajustei as proporções das colunas para caberem os passageiros sem amontoar
col1, col2, col3, col4 = st.columns([2, 2, 1.2, 1.2])
with col1:
    origem_sel = st.selectbox("Origem", options=opcoes_origem, index=idx_o, key="origem", label_visibility="collapsed")
with col2:
    destino_sel = st.selectbox("Destino", options=opcoes_destino, index=idx_d, key="destino", label_visibility="collapsed")
with col3:
    data_ida = st.date_input("Ida", value=default_date, min_value=datetime.today(), label_visibility="collapsed")
with col4:
    if tipo_viagem == "Ida e Volta":
        data_volta = st.date_input("Volta", min_value=data_ida + timedelta(days=1), label_visibility="collapsed")
    else:
        st.button("Somente Ida", disabled=True, use_container_width=True)
        data_volta = None

# --- NOVA LINHA PARA PASSAGEIROS E BOTÃO ---
st.markdown("##### 👥 Passageiros")
c_ad, c_cr, c_be, c_btn = st.columns([1, 1, 1, 2])
with c_ad:
    adultos = st.number_input("Adultos", min_value=1, max_value=9, value=1, step=1)
with c_cr:
    criancas = st.number_input("Crianças", min_value=0, max_value=9, value=0, step=1)
with c_be:
    # Máximo de bebês é limitado ao número de adultos (regra de segurança da aviação)
    bebes = st.number_input("Bebés", min_value=0, max_value=adultos, value=0, step=1)
with c_btn:
    st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True) # Alinhamento visual
    btn_pesquisar = st.button("Pesquisar Voos", use_container_width=True, type="primary")

# --- LÓGICA DE BUSCA ---
if btn_pesquisar:
    if origem_sel == "Cidade ou Aeroporto..." or destino_sel == "Cidade ou Aeroporto...":
        st.warning("⚠️ Selecione a Origem e o Destino.")
    else:
        try:
            mapa_nomes = {v: k for k, v in mapa_iata.items()}
            with st.spinner('A pesquisar para o grupo...'):
                api_token = st.secrets.get("DUFFEL_TOKEN")
                headers = {"Authorization": f"Bearer {api_token}", "Duffel-Version": "v2", "Content-Type": "application/json"}
                cotacao = get_exchange_rate()
                is_br = "Real" in moeda_pref
                iata_origem = mapa_iata[origem_sel]
                
                # Montar a lista de passageiros para a API
                lista_passageiros = []
                for _ in range(adultos): lista_passageiros.append({"type": "adult"})
                for _ in range(criancas): lista_passageiros.append({"type": "child"})
                for _ in range(bebes): lista_passageiros.append({"type": "infant"})

                lista_destinos = [d for d in destinos_explorar_lista if d != iata_origem] if destino_sel == "🌍 EXPLORAR QUALQUER LUGAR" else [mapa_iata[destino_sel]]

                resultados = []
                for iata_dest in lista_destinos:
                    slices = [{"origin": iata_origem, "destination": iata_dest, "departure_date": str(data_ida)}]
                    if data_volta:
                        slices.append({"origin": iata_dest, "destination": iata_origem, "departure_date": str(data_volta)})
                    
                    # PAYLOAD ATUALIZADO COM LISTA DE PASSAGEIROS
                    payload = {
                        "data": {
                            "slices": slices, 
                            "passengers": lista_passageiros, 
                            "requested_currencies": ["BRL" if is_br else "EUR"]
                        }
                    }
                    
                    res = requests.post("https://api.duffel.com/air/offer_requests", headers=headers, json=payload)
                    
                    if res.status_code == 201:
                        offers = requests.get(f"https://api.duffel.com/air/offers?offer_request_id={res.json()['data']['id']}&sort=total_amount", headers=headers).json().get("data", [])
                        if offers:
                            o = offers[0]
                            preco_exibicao = float(o["total_amount"])
                            if not is_br and o["total_currency"] == "BRL": preco_exibicao /= cotacao
                            if is_br and o["total_currency"] == "EUR": preco_exibicao *= cotacao

                            resultados.append({
                                "Destino": mapa_nomes.get(iata_dest, iata_dest),
                                "Companhia": o["owner"]["name"],
                                "Preço": preco_exibicao,
                                "Símbolo": "R$" if is_br else "€",
                                "Link": f"https://www.skyscanner.{'com.br' if is_br else 'pt'}/transport/flights/{iata_origem}/{iata_dest}/{data_ida.strftime('%y%m%d')}/?curr={'BRL' if is_br else 'EUR'}",
                                "Adultos": adultos,   # Guardamos para o alerta depois
                                "Criancas": criancas,
                                "Bebes": bebes
                            })

                if resultados:
                    st.session_state.voos = sorted(resultados, key=lambda x: x['Preço'])
                    st.session_state.is_br = is_br
                    st.session_state.cotacao = cotacao
                    st.session_state.itinerario = f"{origem_sel} para {destino_sel}"
                    st.toast(f"Resultados para {adultos+criancas+bebes} passageiro(s)!", icon="✈️")
                else:
                    st.warning("Não foram encontrados voos para este grupo nesta data.")
        except Exception as e: st.error(f"Erro: {e}")

# --- EXIBIÇÃO ---
# --- EXIBIÇÃO ---
if "voos" in st.session_state:
    simb = st.session_state.voos[0]["Símbolo"]
    df = pd.DataFrame(st.session_state.voos)
    
    # Removemos as colunas internas (Adultos, Criancas, Bebes) da visualização da tabela para ficar clean
    # mas elas continuam no session_state para usarmos no alerta.
    colunas_visiveis = ["Destino", "Companhia", "Preço", "Link"]
    
    st.dataframe(df[colunas_visiveis], column_config={
        "Preço": st.column_config.NumberColumn(f"Preço ({simb})", format=f"{simb} %.2f"),
        "Link": st.column_config.LinkColumn("Reservar", display_text="Ver Oferta ✈️")
    }, hide_index=True, use_container_width=True)
    
    if st.session_state.is_br:
        st.caption(f"ℹ️ Câmbio ao vivo: 1€ = R$ {st.session_state.cotacao:.2f}")

    st.write("---")
    st.subheader("📬 Alerta de Preço por E-mail")
    st.info(f"O alerta será configurado para: **{adultos} Adulto(s), {criancas} Criança(s) e {bebes} Bebé(s)**")
    
    col_mail, col_btn = st.columns([3, 1])
    with col_mail:
        email_user = st.text_input("Teu e-mail:", key="email_input", label_visibility="collapsed", placeholder="exemplo@gmail.com")
    with col_btn:
        if st.button("Ativar Alerta", use_container_width=True):
            if "@" in email_user:
                with st.spinner("A processar alerta..."):
                    # 1. Enviar e-mail de confirmação imediata
                    # Usamos os códigos IATA que já calculamos na lógica de busca
                    orig_cod = mapa_iata[origem_sel]
                    dest_cod = mapa_iata[destino_sel] if destino_sel != "🌍 EXPLORAR QUALQUER LUGAR" else "EXPLORE"
                    
                    enviado = enviar_alerta_email(
                        email_user, 
                        st.session_state.itinerario, 
                        st.session_state.voos[0]["Preço"], 
                        simb,
                        orig_cod,
                        dest_cod,
                        data_ida
                    )
                    
                    # 2. Guardar na Planilha incluindo a nova contagem de passageiros
                    dados_alerta = {
                        "email": email_user,
                        "itinerario": st.session_state.itinerario,
                        "origem": orig_cod,
                        "destino": dest_cod,
                        "data": str(data_ida),
                        "data_volta": str(data_volta) if data_volta else "",
                        "adultos": adultos,   # Valor capturado do number_input
                        "criancas": criancas, # Valor capturado do number_input
                        "bebes": bebes,       # Valor capturado do number_input
                        "preco_inicial": st.session_state.voos[0]["Preço"],
                        "moeda": simb
                    }
                    guardado = guardar_alerta_planilha(dados_alerta)
                    
                    if enviado and guardado:
                        total_pax = adultos + criancas + bebes
                        st.success(f"✅ Alerta ativo para {total_pax} passageiro(s)! Receberá atualizações diárias.")
            else:
                st.error("Por favor, insere um e-mail válido.")
     