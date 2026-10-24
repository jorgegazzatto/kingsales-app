from flask import Blueprint, render_template, session, jsonify, request, Response
from app.utils.auth import login_required, permissao_menu_required, acao_required, tem_acao
from app.database.conexao import conectar
from app.utils.logs import registrar_log
from datetime import datetime
from xhtml2pdf import pisa
from io import BytesIO
from app.utils.config_sistema import get_config_sistema
from types import SimpleNamespace
import base64
import mimetypes
import os


config_dict = get_config_sistema()
config_sistema = SimpleNamespace(**config_dict)



MODULO = 'logs'
TABELA = 'logs'
TEMPLATE = 'painel/logs.html'
CHAVE_PERMISSAO = 'logs'

pagina = Blueprint(MODULO, __name__)


@pagina.route(f'/{MODULO}')
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def index():
    nome = session.get('usuario_nome')
    nivel = session.get('usuario_nivel')
    foto_usuario = session.get('usuario_foto')
    usuario_id = session.get('usuario_id')

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
    usuario = cursor.fetchone()

    cursor.close()
    conexao.close()

    return render_template(
        TEMPLATE,
        nome=nome,
        nivel=nivel,
        foto_usuario=foto_usuario,
        usuario=usuario
    )


@pagina.route(f'/{MODULO}/listar')
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def listar():
    conexao = None
    cursor = None

    try:
        data_inicial = request.args.get('data_inicial', '').strip()
        data_final = request.args.get('data_final', '').strip()
        usuario_id = request.args.get('usuario', '').strip()
        acao = request.args.get('acao', '').strip()

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        query = """
            SELECT
                l.id,
                l.empresa,
                l.usuario_id,
                l.acao,
                l.entidade,
                l.registro_id,
                l.descricao,
                l.rota,
                l.ip,
                l.user_agent,
                l.criado_em,
                u.nome AS usuario_nome,
                u.email AS usuario_email
            FROM logs l
            LEFT JOIN usuarios u ON u.id = l.usuario_id
            WHERE 1=1
        """
        valores = []

        if data_inicial:
            query += " AND DATE(l.criado_em) >= %s"
            valores.append(data_inicial)

        if data_final:
            query += " AND DATE(l.criado_em) <= %s"
            valores.append(data_final)

        if usuario_id:
            query += " AND l.usuario_id = %s"
            valores.append(usuario_id)

        if acao:
            query += " AND l.acao = %s"
            valores.append(acao)

        query += " ORDER BY l.id DESC"

        cursor.execute(query, tuple(valores))
        lista = cursor.fetchall()

        for item in lista:
            if item.get('criado_em'):
                item['criado_em'] = item['criado_em'].strftime('%d/%m/%Y %H:%M')

        return jsonify(lista)

    except Exception as e:
        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao listar logs.',
            'erro': str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()




