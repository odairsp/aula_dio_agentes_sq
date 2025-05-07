import openai
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

# Função para chamar a API do OpenAI e gerar a query SQL
def gerar_query_sql(pergunta: str, colunas: dict) -> str:
    openai.api_key = os.getenv("OPENAI_API_KEY")  # Sua chave da API OpenAI
    
    # Criação do prompt para o OpenAI, incluindo as colunas do banco
    prompt = f"""
Você é um assistente de SQL que opera para o banco de dados ficticio chamado Dio Bank.
Você deve gerar queries baseadas na seguinte estrutura do banco de dados:
{colunas}

Pergunta: {pergunta}
Resposta em SQL:
"""
    
    # Usando a nova API do OpenAI para chat
    response = openai.ChatCompletion.create(
        model="gpt-4.1",  # Pode usar o modelo mais recente
        messages=[
            {"role": "system", "content": "Você é um assistente de SQL."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=150,
        temperature=0
    )

    # Obtendo a resposta gerada
    query = response['choices'][0]['message']['content'].strip()
    
    # Remover qualquer marcação de código (```sql ou ``` no final)
    query = query.replace("```sql", "").replace("```", "").strip()
    
    return query

# Função para obter as tabelas e colunas do banco de dados
def obter_estruturas_tabelas() -> dict:
    try:
        conn = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DB")
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
        return f"Erro ao obter estrutura das tabelas: {e}"

# Função simples que executa a query SQL
def executar_query_func(query: str) -> str:
    """Executa uma query SQL real no banco MySQL e retorna os resultados."""
    try:
        conn = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", "admin123"),
            database=os.getenv("MYSQL_DB", "dioBank")
        )
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall() #recupera todos os resultados de uma consulta SQL já executada.
        cursor.close()
        conn.close()

        return results
    except:
        print('erro')

# Exemplo de interação com o agente
pergunta = input("Realize a sua pergunta ao nosso agente: ")

# Gerar a query com base nas colunas
query_gerada = gerar_query_sql(pergunta, obter_estruturas_tabelas())

print(f"\nQUERY GERADA: `{query_gerada}`")
print(f"\nRESULTADO")

# Executar a query no banco de dados
print(executar_query_func(query_gerada))
