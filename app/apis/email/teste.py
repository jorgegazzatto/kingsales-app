import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.utils.criptografia import descriptografar_texto


def testar_email_smtp(dados):
    retorno = {
        'ok': False,
        'msg': 'Não executado',
        'http': None,
        'raw': None
    }

    try:
        smtp_host = str(dados.get('smtp_host') or '').strip()
        smtp_porta = dados.get('smtp_porta')
        smtp_seguranca = str(dados.get('smtp_seguranca') or '').strip().lower()
        smtp_senha = str(dados.get('smtp_senha') or '').strip()
        email_remetente = str(dados.get('email_sistema') or '').strip()
        email_destino = str(dados.get('email_sistema') or '').strip()

        if not smtp_host or not smtp_porta or not email_remetente or not email_destino:
            retorno['msg'] = 'Host, porta, e-mail do sistema ou e-mail de destino não informados.'
            return retorno

        try:
            smtp_porta = int(smtp_porta)
        except Exception:
            retorno['msg'] = 'Porta SMTP inválida.'
            return retorno

        # Se vier vazio, só tenta com vazio
        senha_final = smtp_senha

        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Teste de SMTP'
        msg['From'] = email_remetente
        msg['To'] = email_destino

        html = f"""
        <p>Olá!</p>
        <p>Este é um <strong>teste de envio SMTP</strong> do sistema.</p>
        <p>Se você recebeu este e-mail, a configuração está funcionando corretamente. ✅</p>
        """

        texto = """Olá!

Este é um teste de envio SMTP do sistema.

Se você recebeu este e-mail, a configuração está funcionando corretamente.
"""

        msg.attach(MIMEText(texto, 'plain', 'utf-8'))
        msg.attach(MIMEText(html, 'html', 'utf-8'))

        if smtp_seguranca == 'ssl':
            servidor = smtplib.SMTP_SSL(smtp_host, smtp_porta, timeout=30)
            servidor.login(email_remetente, senha_final)
            servidor.sendmail(email_remetente, [email_destino], msg.as_string())
            servidor.quit()

            retorno['ok'] = True
            retorno['msg'] = 'E-mail de teste enviado com sucesso.'
            retorno['raw'] = 'Conexão SMTP_SSL realizada com sucesso.'
            return retorno

        servidor = smtplib.SMTP(smtp_host, smtp_porta, timeout=30)
        servidor.ehlo()

        if smtp_seguranca == 'tls':
            servidor.starttls()
            servidor.ehlo()

        servidor.login(email_remetente, senha_final)
        servidor.sendmail(email_remetente, [email_destino], msg.as_string())
        servidor.quit()

        retorno['ok'] = True
        retorno['msg'] = 'E-mail de teste enviado com sucesso.'
        retorno['raw'] = f'Conexão SMTP realizada com segurança: {smtp_seguranca or "nenhuma"}'
        return retorno

    except Exception as e:
        retorno['msg'] = 'Falha ao enviar e-mail de teste.'
        retorno['raw'] = str(e)
        return retorno