from flask import Blueprint, render_template, session, jsonify, request, Response
from app.utils.auth import login_required, permissao_menu_required, acao_required
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
from app.utils.funcoes import valor_para_numero, formatar_numero_int_ou_decimal


config_dict = get_config_sistema()
config_sistema = SimpleNamespace(**config_dict)

MODULO = 'saidas'
TABELA = 'movimentacoes_estoque'
TEMPLATE = 'painel/saidas.html'
CHAVE_PERMISSAO = 'saidas'

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
        produto_id = request.args.get('produto_id', '').strip()
        usuario_id = request.args.get('usuario_id', '').strip()

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        query = """
            SELECT
                m.id,
                m.produto_id,
                m.tipo,
                m.quantidade,
                m.estoque_anterior,
                m.estoque_atual,
                m.observacao,
                m.data_movimentacao,
                m.usuario_id,
                p.nome AS produto_nome,
                u.nome AS usuario_nome
            FROM movimentacoes_estoque m
            LEFT JOIN produtos p ON p.id = m.produto_id
            LEFT JOIN usuarios u ON u.id = m.usuario_id
            WHERE m.tipo = 'Saida'
        """
        valores = []

        if data_inicial:
            query += " AND DATE(m.data_movimentacao) >= %s"
            valores.append(data_inicial)

        if data_final:
            query += " AND DATE(m.data_movimentacao) <= %s"
            valores.append(data_final)

        if produto_id:
            query += " AND m.produto_id = %s"
            valores.append(produto_id)

        if usuario_id:
            query += " AND m.usuario_id = %s"
            valores.append(usuario_id)

        query += " ORDER BY m.id DESC"

        cursor.execute(query, tuple(valores))
        lista = cursor.fetchall()

        for item in lista:
            if item.get('data_movimentacao'):
                item['data_movimentacao_formatada'] = item['data_movimentacao'].strftime('%d/%m/%Y %H:%M')
            else:
                item['data_movimentacao_formatada'] = ''

        return jsonify(lista)

    except Exception as e:
        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao listar saidas.',
            'erro': str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()


@pagina.route(f'/{MODULO}/listar-produtos')
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def listar_produtos():
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, nome
        FROM produtos
        WHERE ativo = 'Sim'
        ORDER BY nome ASC
    """)
    lista = cursor.fetchall()

    cursor.close()
    conexao.close()

    return jsonify(lista)


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


@pagina.route(f'/{MODULO}/excluir', methods=['POST'])
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
@acao_required('excluir')
def excluir():
    conexao = None
    cursor = None

    try:
        dados = request.get_json(silent=True) or {}
        registro_id = str(dados.get('id', '')).strip()

        if not registro_id:
            return jsonify({
                'status': 'erro',
                'mensagem': 'ID do registro não informado.'
            }), 400

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                m.*,
                p.nome AS produto_nome
            FROM movimentacoes_estoque m
            LEFT JOIN produtos p ON p.id = m.produto_id
            WHERE m.id = %s AND m.tipo = 'Saida'
            LIMIT 1
        """, (registro_id,))
        registro = cursor.fetchone()

        if not registro:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Registro não encontrado.'
            }), 404

        produto_id = registro.get('produto_id')
        quantidade = float(registro.get('quantidade') or 0)

        cursor.execute("SELECT id, nome, estoque FROM produtos WHERE id = %s LIMIT 1", (produto_id,))
        produto = cursor.fetchone()

        if not produto:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Produto relacionado não encontrado.'
            }), 404

        estoque_atual_produto = float(produto.get('estoque') or 0)
        novo_estoque = estoque_atual_produto - quantidade

        if novo_estoque < 0:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Não é possível excluir esta saida, pois o estoque atual ficaria negativo.'
            }), 400

        cursor.execute("UPDATE produtos SET estoque = %s WHERE id = %s", (novo_estoque, produto_id))
        cursor.execute("DELETE FROM movimentacoes_estoque WHERE id = %s", (registro_id,))
        conexao.commit()

        registrar_log(
            acao='excluir',
            entidade='movimentacoes_estoque',
            registro_id=registro_id,
            descricao=f"saída de estoque excluída do produto: {registro.get('produto_nome') or produto.get('nome')}"
        )

        return jsonify({
            'status': 'sucesso',
            'mensagem': 'Saída excluída com sucesso.'
        })

    except Exception as e:
        if conexao:
            conexao.rollback()

        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao excluir saida.',
            'erro': str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()


@pagina.route(f'/{MODULO}/relatorio', methods=['POST'])
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def relatorio_entradas():
    conexao = None
    cursor = None

    try:
        data_inicial = request.form.get('data_inicial', '').strip()
        data_final = request.form.get('data_final', '').strip()
        produto_id = request.form.get('produto_id', '').strip()
        usuario_id = request.form.get('usuario_id', '').strip()

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        query = """
            SELECT
                m.id,
                m.produto_id,
                m.tipo,
                m.quantidade,
                m.estoque_anterior,
                m.estoque_atual,
                m.observacao,
                m.data_movimentacao,
                m.usuario_id,
                p.nome AS produto_nome,
                u.nome AS usuario_nome
            FROM movimentacoes_estoque m
            LEFT JOIN produtos p ON p.id = m.produto_id
            LEFT JOIN usuarios u ON u.id = m.usuario_id
            WHERE m.tipo = 'Saida'
        """
        valores = []

        if data_inicial:
            query += " AND DATE(m.data_movimentacao) >= %s"
            valores.append(data_inicial)

        if data_final:
            query += " AND DATE(m.data_movimentacao) <= %s"
            valores.append(data_final)

        if produto_id:
            query += " AND m.produto_id = %s"
            valores.append(produto_id)

        if usuario_id:
            query += " AND m.usuario_id = %s"
            valores.append(usuario_id)

        query += " ORDER BY m.data_movimentacao DESC"

        cursor.execute(query, tuple(valores))
        lista = cursor.fetchall()

        total_quantidade = 0
        for item in lista:
            total_quantidade += float(item.get('quantidade') or 0)

        produto_nome_filtro = 'Todos'
        if produto_id:
            cursor.execute("SELECT nome FROM produtos WHERE id = %s LIMIT 1", (produto_id,))
            produto_filtro = cursor.fetchone()
            if produto_filtro:
                produto_nome_filtro = produto_filtro.get('nome') or f'Produto #{produto_id}'
            else:
                produto_nome_filtro = f'Produto #{produto_id}'

        usuario_nome_filtro = 'Todos'
        if usuario_id:
            cursor.execute("SELECT nome FROM usuarios WHERE id = %s LIMIT 1", (usuario_id,))
            usuario_filtro = cursor.fetchone()
            if usuario_filtro:
                usuario_nome_filtro = usuario_filtro.get('nome') or f'Usuário #{usuario_id}'
            else:
                usuario_nome_filtro = f'Usuário #{usuario_id}'

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
            'relatorios/saidas.html',
            dados=lista,
            data_inicial=data_inicial,
            data_final=data_final,
            data_inicial_label=data_inicial_label,
            data_final_label=data_final_label,
            produto_nome_filtro=produto_nome_filtro,
            usuario_nome_filtro=usuario_nome_filtro,
            total_quantidade=total_quantidade,
            now=datetime.now,
            config_sistema=config_sistema,
            logo_src=logo_src,
            assinatura_src=assinatura_src,
            assinatura_nome=assinatura_nome,
            modo_relatorio=tipo_relatorio,
            formatar_numero=formatar_numero_int_ou_decimal
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
            headers={'Content-Disposition': 'inline; filename=relatorio_saidas.pdf'}
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