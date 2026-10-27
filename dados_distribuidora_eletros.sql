-- ===================================================================
-- DADOS FICTÍCIOS: SIMULAÇÃO DE DISTRIBUIDORA DE ELETRODOMÉSTICOS
-- ===================================================================

-- 1. ATUALIZAR CONFIGURAÇÃO DA EMPRESA (WHITE-LABEL)
UPDATE config SET
    nome_sistema = 'EletroKing Distribuidora',
    email_sistema = 'contato@eletroking.com.br',
    telefone_sistema = '(11) 3456-7890',
    endereco_sistema = 'Av. das Indústrias, 1500 - Galpão 04 - São Paulo/SP',
    tipo_dados_pagamento = 'pix',
    dados_pagamento = 'financeiro@eletroking.com.br (Chave PIX CNPJ)',
    beneficiario = 'EletroKing Distribuidora de Eletros Ltda'
WHERE id > 0;

-- 2. CARGOS
INSERT IGNORE INTO cargos (nome) VALUES 
('Gerente Comercial'),
('Vendedor Interno'),
('Operador de Caixa'),
('Analista Financeiro'),
('Encarregado de Estoque');

-- 3. FORMAS DE PAGAMENTO
INSERT IGNORE INTO formas_pagamento (nome, taxa, desconto, ativo) VALUES
('Dinheiro', 0.00, 5.00, 'Sim'),
('PIX à Vista', 0.00, 3.00, 'Sim'),
('Cartão de Débito', 1.50, 0.00, 'Sim'),
('Cartão de Crédito 1x', 3.00, 0.00, 'Sim'),
('Cartão de Crédito Parcelado', 5.50, 0.00, 'Sim'),
('Boleto Bancário 30 Dias', 2.00, 0.00, 'Sim');

-- 4. CENTROS DE CUSTO
INSERT IGNORE INTO centros_custo (nome, ativo) VALUES
('Matriz - Centro de Distribuição', 'Sim'),
('Showroom & Balcão Vendas', 'Sim'),
('Setor Administrativo & TI', 'Sim'),
('Logística & Frota', 'Sim');

-- 5. PLANO DE CONTAS
INSERT IGNORE INTO plano_contas (nome, tipo, ativo) VALUES
('Vendas no Balcão / PDV', 'Receita', 'Sim'),
('Faturamento Atacado / Distribuição', 'Receita', 'Sim'),
('Aquisição de Mercadorias para Revenda', 'Despesa', 'Sim'),
('Aluguel do Centro de Distribuição', 'Despesa', 'Sim'),
('Energia Elétrica e Telefonia', 'Despesa', 'Sim'),
('Folha de Pagamento & Encargos', 'Despesa', 'Sim'),
('Fretes e Logística de Entrega', 'Despesa', 'Sim'),
('Manutenção e Suprimentos', 'Despesa', 'Sim');

-- 6. FORNECEDORES (Fabricantes)
INSERT IGNORE INTO fornecedores (nome, telefone, email, cpf_cnpj, cep, endereco, numero, bairro, cidade, estado, ativo) VALUES
('Whirlpool S.A. (Brastemp & Consul)', '0800-757-2290', 'comercial@whirlpool.com', '59.105.999/0001-86', '01452-000', 'Avenida das Nações', '1200', 'Distrito Industrial', 'São Paulo', 'SP', 'Sim'),
('Mondial Eletrodomésticos S.A.', '(11) 3345-2000', 'vendas@mondialline.com.br', '03.952.420/0001-44', '06454-000', 'Alameda Rio Negro', '500', 'Alphaville', 'Barueri', 'SP', 'Sim'),
('Samsung Eletrônica da Amazônia', '(11) 4004-0000', 'b2b@samsung.com.br', '00.280.273/0001-37', '13097-105', 'Rua dos Eletros', '100', 'Polo Tecnológico', 'Campinas', 'SP', 'Sim'),
('LG Electronics do Brasil Ltda', '0800-707-5454', 'distribuicao@lge.com.br', '01.166.372/0001-55', '12080-000', 'Rodovia Dutra', 'Km 135', 'Industrial', 'Taubaté', 'SP', 'Sim'),
('Britânia & Philco Eletrônicos S.A.', '(41) 3215-1000', 'pedidos@britania.com.br', '76.492.701/0001-57', '81200-100', 'Rua Dona Francisca', '400', 'Cidade Industrial', 'Curitiba', 'PR', 'Sim'),
('Electrolux do Brasil S.A.', '0800-728-8778', 'vendas@electrolux.com.br', '76.487.032/0001-25', '80215-900', 'Rua Ministro Gabriel', '860', 'Guabirotuba', 'Curitiba', 'PR', 'Sim');

