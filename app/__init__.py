from flask import Flask
from flask_bcrypt import Bcrypt
from app.database.conexao import conectar
from config import EMAIL_SISTEMA, NOME_SISTEMA, SENHA_PADRAO, COR_PRIMARIA, COR_SECUNDARIA, SECRET_KEY
from app.utils.config_sistema import get_config_sistema
from app.utils.menu import MENU_SISTEMA

bcrypt = Bcrypt()

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = SECRET_KEY

    bcrypt.init_app(app)

    from app.routes.main import main
    app.register_blueprint(main)

    from app.routes.painel.routes import painel
    app.register_blueprint(painel)

    from datetime import timedelta
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

    #ROTAS DO PAINEL
    from app.routes.painel.usuarios import pagina as usuarios
    app.register_blueprint(usuarios)

    from app.routes.painel.cargos import pagina as cargos
    app.register_blueprint(cargos)

    from app.routes.painel.logs import pagina as logs
    app.register_blueprint(logs)

    from app.routes.painel.clientes import pagina as clientes
    app.register_blueprint(clientes)

    from app.routes.painel.frequencias import pagina as frequencias
    app.register_blueprint(frequencias)

    from app.routes.painel.formas_pagamento import pagina as formas_pagamento
    app.register_blueprint(formas_pagamento)

    from app.routes.painel.fornecedores import pagina as fornecedores
    app.register_blueprint(fornecedores)

    from app.routes.painel.plano_contas import pagina as plano_contas
    app.register_blueprint(plano_contas)

    from app.routes.painel.centros_custo import pagina as centros_custo
    app.register_blueprint(centros_custo)

    from app.routes.painel.despesas import pagina as despesas
    app.register_blueprint(despesas)

    from app.routes.painel.recebimentos import pagina as recebimentos
    app.register_blueprint(recebimentos)

    from app.routes.painel.arquivos import pagina as arquivos
    app.register_blueprint(arquivos)

    from app.routes.painel.categorias import pagina as categorias
    app.register_blueprint(categorias)

    from app.routes.painel.produtos import pagina as produtos
    app.register_blueprint(produtos)

    from app.routes.painel.entradas import pagina as entradas
    app.register_blueprint(entradas)

    from app.routes.painel.saidas import pagina as saidas
    app.register_blueprint(saidas)

    from app.routes.painel.pdv import pagina as pdv
    app.register_blueprint(pdv)

    from app.routes.painel.lista_vendas import pagina as lista_vendas
    app.register_blueprint(lista_vendas)

    from flask import session
    from app.utils.auth import buscar_menus_permitidos
    from app.utils.menu import MENU_SISTEMA, filtrar_menu_por_permissao

    criar_admin_padrao()
    criar_config_padrao()
    criar_cargos_padrao()
    criar_frequencias_padrao()

    @app.context_processor
    def inject_menu_sistema():
        usuario_id = session.get('usuario_id')
        usuario_nivel = session.get('usuario_nivel')

        if usuario_nivel == 'Administrador':
            return dict(menu_sistema=MENU_SISTEMA)

        if not usuario_id:
            return dict(menu_sistema=[])

        menus_permitidos = buscar_menus_permitidos(usuario_id)
        menu_filtrado = filtrar_menu_por_permissao(MENU_SISTEMA, menus_permitidos)

        return dict(menu_sistema=menu_filtrado)


    @app.context_processor
    def inject_config_sistema():
        config_sistema = get_config_sistema()
        return dict(config_sistema=config_sistema)
    

    @app.context_processor
    def inject_permissoes_especiais():
        from flask import session
        from app.utils.auth import tem_permissao_menu

        usuario_id = session.get('usuario_id')
        usuario_nivel = session.get('usuario_nivel')

        if not usuario_id:
            return dict(pode_ver_configuracoes=False)

        if usuario_nivel == 'Administrador':
            return dict(pode_ver_configuracoes=True)

        return dict(
            pode_ver_configuracoes=tem_permissao_menu(usuario_id, 'configuracoes')
        )
    

    @app.context_processor
    def inject_acoes_usuario():
        from flask import session
        from app.utils.auth import buscar_acoes_permitidas

        usuario_id = session.get('usuario_id')

        if not usuario_id:
            return dict(acoes_usuario=[])

        acoes = buscar_acoes_permitidas(usuario_id)
        return dict(acoes_usuario=acoes)

    
    @app.context_processor
    def carregar_dados_globais():
        conexao = None
        cursor = None

        try:
            conexao = conectar()
            cursor = conexao.cursor(dictionary=True)

            # CLIENTES
            cursor.execute("SELECT id, nome FROM clientes ORDER BY nome ASC")
            clientes = cursor.fetchall()

            # FORNECEDORES
            cursor.execute("SELECT id, nome FROM fornecedores ORDER BY nome ASC")
            fornecedores = cursor.fetchall()

            # PLANO DE CONTAS
            cursor.execute("SELECT id, nome FROM plano_contas ORDER BY nome ASC")
            planos_contas = cursor.fetchall()

            return dict(
                clientes=clientes,
                fornecedores=fornecedores,
                planos_contas=planos_contas
            )

        except:
            return dict(
                clientes=[],
                fornecedores=[],
                planos_contas=[]
            )

        finally:
            if cursor:
                cursor.close()
            if conexao:
                conexao.close()



    @app.context_processor
    def carregar_notificacoes_topo():
        conexao = None
        cursor = None

        try:
            conexao = conectar()
            cursor = conexao.cursor(dictionary=True)

            # RECEBIMENTOS VENCIDOS
            cursor.execute("""
                SELECT 
                    r.id,
                    r.descricao,
                    r.data_vencimento,
                    r.subtotal,
                    c.nome AS cliente_nome
                FROM recebimentos r
                LEFT JOIN clientes c ON r.cliente = c.id
                WHERE r.data_pagamento IS NULL
                AND r.data_vencimento < CURDATE()
                AND r.ativo = 'Sim'
                ORDER BY r.data_vencimento ASC, r.id DESC
                LIMIT 5
            """)
            notificacoes_recebimentos = cursor.fetchall()

            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM recebimentos
                WHERE data_pagamento IS NULL
                AND data_vencimento < CURDATE()
                AND ativo = 'Sim'
            """)
            notificacoes_recebimentos_total = cursor.fetchone()['total']

            # DESPESAS VENCIDAS
            cursor.execute("""
                SELECT 
                    d.id,
                    d.descricao,
                    d.data_vencimento,
                    d.subtotal,
                    f.nome AS fornecedor_nome
                FROM despesas d
                LEFT JOIN fornecedores f ON d.fornecedor = f.id
                WHERE d.data_pagamento IS NULL
                AND d.data_vencimento < CURDATE()
                AND d.ativo = 'Sim'
                ORDER BY d.data_vencimento ASC, d.id DESC
                LIMIT 5
            """)
            notificacoes_despesas = cursor.fetchall()

            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM despesas
                WHERE data_pagamento IS NULL
                AND data_vencimento < CURDATE()
                AND ativo = 'Sim'
            """)
            notificacoes_despesas_total = cursor.fetchone()['total']

            return dict(
                notificacoes_recebimentos=notificacoes_recebimentos,
                notificacoes_recebimentos_total=notificacoes_recebimentos_total,
                notificacoes_despesas=notificacoes_despesas,
                notificacoes_despesas_total=notificacoes_despesas_total
            )

        except Exception:
            return dict(
                notificacoes_recebimentos=[],
                notificacoes_recebimentos_total=0,
                notificacoes_despesas=[],
                notificacoes_despesas_total=0
            )

        finally:
            if cursor:
                cursor.close()
            if conexao:
                conexao.close()


    return app




