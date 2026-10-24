# app/utils/logs.py

from flask import request, session
from app.database.conexao import conectar


def registrar_log(acao, entidade, registro_id=None, descricao=None):
    conexao = None
    cursor = None

    try:
        conexao = conectar()
        cursor = conexao.cursor()

        usuario_id = session.get('usuario_id', 0)
        empresa = session.get('empresa', 0)

        rota = request.path if request else None
        ip = request.remote_addr if request else None
        user_agent = request.headers.get('User-Agent') if request else None

        cursor.execute("""
            INSERT INTO logs (
                empresa,
                usuario_id,
                acao,
                entidade,
                registro_id,
                descricao,
                rota,
                ip,
                user_agent
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            empresa,
            usuario_id,
            acao,
            entidade,
            registro_id,
            descricao,
            rota,
            ip,
            user_agent
        ))

        conexao.commit()

    except Exception as e:
        # evita quebrar o sistema por erro de log
        print("Erro ao registrar log:", str(e))

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()




