from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, Response
from app import bcrypt
from app.utils.auth import login_required, permissao_menu_required, buscar_menus_permitidos
from app.utils.menu import MENU_SISTEMA, buscar_primeira_rota_permitida
painel = Blueprint('painel', __name__)
from config import MODO_TESTE, EMAIL_SISTEMA, SENHA_PADRAO, NOME_SISTEMA, COR_PRIMARIA, COR_SECUNDARIA
from app.database.conexao import conectar
from app.utils.uploads import salvar_arquivo, excluir_arquivo
import os
from app.utils.logs import registrar_log
from app.apis.whatsapp.teste import testar_whatsapp
from app.utils.criptografia import criptografar_texto
from app.apis.email.teste import testar_email_smtp
from app.apis.ia.api_teste import testar_ia
import base64
import uuid
from app.utils.funcoes import valor_para_numero
from datetime import date, datetime, timedelta
from app.utils.config_sistema import get_config_sistema
from io import BytesIO
from xhtml2pdf import pisa
import mimetypes
import traceback

@painel.route('/painel')
@login_required
def index():
    usuario_id = session.get('usuario_id')
    usuario_nivel = session.get('usuario_nivel')

    if usuario_nivel == 'Administrador':
        return redirect(url_for('painel.dashboard'))

    menus_permitidos = buscar_menus_permitidos(usuario_id)

    if 'dashboard' in menus_permitidos:
        return redirect(url_for('painel.dashboard'))

    primeira_rota = buscar_primeira_rota_permitida(MENU_SISTEMA, menus_permitidos)

    if primeira_rota:
        return redirect(url_for(primeira_rota))

    session.clear()
    flash('Seu usuário não possui páginas liberadas para acesso.', 'danger')
    return redirect(url_for('main.index'))







