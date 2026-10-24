import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.utils.config_sistema import get_config_sistema
from app.utils.criptografia import descriptografar_texto


def enviar_email_texto(destinatario, assunto, mensagem_html, mensagem_texto=''):
    """
    Envio silencioso de e-mail.
    Se falhar, apenas ignora e retorna True.
    Busca toda a configuração automaticamente.
    """

    try:
        config_sistema = get_config_sistema()

        smtp_host = str(config_sistema.get('smtp_host') or '').strip()
        smtp_porta = config_sistema.get('smtp_porta')
        smtp_seguranca = str(config_sistema.get('smtp_seguranca') or '').strip().lower()
        email_remetente = str(config_sistema.get('email_sistema') or '').strip()
        smtp_senha_cripto = str(config_sistema.get('smtp_senha') or '').strip()

        smtp_senha = descriptografar_texto(smtp_senha_cripto)

        destinatario = str(destinatario or '').strip()
        assunto = str(assunto or '').strip()
        mensagem_html = str(mensagem_html or '').strip()
        mensagem_texto = str(mensagem_texto or '').strip()

        if not smtp_host or not smtp_porta or not email_remetente or not smtp_senha:
            return True

        if not destinatario or not assunto or (not mensagem_html and not mensagem_texto):
            return True

        try:
            smtp_porta = int(smtp_porta)
        except Exception:
            return True

        msg = MIMEMultipart('alternative')
        msg['Subject'] = assunto
        msg['From'] = email_remetente
        msg['To'] = destinatario

        if mensagem_texto:
            msg.attach(MIMEText(mensagem_texto, 'plain', 'utf-8'))

        if mensagem_html:
            msg.attach(MIMEText(mensagem_html, 'html', 'utf-8'))

        # SSL direto
        if smtp_seguranca == 'ssl':
            servidor = smtplib.SMTP_SSL(smtp_host, smtp_porta, timeout=30)
            servidor.login(email_remetente, smtp_senha)
            servidor.sendmail(email_remetente, [destinatario], msg.as_string())
            servidor.quit()
            return True

        # TLS ou sem segurança
        servidor = smtplib.SMTP(smtp_host, smtp_porta, timeout=30)
        servidor.ehlo()

        if smtp_seguranca == 'tls':
            servidor.starttls()
            servidor.ehlo()

        servidor.login(email_remetente, smtp_senha)
        servidor.sendmail(email_remetente, [destinatario], msg.as_string())
        servidor.quit()

        return True

    except Exception:
        return True