-- 7. CATEGORIAS DE PRODUTOS
INSERT IGNORE INTO categorias (nome, foto, posicao, descricao, ativo) VALUES
('Linha Branca', 'sem_foto.webp', 1, 'Refrigeradores, Lavadoras, Secadoras e Fogões', 'Sim'),
('Eletroportáteis', 'sem_foto.webp', 2, 'Air Fryers, Liquidificadores, Cafeteiras e Batedeiras', 'Sim'),
('Áudio & Vídeo', 'sem_foto.webp', 3, 'Smart TVs, Soundbars, Caixas de Som e Home Theaters', 'Sim'),
('Climatização & Ar', 'sem_foto.webp', 4, 'Aparelhos de Ar-condicionado Split, Ventiladores e Climatizadores', 'Sim'),
('Tecnologia & Telefonia', 'sem_foto.webp', 5, 'Smartphones, Tablets, Monitores e Acessórios', 'Sim');

-- 8. PRODUTOS DO CATÁLOGO
INSERT INTO produtos (nome, descricao, foto, categoria_id, valor_compra, valor_venda, estoque, nivel_minimo_estoque, controlar_estoque, ativo, data_cadastro) VALUES
('Geladeira Frost Free 450L Inox Brastemp', 'Refrigerador duplex inox, painel eletrônico touch e tecnologia evox.', 'sem_foto.webp', 1, 2450.00, 3890.00, 18, 5, 'Sim', 'Sim', NOW()),
('Lavadora de Roupas 13kg Electrolux Turbo', 'Lavadora automática com 12 programas de lavagem e dispenser autolimpante.', 'sem_foto.webp', 1, 1350.00, 2190.00, 14, 4, 'Sim', 'Sim', NOW()),
('Fogão 5 Bocas com Mesa de Vidro Brastemp', 'Mesa de vidro temperado, trempes individuais de ferro fundido e acendimento automático.', 'sem_foto.webp', 1, 980.00, 1690.00, 10, 3, 'Sim', 'Sim', NOW()),
('Fritadeira Air Fryer 4.2L Digital Mondial', 'Air fryer sem óleo, timer 60 min, cuba antiaderente e cesto removível.', 'sem_foto.webp', 2, 185.00, 349.00, 42, 10, 'Sim', 'Sim', NOW()),
('Micro-ondas 34L Espelhado LG EasyClean', 'Micro-ondas com acabamento espelhado, revestimento antibacteriano e receitas pré-programadas.', 'sem_foto.webp', 2, 420.00, 749.00, 25, 8, 'Sim', 'Sim', NOW()),
('Cafeteira Espresso Automática Mondial', 'Prepara cafés expressos cremosos e cappuccinos com bomba de 20 bar de pressão.', 'sem_foto.webp', 2, 210.00, 429.00, 28, 6, 'Sim', 'Sim', NOW()),
('Liquidificador Turbo 1200W Inox Britânia', 'Jarra com capacidade de 3 litros, 12 velocidades e lâminas integradas de inox.', 'sem_foto.webp', 2, 75.00, 159.00, 50, 15, 'Sim', 'Sim', NOW()),
('Smart TV 55" 4K UHD Crystal Samsung', 'Resolução 4K real, design sem bordas, comando de voz e Gaming Hub integrado.', 'sem_foto.webp', 3, 1620.00, 2799.00, 22, 6, 'Sim', 'Sim', NOW()),
('Smart TV 65" 4K OLED LG Evo', 'Painel OLED com pixels que se autoiluminam, taxa de 120Hz e som Dolby Atmos.', 'sem_foto.webp', 3, 3800.00, 5990.00, 8, 3, 'Sim', 'Sim', NOW()),
('Soundbar 2.1 Canais 300W Bluetooth Samsung', 'Subwoofer sem fio potente, conexão Bluetooth e modo de aprimoramento de voz.', 'sem_foto.webp', 3, 490.00, 899.00, 19, 5, 'Sim', 'Sim', NOW()),
('Ar-condicionado Split Inverter 12.000 BTUs LG', 'Dual Inverter, economiza até 70% de energia, super silencioso com Wi-Fi ThinQ.', 'sem_foto.webp', 4, 1580.00, 2650.00, 15, 5, 'Sim', 'Sim', NOW()),
('Ventilador de Coluna 40cm Turbo Mondial', 'Ventilador silencioso com 8 pás e ajuste de altura telescópico.', 'sem_foto.webp', 4, 98.00, 189.00, 7, 12, 'Sim', 'Sim', NOW()),
('Smartphone Galaxy A55 5G 128GB Samsung', 'Tela Super AMOLED 120Hz, câmera tripla de 50MP e resistência contra água IP67.', 'sem_foto.webp', 5, 1250.00, 1999.00, 25, 6, 'Sim', 'Sim', NOW());

