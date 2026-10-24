from flask import Blueprint, render_template, session, jsonify, request, url_for
from app.utils.auth import login_required, permissao_menu_required, acao_required, tem_acao
from app.database.conexao import conectar
from app.utils.uploads import salvar_arquivo, excluir_arquivo
from app.utils.logs import registrar_log
import os
from datetime import date

MODULO = 'clientes'
TABELA = 'clientes'
TEMPLATE = 'painel/clientes.html'
CHAVE_PERMISSAO = 'clientes'
PASTA_UPLOAD = os.path.join('app', 'static', 'img', 'clientes')
NOME_PASTA = 'clientes'

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
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute(f"""
        SELECT id, nome, email, telefone, whatsapp, tipo_pessoa, cpf_cnpj,
               data_nascimento, profissao, cep, endereco, numero, complemento,
               bairro, cidade, estado, foto, ativo, observacoes,
               limite_credito, saldo_devedor, dia_vencimento_padrao,
               forma_pagamento_padrao, score_credito
        FROM {TABELA}
        ORDER BY id DESC
    """)
    lista = cursor.fetchall()

    cursor.close()
    conexao.close()

    return jsonify(lista)





from datetime import datetime

@pagina.route(f'/{MODULO}/salvar', methods=['POST'])
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def salvar():
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    try:
        id = request.form.get('id')

        nome = request.form.get('nome')
        email = request.form.get('email')
        telefone = request.form.get('telefone')
        whatsapp = request.form.get('whatsapp')

        tipo_pessoa = request.form.get('tipo_pessoa')
        cpf_cnpj = request.form.get('cpf_cnpj')

        data_nascimento = request.form.get('data_nascimento', '').strip()

        if data_nascimento:
            try:
                data_nascimento = datetime.strptime(data_nascimento, '%d/%m/%Y').strftime('%Y-%m-%d')
            except:
                data_nascimento = None
        else:
            data_nascimento = None
        profissao = request.form.get('profissao')

        cep = request.form.get('cep')
        endereco = request.form.get('endereco')
        numero = request.form.get('numero')
        complemento = request.form.get('complemento')
        bairro = request.form.get('bairro')
        cidade = request.form.get('cidade')
        estado = request.form.get('estado')

        observacoes = request.form.get('observacoes')

        # FINANCEIRO (sem default no banco)
        limite_credito = request.form.get('limite_credito') or 0
        saldo_devedor = request.form.get('saldo_devedor') or 0
        dia_vencimento_padrao = request.form.get('dia_vencimento_padrao') or None
        forma_pagamento_padrao = request.form.get('forma_pagamento_padrao')
        score_credito = request.form.get('score_credito') or 0

        usuario_cadastro = session.get('usuario_id')

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
                    nome, email, telefone, whatsapp,
                    tipo_pessoa, cpf_cnpj,
                    data_nascimento, profissao,
                    cep, endereco, numero, complemento,
                    bairro, cidade, estado,
                    foto, ativo, observacoes, data_cadastro,
                    limite_credito, saldo_devedor,
                    dia_vencimento_padrao, forma_pagamento_padrao,
                    score_credito, usuario_cadastro
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                nome, email, telefone, whatsapp,
                tipo_pessoa, cpf_cnpj,
                data_nascimento, profissao,
                cep, endereco, numero, complemento,
                bairro, cidade, estado,
                nome_foto, ativo, observacoes, data_cadastro,
                limite_credito, saldo_devedor,
                dia_vencimento_padrao, forma_pagamento_padrao,
                score_credito, usuario_cadastro
            ))

            conexao.commit()

            return jsonify({
                'status': 'sucesso',
                'mensagem': 'Cliente cadastrado com sucesso'
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
                    email=%s,
                    telefone=%s,
                    whatsapp=%s,
                    tipo_pessoa=%s,
                    cpf_cnpj=%s,
                    data_nascimento=%s,
                    profissao=%s,
                    cep=%s,
                    endereco=%s,
                    numero=%s,
                    complemento=%s,
                    bairro=%s,
                    cidade=%s,
                    estado=%s,
                    foto=%s,
                    observacoes=%s,
                    limite_credito=%s,
                    saldo_devedor=%s,
                    dia_vencimento_padrao=%s,
                    forma_pagamento_padrao=%s,
                    score_credito=%s
                WHERE id=%s
            """, (
                nome, email, telefone, whatsapp,
                tipo_pessoa, cpf_cnpj,
                data_nascimento, profissao,
                cep, endereco, numero, complemento,
                bairro, cidade, estado,
                nome_foto,
                observacoes,
                limite_credito, saldo_devedor,
                dia_vencimento_padrao, forma_pagamento_padrao,
                score_credito,
                id
            ))

            conexao.commit()

            return jsonify({
                'status': 'sucesso',
                'mensagem': 'Cliente atualizado com sucesso'
            })

    except Exception as e:
        conexao.rollback()
        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao salvar cliente',
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

        mensagem = 'Cliente ativado com sucesso.' if ativo == 'Sim' else 'Cliente desativado com sucesso.'

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

        return jsonify({'status': 'sucesso', 'mensagem': 'Cliente excluído com sucesso.'})

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

        return jsonify({'status': 'sucesso', 'mensagem': 'Clientes excluídos com sucesso.'})

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

    cursor.execute(f"SELECT * FROM {TABELA} where ativo = 'Sim' ORDER BY nome ASC")
    lista = cursor.fetchall()

    cursor.close()
    conexao.close()

    return jsonify(lista)







@pagina.route(f'/{MODULO}/contas/<int:id_cliente>')
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def listar_contas_cliente(id_cliente):
    conexao = None
    cursor = None

    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                r.*,
                c.nome AS cliente_nome,
                pc.nome AS plano_conta_nome,
                fp.nome AS forma_pagamento_nome
            FROM recebimentos r
            LEFT JOIN clientes c ON r.cliente = c.id
            LEFT JOIN plano_contas pc ON r.plano_conta = pc.id
            LEFT JOIN formas_pagamento fp ON r.forma_pagamento = fp.id
            WHERE r.cliente = %s
              AND r.ativo = 'Sim'
            ORDER BY r.data_vencimento ASC, r.id DESC
        """, (id_cliente,))

        lista = cursor.fetchall()

        for item in lista:
            if item.get('data_pagamento'):
                item['status'] = 'Pago'
            elif item.get('data_vencimento') and item['data_vencimento'] < date.today():
                item['status'] = 'Atrasado'
            else:
                item['status'] = 'Pendente'

            if item.get('data_lancamento'):
                item['data_lancamento'] = item['data_lancamento'].strftime('%Y-%m-%d')

            if item.get('data_vencimento'):
                item['data_vencimento'] = item['data_vencimento'].strftime('%Y-%m-%d')

            if item.get('data_pagamento'):
                item['data_pagamento'] = item['data_pagamento'].strftime('%Y-%m-%d')

            if item.get('hora_lancamento') is not None:
                item['hora_lancamento'] = str(item['hora_lancamento'])

            if item.get('hora') is not None:
                item['hora'] = str(item['hora'])

            if item.get('hora_lembrete') is not None:
                item['hora_lembrete'] = str(item['hora_lembrete'])

        return jsonify(lista)

    except Exception as e:
        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao listar contas do cliente.',
            'erro': str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()