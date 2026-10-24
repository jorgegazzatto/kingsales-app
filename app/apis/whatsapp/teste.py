import requests
import re
from config import DDI_TELEFONE

def limpar_numero(numero):
    return re.sub(r'\D+', '', numero or '')


def normalizar_numero_whatsapp(numero, ddi='55'):
    numero = re.sub(r'\D+', '', numero or '')

    if not numero:
        return ''

    ddi = re.sub(r'\D+', '', ddi or '')

    if ddi and numero.startswith(ddi):
        return numero

    return f"{ddi}{numero}" if ddi else numero

def testar_whatsapp(dados):
    api = dados.get('api_whatsapp')
    token = (dados.get('token_whatsapp') or '').strip()
    instancia = (dados.get('instancia_whatsapp') or '').strip()
    url_api = (dados.get('url_api') or '').strip()

    telefone = normalizar_numero_whatsapp(dados.get('telefone'), DDI_TELEFONE)
    mensagem = f'Teste de envio WhatsApp - API {api}'

    retorno = {
        'api': api,
        'ok': False,
        'msg': 'Não executado',
        'http': None,
        'raw': None
    }

    try:

        # =========================
        # MENUIA
        # =========================
        if api == 'menuia':

            url = "https://chatbot.menuia.com/api/create-message"

            payload = {
                "appkey": token,
                "authkey": instancia,
                "to": telefone,
                "message": mensagem
            }

            response = requests.post(url, json=payload, timeout=30)

            retorno['http'] = response.status_code
            retorno['raw'] = response.text

            if response.ok:
                json_resp = response.json()
                if json_resp.get('status') == 200:
                    retorno['ok'] = True
                    retorno['msg'] = json_resp.get('message', 'Enviado com sucesso')
                else:
                    retorno['msg'] = json_resp.get('message', 'Erro desconhecido')
            else:
                retorno['msg'] = f"Erro HTTP {response.status_code}"

        # =========================
        # META (OFICIAL)
        # =========================
        elif api == 'meta':

            phone_id = instancia
            url = f"https://graph.facebook.com/v22.0/{phone_id}/messages"

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            payload = {
                "messaging_product": "whatsapp",
                "to": telefone,
                "type": "template",
                "template": {
                    "name": "hello_world",
                    "language": {"code": "en_US"}
                }
            }

            response = requests.post(url, json=payload, headers=headers, timeout=30)

            retorno['http'] = response.status_code
            retorno['raw'] = response.text

            if response.ok:
                retorno['ok'] = True
                retorno['msg'] = 'Mensagem enviada com sucesso'
            else:
                try:
                    erro = response.json()
                    retorno['msg'] = erro.get('error', {}).get('message', 'Erro desconhecido')
                except:
                    retorno['msg'] = f"Erro HTTP {response.status_code}"

        # =========================
        # EVOLUTION
        # =========================
        elif api == 'evolution':

            if not url_api or not instancia or not token:
                retorno['msg'] = 'URL, Instância ou Token não configurados.'
                return retorno

            url = f"{url_api.rstrip('/')}/message/sendText/{instancia}"

            headers = {
                "Content-Type": "application/json",
                "apikey": token
            }

            payload = {
                "number": telefone,
                "text": mensagem
            }

            response = requests.post(url, json=payload, headers=headers, timeout=30)

            retorno['http'] = response.status_code
            retorno['raw'] = response.text

            if response.ok:
                retorno['ok'] = True
                retorno['msg'] = 'WhatsApp (Evolution): enviado com sucesso'
            else:
                retorno['msg'] = f"Erro HTTP {response.status_code}"

        else:
            retorno['msg'] = 'Nenhuma API selecionada'

    except Exception as e:
        retorno['msg'] = f"Erro: {str(e)}"

    return retorno