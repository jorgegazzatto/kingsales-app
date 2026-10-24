from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from functools import wraps
from app.database.conexao import conectar

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Sem Acesso, faça o Login!', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


def buscar_menus_permitidos(usuario_id):
    conexao = None
    cursor = None

    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT menu_id
            FROM usuarios_permissoes
            WHERE usuario_id = %s
        """, (usuario_id,))

        dados = cursor.fetchall()
        return [item['menu_id'] for item in dados]

    except Exception:
        return []

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()


def tem_permissao_menu(usuario_id, menu_id):
    nivel = session.get('usuario_nivel')

    if nivel == 'Administrador':
        return True
    menus = buscar_menus_permitidos(usuario_id)
    return menu_id in menus


def permissao_menu_required(menu_id):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            usuario_id = session.get('usuario_id')

            if not usuario_id:
                flash('Sem acesso, faça o login.', 'danger')
                return redirect(url_for('main.index'))

            if not tem_permissao_menu(usuario_id, menu_id):
                flash('Você não tem permissão para acessar esta página.', 'danger')
                return redirect(url_for('painel.index'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator





def buscar_acoes_permitidas(usuario_id):
    conexao = None
    cursor = None

    try:
        nivel = session.get('usuario_nivel')
        if nivel == 'Administrador':
            return ['inserir', 'editar', 'excluir']

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT acao
            FROM usuarios_acoes
            WHERE usuario_id = %s
        """, (usuario_id,))

        dados = cursor.fetchall()
        return [item['acao'] for item in dados]

    except Exception:
        return []

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()


def tem_acao(usuario_id, acao):
    acoes = buscar_acoes_permitidas(usuario_id)
    return acao in acoes


def acao_required(acao):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            usuario_id = session.get('usuario_id')

            if not usuario_id:
                flash('Sem acesso, faça o login.', 'danger')
                return redirect(url_for('main.index'))

            if not tem_acao(usuario_id, acao):
                return {'status': 'erro', 'mensagem': 'Você não tem permissão para esta ação.'}, 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator