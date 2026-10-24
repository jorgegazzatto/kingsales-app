/* =========================
   ALERTAS E LOADING PADRÃO
========================= */

function mostrarLoading(texto = "Carregando...") {
    Swal.fire({
        title: texto,
        html: "Aguarde um momento",
        allowOutsideClick: false,
        allowEscapeKey: false,
        showConfirmButton: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
}

function fecharLoading() {
    Swal.close();
}

function mensagemSucesso(mensagem = "Operação realizada com sucesso!") {
    return Swal.fire({
        icon: "success",
        title: "Sucesso",
        text: mensagem,
        showConfirmButton: false,
        timer: 1000, // tempo em ms (1.8 segundos)
        timerProgressBar: true
    });
}

function mensagemErro(mensagem = "Ocorreu um erro ao processar a solicitação.") {
    return Swal.fire({
        icon: "error",
        title: "Erro",
        text: mensagem,
        confirmButtonText: "OK",
        confirmButtonColor: "#dc3545"
    });
}

function mensagemAviso(mensagem = "Atenção!") {
    return Swal.fire({
        icon: "warning",
        title: "Atenção",
        text: mensagem,
        confirmButtonText: "OK",
        confirmButtonColor: "#f59e0b"
    });
}

function mensagemInfo(mensagem = "Informação") {
    return Swal.fire({
        icon: "info",
        title: "Informação",
        text: mensagem,
        confirmButtonText: "OK",
        confirmButtonColor: "#0d6efd"
    });
}

function confirmarAcao({
    titulo = "Tem certeza?",
    texto = "Essa ação não poderá ser desfeita.",
    textoConfirmar = "Sim, continuar",
    textoCancelar = "Cancelar"
} = {}) {
    return Swal.fire({
        icon: "warning",
        title: titulo,
        text: texto,
        showCancelButton: true,
        confirmButtonText: textoConfirmar,
        cancelButtonText: textoCancelar,
        confirmButtonColor: "#0d6efd",
        cancelButtonColor: "#6c757d",
        reverseButtons: true
    });
}