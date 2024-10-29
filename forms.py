import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from PIL import Image

# Configuração da página
st.set_page_config(page_title="Inscrição em Oficinas IX Ences", page_icon='icone.png')
st.image(Image.open('logo.png').resize((400, 200)))

# Definição das oficinas e suas vagas para cada dia
OFICINAS = {
    "DIA1": {
        "Consulta e extração no BI": 168,
        "Relatórios do Censup": 42,
        "CensoFix para migração": 30
    },
    "DIA2": {
        "Consulta e extração no BI": 42,
        "Relatórios do Censup": 168,
        "CensoFix para migração": 30
    }
}

@st.cache_data(ttl=1)
def ler_dados_sheets():
    """Lê os dados das duas abas do Google Sheets"""
    conn = st.connection('gsheets', type=GSheetsConnection)
    inscritos = conn.read(worksheet="inscritos", usecols=[0,1,2,3])
    lista_evento = conn.read(worksheet="lista_evento", usecols=[0,1,2])
    return inscritos, lista_evento

def get_ies_list():
    """Retorna lista de IES concatenada com código e nome"""
    _, lista_evento = ler_dados_sheets()
    # Convertendo co_ies para inteiro e depois para string para remover decimais
    lista_evento['ies_completo'] = lista_evento['co_ies'].astype(int).astype(str) + ' - ' + lista_evento['no_ies']
    return lista_evento['ies_completo'].unique()

def get_participantes_ies(ies_selecionada):
    """Retorna lista de participantes da IES selecionada"""
    _, lista_evento = ler_dados_sheets()
    # Extrair o código da IES da string selecionada
    co_ies = int(ies_selecionada.split(' - ')[0])
    # Converter co_ies da lista_evento para inteiro para garantir a comparação correta
    return lista_evento[lista_evento['co_ies'].astype(int) == co_ies]['no_pessoa_fisica'].tolist()

def contar_inscritos_por_oficina(dia):
    """Conta quantos inscritos existem em cada oficina por dia"""
    try:
        inscritos, _ = ler_dados_sheets()
        coluna = 'oficina_dia1' if dia == 1 else 'oficina_dia2'
        contagem = inscritos[coluna].value_counts().to_dict()
        oficinas_dia = OFICINAS['DIA1'] if dia == 1 else OFICINAS['DIA2']
        return {oficina: contagem.get(oficina, 0) for oficina in oficinas_dia.keys()}
    except Exception as e:
        st.error(f"Erro ao contar inscritos: {str(e)}")
        return {oficina: 0 for oficina in OFICINAS['DIA1' if dia == 1 else 'DIA2'].keys()}

def get_oficinas_disponiveis(dia, oficina_outro_dia=None):
    """Retorna lista de oficinas que ainda têm vagas disponíveis"""
    inscritos = contar_inscritos_por_oficina(dia)
    oficinas_dia = OFICINAS['DIA1'] if dia == 1 else OFICINAS['DIA2']
    oficinas_disponiveis = []

    for oficina, total_vagas in oficinas_dia.items():
        vagas_ocupadas = inscritos.get(oficina, 0)
        if vagas_ocupadas < total_vagas:
            if oficina_outro_dia and oficina == oficina_outro_dia:
                continue
            vagas_restantes = total_vagas - vagas_ocupadas
            oficinas_disponiveis.append(f"{oficina} ({vagas_restantes} vagas)")

    return oficinas_disponiveis

def adicionar_inscricao(ies, participante, oficina_dia1, oficina_dia2):
    """Adiciona uma nova inscrição ao Google Sheets"""
    try:
        conn = st.connection('gsheets', type=GSheetsConnection)
        st.cache_data.clear()
        inscritos, _ = ler_dados_sheets()

        # Verificar novamente se ainda há vagas
        inscritos_dia1 = contar_inscritos_por_oficina(1)
        inscritos_dia2 = contar_inscritos_por_oficina(2)

        if (inscritos_dia1.get(oficina_dia1, 0) >= OFICINAS['DIA1'][oficina_dia1] or
            inscritos_dia2.get(oficina_dia2, 0) >= OFICINAS['DIA2'][oficina_dia2]):
            st.error("Desculpe, as vagas acabaram de ser preenchidas. Por favor, tente outras opções.")
            return False

        novo_registro = pd.DataFrame({
            'nome_participante': [participante],
            'nome_ies': [ies],
            'oficina_dia1': [oficina_dia1],
            'oficina_dia2': [oficina_dia2]
        })

        data_atualizada = pd.concat([inscritos, novo_registro], ignore_index=True)
        conn.update(worksheet="inscritos", data=data_atualizada)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar inscrição: {str(e)}")
        return False
def verificar_inscricao_existente(participante):
    """Verifica se o participante já está inscrito"""
    inscritos, _ = ler_dados_sheets()
    return participante in inscritos['nome_participante'].values

