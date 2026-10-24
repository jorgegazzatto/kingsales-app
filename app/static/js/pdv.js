let carrinho = [];
let categoriaSelecionada = '';
let timerBusca = null;

document.addEventListener('DOMContentLoaded', function () {
    aplicarDataHoje('data_venda');
    aplicarSelect2('cliente_venda');

    iniciarEventosFixos();
    carregarCategorias();
    carregarProdutos();
    carregarFormasPagamento();
    atualizarResumoVenda();
});


// =====================================
// INICIALIZAÇÃO
// =====================================
function iniciarEventosFixos() {
    const busca = document.getElementById('buscaProduto');
    const filtroEstoque = document.getElementById('filtroEstoque');
    const desconto = document.getElementById('desconto_venda');
    const acrescimo = document.getElementById('acrescimo_venda');
    const btnLimpar = document.getElementById('btnLimparVenda');
    const btnAtualizar = document.getElementById('btnAtualizarProdutos');
    const btnFinalizar = document.getElementById('btnFinalizarVenda');

    if (busca) {
        busca.addEventListener('input', function () {
            clearTimeout(timerBusca);
            timerBusca = setTimeout(() => {
                carregarProdutos();
            }, 300);
        });
    }

    if (filtroEstoque) {
        filtroEstoque.addEventListener('change', function () {
            carregarProdutos();
        });
    }

    if (desconto) {
        desconto.addEventListener('input', function () {
            atualizarResumoVenda();
        });
    }

    if (acrescimo) {
        acrescimo.addEventListener('input', function () {
            atualizarResumoVenda();
        });
    }

    if (btnAtualizar) {
        btnAtualizar.addEventListener('click', function () {
            carregarCategorias();
            carregarProdutos();
            carregarFormasPagamento();
        });
    }

    if (btnLimpar) {
        btnLimpar.addEventListener('click', async function () {
            const confirmacao = await confirmarAcao({
                titulo: 'Limpar venda?',
                texto: 'Todos os itens do carrinho serão removidos.',
                textoConfirmar: 'Sim, limpar',
                textoCancelar: 'Cancelar'
            });

            if (!confirmacao.isConfirmed) return;

            carrinho = [];
            renderizarCarrinho();

            const desconto = document.getElementById('desconto_venda');
            const acrescimo = document.getElementById('acrescimo_venda');
            const observacoes = document.getElementById('observacoes_venda');
            const cliente = document.getElementById('cliente_venda');
            const formaPagamento = document.getElementById('forma_pagamento_venda');
            const busca = document.getElementById('buscaProduto');

            if (desconto) desconto.value = '0,00';
            if (acrescimo) acrescimo.value = '0,00';
            if (observacoes) observacoes.value = '';
            if (busca) busca.value = '';
            if (formaPagamento) formaPagamento.value = '';

            if (cliente) {
                cliente.value = '';
                $('#cliente_venda').trigger('change');
            }

            categoriaSelecionada = '';
            marcarCategoriaAtiva('');

            atualizarResumoVenda();
            mensagemSucesso('Venda limpa com sucesso.');
        });
    }

    if (btnFinalizar) {
        btnFinalizar.addEventListener('click', async function () {
            if (carrinho.length === 0) {
                mensagemAviso('Adicione ao menos um produto para continuar.');
                return;
            }

            const formaPagamento = document.getElementById('forma_pagamento_venda')?.value || '';
            const cliente = document.getElementById('cliente_venda')?.value || '';
            const dataVenda = document.getElementById('data_venda')?.value || '';
            const observacoes = document.getElementById('observacoes_venda')?.value || '';
            const desconto = valorParaNumero(document.getElementById('desconto_venda')?.value || '0');
            const acrescimo = valorParaNumero(document.getElementById('acrescimo_venda')?.value || '0');

            if (!formaPagamento) {
                mensagemAviso('Selecione a forma de pagamento.');
                return;
            }

            if (!dataVenda) {
                mensagemAviso('Informe a data da venda.');
                return;
            }

            const confirmacao = await confirmarAcao({
                titulo: 'Finalizar venda?',
                texto: 'Confirma a finalização desta venda?',
                textoConfirmar: 'Sim, finalizar',
                textoCancelar: 'Cancelar'
            });

            if (!confirmacao.isConfirmed) return;

            try {
                mostrarLoading('Finalizando venda...');

                const payload = {
                    cliente: cliente || null,
                    forma_pagamento: formaPagamento,
                    data_venda: dataVenda,
                    observacoes: observacoes,
                    desconto: desconto,
                    acrescimo: acrescimo,
                    itens: carrinho.map(item => ({
                        id: item.id,
                        quantidade: item.quantidade
                    }))
                };

                const response = await fetch('/pdv/finalizar-venda', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });

                const resultado = await response.json();
                fecharLoading();

                if (!response.ok || resultado.status !== 'sucesso') {
                    mensagemErro(resultado.mensagem || 'Erro ao finalizar venda.');
                    return;
                }

                await mensagemSucesso(`Venda #${resultado.venda_id} finalizada com sucesso.`);

                const imprimir = await confirmarAcao({
                    titulo: 'Imprimir comprovante?',
                    texto: `Deseja imprimir o comprovante da venda #${resultado.venda_id}?`,
                    textoConfirmar: 'Sim, imprimir',
                    textoCancelar: 'Não'
                });

                if (imprimir.isConfirmed) {
                    abrirComprovanteVenda(resultado.venda_id);
                }

                carrinho = [];
                renderizarCarrinho();

                const descontoInput = document.getElementById('desconto_venda');
                const acrescimoInput = document.getElementById('acrescimo_venda');
                const observacoesInput = document.getElementById('observacoes_venda');
                const clienteInput = document.getElementById('cliente_venda');
                const formaPagamentoInput = document.getElementById('forma_pagamento_venda');
                const buscaInput = document.getElementById('buscaProduto');

                if (descontoInput) descontoInput.value = '0,00';
                if (acrescimoInput) acrescimoInput.value = '0,00';
                if (observacoesInput) observacoesInput.value = '';
                if (formaPagamentoInput) formaPagamentoInput.value = '';
                if (buscaInput) buscaInput.value = '';

                if (clienteInput) {
                    clienteInput.value = '';
                    $('#cliente_venda').trigger('change');
                }

                atualizarResumoVenda();
                carregarProdutos();

            } catch (error) {
                fecharLoading();
                mensagemErro('Erro de comunicação ao finalizar venda.');
            }
        });
    }

    document.addEventListener('click', function (e) {
        const botaoCategoria = e.target.closest('.pdv-categoria-item');
        if (botaoCategoria) {
            categoriaSelecionada = botaoCategoria.dataset.id || '';
            marcarCategoriaAtiva(categoriaSelecionada);
            carregarProdutos();
            return;
        }

        const botaoAdicionar = e.target.closest('.btnAdicionarProduto');
        if (botaoAdicionar) {
            adicionarProdutoDoCard(botaoAdicionar);
            return;
        }

        const btnMais = e.target.closest('.btnMaisQtd');
        if (btnMais) {
            alterarQuantidade(btnMais.dataset.id, 1);
            return;
        }

        const btnMenos = e.target.closest('.btnMenosQtd');
        if (btnMenos) {
            alterarQuantidade(btnMenos.dataset.id, -1);
            return;
        }

        const btnRemover = e.target.closest('.btnRemoverItem');
        if (btnRemover) {
            removerItemCarrinho(btnRemover.dataset.id);
        }
    });
}


