document.addEventListener("DOMContentLoaded", function () {
    const formPerfil = document.getElementById("formPerfil");
    const btnSalvar = document.getElementById("btnSalvarPerfil");
    const previewFoto = document.getElementById("previewFotoPerfil");
    const inputFoto = document.getElementById("fotoPerfil");
    const areaFotoPerfil = document.querySelector(".perfil-foto-area");

    const formConfiguracoes = document.getElementById("formConfiguracoes");
    const btnSalvarConfiguracoes = document.getElementById("btnSalvarConfiguracoes");

    if (areaFotoPerfil && inputFoto) {
        areaFotoPerfil.addEventListener("click", function () {
            this.classList.add("clicado_input_file");
            setTimeout(() => {
                 inputFoto.click();
                this.classList.remove("clicado_input_file");
            }, 100);
            
        });
    }
    

    if (inputFoto && previewFoto) {
        inputFoto.addEventListener("change", function () {
            const arquivo = this.files[0];
            if (arquivo) {
                const reader = new FileReader();
                reader.onload = function (e) {
                    previewFoto.src = e.target.result;
                };
                reader.readAsDataURL(arquivo);
            }
        });
    }

    if (formPerfil) {
        formPerfil.addEventListener("submit", async function (e) {
            e.preventDefault();

            const formData = new FormData(formPerfil);

            btnSalvar.disabled = true;
            btnSalvar.textContent = "Salvando...";
            mostrarLoading("Salvando dados...");

            try {
                const response = await fetch("/painel/salvar-perfil", {
                    method: "POST",
                    body: formData
                });

                const data = await response.json();

                if (data.status === "sucesso") {
                    mensagemSucesso(data.mensagem);

                    // Atualiza nome no topo
                    const userName = document.querySelector(".user-name");
                    if (userName && data.nome) {
                        userName.textContent = data.nome;
                    }

                    // Atualiza foto no topo
                    const fotosTopo = document.querySelectorAll(".user-photo img");
                    if (fotosTopo.length && data.foto_url) {
                        fotosTopo.forEach(img => {
                            img.src = data.foto_url + "?v=" + new Date().getTime();
                        });
                    }

                    // Atualiza preview da modal
                    if (previewFoto && data.foto_url) {
                        previewFoto.src = data.foto_url + "?v=" + new Date().getTime();
                    }

                    const modalEl = document.getElementById("modalPerfil");
                    const modal = bootstrap.Modal.getInstance(modalEl);
                    if (modal) {
                        modal.hide();
                    }
                } else {
                    mensagemAviso(data.mensagem);
                }

            } catch (error) {                
                alert(error)
                mensagemErro("Erro ao salvar os dados do perfil.");
            } finally {
                btnSalvar.disabled = false;
                btnSalvar.textContent = "Salvar Alterações";
            }
        });
    }




    
const inputCep = document.getElementById("cepPerfil");
const inputEndereco = document.getElementById("enderecoPerfil");
const inputBairro = document.getElementById("bairroPerfil");
const inputCidade = document.getElementById("cidadePerfil");
const inputEstado = document.getElementById("estadoPerfil");
const inputNumero = document.getElementById("numeroPerfil");

if (inputCep) {
    inputCep.addEventListener("blur", async function () {        
        const cep = this.value.replace(/\D/g, "");

        if (cep.length !== 8) {
            return;
        }

        try {
            mostrarLoading("Buscando CEP...");

            const response = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
            const data = await response.json();

            fecharLoading();

            if (data.erro) {
                mensagemAviso("CEP não encontrado.");
                return;
            }

            if (inputEndereco) inputEndereco.value = data.logradouro || "";
            if (inputBairro) inputBairro.value = data.bairro || "";
            if (inputCidade) inputCidade.value = data.localidade || "";
            if (inputEstado) inputEstado.value = data.uf || "";

            if (inputNumero) {
                inputNumero.focus();
            }

        } catch (error) {
            fecharLoading();
            mensagemErro("Não foi possível buscar o CEP.");
        }
    });
}






if (formConfiguracoes) {
    formConfiguracoes.addEventListener("submit", async function (e) {
        e.preventDefault();

        const formData = new FormData(formConfiguracoes);

        btnSalvarConfiguracoes.disabled = true;
        btnSalvarConfiguracoes.textContent = "Salvando...";
        mostrarLoading("Salvando configurações...");

        try {
            const response = await fetch("/painel/salvar-configuracoes", {
                method: "POST",
                body: formData
            });

            const data = await response.json();
            fecharLoading();

            if (data.status === "sucesso") {
                mensagemSucesso(data.mensagem);

                setTimeout(() => {
                    window.location.reload(true);
                }, 800);

            } else {
                mensagemAviso(data.mensagem);
            }

        } catch (error) {
            fecharLoading();
            mensagemErro("Erro ao salvar as configurações.");
        } finally {
            btnSalvarConfiguracoes.disabled = false;
            btnSalvarConfiguracoes.textContent = "Salvar Alterações";
        }
    });
}







const corPrimaria = document.getElementById("corPrimaria");
const corSecundaria = document.getElementById("corSecundaria");
const corPrimariaHex = document.getElementById("corPrimariaHex");
const corSecundariaHex = document.getElementById("corSecundariaHex");
const previewCorPrimaria = document.getElementById("previewCorPrimaria");
const previewCorSecundaria = document.getElementById("previewCorSecundaria");

function corHexValida(cor) {
    return /^#([0-9A-Fa-f]{6})$/.test(cor);
}

// seletor -> input texto
if (corPrimaria && corPrimariaHex) {
    corPrimaria.addEventListener("input", function () {
        corPrimariaHex.value = this.value;
        if (previewCorPrimaria) {
            previewCorPrimaria.style.background = this.value;
        }
    });
}

if (corSecundaria && corSecundariaHex) {
    corSecundaria.addEventListener("input", function () {
        corSecundariaHex.value = this.value;
        if (previewCorSecundaria) {
            previewCorSecundaria.style.background = this.value;
        }
    });
}

// input texto -> seletor
if (corPrimariaHex && corPrimaria) {
    corPrimariaHex.addEventListener("input", function () {
        if (corHexValida(this.value)) {
            corPrimaria.value = this.value;
            if (previewCorPrimaria) {
                previewCorPrimaria.style.background = this.value;
            }
        }
    });
}

if (corSecundariaHex && corSecundaria) {
    corSecundariaHex.addEventListener("input", function () {
        if (corHexValida(this.value)) {
            corSecundaria.value = this.value;
            if (previewCorSecundaria) {
                previewCorSecundaria.style.background = this.value;
            }
        }
    });
}


const menuToggles = document.querySelectorAll(".menu-toggle");

menuToggles.forEach(function (toggle) {
    toggle.addEventListener("click", function () {
        const alvoId = this.getAttribute("data-menu-toggle");
        const submenu = document.getElementById(alvoId);

        if (submenu) {
            submenu.classList.toggle("show");
            this.classList.toggle("open");
        }
    });
});



});


