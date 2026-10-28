from flask import Blueprint, render_template, session, jsonify, request, url_for
from app import bcrypt
from app.utils.auth import login_required, permissao_menu_required, acao_required, tem_acao
from app.database.conexao import conectar
from app.utils.uploads import salvar_arquivo, excluir_arquivo
import os
from app.utils.logs import registrar_log
from app.apis.whatsapp.texto import enviar_whatsapp_texto
from app.utils.config_sistema import get_config_sistema
from app.apis.email.texto import enviar_email_texto
from app.apis.ia.api_ia import gerar_texto_ia

config_sistema = get_config_sistema()

MODULO = 'usuarios'
TABELA = 'usuarios'
TEMPLATE = 'painel/usuarios.html'
CHAVE_PERMISSAO = 'usuarios'
PASTA_UPLOAD = os.path.join('app', 'static', 'img', 'usuarios')
NOME_PASTA = 'usuarios'

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

    cursor.execute(f"SELECT * FROM {TABELA} WHERE id = %s", (usuario_id,))
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
        SELECT id, nome, telefone, email, cpf, cep, endereco, numero,
               complemento, bairro, cidade, estado, nivel, foto, ativo
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
        cpf = request.form.get('cpf', '').strip()
        cep = request.form.get('cep', '').strip()
        endereco = request.form.get('endereco', '').strip()
        numero = request.form.get('numero', '').strip()
        complemento = request.form.get('complemento', '').strip()
        bairro = request.form.get('bairro', '').strip()
        cidade = request.form.get('cidade', '').strip()
        estado = request.form.get('estado', '').strip()
        nivel = request.form.get('nivel', '').strip()
        senha = request.form.get('senha', '').strip()
        confirmar_senha = request.form.get('confirmar_senha', '').strip()
        foto = request.files.get('foto')

        usuario_id = session.get('usuario_id')

        editando = bool(registro_id)

        # =========================
        # VALIDAÇÕES BÁSICAS
        # =========================
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
            return jsonify({'status': 'erro', 'mensagem': 'Informe o nome.'}), 400

        if not email:
            cursor.close()
            conexao.close()
            return jsonify({'status': 'erro', 'mensagem': 'Informe o e-mail.'}), 400

        if not nivel:
            cursor.close()
            conexao.close()
            return jsonify({'status': 'erro', 'mensagem': 'Informe o nível.'}), 400

        # Validação de email duplicado
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

        pasta_arquivo = PASTA_UPLOAD
        nome_arquivo_foto = None

        # =========================
        # EDIÇÃO
        # =========================
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

            senha_hash = registro_atual['senha']
            nome_arquivo_foto = registro_atual['foto']

            # senha opcional na edição
            if senha or confirmar_senha:
                if senha != confirmar_senha:
                    cursor.close()
                    conexao.close()
                    return jsonify({
                        'status': 'erro',
                        'mensagem': 'A confirmação de senha não confere.'
                    }), 400

                if len(senha) < 3:
                    cursor.close()
                    conexao.close()
                    return jsonify({
                        'status': 'erro',
                        'mensagem': 'A senha deve ter pelo menos 3 caracteres.'
                    }), 400

                senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')

            # upload nova foto
            if foto and foto.filename:
                resultado_upload = salvar_arquivo(
                    arquivo=foto,
                    pasta_destino=pasta_arquivo,
                    extensoes_permitidas=['.jpg', '.jpeg', '.png', '.webp'],
                    largura_maxima=500
                )

                if not resultado_upload['sucesso']:
                    cursor.close()
                    conexao.close()
                    return jsonify({
                        'status': 'erro',
                        'mensagem': resultado_upload['mensagem']
                    }), 400

                nova_foto = resultado_upload['arquivo']

                excluir_arquivo(
                    nome_arquivo=registro_atual['foto'],
                    pasta_destino=pasta_arquivo,
                    arquivos_protegidos=['sem_foto.webp', 'sem-foto.webp', 'sem_foto.png', 'sem-foto.png', 'sem_foto.jpg', 'sem-foto.jpg']
                )

                nome_arquivo_foto = nova_foto

            query = f"""
                UPDATE {TABELA} SET
                    nome = %s,
                    telefone = %s,
                    email = %s,
                    cpf = %s,
                    cep = %s,
                    endereco = %s,
                    numero = %s,
                    complemento = %s,
                    bairro = %s,
                    cidade = %s,
                    estado = %s,
                    nivel = %s,
                    senha = %s,
                    foto = %s
                WHERE id = %s
            """

            valores = (
                nome, telefone, email, cpf, cep, endereco, numero,
                complemento, bairro, cidade, estado, nivel,
                senha_hash, nome_arquivo_foto, registro_id
            )

            cursor.execute(query, valores)
            conexao.commit()


            # LANÇAR EDITAR LOGS 
            registrar_log(
                acao='editar',
                entidade=TABELA,
                registro_id=registro_id,
                descricao=f"regitro editado em {TABELA}: {nome}"
            )

            foto_url = url_for(
                'static',
                filename=f'img/{NOME_PASTA}/{nome_arquivo_foto}'
            ) if nome_arquivo_foto else url_for('static', filename='img/sem-foto.webp')

            cursor.close()
            conexao.close()

            return jsonify({
                'status': 'sucesso',
                'mensagem': 'Registro atualizado com sucesso.',
                'acao': 'update',
                'id': registro_id,
                'foto_url': foto_url
            })

        # =========================
        # CADASTRO
        # =========================
        else:
            if not senha:
                cursor.close()
                conexao.close()
                return jsonify({
                    'status': 'erro',
                    'mensagem': 'Informe a senha no cadastro.'
                }), 400

            if senha != confirmar_senha:
                cursor.close()
                conexao.close()
                return jsonify({
                    'status': 'erro',
                    'mensagem': 'A confirmação de senha não confere.'
                }), 400

            if len(senha) < 3:
                cursor.close()
                conexao.close()
                return jsonify({
                    'status': 'erro',
                    'mensagem': 'A senha deve ter pelo menos 3 caracteres.'
                }), 400

            senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')

            if foto and foto.filename:
                resultado_upload = salvar_arquivo(
                    arquivo=foto,
                    pasta_destino=pasta_arquivo,
                    extensoes_permitidas=['.jpg', '.jpeg', '.png', '.webp'],
                    largura_maxima=500
                )

                if not resultado_upload['sucesso']:
                    cursor.close()
                    conexao.close()
                    return jsonify({
                        'status': 'erro',
                        'mensagem': resultado_upload['mensagem']
                    }), 400

                nome_arquivo_foto = resultado_upload['arquivo']

            cursor.execute(f"""
                INSERT INTO {TABELA} (
                    nome, telefone, email, cpf, cep, endereco, numero,
                    complemento, bairro, cidade, estado, nivel, senha, foto, ativo
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                nome, telefone, email, cpf, cep, endereco, numero,
                complemento, bairro, cidade, estado, nivel,
                senha_hash, nome_arquivo_foto, 'Sim'
            ))

            novo_id = cursor.lastrowid
            conexao.commit()

           
            # LANÇAR inserir LOGS 
            registrar_log(
                acao='inserir',
                entidade=TABELA,
                registro_id=novo_id,
                descricao=f"novo cadastro em {TABELA}: {nome}"
            )


            #CHAMAR A API DO WHATSAPP
            url_sistema = request.host_url.rstrip('/')
            mensagem_padrao = f"""Olá *{nome}*, tudo bem? 😊

Seu cadastro foi realizado com sucesso em nosso sistema! ✅

🔐 *Dados de acesso:*
📧 *Email:* {email}
🔑 *Senha:* {senha}

🌐 *Acesse o sistema pelo link abaixo:*
{url_sistema}

⚠️ *Importante:*
Por segurança, recomendamos que você altere sua senha após o primeiro acesso.

Se precisar de ajuda, estamos à disposição! 🤝
"""

            prompt_ia = f"""
Gere uma mensagem de boas-vindas para WhatsApp, em português do Brasil, com tom profissional, amigável e organizado.

Dados do usuário:
- Nome: {nome}
- Email: {email}
- Senha: {senha}
- Link do sistema: {url_sistema}

Regras:
- A mensagem deve ser pronta para envio no WhatsApp
- Use negrito com *asteriscos*
- Use alguns emojis, sem exagero
- Informe que o cadastro foi realizado com sucesso
- Informe email e senha de acesso
- Oriente o usuário a alterar a senha após o primeiro acesso
- Não invente informações
- Não coloque explicações fora da mensagem
"""
            
            mensagem_ia = gerar_texto_ia(prompt_ia)
            mensagem = mensagem_ia if mensagem_ia else mensagem_padrao

            enviar_whatsapp_texto(telefone, mensagem)


            #CHAMAR API DISPARO EMAIL
            logo_url = f"{url_sistema}/static/img/{config_sistema.get('logo')}"
            assunto = 'Cadastro realizado com sucesso'
            mensagem_html = f"""
            <div style="font-family: Arial, sans-serif;">

                <div style="text-align:center; margin-bottom:20px;">
                    <img src="{logo_url}" alt="Logo" style="max-width:200px;">
                </div>

                <p>Olá <strong>{nome}</strong>, tudo bem?</p>

                <p>Seu cadastro foi realizado com sucesso em nosso sistema.</p>

                <p><strong>Dados de acesso:</strong><br>
                Email: {email}<br>
                Senha: {senha}</p>

                <p>Acesse o sistema pelo link abaixo:<br>
                <a href="{url_sistema}">{url_sistema}</a></p>

                <p>Recomendamos que você altere sua senha após o primeiro acesso.</p>

            </div>
            """
            mensagem_texto = f"""Olá {nome}, tudo bem?

            Seu cadastro foi realizado com sucesso em nosso sistema.

            Dados de acesso:
            Email: {email}
            Senha: {senha}

            Acesse o sistema:
            {url_sistema}

            Recomendamos que você altere sua senha após o primeiro acesso.
            """

            enviar_email_texto(email, assunto, mensagem_html, mensagem_texto)




            foto_url = url_for(
                'static',
                filename=f'img/{NOME_PASTA}/{nome_arquivo_foto}'
            ) if nome_arquivo_foto else url_for('static', filename='img/sem-foto.webp')

            cursor.close()
            conexao.close()

            return jsonify({
                'status': 'sucesso',
                'mensagem': 'Registro cadastrado com sucesso.',
                'acao': 'insert',
                'id': novo_id,
                'foto_url': foto_url
            })

    except Exception as e:
        conexao.rollback()
        cursor.close()
        conexao.close()

        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro interno ao salvar registro.' + str(e),
            'erro': str(e)
        }), 500



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

        # LANÇAR editar LOGS 
        registrar_log(
            acao='editar',
            entidade=TABELA,
            registro_id=registro_id,
            descricao=f"status alterado em {TABELA}: {registro['nome']}"
        )

        mensagem = 'Usuário ativado com sucesso.' if ativo == 'Sim' else 'Usuário desativado com sucesso.'

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
            f"SELECT id, nome, foto FROM {TABELA} WHERE id = %s",
            (registro_id,)
        )
        registro = cursor.fetchone()

        if not registro:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Registro não encontrado.'
            }), 404

        usuario_logado_id = str(session.get('usuario_id', '')).strip()
        if usuario_logado_id == registro_id:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Você não pode excluir seu próprio usuário.'
            }), 400
        

        cursor.execute("DELETE FROM usuarios_permissoes WHERE usuario_id = %s", (registro_id,))
        cursor.execute("DELETE FROM usuarios_acoes WHERE usuario_id = %s", (registro_id,))

        cursor.execute(f"DELETE FROM {TABELA} WHERE id = %s", (registro_id,))
        conexao.commit()

        # LANÇAR excluir LOGS 
        registrar_log(
            acao='excluir',
            entidade=TABELA,
            registro_id=registro_id,
            descricao=f"registro excluido em {TABELA}: {registro['nome']}"
        )

        excluir_arquivo(
            nome_arquivo=registro.get('foto'),
            pasta_destino=PASTA_UPLOAD,
            arquivos_protegidos=['sem_foto.webp', 'sem-foto.webp', 'sem_foto.png', 'sem-foto.png', 'sem_foto.jpg', 'sem-foto.jpg']
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

        usuario_logado_id = str(session.get('usuario_id', '')).strip()

        if usuario_logado_id in ids_validos:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Você não pode excluir seu próprio usuário em lote.'
            }), 400

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        placeholders = ','.join(['%s'] * len(ids_validos))

        cursor.execute(
            f"SELECT id, nome, foto FROM {TABELA} WHERE id IN ({placeholders})",
            tuple(ids_validos)
        )
        registros_encontrados = cursor.fetchall()

        if not registros_encontrados:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Nenhum registro encontrado.'
            }), 404
        

        cursor.execute(
            f"DELETE FROM usuarios_permissoes WHERE usuario_id IN ({placeholders})",
            tuple(ids_validos)
        )
       

        cursor.execute(
            f"DELETE FROM usuarios_acoes WHERE usuario_id IN ({placeholders})",
            tuple(ids_validos)
        )
       

        cursor.execute(
            f"DELETE FROM {TABELA} WHERE id IN ({placeholders})",
            tuple(ids_validos)
        )
        conexao.commit()


        for registro in registros_encontrados:
            # LANÇAR excluir LOGS 
            registrar_log(
                acao='excluir',
                entidade=TABELA,
                registro_id=registro['id'],
                descricao=f"registro excluido em {TABELA}: {registro['nome']}"
            )

        for usuario in registros_encontrados:
            excluir_arquivo(
                nome_arquivo=usuario.get('foto'),
                pasta_destino=PASTA_UPLOAD,
                arquivos_protegidos=[
                    'sem_foto.webp', 'sem-foto.webp',
                    'sem_foto.png', 'sem-foto.png',
                    'sem_foto.jpg', 'sem-foto.jpg'
                ]
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



@pagina.route(f'/{MODULO}/permissoes/<int:usuario_id>', methods=['GET'])
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
def buscar_permissoes(usuario_id):
    conexao = None
    cursor = None

    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT menu_id
            FROM usuarios_permissoes
            WHERE usuario_id = %s
        """, (usuario_id,))
        permissoes_menu = cursor.fetchall()

        cursor.execute("""
            SELECT acao
            FROM usuarios_acoes
            WHERE usuario_id = %s
        """, (usuario_id,))
        permissoes_acoes = cursor.fetchall()

        return jsonify({
            'status': 'sucesso',
            'menus': [item['menu_id'] for item in permissoes_menu],
            'acoes': [item['acao'] for item in permissoes_acoes]
        })

    except Exception as e:
        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao buscar permissões.',
            'erro': str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()