// =====================================
// CATEGORIAS
// =====================================
async function carregarCategorias() {
    const container = document.getElementById('listaCategorias');
    if (!container) return;

    try {
        const response = await fetch('/pdv/listar-categorias');
        const dados = await response.json();

        if (!response.ok) {
            throw new Error(dados.mensagem || 'Erro ao carregar categorias.');
        }

        let html = `
            <button type="button" class="pdv-categoria-item ${categoriaSelecionada === '' ? 'active' : ''}" data-id="">
                <div class="pdv-categoria-foto">
                    <img src="/static/img/todas.png" alt="Todas">
                </div>
                <span>Todas</span>
            </button>
        `;

        dados.forEach(item => {
            const foto = item.foto ? `/static/img/categorias/${item.foto}` : '/static/img/sem_foto_produto.png';

            html += `
                <button type="button" class="pdv-categoria-item ${String(categoriaSelecionada) === String(item.id) ? 'active' : ''}" data-id="${item.id}">
                    <div class="pdv-categoria-foto">
                        <img src="${foto}" alt="${escapeHtml(item.nome)}" onerror="this.src='/static/img/sem_foto_produto.png'">
                    </div>
                    <span>${escapeHtml(item.nome)}</span>
                </button>
            `;
        });

        container.innerHTML = html;

    } catch (error) {
        container.innerHTML = `
            <div class="text-danger small">
                Erro ao carregar categorias.
            </div>
        `;
    }
}

