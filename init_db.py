# init_db.py

import sqlite3
from config import DB_PATH

def init_db():
    """Inicializa todas las tablas en la base de datos si no existen."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tabla: archivos_procesados - Archivos descargados y subidos a OpenAI
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS archivos_procesados (
            canvas_file_id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            file_id_openai TEXT
        )
    ''')

    # Tabla: consultas - Conteo mensual de preguntas por usuario y curso
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS consultas (
            user_id TEXT,
            course_id TEXT,
            mes TEXT,
            total INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, course_id, mes)
        )
    ''')

    # Tabla: historial_consultas - Registro completo de preguntas y respuestas
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

    # Tabla: cursos - Información de cada curso con sus IDs de OpenAI
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cursos (
            course_id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            assistant_id TEXT NOT NULL,
            vector_store_id TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada correctamente.")
    print(f"📁 Ubicación: {DB_PATH}")

if __name__ == "__main__":
    print("🔧 Inicializando la base de datos...")
    init_db()