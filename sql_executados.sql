CREATE TABLE usuarios (
    
    id INT NOT NULL AUTO_INCREMENT,
    
    nome VARCHAR(100) NULL,
    telefone VARCHAR(20) NULL,
    email VARCHAR(100) NULL,
    senha VARCHAR(255) NULL,
    cpf VARCHAR(14) NULL,
    
    endereco VARCHAR(200) NULL,
    numero VARCHAR(10) NULL,
    complemento VARCHAR(100) NULL,
    bairro VARCHAR(100) NULL,
    cidade VARCHAR(100) NULL,
    estado CHAR(2) NULL,
    cep VARCHAR(10) NULL,
    
    foto VARCHAR(255) NULL,
    nivel VARCHAR(50) DEFAULT 'comum',
    ativo VARCHAR(5) NULL,
    
    data_cadastro DATETIME DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    
    assinatura VARCHAR(100) NULL,

    PRIMARY KEY (id)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;





CREATE TABLE config (
    id INT AUTO_INCREMENT PRIMARY KEY,

    nome_sistema VARCHAR(150) NULL,
    email_sistema VARCHAR(150) NULL,
    telefone_sistema VARCHAR(20) NULL,
    endereco_sistema VARCHAR(255) NULL,

    logo VARCHAR(255) NULL,
    icone VARCHAR(255) NULL,

    cor_primaria VARCHAR(20) NULL,
    cor_secundaria VARCHAR(20) NULL
);


CREATE TABLE cargos (
    id INT NOT NULL AUTO_INCREMENT,
    nome VARCHAR(100) NULL,
    PRIMARY KEY (id)
);


CREATE TABLE usuarios_permissoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    menu_id VARCHAR(100) NOT NULL,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY unique_usuario_menu (usuario_id, menu_id),
    INDEX idx_usuario (usuario_id),
    INDEX idx_menu (menu_id)
);


CREATE TABLE usuarios_acoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    acao VARCHAR(50) NOT NULL,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY unique_usuario_acao (usuario_id, acao),
    INDEX idx_usuario (usuario_id),
    INDEX idx_acao (acao)
);




CREATE TABLE logs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    empresa INT NOT NULL DEFAULT 0,
    usuario_id INT NOT NULL DEFAULT 0,

    acao ENUM('login', 'logout', 'inserir', 'editar', 'excluir') NOT NULL,

    entidade VARCHAR(50) NULL,
    registro_id BIGINT NULL,

    descricao VARCHAR(255) NULL,
    rota VARCHAR(120) NULL,

    ip VARCHAR(45) NULL,
    user_agent VARCHAR(255) NULL,

    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    INDEX idx_empresa (empresa),
    INDEX idx_usuario (usuario_id),
    INDEX idx_acao (acao),
    INDEX idx_entidade (entidade),
    INDEX idx_registro (registro_id),
    INDEX idx_data (criado_em)
);



ALTER TABLE config
ADD COLUMN smtp_host VARCHAR(120) COLLATE utf8mb3_general_ci NULL,
ADD COLUMN smtp_senha VARCHAR(255) COLLATE utf8mb3_general_ci NULL,
ADD COLUMN smtp_porta INT NULL,
ADD COLUMN smtp_seguranca VARCHAR(10) COLLATE utf8mb3_general_ci NULL,
ADD COLUMN api_whatsapp VARCHAR(100) COLLATE utf8mb3_general_ci NULL,
ADD COLUMN token_whatsapp TEXT COLLATE utf8mb3_general_ci NULL,
ADD COLUMN instancia_whatsapp VARCHAR(150) COLLATE utf8mb3_general_ci NULL,
ADD COLUMN url_api VARCHAR(255) COLLATE utf8mb3_general_ci NULL,
ADD COLUMN api_ia VARCHAR(50) COLLATE utf8mb3_general_ci NULL,
ADD COLUMN token_ia VARCHAR(255) COLLATE utf8mb3_general_ci NULL,
ADD COLUMN dias_excluir_logs INT NULL,
ADD COLUMN rel_html_pdf VARCHAR(5) NULL;


ALTER TABLE usuarios 
ADD COLUMN token_recuperacao VARCHAR(255),
ADD COLUMN token_expira DATETIME;