def mostrar_inscricao_existente(participante):
    """Mostra os detalhes da inscrição existente do participante"""
    inscritos, _ = ler_dados_sheets()
    inscricao = inscritos[inscritos['nome_participante'] == participante].iloc[0]
    st.error("Você já está inscrito nas seguintes oficinas:")
    st.write(f"Dia 1 (30/10): {inscricao['oficina_dia1']}")
    st.write(f"Dia 2 (31/10): {inscricao['oficina_dia2']}")
    st.warning("Não é permitido realizar mais de uma inscrição por participante.")

def get_iniciais(nome):
    """Converte o nome completo para iniciais"""
    palavras = nome.split()
    iniciais = ' '.join(palavra[0].upper() for palavra in palavras)
    return iniciais

def get_participantes_ies(ies_selecionada):
    """Retorna lista de participantes da IES selecionada com suas iniciais"""
    _, lista_evento = ler_dados_sheets()
    co_ies = int(ies_selecionada.split(' - ')[0])
    
    # Filtrar participantes da IES
    participantes = lista_evento[lista_evento['co_ies'].astype(int) == co_ies]['no_pessoa_fisica'].tolist()
    
    # Criar dicionário com mapeamento de iniciais para nome completo
    if 'mapeamento_nomes' not in st.session_state:
        st.session_state.mapeamento_nomes = {}
    
    # Criar lista de iniciais mantendo o mapeamento
    participantes_iniciais = []
    for nome in participantes:
        iniciais = get_iniciais(nome)
        # Adicionar um contador se houver duplicata de iniciais
        base_iniciais = iniciais
        contador = 1
        while iniciais in st.session_state.mapeamento_nomes and \
              st.session_state.mapeamento_nomes[iniciais] != nome:
            iniciais = f"{base_iniciais} ({contador})"
            contador += 1
        
        st.session_state.mapeamento_nomes[iniciais] = nome
        participantes_iniciais.append(iniciais)
    
    return participantes_iniciais

def main():
    st.title("Inscrição em Oficinas IX Ences")

    # Seleção da IES
    ies_options = ["Selecione uma IES..."] + list(get_ies_list())
    ies = st.selectbox("Selecione sua Instituição", options=ies_options)

    if ies != "Selecione uma IES...":
        # Seleção do Participante
        participantes_iniciais = get_participantes_ies(ies)
        if participantes_iniciais:
            participante_iniciais = st.selectbox("Selecione o Participante", 
                                               options=["Selecione um participante..."] + participantes_iniciais)
            
            if participante_iniciais != "Selecione um participante...":
                # Recuperar o nome completo do participante
                nome_completo = st.session_state.mapeamento_nomes[participante_iniciais]
                
                # Verificar se o participante já está inscrito
                if verificar_inscricao_existente(nome_completo):
                    mostrar_inscricao_existente(nome_completo)
                    return  # Encerra o fluxo aqui se já estiver inscrito
                
                # Continua com o fluxo normal se não estiver inscrito
                # Oficina Dia 1
                oficinas_dia1 = get_oficinas_disponiveis(1)
                if not oficinas_dia1:
                    st.error("Não há mais vagas disponíveis para o primeiro dia!")
                    oficina_dia1 = st.selectbox("Escolha a oficina para o Dia 1 (30/10) *", 
                                              options=["Não há vagas disponíveis"], 
                                              key="oficina_dia1")
                else:
                    oficina_dia1 = st.selectbox("Escolha a oficina para o Dia 1 (30/10) *", 
                                              options=["Selecione uma oficina..."] + oficinas_dia1, 
                                              key="oficina_dia1")

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
                        oficina_dia2 = st.selectbox("Escolha a oficina para o Dia 2 (31/10) *", 
                                                  options=["Não há vagas disponíveis"], 
                                                  key="oficina_dia2")
                    else:
                        oficina_dia2 = st.selectbox("Escolha a oficina para o Dia 2 (31/10) *", 
                                                  options=["Selecione uma oficina..."] + oficinas_dia2_filtradas, 
                                                  key="oficina_dia2")

                    submitted = st.button("Salvar segundo Dia e Enviar Inscrição")

                    if submitted:
                        # Verificar novamente antes de salvar, por segurança
                        if verificar_inscricao_existente(nome_completo):
                            mostrar_inscricao_existente(nome_completo)
                            return

                        if oficina_dia1 in ["Não há vagas disponíveis", "Selecione uma oficina..."] or \
                           oficina_dia2 in ["Não há vagas disponíveis", "Selecione uma oficina..."]:
                            st.error("Por favor, selecione oficinas válidas nos dois dias!")
                            return

                        oficina_dia1_final = st.session_state.oficina_dia1_selecionada
                        oficina_dia2_final = oficina_dia2.split(" (")[0]

                        if adicionar_inscricao(ies, nome_completo, oficina_dia1_final, oficina_dia2_final):
                            st.success("Inscrição realizada com sucesso!")
                            st.balloons()

                            # Limpa o cache e força atualização
                            st.cache_data.clear()
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("Não foi possível realizar a inscrição. Por favor, tente novamente.")
                            st.cache_data.clear()
        else:
            st.error("Nenhum participante encontrado para esta IES")

if __name__ == "__main__":
    main()