function marcarCategoriaAtiva(id) {
    document.querySelectorAll('.pdv-categoria-item').forEach(item => {
        item.classList.remove('active');

        const itemId = item.dataset.id || '';
        if (String(itemId) === String(id)) {
            item.classList.add('active');
        }
    });
}


// =====================================
// PRODUTOS
// =====================================
async function carregarProdutos() {
    const container = document.getElementById('listaProdutos');
    if (!container) return;

    const busca = document.getElementById('buscaProduto')?.value?.trim() || '';
    const filtroEstoque = document.getElementById('filtroEstoque')?.value || '';

    try {
        container.innerHTML = `
            <div class="col-12">
                <div class="text-center py-5 text-muted">
                    <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                    Carregando produtos...
                </div>
            </div>
        `;

        const params = new URLSearchParams();

        if (categoriaSelecionada) params.append('categoria_id', categoriaSelecionada);
        if (busca) params.append('busca', busca);
        if (filtroEstoque) params.append('filtro_estoque', filtroEstoque);

        const response = await fetch(`/pdv/listar-produtos?${params.toString()}`);
        const dados = await response.json();

        if (!response.ok) {
            throw new Error(dados.mensagem || 'Erro ao carregar produtos.');
        }

        if (!dados.length) {
            container.innerHTML = `
                <div class="col-12">
                    <div class="text-center py-5 text-muted">
                        <i class="bi bi-box fs-1 d-block mb-2"></i>
                        <div class="fw-semibold">Nenhum produto encontrado</div>
                        <small>Tente mudar a categoria ou a busca.</small>
                    </div>
                </div>
            `;
            return;
        }

        let html = '';

        dados.forEach(item => {
            const foto = item.foto ? `/static/img/produtos/${item.foto}` : '/static/img/sem_foto_produtos.png';

            let badge = '';
            let botao = `
                <button type="button" class="btn btn-sm btn-primary btnAdicionarProduto">
                    <i class="bi bi-cart-plus me-1"></i> Adicionar
                </button>
            `;

            if (item.controlar_estoque === 'Sim') {
                if (item.situacao_estoque === 'sem_estoque') {
                    badge = `<span class="badge bg-danger">Sem Estoque</span>`;
                    botao = `
                        <button type="button" class="btn btn-sm btn-outline-secondary" disabled>
                            <i class="bi bi-x-circle me-1"></i> Indisponível
                        </button>
                    `;
                } else if (item.situacao_estoque === 'baixo_estoque') {
                    badge = `<span class="badge bg-warning text-dark">Baixo Estoque</span>`;
                } else {
                    badge = `<span class="badge bg-success">Disponível</span>`;
                }
            } else {
                badge = `<span class="badge bg-info text-dark">Sem Controle</span>`;
            }

            html += `
                <div class="col-md-4 col-sm-6 col-6 produto-item"
                    data-id="${item.id}"
                    data-nome="${escapeHtml(item.nome)}"
                    data-categoria="${item.categoria_id || ''}"
                    data-valor="${Number(item.valor_venda || 0)}"
                    data-estoque="${Number(item.estoque || 0)}"
                    data-nivel-minimo="${Number(item.nivel_minimo_estoque || 0)}"
                    data-controlar-estoque="${item.controlar_estoque || 'Sim'}"
                    data-foto="${escapeHtml(item.foto || '')}">

                    <div class="card pdv-produto-card h-100">
                        <div class="pdv-produto-img-box">
                            <img src="${foto}" class="pdv-produto-img" alt="${escapeHtml(item.nome)}" onerror="this.src='/static/img/sem_foto_produto.png'">
                        </div>

                        <div class="card-body p-2">
                            <div class="d-flex justify-content-between align-items-start gap-2 mb-1">
                                <div class="pdv-produto-nome">${escapeHtml(item.nome)}</div>
                                ${badge}
                            </div>

                            <div class="pdv-produto-categoria text-muted small">
                                ${escapeHtml(item.categoria_nome || 'Sem categoria')}
                            </div>

                            <div class="mt-2 mb-2">
                                <div class="fw-bold text-success">R$ ${formatarValorBR(Number(item.valor_venda || 0))}</div>
                                <small class="text-muted">
                                    Estoque: ${formatarNumeroIntOuDecimal(Number(item.estoque || 0))}
                                </small>
                            </div>

                            <div class="d-grid">
                                ${botao}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;

    } catch (error) {
        container.innerHTML = `
            <div class="col-12">
                <div class="text-center py-5 text-danger">
                    Erro ao carregar produtos.
                </div>
            </div>
        `;
    }
}

function adicionarProdutoDoCard(botaoAdicionar) {
    const card = botaoAdicionar.closest('.produto-item');
    if (!card) return;

    const id = String(card.dataset.id || '');
    const nome = card.dataset.nome || '';
    const valor = parseFloat(card.dataset.valor || '0');
    const foto = card.dataset.foto || '';
    const estoque = parseFloat(card.dataset.estoque || '0');
    const controlarEstoque = card.dataset.controlarEstoque || 'Sim';

    if (controlarEstoque === 'Sim' && estoque <= 0) {
        mensagemAviso('Este produto está sem estoque.');
        return;
    }

    adicionarAoCarrinho({
        id,
        nome,
        valor,
        foto,
        estoque,
        controlarEstoque,
        quantidade: 1
    });
}


// =====================================
// FORMAS DE PAGAMENTO
// =====================================
async function carregarFormasPagamento() {
    const select = document.getElementById('forma_pagamento_venda');
    if (!select) return;

    try {
        const response = await fetch('/pdv/listar-formas-pagamento');
        const dados = await response.json();

        if (!response.ok) {
            throw new Error(dados.mensagem || 'Erro ao carregar formas de pagamento.');
        }

        let html = `<option value="">Selecione</option>`;

        dados.forEach(item => {
            html += `<option value="${item.id}">${escapeHtml(item.nome)}</option>`;
        });

        select.innerHTML = html;

    } catch (error) {
        select.innerHTML = `<option value="">Erro ao carregar</option>`;
    }
}


// =====================================
// CARRINHO
// =====================================
function adicionarAoCarrinho(produto) {
    const itemExistente = carrinho.find(item => item.id === produto.id);

    if (itemExistente) {
        if (
            itemExistente.controlarEstoque === 'Sim' &&
            itemExistente.quantidade >= itemExistente.estoque
        ) {
            mensagemAviso('Quantidade maior que o estoque disponível.');
            return;
        }

        itemExistente.quantidade += 1;
    } else {
        carrinho.push(produto);
    }

    renderizarCarrinho();
    atualizarResumoVenda();
}

function alterarQuantidade(id, variacao) {
    const item = carrinho.find(prod => prod.id === id);
    if (!item) return;

    const novaQuantidade = item.quantidade + variacao;

    if (novaQuantidade <= 0) {
        removerItemCarrinho(id);
        return;
    }

    if (item.controlarEstoque === 'Sim' && novaQuantidade > item.estoque) {
        mensagemAviso('Quantidade maior que o estoque disponível.');
        return;
    }

    item.quantidade = novaQuantidade;

    renderizarCarrinho();
    atualizarResumoVenda();
}

function removerItemCarrinho(id) {
    carrinho = carrinho.filter(item => item.id !== id);
    renderizarCarrinho();
    atualizarResumoVenda();
}

function renderizarCarrinho() {
    const lista = document.getElementById('listaCarrinho');
    if (!lista) return;

    if (carrinho.length === 0) {
        lista.innerHTML = `
            <div class="pdv-item-empty text-center text-muted py-5">
                <i class="bi bi-cart3 fs-1 d-block mb-2"></i>
                <div class="fw-semibold">Nenhum produto adicionado</div>
                <small>Os itens da venda aparecerão aqui</small>
            </div>
        `;
        return;
    }

    let html = '';

    carrinho.forEach(item => {
        const subtotal = item.quantidade * item.valor;

        html += `
            <div class="pdv-item">
                <div class="pdv-item-top">
                    <div>
                        <div class="pdv-item-nome">${escapeHtml(item.nome)}</div>
                        <small class="text-muted">R$ ${formatarValorBR(item.valor)} cada</small>
                    </div>

                    <button type="button" class="btn btn-sm btn-outline-danger btnRemoverItem" data-id="${item.id}">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>

                <div class="d-flex justify-content-between align-items-center mt-2 gap-2">
                    <div class="input-group input-group-sm pdv-qtd-box">
                        <button class="btn btn-outline-secondary btnMenosQtd" type="button" data-id="${item.id}">-</button>
                        <input type="text" class="form-control text-center" value="${formatarNumeroIntOuDecimal(item.quantidade)}" readonly>
                        <button class="btn btn-outline-secondary btnMaisQtd" type="button" data-id="${item.id}">+</button>
                    </div>

                    <div class="fw-semibold text-success">R$ ${formatarValorBR(subtotal)}</div>
                </div>
            </div>
        `;
    });

    lista.innerHTML = html;
}


// =====================================
// TOTAIS
// =====================================
function atualizarResumoVenda() {
    const subtotal = carrinho.reduce((total, item) => {
        return total + (item.quantidade * item.valor);
    }, 0);

    const desconto = valorParaNumero(document.getElementById('desconto_venda')?.value || '0');
    const acrescimo = valorParaNumero(document.getElementById('acrescimo_venda')?.value || '0');
    const total = subtotal - desconto + acrescimo;
    const qtdItens = carrinho.reduce((total, item) => total + Number(item.quantidade || 0), 0);

    const subtotalEl = document.getElementById('subtotalVenda');
    const descontoEl = document.getElementById('valorDescontoVenda');
    const acrescimoEl = document.getElementById('valorAcrescimoVenda');
    const totalEl = document.getElementById('totalVenda');
    const qtdEl = document.getElementById('qtdItensCarrinho');

    if (subtotalEl) subtotalEl.textContent = `R$ ${formatarValorBR(subtotal)}`;
    if (descontoEl) descontoEl.textContent = `R$ ${formatarValorBR(desconto)}`;
    if (acrescimoEl) acrescimoEl.textContent = `R$ ${formatarValorBR(acrescimo)}`;
    if (totalEl) totalEl.textContent = `R$ ${formatarValorBR(total < 0 ? 0 : total)}`;
    if (qtdEl) qtdEl.textContent = `${formatarNumeroIntOuDecimal(qtdItens)} item(s)`;
}


// =====================================
// AUXILIARES
// =====================================
function escapeHtml(texto) {
    return String(texto ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}



function abrirComprovanteVenda(vendaId) {
    const largura = 420;
    const altura = 700;

    const esquerda = (window.screen.width / 2) - (largura / 2);
    const topo = (window.screen.height / 2) - (altura / 2);

    const popup = window.open(
        `/pdv/comprovante/${vendaId}?print=1`,
        'comprovanteVenda',
        `width=${largura},height=${altura},left=${esquerda},top=${topo},scrollbars=yes,resizable=yes`
    );

    if (!popup) {
        mensagemAviso('O navegador bloqueou a popup do comprovante. Libere popups para este sistema.');
        return;
    }

    popup.focus();
}