from flask import Blueprint, render_template, session, jsonify, request
from app.utils.auth import login_required, permissao_menu_required, acao_required
from app.database.conexao import conectar
from app.utils.uploads import salvar_arquivo, excluir_arquivo
from app.utils.logs import registrar_log
import os

MODULO = 'categorias'
TABELA = 'categorias'
TEMPLATE = 'painel/categorias.html'
CHAVE_PERMISSAO = 'categorias'
PASTA_UPLOAD = os.path.join('app', 'static', 'img', 'categorias')
NOME_PASTA = 'categorias'

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
        SELECT id, nome, foto, posicao, descricao, ativo, data_cadastro, usuario_cadastro
        FROM {TABELA}
        ORDER BY posicao ASC, id DESC
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
        posicao = request.form.get('posicao') or 0
        descricao = request.form.get('descricao')

        usuario_cadastro = session.get('usuario_id')

        foto = request.files.get('foto')
        nome_foto = None

        if not nome or not nome.strip():
            return jsonify({
                'status': 'erro',
                'mensagem': 'O nome é obrigatório.'
            })

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
                    nome, foto, posicao, descricao, ativo, data_cadastro, usuario_cadastro
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                nome, nome_foto, posicao, descricao, ativo, data_cadastro, usuario_cadastro
            ))

            conexao.commit()

            return jsonify({
                'status': 'sucesso',
                'mensagem': 'Categoria cadastrada com sucesso'
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
                    foto=%s,
                    posicao=%s,
                    descricao=%s
                WHERE id=%s
            """, (
                nome, nome_foto, posicao, descricao, id
            ))

            conexao.commit()

            return jsonify({
                'status': 'sucesso',
                'mensagem': 'Categoria atualizada com sucesso'
            })

    except Exception as e:
        conexao.rollback()
        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao salvar categoria',
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

        mensagem = 'Categoria ativada com sucesso.' if ativo == 'Sim' else 'Categoria desativada com sucesso.'

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

        return jsonify({'status': 'sucesso', 'mensagem': 'Categoria excluída com sucesso.'})

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
            'mensagem': f'{len(registros_encontrados)} categoria(s) excluída(s) com sucesso.'
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