from flask import Blueprint, render_template, session, jsonify, request
from app.utils.auth import login_required, permissao_menu_required, acao_required, tem_acao
from app.database.conexao import conectar
from app.utils.logs import registrar_log

MODULO = 'fornecedores'
TABELA = 'fornecedores'
TEMPLATE = 'painel/fornecedores.html'
CHAVE_PERMISSAO = 'fornecedores'

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
        SELECT *
        FROM {TABELA}
        ORDER BY id DESC
    """)
    lista = cursor.fetchall()

    cursor.close()
    conexao.close()

    return jsonify(lista)


@pagina.route(f'/{MODULO}/salvar', methods=['POST'])
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def salvar():
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    try:
        registro_id = request.form.get('id', '').strip()
        nome = request.form.get('nome', '').strip()
        telefone = request.form.get('telefone', '').strip()
        email = request.form.get('email', '').strip().lower()
        cpf_cnpj = request.form.get('cpf_cnpj', '').strip()
        cep = request.form.get('cep', '').strip()
        endereco = request.form.get('endereco', '').strip()
        numero = request.form.get('numero', '').strip()
        complemento = request.form.get('complemento', '').strip()
        bairro = request.form.get('bairro', '').strip()
        cidade = request.form.get('cidade', '').strip()
        estado = request.form.get('estado', '').strip()

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

        if not nome:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Informe o nome.'
            }), 400

        if editando:
            cursor.execute(
                f"SELECT id FROM {TABELA} WHERE nome = %s AND id != %s",
                (nome, registro_id)
            )
        else:
            cursor.execute(
                f"SELECT id FROM {TABELA} WHERE nome = %s",
                (nome,)
            )

        nome_existente = cursor.fetchone()
        if nome_existente:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': 'Este nome já está cadastrado.'
            }), 400

        if email:
            if editando:
                cursor.execute(
                    f"SELECT id FROM {TABELA} WHERE email = %s AND id != %s",
                    (email, registro_id)
                )
            else:
                cursor.execute(
                    f"SELECT id FROM {TABELA} WHERE email = %s",
                    (email,)
                )

            email_existente = cursor.fetchone()
            if email_existente:
                cursor.close()
                conexao.close()
                return jsonify({
                    'status': 'erro',
                    'mensagem': 'Este e-mail já está cadastrado.'
                }), 400

        if cpf_cnpj:
            if editando:
                cursor.execute(
                    f"SELECT id FROM {TABELA} WHERE cpf_cnpj = %s AND id != %s",
                    (cpf_cnpj, registro_id)
                )
            else:
                cursor.execute(
                    f"SELECT id FROM {TABELA} WHERE cpf_cnpj = %s",
                    (cpf_cnpj,)
                )

            documento_existente = cursor.fetchone()
            if documento_existente:
                cursor.close()
                conexao.close()
                return jsonify({
                    'status': 'erro',
                    'mensagem': 'Este CPF / CNPJ já está cadastrado.'
                }), 400

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

            cursor.execute(f"""
                UPDATE {TABELA} SET
                    nome = %s,
                    telefone = %s,
                    email = %s,
                    cpf_cnpj = %s,
                    cep = %s,
                    endereco = %s,
                    numero = %s,
                    complemento = %s,
                    bairro = %s,
                    cidade = %s,
                    estado = %s
                WHERE id = %s
            """, (
                nome, telefone, email, cpf_cnpj, cep, endereco,
                numero, complemento, bairro, cidade, estado, registro_id
            ))
            conexao.commit()

            cursor.close()
            conexao.close()

            registrar_log(
                acao='editar',
                entidade=TABELA,
                registro_id=registro_id,
                descricao=f"registro editado em {TABELA}: {nome}"
            )

            return jsonify({
                'status': 'sucesso',
                'mensagem': 'Registro atualizado com sucesso.',
                'acao': 'update',
                'id': registro_id
            })

        else:
            cursor.execute(f"""
                INSERT INTO {TABELA} (
                    nome, telefone, email, cpf_cnpj, cep, endereco,
                    numero, complemento, bairro, cidade, estado, ativo
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Sim')
            """, (
                nome, telefone, email, cpf_cnpj, cep, endereco,
                numero, complemento, bairro, cidade, estado
            ))

            novo_id = cursor.lastrowid
            conexao.commit()

            cursor.close()
            conexao.close()

            registrar_log(
                acao='inserir',
                entidade=TABELA,
                registro_id=novo_id,
                descricao=f"novo cadastro em {TABELA}: {nome}"
            )

            return jsonify({
                'status': 'sucesso',
                'mensagem': 'Registro cadastrado com sucesso.',
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
            f"SELECT id, nome FROM {TABELA} WHERE id = %s",
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
            descricao=f"registro excluido em {TABELA}: {registro['nome']}"
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
            f"SELECT id, nome FROM {TABELA} WHERE id IN ({placeholders})",
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
                descricao=f"registro excluido em {TABELA}: {registro['nome']}"
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

    cursor.execute(f"""
        SELECT id, nome
        FROM {TABELA}
        WHERE ativo = 'Sim'
        ORDER BY nome ASC
    """)
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