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

MODULO = 'despesas'
TABELA = 'despesas'
TEMPLATE = 'painel/despesas.html'
CHAVE_PERMISSAO = 'despesas'

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
    fornecedor = request.args.get('fornecedor')
    centro_custo = request.args.get('centro_custo')
    plano_conta = request.args.get('plano_conta')

    query = """
        SELECT 
            d.*,
            f.nome AS fornecedor_nome,
            pc.nome AS plano_conta_nome,
            cc.nome AS centro_custo_nome,
            fp.nome AS forma_pagamento_nome,
            fr.nome AS frequencia_nome,
            up.nome AS usuario_pgto,
            ul.nome AS usuario_lanc
        FROM despesas d
        LEFT JOIN fornecedores f ON d.fornecedor = f.id
        LEFT JOIN plano_contas pc ON d.plano_conta = pc.id
        LEFT JOIN centros_custo cc ON d.centro_custo = cc.id
        LEFT JOIN formas_pagamento fp ON d.forma_pagamento = fp.id
        LEFT JOIN frequencias fr ON d.frequencia = fr.id
        LEFT JOIN usuarios up ON d.usuario_pagamento = up.id
        LEFT JOIN usuarios ul ON d.usuario_lancamento = ul.id
        WHERE 1=1
    """

    params = []

    # 📅 filtro por data
    if data_inicial and data_final:
        query += " AND d.data_vencimento BETWEEN %s AND %s"
        params.append(data_inicial)
        params.append(data_final)

    # 📌 status
    if status:
        query += " AND d.status = %s"
        params.append(status)

    # 📌 fornecedor
    if fornecedor:
        query += " AND d.fornecedor = %s"
        params.append(fornecedor)

    # 📌 centro de custo
    if centro_custo:
        query += " AND d.centro_custo = %s"
        params.append(centro_custo)

    # 📌 plano de contas
    if plano_conta:
        query += " AND d.plano_conta = %s"
        params.append(plano_conta)

    query += " ORDER BY d.data_vencimento ASC, d.id DESC"

    cursor.execute(query, params)
    resultados = cursor.fetchall()

    # 🔄 Ajuste de status automático (REGRA DO SEU SISTEMA)
    for item in resultados:
        if item.get('data_pagamento'):
            item['status'] = 'Pago'
        elif item.get('data_vencimento') and item['data_vencimento'] < date.today():
            item['status'] = 'Atrasado'
        else:
            item['status'] = 'Pendente'

        if item.get('hora') is not None:
            item['hora'] = str(item['hora'])

        if item.get('data_lancamento') is not None:
            item['data_lancamento'] = item['data_lancamento'].strftime('%Y-%m-%d')

        if item.get('data_vencimento') is not None:
            item['data_vencimento'] = item['data_vencimento'].strftime('%Y-%m-%d')

        if item.get('data_pagamento') is not None:
            item['data_pagamento'] = item['data_pagamento'].strftime('%Y-%m-%d')

        # Adicione estas linhas para tratar o novo campo:
        if item.get('hora_lembrete') is not None:
            item['hora_lembrete'] = str(item['hora_lembrete'])

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

        fornecedor = request.form.get('fornecedor', '').strip() or None
        forma_pagamento = request.form.get('forma_pagamento', '').strip() or None
        plano_conta = request.form.get('plano_conta', '').strip() or None
        centro_custo = request.form.get('centro_custo', '').strip() or None
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
        recorrencia = qtd_parcelas if qtd_parcelas > 1 else 1

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
                    fornecedor = %s,
                    forma_pagamento = %s,
                    plano_conta = %s,
                    centro_custo = %s,
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
                fornecedor,
                forma_pagamento,
                plano_conta,
                centro_custo,
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

            # 1. Busca as configurações do sistema
            config = get_config_sistema()
            hora_ini = config.get('hora_inicial_alerta') or '08:00'
            hora_fim = config.get('hora_final_alerta') or '18:00'

            # 2. Gera a hora randômica baseada no config
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
                        data_vencimento,
                        data_pagamento,
                        status,
                        fornecedor,
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
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Sim', 'Conta', curTime(), %s, 'Não')
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
                    fornecedor,
                    forma_pagamento,
                    plano_conta,
                    centro_custo,
                    frequencia,
                    qtd_parcelas,                    
                    parcela_atual,
                    observacoes,
                    usuario_id,
                    usuario_pagamento_parcela,
                    hora_sorteada
                ))

                if not novo_id:
                    novo_id = cursor.lastrowid

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

        valor = float(registro.get('valor') or 0)
        subtotal = valor - desconto + multa + juros

        if subtotal < 0:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'O subtotal não pode ser negativo.'
            }), 400

        cursor.execute(f"""
            UPDATE {TABELA} SET
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
            data_pagamento,
            forma_pagamento,
            desconto,
            multa,
            juros,
            subtotal,
            observacoes,
            usuario_id,
            registro_id
        ))

        conexao.commit()



        qtd_parcelas = int(registro.get('qtd_parcelas') or 1)
        frequencia_id = registro.get('frequencia')

        if qtd_parcelas <= 1 and frequencia_id:
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
                    data_vencimento,
                    data_pagamento,
                    status,
                    fornecedor,
                    forma_pagamento,
                    plano_conta,
                    centro_custo,
                    frequencia,
                    qtd_parcelas,
                    observacoes,
                    usuario_lancamento,
                    usuario_pagamento,
                    ativo,
                    referencia,
                    hora,
                    hora_lembrete,
                    alertado
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL, 'Pendente', %s, NULL, %s, %s, %s, 1, %s, %s, NULL, 'Sim', 'Conta', curTime(), %s, 'Não')
            """, (
                registro.get('descricao'),
                registro.get('valor') or 0,
                registro.get('desconto') or 0,
                registro.get('multa') or 0,
                registro.get('juros') or 0,
                registro.get('subtotal') or 0,
                nova_data_lancamento,
                nova_data_vencimento,
                registro.get('fornecedor'),
                registro.get('plano_conta'),
                registro.get('centro_custo'),
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

        cursor.close()
        conexao.close()

        return jsonify({
            'status': 'sucesso',
            'mensagem': 'Conta baixada com sucesso.'
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
                    fornecedor,
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
                registro.get('fornecedor'),
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
def relatorio_despesas():
    conexao = None
    cursor = None

    try:
        data_inicial = request.form.get('data_inicial', '').strip()
        data_final = request.form.get('data_final', '').strip()
        status = request.form.get('status', '').strip()
        fornecedor = request.form.get('fornecedor', '').strip()
        centro_custo = request.form.get('centro_custo', '').strip()
        plano_conta = request.form.get('plano_conta', '').strip()

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        query = """
            SELECT
                d.*,
                f.nome AS fornecedor_nome,
                pc.nome AS plano_conta_nome,
                cc.nome AS centro_custo_nome,
                fp.nome AS forma_pagamento_nome,
                fr.nome AS frequencia_nome
            FROM despesas d
            LEFT JOIN fornecedores f ON f.id = d.fornecedor
            LEFT JOIN plano_contas pc ON pc.id = d.plano_conta
            LEFT JOIN centros_custo cc ON cc.id = d.centro_custo
            LEFT JOIN formas_pagamento fp ON fp.id = d.forma_pagamento
            LEFT JOIN frequencias fr ON fr.id = d.frequencia
            WHERE 1=1
        """
        valores = []

        if data_inicial:
            query += " AND d.data_vencimento >= %s"
            valores.append(data_inicial)

        if data_final:
            query += " AND d.data_vencimento <= %s"
            valores.append(data_final)

        if fornecedor:
            query += " AND d.fornecedor = %s"
            valores.append(fornecedor)

        if centro_custo:
            query += " AND d.centro_custo = %s"
            valores.append(centro_custo)

        if plano_conta:
            query += " AND d.plano_conta = %s"
            valores.append(plano_conta)

        query += " ORDER BY d.data_vencimento ASC, d.id DESC"

        cursor.execute(query, tuple(valores))
        lista_despesas = cursor.fetchall()

        total_geral = 0
        total_pago = 0
        total_pendente = 0
        total_atrasado = 0

        for item in lista_despesas:
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
            lista_despesas = [item for item in lista_despesas if item.get('status') == status]

        fornecedor_nome_filtro = 'Todos'
        if fornecedor:
            cursor.execute(
                "SELECT nome FROM fornecedores WHERE id = %s LIMIT 1",
                (fornecedor,)
            )
            fornecedor_filtro = cursor.fetchone()
            if fornecedor_filtro:
                fornecedor_nome_filtro = fornecedor_filtro.get('nome') or f'Fornecedor #{fornecedor}'
            else:
                fornecedor_nome_filtro = f'Fornecedor #{fornecedor}'

        centro_custo_nome_filtro = 'Todos'
        if centro_custo:
            cursor.execute(
                "SELECT nome FROM centros_custo WHERE id = %s LIMIT 1",
                (centro_custo,)
            )
            centro_filtro = cursor.fetchone()
            if centro_filtro:
                centro_custo_nome_filtro = centro_filtro.get('nome') or f'Centro #{centro_custo}'
            else:
                centro_custo_nome_filtro = f'Centro #{centro_custo}'

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

        query_centros = """
            SELECT
                COALESCE(cc.nome, 'Não informado') AS nome,
                COUNT(d.id) AS quantidade,
                SUM(d.subtotal) AS total
            FROM despesas d
            LEFT JOIN centros_custo cc ON cc.id = d.centro_custo
            WHERE 1=1
        """
        valores_centros = []

        if data_inicial:
            query_centros += " AND d.data_vencimento >= %s"
            valores_centros.append(data_inicial)

        if data_final:
            query_centros += " AND d.data_vencimento <= %s"
            valores_centros.append(data_final)

        if fornecedor:
            query_centros += " AND d.fornecedor = %s"
            valores_centros.append(fornecedor)

        if centro_custo:
            query_centros += " AND d.centro_custo = %s"
            valores_centros.append(centro_custo)

        if plano_conta:
            query_centros += " AND d.plano_conta = %s"
            valores_centros.append(plano_conta)

        query_centros += " GROUP BY cc.nome ORDER BY total DESC"
        cursor.execute(query_centros, tuple(valores_centros))
        resumo_centros = cursor.fetchall()

        query_planos = """
            SELECT
                COALESCE(pc.nome, 'Não informado') AS nome,
                COUNT(d.id) AS quantidade,
                SUM(d.subtotal) AS total
            FROM despesas d
            LEFT JOIN plano_contas pc ON pc.id = d.plano_conta
            WHERE 1=1
        """
        valores_planos = []

        if data_inicial:
            query_planos += " AND d.data_vencimento >= %s"
            valores_planos.append(data_inicial)

        if data_final:
            query_planos += " AND d.data_vencimento <= %s"
            valores_planos.append(data_final)

        if fornecedor:
            query_planos += " AND d.fornecedor = %s"
            valores_planos.append(fornecedor)

        if centro_custo:
            query_planos += " AND d.centro_custo = %s"
            valores_planos.append(centro_custo)

        if plano_conta:
            query_planos += " AND d.plano_conta = %s"
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
            'relatorios/despesas.html',
            dados=lista_despesas,
            data_inicial=data_inicial,
            data_final=data_final,
            data_inicial_label=data_inicial_label,
            data_final_label=data_final_label,
            status_filtro=status_filtro,
            fornecedor_nome_filtro=fornecedor_nome_filtro,
            centro_custo_nome_filtro=centro_custo_nome_filtro,
            plano_conta_nome_filtro=plano_conta_nome_filtro,
            total_geral=total_geral,
            total_pago=total_pago,
            total_pendente=total_pendente,
            total_atrasado=total_atrasado,
            resumo_centros=resumo_centros,
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
            headers={'Content-Disposition': 'inline; filename=relatorio_despesas.pdf'}
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