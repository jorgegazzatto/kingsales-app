from flask import Blueprint, render_template, session, jsonify, request, Response
from app.utils.auth import login_required, permissao_menu_required, acao_required
from app.database.conexao import conectar
from app.utils.logs import registrar_log
from datetime import datetime
from xhtml2pdf import pisa
from io import BytesIO
import os
from app.utils.config_sistema import get_config_sistema
import mimetypes
import base64


MODULO = 'lista_vendas'
TABELA = 'lista_vendas'
TEMPLATE = 'painel/lista_vendas.html'
CHAVE_PERMISSAO = 'lista_vendas'

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
        cliente = request.args.get('cliente', '').strip()
        forma_pagamento = request.args.get('forma_pagamento', '').strip()
        status = request.args.get('status', '').strip()
        busca = request.args.get('busca', '').strip()

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        query = """
            SELECT
                v.*,
                c.nome AS cliente_nome,
                fp.nome AS forma_pagamento_nome,
                u.nome AS usuario_lancamento_nome
            FROM vendas v
            LEFT JOIN clientes c ON v.cliente = c.id
            LEFT JOIN formas_pagamento fp ON v.forma_pagamento = fp.id
            LEFT JOIN usuarios u ON v.usuario_lancamento = u.id
            WHERE v.ativo = 'Sim'
        """
        params = []

        if data_inicial and data_final:
            query += " AND v.data_lancamento BETWEEN %s AND %s"
            params.extend([data_inicial, data_final])

        if cliente:
            query += " AND v.cliente = %s"
            params.append(cliente)

        if forma_pagamento:
            query += " AND v.forma_pagamento = %s"
            params.append(forma_pagamento)

        if status:
            query += " AND v.status = %s"
            params.append(status)

        if busca:
            query += """
                AND (
                    CAST(v.id AS CHAR) LIKE %s
                    OR c.nome LIKE %s
                    OR v.observacoes LIKE %s
                )
            """
            termo = f"%{busca}%"
            params.extend([termo, termo, termo])

        query += " ORDER BY v.id DESC"

        cursor.execute(query, params)
        vendas = cursor.fetchall()

        for item in vendas:
            if item.get('hora_lancamento') is not None:
                item['hora_lancamento'] = str(item['hora_lancamento'])

            if item.get('data_lancamento') is not None:
                item['data_lancamento_formatada'] = item['data_lancamento'].strftime('%d/%m/%Y')
            else:
                item['data_lancamento_formatada'] = '-'

            item['valor'] = float(item.get('valor') or 0)
            item['desconto'] = float(item.get('desconto') or 0)
            item['acrescimo'] = float(item.get('acrescimo') or 0)
            item['subtotal'] = float(item.get('subtotal') or 0)

        return jsonify(vendas)

    except Exception as e:
        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao listar vendas.',
            'erro': str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()


@pagina.route(f'/{MODULO}/listar-formas-pagamento')
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def listar_formas_pagamento():
    conexao = None
    cursor = None

    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, nome
            FROM formas_pagamento
            WHERE ativo = 'Sim'
            ORDER BY nome ASC
        """)
        formas = cursor.fetchall()

        return jsonify(formas)

    except Exception as e:
        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao listar formas de pagamento.',
            'erro': str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()


@pagina.route(f'/{MODULO}/detalhar/<int:venda_id>')
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def detalhar(venda_id):
    conexao = None
    cursor = None

    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                v.*,
                c.nome AS cliente_nome,
                fp.nome AS forma_pagamento_nome,
                ul.nome AS usuario_lancamento_nome,
                up.nome AS usuario_pagamento_nome
            FROM vendas v
            LEFT JOIN clientes c ON v.cliente = c.id
            LEFT JOIN formas_pagamento fp ON v.forma_pagamento = fp.id
            LEFT JOIN usuarios ul ON v.usuario_lancamento = ul.id
            LEFT JOIN usuarios up ON v.usuario_pagamento = up.id
            WHERE v.id = %s
            LIMIT 1
        """, (venda_id,))
        venda = cursor.fetchone()

        if not venda:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Venda não encontrada.'
            }), 404

        cursor.execute("""
            SELECT
                iv.*,
                p.nome AS produto_nome
            FROM itens_venda iv
            LEFT JOIN produtos p ON iv.produto_id = p.id
            WHERE iv.venda_id = %s
            ORDER BY iv.id ASC
        """, (venda_id,))
        itens = cursor.fetchall()

        if venda.get('hora_lancamento') is not None:
            venda['hora_lancamento'] = str(venda['hora_lancamento'])

        if venda.get('data_lancamento') is not None:
            venda['data_lancamento_formatada'] = venda['data_lancamento'].strftime('%d/%m/%Y')
        else:
            venda['data_lancamento_formatada'] = '-'

        venda['valor'] = float(venda.get('valor') or 0)
        venda['desconto'] = float(venda.get('desconto') or 0)
        venda['acrescimo'] = float(venda.get('acrescimo') or 0)
        venda['subtotal'] = float(venda.get('subtotal') or 0)

        for item in itens:
            item['quantidade'] = float(item.get('quantidade') or 0)
            item['valor_unitario'] = float(item.get('valor_unitario') or 0)
            item['subtotal'] = float(item.get('subtotal') or 0)

        return jsonify({
            'status': 'sucesso',
            'venda': venda,
            'itens': itens
        })

    except Exception as e:
        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao detalhar venda.',
            'erro': str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()


