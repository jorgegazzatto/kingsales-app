from flask import Blueprint, Response, render_template, session, jsonify, request
from app.utils.auth import login_required, permissao_menu_required, acao_required, tem_acao
from app.database.conexao import conectar
from app.utils.logs import registrar_log
from app.utils.funcoes import valor_para_numero
from datetime import date, datetime, timedelta
from xhtml2pdf import pisa
from io import BytesIO
import os
import mimetypes
import base64
from app.utils.config_sistema import get_config_sistema
import random
from app.apis.whatsapp.texto import enviar_whatsapp_texto
from app.apis.email.texto import enviar_email_texto

MODULO = 'recebimentos'
TABELA = 'recebimentos'
TEMPLATE = 'painel/recebimentos.html'
CHAVE_PERMISSAO = 'recebimentos'

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
def listar():
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    data_inicial = request.args.get('data_inicial')
    data_final = request.args.get('data_final')
    status = request.args.get('status')
    cliente = request.args.get('cliente')
    plano_conta = request.args.get('plano_conta')

    query = """
        SELECT 
            r.*,
            c.nome AS cliente_nome,
            pc.nome AS plano_conta_nome,
            fp.nome AS forma_pagamento_nome,
            fr.nome AS frequencia_nome,
            up.nome AS usuario_pgto,
            ul.nome AS usuario_lanc
        FROM recebimentos r
        LEFT JOIN clientes c ON r.cliente = c.id
        LEFT JOIN plano_contas pc ON r.plano_conta = pc.id
        LEFT JOIN formas_pagamento fp ON r.forma_pagamento = fp.id
        LEFT JOIN frequencias fr ON r.frequencia = fr.id
        LEFT JOIN usuarios up ON r.usuario_pagamento = up.id
        LEFT JOIN usuarios ul ON r.usuario_lancamento = ul.id
        WHERE 1=1
    """

    params = []

    # filtro por data
    if data_inicial and data_final:
        query += " AND r.data_vencimento BETWEEN %s AND %s"
        params.append(data_inicial)
        params.append(data_final)

    # status
    if status:
        query += " AND r.status = %s"
        params.append(status)

    # cliente
    if cliente:
        query += " AND r.cliente = %s"
        params.append(cliente)

    # plano de contas
    if plano_conta:
        query += " AND r.plano_conta = %s"
        params.append(plano_conta)

    query += " ORDER BY r.data_vencimento ASC, r.id DESC"

    cursor.execute(query, params)
    resultados = cursor.fetchall()

    for item in resultados:
        if item.get('data_pagamento'):
            item['status'] = 'Pago'
        elif item.get('data_vencimento') and item['data_vencimento'] < date.today():
            item['status'] = 'Atrasado'
        else:
            item['status'] = 'Pendente'

        if item.get('hora') is not None:
            item['hora'] = str(item['hora'])

        if item.get('hora_lancamento') is not None:
            item['hora_lancamento'] = str(item['hora_lancamento'])

        if item.get('hora_lembrete') is not None:
            item['hora_lembrete'] = str(item['hora_lembrete'])

        if item.get('data_lancamento') is not None:
            item['data_lancamento'] = item['data_lancamento'].strftime('%Y-%m-%d')

        if item.get('data_vencimento') is not None:
            item['data_vencimento'] = item['data_vencimento'].strftime('%Y-%m-%d')

        if item.get('data_pagamento') is not None:
            item['data_pagamento'] = item['data_pagamento'].strftime('%Y-%m-%d')

    cursor.close()
    conexao.close()

    return jsonify(resultados)






