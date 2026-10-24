def valor_para_numero(valor):
    if not valor:
        return 0.0

    valor = str(valor).strip()

    try:
        return float(valor.replace('.', '').replace(',', '.'))
    except:
        return 0.0
    


def formatar_numero_int_ou_decimal(valor):
    try:
        numero = float(valor or 0)

        if numero.is_integer():
            return str(int(numero))

        return f"{numero:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return "0"