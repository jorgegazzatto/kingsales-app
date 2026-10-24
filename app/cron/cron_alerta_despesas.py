import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.database.conexao import conectar
from app.apis.whatsapp.texto import enviar_whatsapp_texto
from app.apis.email.texto import enviar_email_texto
from app.utils.config_sistema import get_config_sistema
from datetime import datetime


def formatar_valor(valor):
    valor = float(valor or 0)
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_data(data):
    if not data:
        return ""
    return data.strftime("%d/%m/%Y")


def enviar_alertas_despesas():
    conexao = None
    cursor = None

    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        print(f"[CRON] Iniciando alerta de despesas - {datetime.now()}")

        config = get_config_sistema()

        nome_sistema = (config.get("nome_sistema") or "Sistema").strip()
        telefone_admin = config.get("telefone_sistema")
        email_admin = config.get("email_sistema")

        cursor.execute("""
            SELECT 
                d.id,
                d.descricao,
                d.valor,
                d.subtotal,
                d.data_vencimento,
                d.hora_lembrete,
                d.alertado
            FROM despesas d
            WHERE d.ativo = 'Sim'
              AND d.data_pagamento IS NULL
              AND d.data_vencimento = CURDATE()
              AND (d.alertado IS NULL OR d.alertado != 'Sim')
              AND d.hora_lembrete IS NOT NULL
              AND d.hora_lembrete <= CURTIME()
            ORDER BY d.hora_lembrete ASC, d.id ASC
        """)

        despesas = cursor.fetchall()

        print(f"[CRON] Despesas encontradas: {len(despesas)}")

        total_enviadas = 0

        for despesa in despesas:
            despesa_id = despesa.get("id")
            descricao = despesa.get("descricao") or "Despesa"
            valor = despesa.get("subtotal") or despesa.get("valor") or 0

            valor_formatado = formatar_valor(valor)
            vencimento_formatado = formatar_data(despesa.get("data_vencimento"))

            mensagem_whatsapp = f"""⚠️ *{nome_sistema.upper()}*

*LEMBRETE DE DESPESA*

Uma despesa vence hoje.

📌 *Descrição:* {descricao}
💰 *Valor:* {valor_formatado}
📅 *Vencimento:* {vencimento_formatado}

Verifique e realize o pagamento para evitar atrasos.
"""

            assunto = f"{nome_sistema} - Despesa com vencimento hoje"

            mensagem_html = f"""
            <p><strong>{nome_sistema}</strong></p>

            <p>Existe uma despesa com vencimento hoje.</p>

            <p>
                <strong>Descrição:</strong> {descricao}<br>
                <strong>Valor:</strong> {valor_formatado}<br>
                <strong>Vencimento:</strong> {vencimento_formatado}
            </p>

            <p>Verifique e realize o pagamento para evitar atrasos.</p>
            """

            mensagem_texto = f"""
{nome_sistema}

Despesa com vencimento hoje

Descrição: {descricao}
Valor: {valor_formatado}
Vencimento: {vencimento_formatado}

Verifique e realize o pagamento.
"""

            enviou = False

            try:
                if telefone_admin:
                    enviar_whatsapp_texto(telefone_admin, mensagem_whatsapp)
                    enviou = True
            except Exception as e:
                print(f"[CRON ERRO WHATSAPP] Despesa {despesa_id}: {str(e)}")

            try:
                if email_admin:
                    enviar_email_texto(email_admin, assunto, mensagem_html, mensagem_texto)
                    enviou = True
            except Exception as e:
                print(f"[CRON ERRO EMAIL] Despesa {despesa_id}: {str(e)}")

            if enviou:
                cursor.execute("""
                    UPDATE despesas
                    SET alertado = 'Sim'
                    WHERE id = %s
                """, (despesa_id,))

                total_enviadas += 1

                print(f"[CRON] Alerta enviado para despesa ID {despesa_id}")
            else:
                print(f"[CRON] Sem contato configurado para envio.")

        conexao.commit()

        print(f"[CRON] Total alertas enviados: {total_enviadas}")
        print(f"[CRON] Finalizado com sucesso - {datetime.now()}")

    except Exception as e:
        if conexao:
            conexao.rollback()

        print(f"[CRON ERRO] {str(e)}")

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()


if __name__ == "__main__":
    enviar_alertas_despesas()