@pagina.route(f'/{MODULO}/salvar', methods=['POST'])
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def salvar():
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    try:
        registro_id = request.form.get('id', '').strip()
        descricao = request.form.get('descricao', '').strip()

        data_lancamento = request.form.get('data_lancamento', '').strip() or None
        data_vencimento = request.form.get('data_vencimento', '').strip() or None
        data_pagamento = request.form.get('data_pagamento', '').strip() or None

        qtd_parcelas = request.form.get('qtd_parcelas', '').strip() or '1'

        valor = valor_para_numero(request.form.get('valor', '0'))
        desconto = valor_para_numero(request.form.get('desconto', '0'))
        multa = valor_para_numero(request.form.get('multa', '0'))
        juros = valor_para_numero(request.form.get('juros', '0'))

        cliente = request.form.get('cliente', '').strip() or None
        forma_pagamento = request.form.get('forma_pagamento', '').strip() or None
        plano_conta = request.form.get('plano_conta', '').strip() or None
        frequencia = request.form.get('frequencia', '').strip() or None

        observacoes = request.form.get('observacoes', '').strip()

        usuario_id = session.get('usuario_id')
        editando = bool(registro_id)

        if editando:
            if not tem_acao(usuario_id, 'editar'):
                cursor.close()
                conexao.close()
                return jsonify({
                    'status': 'erro',
                    'mensagem': 'Você não tem permissão para editar.'
                }), 403
        else:
            if not tem_acao(usuario_id, 'inserir'):
                cursor.close()
                conexao.close()
                return jsonify({
                    'status': 'erro',
                    'mensagem': 'Você não tem permissão para inserir.'
                }), 403

        if not descricao:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Informe a descrição.'
            }), 400

        if not data_lancamento:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Informe a data de lançamento.'
            }), 400

        if not data_vencimento:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Informe a data de vencimento.'
            }), 400

        if valor <= 0:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Informe um valor válido.'
            }), 400

        try:
            qtd_parcelas = int(qtd_parcelas)
        except:
            qtd_parcelas = 1

        if qtd_parcelas < 1:
            qtd_parcelas = 1

        if qtd_parcelas > 1 and not frequencia:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Para lançar mais de uma parcela, informe uma frequência.'
            }), 400

        subtotal = valor - desconto + multa + juros

        if subtotal < 0:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'O subtotal não pode ser negativo.'
            }), 400

        status = 'Pago' if data_pagamento else 'Pendente'
        usuario_pagamento = usuario_id if data_pagamento else None

        if editando:
            cursor.execute(f"SELECT * FROM {TABELA} WHERE id = %s", (registro_id,))
            registro_atual = cursor.fetchone()

            if not registro_atual:
                cursor.close()
                conexao.close()
                return jsonify({
                    'status': 'erro',
                    'mensagem': 'Registro não encontrado.'
                }), 404

            if data_pagamento and not registro_atual.get('usuario_pagamento'):
                usuario_pagamento = usuario_id
            else:
                usuario_pagamento = registro_atual.get('usuario_pagamento')

            cursor.execute(f"""
                UPDATE {TABELA} SET
                    descricao = %s,
                    valor = %s,
                    desconto = %s,
                    multa = %s,
                    juros = %s,
                    subtotal = %s,
                    data_lancamento = %s,
                    data_vencimento = %s,
                    data_pagamento = %s,
                    status = %s,
                    cliente = %s,
                    forma_pagamento = %s,
                    plano_conta = %s,
                    frequencia = %s,
                    qtd_parcelas = %s,
                    observacoes = %s,
                    usuario_pagamento = %s
                WHERE id = %s
            """, (
                descricao,
                valor,
                desconto,
                multa,
                juros,
                subtotal,
                data_lancamento,
                data_vencimento,
                data_pagamento,
                status,
                cliente,
                forma_pagamento,
                plano_conta,
                frequencia,
                qtd_parcelas,
                observacoes,
                usuario_pagamento,
                registro_id
            ))

            conexao.commit()

            cursor.close()
            conexao.close()

            registrar_log(
                acao='editar',
                entidade=TABELA,
                registro_id=registro_id,
                descricao=f"registro editado em {TABELA}: {descricao}"
            )

            return jsonify({
                'status': 'sucesso',
                'mensagem': 'Registro atualizado com sucesso.',
                'acao': 'update',
                'id': registro_id
            })

        else:
            dias_frequencia = 0

            config = get_config_sistema()
            hora_ini = config.get('hora_inicial_alerta') or '08:00'
            hora_fim = config.get('hora_final_alerta') or '18:00'

            hora_sorteada = gerar_hora_aleatoria(hora_ini, hora_fim)

            if frequencia:
                cursor.execute("SELECT dias FROM frequencias WHERE id = %s", (frequencia,))
                freq = cursor.fetchone()

                if not freq:
                    cursor.close()
                    conexao.close()
                    return jsonify({
                        'status': 'erro',
                        'mensagem': 'Frequência não encontrada.'
                    }), 400

                dias_frequencia = int(freq.get('dias') or 0)

            data_lancamento_base = datetime.strptime(data_lancamento, '%Y-%m-%d').date()
            data_vencimento_base = datetime.strptime(data_vencimento, '%Y-%m-%d').date()
            data_pagamento_base = datetime.strptime(data_pagamento, '%Y-%m-%d').date() if data_pagamento else None

            novo_id = None

            for parcela_atual in range(1, qtd_parcelas + 1):
                if parcela_atual == 1:
                    data_lancamento_parcela = data_lancamento_base
                    data_vencimento_parcela = data_vencimento_base
                    data_pagamento_parcela = data_pagamento_base
                    status_parcela = status
                    usuario_pagamento_parcela = usuario_pagamento
                else:
                    incremento = timedelta(days=dias_frequencia)
                    data_lancamento_parcela = data_lancamento_base + (incremento * (parcela_atual - 1))
                    data_vencimento_parcela = data_vencimento_base + (incremento * (parcela_atual - 1))
                    data_pagamento_parcela = None
                    status_parcela = 'Pendente'
                    usuario_pagamento_parcela = None

                cursor.execute(f"""
                    INSERT INTO {TABELA} (
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
                        %s, %s, %s, %s, %s, %s, %s, curTime(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, curTime(), %s, 'Não', %s, 'Sim'
                    )
                """, (
                    descricao,
                    valor,
                    desconto,
                    multa,
                    juros,
                    subtotal,
                    data_lancamento_parcela,
                    data_vencimento_parcela,
                    data_pagamento_parcela,
                    status_parcela,
                    cliente,
                    forma_pagamento,
                    plano_conta,
                    frequencia,
                    'Sim' if qtd_parcelas > 1 else 'Não',
                    qtd_parcelas,
                    parcela_atual,
                    None,
                    'Conta',
                    usuario_id,
                    usuario_pagamento_parcela,
                    hora_sorteada,
                    observacoes
                ))

                if not novo_id:
                    novo_id = cursor.lastrowid
                    cursor.execute(f"UPDATE {TABELA} SET id_ref = %s WHERE id = %s", (novo_id, novo_id))

                else:
                    cursor.execute(f"UPDATE {TABELA} SET id_ref = %s WHERE id = %s", (novo_id, cursor.lastrowid))

            conexao.commit()

            cursor.close()
            conexao.close()

            registrar_log(
                acao='inserir',
                entidade=TABELA,
                registro_id=novo_id,
                descricao=f"novo cadastro em {TABELA}: {descricao}"
            )

            mensagem = 'Registros cadastrados com sucesso.' if qtd_parcelas > 1 else 'Registro cadastrado com sucesso.'

            return jsonify({
                'status': 'sucesso',
                'mensagem': mensagem,
                'acao': 'insert',
                'id': novo_id
            })

    except Exception as e:
        conexao.rollback()
        cursor.close()
        conexao.close()

        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro interno ao salvar registro. ' + str(e),
            'erro': str(e)
        }), 500

    



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

        cursor.execute(
            f"SELECT * FROM {TABELA} WHERE id = %s",
            (registro_id,)
        )
        registro = cursor.fetchone()

        if not registro:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Registro não encontrado.'
            }), 404

        cursor.execute(
            f"DELETE FROM {TABELA} WHERE id = %s",
            (registro_id,)
        )
        conexao.commit()

        registrar_log(
            acao='excluir',
            entidade=TABELA,
            registro_id=registro_id,
            descricao=f"registro excluido em {TABELA}: {registro['descricao']}"
        )

        return jsonify({
            'status': 'sucesso',
            'mensagem': 'Registro excluído com sucesso.'
        })

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
            return jsonify({
                'status': 'erro',
                'mensagem': 'Nenhum registro foi selecionado.'
            }), 400

        ids_validos = [str(i).strip() for i in ids if str(i).strip().isdigit()]

        if not ids_validos:
            return jsonify({
                'status': 'erro',
                'mensagem': 'IDs inválidos.'
            }), 400

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        placeholders = ','.join(['%s'] * len(ids_validos))

        cursor.execute(
            f"SELECT * FROM {TABELA} WHERE id IN ({placeholders})",
            tuple(ids_validos)
        )
        registros_encontrados = cursor.fetchall()

        if not registros_encontrados:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Nenhum registro encontrado.'
            }), 404

        cursor.execute(
            f"DELETE FROM {TABELA} WHERE id IN ({placeholders})",
            tuple(ids_validos)
        )
        conexao.commit()

        for registro in registros_encontrados:
            registrar_log(
                acao='excluir',
                entidade=TABELA,
                registro_id=registro['id'],
                descricao=f"registro excluido em {TABELA}: {registro['descricao']}"
            )

        return jsonify({
            'status': 'sucesso',
            'mensagem': 'Registros excluídos com sucesso.'
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


@pagina.route(f'/{MODULO}/listar-select')
@login_required
def listar_select():
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute(f"SELECT nome FROM {TABELA} WHERE ativo = 'Sim' ORDER BY nome ASC")
    lista = cursor.fetchall()

    cursor.close()
    conexao.close()

    return jsonify(lista)


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
            return jsonify({
                'status': 'erro',
                'mensagem': 'ID do registro não informado.'
            }), 400

        if ativo not in ['Sim', 'Não']:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Status inválido.'
            }), 400

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute(
            f"SELECT id, nome, ativo FROM {TABELA} WHERE id = %s",
            (registro_id,)
        )
        registro = cursor.fetchone()

        if not registro:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Registro não encontrado.'
            }), 404

        cursor.execute(
            f"UPDATE {TABELA} SET ativo = %s WHERE id = %s",
            (ativo, registro_id)
        )
        conexao.commit()

        registrar_log(
            acao='editar',
            entidade=TABELA,
            registro_id=registro_id,
            descricao=f"status alterado em {TABELA}: {registro['nome']}"
        )

        mensagem = 'Registro ativado com sucesso.' if ativo == 'Sim' else 'Registro desativado com sucesso.'

        return jsonify({
            'status': 'sucesso',
            'mensagem': mensagem
        })

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





