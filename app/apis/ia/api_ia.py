import requests

from app.utils.config_sistema import get_config_sistema


def gerar_texto_ia(prompt):
    """
    Uso real da IA.
    Retorna apenas o texto da resposta.
    Se falhar, retorna string vazia.
    """

    try:
        config_sistema = get_config_sistema()

        api_ia = str(config_sistema.get('api_ia') or '').strip().lower()
        token_ia = str(config_sistema.get('token_ia') or '').strip()

        if not prompt:
            return ''

        if not api_ia or api_ia == 'nenhuma':
            return ''

        if not token_ia:
            return ''

        # =========================================
        # CHATGPT / OPENAI
        # =========================================
        if api_ia == 'chatgpt':
            try:
                url = "https://api.openai.com/v1/responses"

                payload = {
                    "model": "gpt-5.2-2025-12-11",
                    "input": str(prompt).strip()
                }

                headers = {
                    "Authorization": f"Bearer {token_ia}",
                    "Content-Type": "application/json"
                }

                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=45
                )

                if not response.ok:
                    return ''

                data = response.json()

                texto = ''

                if data.get('output') and isinstance(data['output'], list):
                    for output_item in data['output']:
                        for content_item in output_item.get('content', []):
                            if content_item.get('text'):
                                texto += (content_item.get('text') or '')

                return texto.strip()

            except Exception:
                return ''

        # =========================================
        # GEMINI
        # =========================================
        if api_ia == 'gemini':
            try:
                model = "gemini-2.5-flash"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

                payload = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {"text": str(prompt).strip()}
                            ]
                        }
                    ]
                }

                headers = {
                    "x-goog-api-key": token_ia,
                    "Content-Type": "application/json"
                }

                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=45
                )

                if not response.ok:
                    return ''

                data = response.json()

                texto = (
                    data.get('candidates', [{}])[0]
                    .get('content', {})
                    .get('parts', [{}])[0]
                    .get('text', '')
                )

                return str(texto).strip()

            except Exception:
                return ''

        return ''

    except Exception:
        return ''