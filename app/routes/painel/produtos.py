from flask import Blueprint, render_template, session, jsonify, request, Response
from app.utils.auth import login_required, permissao_menu_required, acao_required
from app.database.conexao import conectar
from app.utils.uploads import salvar_arquivo, excluir_arquivo
from app.utils.logs import registrar_log
from app.utils.funcoes import valor_para_numero, formatar_numero_int_ou_decimal
import os
from datetime import datetime
from app.utils.config_sistema import get_config_sistema
from xhtml2pdf import pisa
from io import BytesIO
import mimetypes
import base64

MODULO = 'produtos'
TABELA = 'produtos'
TEMPLATE = 'painel/produtos.html'
CHAVE_PERMISSAO = 'produtos'
PASTA_UPLOAD = os.path.join('app', 'static', 'img', 'produtos')

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

    cursor.execute("SELECT id, nome FROM categorias WHERE ativo = 'Sim' ORDER BY nome ASC")
    categorias = cursor.fetchall()

    cursor.close()
    conexao.close()

    return render_template(
        TEMPLATE,
        nome=nome,
        nivel=nivel,
        foto_usuario=foto_usuario,
        usuario=usuario,
        categorias=categorias
    )


@pagina.route(f'/{MODULO}/listar')
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def listar():
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    try:
        categoria_id = request.args.get('categoria_id')
        status = request.args.get('status')
        texto = request.args.get('texto')
        estoque_baixo = request.args.get('estoque_baixo')

        sql = f"""
            SELECT p.*, c.nome AS categoria_nome
            FROM {TABELA} p
            LEFT JOIN categorias c ON c.id = p.categoria_id
            WHERE 1=1
        """

        params = []

        if categoria_id:
            sql += " AND p.categoria_id = %s"
            params.append(categoria_id)

        if status:
            sql += " AND p.ativo = %s"
            params.append(status)

        if texto:
            sql += " AND p.nome LIKE %s"
            params.append(f"%{texto}%")

        if estoque_baixo == 'Sim':
            sql += " AND p.controlar_estoque = 'Sim' AND p.estoque <= p.nivel_minimo_estoque"

        if estoque_baixo == 'Não':
            sql += " AND (p.controlar_estoque = 'Não' OR p.estoque > p.nivel_minimo_estoque)"

        sql += " ORDER BY p.id DESC"

        cursor.execute(sql, tuple(params))
        lista = cursor.fetchall()

        return jsonify(lista)

    except Exception as e:
        return jsonify({'status': 'erro', 'mensagem': str(e)})

    finally:
        cursor.close()
        conexao.close()


