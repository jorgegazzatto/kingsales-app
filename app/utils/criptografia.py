from cryptography.fernet import Fernet
from config import CHAVE_CRIPTOGRAFIA

fernet = Fernet(CHAVE_CRIPTOGRAFIA.encode())


def criptografar_texto(texto):
    if not texto:
        return ''
    return fernet.encrypt(texto.encode()).decode()


def descriptografar_texto(texto_criptografado):
    if not texto_criptografado:
        return ''
    try:
        return fernet.decrypt(texto_criptografado.encode()).decode()
    except Exception:
        return ''