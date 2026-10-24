function valorParaNumero(valor) {
    if (!valor) return 0;

    return parseFloat(
        valor.replace(/\./g, '').replace(',', '.')
    ) || 0;
}

function formatarValorBR(valor) {
    return valor.toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function getDataHoje() {
    const hoje = new Date();
    const ano = hoje.getFullYear();
    const mes = String(hoje.getMonth() + 1).padStart(2, '0');
    const dia = String(hoje.getDate()).padStart(2, '0');

    return `${ano}-${mes}-${dia}`;
}


function aplicarDataHoje(id) {
    const campo = document.getElementById(id);
    if (campo && !campo.value) {
        campo.value = getDataHoje();
    }
}




// ===============================
// 🔢 VALORES
// ===============================
function valorParaNumero(valor) {
    if (!valor) return 0;

    return parseFloat(
        valor.replace(/\./g, '').replace(',', '.')
    ) || 0;
}

function formatarValorBR(valor) {
    return Number(valor || 0).toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// ===============================
// 📅 DATAS
// ===============================
function formatarDataISO(data) {
    const ano = data.getFullYear();
    const mes = String(data.getMonth() + 1).padStart(2, '0');
    const dia = String(data.getDate()).padStart(2, '0');

    return `${ano}-${mes}-${dia}`;
}

function getDataHoje() {
    return formatarDataISO(new Date());
}

function getDataOntem() {
    const data = new Date();
    data.setDate(data.getDate() - 1);
    return formatarDataISO(data);
}

function getDataAmanha() {
    const data = new Date();
    data.setDate(data.getDate() + 1);
    return formatarDataISO(data);
}

function getDataInicioMes() {
    const hoje = new Date();
    const inicio = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
    return formatarDataISO(inicio);
}

function getDataFimMes() {
    const hoje = new Date();
    const fim = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0);
    return formatarDataISO(fim);
}

// ===============================
// ⚙️ APLICAÇÃO EM CAMPOS
// ===============================
function aplicarDataHoje(id) {
    const campo = document.getElementById(id);
    if (campo && !campo.value) {
        campo.value = getDataHoje();
    }
}

function aplicarPeriodo(inicioId, fimId, dataInicio, dataFim) {
    const inicio = document.getElementById(inicioId);
    const fim = document.getElementById(fimId);

    if (inicio) inicio.value = dataInicio;
    if (fim) fim.value = dataFim;
}

// ===============================
// 🚀 ATALHOS PRONTOS
// ===============================
function periodoHoje(inicioId, fimId) {
    const hoje = getDataHoje();
    aplicarPeriodo(inicioId, fimId, hoje, hoje);
}

function periodoOntem(inicioId, fimId) {
    const ontem = getDataOntem();
    aplicarPeriodo(inicioId, fimId, ontem, ontem);
}

function periodoMesAtual(inicioId, fimId) {
    aplicarPeriodo(inicioId, fimId, getDataInicioMes(), getDataFimMes());
}


function periodoSemanaAtual(inicioId, fimId) {
    const hoje = new Date();
    const diaSemana = hoje.getDay();

    const inicio = new Date(hoje);
    inicio.setDate(hoje.getDate() - diaSemana);

    const fim = new Date(inicio);
    fim.setDate(inicio.getDate() + 6);

    aplicarPeriodo(inicioId, fimId, formatarDataISO(inicio), formatarDataISO(fim));
}


function aplicarSelect2(id) {
    const elemento = $('#' + id);

    if (!elemento.length) return;

    if (elemento.hasClass('select2-hidden-accessible')) {
        elemento.select2('destroy');
    }

    const modalPai = elemento.closest('.modal');
    const offcanvasPai = elemento.closest('.offcanvas');

    let config = {
        width: '100%',
        theme: 'bootstrap-5',
        placeholder: 'Selecione uma opção',
        allowClear: true
    };

    if (modalPai.length) {
        config.dropdownParent = modalPai;
    } else if (offcanvasPai.length) {
        config.dropdownParent = offcanvasPai;
    }

    elemento.select2(config);
}



function formatarNumeroIntOuDecimal(valor) {
    const numero = Number(valor || 0);

    // se for inteiro, mostra sem casas decimais
    if (Number.isInteger(numero)) {
        return numero.toString();
    }

    // se não for, mantém padrão BR
    return numero.toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}