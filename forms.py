import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from PIL import Image

# Configuração da página

st.set_page_config(page_title="Inscrição em Oficinas IX Ences", layout="wide")
st.image(Image.open('logo.png').resize((400, 200)))


# Definição das oficinas e suas vagas
OFICINAS = {
    "BI": 45,
    "CENSOFIX": 30,
    "RELATÓRIOS": 100
}

@st.cache_data(ttl=1)  # Cache com duração de 1 segundo
def ler_dados_sheets():
    """Lê os dados do Google Sheets com cache curto"""
    conn = st.connection('gsheets', type=GSheetsConnection)
    return conn.read(usecols=[0,1,2,3])

def contar_inscritos_por_oficina(dia):
    """Conta quantos inscritos existem em cada oficina por dia"""
    try:
        data_atual = ler_dados_sheets()
        coluna = 'oficina_dia1' if dia == 1 else 'oficina_dia2'
        contagem = data_atual[coluna].value_counts().to_dict()
        return {oficina: contagem.get(oficina, 0) for oficina in OFICINAS.keys()}
    except Exception as e:
        st.error(f"Erro ao contar inscritos: {str(e)}")
        return {oficina: 0 for oficina in OFICINAS.keys()}

def get_oficinas_disponiveis(dia, oficina_outro_dia=None):
    """Retorna lista de oficinas que ainda têm vagas disponíveis"""
    inscritos = contar_inscritos_por_oficina(dia)
    oficinas_disponiveis = []

    for oficina, total_vagas in OFICINAS.items():
        vagas_ocupadas = inscritos.get(oficina, 0)
        if vagas_ocupadas < total_vagas:
            if oficina_outro_dia and oficina == oficina_outro_dia:
                continue
            vagas_restantes = total_vagas - vagas_ocupadas
            oficinas_disponiveis.append(f"{oficina} ({vagas_restantes} vagas)")

    return oficinas_disponiveis

def adicionar_inscricao(nome, ies, oficina_dia1, oficina_dia2):
    """Adiciona uma nova inscrição ao Google Sheets"""
    try:
        conn = st.connection('gsheets', type=GSheetsConnection)
        st.cache_data.clear()
        data_atual = ler_dados_sheets()

        # Verificar novamente se ainda há vagas
        inscritos_dia1 = contar_inscritos_por_oficina(1)
        inscritos_dia2 = contar_inscritos_por_oficina(2)

        if (inscritos_dia1.get(oficina_dia1, 0) >= OFICINAS[oficina_dia1] or
            inscritos_dia2.get(oficina_dia2, 0) >= OFICINAS[oficina_dia2]):
            st.error("Desculpe, as vagas acabaram de ser preenchidas. Por favor, tente outras opções.")
            return False

        novo_registro = pd.DataFrame({
            'nome_participante': [nome.strip()],
            'nome_ies': [ies.strip()],
            'oficina_dia1': [oficina_dia1],
            'oficina_dia2': [oficina_dia2]
        })

        data_atualizada = pd.concat([data_atual, novo_registro], ignore_index=True)
        conn.update(data=data_atualizada)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar inscrição: {str(e)}")
        return False


def main():
    st.title("Inscrição em Oficinas")

    nome = st.text_input("Nome do Participante *")
    ies = st.text_input("Nome da IES *")

    # Oficina Dia 1
    oficinas_dia1 = get_oficinas_disponiveis(1)

    if not oficinas_dia1:
        st.error("Não há mais vagas disponíveis para o primeiro dia!")
        oficina_dia1 = st.selectbox("Escolha a oficina para o Dia 1 *", options=["Não há vagas disponíveis"], key="oficina_dia1")
    else:
        oficina_dia1 = st.selectbox("Escolha a oficina para o Dia 1 *", options=["Selecione uma oficina..."] + oficinas_dia1, key="oficina_dia1")

    # Botão para salvar a escolha do dia 1
    salvar_dia1 = st.button("Salvar Primeiro Dia")

    if "oficina_dia1_selecionada" not in st.session_state:
        st.session_state.oficina_dia1_selecionada = None

    if salvar_dia1 and oficina_dia1 not in ["Selecione uma oficina...", "Não há vagas disponíveis"]:
        st.session_state.oficina_dia1_selecionada = oficina_dia1.split(" (")[0]

    if st.session_state.oficina_dia1_selecionada:
        # Oficina Dia 2
        oficinas_dia2_filtradas = get_oficinas_disponiveis(2, st.session_state.oficina_dia1_selecionada)

        if not oficinas_dia2_filtradas:
            st.error("Não há mais vagas disponíveis para o segundo dia!")
            oficina_dia2 = st.selectbox("Escolha a oficina para o Dia 2 *", options=["Não há vagas disponíveis"], key="oficina_dia2")
        else:
            oficina_dia2 = st.selectbox("Escolha a oficina para o Dia 2 *", options=["Selecione uma oficina..."] + oficinas_dia2_filtradas, key="oficina_dia2")

        st.markdown("(*) Campos obrigatórios")

        submitted = st.button("Salvar segundo Dia e Enviar Inscrição")

        if submitted:
            if not nome.strip():
                st.error("Por favor, preencha o nome do participante!")
                return

            if not ies.strip():
                st.error("Por favor, preencha o nome da IES!")
                return


            if oficina_dia1 in ["Não há vagas disponíveis", "Selecione uma oficina..."] or \
               oficina_dia2 in ["Não há vagas disponíveis", "Selecione uma oficina..."]:
                st.error("Por favor, selecione oficinas válidas nos dois dias!")
                return

            oficina_dia1_final = st.session_state.oficina_dia1_selecionada
            oficina_dia2_final = oficina_dia2.split(" (")[0]

            if adicionar_inscricao(nome, ies, oficina_dia1_final, oficina_dia2_final):
                st.success("Inscrição realizada com sucesso!")
                st.balloons()

                # Limpa o cache e força atualização
                st.cache_data.clear()
                time.sleep(2)  # Pequena pausa para garantir a atualização
                st.rerun()
            else:
                st.error("Não foi possível realizar a inscrição. Por favor, tente novamente.")
                st.cache_data.clear()



if __name__ == "__main__":
    main()