@pagina.route(f'/{MODULO}/baixar', methods=['POST'])
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def baixar():
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    try:
        usuario_id = session.get('usuario_id')

        if not tem_acao(usuario_id, 'editar'):
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Você não tem permissão para baixar contas.'
            }), 403

        registro_id = request.form.get('id', '').strip()
        data_pagamento = request.form.get('data_pagamento', '').strip()
        forma_pagamento = request.form.get('forma_pagamento', '').strip() or None
        valor_pago = valor_para_numero(request.form.get('valor', '0'))
        desconto = valor_para_numero(request.form.get('desconto', '0'))
        multa = valor_para_numero(request.form.get('multa', '0'))
        juros = valor_para_numero(request.form.get('juros', '0'))
        observacoes = request.form.get('observacoes', '').strip()

        if not registro_id:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'ID do registro não informado.'
            }), 400

        if not data_pagamento:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Informe a data do pagamento.'
            }), 400

        cursor.execute(
            f"SELECT * FROM {TABELA} WHERE id = %s",
            (registro_id,)
        )
        registro = cursor.fetchone()

        if not registro:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Registro não encontrado.'
            }), 404

        if registro.get('status') == 'Pago' or registro.get('data_pagamento'):
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Esta conta já está paga.'
            }), 400

        valor_original = float(registro.get('valor') or 0)

        if valor_pago <= 0:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Informe um valor válido para a baixa.'
            }), 400

        if valor_pago > valor_original:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'O valor informado não pode ser maior que o valor da conta.'
            }), 400

        subtotal_pago = valor_pago - desconto + multa + juros

        if subtotal_pago < 0:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'O subtotal não pode ser negativo.'
            }), 400

        residuo_valor = round(valor_original - valor_pago, 2)
        id_residuo_gerado = None

        # baixa da conta atual com o valor realmente recebido
        cursor.execute(f"""
            UPDATE {TABELA} SET
                valor = %s,
                data_pagamento = %s,
                forma_pagamento = %s,
                desconto = %s,
                multa = %s,
                juros = %s,
                subtotal = %s,
                observacoes = %s,
                usuario_pagamento = %s,
                status = 'Pago'
            WHERE id = %s
        """, (
            valor_pago,
            data_pagamento,
            forma_pagamento,
            desconto,
            multa,
            juros,
            subtotal_pago,
            observacoes,
            usuario_id,
            registro_id
        ))

        # se recebeu menos, gera o resíduo
        if residuo_valor > 0:
            descricao_residuo = f"{registro.get('descricao')} - Resíduo"

            cursor.execute(f"""
                INSERT INTO {TABELA} (
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
                    frequencia,
                    recorrente,
                    qtd_parcelas,
                    parcela,
                    id_ref,
                    id_residuo,
                    referencia,
                    usuario_lancamento,
                    usuario_pagamento,
                    hora,
                    hora_lembrete,
                    alertado,
                    observacoes,
                    ativo
                ) VALUES (
                    %s, %s, 0, 0, 0, %s, %s, curTime(), %s, NULL, 'Pendente',
                    %s, NULL, %s, NULL, 'Não', 1, 1, NULL, %s, 'Resíduo',
                    %s, NULL, curTime(), %s, 'Não', %s, 'Sim'
                )
            """, (
                descricao_residuo,
                residuo_valor,
                residuo_valor,
                registro.get('data_lancamento'),
                registro.get('data_vencimento'),
                registro.get('cliente'),
                registro.get('plano_conta'),
                registro_id,
                registro.get('usuario_lancamento'),
                registro.get('hora_lembrete'),
                f"Resíduo gerado na baixa da conta ID {registro_id}."
            ))

            id_residuo_gerado = cursor.lastrowid

            # grava o vínculo no registro original
            cursor.execute(f"""
                UPDATE {TABELA}
                SET id_residuo = %s
                WHERE id = %s
            """, (id_residuo_gerado, registro_id))

        conexao.commit()

        # recorrência automática: só gera próxima se não houve resíduo
        qtd_parcelas = int(registro.get('qtd_parcelas') or 1)
        frequencia_id = registro.get('frequencia')

        if residuo_valor <= 0 and qtd_parcelas <= 1 and frequencia_id:
            cursor.execute(
                "SELECT dias FROM frequencias WHERE id = %s",
                (frequencia_id,)
            )
            freq = cursor.fetchone()

            if freq and freq.get('dias'):
                dias_frequencia = int(freq['dias'])

                data_lancamento_base = registro.get('data_lancamento')
                data_vencimento_base = registro.get('data_vencimento')

                if hasattr(data_lancamento_base, 'date'):
                    data_lancamento_base = data_lancamento_base.date()

                if hasattr(data_vencimento_base, 'date'):
                    data_vencimento_base = data_vencimento_base.date()

                nova_data_lancamento = data_lancamento_base + timedelta(days=dias_frequencia) if data_lancamento_base else None
                nova_data_vencimento = data_vencimento_base + timedelta(days=dias_frequencia) if data_vencimento_base else None

                cursor.execute(f"""
                    INSERT INTO {TABELA} (
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
                        frequencia,
                        recorrente,
                        qtd_parcelas,
                        parcela,
                        id_ref,
                        id_residuo,
                        observacoes,
                        usuario_lancamento,
                        usuario_pagamento,
                        ativo,
                        referencia,
                        hora,
                        hora_lembrete,
                        alertado
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, curTime(), %s, NULL, 'Pendente',
                        %s, NULL, %s, %s, 'Não', 1, 1, NULL, NULL, %s, %s, NULL,
                        'Sim', 'Conta', curTime(), %s, 'Não'
                    )
                """, (
                    registro.get('descricao'),
                    registro.get('valor') or 0,
                    registro.get('desconto') or 0,
                    registro.get('multa') or 0,
                    registro.get('juros') or 0,
                    registro.get('subtotal') or 0,
                    nova_data_lancamento,
                    nova_data_vencimento,
                    registro.get('cliente'),
                    registro.get('plano_conta'),
                    registro.get('frequencia'),
                    registro.get('observacoes'),
                    registro.get('usuario_lancamento'),
                    registro.get('hora_lembrete')
                ))

                conexao.commit()

        registrar_log(
            acao='editar',
            entidade=TABELA,
            registro_id=registro_id,
            descricao=f"baixa realizada em {TABELA}: {registro['descricao']}"
        )

        if id_residuo_gerado:
            registrar_log(
                acao='inserir',
                entidade=TABELA,
                registro_id=id_residuo_gerado,
                descricao=f"resíduo gerado em {TABELA} a partir do registro {registro_id}"
            )

        cursor.close()
        conexao.close()

        mensagem = 'Conta baixada com sucesso.'
        if id_residuo_gerado:
            mensagem = 'Conta baixada com sucesso e resíduo gerado.'

        return jsonify({
            'status': 'sucesso',
            'mensagem': mensagem,
            'id_residuo': id_residuo_gerado
        })

    except Exception as e:
        if conexao:
            conexao.rollback()
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro interno ao baixar conta.',
            'erro': str(e)
        }), 500