def criar_admin_padrao():
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("SELECT * FROM usuarios WHERE nivel = 'Administrador' LIMIT 1")
    usuario = cursor.fetchone()

    if not usuario:
        senha_crip = bcrypt.generate_password_hash(SENHA_PADRAO).decode('utf-8')
        cursor.execute("INSERT INTO usuarios SET nome = %s, email = %s, senha = %s, nivel = 'Administrador', ativo = 'Sim', data_cadastro = curDate(), foto = 'sem_foto.webp'", (NOME_SISTEMA, EMAIL_SISTEMA, senha_crip))
        conexao.commit()

    cursor.close()
    conexao.close()




def criar_config_padrao():
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("SELECT * FROM config LIMIT 1")
    config = cursor.fetchone()

    if not config:
        cursor.execute("""
            INSERT INTO config SET
                nome_sistema = %s,
                email_sistema = %s,
                telefone_sistema = '',
                endereco_sistema = '',
                logo = 'logo.webp',
                icone = 'icone.webp',
                cor_primaria = %s,
                cor_secundaria = %s
        """, (
            NOME_SISTEMA,
            EMAIL_SISTEMA,
            COR_PRIMARIA,
            COR_SECUNDARIA
        ))
        conexao.commit()

    cursor.close()
    conexao.close()





def criar_cargos_padrao():
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("SELECT * FROM cargos LIMIT 1")
    cargo = cursor.fetchone()

    if not cargo:       
        cursor.execute("INSERT INTO cargos SET nome = 'Administrador' ")
        conexao.commit()
        cursor.execute("INSERT INTO cargos SET nome = 'Comum' ")
        conexao.commit()

    cursor.close()
    conexao.close()





def criar_frequencias_padrao():
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("SELECT * FROM frequencias LIMIT 1")
    frequencia = cursor.fetchone()

    if not frequencia:       
        cursor.execute("INSERT INTO frequencias SET nome = 'Nenhuma', dias = 0, ativo = 'Sim' ")
        conexao.commit()
        cursor.execute("INSERT INTO frequencias SET nome = 'Diária', dias = 1, ativo = 'Sim' ")
        conexao.commit()
        cursor.execute("INSERT INTO frequencias SET nome = 'Mensal', dias = 30, ativo = 'Sim' ")
        conexao.commit()

    cursor.close()
    conexao.close()
    