-- 9. CLIENTES LOJISTAS E CONSUMIDORES
INSERT INTO clientes (nome, email, telefone, whatsapp, tipo_pessoa, cpf_cnpj, cep, endereco, numero, bairro, cidade, estado, foto, ativo, data_cadastro, limite_credito, saldo_devedor) VALUES
('Eletro Magazine Silva & Cia Ltda', 'contato@eletromagazine.com.br', '(11) 3210-9988', '(11) 99888-7711', 'PJ', '12.345.678/0001-90', '01400-000', 'Rua das Lojas', '250', 'Centro', 'Guarulhos', 'SP', 'sem_foto.webp', 'Sim', NOW(), 50000.00, 0.00),
('Varejão dos Eletros Bom Preço', 'compras@varejaobompreco.com.br', '(11) 3456-1122', '(11) 98777-6622', 'PJ', '23.456.789/0001-01', '01400-000', 'Av. do Comércio', '1100', 'Jardins', 'São Paulo', 'SP', 'sem_foto.webp', 'Sim', NOW(), 35000.00, 0.00),
('Construtora & Engenharia Horizonte', 'suprimentos@horizonte.eng.br', '(11) 2233-4455', '(11) 97666-5533', 'PJ', '34.567.890/0001-12', '01400-000', 'Rua Bela Cintra', '800', 'Consolação', 'São Paulo', 'SP', 'sem_foto.webp', 'Sim', NOW(), 80000.00, 0.00),
('Carlos Eduardo Mendes', 'carlos.mendes@gmail.com', '(11) 99111-2233', '(11) 99111-2233', 'PF', '111.222.333-44', '01400-000', 'Alameda dos Anapurus', '45', 'Moema', 'São Paulo', 'SP', 'sem_foto.webp', 'Sim', NOW(), 10000.00, 0.00),
('Mariana Costa Ferreira', 'mariana.costa@hotmail.com', '(11) 98222-3344', '(11) 98222-3344', 'PF', '222.333.444-55', '01400-000', 'Rua Pamplona', '720', 'Jardim Paulista', 'São Paulo', 'SP', 'sem_foto.webp', 'Sim', NOW(), 12000.00, 0.00),
('Supermercado e Variedades Santos', 'financeiro@supermercadosantos.com', '(13) 3344-5566', '(13) 99555-4433', 'PJ', '45.678.901/0001-23', '01400-000', 'Av. Ana Costa', '300', 'Gonzaga', 'Santos', 'SP', 'sem_foto.webp', 'Sim', NOW(), 40000.00, 0.00);