@pagina.route(f'/{MODULO}/cancelar-baixa', methods=['POST'])
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def cancelar_baixa():
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    try:
        usuario_id = session.get('usuario_id')

        if not tem_acao(usuario_id, 'editar'):
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Você não tem permissão para cancelar a baixa.'
            }), 403

        dados = request.get_json(silent=True) or {}
        registro_id = str(dados.get('id', '')).strip()

        if not registro_id:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'ID do registro não informado.'
            }), 400

        cursor.execute(
            f"SELECT * FROM {TABELA} WHERE id = %s",
            (registro_id,)
        )
        registro = cursor.fetchone()

        if not registro:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Registro não encontrado.'
            }), 404

        if not registro.get('data_pagamento') and registro.get('status') != 'Pago':
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Esta conta não está paga.'
            }), 400

        data_vencimento = registro.get('data_vencimento')
        novo_status = 'Pendente'

        if data_vencimento:
            try:
                if hasattr(data_vencimento, 'date'):
                    data_vencimento = data_vencimento.date()

                if data_vencimento < date.today():
                    novo_status = 'Atrasado'
            except:
                novo_status = 'Pendente'

        cursor.execute(f"""
            UPDATE {TABELA} SET
                data_pagamento = NULL,
                usuario_pagamento = NULL,
                forma_pagamento = NULL,
                status = %s
            WHERE id = %s
        """, (
            novo_status,
            registro_id
        ))

        conexao.commit()

        registrar_log(
            acao='editar',
            entidade=TABELA,
            registro_id=registro_id,
            descricao=f"baixa cancelada em {TABELA}: {registro['descricao']}"
        )

        cursor.close()
        conexao.close()

        return jsonify({
            'status': 'sucesso',
            'mensagem': 'Baixa cancelada com sucesso.'
        })

    except Exception as e:
        conexao.rollback()
        cursor.close()
        conexao.close()

        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro interno ao cancelar a baixa.',
            'erro': str(e)
        }), 500




