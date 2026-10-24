function somenteNumeros(valor) {
    return valor.replace(/\D/g, "");
}

// CPF: 000.000.000-00
function mascaraCPF(valor) {
    valor = somenteNumeros(valor).slice(0, 11);

    if (valor.length > 9) {
        valor = valor.replace(/(\d{3})(\d{3})(\d{3})(\d{1,2})/, "$1.$2.$3-$4");
    } else if (valor.length > 6) {
        valor = valor.replace(/(\d{3})(\d{3})(\d+)/, "$1.$2.$3");
    } else if (valor.length > 3) {
        valor = valor.replace(/(\d{3})(\d+)/, "$1.$2");
    }

    return valor;
}

// CNPJ: 00.000.000/0000-00
function mascaraCNPJ(valor) {
    valor = somenteNumeros(valor).slice(0, 14);

    if (valor.length > 12) {
        valor = valor.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{1,2})/, "$1.$2.$3/$4-$5");
    } else if (valor.length > 8) {
        valor = valor.replace(/(\d{2})(\d{3})(\d{3})(\d+)/, "$1.$2.$3/$4");
    } else if (valor.length > 5) {
        valor = valor.replace(/(\d{2})(\d{3})(\d+)/, "$1.$2.$3");
    } else if (valor.length > 2) {
        valor = valor.replace(/(\d{2})(\d+)/, "$1.$2");
    }

    return valor;
}

// CPF ou CNPJ dinâmico
function mascaraCpfCnpj(valor) {
    valor = somenteNumeros(valor);

    if (valor.length <= 11) {
        return mascaraCPF(valor);
    }

    return mascaraCNPJ(valor);
}

// CEP: 00000-000
function mascaraCEP(valor) {
    valor = somenteNumeros(valor).slice(0, 8);

    if (valor.length > 5) {
        valor = valor.replace(/(\d{5})(\d+)/, "$1-$2");
    }

    return valor;
}

// Telefone:
// (00) 0000-0000
// (00) 00000-0000
function mascaraTelefone(valor) {
    valor = somenteNumeros(valor).slice(0, 11);

    if (valor.length <= 10) {
        valor = valor.replace(/(\d{0,2})(\d{0,4})(\d{0,4})/, function (_, ddd, parte1, parte2) {
            let resultado = "";

            if (ddd) resultado += `(${ddd}`;
            if (ddd.length === 2) resultado += ") ";
            if (parte1) resultado += parte1;
            if (parte2) resultado += `-${parte2}`;

            return resultado;
        });
    } else {
        valor = valor.replace(/(\d{0,2})(\d{0,5})(\d{0,4})/, function (_, ddd, parte1, parte2) {
            let resultado = "";

            if (ddd) resultado += `(${ddd}`;
            if (ddd.length === 2) resultado += ") ";
            if (parte1) resultado += parte1;
            if (parte2) resultado += `-${parte2}`;

            return resultado;
        });
    }

    return valor;
}

// Data: dd/mm/aaaa
function mascaraData(valor) {
    valor = somenteNumeros(valor).slice(0, 8);

    if (valor.length > 4) {
        valor = valor.replace(/(\d{2})(\d{2})(\d{1,4})/, "$1/$2/$3");
    } else if (valor.length > 2) {
        valor = valor.replace(/(\d{2})(\d{1,2})/, "$1/$2");
    }

    return valor;
}

function mascaraDecimal(valor) {
    valor = valor.replace(/\D/g, "");

    if (valor.length === 0) return "";

    valor = (parseInt(valor) / 100).toFixed(2);

    return valor;
}

function aplicarMascaraDecimal(input) {
    input.value = mascaraDecimal(input.value);
}

// =========================
// MÁSCARA MONETÁRIA (2 casas)
// =========================
function mascaraValor(valor) {
    valor = valor.replace(/\D/g, '');

    if (valor === '') return '';

    valor = (parseInt(valor) / 100).toFixed(2);

    return valor;
}


function aplicarMascaraValor(input) {
    input.value = mascaraValor(input.value);
}

// =========================
// MÁSCARA MONETÁRIA BR (1.234,56)
// =========================
function mascaraValorBR(valor) {
    valor = valor.replace(/\D/g, '');

    if (valor === '') return '';

    valor = (parseInt(valor) / 100).toFixed(2) + '';

    let partes = valor.split('.');
    let inteiro = partes[0];
    let decimal = partes[1];

    // separador de milhar
    inteiro = inteiro.replace(/\B(?=(\d{3})+(?!\d))/g, ".");

    return inteiro + ',' + decimal;
}


function aplicarMascaraValorBR(input) {
    input.value = mascaraValorBR(input.value);
}

document.addEventListener("DOMContentLoaded", function () {
    const cpfs = document.querySelectorAll('input[name="cpf"]');
    const cnpjs = document.querySelectorAll('input[name="cnpj"]');
    const cpfCnpjs = document.querySelectorAll('input[name="cpf_cnpj"]');
    const ceps = document.querySelectorAll('input[name="cep"]');
    const telefones = document.querySelectorAll('input[name="telefone"], input[name="telefone_sistema"], input[name="whatsapp"]');
    const datas = document.querySelectorAll('input[name="data_nascimento"]');

    cpfs.forEach(function (campo) {
        campo.addEventListener("input", function () {
            this.value = mascaraCPF(this.value);
        });
    });

    cnpjs.forEach(function (campo) {
        campo.addEventListener("input", function () {
            this.value = mascaraCNPJ(this.value);
        });
    });

    cpfCnpjs.forEach(function (campo) {
        campo.addEventListener("input", function () {
            this.value = mascaraCpfCnpj(this.value);
        });
    });

    ceps.forEach(function (campo) {
        campo.addEventListener("input", function () {
            this.value = mascaraCEP(this.value);
        });
    });

    telefones.forEach(function (campo) {
        campo.addEventListener("input", function () {
            this.value = mascaraTelefone(this.value);
        });
    });

    datas.forEach(function (campo) {
        campo.addEventListener("input", function () {
            this.value = mascaraData(this.value);
        });
    }); 





});