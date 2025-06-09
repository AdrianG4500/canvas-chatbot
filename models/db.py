import sqlite3
import os
from config import DB_PATH, CONS_LIMIT
from datetime import datetime

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if not os.path.exists(DB_PATH):
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS archivos_procesados (
                canvas_file_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                file_id_openai TEXT
            )
        ''')

        # Tabla de consultas mensuales
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consultas (
                user_id TEXT,
                course_id TEXT,
                mes TEXT,
                total INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, course_id, mes)
            )
        ''')

        # Tabla de historial completo de preguntas y respuestas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historial_consultas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                course_id TEXT,
                user_full_name TEXT,
                course_name TEXT,
                pregunta TEXT,
                respuesta TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla de cursos con sus asistentes y vector stores
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cursos (
                course_id TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                assistant_id TEXT NOT NULL,
                vector_store_id TEXT NOT NULL
                lti_deployment_id TEXT
            )
        ''')
        conn.commit()
        print("✅ Base de datos creada")
    else:
        print("⚠️ Base de datos ya existe")

def get_db_connection():
    from config import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row 
    return conn

def archivo_ya_procesado(cursor, canvas_file_id):
    cursor.execute('SELECT * FROM archivos_procesados WHERE canvas_file_id = ?', (canvas_file_id,))
    return cursor.fetchone()

def registrar_archivo(cursor, canvas_file_id, filename, updated_at, file_id_openai, course_id):
    cursor.execute('''
        INSERT OR REPLACE INTO archivos_procesados 
        (canvas_file_id, filename, updated_at, file_id_openai, course_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (canvas_file_id, filename, updated_at, file_id_openai, course_id))

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

    #print(consulta['total'])

    conn.commit()
    conn.close()
    return consulta['total']

def obtener_datos_curso(course_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM cursos WHERE course_id = ?", (course_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    else:
        print(f"⚠️ Curso {course_id} no encontrado.")
        return None
    
def registrar_consulta_completa(user_id, course_id, user_full_name, course_name, pregunta, respuesta):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO historial_consultas 
        (user_id, course_id, user_full_name, course_name, pregunta, respuesta) 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, course_id, user_full_name, course_name, pregunta, respuesta))
    conn.commit()
    conn.close()

def obtener_datos_curso_por_deployment_id(deployment_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM cursos WHERE lti_deployment_id = ?", (deployment_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    else:
        return None