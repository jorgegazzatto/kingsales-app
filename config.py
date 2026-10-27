import os

# DADOS DO SISTEMA
MODO_TESTE = os.getenv("MODO_TESTE", "Não")
NOME_SISTEMA = os.getenv("NOME_SISTEMA", "Sistema Python")
EMAIL_SISTEMA = os.getenv("EMAIL_SISTEMA", "jorgeluizfilho@hotmail.com")
SENHA_PADRAO = os.getenv("SENHA_PADRAO", "123")
COR_PRIMARIA = os.getenv("COR_PRIMARIA", "#0d6efd")
COR_SECUNDARIA = os.getenv("COR_SECUNDARIA", "#1d4688")

# DADOS DO BANCO
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    from urllib.parse import urlparse, unquote
    parsed_url = urlparse(DATABASE_URL)
    DB_HOST = parsed_url.hostname or "localhost"
    DB_PORT = parsed_url.port or 3306
    DB_USER = unquote(parsed_url.username) if parsed_url.username else "root"
    DB_PASSWORD = unquote(parsed_url.password) if parsed_url.password else ""
    DB_NAME = parsed_url.path.lstrip('/') if parsed_url.path else "python"
else:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "1234")
    DB_NAME = os.getenv("DB_NAME", "python")

DDI_TELEFONE = os.getenv("DDI_TELEFONE", "55")

CHAVE_CRIPTOGRAFIA = os.getenv("CHAVE_CRIPTOGRAFIA", "jR_TEeAlIZtm4HZJ6gavFrX02nxyX5xp7Lux_Tw_ZtU=")
SECRET_KEY = os.getenv("SECRET_KEY", "kingsales-secret-key-change-in-prod")