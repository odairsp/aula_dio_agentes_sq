import streamlit as st
import mysql.connector
import openai
import os
from dotenv import load_dotenv
import json

load_dotenv()

# --- CONFIGURAÇÃO DA PÁGINA STREAMLIT ---

# Configuração inicial
st.set_page_config(page_title="dioBank Consultas", page_icon="🏛️")
st.title("🏛️ dioBank Consultas")

# --- CONFIGURAÇÃO DA SIDEBAR (INSERÇÃO DE CREDENCIAIS) ---

# Sidebar para credenciais
st.sidebar.header("🔐 Configurações")
openai_api_key = st.sidebar.text_input("Chave da API OpenAI", type="password")
mysql_host = st.sidebar.text_input("MySQL Host", value="localhost")
mysql_user = st.sidebar.text_input("Usuário MySQL", value="root")
mysql_password = st.sidebar.text_input("Senha MySQL", type="password")
mysql_db = st.sidebar.text_input("Nome do Banco de Dados", value="dioBank")


# --- MEIO: INTERAÇÃO COM O USUÁRIO E ENTRADA DA PERGUNTA ---

# Sessão para manter pergunta sugerida
if "pergunta" not in st.session_state:
    st.session_state.pergunta = ""

# Sugestões de perguntas como no GPT
st.markdown("### 💬 Sugestões de perguntas")
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("📋 Clientes"):
        st.session_state.pergunta = "Me mostre todos os clientes"
with col2:
    if st.button("💸 Pagamentos"):
        st.session_state.pergunta = "Me mostre todos os pagamentos"
with col3:
    if st.button("🏠 Endereços"):
        st.session_state.pergunta = "Me mostre todos os endereços"
with col4:
    if st.button("📈 Movimentações"):
        st.session_state.pergunta = "Me mostre todas as movimentações"

# Campo de pergunta
st.markdown("### ✍️ Pergunta personalizada")
pergunta = st.text_input("Digite sua pergunta em linguagem natural:", 
                         value=st.session_state.pergunta, 
                         key="input_pergunta")

# --- FUNÇÕES AUXILIARES ---



# Função para obter estrutura das tabelas
def obter_estruturas_tabelas():
    try:
        conn = mysql.connector.connect(
            host=mysql_host,
            user=mysql_user,
            password=mysql_password,
            database=mysql_db
        )
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES;")
        tabelas = cursor.fetchall()

        colunas = {}
        for tabela in tabelas:
            cursor.execute(f"DESCRIBE {tabela[0]};")
            colunas_tabela = cursor.fetchall()
            colunas[tabela[0]] = [coluna[0] for coluna in colunas_tabela]

        cursor.close()
        conn.close()
        return colunas
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return {}
    
# Função para carregar o prompt salvo (contexto para o modelo da OpenAI)    

# Carregar contexto dos prompts
def carregar_prompt():
    try:
        with open("protocolos/prompt.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Erro ao carregar o contexto do prompt: {e}")
        return {}

# Gerar query SQL
def gerar_query_sql(pergunta, colunas):
    openai.api_key = (openai_api_key)
    prompt = carregar_prompt()

    instrucoes_adicionais = "\n- " + "\n- ".join(prompt.get("instrucoes_sql", []))

    contexto = f"""
Sistema: {prompt.get('system_name', 'Desconhecido')}
Função do modelo: {prompt.get('model_role', '')}
Perfil do usuário: {prompt.get('user_profile', {})}
Restrições: {'; '.join(prompt.get('restricoes', []))}

Instruções adicionais para gerar SQL corretamente:
{instrucoes_adicionais}

Base de dados:
{json.dumps(colunas, indent=2, ensure_ascii=False)}

Pergunta do usuário:
{pergunta}

Gere uma consulta SQL correspondente:
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt.get('model_role', "Você é um assistente de SQL.")},
                {"role": "user", "content": contexto}
            ],
            max_tokens=300,
            temperature=0
        )
        query = response.choices[0].message.content.strip()
        return query.replace("```sql", "").replace("```", "").strip()
    except Exception as e:
        st.error(f"Erro ao gerar a query SQL: {e}")
        return ""

#  Função que executa a query SQL no banco e retorna os resultados

# Executar query no MySQL
def executar_query(query):
    if not query:
        st.warning("⚠️ A consulta SQL está vazia. Verifique sua pergunta ou o contexto.")
        return [], []

    try:
        conn = mysql.connector.connect(
            host=mysql_host,
            user=mysql_user,
            password=mysql_password,
            database=mysql_db
        )
        cursor = conn.cursor()
        cursor.execute(query)
        resultados = cursor.fetchall()
        colunas = [desc[0] for desc in cursor.description]
        cursor.close()
        conn.close()
        return colunas, resultados
    except Exception as e:
        st.error(f"Erro ao executar a query SQL: {e}")
        return [], []

# Salvar histórico
# Salvar histórico
def salvar_historico(pergunta, query, resultado):
    try:
        conn = mysql.connector.connect(
            host=mysql_host,
            user=mysql_user,
            password=mysql_password,
            database=mysql_db
        )
        cursor = conn.cursor()
        
        # Garantir criação e tipo correto da tabela
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_interacoes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                pergunta TEXT,
                query_gerada TEXT,
                resultado LONGTEXT,
                feedback VARCHAR(10),
                data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        
        cursor.execute("""
            INSERT INTO historico_interacoes (pergunta, query_gerada, resultado)
            VALUES (%s, %s, %s)
        """, (pergunta, query, str(resultado)))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        st.error(f"Erro ao salvar histórico: {e}")


# Salvar feedback
def salvar_feedback(pergunta, feedback):
    try:
        conn = mysql.connector.connect(
            host=mysql_host,
            user=mysql_user,
            password=mysql_password,
            database=mysql_db
        )
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE historico_interacoes
            SET feedback = %s
            WHERE pergunta = %s
            ORDER BY data DESC LIMIT 1;
        """, (feedback, pergunta))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        st.error(f"Erro ao salvar feedback: {e}")


# --- FIM: EXECUÇÃO PRINCIPAL DA LÓGICA ---

# Execução principal
if pergunta:
    estrutura = obter_estruturas_tabelas()
    if estrutura:
        query = gerar_query_sql(pergunta, estrutura)

        # Botão para exibir ou não a query SQL
        mostrar_sql = st.toggle("👁️ Mostrar consulta SQL")
        if mostrar_sql:
            st.code(query, language="sql")

        colunas, resultados = executar_query(query)

        if resultados:
            st.success("✅ Consulta realizada com sucesso!")
            st.dataframe([dict(zip(colunas, row)) for row in resultados])
            salvar_historico(pergunta, query, resultados)
        else:
            st.warning("Nenhum resultado encontrado.")

        feedback = st.radio("Essa resposta foi útil?", ("👍 Sim", "👎 Não"), key="feedback")
        salvar_feedback(pergunta, feedback)
