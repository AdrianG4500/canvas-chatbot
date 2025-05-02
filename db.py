import sqlite3
import os
from config import DB_PATH

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