CREATE TABLE clientes (
    id INT AUTO_INCREMENT PRIMARY KEY,

    nome VARCHAR(150) NOT NULL,
    email VARCHAR(150),
    telefone VARCHAR(20),
    whatsapp VARCHAR(20),

    tipo_pessoa VARCHAR(20),
    cpf_cnpj VARCHAR(20),

    data_nascimento DATE,
    profissao VARCHAR(100),

    -- ENDEREÇO
    cep VARCHAR(10),
    endereco VARCHAR(255),
    numero VARCHAR(20),
    complemento VARCHAR(100),
    bairro VARCHAR(100),
    cidade VARCHAR(100),
    estado VARCHAR(2),

    -- VISUAL
    foto VARCHAR(255),

    -- CONTROLE
    ativo VARCHAR(5),
    observacoes TEXT,
    data_cadastro DATETIME,

    -- FINANCEIRO
    limite_credito DECIMAL(10,2),
    saldo_devedor DECIMAL(10,2),
    dia_vencimento_padrao INT,
    forma_pagamento_padrao VARCHAR(50),
    score_credito INT,

    -- CONTROLE INTERNO
    usuario_cadastro INT,

    INDEX (nome),
    INDEX (cpf_cnpj)
);





CREATE TABLE frequencias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(50) NOT NULL,
    dias INT NOT NULL,
    ativo ENUM('Sim', 'Não') DEFAULT 'Sim'
);

CREATE TABLE plano_contas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    tipo ENUM('Receita', 'Despesa') NOT NULL,
    ativo ENUM('Sim', 'Não') DEFAULT 'Sim'
);



CREATE TABLE formas_pagamento (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    taxa DECIMAL(10,2) NULL,
    desconto DECIMAL(10,2) NULL,
    ativo ENUM('Sim', 'Não') DEFAULT 'Sim'
);


CREATE TABLE fornecedores (
    id INT AUTO_INCREMENT PRIMARY KEY,

    nome VARCHAR(150) NOT NULL,
    telefone VARCHAR(20),
    email VARCHAR(100),

    -- DOCUMENTO
    cpf_cnpj VARCHAR(20),

    -- ENDEREÇO
    cep VARCHAR(10),
    endereco VARCHAR(150),
    numero VARCHAR(10),
    complemento VARCHAR(100),
    bairro VARCHAR(100),
    cidade VARCHAR(100),
    estado VARCHAR(2),

    -- CONTROLE
    ativo ENUM('Sim', 'Não') DEFAULT 'Sim'
);



CREATE TABLE centros_custo (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    ativo ENUM('Sim', 'Não') DEFAULT 'Sim'
);


CREATE TABLE despesas (
    id INT AUTO_INCREMENT PRIMARY KEY,

    descricao VARCHAR(255) NOT NULL,

    valor DECIMAL(10,2) NOT NULL,
    desconto DECIMAL(10,2) DEFAULT 0,
    multa DECIMAL(10,2) DEFAULT 0,
    juros DECIMAL(10,2) DEFAULT 0,
    subtotal DECIMAL(10,2) DEFAULT 0,

    data_lancamento DATE,
    hora_lancamento TIME,
    data_vencimento DATE,
    data_pagamento DATE,

    status VARCHAR(50),

    -- RELACIONAMENTOS
    fornecedor INT,
    forma_pagamento INT,
    plano_conta INT,
    centro_custo INT,

    -- RECORRÊNCIA / PARCELAMENTO
    frequencia INT,
    recorrente VARCHAR(10),
    qtd_parcelas INT DEFAULT 1,
    parcela INT DEFAULT 1,
    id_ref INT,

    -- CONTROLE
    referencia VARCHAR(100),
    usuario_lancamento INT,
    usuario_pagamento INT,
    hora TIME NULL,

    observacoes TEXT,
    ativo ENUM('Sim', 'Não') DEFAULT 'Sim'
);




CREATE TABLE arquivos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    descricao VARCHAR(150) NULL,
    arquivo VARCHAR(255) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    tabela VARCHAR(50) NOT NULL,
    id_registro INT NOT NULL,
    usuario INT NULL,
    data DATE NULL,
    hora TIME NULL,
    ativo ENUM('Sim', 'Não') DEFAULT 'Sim'
);



ALTER TABLE despesas 
ADD COLUMN hora_lembrete TIME NULL,
ADD COLUMN alertado VARCHAR(5) NULL;

ALTER TABLE config 
ADD COLUMN hora_inicial_alerta TIME NULL,
ADD COLUMN hora_final_alerta TIME NULL;