-- 10. RECEBIMENTOS SIMULADOS (Recebidos, A Receber e Atrasados)
INSERT INTO recebimentos (descricao, valor, subtotal, data_lancamento, data_vencimento, data_pagamento, status, cliente, forma_pagamento, plano_conta, centro_custo, ativo, alertado) VALUES
('Venda Faturada 10x TVs 55 - Eletro Magazine', 27990.00, 27990.00, CURDATE(), CURDATE(), CURDATE(), 'Pago', 1, 2, 2, 1, 'Sim', 'Não'),
('Venda Balcão 2x Geladeiras Frost Free', 7780.00, 7780.00, CURDATE(), CURDATE(), CURDATE(), 'Pago', 2, 2, 1, 2, 'Sim', 'Não'),
('Venda 5x Air Fryer Mondial - Cliente Balcão', 1745.00, 1745.00, CURDATE(), CURDATE(), CURDATE(), 'Pago', 4, 1, 1, 2, 'Sim', 'Não'),
('Parcela 2/3 Lote Climatizadores e Splits', 13250.00, 13250.00, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 10 DAY), NULL, 'Pendente', 3, 6, 2, 1, 'Sim', 'Não'),
('Parcela 3/3 Lote Climatizadores e Splits', 13250.00, 13250.00, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 20 DAY), NULL, 'Pendente', 3, 6, 2, 1, 'Sim', 'Não'),
('Faturamento Quinzena - Supermercado Santos', 9850.00, 9850.00, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 12 DAY), NULL, 'Pendente', 6, 6, 2, 1, 'Sim', 'Não'),
('Faturamento Lote 4x Lavadoras - Em Atraso', 8760.00, 8760.00, DATE_SUB(CURDATE(), INTERVAL 30 DAY), DATE_SUB(CURDATE(), INTERVAL 7 DAY), NULL, 'Vencida', 2, 6, 2, 1, 'Sim', 'Não'),
('Manutenção e Suprimentos - Varejão Bom Preço', 1450.00, 1450.00, DATE_SUB(CURDATE(), INTERVAL 45 DAY), DATE_SUB(CURDATE(), INTERVAL 15 DAY), NULL, 'Vencida', 2, 6, 2, 1, 'Sim', 'Não');

-- 11. DESPESAS SIMULADAS (Pagas e A Pagar)
INSERT INTO despesas (descricao, valor, subtotal, data_lancamento, data_vencimento, data_pagamento, status, fornecedor, forma_pagamento, plano_conta, centro_custo, ativo) VALUES
('Aluguel Galpão Logístico - CD Central', 8500.00, 8500.00, CURDATE(), CURDATE(), CURDATE(), 'Pago', 1, 2, 4, 1, 'Sim'),
('Conta de Energia Elétrica - Enel SP', 2150.00, 2150.00, CURDATE(), CURDATE(), CURDATE(), 'Pago', 1, 2, 5, 1, 'Sim'),
('Folha de Pagamento Funcionários - Competência', 14200.00, 14200.00, CURDATE(), CURDATE(), CURDATE(), 'Pago', 1, 2, 6, 3, 'Sim'),
('Fatura Frete Transportadora TransEletro', 3800.00, 3800.00, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 8 DAY), NULL, 'Pendente', 2, 6, 7, 4, 'Sim'),
('Aquisição Lote 50x Air Fryers Mondial', 9250.00, 9250.00, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 18 DAY), NULL, 'Pendente', 2, 6, 3, 1, 'Sim');
