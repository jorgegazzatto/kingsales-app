import mysql.connector 
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT

def conectar():
    conexao = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    return conexao