@pagina.route(f'/{MODULO}/permissoes/salvar', methods=['POST'])
@login_required
@permissao_menu_required(CHAVE_PERMISSAO)
@acao_required('editar')
def salvar_permissoes():
    conexao = None
    cursor = None

    try:
        dados = request.get_json(silent=True) or {}

        usuario_id = str(dados.get('usuario_id', '')).strip()
        menus = dados.get('menus', [])
        acoes = dados.get('acoes', [])

        

        if not usuario_id:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Usuário não informado.'
            }), 400

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        # busca o usuário para usar no log
        cursor.execute("SELECT id, nome FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        # limpa permissões antigas
        cursor.execute("DELETE FROM usuarios_permissoes WHERE usuario_id = %s", (usuario_id,))
        cursor.execute("DELETE FROM usuarios_acoes WHERE usuario_id = %s", (usuario_id,))

        # salva menus
        for menu_id in menus:
            menu_id = str(menu_id).strip()

            if not menu_id:
                continue

            cursor.execute("""
                INSERT INTO usuarios_permissoes (usuario_id, menu_id)
                VALUES (%s, %s)
            """, (usuario_id, menu_id))

        # salva ações
        for acao in acoes:
            acao = str(acao).strip().lower()

            if not acao:
                continue

            cursor.execute("""
                INSERT INTO usuarios_acoes (usuario_id, acao)
                VALUES (%s, %s)
            """, (usuario_id, acao))

        conexao.commit()

        registrar_log(
            acao='editar',
            entidade='usuarios_permissoes',
            registro_id=usuario_id,
            descricao=(
                f"Permissões alteradas do usuário {usuario['nome']}. "
                f"Menus: {', '.join(menus) if menus else 'nenhum'}. "
                f"Ações: {', '.join(acoes) if acoes else 'nenhuma'}."
            )
        )
        

        return jsonify({
            'status': 'sucesso',
            'mensagem': 'Permissões salvas com sucesso.'
        })

    except Exception as e:
        if conexao:
            conexao.rollback()

        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao salvar permissões.',
            'erro': str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()