from app.database.conexao import conectar
from datetime import datetime


def excluir_logs_antigos():
    conexao = None
    cursor = None

    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)

        print(f"[CRON] Iniciando exclusão de logs antigos - {datetime.now()}")

        # =========================
        # BUSCAR CONFIGURAÇÃO
        # =========================
        cursor.execute("""
            SELECT dias_excluir_logs
            FROM config
            LIMIT 1
        """)

        config = cursor.fetchone()

        if not config:
            print("[CRON] Configuração não encontrada.")
            return

        dias_excluir_logs = config.get("dias_excluir_logs")

        if not dias_excluir_logs:
            print("[CRON] Nenhum prazo configurado para exclusão de logs.")
            return

        try:
            dias_excluir_logs = int(dias_excluir_logs)
        except:
            print("[CRON] Valor inválido em dias_excluir_logs.")
            return

        if dias_excluir_logs <= 0:
            print("[CRON] dias_excluir_logs precisa ser maior que zero.")
            return

        # =========================
        # EXCLUIR LOGS ANTIGOS
        # =========================
        cursor.execute("""
            DELETE FROM logs
            WHERE criado_em < DATE_SUB(NOW(), INTERVAL %s DAY)
        """, (dias_excluir_logs,))

        total_excluidos = cursor.rowcount

        conexao.commit()

        print(f"[CRON] Logs excluídos: {total_excluidos}")
        print(f"[CRON] Mantendo apenas logs dos últimos {dias_excluir_logs} dias.")
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


if __name__ == "__main__":
    excluir_logs_antigos()