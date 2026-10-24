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


def enviar_alertas_recebimentos():
    conexao = None
    cursor = None

    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        print(f"[CRON] Iniciando alerta de recebimentos - {datetime.now()}")

        config = get_config_sistema()
        nome_sistema = (config.get("nome_sistema") or "Sistema").strip()

        tipo_dados_pagamento = (config.get("tipo_dados_pagamento") or "").strip()
        dados_pagamento = (config.get("dados_pagamento") or "").strip()
        beneficiario = (config.get("beneficiario") or "").strip()

        tipo_label = "Dados para pagamento"

        if tipo_dados_pagamento == "pix":
            tipo_label = "PIX"
        elif tipo_dados_pagamento == "conta":
            tipo_label = "Conta Bancária"

        bloco_pagamento_whatsapp = ""
        bloco_pagamento_html = ""
        bloco_pagamento_texto = ""

        if dados_pagamento or beneficiario:
            bloco_pagamento_whatsapp = f"""

💳 *{tipo_label}*
{dados_pagamento}

👤 *Beneficiário*
{beneficiario}
"""

            bloco_pagamento_html = f"""
            <p>
                <strong>💳 {tipo_label}</strong><br>
                {dados_pagamento.replace(chr(10), '<br>')}
            </p>

            <p>
                <strong>👤 Beneficiário</strong><br>
                {beneficiario}
            </p>
            """

            bloco_pagamento_texto = f"""

Dados para pagamento:
{tipo_label}
{dados_pagamento}

Beneficiário:
{beneficiario}
"""

        cursor.execute("""
            SELECT 
                r.id,
                r.descricao,
                r.valor,
                r.subtotal,
                r.data_vencimento,
                r.hora_lembrete,
                r.alertado,
                c.nome AS cliente_nome,
                c.email AS cliente_email,
                c.telefone AS cliente_telefone,
                c.whatsapp AS cliente_whatsapp
            FROM recebimentos r
            LEFT JOIN clientes c ON r.cliente = c.id
            WHERE r.ativo = 'Sim'
              AND r.data_pagamento IS NULL
              AND r.data_vencimento = CURDATE()
              AND (r.alertado IS NULL OR r.alertado != 'Sim')
              AND r.hora_lembrete IS NOT NULL
              AND r.hora_lembrete <= CURTIME()
            ORDER BY r.hora_lembrete ASC, r.id ASC
        """)

        contas = cursor.fetchall()

        print(f"[CRON] Contas encontradas para alerta: {len(contas)}")

        total_enviadas = 0

        for conta in contas:
            conta_id = conta.get("id")
            cliente_nome = conta.get("cliente_nome") or "Cliente"
            cliente_email = conta.get("cliente_email")
            cliente_whatsapp = conta.get("cliente_whatsapp") or conta.get("cliente_telefone")

            descricao = conta.get("descricao") or "Conta em aberto"
            valor = conta.get("subtotal") or conta.get("valor") or 0
            valor_formatado = formatar_valor(valor)
            vencimento_formatado = formatar_data(conta.get("data_vencimento"))

            mensagem_whatsapp = f"""🔔 *{nome_sistema.upper()}*

*LEMBRETE DE VENCIMENTO*

Olá *{cliente_nome}*.

Estamos passando para lembrar que existe uma conta com vencimento para hoje.

📌 *Descrição:* {descricao}
💰 *Valor:* {valor_formatado}
📅 *Vencimento:* {vencimento_formatado}

Evite atrasos realizando o pagamento até o final do dia.
{bloco_pagamento_whatsapp}

Caso já tenha realizado o pagamento, desconsidere esta mensagem.
"""

            assunto = f"{nome_sistema} - Lembrete de vencimento"

            mensagem_html = f"""
            <p><strong>{nome_sistema}</strong></p>

            <p>Olá <strong>{cliente_nome}</strong>,</p>

            <p>Estamos passando para lembrar que existe uma conta com vencimento para hoje.</p>

            <p>
                <strong>Descrição:</strong> {descricao}<br>
                <strong>Valor:</strong> {valor_formatado}<br>
                <strong>Vencimento:</strong> {vencimento_formatado}
            </p>

            <p>Evite atrasos realizando o pagamento até o final do dia.</p>

            {bloco_pagamento_html}

            <p>Caso já tenha realizado o pagamento, desconsidere esta mensagem.</p>
            """

            mensagem_texto = f"""
{nome_sistema}

Olá {cliente_nome}

Estamos passando para lembrar que existe uma conta com vencimento para hoje.

Descrição: {descricao}
Valor: {valor_formatado}
Vencimento: {vencimento_formatado}

Evite atrasos realizando o pagamento até o final do dia.
{bloco_pagamento_texto}

Caso já tenha realizado o pagamento, desconsidere esta mensagem.
"""

            enviou = False

            try:
                if cliente_whatsapp:
                    enviar_whatsapp_texto(cliente_whatsapp, mensagem_whatsapp)
                    enviou = True
            except Exception as e:
                print(f"[CRON ERRO WHATSAPP] Conta {conta_id}: {str(e)}")

            try:
                if cliente_email:
                    enviar_email_texto(cliente_email, assunto, mensagem_html, mensagem_texto)
                    enviou = True
            except Exception as e:
                print(f"[CRON ERRO EMAIL] Conta {conta_id}: {str(e)}")

            if enviou:
                cursor.execute("""
                    UPDATE recebimentos
                    SET alertado = 'Sim'
                    WHERE id = %s
                """, (conta_id,))

                total_enviadas += 1

                print(f"[CRON] Alerta enviado para conta ID {conta_id} - {cliente_nome}")
            else:
                print(f"[CRON] Conta ID {conta_id} sem e-mail/WhatsApp para envio.")

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
    enviar_alertas_recebimentos()