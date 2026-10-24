from flask import Blueprint, render_template, session, jsonify, request
from app.utils.auth import login_required, permissao_menu_required
from app.database.conexao import conectar
from app.utils.logs import registrar_log
from app.utils.funcoes import valor_para_numero
from datetime import datetime, date
from flask import request

MODULO = 'pdv'
TEMPLATE = 'painel/pdv.html'
CHAVE_PERMISSAO = 'pdv'

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


@pagina.route(f'/{MODULO}/listar-categorias')
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def listar_categorias():
    conexao = None
    cursor = None

    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, nome, foto, posicao, descricao
            FROM categorias
            WHERE ativo = 'Sim'
            ORDER BY posicao ASC, nome ASC
        """)
        categorias = cursor.fetchall()

        for item in categorias:
            item['foto'] = item.get('foto') or ''

        return jsonify(categorias)

    except Exception as e:
        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao listar categorias.',
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
    conexao = None
    cursor = None

    try:
        categoria_id = request.args.get('categoria_id', '').strip()
        busca = request.args.get('busca', '').strip()
        filtro_estoque = request.args.get('filtro_estoque', '').strip()

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        query = """
            SELECT
                p.id,
                p.nome,
                p.descricao,
                p.foto,
                p.categoria_id,
                p.valor_compra,
                p.valor_venda,
                p.estoque,
                p.nivel_minimo_estoque,
                p.controlar_estoque,
                c.nome AS categoria_nome
            FROM produtos p
            LEFT JOIN categorias c ON p.categoria_id = c.id
            WHERE p.ativo = 'Sim'
        """
        params = []

        if categoria_id:
            query += " AND p.categoria_id = %s"
            params.append(categoria_id)

        if busca:
            query += " AND p.nome LIKE %s"
            params.append(f"%{busca}%")

        if filtro_estoque == 'com_estoque':
            query += " AND (p.controlar_estoque = 'Não' OR p.estoque > 0)"

        elif filtro_estoque == 'sem_estoque':
            query += " AND p.controlar_estoque = 'Sim' AND p.estoque <= 0"

        elif filtro_estoque == 'baixo_estoque':
            query += """
                AND p.controlar_estoque = 'Sim'
                AND p.estoque > 0
                AND p.nivel_minimo_estoque IS NOT NULL
                AND p.estoque <= p.nivel_minimo_estoque
            """

        query += " ORDER BY p.nome ASC"

        cursor.execute(query, params)
        produtos = cursor.fetchall()

        for item in produtos:
            item['foto'] = item.get('foto') or ''
            item['valor_venda'] = float(item.get('valor_venda') or 0)
            item['estoque'] = float(item.get('estoque') or 0)
            item['nivel_minimo_estoque'] = float(item.get('nivel_minimo_estoque') or 0)

            if item['controlar_estoque'] == 'Não':
                item['situacao_estoque'] = 'livre'
            elif item['estoque'] <= 0:
                item['situacao_estoque'] = 'sem_estoque'
            elif item['estoque'] <= item['nivel_minimo_estoque']:
                item['situacao_estoque'] = 'baixo_estoque'
            else:
                item['situacao_estoque'] = 'normal'

        return jsonify(produtos)

    except Exception as e:
        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao listar produtos.',
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







@pagina.route(f'/{MODULO}/finalizar-venda', methods=['POST'])
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def finalizar_venda():
    conexao = None
    cursor = None

    try:
        dados = request.get_json(silent=True) or {}

        cliente = dados.get('cliente') or None
        forma_pagamento = dados.get('forma_pagamento') or None
        data_venda = str(dados.get('data_venda') or '').strip()
        observacoes = str(dados.get('observacoes') or '').strip()
        itens = dados.get('itens') or []

        desconto = float(dados.get('desconto') or 0)
        acrescimo = float(dados.get('acrescimo') or 0)

        usuario_id = session.get('usuario_id')

        if not itens or not isinstance(itens, list):
            return jsonify({
                'status': 'erro',
                'mensagem': 'Adicione ao menos um produto à venda.'
            }), 400

        if not forma_pagamento:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Selecione a forma de pagamento.'
            }), 400

        if not data_venda:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Informe a data da venda.'
            }), 400

        try:
            data_venda_date = datetime.strptime(data_venda, '%Y-%m-%d').date()
        except:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Data da venda inválida.'
            }), 400

        hoje = date.today()

        if data_venda_date < hoje:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Não é permitido lançar venda com data anterior à data atual.'
            }), 400

        if data_venda_date > hoje and not cliente:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Para vendas com data futura, é obrigatório informar o cliente.'
            }), 400

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)
        conexao.start_transaction()

        subtotal_itens = 0.0
        itens_processados = []

        for item in itens:
            produto_id = str(item.get('id') or '').strip()
            quantidade = float(item.get('quantidade') or 0)

            if not produto_id or quantidade <= 0:
                conexao.rollback()
                return jsonify({
                    'status': 'erro',
                    'mensagem': 'Há item inválido na venda.'
                }), 400

            cursor.execute("""
                SELECT id, nome, valor_venda, estoque, controlar_estoque
                FROM produtos
                WHERE id = %s AND ativo = 'Sim'
            """, (produto_id,))
            produto = cursor.fetchone()

            if not produto:
                conexao.rollback()
                return jsonify({
                    'status': 'erro',
                    'mensagem': f'Produto não encontrado: ID {produto_id}.'
                }), 404

            valor_unitario = float(produto.get('valor_venda') or 0)
            estoque_atual = float(produto.get('estoque') or 0)
            controlar_estoque = produto.get('controlar_estoque') or 'Sim'

            if valor_unitario <= 0:
                conexao.rollback()
                return jsonify({
                    'status': 'erro',
                    'mensagem': f'O produto "{produto["nome"]}" está sem valor de venda válido.'
                }), 400

            if controlar_estoque == 'Sim' and quantidade > estoque_atual:
                conexao.rollback()
                return jsonify({
                    'status': 'erro',
                    'mensagem': f'Estoque insuficiente para o produto "{produto["nome"]}".'
                }), 400

            subtotal_item = quantidade * valor_unitario
            subtotal_itens += subtotal_item

            itens_processados.append({
                'produto_id': produto['id'],
                'produto_nome': produto['nome'],
                'quantidade': quantidade,
                'valor_unitario': valor_unitario,
                'subtotal': subtotal_item,
                'estoque_atual': estoque_atual,
                'controlar_estoque': controlar_estoque
            })

        total_venda = subtotal_itens - desconto + acrescimo

        if total_venda < 0:
            conexao.rollback()
            return jsonify({
                'status': 'erro',
                'mensagem': 'O total da venda não pode ser negativo.'
            }), 400

        venda_status = 'Pago' if data_venda_date == hoje else 'Pendente'
        usuario_pagamento = usuario_id if data_venda_date == hoje else None
        data_pagamento = data_venda_date if data_venda_date == hoje else None
        recebimento_status = 'Pago' if data_venda_date == hoje else 'Pendente'

        cursor.execute("""
            INSERT INTO vendas (
                cliente,
                valor,
                desconto,
                acrescimo,
                subtotal,
                data_lancamento,
                hora_lancamento,
                forma_pagamento,
                qtd_parcelas,
                referencia,
                id_ref,
                observacoes,
                status,
                usuario_lancamento,
                usuario_pagamento,
                ativo
            ) VALUES (
                %s, %s, %s, %s, %s, %s, CURTIME(), %s, %s, %s, %s, %s, %s, %s, %s, 'Sim'
            )
        """, (
            cliente,
            subtotal_itens,
            desconto,
            acrescimo,
            total_venda,
            data_venda_date,
            forma_pagamento,
            1,
            'Venda PDV',
            None,
            observacoes,
            venda_status,
            usuario_id,
            usuario_pagamento
        ))

        venda_id = cursor.lastrowid

        cursor.execute("""
            UPDATE vendas
            SET id_ref = %s
            WHERE id = %s
        """, (venda_id, venda_id))

        for item in itens_processados:
            cursor.execute("""
                INSERT INTO itens_venda (
                    venda_id,
                    produto_id,
                    quantidade,
                    valor_unitario,
                    subtotal,
                    usuario_lancamento
                ) VALUES (
                    %s, %s, %s, %s, %s, %s
                )
            """, (
                venda_id,
                item['produto_id'],
                item['quantidade'],
                item['valor_unitario'],
                item['subtotal'],
                usuario_id
            ))

            if item['controlar_estoque'] == 'Sim':
                novo_estoque = item['estoque_atual'] - item['quantidade']

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
                        %s, 'Saida', %s, %s, %s, %s, %s
                    )
                """, (
                    item['produto_id'],
                    item['quantidade'],
                    item['estoque_atual'],
                    novo_estoque,
                    f'Venda PDV #{venda_id}',
                    usuario_id
                ))

        cursor.execute("""
            INSERT INTO recebimentos (
                descricao,
                valor,
                desconto,
                multa,
                juros,
                subtotal,
                data_lancamento,
                hora_lancamento,
                data_vencimento,
                data_pagamento,
                status,
                cliente,
                forma_pagamento,
                plano_conta,
                centro_custo,
                frequencia,
                recorrente,
                qtd_parcelas,
                parcela,
                id_ref,
                referencia,
                usuario_lancamento,
                usuario_pagamento,
                hora,
                hora_lembrete,
                alertado,
                observacoes,
                ativo
            ) VALUES (
                %s, %s, %s, 0, 0, %s, %s, CURTIME(), %s, %s, %s, %s, %s, NULL, NULL, NULL, 'Não', 1, 1, %s, %s, %s, %s, CURTIME(), NULL, 'Não', %s, 'Sim'
            )
        """, (
            f'Venda PDV #{venda_id}',
            subtotal_itens,
            desconto,
            total_venda,
            data_venda_date,
            data_venda_date,
            data_pagamento,
            recebimento_status,
            cliente,
            forma_pagamento,
            venda_id,
            'Venda PDV',
            usuario_id,
            usuario_pagamento,
            observacoes
        ))

        conexao.commit()

        registrar_log(
            acao='inserir',
            entidade='vendas',
            registro_id=venda_id,
            descricao=f'nova venda PDV cadastrada: venda #{venda_id}'
        )

        return jsonify({
            'status': 'sucesso',
            'mensagem': 'Venda finalizada com sucesso.',
            'venda_id': venda_id
        })

    except Exception as e:
        if conexao:
            conexao.rollback()

        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao finalizar venda.',
            'erro': str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()



