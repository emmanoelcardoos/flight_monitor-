import streamlit as st
from duffel_api import Duffel
import pandas as pd
import os

# 1. Configuração da Página
st.set_page_config(page_title="Flight Monitor GDS", page_icon="✈️", layout="centered")

# Estilização
st.markdown("""<style>.stButton>button {width: 100%; background-color: #007bff; color: white; font-weight: bold; border-radius: 8px;}</style>""", unsafe_allow_html=True)

# 2. Token da Duffel (Pegando o que você salvou nos Secrets)
api_token = os.getenv('DUFFEL_TOKEN')

# 3. Cidades Organizadas
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

# Interface Principal
st.title("🌍 Flight Monitor - Duffel Power")
st.subheader("Olá! Escolha o destino e a data para encontrar os melhores preços.")

with st.container():
    col1, col2 = st.columns(2)
    with col1:
        origem_sel = st.selectbox("Saindo de:", options=opcoes, index=0)
    with col2:
        destino_sel = st.selectbox("Indo para:", options=opcoes, index=3) # Madrid por padrão
    
    data_voo = st.date_input("Quando pretendem viajar?")

# 4. Busca usando a Duffel
if st.button("🔍 Procurar Voos Agora"):
    if not api_token:
        st.error("Token da Duffel não configurado! Verifique os Secrets no Streamlit Cloud.")
    else:
        try:
            client = Duffel(access_token=api_token)
            
            with st.spinner('A consultar ofertas em tempo real...'):
                # Criar a requisição de oferta
                slices = [{"origin": mapa_iata[origem_sel], "destination": mapa_iata[destino_sel], "departure_date": str(data_voo)}]
                offer_request = client.offer_requests.create().slices(slices).passengers([{"type": "adult"}]).execute()
                
                # Listar as ofertas geradas
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
                    st.success(f"Encontramos {len(df)} ofertas!")
                    
                    st.dataframe(
                        df[["Companhia", "Preço", "Moeda", "Link"]],
                        column_config={
                            "Preço": st.column_config.NumberColumn(format="%.2f"),
                            "Link": st.column_config.LinkColumn("Reservar 🔗", display_text="Ver no Google")
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                    st.bar_chart(df.set_index('Companhia')['Preço'])
                else:
                    st.warning("Nenhum voo encontrado para esta data.")
        except Exception as e:
            st.error(f"Erro na busca: {e}")

st.markdown("---")
st.caption("Desenvolvido por Emmanoel.")