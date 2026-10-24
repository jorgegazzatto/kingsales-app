from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from app import bcrypt
from app.database.conexao import conectar
from config import MODO_TESTE, EMAIL_SISTEMA, SENHA_PADRAO, NOME_SISTEMA, COR_PRIMARIA, COR_SECUNDARIA
from app.utils.logs import registrar_log
import secrets
from datetime import datetime, timedelta
from flask import jsonify
from app.apis.whatsapp.texto import enviar_whatsapp_texto
from app.apis.email.texto import enviar_email_texto
import subprocess

main = Blueprint('main', __name__)

@main.route('/')
def index():
    senha_padrao = SENHA_PADRAO.strip()
    if 'usuario_id' in session:
        return redirect(url_for('painel.index'))
    return render_template(
        'index.html', 
        modo_teste=MODO_TESTE,
        email_padrao=EMAIL_SISTEMA,
        senha_padrao=senha_padrao,
        nome_sistema=NOME_SISTEMA,
        cor_primaria=COR_PRIMARIA,
        cor_secundaria=COR_SECUNDARIA,
        )

@main.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    senha = request.form.get('senha')
    lembrar = request.form.get('lembrar')

    if lembrar:
        session.permanent = True
    else:
        session.permanent = False

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
    usuario = cursor.fetchone()
    cursor.close()
    conexao.close()

    if usuario and usuario['ativo'] != 'Sim':
        flash('Usuário inativo, contate o Administrador!', 'danger')
        return redirect(url_for('main.index'))

    if usuario and bcrypt.check_password_hash(usuario['senha'], senha):
        session['usuario_id'] = usuario['id']
        session['usuario_nome'] = usuario['nome']
        session['usuario_nivel'] = usuario['nivel']
        session['usuario_foto'] = usuario['foto']
        
        # LANÇAR LOGOUT LOGS 
        registrar_log(
            acao='login',
            entidade='usuarios',
            registro_id=usuario['id'],
            descricao=f"Login do usuário {usuario['nome']}"
        )

        return redirect(url_for('painel.index'))
    flash('Email ou senha incorretos!', 'danger')
    return redirect(url_for('main.index'))







@main.route('/recuperar-senha', methods=['POST'])
def recuperar_senha():

    email = request.form.get('email')

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
    usuario = cursor.fetchone()

    if usuario:

        token = secrets.token_urlsafe(32)
        expira = datetime.now() + timedelta(minutes=30)

        cursor.execute("""
            UPDATE usuarios 
            SET token_recuperacao = %s, token_expira = %s 
            WHERE id = %s
        """, (token, expira, usuario['id']))

        conexao.commit()

        url_sistema = request.host_url.rstrip('/')
        link = f"{url_sistema}/redefinir-senha/{token}"

        nome = usuario['nome']
        telefone = usuario.get('telefone')

        # EMAIL
        assunto = "Recuperação de senha"

        mensagem_html = f"""
        <p>Olá <strong>{nome}</strong>,</p>

        <p>Recebemos uma solicitação para redefinir sua senha.</p>

        <p><a href="{link}">Clique aqui para redefinir sua senha</a></p>

        <p>Esse link expira em 30 minutos.</p>

        <p>Se não foi você, ignore esta mensagem.</p>
        """

        mensagem_texto = f"""
Olá {nome}

Recuperação de senha:

{link}

Expira em 30 minutos.
"""

        try:
            enviar_email_texto(email, assunto, mensagem_html, mensagem_texto)
        except:
            pass

        # WHATSAPP
        try:
            if telefone:
                mensagem = f"""🔐 *RECUPERAÇÃO DE SENHA*

Olá *{nome}* 👋

Recebemos uma solicitação para redefinir sua senha no sistema.

👉 *Clique no link abaixo para continuar:*
{link}

⏳ *Validade:* 30 minutos

⚠️ Se você não solicitou essa alteração, ignore esta mensagem.

🔒 Sua segurança é muito importante para nós.
"""
                enviar_whatsapp_texto(telefone, mensagem)
        except:
            pass

    cursor.close()
    conexao.close()

    return jsonify({
        'status': 'ok',
        'mensagem': 'Se o e-mail estiver cadastrado, enviaremos as instruções.'
    })






@main.route('/redefinir-senha/<token>')
def redefinir_senha(token):
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM usuarios
        WHERE token_recuperacao = %s
    """, (token,))
    usuario = cursor.fetchone()

    cursor.close()
    conexao.close()

    if not usuario:
        flash('Link inválido!', 'danger')
        return redirect(url_for('main.index'))

    if not usuario.get('token_expira') or usuario['token_expira'] < datetime.now():
        flash('Link expirado!', 'danger')
        return redirect(url_for('main.index'))

    return render_template('redefinir_senha.html', token=token)



@main.route('/salvar-nova-senha', methods=['POST'])
def salvar_nova_senha():

    token = request.form.get('token')
    senha = request.form.get('senha')
    confirmar = request.form.get('confirmar')

    if senha != confirmar:
        flash('As senhas não coincidem', 'danger')
        return redirect(request.referrer)

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM usuarios 
        WHERE token_recuperacao = %s
    """, (token,))

    usuario = cursor.fetchone()

    if not usuario:
        flash('Token inválido', 'danger')
        return redirect(url_for('main.index'))

    nova_senha = bcrypt.generate_password_hash(senha).decode('utf-8')

    cursor.execute("""
        UPDATE usuarios 
        SET senha = %s,
            token_recuperacao = NULL,
            token_expira = NULL
        WHERE id = %s
    """, (nova_senha, usuario['id']))

    conexao.commit()
    cursor.close()
    conexao.close()

    flash('Senha alterada com sucesso!', 'success')
    return redirect(url_for('main.index'))

    

def deploy_webhook():
    repo_dir = "/www/wwwroot/kingsales-app"
    
    # Executa o comando de pull na VPS para atualizar os arquivos
    subprocess.run(["git", "-C", repo_dir, "pull", "origin", "main"])
    
    return "Atualizado com sucesso!", 200