@pagina.route(f'/{MODULO}/salvar', methods=['POST'])
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def salvar():
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    try:
        id = request.form.get('id')

        nome = (request.form.get('nome') or '').strip()
        categoria_id = request.form.get('categoria_id') or None
        descricao = request.form.get('descricao') or None
        controlar_estoque = request.form.get('controlar_estoque') or 'Sim'

        valor_compra = request.form.get('valor_compra')
        valor_venda = request.form.get('valor_venda')
        estoque = request.form.get('estoque')
        nivel_minimo_estoque = request.form.get('nivel_minimo_estoque')

        usuario_cadastro = session.get('usuario_id')
        

        if not nome:
            return jsonify({
                'status': 'erro',
                'mensagem': 'O nome do produto é obrigatório.'
            })

        valor_compra = valor_para_numero(request.form.get('valor_compra'))
        valor_venda = valor_para_numero(request.form.get('valor_venda'))

        estoque = request.form.get('estoque')
        nivel_minimo_estoque = request.form.get('nivel_minimo_estoque')

        try:
            estoque = float(str(estoque).strip().replace(',', '.')) if estoque not in [None, ''] else None
        except:
            estoque = None

        try:
            nivel_minimo_estoque = float(str(nivel_minimo_estoque).strip().replace(',', '.')) if nivel_minimo_estoque not in [None, ''] else None
        except:
            nivel_minimo_estoque = None

        if controlar_estoque == 'Não':
            estoque = None
            nivel_minimo_estoque = None

        foto = request.files.get('foto')
        nome_foto = None

        # =========================
        # INSERT
        # =========================
        if not id:

            ativo = 'Sim'
            data_cadastro = datetime.now()

            if foto and foto.filename:
                resultado = salvar_arquivo(
                    arquivo=foto,
                    pasta_destino=PASTA_UPLOAD,
                    extensoes_permitidas=['.jpg', '.jpeg', '.png', '.webp']
                )

                if not resultado['sucesso']:
                    return jsonify({'status': 'erro', 'mensagem': resultado['mensagem']})

                nome_foto = resultado['arquivo']

            cursor.execute(f"""
                INSERT INTO {TABELA} (
                    nome, descricao, foto, categoria_id,
                    valor_compra, valor_venda,
                    estoque, nivel_minimo_estoque,
                    controlar_estoque, ativo,
                    data_cadastro, usuario_cadastro
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                nome, descricao, nome_foto, categoria_id,
                valor_compra, valor_venda,
                estoque, nivel_minimo_estoque,
                controlar_estoque, ativo,
                data_cadastro, usuario_cadastro
            ))

            conexao.commit()

            return jsonify({
                'status': 'sucesso',
                'mensagem': 'Produto cadastrado com sucesso'
            })

        # =========================
        # UPDATE
        # =========================
        else:

            cursor.execute(f"SELECT foto FROM {TABELA} WHERE id = %s", (id,))
            registro = cursor.fetchone()

            nome_foto = registro['foto'] if registro else None

            if foto and foto.filename:
                resultado = salvar_arquivo(
                    arquivo=foto,
                    pasta_destino=PASTA_UPLOAD,
                    extensoes_permitidas=['.jpg', '.jpeg', '.png', '.webp']
                )

                if not resultado['sucesso']:
                    return jsonify({'status': 'erro', 'mensagem': resultado['mensagem']})

                nova_foto = resultado['arquivo']

                excluir_arquivo(
                    nome_arquivo=nome_foto,
                    pasta_destino=PASTA_UPLOAD,
                    arquivos_protegidos=['sem_foto.webp']
                )

                nome_foto = nova_foto

            cursor.execute(f"""
                UPDATE {TABELA} SET
                    nome=%s,
                    descricao=%s,
                    foto=%s,
                    categoria_id=%s,
                    valor_compra=%s,
                    valor_venda=%s,
                    estoque=%s,
                    nivel_minimo_estoque=%s,
                    controlar_estoque=%s
                WHERE id=%s
            """, (
                nome, descricao, nome_foto, categoria_id,
                valor_compra, valor_venda,
                estoque, nivel_minimo_estoque,
                controlar_estoque,
                id
            ))

            conexao.commit()

            return jsonify({
                'status': 'sucesso',
                'mensagem': 'Produto atualizado com sucesso'
            })

    except Exception as e:
        conexao.rollback()
        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao salvar produto',
            'erro': str(e)
        })

    finally:
        cursor.close()
        conexao.close()


@pagina.route(f'/{MODULO}/alternar-status', methods=['POST'])
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
@acao_required('editar')
def alternar_status():
    conexao = None
    cursor = None

    try:
        dados = request.get_json(silent=True) or {}
        registro_id = str(dados.get('id', '')).strip()
        ativo = str(dados.get('ativo', '')).strip()

        if not registro_id:
            return jsonify({'status': 'erro', 'mensagem': 'ID do registro não informado.'}), 400

        if ativo not in ['Sim', 'Não']:
            return jsonify({'status': 'erro', 'mensagem': 'Status inválido.'}), 400

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute(f"SELECT id, nome, ativo FROM {TABELA} WHERE id = %s", (registro_id,))
        registro = cursor.fetchone()

        if not registro:
            return jsonify({'status': 'erro', 'mensagem': 'Registro não encontrado.'}), 404

        cursor.execute(f"UPDATE {TABELA} SET ativo = %s WHERE id = %s", (ativo, registro_id))
        conexao.commit()

        registrar_log(
            acao='editar',
            entidade=TABELA,
            registro_id=registro_id,
            descricao=f"status alterado em {TABELA}: {registro['nome']}"
        )

        mensagem = 'Produto ativado com sucesso.' if ativo == 'Sim' else 'Produto desativado com sucesso.'

        return jsonify({'status': 'sucesso', 'mensagem': mensagem})

    except Exception as e:
        if conexao:
            conexao.rollback()

        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro interno ao alterar o status.',
            'erro': str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()


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
            return jsonify({'status': 'erro', 'mensagem': 'ID do registro não informado.'}), 400

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute(f"SELECT id, nome, foto FROM {TABELA} WHERE id = %s", (registro_id,))
        registro = cursor.fetchone()

        if not registro:
            return jsonify({'status': 'erro', 'mensagem': 'Registro não encontrado.'}), 404

        cursor.execute(f"DELETE FROM {TABELA} WHERE id = %s", (registro_id,))
        conexao.commit()

        registrar_log(
            acao='excluir',
            entidade=TABELA,
            registro_id=registro_id,
            descricao=f"registro excluído em {TABELA}: {registro['nome']}"
        )

        excluir_arquivo(
            nome_arquivo=registro.get('foto'),
            pasta_destino=PASTA_UPLOAD,
            arquivos_protegidos=['sem_foto.webp', 'sem-foto.webp', 'sem_foto.png', 'sem-foto.png', 'sem_foto.jpg', 'sem-foto.jpg']
        )

        return jsonify({'status': 'sucesso', 'mensagem': 'Produto excluído com sucesso.'})

    except Exception as e:
        if conexao:
            conexao.rollback()

        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro interno ao excluir registro.',
            'erro': str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()


@pagina.route(f'/{MODULO}/excluir-lote', methods=['POST'])
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
@acao_required('excluir')
def excluir_lote():
    conexao = None
    cursor = None

    try:
        dados = request.get_json(silent=True) or {}
        ids = dados.get('ids', [])

        if not ids or not isinstance(ids, list):
            return jsonify({'status': 'erro', 'mensagem': 'Nenhum registro foi selecionado.'}), 400

        ids_validos = [str(i).strip() for i in ids if str(i).strip().isdigit()]

        if not ids_validos:
            return jsonify({'status': 'erro', 'mensagem': 'IDs inválidos.'}), 400

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        placeholders = ','.join(['%s'] * len(ids_validos))

        cursor.execute(
            f"SELECT id, nome, foto FROM {TABELA} WHERE id IN ({placeholders})",
            tuple(ids_validos)
        )
        registros_encontrados = cursor.fetchall()

        if not registros_encontrados:
            return jsonify({'status': 'erro', 'mensagem': 'Nenhum registro encontrado.'}), 404

        cursor.execute(f"DELETE FROM {TABELA} WHERE id IN ({placeholders})", tuple(ids_validos))
        conexao.commit()

        for registro in registros_encontrados:
            registrar_log(
                acao='excluir',
                entidade=TABELA,
                registro_id=registro['id'],
                descricao=f"registro excluído em {TABELA}: {registro['nome']}"
            )

            excluir_arquivo(
                nome_arquivo=registro.get('foto'),
                pasta_destino=PASTA_UPLOAD,
                arquivos_protegidos=['sem_foto.webp', 'sem-foto.webp', 'sem_foto.png', 'sem-foto.png', 'sem_foto.jpg', 'sem-foto.jpg']
            )

        return jsonify({
            'status': 'sucesso',
            'mensagem': f'{len(registros_encontrados)} produto(s) excluído(s) com sucesso.'
        })

    except Exception as e:
        if conexao:
            conexao.rollback()

        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro interno ao excluir registros.',
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
def relatorio_produtos():
    conexao = None
    cursor = None

    try:
        categoria_id = request.form.get('categoria_id', '').strip()
        status = request.form.get('status', '').strip()
        texto = request.form.get('texto', '').strip()
        estoque_baixo = request.form.get('estoque_baixo', '').strip()

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        query = """
            SELECT
                p.*,
                c.nome AS categoria_nome
            FROM produtos p
            LEFT JOIN categorias c ON c.id = p.categoria_id
            WHERE 1=1
        """
        valores = []

        if categoria_id:
            query += " AND p.categoria_id = %s"
            valores.append(categoria_id)

        if status:
            query += " AND p.ativo = %s"
            valores.append(status)

        if texto:
            query += " AND p.nome LIKE %s"
            valores.append(f"%{texto}%")

        if estoque_baixo == 'Sim':
            query += " AND p.controlar_estoque = 'Sim' AND p.estoque <= p.nivel_minimo_estoque"

        if estoque_baixo == 'Não':
            query += " AND (p.controlar_estoque = 'Não' OR p.estoque > p.nivel_minimo_estoque)"

        query += " ORDER BY p.nome ASC"

        cursor.execute(query, tuple(valores))
        lista = cursor.fetchall()

        # =========================
        # TOTAIS
        # =========================
        total_compra = 0
        total_venda = 0
        total_lucro = 0
        qtd_estoque_baixo = 0

        for item in lista:
            compra = float(item.get('valor_compra') or 0)
            venda = float(item.get('valor_venda') or 0)
            estoque = float(item.get('estoque') or 0)
            minimo = float(item.get('nivel_minimo_estoque') or 0)

            total_compra += compra
            total_venda += venda
            total_lucro += (venda - compra)

            if item.get('controlar_estoque') == 'Sim' and estoque <= minimo:
                qtd_estoque_baixo += 1

        # =========================
        # NOME DOS FILTROS
        # =========================
        categoria_nome_filtro = 'Todas'
        if categoria_id:
            cursor.execute("SELECT nome FROM categorias WHERE id = %s LIMIT 1", (categoria_id,))
            cat = cursor.fetchone()
            if cat:
                categoria_nome_filtro = cat.get('nome')

        status_filtro = status if status else 'Todos'
        texto_filtro = texto if texto else ''
        estoque_baixo_filtro = estoque_baixo if estoque_baixo else 'Todos'

        # =========================
        # RESUMO POR CATEGORIA
        # =========================
        query_cat = """
            SELECT
                COALESCE(c.nome, 'Sem categoria') AS nome,
                COUNT(p.id) AS quantidade,
                SUM(p.valor_compra) AS total_compra,
                SUM(p.valor_venda) AS total_venda
            FROM produtos p
            LEFT JOIN categorias c ON c.id = p.categoria_id
            WHERE 1=1
        """
        valores_cat = []

        if categoria_id:
            query_cat += " AND p.categoria_id = %s"
            valores_cat.append(categoria_id)

        if status:
            query_cat += " AND p.ativo = %s"
            valores_cat.append(status)

        if texto:
            query_cat += " AND p.nome LIKE %s"
            valores_cat.append(f"%{texto}%")

        query_cat += " GROUP BY c.nome ORDER BY total_venda DESC"

        cursor.execute(query_cat, tuple(valores_cat))
        resumo_categorias = cursor.fetchall()

        # =========================
        # RESUMO POR STATUS
        # =========================
        query_status = """
            SELECT
                p.ativo AS status,
                COUNT(p.id) AS quantidade
            FROM produtos p
            WHERE 1=1
        """
        valores_status = []

        if categoria_id:
            query_status += " AND p.categoria_id = %s"
            valores_status.append(categoria_id)

        if texto:
            query_status += " AND p.nome LIKE %s"
            valores_status.append(f"%{texto}%")

        query_status += " GROUP BY p.ativo"

        cursor.execute(query_status, tuple(valores_status))
        resumo_status = cursor.fetchall()

        # =========================
        # CONFIG
        # =========================
        config_sistema = get_config_sistema()

        tipo_relatorio = (config_sistema.get('rel_html_pdf') or 'pdf').strip().lower()
        if tipo_relatorio not in ['pdf', 'html']:
            tipo_relatorio = 'pdf'

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

        # =========================
        # RENDER
        # =========================
        html = render_template(
            'relatorios/produtos.html',
            dados=lista,
            categoria_nome_filtro=categoria_nome_filtro,
            status_filtro=status_filtro,
            texto_filtro=texto_filtro,
            total_compra=total_compra,
            total_venda=total_venda,
            total_lucro=total_lucro,
            qtd_estoque_baixo=qtd_estoque_baixo,
            resumo_categorias=resumo_categorias,
            resumo_status=resumo_status,
            now=datetime.now,
            config_sistema=config_sistema,
            logo_src=logo_src,
            assinatura_src=assinatura_src,
            assinatura_nome=assinatura_nome,
            modo_relatorio=tipo_relatorio,
            estoque_baixo_filtro=estoque_baixo_filtro,
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
                'mensagem': 'Erro ao gerar PDF.'
            }), 500

        pdf_file.seek(0)

        return Response(
            pdf_file.getvalue(),
            mimetype='application/pdf',
            headers={'Content-Disposition': 'inline; filename=relatorio_produtos.pdf'}
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







@pagina.route(f'/{MODULO}/salvar-movimentacao', methods=['POST'])
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
@acao_required('editar')
def salvar_movimentacao():
    conexao = None
    cursor = None

    try:
        produto_id = request.form.get('produto_id')
        tipo = (request.form.get('tipo') or '').strip()
        quantidade = request.form.get('quantidade')
        observacao = (request.form.get('observacao') or '').strip()
        usuario_id = session.get('usuario_id')

        if not produto_id:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Produto não informado.'
            }), 400

        if tipo not in ['Entrada', 'Saida']:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Tipo de movimentação inválido.'
            }), 400

        quantidade = valor_para_numero(quantidade)

        if quantidade <= 0:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Informe uma quantidade válida.'
            }), 400

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute(f"""
            SELECT id, nome, estoque, controlar_estoque
            FROM {TABELA}
            WHERE id = %s
            LIMIT 1
        """, (produto_id,))
        produto = cursor.fetchone()

        if not produto:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Produto não encontrado.'
            }), 404

        if produto.get('controlar_estoque') != 'Sim':
            return jsonify({
                'status': 'erro',
                'mensagem': 'Este produto não controla estoque.'
            }), 400

        estoque_anterior = float(produto.get('estoque') or 0)

        if tipo == 'Entrada':
            estoque_atual = estoque_anterior + quantidade
        else:
            if quantidade > estoque_anterior:
                return jsonify({
                    'status': 'erro',
                    'mensagem': 'A quantidade de saída é maior que o estoque atual.'
                }), 400

            estoque_atual = estoque_anterior - quantidade

        cursor.execute(f"""
            UPDATE {TABELA}
            SET estoque = %s
            WHERE id = %s
        """, (estoque_atual, produto_id))

        cursor.execute("""
            INSERT INTO movimentacoes_estoque (
                produto_id,
                tipo,
                quantidade,
                estoque_anterior,
                estoque_atual,
                observacao,
                data_movimentacao,
                usuario_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            produto_id,
            tipo,
            quantidade,
            estoque_anterior,
            estoque_atual,
            observacao if observacao else None,
            datetime.now(),
            usuario_id
        ))

        conexao.commit()

        registrar_log(
            acao='editar',
            entidade='movimentacoes_estoque',
            registro_id=produto_id,
            descricao=f"movimentação de estoque ({tipo.lower()}) no produto: {produto['nome']}"
        )

        return jsonify({
            'status': 'sucesso',
            'mensagem': f'{tipo} registrada com sucesso.'
        })

    except Exception as e:
        if conexao:
            conexao.rollback()

        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao salvar movimentação.',
            'erro': str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()