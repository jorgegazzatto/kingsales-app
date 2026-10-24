from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
from app.utils.auth import login_required, tem_acao
from app.database.conexao import conectar
from app.utils.logs import registrar_log
import os
import uuid

MODULO = 'arquivos'
TABELA = 'arquivos'

pagina = Blueprint(MODULO, __name__)


@pagina.route(f'/{MODULO}/salvar', methods=['POST'])
@login_required
def salvar():
    conexao = None
    cursor = None

    try:
        usuario_id = session.get('usuario_id')

        if not tem_acao(usuario_id, 'editar'):
            return jsonify({
                'status': 'erro',
                'mensagem': 'Você não tem permissão para enviar arquivos.'
            }), 403

        
        tabela = request.form.get('tabela', '').strip()
        tipo = request.form.get('tipo', '').strip()
        descricao = request.form.get('descricao', '').strip()
        arquivo = request.files.get('arquivo')
        id_registro = request.form.get('id_registro', '').strip()

        if not id_registro:
            return jsonify({
                'status': 'erro',
                'mensagem': 'ID de referência não informado.'
            }), 400

        if not tabela:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Tabela não informada.'
            }), 400

        if not tipo:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Tipo do arquivo não informado.'
            }), 400

        if not arquivo or not arquivo.filename:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Selecione um arquivo.'
            }), 400

        tabelas_permitidas = ['despesas', 'receitas']
        if tabela not in tabelas_permitidas:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Tabela inválida.'
            }), 400

        tipos_permitidos = ['despesa', 'receita']
        if tipo not in tipos_permitidos:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Tipo inválido.'
            }), 400

        extensoes_permitidas = {
            '.pdf', '.jpg', '.jpeg', '.png', '.webp', '.gif',
            '.doc', '.docx', '.xls', '.xlsx', '.csv',
            '.xml', '.txt', '.zip', '.rar', '.7z'
        }

        nome_original = secure_filename(arquivo.filename)
        extensao = os.path.splitext(nome_original)[1].lower()

        if extensao not in extensoes_permitidas:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Formato de arquivo não permitido.'
            }), 400

        nome_arquivo = f"{uuid.uuid4().hex}{extensao}"

        pasta_destino = os.path.join(current_app.root_path, 'static', 'img', 'arquivos')
        os.makedirs(pasta_destino, exist_ok=True)

        caminho_arquivo = os.path.join(pasta_destino, nome_arquivo)
        arquivo.save(caminho_arquivo)

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute(f"""
            INSERT INTO {TABELA} (
                descricao,
                arquivo,
                tipo,
                tabela,
                id_registro,
                usuario,
                data,
                hora,
                ativo
            ) VALUES (%s, %s, %s, %s, %s, %s, curDate(), curTime(), 'Sim')
        """, (
            descricao,
            nome_arquivo,
            tipo,
            tabela,
            id_registro,
            usuario_id
        ))

        novo_id = cursor.lastrowid
        conexao.commit()

        registrar_log(
            acao='inserir',
            entidade=TABELA,
            registro_id=novo_id,
            descricao=f"novo arquivo enviado para {tabela}, ref {id_registro}"
        )

        return jsonify({
            'status': 'sucesso',
            'mensagem': 'Arquivo enviado com sucesso.',
            'id': novo_id,
            'arquivo': nome_arquivo
        })

    except Exception as e:
        if conexao:
            conexao.rollback()

        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro interno ao salvar arquivo.',
            'erro': str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()





@pagina.route(f'/{MODULO}/listar')
@login_required
def listar():
    conexao = None
    cursor = None

    try:
        id_registro = request.args.get('id_registro', '').strip()
        tabela = request.args.get('tabela', '').strip()
        tipo = request.args.get('tipo', '').strip()

        if not id_registro:
            return jsonify({
                'status': 'erro',
                'mensagem': 'ID do registro não informado.'
            }), 400

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        query = f"""
            SELECT *
            FROM {TABELA}
            WHERE id_registro = %s
              AND tabela = %s
              AND tipo = %s
              AND ativo = 'Sim'
            ORDER BY id DESC
        """

        cursor.execute(query, (id_registro, tabela, tipo))
        lista = cursor.fetchall()

        # 🔥 converter campos problemáticos
        for item in lista:
            for chave, valor in item.items():
                if hasattr(valor, 'isoformat'):
                    item[chave] = valor.isoformat()
                elif str(type(valor)) == "<class 'datetime.timedelta'>":
                    item[chave] = str(valor)

        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

        return jsonify(lista)

    except Exception as e:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao listar arquivos.',
            'erro': str(e)
        }), 500
    





@pagina.route(f'/{MODULO}/excluir', methods=['POST'])
@login_required
def excluir():
    conexao = None
    cursor = None

    try:
        usuario_id = session.get('usuario_id')

        if not tem_acao(usuario_id, 'editar'):
            return jsonify({
                'status': 'erro',
                'mensagem': 'Você não tem permissão para excluir arquivos.'
            }), 403

        dados = request.get_json(silent=True) or {}
        registro_id = str(dados.get('id', '')).strip()

        if not registro_id:
            return jsonify({
                'status': 'erro',
                'mensagem': 'ID do arquivo não informado.'
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
                'mensagem': 'Arquivo não encontrado.'
            }), 404

        nome_arquivo = registro.get('arquivo') or ''
        caminho_arquivo = os.path.join(current_app.root_path, 'static', 'img', 'arquivos', nome_arquivo)

        if nome_arquivo and os.path.exists(caminho_arquivo) and os.path.isfile(caminho_arquivo):
            os.remove(caminho_arquivo)

        cursor.execute(
            f"DELETE FROM {TABELA} WHERE id = %s",
            (registro_id,)
        )
        conexao.commit()

        registrar_log(
            acao='excluir',
            entidade=TABELA,
            registro_id=registro_id,
            descricao=f"arquivo excluído: {nome_arquivo}"
        )

        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

        return jsonify({
            'status': 'sucesso',
            'mensagem': 'Arquivo excluído com sucesso.'
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
            'mensagem': 'Erro ao excluir arquivo.',
            'erro': str(e)
        }), 500