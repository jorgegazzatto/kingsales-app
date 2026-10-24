from app.database.conexao import conectar
from datetime import datetime


def atualizar_status_contas():
    conexao = None
    cursor = None

    try:
        conexao = conectar()
        cursor = conexao.cursor()

        print(f"[CRON] Iniciando atualização de status - {datetime.now()}")

        # =========================
        # RECEBIMENTOS
        # =========================
        cursor.execute("""
            UPDATE recebimentos
            SET status = 'Atrasado'
            WHERE data_pagamento IS NULL
            AND data_vencimento < CURDATE()
            AND (status IS NULL OR status != 'Atrasado')
        """)

        print(f"[CRON] Recebimentos atualizados: {cursor.rowcount}")

        # =========================
        # DESPESAS
        # =========================
        cursor.execute("""
            UPDATE despesas
            SET status = 'Atrasado'
            WHERE data_pagamento IS NULL
            AND data_vencimento < CURDATE()
            AND (status IS NULL OR status != 'Atrasado')
        """)

        print(f"[CRON] Despesas atualizadas: {cursor.rowcount}")

        conexao.commit()

        print(f"[CRON] Finalizado com sucesso - {datetime.now()}")

    except Exception as e:
        if conexao:
            conexao.rollback()

        print(f"[CRON ERRO] {str(e)}")

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()


# execução direta
if __name__ == "__main__":
    atualizar_status_contas()