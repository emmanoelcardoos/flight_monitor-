import streamlit as st
from duffel_api import Duffel
import pandas as pd
import os

os.environ["DUFFEL_API_VERSION"] = "v1"

# 1. Configuração da Página
st.set_page_config(page_title="Flight Monitor DGS", page_icon="✈️", layout="centered")

# Estilização
st.markdown("""<style>.stButton>button {width: 100%; background-color: #007bff; color: white; font-weight: bold; border-radius: 8px;}</style>""", unsafe_allow_html=True)

# 2. Token da Duffel
api_token = os.getenv('DUFFEL_TOKEN')

# 3. Cidades
cidades = {
    "Brasil": {"São Paulo (GRU)": "GRU", "Rio (GIG)": "GIG", "Brasília (BSB)": "BSB"},
    "Europa": {"Madrid (MAD)": "MAD", "Lisboa (LIS)": "LIS", "Porto (OPO)": "OPO", "Paris (CDG)": "CDG", "Londres (LHR)": "LHR"},
    "EUA": {"Nova York (JFK)": "JFK", "Miami (MIA)": "MIA", "Orlando (MCO)": "MCO"}
}

opcoes = []
mapa_iata = {}
for regiao, items in cidades.items():
    for nome, iata in items.items():
        opcoes.append(nome)
        mapa_iata[nome] = iata

# Interface
st.title("🌍 Flight Monitor - Duffel Power")
st.subheader("Olá! Escolha o destino e a data para encontrar os melhores preços.")

with st.container():
    col1, col2 = st.columns(2)
    with col1:
        origem_sel = st.selectbox("Saindo de:", options=opcoes, index=0)
    with col2:
        destino_sel = st.selectbox("Indo para:", options=opcoes, index=3)
    
    data_voo = st.date_input("Quando pretendem viajar?")

# 4. Busca
if st.button("🔍 Procurar Voos Agora"):
    if not api_token:
        st.error("Token não configurado!")
    else:
        try:
            # ADICIONADO: version="v1" para corrigir o erro de Unsupported Version
            client = Duffel(access_token=api_token)
            
            with st.spinner('Consultando ofertas atualizadas...'):
                slices = [{"origin": mapa_iata[origem_sel], "destination": mapa_iata[destino_sel], "departure_date": str(data_voo)}]
                
                # Criar a requisição
                offer_request = client.offer_requests.create().slices(slices).passengers([{"type": "adult"}]).execute()
                
                # Listar ofertas
                offers = client.offers.list(offer_request.id)
                
                voos_proc = []
                for o in offers:
                    voos_proc.append({
                        "Companhia": o.owner.name,
                        "Preço": float(o.total_amount),
                        "Moeda": o.total_currency,
                        "Link": f"https://www.google.com/travel/flights?q=Flights%20to%20{mapa_iata[destino_sel]}%20from%20{mapa_iata[origem_sel]}%20on%20{data_voo}"
                    })

                if voos_proc:
                    df = pd.DataFrame(voos_proc).sort_values(by="Preço")
                    st.balloons()
                    st.success(f"Encontramos {len(df)} voos!")
                    
                    st.dataframe(
                        df,
                        column_config={
                            "Preço": st.column_config.NumberColumn(format="%.2f"),
                            "Link": st.column_config.LinkColumn("Reservar 🔗", display_text="Ver no Google")
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.warning("A Duffel não encontrou voos para esta data no Modo de Teste. Tente outra data ou rota.")
        except Exception as e:
            st.error(f"Erro na busca: {e}")

st.markdown("---")
st.caption("Desenvolvido por Emmanoel.")