@pagina.route(f'/{MODULO}/parcelar', methods=['POST'])
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def parcelar():
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    try:
        usuario_id = session.get('usuario_id')

        if not tem_acao(usuario_id, 'editar'):
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Você não tem permissão para parcelar contas.'
            }), 403

        registro_id = request.form.get('id', '').strip()
        qtd_parcelas = request.form.get('qtd_parcelas', '').strip()
        frequencia = request.form.get('frequencia', '').strip()
        observacoes = request.form.get('observacoes', '').strip()

        if not registro_id:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'ID do registro não informado.'
            }), 400

        try:
            qtd_parcelas = int(qtd_parcelas)
        except:
            qtd_parcelas = 0

        if qtd_parcelas < 2:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Informe ao menos 2 parcelas.'
            }), 400

        if not frequencia:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Informe a frequência do parcelamento.'
            }), 400

        cursor.execute(
            f"SELECT * FROM {TABELA} WHERE id = %s",
            (registro_id,)
        )
        registro = cursor.fetchone()

        if not registro:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Registro não encontrado.'
            }), 404

        if registro.get('status') == 'Pago' or registro.get('data_pagamento'):
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Não é possível parcelar uma conta já paga.'
            }), 400

        if int(registro.get('qtd_parcelas') or 1) > 1:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Esta conta já está parcelada.'
            }), 400

        cursor.execute(
            "SELECT dias FROM frequencias WHERE id = %s",
            (frequencia,)
        )
        freq = cursor.fetchone()

        if not freq:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Frequência não encontrada.'
            }), 400

        dias_frequencia = int(freq.get('dias') or 0)

        if dias_frequencia <= 0:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'A frequência precisa ter dias válidos.'
            }), 400

        valor_total = float(registro.get('valor') or 0)

        if valor_total <= 0:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'O valor da conta precisa ser maior que zero para parcelar.'
            }), 400

        # divisão exata em centavos
        total_centavos = int(round(valor_total * 100))
        base_centavos = total_centavos // qtd_parcelas
        resto_centavos = total_centavos % qtd_parcelas

        data_lancamento_base = registro.get('data_lancamento')
        data_vencimento_base = registro.get('data_vencimento')

        if hasattr(data_lancamento_base, 'date'):
            data_lancamento_base = data_lancamento_base.date()

        if hasattr(data_vencimento_base, 'date'):
            data_vencimento_base = data_vencimento_base.date()

        # remove a conta original para recriar parcelada
        cursor.execute(
            f"DELETE FROM {TABELA} WHERE id = %s",
            (registro_id,)
        )

        novo_primeiro_id = None

        for parcela_atual in range(1, qtd_parcelas + 1):
            valor_centavos = base_centavos

            # joga a diferença para a última
            if parcela_atual == qtd_parcelas:
                valor_centavos += resto_centavos

            valor_parcela = valor_centavos / 100

            nova_data_lancamento = data_lancamento_base + timedelta(days=dias_frequencia * (parcela_atual - 1)) if data_lancamento_base else None
            nova_data_vencimento = data_vencimento_base + timedelta(days=dias_frequencia * (parcela_atual - 1)) if data_vencimento_base else None

            nova_descricao = f"{registro.get('descricao')} - Parcela: {parcela_atual}"

            cursor.execute(f"""
                INSERT INTO {TABELA} (
                    descricao,
                    valor,
                    desconto,
                    multa,
                    juros,
                    subtotal,
                    data_lancamento,
                    data_vencimento,
                    data_pagamento,
                    status,
                    cliente,
                    forma_pagamento,
                    plano_conta,
                    centro_custo,
                    frequencia,
                    qtd_parcelas,
                    parcela,
                    observacoes,
                    usuario_lancamento,
                    usuario_pagamento,
                    ativo,
                    referencia,
                    hora,
                    hora_lembrete,
                    alertado
                ) VALUES (%s, %s, 0, 0, 0, %s, %s, %s, NULL, 'Pendente', %s, NULL, %s, %s, %s, %s, %s, %s, %s, NULL, 'Sim', 'Conta', curTime(), %s, 'Não')
            """, (
                nova_descricao,
                valor_parcela,
                valor_parcela,
                nova_data_lancamento,
                nova_data_vencimento,
                registro.get('cliente'),
                registro.get('plano_conta'),
                registro.get('centro_custo'),
                frequencia,
                qtd_parcelas,
                parcela_atual,
                observacoes if observacoes else registro.get('observacoes'),
                registro.get('usuario_lancamento'),
                registro.get('hora_lembrete')
            ))

            if not novo_primeiro_id:
                novo_primeiro_id = cursor.lastrowid

        conexao.commit()

        registrar_log(
            acao='editar',
            entidade=TABELA,
            registro_id=registro_id,
            descricao=f"conta parcelada em {TABELA}: {registro['descricao']} em {qtd_parcelas}x"
        )

        cursor.close()
        conexao.close()

        return jsonify({
            'status': 'sucesso',
            'mensagem': 'Conta parcelada com sucesso.',
            'id': novo_primeiro_id
        })

    except Exception as e:
        if conexao:
            conexao.rollback()
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro interno ao parcelar conta.',
            'erro': str(e)
        }), 500





