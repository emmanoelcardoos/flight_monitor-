# --- PÁGINA 2: RESERVA (CORREÇÃO DE VISIBILIDADE) ---
elif st.session_state.pagina == "reserva":
    v = st.session_state.voo_selecionado
    st.title("🏁 Checkout Seguro")
    st.info(f"📍 {v['Companhia']} | Total: {v['Moeda']} {v['Preço']:.2f}")

    # 1. O SELETOR FICA FORA DO FORM PARA REAGIR INSTANTANEAMENTE
    metodo = st.radio(
        "Selecione o método de pagamento:", 
        ["Cartão de Crédito", "PIX"], 
        horizontal=True,
        key="metodo_pagamento"
    )

    # 2. INÍCIO DO FORMULÁRIO
    with st.form("form_final"):
        st.subheader("👤 Dados do Passageiro")
        c1, c2 = st.columns(2)
        n = c1.text_input("Nome Próprio")
        a = c2.text_input("Apelido")
        e = st.text_input("E-mail para Bilhete")
        # Data de nascimento permitindo crianças e bebés (até 2026)
        dn = st.date_input("Data de Nascimento", value=datetime(1995,1,1), max_value=datetime(2026,12,31))
        
        st.divider()

        # 3. LÓGICA DE EXIBIÇÃO: Só desenha o cartão se o rádio for "Cartão"
        if metodo == "Cartão de Crédito":
            st.markdown("### 💳 Dados do Cartão")
            st.text_input("Número do Cartão", placeholder="0000 0000 0000 0000")
            st.text_input("Nome Impresso")
            cc1, cc2 = st.columns(2)
            cc1.text_input("Validade (MM/AA)", placeholder="MM/AA")
            cc2.text_input("CVV", type="password")
            
            if v['Moeda'] == "R$":
                # Parcelamento solicitado
                opcoes = [f"{i}x de R$ {v['Preço']/i:.2f} sem juros" for i in range(1, 11)]
                opcoes.extend([f"11x de R$ {(v['Preço']*1.05)/11:.2f} (c/ taxas)", f"12x de R$ {(v['Preço']*1.07)/12:.2f} (c/ taxas)"])
                st.selectbox("Parcelamento", opcoes)
        else:
            # Se for PIX, mostra apenas as instruções e o link
            st.success("💠 **Pagamento via PIX Selecionado**")
            st.warning("Os campos de cartão foram removidos. Finalize abaixo para receber as instruções.")
            st.markdown(f"""
                <a href="https://wa.me/{WHATSAPP_SUPORTE}?text=Olá,%20pagamento%20PIX%20de%20{v['Preço']}" target="_blank" style="text-decoration:none;">
                    <div style="background-color: #25D366; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 18px;">
                        💬 Chamar no WhatsApp para Chave PIX
                    </div>
                </a>
            """, unsafe_allow_html=True)

        st.divider()
        if st.form_submit_button("CONFIRMAR E EMITIR BILHETE"):
            if n and e:
                st.balloons()
                st.success(f"Solicitação enviada! PNR será gerado para {n}.")
            else:
                st.error("Preencha o Nome e E-mail.")

# --- PÁGINA 3: ÁREA DO CLIENTE (COM LOGIN PNR + EMAIL) ---
elif st.session_state.pagina == "login":
    st.title("🔑 Área Privada do Passageiro")
    st.markdown("Introduza os seus dados para consultar a reserva.")
    
    # Caixa de login estilizada
    with st.container(border=True):
        st.subheader("Consultar minha Reserva")
        col_id1, col_id2 = st.columns(2)
        pnr_input = col_id1.text_input("Código da Reserva (PNR)", placeholder="Ex: GTD78X").upper()
        email_input = col_id2.text_input("E-mail da Reserva", placeholder="seu@email.com")
        
        if st.button("🔍 Aceder aos Detalhes"):
            if pnr_input and email_input:
                st.divider()
                st.success(f"Reserva **{pnr_input}** localizada!")
                st.info(f"Enviamos um código de acesso temporário para **{email_input}**.")
            else:
                st.error("É necessário introduzir o PNR e o E-mail para continuar.")