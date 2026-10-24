import requests


def testar_ia(dados):
    """
    Teste/debug da IA.
    Retorna estrutura completa com:
    ok, msg, http, raw, text, api
    """

    retorno = {
        'api': None,
        'ok': False,
        'msg': 'IA: não executada.',
        'http': None,
        'text': '',
        'raw': None
    }

    try:
        prompt = str(dados.get('prompt') or '').strip()
        api_ia = str(dados.get('api_ia') or '').strip().lower()
        token_ia = str(dados.get('token_ia') or '').strip()

        retorno['api'] = api_ia

        if not prompt:
            retorno['msg'] = 'IA: informe um prompt.'
            return retorno

        if not api_ia or api_ia == 'nenhuma':
            retorno['msg'] = 'IA: nenhuma API selecionada.'
            return retorno

        if not token_ia:
            retorno['msg'] = 'IA: token não configurado.'
            return retorno

        # =========================================
        # CHATGPT / OPENAI
        # =========================================
        if api_ia == 'chatgpt':
            try:
                url = "https://api.openai.com/v1/responses"

                payload = {
                    "model": "gpt-5.2-2025-12-11",
                    "input": prompt
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

                retorno['http'] = response.status_code
                retorno['raw'] = response.text

                try:
                    data = response.json()
                except Exception:
                    retorno['msg'] = f"ChatGPT: retorno inválido (HTTP {response.status_code})."
                    return retorno

                if not response.ok:
                    erro = data.get('error', {}).get('message', 'Erro desconhecido.')
                    retorno['msg'] = f"ChatGPT: falhou (HTTP {response.status_code}) - {erro}"
                    return retorno

                texto = ''

                if data.get('output') and isinstance(data['output'], list):
                    for output_item in data['output']:
                        for content_item in output_item.get('content', []):
                            if content_item.get('text'):
                                texto += (content_item.get('text') or '')

                texto = texto.strip()

                if not texto:
                    retorno['msg'] = "ChatGPT: ok, mas não retornou texto."
                    return retorno

                retorno['ok'] = True
                retorno['text'] = texto
                retorno['msg'] = "ChatGPT: ok."
                return retorno

            except requests.RequestException as e:
                retorno['msg'] = f"ChatGPT: erro de conexão - {str(e)}"
                return retorno

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
                                {"text": prompt}
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

                retorno['http'] = response.status_code
                retorno['raw'] = response.text

                try:
                    data = response.json()
                except Exception:
                    retorno['msg'] = f"Gemini: retorno inválido (HTTP {response.status_code})."
                    return retorno

                if not response.ok:
                    erro = data.get('error', {}).get('message', 'Erro desconhecido.')
                    retorno['msg'] = f"Gemini: falhou (HTTP {response.status_code}) - {erro}"
                    return retorno

                texto = (
                    data.get('candidates', [{}])[0]
                    .get('content', {})
                    .get('parts', [{}])[0]
                    .get('text', '')
                )

                texto = str(texto).strip()

                if not texto:
                    retorno['msg'] = "Gemini: resposta vazia."
                    return retorno

                retorno['ok'] = True
                retorno['text'] = texto
                retorno['msg'] = "Gemini: ok."
                return retorno

            except requests.RequestException as e:
                retorno['msg'] = f"Gemini: erro de conexão - {str(e)}"
                return retorno

        retorno['msg'] = f"IA: api_ia inválida ('{api_ia}'). Use 'chatgpt' ou 'gemini'."
        return retorno

    except Exception as e:
        retorno['msg'] = f"IA: erro interno - {str(e)}"
        return retorno