@pagina.route(f'/{MODULO}/cancelar', methods=['POST'])
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
@acao_required('editar')
def cancelar():
    conexao = None
    cursor = None

    try:
        dados = request.get_json(silent=True) or {}

        venda_id = str(dados.get('id', '')).strip()
        motivo = str(dados.get('motivo', '')).strip()
        usuario_id = session.get('usuario_id')

        if not venda_id:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Venda não informada.'
            }), 400

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)
        conexao.start_transaction()

        cursor.execute("""
            SELECT *
            FROM vendas
            WHERE id = %s AND ativo = 'Sim'
            LIMIT 1
        """, (venda_id,))
        venda = cursor.fetchone()

        if not venda:
            conexao.rollback()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Venda não encontrada.'
            }), 404

        if venda.get('status') == 'Cancelado':
            conexao.rollback()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Esta venda já está cancelada.'
            }), 400

        cursor.execute("""
            SELECT
                iv.*,
                p.nome AS produto_nome,
                p.estoque,
                p.controlar_estoque
            FROM itens_venda iv
            LEFT JOIN produtos p ON iv.produto_id = p.id
            WHERE iv.venda_id = %s
        """, (venda_id,))
        itens = cursor.fetchall()

        # estorno de estoque
        for item in itens:
            controlar_estoque = item.get('controlar_estoque') or 'Sim'
            quantidade = float(item.get('quantidade') or 0)
            estoque_atual = float(item.get('estoque') or 0)

            if controlar_estoque == 'Sim':
                novo_estoque = estoque_atual + quantidade

                cursor.execute("""
                    UPDATE produtos
                    SET estoque = %s
                    WHERE id = %s
                """, (novo_estoque, item['produto_id']))

                cursor.execute("""
                    INSERT INTO movimentacoes_estoque (
                        produto_id,
                        tipo,
                        quantidade,
                        estoque_anterior,
                        estoque_atual,
                        observacao,
                        usuario_id
                    ) VALUES (
                        %s, 'Entrada', %s, %s, %s, %s, %s
                    )
                """, (
                    item['produto_id'],
                    quantidade,
                    estoque_atual,
                    novo_estoque,
                    f'Estorno da venda #{venda_id}',
                    usuario_id
                ))

        # cancelar venda
        observacao_cancelamento = f"{venda.get('observacoes') or ''}\n[CANCELADA] {motivo}".strip()

        cursor.execute("""
            UPDATE vendas
            SET
                status = 'Cancelado',
                observacoes = %s
            WHERE id = %s
        """, (observacao_cancelamento, venda_id))

        # cancelar recebimento vinculado
        cursor.execute("""
            UPDATE recebimentos
            SET
                status = 'Cancelado',
                ativo = 'Não',
                descricao = CONCAT('[CANCELADA] ', descricao),
                observacoes = CONCAT(IFNULL(observacoes, ''), %s)
            WHERE referencia = 'Venda PDV'
            AND id_ref = %s
            AND ativo = 'Sim'
        """, (f"\n[CANCELADO] {motivo}", venda_id))

        conexao.commit()

        registrar_log(
            acao='editar',
            entidade='vendas',
            registro_id=venda_id,
            descricao=f'venda cancelada: #{venda_id}'
        )

        return jsonify({
            'status': 'sucesso',
            'mensagem': 'Venda cancelada com sucesso.'
        })

    except Exception as e:
        if conexao:
            conexao.rollback()

        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao cancelar venda.',
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
def relatorio_vendas():
    conexao = None
    cursor = None

    try:
        data_inicial = request.form.get('data_inicial', '').strip()
        data_final = request.form.get('data_final', '').strip()
        cliente = request.form.get('cliente', '').strip()
        forma_pagamento = request.form.get('forma_pagamento', '').strip()
        status = request.form.get('status', '').strip()
        busca = request.form.get('busca', '').strip()

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        query = """
            SELECT
                v.*,
                c.nome AS cliente_nome,
                fp.nome AS forma_pagamento_nome,
                ul.nome AS usuario_lancamento_nome
            FROM vendas v
            LEFT JOIN clientes c ON c.id = v.cliente
            LEFT JOIN formas_pagamento fp ON fp.id = v.forma_pagamento
            LEFT JOIN usuarios ul ON ul.id = v.usuario_lancamento
            WHERE v.ativo = 'Sim'
        """
        valores = []

        if data_inicial:
            query += " AND v.data_lancamento >= %s"
            valores.append(data_inicial)

        if data_final:
            query += " AND v.data_lancamento <= %s"
            valores.append(data_final)

        if cliente:
            query += " AND v.cliente = %s"
            valores.append(cliente)

        if forma_pagamento:
            query += " AND v.forma_pagamento = %s"
            valores.append(forma_pagamento)

        if status:
            query += " AND v.status = %s"
            valores.append(status)

        if busca:
            query += """
                AND (
                    CAST(v.id AS CHAR) LIKE %s
                    OR c.nome LIKE %s
                    OR v.observacoes LIKE %s
                )
            """
            termo = f"%{busca}%"
            valores.extend([termo, termo, termo])

        query += " ORDER BY v.data_lancamento ASC, v.id DESC"

        cursor.execute(query, tuple(valores))
        lista_vendas = cursor.fetchall()

        total_bruto = 0
        total_desconto = 0
        total_acrescimo = 0
        total_liquido = 0
        total_pago = 0
        total_pendente = 0
        total_cancelado = 0

        for item in lista_vendas:
            item['valor'] = float(item.get('valor') or 0)
            item['desconto'] = float(item.get('desconto') or 0)
            item['acrescimo'] = float(item.get('acrescimo') or 0)
            item['subtotal'] = float(item.get('subtotal') or 0)

            total_bruto += item['valor']
            total_desconto += item['desconto']
            total_acrescimo += item['acrescimo']
            total_liquido += item['subtotal']

            if item.get('status') == 'Pago':
                total_pago += item['subtotal']
            elif item.get('status') == 'Pendente':
                total_pendente += item['subtotal']
            elif item.get('status') == 'Cancelado':
                total_cancelado += item['subtotal']

        cliente_nome_filtro = 'Todos'
        if cliente:
            cursor.execute(
                "SELECT nome FROM clientes WHERE id = %s LIMIT 1",
                (cliente,)
            )
            cliente_filtro = cursor.fetchone()
            if cliente_filtro:
                cliente_nome_filtro = cliente_filtro.get('nome') or f'Cliente #{cliente}'
            else:
                cliente_nome_filtro = f'Cliente #{cliente}'

        forma_pagamento_nome_filtro = 'Todas'
        if forma_pagamento:
            cursor.execute(
                "SELECT nome FROM formas_pagamento WHERE id = %s LIMIT 1",
                (forma_pagamento,)
            )
            forma_filtro = cursor.fetchone()
            if forma_filtro:
                forma_pagamento_nome_filtro = forma_filtro.get('nome') or f'Forma #{forma_pagamento}'
            else:
                forma_pagamento_nome_filtro = f'Forma #{forma_pagamento}'

        status_filtro = status if status else 'Todos'
        busca_filtro = busca if busca else '—'

        query_formas = """
            SELECT
                COALESCE(fp.nome, 'Não informado') AS nome,
                COUNT(v.id) AS quantidade,
                SUM(v.subtotal) AS total
            FROM vendas v
            LEFT JOIN formas_pagamento fp ON fp.id = v.forma_pagamento
            WHERE v.ativo = 'Sim'
        """
        valores_formas = []

        if data_inicial:
            query_formas += " AND v.data_lancamento >= %s"
            valores_formas.append(data_inicial)

        if data_final:
            query_formas += " AND v.data_lancamento <= %s"
            valores_formas.append(data_final)

        if cliente:
            query_formas += " AND v.cliente = %s"
            valores_formas.append(cliente)

        if forma_pagamento:
            query_formas += " AND v.forma_pagamento = %s"
            valores_formas.append(forma_pagamento)

        if status:
            query_formas += " AND v.status = %s"
            valores_formas.append(status)

        if busca:
            query_formas += """
                AND (
                    CAST(v.id AS CHAR) LIKE %s
                    OR EXISTS (
                        SELECT 1
                        FROM clientes c2
                        WHERE c2.id = v.cliente
                        AND c2.nome LIKE %s
                    )
                    OR v.observacoes LIKE %s
                )
            """
            termo = f"%{busca}%"
            valores_formas.extend([termo, termo, termo])

        query_formas += " GROUP BY fp.nome ORDER BY total DESC"

        cursor.execute(query_formas, tuple(valores_formas))
        resumo_formas = cursor.fetchall()

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
            'relatorios/vendas.html',
            dados=lista_vendas,
            data_inicial=data_inicial,
            data_final=data_final,
            data_inicial_label=data_inicial_label,
            data_final_label=data_final_label,
            status_filtro=status_filtro,
            cliente_nome_filtro=cliente_nome_filtro,
            forma_pagamento_nome_filtro=forma_pagamento_nome_filtro,
            busca_filtro=busca_filtro,
            total_bruto=total_bruto,
            total_desconto=total_desconto,
            total_acrescimo=total_acrescimo,
            total_liquido=total_liquido,
            total_pago=total_pago,
            total_pendente=total_pendente,
            total_cancelado=total_cancelado,
            resumo_formas=resumo_formas,
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
            headers={'Content-Disposition': 'inline; filename=relatorio_vendas.pdf'}
        )

    except Exception as e:
        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao gerar relatório de vendas.',
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