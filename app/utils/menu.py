MENU_SISTEMA = [
    {
        "titulo": "Dashboard",
        "icone": "bi bi-grid",
        "rota": "painel.dashboard",
        "chave": "dashboard",
        "submenu": []
    },
    {
        "titulo": "Usuários",
        "icone": "bi bi-people",
        "rota": "usuarios.index",
        "chave": "usuarios",
        "submenu": [           
        ]
    },
    {
        "titulo": "Clientes",
        "icone": "bi bi-person-vcard",
        "rota": "clientes.index",
        "chave": "clientes",
        "submenu": [           
        ]
    },
    {
        "titulo": "Cadastros",
        "icone": "bi bi-folder2-open",
        "rota": None,
        "chave": "cadastros",
        "submenu": [

            {
                "titulo": "Cargos",
                "icone": "bi bi-briefcase",
                "rota": "cargos.index",
                "chave": "cargos"
            },

            {
                "titulo": "Frequências",
                "icone": "bi bi-arrow-repeat",
                "rota": "frequencias.index",
                "chave": "frequencias"
            },

            {
                "titulo": "Plano de Contas",
                "icone": "bi bi-diagram-3",
                "rota": "plano_contas.index",
                "chave": "plano_contas"
            },

            {
                "titulo": "Formas de Pagamento",
                "icone": "bi bi-credit-card",
                "rota": "formas_pagamento.index",
                "chave": "formas_pagamento"
            },

            {
                "titulo": "Fornecedores",
                "icone": "bi bi-truck",
                "rota": "fornecedores.index",
                "chave": "fornecedores"
            },
            {
                "titulo": "Centro de Custos",
                "icone": "bi bi-building",
                "rota": "centros_custo.index",
                "chave": "centros_custo"
            }

        ]
    },
    {
        "titulo": "Recebimentos",
        "icone": "bi bi-cash-coin",
        "rota": "recebimentos.index",
        "chave": "recebimentos",
        "submenu": []
    },
    {
        "titulo": "Despesas",
        "icone": "bi bi-cash-stack",
        "rota": "despesas.index",
        "chave": "despesas",
        "submenu": []
    }, 

    {
        "titulo": "Relatórios",
        "icone": "bi bi-bar-chart",
        "rota": None,
        "chave": "relatorios",
        "submenu": [

            {
                "titulo": "Inadimplentes",
                "icone": "bi bi-exclamation-triangle",
                "rota": None,
                "modal": "#modalRelatorioInadimplentes",
                "chave": "relatorios_inadimplentes"
            },

            {
                "titulo": "Financeiro",
                "icone": "bi bi-cash-coin",
                "rota": None,
                "modal": "#modalRelatorioFinanceiro",
                "chave": "relatorios_financeiro"
            }

        ]
    },

    {
        "titulo": "Vendas / PDV",
        "icone": "bi bi-cart-check",
        "rota": None,
        "chave": "vendas",
        "submenu": [

            {
                "titulo": "PDV",
                "icone": "bi bi-upc-scan",
                "rota": "pdv.index",
                "chave": "pdv"
            },

            {
                "titulo": "Lista de Vendas",
                "icone": "bi bi-receipt",
                "rota": "lista_vendas.index",
                "chave": "vendas"
            }

        ]
    },

    {
        "titulo": "Produtos",
        "icone": "bi bi-box-seam",
        "rota": None,
        "chave": "produtos",
        "submenu": [

            {
                "titulo": "Cadastro de Produtos",
                "icone": "bi bi-box",
                "rota": "produtos.index",
                "chave": "produtos"
            },

            {
                "titulo": "Categorias",
                "icone": "bi bi-tags",
                "rota": "categorias.index",
                "chave": "categorias"
            },

            {
                "titulo": "Entradas",
                "icone": "bi bi-arrow-down-circle",
                "rota": "entradas.index",
                "chave": "entradas"
            },

            {
                "titulo": "Saídas",
                "icone": "bi bi-arrow-up-circle",
                "rota": "saidas.index",
                "chave": "saidas"
            }

        ]
    },  
    {
        "titulo": "Logs",
        "icone": "bi bi-journal-text",
        "rota": "logs.index",
        "chave": "logs",
        "submenu": [           
        ]
    }    
]


from copy import deepcopy

def filtrar_menu_por_permissao(menu_sistema, menus_permitidos):
    menu_filtrado = []

    for item in deepcopy(menu_sistema):
        submenu = item.get('submenu', [])

        # se tem submenu, filtra os filhos
        if submenu:
            submenu_filtrado = [
                sub for sub in submenu
                if sub.get('chave') in menus_permitidos
            ]

            if submenu_filtrado:
                item['submenu'] = submenu_filtrado
                menu_filtrado.append(item)

        else:
            if item.get('chave') in menus_permitidos:
                menu_filtrado.append(item)

    return menu_filtrado





def buscar_primeira_rota_permitida(menu_sistema, menus_permitidos):
    menu_filtrado = filtrar_menu_por_permissao(menu_sistema, menus_permitidos)

    for item in menu_filtrado:
        if item.get('rota'):
            return item['rota']

        submenu = item.get('submenu', [])
        for sub in submenu:
            if sub.get('rota'):
                return sub['rota']

    return None