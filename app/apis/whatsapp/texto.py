import re
import requests

from app.utils.config_sistema import get_config_sistema


def limpar_numero(numero):
    return re.sub(r'\D+', '', str(numero or ''))


def enviar_whatsapp_texto(telefone, mensagem):
    """
    Envio silencioso de WhatsApp.
    Recebe apenas telefone e mensagem.
    Todo o restante é buscado nas configurações do sistema.
    Se falhar, apenas ignora.
    """

    try:
        config_sistema = get_config_sistema()

        api_whatsapp = str(config_sistema.get('api_whatsapp') or '').strip().lower()
        token_whatsapp = str(config_sistema.get('token_whatsapp') or '').strip()
        instancia_whatsapp = str(config_sistema.get('instancia_whatsapp') or '').strip()
        url_api = str(config_sistema.get('url_api') or '').strip()
        ddi_telefone = limpar_numero(config_sistema.get('ddi_telefone') or '55')

        telefone_disparo = limpar_numero(telefone)
        mensagem_whatsapp = str(mensagem or '').strip()

        if not api_whatsapp:
            return True

        if api_whatsapp not in ['menuia', 'evolution', 'meta']:
            return True

        if not telefone_disparo or not mensagem_whatsapp:
            return True

        numero_completo = limpar_numero(f"{ddi_telefone}{telefone_disparo}")
        

        # =========================
        # MENUIA
        # =========================
        if api_whatsapp == 'menuia':
            try:
                url = "https://chatbot.menuia.com/api/create-message"

                payload = {
                    "appkey": token_whatsapp,
                    "authkey": instancia_whatsapp,
                    "to": numero_completo,
                    "message": mensagem_whatsapp
                }

                requests.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
            except Exception:
                pass

            return True

        # =========================
        # EVOLUTION
        # =========================
        if api_whatsapp == 'evolution':
            try:
                url_base = url_api.rstrip('/')

                if not url_base or not instancia_whatsapp or not token_whatsapp:
                    return True

                url = f"{url_base}/message/sendText/{instancia_whatsapp}"

                payload = {
                    "number": numero_completo,
                    "text": mensagem_whatsapp
                }

                headers = {
                    "Content-Type": "application/json",
                    "apikey": token_whatsapp
                }

                requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=30
                )
            except Exception:
                pass

            return True

        # =========================
        # META
        # =========================
        if api_whatsapp == 'meta':
            try:
                phone_number_id = instancia_whatsapp
                meta_token = re.sub(r'\s+', '', token_whatsapp)

                if not phone_number_id or not meta_token:
                    return True

                url = f"https://graph.facebook.com/v22.0/{phone_number_id}/messages"

                payload = {
                    "messaging_product": "whatsapp",
                    "to": numero_completo,
                    "type": "template",
                    "template": {
                        "name": "hello_world",
                        "language": {
                            "code": "en_US"
                        }
                    }
                }

                headers = {
                    "Authorization": f"Bearer {meta_token}",
                    "Content-Type": "application/json"
                }

                requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=30
                )
            except Exception:
                pass

            return True

        return True

    except Exception:
        return True