@pagina.route(f'/{MODULO}/comprovante/<int:venda_id>')
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def comprovante(venda_id):
    conexao = None
    cursor = None

    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        # VENDA
        cursor.execute("""
            SELECT
                v.*,
                c.nome AS cliente_nome,
                fp.nome AS forma_pagamento_nome
            FROM vendas v
            LEFT JOIN clientes c ON v.cliente = c.id
            LEFT JOIN formas_pagamento fp ON v.forma_pagamento = fp.id
            WHERE v.id = %s
            LIMIT 1
        """, (venda_id,))
        venda = cursor.fetchone()

        if not venda:
            return "Venda não encontrada.", 404

        # ITENS
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

                # normalizar campos de data/hora para exibição
        if venda.get('hora_lancamento') is not None:
            venda['hora_lancamento'] = str(venda['hora_lancamento'])

        if venda.get('data_lancamento') is not None:
            venda['data_lancamento_formatada'] = venda['data_lancamento'].strftime('%d/%m/%Y')
        else:
            venda['data_lancamento_formatada'] = '-'

        
        auto_print = request.args.get('print') == '1'

        return render_template(
            'relatorios/comprovante_venda.html',
            venda=venda,
            itens=itens,
            auto_print=auto_print
        )

    except Exception as e:
        return f"Erro ao gerar comprovante: {str(e)}", 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()