@pagina.route(f'/{MODULO}/listar-usuarios')
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def listar_usuarios():
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, nome
        FROM usuarios
        WHERE ativo = 'Sim'
        ORDER BY nome ASC
    """)
    lista = cursor.fetchall()

    cursor.close()
    conexao.close()

    return jsonify(lista)




@pagina.route(f'/{MODULO}/relatorio', methods=['POST'])
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def relatorio_logs():
    conexao = None
    cursor = None

    try:
        data_inicial = request.form.get('data_inicial', '').strip()
        data_final = request.form.get('data_final', '').strip()
        usuario_id = request.form.get('usuario', '').strip()
        acao = request.form.get('acao', '').strip()

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        query = """
            SELECT
                l.id,
                l.empresa,
                l.usuario_id,
                l.acao,
                l.entidade,
                l.registro_id,
                l.descricao,
                l.rota,
                l.ip,
                l.user_agent,
                l.criado_em,
                u.nome AS usuario_nome,
                u.email AS usuario_email
            FROM logs l
            LEFT JOIN usuarios u ON u.id = l.usuario_id
            WHERE 1=1
        """
        valores = []

        if data_inicial:
            query += " AND DATE(l.criado_em) >= %s"
            valores.append(data_inicial)

        if data_final:
            query += " AND DATE(l.criado_em) <= %s"
            valores.append(data_final)

        if usuario_id:
            query += " AND l.usuario_id = %s"
            valores.append(usuario_id)

        if acao:
            query += " AND l.acao = %s"
            valores.append(acao)

        query += " ORDER BY l.criado_em DESC"

        cursor.execute(query, tuple(valores))
        lista_logs = cursor.fetchall()

        usuario_nome_filtro = 'Todos'
        if usuario_id:
            cursor.execute(
                "SELECT nome, email FROM usuarios WHERE id = %s LIMIT 1",
                (usuario_id,)
            )
            usuario_filtro = cursor.fetchone()
            if usuario_filtro:
                usuario_nome_filtro = usuario_filtro.get('nome') or f'Usuário #{usuario_id}'
                if usuario_filtro.get('email'):
                    usuario_nome_filtro += f" ({usuario_filtro['email']})"
            else:
                usuario_nome_filtro = f'Usuário #{usuario_id}'

        mapa_acoes = {
            'login': 'Login',
            'logout': 'Logout',
            'inserir': 'Inserir',
            'editar': 'Editar',
            'excluir': 'Excluir'
        }
        acao_label = mapa_acoes.get(acao, 'Todas') if acao else 'Todas'

        config_sistema = get_config_sistema()

        tipo_relatorio = (config_sistema.get('rel_html_pdf') or 'pdf').strip().lower()
        if tipo_relatorio not in ['pdf', 'html']:
            tipo_relatorio = 'pdf'


        data_inicial_label = datetime.strptime(data_inicial, '%Y-%m-%d').strftime('%d/%m/%Y') if data_inicial else '—'
        data_final_label = datetime.strptime(data_final, '%Y-%m-%d').strftime('%d/%m/%Y') if data_final else '—'

        logo_src = None
        logo_arquivo = (config_sistema.get('logo') or '').strip()
        if logo_arquivo:
            logo_path = os.path.join('app', 'static', 'img', logo_arquivo)
            logo_src = arquivo_para_data_uri(logo_path)

        assinatura_src = None
        assinatura_nome = ''
        usuario_logado_id = session.get('usuario_id')

        if usuario_logado_id:
            cursor.execute(
                "SELECT nome, assinatura FROM usuarios WHERE id = %s LIMIT 1",
                (usuario_logado_id,)
            )
            usuario_ass = cursor.fetchone()

            if usuario_ass:
                assinatura_nome = usuario_ass.get('nome') or ''
                assinatura_arquivo = (usuario_ass.get('assinatura') or '').strip()

                if assinatura_arquivo:
                    assinatura_path = os.path.join('app', 'static', 'img', 'assinaturas', assinatura_arquivo)
                    assinatura_src = arquivo_para_data_uri(assinatura_path)

        html = render_template(
            'relatorios/logs.html',
            dados=lista_logs,
            data_inicial=data_inicial,
            data_final=data_final,
            data_inicial_label=data_inicial_label,
            data_final_label=data_final_label,
            usuario_id=usuario_id,
            usuario_nome_filtro=usuario_nome_filtro,
            acao=acao,
            acao_label=acao_label,
            now=datetime.now,
            config_sistema=config_sistema,
            logo_src=logo_src,
            assinatura_src=assinatura_src,
            assinatura_nome=assinatura_nome,
            modo_relatorio=tipo_relatorio
        )

        if tipo_relatorio == 'html':
            return Response(html, mimetype='text/html; charset=utf-8')

        pdf_file = BytesIO()

        pisa_status = pisa.CreatePDF(
            src=html,
            dest=pdf_file,
            encoding='utf-8'
        )

        if pisa_status.err:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Erro ao gerar PDF com xhtml2pdf.'
            }), 500

        pdf_file.seek(0)

        return Response(
            pdf_file.getvalue(),
            mimetype='application/pdf',
            headers={'Content-Disposition': 'inline; filename=relatorio_logs.pdf'}
        )

    except Exception as e:
        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao gerar relatório.',
            'erro': str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()



def arquivo_para_data_uri(caminho_arquivo):
    if not caminho_arquivo or not os.path.isfile(caminho_arquivo):
        return None

    mime_type, _ = mimetypes.guess_type(caminho_arquivo)
    mime_type = mime_type or 'image/png'

    with open(caminho_arquivo, 'rb') as f:
        conteudo = base64.b64encode(f.read()).decode('utf-8')

    return f"data:{mime_type};base64,{conteudo}"