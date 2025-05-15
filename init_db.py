# init_db.py
from db import init_db
import sqlite3
from config import DB_PATH

print(f"🔧 Inicializando base de datos en {DB_PATH}...")

try:
    # Esto creará ambas tablas si no existen
    init_db()
    
    # Opcional: verificar manualmente si la tabla 'consultas' existe
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='consultas'")
    if cursor.fetchone():
        print("✅ Tabla 'consultas' ya existe.")
    else:
        print("❌ Tabla 'consultas' NO encontrada. Creando manualmente...")
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
        print("✅ Tabla 'consultas' creada manualmente.")
        
    conn.close()
except Exception as e:
    print(f"❌ Error al inicializar: {e}")