@pagina.route(f'/{MODULO}/relatorio', methods=['POST'])
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def relatorio_recebimentos():
    conexao = None
    cursor = None

    try:
        data_inicial = request.form.get('data_inicial', '').strip()
        data_final = request.form.get('data_final', '').strip()
        status = request.form.get('status', '').strip()
        cliente = request.form.get('cliente', '').strip()
        plano_conta = request.form.get('plano_conta', '').strip()

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        query = """
            SELECT
                r.*,
                c.nome AS cliente_nome,
                pc.nome AS plano_conta_nome,
                fp.nome AS forma_pagamento_nome,
                fr.nome AS frequencia_nome
            FROM recebimentos r
            LEFT JOIN clientes c ON c.id = r.cliente
            LEFT JOIN plano_contas pc ON pc.id = r.plano_conta
            LEFT JOIN formas_pagamento fp ON fp.id = r.forma_pagamento
            LEFT JOIN frequencias fr ON fr.id = r.frequencia
            WHERE 1=1
        """
        valores = []

        if data_inicial:
            query += " AND r.data_vencimento >= %s"
            valores.append(data_inicial)

        if data_final:
            query += " AND r.data_vencimento <= %s"
            valores.append(data_final)

        if cliente:
            query += " AND r.cliente = %s"
            valores.append(cliente)

        if plano_conta:
            query += " AND r.plano_conta = %s"
            valores.append(plano_conta)

        query += " ORDER BY r.data_vencimento ASC, r.id DESC"

        cursor.execute(query, tuple(valores))
        lista_recebimentos = cursor.fetchall()

        total_geral = 0
        total_pago = 0
        total_pendente = 0
        total_atrasado = 0

        for item in lista_recebimentos:
            if item.get('data_pagamento'):
                item['status'] = 'Pago'
            elif item.get('data_vencimento') and item['data_vencimento'] < date.today():
                item['status'] = 'Atrasado'
            else:
                item['status'] = 'Pendente'

            valor_item = float(item.get('subtotal') or 0)
            total_geral += valor_item

            if item['status'] == 'Pago':
                total_pago += valor_item
            elif item['status'] == 'Atrasado':
                total_atrasado += valor_item
            else:
                total_pendente += valor_item

        if status:
            lista_recebimentos = [item for item in lista_recebimentos if item.get('status') == status]

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

        plano_conta_nome_filtro = 'Todos'
        if plano_conta:
            cursor.execute(
                "SELECT nome FROM plano_contas WHERE id = %s LIMIT 1",
                (plano_conta,)
            )
            plano_filtro = cursor.fetchone()
            if plano_filtro:
                plano_conta_nome_filtro = plano_filtro.get('nome') or f'Plano #{plano_conta}'
            else:
                plano_conta_nome_filtro = f'Plano #{plano_conta}'

        status_filtro = status if status else 'Todos'

        query_planos = """
            SELECT
                COALESCE(pc.nome, 'Não informado') AS nome,
                COUNT(r.id) AS quantidade,
                SUM(r.subtotal) AS total
            FROM recebimentos r
            LEFT JOIN plano_contas pc ON pc.id = r.plano_conta
            WHERE 1=1
        """
        valores_planos = []

        if data_inicial:
            query_planos += " AND r.data_vencimento >= %s"
            valores_planos.append(data_inicial)

        if data_final:
            query_planos += " AND r.data_vencimento <= %s"
            valores_planos.append(data_final)

        if cliente:
            query_planos += " AND r.cliente = %s"
            valores_planos.append(cliente)

        if plano_conta:
            query_planos += " AND r.plano_conta = %s"
            valores_planos.append(plano_conta)

        query_planos += " GROUP BY pc.nome ORDER BY total DESC"
        cursor.execute(query_planos, tuple(valores_planos))
        resumo_planos = cursor.fetchall()

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
            'relatorios/recebimentos.html',
            dados=lista_recebimentos,
            data_inicial=data_inicial,
            data_final=data_final,
            data_inicial_label=data_inicial_label,
            data_final_label=data_final_label,
            status_filtro=status_filtro,
            cliente_nome_filtro=cliente_nome_filtro,
            plano_conta_nome_filtro=plano_conta_nome_filtro,
            total_geral=total_geral,
            total_pago=total_pago,
            total_pendente=total_pendente,
            total_atrasado=total_atrasado,
            resumo_planos=resumo_planos,
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
            headers={'Content-Disposition': 'inline; filename=relatorio_recebimentos.pdf'}
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




