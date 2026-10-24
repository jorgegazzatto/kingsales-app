from app.database.conexao import conectar
from config import NOME_SISTEMA, EMAIL_SISTEMA, COR_PRIMARIA, COR_SECUNDARIA, DDI_TELEFONE
from datetime import timedelta


def formatar_hora_input(valor):
    if not valor:
        return ''

    # Se vier como timedelta do mysql.connector
    if isinstance(valor, timedelta):
        total_segundos = int(valor.total_seconds())
        horas = total_segundos // 3600
        minutos = (total_segundos % 3600) // 60
        return f'{horas:02d}:{minutos:02d}'

    # Se vier como string
    valor = str(valor).strip()

    if not valor:
        return ''

    partes = valor.split(':')

    if len(partes) >= 2:
        horas = partes[0].zfill(2)
        minutos = partes[1].zfill(2)
        return f'{horas}:{minutos}'

    return ''


def get_config_sistema():
    config_padrao = {
        'nome_sistema': NOME_SISTEMA,
        'email_sistema': EMAIL_SISTEMA,
        'telefone_sistema': '',
        'endereco_sistema': '',
        'logo': '',
        'icone': '',
        'cor_primaria': COR_PRIMARIA,
        'cor_secundaria': COR_SECUNDARIA,
        'ddi_telefone': DDI_TELEFONE,
        'api_whatsapp': '',
        'token_whatsapp': '',
        'instancia_whatsapp': '',
        'url_api': '',
        'api_ia': '',
        'token_ia': '',
        'smtp_host': '',
        'smtp_senha': '',
        'smtp_porta': '',
        'smtp_seguranca': '',
        'dias_excluir_logs': '',
        'rel_html_pdf': '',
        'hora_inicial_alerta': '',
        'hora_final_alerta': '',
        'tipo_dados_pagamento': '',
        'dados_pagamento': '',
        'beneficiario': '',
    }

    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("SELECT * FROM config LIMIT 1")
        config_db = cursor.fetchone()

        cursor.close()
        conexao.close()

        if config_db:
            config_db['hora_inicial_alerta'] = formatar_hora_input(config_db.get('hora_inicial_alerta'))
            config_db['hora_final_alerta'] = formatar_hora_input(config_db.get('hora_final_alerta'))
            return config_db

        return config_padrao

    except Exception:
        return config_padrao