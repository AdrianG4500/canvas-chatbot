import sqlite3
import os
from config import DB_PATH, CONS_LIMIT
from datetime import datetime

def init_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE archivos_procesados (
                canvas_file_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                file_id_openai TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE consultas (
                user_id TEXT,
                course_id TEXT,
                mes TEXT,
                total INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, course_id, mes)
            )
        ''')
        conn.commit()
        print("✅ Base de datos creada")
    else:
        print("⚠️ Base de datos ya existe")

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def archivo_ya_procesado(cursor, canvas_file_id):
    cursor.execute('SELECT * FROM archivos_procesados WHERE canvas_file_id = ?', (canvas_file_id,))
    return cursor.fetchone()

def registrar_archivo(cursor, canvas_file_id, filename, updated_at, file_id_openai=None):
    cursor.execute('''
        INSERT OR REPLACE INTO archivos_procesados 
        (canvas_file_id, filename, updated_at, file_id_openai)
        VALUES (?, ?, ?, ?)
    ''', (canvas_file_id, filename, updated_at, file_id_openai))

def obtener_todos_los_archivos(cursor):
    cursor.execute('SELECT * FROM archivos_procesados')
    return cursor.fetchall()

def eliminar_registro(cursor, canvas_file_id):
    cursor.execute('DELETE FROM archivos_procesados WHERE canvas_file_id = ?', (canvas_file_id,))

def registrar_consulta(user_id, course_id):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    mes_actual = datetime.now().strftime('%Y-%m')

    consulta = conn.execute(
        "SELECT total FROM consultas WHERE user_id = ? AND course_id = ? AND mes = ?",
        (user_id, course_id, mes_actual)
    ).fetchone()

    if consulta:
        if consulta['total'] >= CONS_LIMIT:
            conn.close()
            return False  # límite alcanzado
        conn.execute(
            "UPDATE consultas SET total = total + 1 WHERE user_id = ? AND course_id = ? AND mes = ?",
            (user_id, course_id, mes_actual)
        )
    else:
        conn.execute(
            "INSERT INTO consultas (user_id, course_id, mes, total) VALUES (?, ?, ?, 1)",
            (user_id, course_id, mes_actual)
        )

    conn.commit()
    conn.close()
    return True

def get_nro_consultas(user_id, course_id):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    mes_actual = datetime.now().strftime('%Y-%m')

    consulta = conn.execute(
        "SELECT total FROM consultas WHERE user_id = ? AND course_id = ? AND mes = ?",
        (user_id, course_id, mes_actual)
    ).fetchone()

    print(consulta['total'])

    conn.commit()
    conn.close()
    return consulta['total']