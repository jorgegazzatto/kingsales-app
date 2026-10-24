#Manipular caminhos e arquivos do sistema operacional.
import os

#Gerar nomes únicos para arquivos.
import uuid

#Sanitizar (limpar) o nome do arquivo enviado pelo usuário. evitar arquivo malicioso
from werkzeug.utils import secure_filename

#para redimensionar imagem
from PIL import Image

def salvar_arquivo(
    arquivo,
    pasta_destino,
    extensoes_permitidas=None,
    largura_maxima=None
):
    if not arquivo or not arquivo.filename:
        return {
            'sucesso': False,
            'arquivo': None,
            'mensagem': 'Nenhum arquivo enviado.'
        }

    nome_original = secure_filename(arquivo.filename)
    extensao = os.path.splitext(nome_original)[1].lower()

    if extensoes_permitidas and extensao not in extensoes_permitidas:
        return {
            'sucesso': False,
            'arquivo': None,
            'mensagem': 'Formato de arquivo inválido.'
        }

    os.makedirs(pasta_destino, exist_ok=True)

    nome_arquivo = f"{uuid.uuid4().hex}{extensao}"
    caminho_arquivo = os.path.join(pasta_destino, nome_arquivo)

    imagem = Image.open(arquivo)

    largura_original, altura_original = imagem.size

    if largura_maxima and largura_original > largura_maxima:
        proporcao = largura_maxima / largura_original
        nova_largura = largura_maxima
        nova_altura = int(altura_original * proporcao)
        imagem = imagem.resize((nova_largura, nova_altura), Image.LANCZOS)

    if extensao in ['.jpg', '.jpeg'] and imagem.mode in ('RGBA', 'LA', 'P'):
        imagem = imagem.convert('RGB')

    imagem.save(caminho_arquivo, quality=90, optimize=True)

    return {
        'sucesso': True,
        'arquivo': nome_arquivo,
        'caminho': caminho_arquivo,
        'mensagem': 'Arquivo salvo com sucesso.'
    }


def excluir_arquivo(nome_arquivo, pasta_destino, arquivos_protegidos=None):
    if not nome_arquivo:
        return

    if arquivos_protegidos is None:
        arquivos_protegidos = []

    if nome_arquivo in arquivos_protegidos:
        return

    caminho_arquivo = os.path.join(pasta_destino, nome_arquivo)

    if os.path.exists(caminho_arquivo) and os.path.isfile(caminho_arquivo):
        os.remove(caminho_arquivo)