@painel.route('/painel/dashboard')
@login_required
@permissao_menu_required('dashboard')
def dashboard():
    usuario_id = session.get('usuario_id')

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
    usuario = cursor.fetchone()

    nome = session.get('usuario_nome')
    nivel = session.get('usuario_nivel')
    foto_usuario = session.get('usuario_foto')

    hoje = date.today()
    primeiro_dia_mes = hoje.replace(day=1)

    # =========================
    # RECEBIDO NO MÊS
    # =========================
    cursor.execute("""
        SELECT COALESCE(SUM(subtotal), 0) AS total
        FROM recebimentos
        WHERE data_pagamento IS NOT NULL
        AND data_pagamento BETWEEN %s AND %s
        AND ativo = 'Sim'
    """, (primeiro_dia_mes, hoje))
    total_recebido = float(cursor.fetchone()['total'] or 0)

    # =========================
    # A RECEBER / PENDENTES
    # =========================
    cursor.execute("""
        SELECT COALESCE(SUM(subtotal), 0) AS total
        FROM recebimentos
        WHERE data_pagamento IS NULL
        AND data_vencimento >= %s
        AND ativo = 'Sim'
    """, (hoje,))
    total_a_receber = float(cursor.fetchone()['total'] or 0)

    # =========================
    # ATRASADAS
    # =========================
    cursor.execute("""
        SELECT COALESCE(SUM(subtotal), 0) AS total
        FROM recebimentos
        WHERE data_pagamento IS NULL
        AND data_vencimento < %s
        AND ativo = 'Sim'
    """, (hoje,))
    total_atrasadas = float(cursor.fetchone()['total'] or 0)

    # =========================
    # EM ABERTO
    # =========================
    total_em_aberto = total_a_receber + total_atrasadas

    # =========================
    # FATURAMENTO DO MÊS
    # Vendas + recebimentos pagos no mês
    # =========================
    cursor.execute("""
        SELECT COALESCE(SUM(subtotal), 0) AS total
        FROM vendas
        WHERE data_lancamento BETWEEN %s AND %s
        AND ativo = 'Sim'
    """, (primeiro_dia_mes, hoje))
    total_vendas_mes = float(cursor.fetchone()['total'] or 0)

    faturamento_mes = total_recebido + total_vendas_mes

    # =========================
    # CLIENTES
    # =========================
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM clientes
        WHERE ativo = 'Sim'
    """)
    total_clientes = int(cursor.fetchone()['total'] or 0)

    # =========================
    # QUANTIDADE DE VENDAS NO MÊS
    # =========================
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM vendas
        WHERE data_lancamento BETWEEN %s AND %s
        AND ativo = 'Sim'
    """, (primeiro_dia_mes, hoje))
    total_vendas = int(cursor.fetchone()['total'] or 0)

    # =========================
    # ESTOQUE BAIXO
    # =========================
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM produtos
        WHERE controlar_estoque = 'Sim'
        AND ativo = 'Sim'
        AND estoque <= nivel_minimo_estoque
    """)
    total_estoque_baixo = int(cursor.fetchone()['total'] or 0)

    # =========================
    # DESPESAS DO MÊS
    # =========================
    cursor.execute("""
        SELECT COALESCE(SUM(subtotal), 0) AS total
        FROM despesas
        WHERE data_vencimento BETWEEN %s AND %s
        AND ativo = 'Sim'
    """, (primeiro_dia_mes, hoje))
    total_despesas_mes = float(cursor.fetchone()['total'] or 0)

    # =========================
    # LUCRO DO MÊS
    # =========================
    lucro_mes = faturamento_mes - total_despesas_mes



    # =========================
    # GRÁFICO: ÚLTIMOS 6 MESES
    # =========================
    meses_labels = []
    grafico_recebimentos = []
    grafico_despesas = []
    grafico_saldo = []

    for i in range(5, -1, -1):
        mes = hoje.month - i
        ano = hoje.year

        while mes <= 0:
            mes += 12
            ano -= 1

        data_inicio = date(ano, mes, 1)

        if mes == 12:
            data_fim = date(ano + 1, 1, 1) - timedelta(days=1)
        else:
            data_fim = date(ano, mes + 1, 1) - timedelta(days=1)

        meses_labels.append(data_inicio.strftime('%m/%Y'))

        cursor.execute("""
            SELECT COALESCE(SUM(subtotal), 0) AS total
            FROM recebimentos
            WHERE data_pagamento BETWEEN %s AND %s
            AND ativo = 'Sim'
        """, (data_inicio, data_fim))
        total_rec_mes = float(cursor.fetchone()['total'] or 0)

        cursor.execute("""
            SELECT COALESCE(SUM(subtotal), 0) AS total
            FROM despesas
            WHERE data_pagamento BETWEEN %s AND %s
            AND ativo = 'Sim'
        """, (data_inicio, data_fim))
        total_desp_mes = float(cursor.fetchone()['total'] or 0)

        saldo_mes = total_rec_mes - total_desp_mes

        grafico_recebimentos.append(total_rec_mes)
        grafico_despesas.append(total_desp_mes)
        grafico_saldo.append(saldo_mes)




        # =========================
        # STATUS DOS RECEBIMENTOS
        # =========================

        cursor.execute("""
            SELECT COALESCE(SUM(subtotal), 0) as total
            FROM recebimentos
            WHERE data_pagamento IS NOT NULL
            AND ativo = 'Sim'
        """)
        total_pago = float(cursor.fetchone()['total'] or 0)

        cursor.execute("""
            SELECT COALESCE(SUM(subtotal), 0) as total
            FROM recebimentos
            WHERE data_pagamento IS NULL
            AND data_vencimento >= %s
            AND ativo = 'Sim'
        """, (hoje,))
        total_pendente = float(cursor.fetchone()['total'] or 0)

        cursor.execute("""
            SELECT COALESCE(SUM(subtotal), 0) as total
            FROM recebimentos
            WHERE data_pagamento IS NULL
            AND data_vencimento < %s
            AND ativo = 'Sim'
        """, (hoje,))
        total_atrasado = float(cursor.fetchone()['total'] or 0)





        # =========================
        # EVOLUÇÃO DAS VENDAS (6 MESES)
        # =========================

        grafico_vendas = []

        for i in range(5, -1, -1):
            mes = hoje.month - i
            ano = hoje.year

            while mes <= 0:
                mes += 12
                ano -= 1

            data_inicio = date(ano, mes, 1)

            if mes == 12:
                data_fim = date(ano + 1, 1, 1) - timedelta(days=1)
            else:
                data_fim = date(ano, mes + 1, 1) - timedelta(days=1)

            cursor.execute("""
                SELECT COALESCE(SUM(subtotal), 0) as total
                FROM vendas
                WHERE data_lancamento BETWEEN %s AND %s
                AND ativo = 'Sim'
            """, (data_inicio, data_fim))

            total_mes = float(cursor.fetchone()['total'] or 0)
            grafico_vendas.append(total_mes)




    cursor.close()
    conexao.close()

    return render_template(
        'painel/index.html',
        nome=nome,
        nivel=nivel,
        foto_usuario=foto_usuario,
        nome_sistema=NOME_SISTEMA,
        cor_primaria=COR_PRIMARIA,
        cor_secundaria=COR_SECUNDARIA,
        usuario=usuario,

        total_recebido=total_recebido,
        total_a_receber=total_a_receber,
        total_atrasadas=total_atrasadas,
        total_em_aberto=total_em_aberto,
        faturamento_mes=faturamento_mes,
        total_clientes=total_clientes,
        total_vendas=total_vendas,
        total_estoque_baixo=total_estoque_baixo,
        total_despesas_mes=total_despesas_mes,
        lucro_mes=lucro_mes,
        meses_labels=meses_labels,
        grafico_recebimentos=grafico_recebimentos,
        grafico_despesas=grafico_despesas,
        grafico_saldo=grafico_saldo,
        total_pago=total_pago,
        total_pendente=total_pendente,
        total_atrasado=total_atrasado,
        grafico_vendas=grafico_vendas,
    )




@painel.route('/logout')
def logout():
    usuario_id = session.get('usuario_id')
    nome = session.get('usuario_nome')
    # LANÇAR LOGOUT LOGS 
    registrar_log(
        acao='logout',
        entidade='usuarios',
        registro_id=usuario_id,
        descricao=f"Logout do usuário {nome}"
    )

    session.clear()
    flash('Deslogado com Sucesso!', 'success')
    return redirect(url_for('main.index'))



@painel.route('/painel/salvar-perfil', methods=['POST'])
@login_required
def salvar_perfil():
    usuario_id = session.get('usuario_id')

    nome = request.form.get('nome', '').strip()
    telefone = request.form.get('telefone', '').strip()
    email = request.form.get('email', '').strip()
    cpf = request.form.get('cpf', '').strip()
    cep = request.form.get('cep', '').strip()
    endereco = request.form.get('endereco', '').strip()
    numero = request.form.get('numero', '').strip()
    complemento = request.form.get('complemento', '').strip()
    bairro = request.form.get('bairro', '').strip()
    cidade = request.form.get('cidade', '').strip()
    estado = request.form.get('estado', '').strip()
    senha = request.form.get('senha', '').strip()
    confirmar_senha = request.form.get('confirmar_senha', '').strip()

    pasta_assinaturas = os.path.join('app', 'static', 'img', 'assinaturas')
    os.makedirs(pasta_assinaturas, exist_ok=True)

    assinatura_base64 = request.form.get('assinatura_base64', '').strip()
    remover_assinatura = request.form.get('remover_assinatura', 'não').strip().lower()

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
    usuario_atual = cursor.fetchone()

    assinatura_atual = usuario_atual.get('assinatura') or ''
    nome_arquivo_assinatura = assinatura_atual

    if remover_assinatura == 'sim' and assinatura_atual:
        excluir_arquivo(
            nome_arquivo=assinatura_atual,
            pasta_destino=pasta_assinaturas,
            arquivos_protegidos=[]
        )
        nome_arquivo_assinatura = ''


    if assinatura_base64.startswith('data:image/png;base64,'):
            try:
                conteudo_base64 = assinatura_base64.split(',', 1)[1]
                imagem_bytes = base64.b64decode(conteudo_base64)

                novo_nome_assinatura = f"assinatura_{usuario_id}_{uuid.uuid4().hex[:10]}.png"
                caminho_assinatura = os.path.join(pasta_assinaturas, novo_nome_assinatura)

                with open(caminho_assinatura, 'wb') as f:
                    f.write(imagem_bytes)

                if assinatura_atual and assinatura_atual != novo_nome_assinatura:
                    excluir_arquivo(
                        nome_arquivo=assinatura_atual,
                        pasta_destino=pasta_assinaturas,
                        arquivos_protegidos=[]
                    )

                nome_arquivo_assinatura = novo_nome_assinatura

            except Exception:
                pass        

    if not usuario_atual:
        cursor.close()
        conexao.close()
        return jsonify({'status': 'erro', 'mensagem': 'Usuário não encontrado.'}), 404

    # Verifica se email já existe para outro usuário
    cursor.execute("SELECT id FROM usuarios WHERE email = %s AND id != %s", (email, usuario_id))
    email_existente = cursor.fetchone()

    if email_existente:
        cursor.close()
        conexao.close()
        return jsonify({'status': 'erro', 'mensagem': 'Este e-mail já está sendo usado por outro usuário.'}), 400

    # Validação de senha
    senha_hash = usuario_atual['senha']
    if senha or confirmar_senha:
        if senha != confirmar_senha:
            cursor.close()
            conexao.close()
            return jsonify({'status': 'erro', 'mensagem': 'A confirmação de senha não confere.'}), 400

        senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')

    # Upload da foto
    nome_arquivo_foto = usuario_atual['foto']
    foto = request.files.get('foto')
    pasta_arquivo = os.path.join('app', 'static', 'img', 'usuarios')

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
        foto_antiga = usuario_atual['foto']
        

        excluir_arquivo(
            nome_arquivo=foto_antiga,
            pasta_destino=pasta_arquivo,
            arquivos_protegidos=['sem-foto.jpg', 'sem-foto.png', 'sem-foto.webp']
        )
    
    

    query = """
        UPDATE usuarios SET
            nome = %s,
            telefone = %s,
            email = %s,
            senha = %s,
            cpf = %s,
            endereco = %s,
            numero = %s,
            complemento = %s,
            bairro = %s,
            cidade = %s,
            estado = %s,
            cep = %s,
            foto = %s,
            assinatura = %s
        WHERE id = %s
    """

    valores = (
        nome, telefone, email, senha_hash, cpf, endereco, numero,
        complemento, bairro, cidade, estado, cep, nome_arquivo_foto, nome_arquivo_assinatura, usuario_id
    )

    cursor.execute(query, valores)
    conexao.commit()


    # LANÇAR EDITAR LOGS 
    registrar_log(
        acao='editar',
        entidade='usuarios',
        registro_id=usuario_id,
        descricao=f"perfil do usuário editado: {nome}"
    )

    cursor.close()
    conexao.close()

    # Atualiza sessão
    session['usuario_nome'] = nome
    session['usuario_foto'] = nome_arquivo_foto

    foto_url = url_for('static', filename=f'img/usuarios/{nome_arquivo_foto}') if nome_arquivo_foto else url_for('static', filename='img/sem-foto.jpg')

    return jsonify({
        'status': 'sucesso',
        'mensagem': 'Perfil atualizado com sucesso.',
        'nome': nome,
        'foto_url': foto_url
    })



@painel.route('/painel/salvar-configuracoes', methods=['POST'])
@login_required
@permissao_menu_required('configuracoes')
def salvar_configuracoes():
    nome_sistema = request.form.get('nome_sistema', '').strip()
    email_sistema = request.form.get('email_sistema', '').strip()
    telefone_sistema = request.form.get('telefone', '').strip()
    endereco_sistema = request.form.get('endereco_sistema', '').strip()
    cor_primaria = request.form.get('cor_primaria', '').strip()
    cor_secundaria = request.form.get('cor_secundaria', '').strip()

    # NOVOS CAMPOS SMTP
    smtp_host = request.form.get('smtp_host', '').strip()
    smtp_senha_digitada = request.form.get('smtp_senha', '').strip()
    smtp_porta = request.form.get('smtp_porta', '').strip()
    smtp_seguranca = request.form.get('smtp_seguranca', '').strip()
    

    # NOVOS CAMPOS WHATSAPP
    api_whatsapp = request.form.get('api_whatsapp', '').strip()
    instancia_whatsapp = request.form.get('instancia_whatsapp', '').strip()
    token_whatsapp = request.form.get('token_whatsapp', '').strip()
    url_api = request.form.get('url_api', '').strip()

    # NOVOS CAMPOS IA
    api_ia = request.form.get('api_ia', '').strip()
    token_ia = request.form.get('token_ia', '').strip()

    # NOVOS CAMPOS DEMAIS CONFIG
    dias_excluir_logs = request.form.get('dias_excluir_logs', '').strip()
    rel_html_pdf = request.form.get('rel_html_pdf', '').strip()

    # tratando inteiros
    smtp_porta = int(smtp_porta) if smtp_porta.isdigit() else None
    dias_excluir_logs = int(dias_excluir_logs) if dias_excluir_logs.isdigit() else None

    hora_inicial_alerta = request.form.get('hora_inicial_alerta', '').strip()
    hora_final_alerta = request.form.get('hora_final_alerta', '').strip()

    tipo_dados_pagamento = request.form.get('tipo_dados_pagamento', '').strip()
    dados_pagamento = request.form.get('dados_pagamento', '').strip()
    beneficiario = request.form.get('beneficiario', '').strip()

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("SELECT * FROM config LIMIT 1")
    config_atual = cursor.fetchone()

    if not config_atual:
        cursor.close()
        conexao.close()
        return jsonify({
            'status': 'erro',
            'mensagem': 'Configurações não encontradas.'
        }), 404
    

    smtp_senha_final = config_atual.get('smtp_senha') or ''

    if smtp_senha_digitada:
        smtp_senha_final = criptografar_texto(smtp_senha_digitada)

    logo_atual = config_atual.get('logo')
    icone_atual = config_atual.get('icone')

    nova_logo = logo_atual
    novo_icone = icone_atual

    pasta_arquivo = os.path.join('app', 'static', 'img')

    # Upload da logo
    logo = request.files.get('logo')
    if logo and logo.filename:
        resultado_logo = salvar_arquivo(
            arquivo=logo,
            pasta_destino=pasta_arquivo,
            extensoes_permitidas=['.jpg', '.jpeg', '.png', '.webp'],
            largura_maxima=1000
        )

        if not resultado_logo['sucesso']:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': resultado_logo['mensagem']
            }), 400

        nova_logo = resultado_logo['arquivo']

        excluir_arquivo(
            nome_arquivo=logo_atual,
            pasta_destino=pasta_arquivo,
            arquivos_protegidos=['sem-foto.jpg', 'sem-foto.png', 'sem-foto.webp']
        )

    # Upload do ícone
    icone = request.files.get('icone')
    if icone and icone.filename:
        resultado_icone = salvar_arquivo(
            arquivo=icone,
            pasta_destino=pasta_arquivo,
            extensoes_permitidas=['.jpg', '.jpeg', '.png', '.webp', '.ico'],
            largura_maxima=256
        )

        if not resultado_icone['sucesso']:
            cursor.close()
            conexao.close()
            return jsonify({
                'status': 'erro',
                'mensagem': resultado_icone['mensagem']
            }), 400

        novo_icone = resultado_icone['arquivo']

        excluir_arquivo(
            nome_arquivo=icone_atual,
            pasta_destino=pasta_arquivo,
            arquivos_protegidos=['sem-foto.jpg', 'sem-foto.png', 'sem-foto.webp']
        )

    query = """
        UPDATE config SET
            nome_sistema = %s,
            email_sistema = %s,
            telefone_sistema = %s,
            endereco_sistema = %s,
            logo = %s,
            icone = %s,
            cor_primaria = %s,
            cor_secundaria = %s,
            smtp_host = %s,
            smtp_senha = %s,
            smtp_porta = %s,
            smtp_seguranca = %s,
            api_whatsapp = %s,
            token_whatsapp = %s,
            instancia_whatsapp = %s,
            url_api = %s,
            api_ia = %s,
            token_ia = %s,
            dias_excluir_logs = %s,
            rel_html_pdf = %s,
            hora_inicial_alerta = %s,
            hora_final_alerta = %s,
            tipo_dados_pagamento = %s,
            dados_pagamento = %s,
            beneficiario = %s
        WHERE id = %s
    """

    valores = (
        nome_sistema,
        email_sistema,
        telefone_sistema,
        endereco_sistema,
        nova_logo,
        novo_icone,
        cor_primaria,
        cor_secundaria,
        smtp_host,
        smtp_senha_final,
        smtp_porta,
        smtp_seguranca,
        api_whatsapp,
        token_whatsapp,
        instancia_whatsapp,
        url_api,
        api_ia,
        token_ia,
        dias_excluir_logs,
        rel_html_pdf,
        hora_inicial_alerta,
        hora_final_alerta,
        tipo_dados_pagamento,
        dados_pagamento,
        beneficiario,
        config_atual['id']
        
    )

    cursor.execute(query, valores)
    conexao.commit()

    registrar_log(
        acao='editar',
        entidade='config',
        registro_id=config_atual['id'],
        descricao='registro editado em config'
    )

    cursor.close()
    conexao.close()

    logo_url = url_for('static', filename=f'img/{nova_logo}') if nova_logo else url_for('static', filename='img/sem-foto.jpg')
    icone_url = url_for('static', filename=f'img/{novo_icone}') if novo_icone else url_for('static', filename='img/sem-foto.jpg')

    return jsonify({
        'status': 'sucesso',
        'mensagem': 'Configurações atualizadas com sucesso.',
        'nome_sistema': nome_sistema,
        'logo_url': logo_url,
        'icone_url': icone_url,
        'cor_primaria': cor_primaria,
        'cor_secundaria': cor_secundaria
    })



    


@painel.route('/painel/testar-whatsapp', methods=['POST'])
@login_required
@permissao_menu_required('configuracoes')
def testar_whatsapp_rota():
    try:
        dados = request.get_json()

        if not dados:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Dados não enviados.'
            }), 400

        resultado = testar_whatsapp(dados)

        return jsonify({
            'status': 'sucesso' if resultado.get('ok') else 'erro',
            'mensagem': resultado.get('msg'),
            'dados': resultado  # 🔥 aqui vem o debug completo
        })

    except Exception as e:
        return jsonify({
            'status': 'erro',
            'mensagem': f'Erro interno: {str(e)}'
        }), 500
    



@painel.route('/painel/testar-email', methods=['POST'])
@login_required
@permissao_menu_required('configuracoes')
def testar_email_rota():
    try:
        dados = request.get_json()

        if not dados:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Dados não enviados.'
            }), 400

        resultado = testar_email_smtp(dados)

        return jsonify({
            'status': 'sucesso' if resultado.get('ok') else 'erro',
            'mensagem': resultado.get('msg'),
            'dados': resultado
        })

    except Exception as e:
        return jsonify({
            'status': 'erro',
            'mensagem': f'Erro interno: {str(e)}'
        }), 500
    


@painel.route('/painel/testar-ia', methods=['POST'])
@login_required
@permissao_menu_required('configuracoes')
def testar_ia_rota():
    try:
        dados = request.get_json()

        if not dados:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Dados não enviados.'
            }), 400

        resultado = testar_ia(dados)

        return jsonify({
            'status': 'sucesso' if resultado.get('ok') else 'erro',
            'mensagem': resultado.get('msg'),
            'dados': resultado
        })

    except Exception as e:
        return jsonify({
            'status': 'erro',
            'mensagem': f'Erro interno: {str(e)}'
        }), 500
    





@painel.route('/relatorios/financeiro', methods=['POST'])
@login_required
def relatorio_financeiro():
    conexao = None
    cursor = None

    try:
        tipo = (request.form.get('tipo') or '').strip()
        status = (request.form.get('status') or '').strip()
        plano_conta = (request.form.get('plano_conta') or '').strip()
        cliente = (request.form.get('cliente') or '').strip()
        fornecedor = (request.form.get('fornecedor') or '').strip()
        data_inicial = (request.form.get('data_inicial') or '').strip()
        data_final = (request.form.get('data_final') or '').strip()

        # regra de coerência dos filtros
        if cliente:
            tipo = 'recebimentos'
            fornecedor = ''

        if fornecedor:
            tipo = 'despesas'
            cliente = ''

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        dados = []

        # =========================================
        # RECEBIMENTOS
        # =========================================
        if tipo in ['', 'recebimentos']:
            query_receb = """
                SELECT
                    r.id,
                    'Recebimento' AS tipo_movimento,
                    r.descricao,
                    r.data_lancamento,
                    r.data_vencimento,
                    r.data_pagamento,
                    r.valor,
                    r.desconto,
                    r.multa,
                    r.juros,
                    r.subtotal,
                    r.status,
                    c.nome AS pessoa_nome,
                    pc.nome AS plano_conta_nome,
                    fp.nome AS forma_pagamento_nome,
                    fr.nome AS frequencia_nome,
                    r.parcela,
                    r.qtd_parcelas,
                    r.observacoes
                FROM recebimentos r
                LEFT JOIN clientes c ON r.cliente = c.id
                LEFT JOIN plano_contas pc ON r.plano_conta = pc.id
                LEFT JOIN formas_pagamento fp ON r.forma_pagamento = fp.id
                LEFT JOIN frequencias fr ON r.frequencia = fr.id
                WHERE 1=1
            """
            params_receb = []

            if data_inicial:
                query_receb += " AND r.data_vencimento >= %s"
                params_receb.append(data_inicial)

            if data_final:
                query_receb += " AND r.data_vencimento <= %s"
                params_receb.append(data_final)

            if plano_conta:
                query_receb += " AND r.plano_conta = %s"
                params_receb.append(plano_conta)

            if cliente:
                query_receb += " AND r.cliente = %s"
                params_receb.append(cliente)

            query_receb += " ORDER BY r.data_vencimento ASC, r.id DESC"

            cursor.execute(query_receb, tuple(params_receb))
            recebimentos = cursor.fetchall()

            for item in recebimentos:
                data_pagamento = item.get('data_pagamento')
                data_vencimento = item.get('data_vencimento')

                if data_pagamento:
                    item['status_calculado'] = 'Pago'

                elif isinstance(data_vencimento, date) and data_vencimento < date.today():
                    item['status_calculado'] = 'Atrasado'

                else:
                    item['status_calculado'] = 'Pendente'

            if status:
                recebimentos = [item for item in recebimentos if item.get('status_calculado') == status]

            dados.extend(recebimentos)

        # =========================================
        # DESPESAS
        # =========================================
        if tipo in ['', 'despesas']:
            query_desp = """
                SELECT
                    d.id,
                    'Despesa' AS tipo_movimento,
                    d.descricao,
                    d.data_lancamento,
                    d.data_vencimento,
                    d.data_pagamento,
                    d.valor,
                    d.desconto,
                    d.multa,
                    d.juros,
                    d.subtotal,
                    d.status,
                    f.nome AS pessoa_nome,
                    pc.nome AS plano_conta_nome,
                    fp.nome AS forma_pagamento_nome,
                    fr.nome AS frequencia_nome,
                    d.parcela,
                    d.qtd_parcelas,
                    d.observacoes
                FROM despesas d
                LEFT JOIN fornecedores f ON d.fornecedor = f.id
                LEFT JOIN plano_contas pc ON d.plano_conta = pc.id
                LEFT JOIN formas_pagamento fp ON d.forma_pagamento = fp.id
                LEFT JOIN frequencias fr ON d.frequencia = fr.id
                WHERE 1=1
            """
            params_desp = []

            if data_inicial:
                query_desp += " AND d.data_vencimento >= %s"
                params_desp.append(data_inicial)

            if data_final:
                query_desp += " AND d.data_vencimento <= %s"
                params_desp.append(data_final)

            if plano_conta:
                query_desp += " AND d.plano_conta = %s"
                params_desp.append(plano_conta)

            if fornecedor:
                query_desp += " AND d.fornecedor = %s"
                params_desp.append(fornecedor)

            query_desp += " ORDER BY d.data_vencimento ASC, d.id DESC"

            cursor.execute(query_desp, tuple(params_desp))
            despesas = cursor.fetchall()

            for item in despesas:
                data_pagamento = item.get('data_pagamento')
                data_vencimento = item.get('data_vencimento')

                if data_pagamento:
                    item['status_calculado'] = 'Pago'

                elif isinstance(data_vencimento, date) and data_vencimento < date.today():
                    item['status_calculado'] = 'Atrasado'

                else:
                    item['status_calculado'] = 'Pendente'

            if status:
                despesas = [item for item in despesas if item.get('status_calculado') == status]

            dados.extend(despesas)

        # =========================================
        # ORDENAÇÃO FINAL
        # =========================================
        def ordenar_data(item):
            data_venc = item.get('data_vencimento')

            # Se for uma data válida
            if isinstance(data_venc, date):
                return (data_venc, item.get('id') or 0)

            # Se for None ou inválido, joga lá pra baixo
            return (date.min, item.get('id') or 0)


        dados.sort(key=ordenar_data)

        # =========================================
        # TOTAIS
        # =========================================
        total_recebimentos = sum(
            float(item.get('subtotal') or 0)
            for item in dados
            if item.get('tipo_movimento') == 'Recebimento'
        )

        total_despesas = sum(
            float(item.get('subtotal') or 0)
            for item in dados
            if item.get('tipo_movimento') == 'Despesa'
        )

        saldo_periodo = total_recebimentos - total_despesas

        total_pago = sum(
            float(item.get('subtotal') or 0)
            for item in dados
            if item.get('status_calculado') == 'Pago'
        )

        total_pendente = sum(
            float(item.get('subtotal') or 0)
            for item in dados
            if item.get('status_calculado') == 'Pendente'
        )

        total_atrasado = sum(
            float(item.get('subtotal') or 0)
            for item in dados
            if item.get('status_calculado') == 'Atrasado'
        )

        # =========================================
        # RESUMO POR PLANO DE CONTAS
        # =========================================      
       
        mapa_planos = {}

        for item in dados:
            nome_plano = item.get('plano_conta_nome') or 'Não informado'
            subtotal_item = float(item.get('subtotal') or 0)

            if nome_plano not in mapa_planos:
                mapa_planos[nome_plano] = {
                    'nome': nome_plano,
                    'quantidade': 0,
                    'total': 0.0
                }

            mapa_planos[nome_plano]['quantidade'] += 1
            mapa_planos[nome_plano]['total'] += subtotal_item

        resumo_planos = list(mapa_planos.values())
        resumo_planos.sort(key=lambda x: float(x.get('total') or 0), reverse=True)

        # =========================================
        # NOMES DOS FILTROS
        # =========================================
        tipo_filtro = 'Todos'
        if tipo == 'recebimentos':
            tipo_filtro = 'Recebimentos'
        elif tipo == 'despesas':
            tipo_filtro = 'Despesas'

        status_filtro = status if status else 'Todos'

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

        # =========================================
        # CONFIG RELATÓRIO
        # =========================================
        config_sistema = get_config_sistema()

        tipo_relatorio = (config_sistema.get('rel_html_pdf') or 'pdf').strip().lower()
        if tipo_relatorio not in ['pdf', 'html']:
            tipo_relatorio = 'pdf'

        data_inicial_label = datetime.strptime(data_inicial, '%Y-%m-%d').strftime('%d/%m/%Y') if data_inicial else '—'
        data_final_label = datetime.strptime(data_final, '%Y-%m-%d').strftime('%d/%m/%Y') if data_final else '—'

        # =========================================
        # LOGO
        # =========================================
        logo_src = None
        logo_arquivo = (config_sistema.get('logo') or '').strip()
        if logo_arquivo:
            logo_path = os.path.join('app', 'static', 'img', logo_arquivo)
            logo_src = arquivo_para_data_uri(logo_path)

        # =========================================
        # ASSINATURA
        # =========================================
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

        # =========================================
        # HTML
        # =========================================
        html = render_template(
            'relatorios/relatorios_financeiro.html',
            dados=dados,
            tipo=tipo,
            status=status,
            plano_conta=plano_conta,
            cliente=cliente,
            fornecedor=fornecedor,
            data_inicial=data_inicial,
            data_final=data_final,
            data_inicial_label=data_inicial_label,
            data_final_label=data_final_label,
            tipo_filtro=tipo_filtro,
            status_filtro=status_filtro,
            plano_conta_nome_filtro=plano_conta_nome_filtro,
            cliente_nome_filtro=cliente_nome_filtro,
            fornecedor_nome_filtro=fornecedor_nome_filtro,
            total_recebimentos=total_recebimentos,
            total_despesas=total_despesas,
            saldo_periodo=saldo_periodo,
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

        # =========================================
        # PDF
        # =========================================
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
            headers={'Content-Disposition': 'inline; filename=relatorio_financeiro.pdf'}
        )

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao gerar relatório financeiro.',
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





@painel.route('/relatorios/inadimplentes', methods=['POST'])
@login_required
def relatorio_inadimplentes():
    conexao = None
    cursor = None

    try:
        data_inicial = (request.form.get('data_inicial') or '').strip()
        data_final = (request.form.get('data_final') or '').strip()
        cliente = (request.form.get('cliente') or '').strip()
        ordenar = (request.form.get('ordenar') or 'valor_desc').strip()

        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        hoje = date.today()

        query = """
            SELECT 
                r.cliente,
                c.nome AS cliente_nome,
                c.telefone,
                COUNT(r.id) AS qtd_contas,
                SUM(r.subtotal) AS total_devido,
                MAX(DATEDIFF(%s, r.data_vencimento)) AS dias_atraso
            FROM recebimentos r
            LEFT JOIN clientes c ON r.cliente = c.id
            WHERE r.data_pagamento IS NULL
              AND r.data_vencimento < %s
              AND r.ativo = 'Sim'
        """
        params = [hoje, hoje]

        if data_inicial and data_final:
            query += " AND r.data_vencimento BETWEEN %s AND %s"
            params.append(data_inicial)
            params.append(data_final)

        if cliente:
            query += " AND r.cliente = %s"
            params.append(cliente)

        query += " GROUP BY r.cliente, c.nome, c.telefone"

        if ordenar == 'valor_desc':
            query += " ORDER BY total_devido DESC"
            ordenar_filtro = 'Maior valor devido'
        elif ordenar == 'valor_asc':
            query += " ORDER BY total_devido ASC"
            ordenar_filtro = 'Menor valor devido'
        elif ordenar == 'qtd_desc':
            query += " ORDER BY qtd_contas DESC"
            ordenar_filtro = 'Mais contas'
        elif ordenar == 'qtd_asc':
            query += " ORDER BY qtd_contas ASC"
            ordenar_filtro = 'Menos contas'
        elif ordenar == 'nome_desc':
            query += " ORDER BY cliente_nome DESC"
            ordenar_filtro = 'Nome do cliente (Z-A)'
        else:
            query += " ORDER BY cliente_nome ASC"
            ordenar_filtro = 'Nome do cliente'

        cursor.execute(query, params)
        dados = cursor.fetchall()

        total_geral = 0.0
        total_qtd_contas = 0
        maior_atraso = 0

        for item in dados:
            item['total_devido'] = float(item.get('total_devido') or 0)
            item['qtd_contas'] = int(item.get('qtd_contas') or 0)
            item['dias_atraso'] = int(item.get('dias_atraso') or 0)

            total_geral += item['total_devido']
            total_qtd_contas += item['qtd_contas']

            if item['dias_atraso'] > maior_atraso:
                maior_atraso = item['dias_atraso']

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

        data_inicial_label = datetime.strptime(data_inicial, '%Y-%m-%d').strftime('%d/%m/%Y') if data_inicial else 'Todos'
        data_final_label = datetime.strptime(data_final, '%Y-%m-%d').strftime('%d/%m/%Y') if data_final else 'Todos'

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

        html = render_template(
            'relatorios/relatorios_inadimplentes.html',
            dados=dados,
            total_geral=total_geral,
            total_qtd_contas=total_qtd_contas,
            maior_atraso=maior_atraso,
            data_inicial_label=data_inicial_label,
            data_final_label=data_final_label,
            cliente_nome_filtro=cliente_nome_filtro,
            ordenar_filtro=ordenar_filtro,
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
            headers={'Content-Disposition': 'inline; filename=relatorio_inadimplentes.pdf'}
        )

    except Exception as e:
        return jsonify({
            'status': 'erro',
            'mensagem': 'Erro ao gerar relatório de inadimplentes.',
            'erro': str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()