CREATE TABLE recebimentos (
    id INT AUTO_INCREMENT PRIMARY KEY,

    descricao VARCHAR(255) NOT NULL,

    valor DECIMAL(10,2) NOT NULL,
    desconto DECIMAL(10,2) DEFAULT 0,
    multa DECIMAL(10,2) DEFAULT 0,
    juros DECIMAL(10,2) DEFAULT 0,
    subtotal DECIMAL(10,2) DEFAULT 0,

    data_lancamento DATE,
    hora_lancamento TIME,
    data_vencimento DATE,
    data_pagamento DATE, -- Representa a data que o cliente pagou

    status VARCHAR(50),

    -- RELACIONAMENTOS (Trocado fornecedor por cliente)
    cliente INT,
    forma_pagamento INT,
    plano_conta INT,
    centro_custo INT,

    -- RECORRÊNCIA / PARCELAMENTO
    frequencia INT,
    recorrente VARCHAR(10),
    qtd_parcelas INT DEFAULT 1,
    parcela INT DEFAULT 1,
    id_ref INT,

    -- CONTROLE
    referencia VARCHAR(100),
    usuario_lancamento INT,
    usuario_pagamento INT,
    id_residuo INT NULL,
    hora TIME NULL,
    
    -- ALERTAS E LEMBRETES (Já integrados)
    hora_lembrete TIME NULL,
    alertado VARCHAR(5) DEFAULT 'Não',

    observacoes TEXT,
    ativo ENUM('Sim', 'Não') DEFAULT 'Sim'
);



CREATE TABLE categorias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    foto VARCHAR(255) NULL,
    posicao INT DEFAULT 0,
    descricao TEXT NULL,
    ativo ENUM('Sim','Não') DEFAULT 'Sim',
    data_cadastro DATETIME DEFAULT CURRENT_TIMESTAMP,
    usuario_cadastro INT NULL
);




CREATE TABLE produtos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    descricao TEXT NULL,
    foto VARCHAR(255) NULL,
    categoria_id INT NULL,
    valor_compra DECIMAL(10,2) NULL,
    valor_venda DECIMAL(10,2) NULL,
    estoque DECIMAL(10,2) NULL,
    nivel_minimo_estoque DECIMAL(10,2) NULL,
    controlar_estoque ENUM('Sim','Não') DEFAULT 'Sim',
    ativo ENUM('Sim','Não') DEFAULT 'Sim',
    data_cadastro DATETIME NULL,
    usuario_cadastro INT NULL
);


CREATE TABLE movimentacoes_estoque (
    id INT AUTO_INCREMENT PRIMARY KEY,
    produto_id INT NOT NULL,
    tipo ENUM('Entrada','Saida') NOT NULL,
    quantidade DECIMAL(10,2) NOT NULL,
    estoque_anterior DECIMAL(10,2) NULL,
    estoque_atual DECIMAL(10,2) NULL,
    observacao TEXT NULL,
    data_movimentacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    usuario_id INT NULL
);




CREATE TABLE vendas (
    id INT AUTO_INCREMENT PRIMARY KEY,

    cliente INT NULL,

    valor DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    desconto DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    acrescimo DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    subtotal DECIMAL(10,2) NOT NULL DEFAULT 0.00,

    data_lancamento DATE NULL,
    hora_lancamento TIME NULL,

    forma_pagamento INT NULL,
    qtd_parcelas INT DEFAULT 1,

    referencia VARCHAR(100) NULL,
    id_ref INT NULL,

    observacoes TEXT NULL,
    status VARCHAR(50) NULL,

    usuario_lancamento INT NULL,
    usuario_pagamento INT NULL,

    ativo ENUM('Sim', 'Não') DEFAULT 'Sim'
);


CREATE TABLE itens_venda (
    id INT AUTO_INCREMENT PRIMARY KEY,
    venda_id INT NOT NULL,
    produto_id INT NOT NULL,
    quantidade DECIMAL(10,2) NULL,
    valor_unitario DECIMAL(10,2) NULL,
    subtotal DECIMAL(10,2) NULL,
    usuario_lancamento INT NULL
);


ALTER TABLE config
ADD COLUMN tipo_dados_pagamento VARCHAR(30) NULL,
ADD COLUMN dados_pagamento VARCHAR(255) NULL,
ADD COLUMN beneficiario VARCHAR(150) NULL;