def gerar_hora_aleatoria(hora_inicio_str, hora_fim_str):
    try:
        # Converte strings "HH:MM" para minutos totais desde o início do dia
        h_ini, m_ini = map(int, hora_inicio_str.split(':'))
        h_fim, m_fim = map(int, hora_fim_str.split(':'))
        
        inicio_em_minutos = h_ini * 60 + m_ini
        fim_em_minutos = h_fim * 60 + m_fim
        
        # Garante que o fim seja maior que o início
        if fim_em_minutos <= inicio_em_minutos:
            return "09:00" # Fallback caso a config esteja errada
            
        sorteio_minutos = random.randint(inicio_em_minutos, fim_em_minutos)
        
        horas = sorteio_minutos // 60
        minutos = sorteio_minutos % 60
        
        return f"{horas:02d}:{minutos:02d}"
    except:
        return "08:00" # Fallback para erros de conversão





@pagina.route(f'/{MODULO}/recibo/<int:id>')
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def recibo(id):
    conexao = None
    cursor = None

    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                r.*,
                c.nome AS cliente_nome,
                fp.nome AS forma_pagamento_nome,
                ul.nome AS usuario_lancamento_nome,
                up.nome AS usuario_pagamento_nome
            FROM recebimentos r
            LEFT JOIN clientes c ON r.cliente = c.id
            LEFT JOIN formas_pagamento fp ON r.forma_pagamento = fp.id
            LEFT JOIN usuarios ul ON r.usuario_lancamento = ul.id
            LEFT JOIN usuarios up ON r.usuario_pagamento = up.id
            WHERE r.id = %s
            LIMIT 1
        """, (id,))
        recebimento = cursor.fetchone()

        if not recebimento:
            return "Recebimento não encontrado.", 404

        config_sistema = get_config_sistema()

        # logo
        logo_src = None
        logo_arquivo = (config_sistema.get('logo') or '').strip()
        if logo_arquivo:
            logo_path = os.path.join('app', 'static', 'img', logo_arquivo)
            logo_src = arquivo_para_data_uri(logo_path)

        # assinatura do usuário logado
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

        return render_template(
            'relatorios/recibo_recebimento.html',
            recebimento=recebimento,
            now=datetime.now,
            config_sistema=config_sistema,
            logo_src=logo_src,
            assinatura_src=assinatura_src,
            assinatura_nome=assinatura_nome
        )

    except Exception as e:
        return f"Erro ao gerar recibo: {str(e)}", 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()






@pagina.route(f'/{MODULO}/enviar-cobranca', methods=['POST'])
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def enviar_cobranca():
    conexao = None
    cursor = None

    try:
        dados = request.get_json(silent=True) or {}
        registro_id = str(dados.get('id', '')).strip()

        if not registro_id:
            return jsonify({
                'status': 'erro',
                'mensagem': 'ID do recebimento não informado.'
            }), 400

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                r.*,
                c.nome AS cliente_nome,
                c.email AS cliente_email,
                c.telefone AS cliente_telefone,
                c.whatsapp AS cliente_whatsapp
            FROM recebimentos r
            LEFT JOIN clientes c ON r.cliente = c.id
            WHERE r.id = %s
            LIMIT 1
        """, (registro_id,))

        conta = cursor.fetchone()

        if not conta:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Recebimento não encontrado.'
            }), 404

        if conta.get('data_pagamento'):
            return jsonify({
                'status': 'erro',
                'mensagem': 'Esta conta já está paga. Nenhuma cobrança foi enviada.'
            }), 400

        cliente_nome = conta.get('cliente_nome') or 'Cliente'
        cliente_email = conta.get('cliente_email')
        cliente_whatsapp = conta.get('cliente_whatsapp') or conta.get('cliente_telefone')
        

        descricao = conta.get('descricao') or 'Conta em aberto'
        valor = float(conta.get('subtotal') or conta.get('valor') or 0)
        data_vencimento = conta.get('data_vencimento')


        config_sistema = get_config_sistema()

        tipo_dados_pagamento = (config_sistema.get('tipo_dados_pagamento') or '').strip()
        dados_pagamento = (config_sistema.get('dados_pagamento') or '').strip()
        beneficiario = (config_sistema.get('beneficiario') or '').strip()
        nome_sistema = (config_sistema.get('nome_sistema') or '').strip()

        bloco_pagamento_whatsapp = ''
        bloco_pagamento_html = ''
        bloco_pagamento_texto = ''

        if dados_pagamento or beneficiario:
            tipo_label = ''

            if tipo_dados_pagamento == 'pix':
                tipo_label = 'PIX'
            elif tipo_dados_pagamento == 'conta':
                tipo_label = 'Conta Bancária'
            else:
                tipo_label = 'Dados para pagamento'

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

        valor_formatado = f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

        data_vencimento_br = ''
        if data_vencimento:
            data_vencimento_br = data_vencimento.strftime('%d/%m/%Y')

        hoje = date.today()

        if data_vencimento and data_vencimento < hoje:
            tipo_mensagem = 'cobranca'
            assunto = f"{nome_sistema} - Cobrança de conta vencida"

            mensagem_whatsapp = f"""⚠️ *{nome_sistema.upper()}*

*COBRANÇA DE CONTA VENCIDA*

Olá *{cliente_nome}*.

Identificamos uma conta em aberto vencida em nosso sistema.

📌 *Descrição:* {descricao}
💰 *Valor:* {valor_formatado}
📅 *Vencimento:* {data_vencimento_br}

Por favor, regularize o pagamento assim que possível.

{bloco_pagamento_whatsapp}

Caso já tenha realizado o pagamento, desconsidere esta mensagem.
"""

            mensagem_html = f"""
            <p>Olá <strong>{cliente_nome}</strong>,</p>

            <p>Identificamos uma conta em aberto vencida em nosso sistema.</p>

            <p>
                <strong>Descrição:</strong> {descricao}<br>
                <strong>Valor:</strong> {valor_formatado}<br>
                <strong>Vencimento:</strong> {data_vencimento_br}
            </p>

            <p>Por favor, regularize o pagamento assim que possível.</p>

            {bloco_pagamento_html}

            <p>Caso já tenha realizado o pagamento, desconsidere esta mensagem.</p>
            """

            mensagem_texto = f"""
Olá {cliente_nome}

Identificamos uma conta em aberto vencida em nosso sistema.

Descrição: {descricao}
Valor: {valor_formatado}
Vencimento: {data_vencimento_br}

Por favor, regularize o pagamento assim que possível.

Caso já tenha realizado o pagamento, desconsidere esta mensagem.
"""

        else:
            tipo_mensagem = 'aviso'
            assunto = f"{nome_sistema} - Aviso de vencimento"

            mensagem_whatsapp = f"""🔔 *{nome_sistema.upper()}*

*AVISO DE VENCIMENTO*

Olá *{cliente_nome}*.

Estamos passando para lembrar sobre uma conta em aberto.

📌 *Descrição:* {descricao}
💰 *Valor:* {valor_formatado}
📅 *Vencimento:* {data_vencimento_br}

Evite atrasos realizando o pagamento até a data de vencimento.

{bloco_pagamento_whatsapp}

Caso já tenha realizado o pagamento, desconsidere esta mensagem.
"""

            mensagem_html = f"""
            <p>Olá <strong>{cliente_nome}</strong>,</p>

            <p>Estamos passando para lembrar sobre uma conta em aberto.</p>

            <p>
                <strong>Descrição:</strong> {descricao}<br>
                <strong>Valor:</strong> {valor_formatado}<br>
                <strong>Vencimento:</strong> {data_vencimento_br}
            </p>

            <p>Evite atrasos realizando o pagamento até a data de vencimento.</p>

            {bloco_pagamento_html}

            <p>Caso já tenha realizado o pagamento, desconsidere esta mensagem.</p>
            """

            mensagem_texto = f"""
Olá {cliente_nome}

Estamos passando para lembrar sobre uma conta em aberto.

Descrição: {descricao}
Valor: {valor_formatado}
Vencimento: {data_vencimento_br}

Evite atrasos realizando o pagamento até a data de vencimento.

{bloco_pagamento_texto}

Caso já tenha realizado o pagamento, desconsidere esta mensagem.
"""

        enviou_whatsapp = False
        enviou_email = False

        if cliente_whatsapp:
            enviar_whatsapp_texto(cliente_whatsapp, mensagem_whatsapp)
            enviou_whatsapp = True

        if cliente_email:
            enviar_email_texto(cliente_email, assunto, mensagem_html, mensagem_texto)
            enviou_email = True

        if not enviou_whatsapp and not enviou_email:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Cliente sem WhatsApp/telefone e sem e-mail cadastrado.'
            }), 400

        registrar_log(
            acao='editar',
            entidade=TABELA,
            registro_id=registro_id,
            descricao=f"mensagem de {'cobrança' if tipo_mensagem == 'cobranca' else 'aviso de vencimento'} enviada para {cliente_nome}"
        )

        canais = []
        if enviou_whatsapp:
            canais.append('WhatsApp')
        if enviou_email:
            canais.append('E-mail')

        return jsonify({
            'status': 'sucesso',
            'mensagem': 'Mensagem enviada via ' + ' e '.join(canais) + '.'
        })

    except Exception as e:
        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao enviar cobrança.',
            'erro': str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()