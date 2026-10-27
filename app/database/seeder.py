from datetime import date, datetime, timedelta
from app.database.conexao import conectar
from app import bcrypt
from config import SENHA_PADRAO


def popular_dados_distribuidora():
    """
    Popula o banco de dados com uma simulação realista de uma Distribuidora de Eletrodomésticos e Eletrônicos:
    - Cargos estruturais
    - Funcionários com perfis e permissões granulares (vendas, caixa, financeiro, estoque)
    - Formas de pagamento comerciais
    - Centros de custo e Plano de contas contábil
    - Fornecedores (fabricantes como Whirlpool, Samsung, LG, Mondial, Britânia)
    - Categorias e Catálogo de produtos (Linha Branca, Portáteis, TV, Climatização)
    - Clientes lojistas (PJ) e consumidores (PF)
    - Vendas, Recebimentos e Despesas para dar vida ao Dashboard
    """
    conexao = None
    cursor = None

    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        # Verifica se já foi populado
        cursor.execute("SELECT COUNT(*) AS total FROM produtos")
        res = cursor.fetchone()
        if res and res['total'] > 0:
            print("[SEEDER] O banco já possui produtos cadastrados. Pulando seed.")
            return

        print("[SEEDER] Iniciando população de dados da Distribuidora de Eletros...")

        hoje = date.today()
        primeiro_dia_mes = hoje.replace(day=1)
        senha_hash = bcrypt.generate_password_hash(SENHA_PADRAO).decode('utf-8')

        # ---------------------------------------------------------
        # 1. ATUALIZAR CONFIGURAÇÃO DA EMPRESA
        # ---------------------------------------------------------
        cursor.execute("""
            UPDATE config SET
                nome_sistema = 'EletroKing Distribuidora',
                email_sistema = 'contato@eletroking.com.br',
                telefone_sistema = '(11) 3456-7890',
                endereco_sistema = 'Av. das Indústrias, 1500 - Galpão 04 - São Paulo/SP',
                tipo_dados_pagamento = 'pix',
                dados_pagamento = 'financeiro@eletroking.com.br (Chave PIX CNPJ)',
                beneficiario = 'EletroKing Distribuidora de Eletros Ltda'
            WHERE id > 0
        """)

        # ---------------------------------------------------------
        # 2. CARGOS
        # ---------------------------------------------------------
        cargos = [
            "Gerente Comercial",
            "Vendedor Interno",
            "Operador de Caixa",
            "Analista Financeiro",
            "Encarregado de Estoque"
        ]
        for cargo in cargos:
            cursor.execute("SELECT id FROM cargos WHERE nome = %s", (cargo,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO cargos (nome) VALUES (%s)", (cargo,))

        # ---------------------------------------------------------
        # 3. USUÁRIOS / FUNCIONÁRIOS (Senha padrão: 123)
        # ---------------------------------------------------------
        funcionarios = [
            {
                "nome": "Carlos Silva - Vendas",
                "email": "vendas@eletroking.com",
                "telefone": "(11) 98765-1001",
                "cpf": "111.222.333-44",
                "nivel": "Comum",
                "menus": ["dashboard", "clientes", "produtos", "pdv", "vendas"],
                "acoes": ["inserir", "editar"]
            },
            {
                "nome": "Juliana Mendes - Caixa",
                "email": "caixa@eletroking.com",
                "telefone": "(11) 98765-1002",
                "cpf": "222.333.444-55",
                "nivel": "Comum",
                "menus": ["pdv", "vendas", "clientes"],
                "acoes": ["inserir"]
            },
            {
                "nome": "Roberto Alves - Financeiro",
                "email": "financeiro@eletroking.com",
                "telefone": "(11) 98765-1003",
                "cpf": "333.444.555-66",
                "nivel": "Comum",
                "menus": ["dashboard", "recebimentos", "despesas", "relatorios", "relatorios_inadimplentes", "relatorios_financeiro", "formas_pagamento", "plano_contas", "centros_custo"],
                "acoes": ["inserir", "editar", "baixar"]
            },
            {
                "nome": "Marcos Souza - Estoque",
                "email": "estoque@eletroking.com",
                "telefone": "(11) 98765-1004",
                "cpf": "444.555.666-77",
                "nivel": "Comum",
                "menus": ["produtos", "categorias", "entradas", "saidas"],
                "acoes": ["inserir", "editar"]
            }
        ]

        for func in funcionarios:
            cursor.execute("SELECT id FROM usuarios WHERE email = %s", (func["email"],))
            user_exist = cursor.fetchone()
            if not user_exist:
                cursor.execute("""
                    INSERT INTO usuarios (
                        nome, email, senha, telefone, cpf, endereco, numero, bairro, cidade, estado, cep,
                        foto, nivel, ativo, data_cadastro
                    ) VALUES (
                        %s, %s, %s, %s, %s, 'Rua Comercial', '100', 'Centro', 'São Paulo', 'SP', '01001-000',
                        'sem_foto.webp', %s, 'Sim', NOW()
                    )
                """, (func["nome"], func["email"], senha_hash, func["telefone"], func["cpf"], func["nivel"]))
                user_id = cursor.lastrowid

                # Cadastra permissões de menu
                for menu in func["menus"]:
                    cursor.execute("""
                        INSERT IGNORE INTO usuarios_permissoes (usuario_id, menu_id)
                        VALUES (%s, %s)
                    """, (user_id, menu))

                # Cadastra permissões de ações
                for acao in func["acoes"]:
                    cursor.execute("""
                        INSERT IGNORE INTO usuarios_acoes (usuario_id, acao)
                        VALUES (%s, %s)
                    """, (user_id, acao))

        # ---------------------------------------------------------
        # 4. FORMAS DE PAGAMENTO
        # ---------------------------------------------------------
        formas = [
            ("Dinheiro", 0.00, 5.00),
            ("PIX à Vista", 0.00, 3.00),
            ("Cartão de Débito", 1.50, 0.00),
            ("Cartão de Crédito 1x", 3.00, 0.00),
            ("Cartão de Crédito Parcelado", 5.50, 0.00),
            ("Boleto Bancário 30 Dias", 2.00, 0.00)
        ]
        for nome_f, taxa, desc in formas:
            cursor.execute("SELECT id FROM formas_pagamento WHERE nome = %s", (nome_f,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO formas_pagamento (nome, taxa, desconto, ativo) VALUES (%s, %s, %s, 'Sim')", (nome_f, taxa, desc))

        # ---------------------------------------------------------
        # 5. CENTROS DE CUSTO
        # ---------------------------------------------------------
        centros = [
            "Matriz - Centro de Distribuição",
            "Showroom & Balcão Vendas",
            "Setor Administrativo & TI",
            "Logística & Frota"
        ]
        for c in centros:
            cursor.execute("SELECT id FROM centros_custo WHERE nome = %s", (c,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO centros_custo (nome, ativo) VALUES (%s, 'Sim')", (c,))

        # ---------------------------------------------------------
        # 6. PLANO DE CONTAS
        # ---------------------------------------------------------
        planos = [
            ("Vendas no Balcão / PDV", "Receita"),
            ("Faturamento Atacado / Distribuição", "Receita"),
            ("Aquisição de Mercadorias para Revenda", "Despesa"),
            ("Aluguel do Centro de Distribuição", "Despesa"),
            ("Energia Elétrica e Telefonia", "Despesa"),
            ("Folha de Pagamento & Encargos", "Despesa"),
            ("Fretes e Logística de Entrega", "Despesa"),
            ("Manutenção e Suprimentos", "Despesa")
        ]
        for nome_p, tipo_p in planos:
            cursor.execute("SELECT id FROM plano_contas WHERE nome = %s", (nome_p,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO plano_contas (nome, tipo, ativo) VALUES (%s, %s, 'Sim')", (nome_p, tipo_p))

        # ---------------------------------------------------------
        # 7. FORNECEDORES (Fabricantes de Eletros)
        # ---------------------------------------------------------
        fornecedores = [
            ("Whirlpool S.A. (Brastemp & Consul)", "0800-757-2290", "comercial@whirlpool.com", "59.105.999/0001-86", "São Paulo", "SP"),
            ("Mondial Eletrodomésticos S.A.", "(11) 3345-2000", "vendas@mondialline.com.br", "03.952.420/0001-44", "Barueri", "SP"),
            ("Samsung Eletrônica da Amazônia", "(11) 4004-0000", "b2b@samsung.com.br", "00.280.273/0001-37", "Campinas", "SP"),
            ("LG Electronics do Brasil Ltda", "0800-707-5454", "distribuicao@lge.com.br", "01.166.372/0001-55", "Taubaté", "SP"),
            ("Britânia & Philco Eletrônicos S.A.", "(41) 3215-1000", "pedidos@britania.com.br", "76.492.701/0001-57", "Curitiba", "PR"),
            ("Electrolux do Brasil S.A.", "0800-728-8778", "vendas@electrolux.com.br", "76.487.032/0001-25", "Curitiba", "PR")
        ]
        for f_nome, f_tel, f_email, f_cnpj, f_cid, f_uf in fornecedores:
            cursor.execute("SELECT id FROM fornecedores WHERE nome = %s", (f_nome,))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO fornecedores (
                        nome, telefone, email, cpf_cnpj, cep, endereco, numero, bairro, cidade, estado, ativo
                    ) VALUES (
                        %s, %s, %s, %s, '01452-000', 'Avenida Industrial', '500', 'Distrito Industrial', %s, %s, 'Sim'
                    )
                """, (f_nome, f_tel, f_email, f_cnpj, f_cid, f_uf))

        # ---------------------------------------------------------
        # 8. CATEGORIAS DE PRODUTOS
        # ---------------------------------------------------------
        categorias = [
            ("Linha Branca", "Refrigeradores, Lavadoras, Secadoras e Fogões", 1),
            ("Eletroportáteis", "Air Fryers, Liquidificadores, Cafeteiras e Batedeiras", 2),
            ("Áudio & Vídeo", "Smart TVs, Soundbars, Caixas de Som e Home Theaters", 3),
            ("Climatização & Ar", "Aparelhos de Ar-condicionado Split, Ventiladores e Climatizadores", 4),
            ("Tecnologia & Telefonia", "Smartphones, Tablets, Monitores e Acessórios", 5)
        ]
        map_categorias = {}
        for cat_nome, cat_desc, cat_pos in categorias:
            cursor.execute("SELECT id FROM categorias WHERE nome = %s", (cat_nome,))
            row = cursor.fetchone()
            if not row:
                cursor.execute("""
                    INSERT INTO categorias (nome, foto, posicao, descricao, ativo)
                    VALUES (%s, 'sem_foto.webp', %s, %s, 'Sim')
                """, (cat_nome, cat_pos, cat_desc))
                map_categorias[cat_nome] = cursor.lastrowid
            else:
                map_categorias[cat_nome] = row['id']

        # ---------------------------------------------------------
        # 9. PRODUTOS (Catálogo Realista com Custos e Venda)
        # ---------------------------------------------------------
        produtos = [
            ("Geladeira Frost Free 450L Inox Brastemp", "Refrigerador duplex inox, painel eletrônico touch e tecnologia evox.", "Linha Branca", 2450.00, 3890.00, 18, 5),
            ("Lavadora de Roupas 13kg Electrolux Turbo", "Lavadora automática com 12 programas de lavagem e dispenser autolimpante.", "Linha Branca", 1350.00, 2190.00, 14, 4),
            ("Fogão 5 Bocas com Mesa de Vidro Brastemp", "Mesa de vidro temperado, trempes individuais de ferro fundido e acendimento automático.", "Linha Branca", 980.00, 1690.00, 10, 3),
            ("Fritadeira Air Fryer 4.2L Digital Mondial", "Air fryer sem óleo, timer 60 min, cuba antiaderente e cesto removível.", "Eletroportáteis", 185.00, 349.00, 42, 10),
            ("Micro-ondas 34L Espelhado LG EasyClean", "Micro-ondas com acabamento espelhado, revestimento antibacteriano e 16 receitas pré-programadas.", "Eletroportáteis", 420.00, 749.00, 25, 8),
            ("Cafeteira Espresso Automática Mondial", "Prepara cafés expressos cremosos e cappuccinos com bomba de 20 bar de pressão.", "Eletroportáteis", 210.00, 429.00, 28, 6),
            ("Liquidificador Turbo 1200W Inox Britânia", "Jarra com capacidade de 3 litros, 12 velocidades e lâminas integradas de inox.", "Eletroportáteis", 75.00, 159.00, 50, 15),
            ("Smart TV 55\" 4K UHD Crystal Samsung", "Resolução 4K real, design sem bordas, comando de voz e Gaming Hub integrado.", "Áudio & Vídeo", 1620.00, 2799.00, 22, 6),
            ("Smart TV 65\" 4K OLED LG Evo", "Painel OLED com pixels que se autoiluminam, taxa de 120Hz e som Dolby Atmos.", "Áudio & Vídeo", 3800.00, 5990.00, 8, 3),
            ("Soundbar 2.1 Canais 300W Bluetooth Samsung", "Subwoofer sem fio potente, conexão Bluetooth e modo de aprimoramento de voz.", "Áudio & Vídeo", 490.00, 899.00, 19, 5),
            ("Ar-condicionado Split Inverter 12.000 BTUs LG", "Dual Inverter, economiza até 70% de energia, super silencioso com Wi-Fi ThinQ.", "Climatização & Ar", 1580.00, 2650.00, 15, 5),
            ("Ventilador de Coluna 40cm Turbo Mondial", "Ventilador silencioso com 8 pás e ajuste de altura telescópico.", "Climatização & Ar", 98.00, 189.00, 7, 12), # Estoque baixo para testar alerta!
            ("Smartphone Galaxy A55 5G 128GB Samsung", "Tela Super AMOLED 120Hz, câmera tripla de 50MP e resistência contra água IP67.", "Tecnologia & Telefonia", 1250.00, 1999.00, 25, 6)
        ]

        for p_nome, p_desc, p_cat_nome, p_compra, p_venda, p_est, p_est_min in produtos:
            cat_id = map_categorias.get(p_cat_nome, 1)
            cursor.execute("""
                INSERT INTO produtos (
                    nome, descricao, foto, categoria_id, valor_compra, valor_venda,
                    estoque, nivel_minimo_estoque, controlar_estoque, ativo, data_cadastro
                ) VALUES (
                    %s, %s, 'sem_foto.webp', %s, %s, %s, %s, %s, 'Sim', 'Sim', NOW()
                )
            """, (p_nome, p_desc, cat_id, p_compra, p_venda, p_est, p_est_min))

        # ---------------------------------------------------------
        # 10. CLIENTES (Lojistas e Consumidores Finais)
        # ---------------------------------------------------------
        clientes = [
            ("Eletro Magazine Silva & Cia Ltda", "contato@eletromagazine.com.br", "(11) 3210-9988", "(11) 99888-7711", "PJ", "12.345.678/0001-90", "Rua das Lojas", "250", "Centro", "Guarulhos", "SP", 50000.00),
            ("Varejão dos Eletros Bom Preço", "compras@varejaobompreco.com.br", "(11) 3456-1122", "(11) 98777-6622", "PJ", "23.456.789/0001-01", "Av. do Comércio", "1100", "Jardins", "São Paulo", "SP", 35000.00),
            ("Construtora & Engenharia Horizonte", "suprimentos@horizonte.eng.br", "(11) 2233-4455", "(11) 97666-5533", "PJ", "34.567.890/0001-12", "Rua Bela Cintra", "800", "Consolação", "São Paulo", "SP", 80000.00),
            ("Carlos Eduardo Mendes", "carlos.mendes@gmail.com", "(11) 99111-2233", "(11) 99111-2233", "PF", "111.222.333-44", "Alameda dos Anapurus", "45", "Moema", "São Paulo", "SP", 10000.00),
            ("Mariana Costa Ferreira", "mariana.costa@hotmail.com", "(11) 98222-3344", "(11) 98222-3344", "PF", "222.333.444-55", "Rua Pamplona", "720", "Jardim Paulista", "São Paulo", "SP", 12000.00),
            ("Supermercado e Variedades Santos", "financeiro@supermercadosantos.com", "(13) 3344-5566", "(13) 99555-4433", "PJ", "45.678.901/0001-23", "Av. Ana Costa", "300", "Gonzaga", "Santos", "SP", 40000.00)
        ]

        cliente_ids = []
        for c_nome, c_email, c_tel, c_whats, c_tipo, c_doc, c_rua, c_num, c_bairro, c_cid, c_uf, c_limite in clientes:
            cursor.execute("""
                INSERT INTO clientes (
                    nome, email, telefone, whatsapp, tipo_pessoa, cpf_cnpj,
                    cep, endereco, numero, bairro, cidade, estado, foto,
                    ativo, data_cadastro, limite_credito, saldo_devedor
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    '01400-000', %s, %s, %s, %s, %s, 'sem_foto.webp',
                    'Sim', NOW(), %s, 0.00
                )
            """, (c_nome, c_email, c_tel, c_whats, c_tipo, c_doc, c_rua, c_num, c_bairro, c_cid, c_uf, c_limite))
            cliente_ids.append(cursor.lastrowid)

        # ---------------------------------------------------------
        # 11. FINANCEIRO: RECEBIMENTOS SIMULADOS
        # ---------------------------------------------------------
        # A) Recebidos neste mês (para alimentar o indicador "Recebido no Mês")
        cursor.execute("""
            INSERT INTO recebimentos (
                descricao, valor, subtotal, data_lancamento, data_vencimento, data_pagamento, status,
                cliente, forma_pagamento, plano_conta, centro_custo, ativo, alertado
            ) VALUES
            ('Venda Faturada 10x TVs 55 - Eletro Magazine', 27990.00, 27990.00, %s, %s, %s, 'Pago', %s, 2, 2, 1, 'Sim', 'Não'),
            ('Venda Balcão 2x Geladeiras Frost Free', 7780.00, 7780.00, %s, %s, %s, 'Pago', %s, 2, 1, 2, 'Sim', 'Não'),
            ('Venda 5x Air Fryer Mondial - Cliente Balcão', 1745.00, 1745.00, %s, %s, %s, 'Pago', %s, 1, 1, 2, 'Sim', 'Não')
        """, (
            primeiro_dia_mes, primeiro_dia_mes, hoje, cliente_ids[0],
            primeiro_dia_mes, primeiro_dia_mes, hoje, cliente_ids[1],
            primeiro_dia_mes, primeiro_dia_mes, hoje, cliente_ids[3]
        ))

        # B) Contas a Receber Futuras / Pendentes (para alimentar "A Receber")
        data_futura_1 = hoje + timedelta(days=10)
        data_futura_2 = hoje + timedelta(days=20)
        cursor.execute("""
            INSERT INTO recebimentos (
                descricao, valor, subtotal, data_lancamento, data_vencimento, data_pagamento, status,
                cliente, forma_pagamento, plano_conta, centro_custo, ativo, alertado
            ) VALUES
            ('Parcela 2/3 Lote Climatizadores e Splits', 13250.00, 13250.00, %s, %s, NULL, 'Pendente', %s, 6, 2, 1, 'Sim', 'Não'),
            ('Parcela 3/3 Lote Climatizadores e Splits', 13250.00, 13250.00, %s, %s, NULL, 'Pendente', %s, 6, 2, 1, 'Sim', 'Não'),
            ('Faturamento Quinzena - Supermercado Santos', 9850.00, 9850.00, %s, %s, NULL, 'Pendente', %s, 6, 2, 1, 'Sim', 'Não')
        """, (
            hoje, data_futura_1, cliente_ids[2],
            hoje, data_futura_2, cliente_ids[2],
            hoje, data_futura_1, cliente_ids[5]
        ))

        # C) Contas Atrasadas (para alimentar o indicador "Contas Atrasadas" e notificações)
        data_atrasada_1 = hoje - timedelta(days=7)
        data_atrasada_2 = hoje - timedelta(days=15)
        cursor.execute("""
            INSERT INTO recebimentos (
                descricao, valor, subtotal, data_lancamento, data_vencimento, data_pagamento, status,
                cliente, forma_pagamento, plano_conta, centro_custo, ativo, alertado
            ) VALUES
            ('Faturamento Lote 4x Lavadoras - Em Atraso', 8760.00, 8760.00, %s, %s, NULL, 'Vencida', %s, 6, 2, 1, 'Sim', 'Não'),
            ('Manutenção e Suprimentos - Varejão Bom Preço', 1450.00, 1450.00, %s, %s, NULL, 'Vencida', %s, 6, 2, 1, 'Sim', 'Não')
        """, (
            hoje - timedelta(days=30), data_atrasada_1, cliente_ids[1],
            hoje - timedelta(days=45), data_atrasada_2, cliente_ids[1]
        ))

        # ---------------------------------------------------------
        # 12. FINANCEIRO: DESPESAS SIMULADAS
        # ---------------------------------------------------------
        # A) Despesas Pagas no Mês
        cursor.execute("""
            INSERT INTO despesas (
                descricao, valor, subtotal, data_lancamento, data_vencimento, data_pagamento, status,
                fornecedor, forma_pagamento, plano_conta, centro_custo, ativo
            ) VALUES
            ('Aluguel Galpão Logístico - CD Central', 8500.00, 8500.00, %s, %s, %s, 'Pago', 1, 2, 4, 1, 'Sim'),
            ('Conta de Energia Elétrica - Enel SP', 2150.00, 2150.00, %s, %s, %s, 'Pago', 1, 2, 5, 1, 'Sim'),
            ('Folha de Pagamento Funcionários - Competência', 14200.00, 14200.00, %s, %s, %s, 'Pago', 1, 2, 6, 3, 'Sim')
        """, (
            primeiro_dia_mes, primeiro_dia_mes, hoje,
            primeiro_dia_mes, primeiro_dia_mes, hoje,
            primeiro_dia_mes, primeiro_dia_mes, hoje
        ))

        # B) Despesas Pendentes / A Pagar Futuras
        cursor.execute("""
            INSERT INTO despesas (
                descricao, valor, subtotal, data_lancamento, data_vencimento, data_pagamento, status,
                fornecedor, forma_pagamento, plano_conta, centro_custo, ativo
            ) VALUES
            ('Fatura Frete Transportadora TransEletro', 3800.00, 3800.00, %s, %s, NULL, 'Pendente', 2, 6, 7, 4, 'Sim'),
            ('Aquisição Lote 50x Air Fryers Mondial', 9250.00, 9250.00, %s, %s, NULL, 'Pendente', 2, 6, 3, 1, 'Sim')
        """, (
            hoje, data_futura_1,
            hoje, data_futura_2
        ))

        conexao.commit()
        print("[SEEDER] População da Distribuidora de Eletros concluída com sucesso!")

    except Exception as e:
        if conexao:
            conexao.rollback()
        print(f"[SEEDER ERRO] Falha ao popular dados: {e}")

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()
