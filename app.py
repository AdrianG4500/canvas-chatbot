# app.py
from flask import Flask, session
from routes.main_routes import main_bp
from routes.lti_routes import lti_bp
from routes.api_routes import api_bp
import jwt
import secrets
import os
from datetime import datetime, timedelta
from config import PORT, LTI_CLIENT_IDS, SECRET_KEY
import logging


# Crear la aplicación Flask
app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

app.secret_key = SECRET_KEY

app.config.update(
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True,  # Solo funciona en HTTPS, Render usa HTTPS
)

# Cargar claves
PRIVATE_KEY = None
PUBLIC_KEY = None

# Ver si estamos en Render (producción) o en local
ON_RENDER = os.getenv("RENDER", "0") == "1"

# Ruta absoluta para Render (cuando subes los archivos .pem desde el dashboard de Render)
PRIVATE_KEY_PATH = "/etc/secrets/private_key.pem" if ON_RENDER else "private_key.pem"
PUBLIC_KEY_PATH = "/etc/secrets/public_key.pem" if ON_RENDER else "public_key.pem"

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend

    with open(PRIVATE_KEY_PATH, "rb") as key_file:
        PRIVATE_KEY = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )
    print("✅ Clave privada cargada correctamente")
    app.PRIVATE_KEY = PRIVATE_KEY
except ImportError:
    print("❌ Error: Faltan dependencias (cryptography)")
except FileNotFoundError:
    print(f"❌ Error: Archivo no encontrado en {PRIVATE_KEY_PATH}")
    PRIVATE_KEY = None
except Exception as e:
    print(f"❌ Error al cargar la clave privada: {e}")
    PRIVATE_KEY = None

# Cargar clave pública
try:
    with open(PUBLIC_KEY_PATH, "rb") as key_file:
        PUBLIC_KEY = key_file.read()
    app.config["PUBLIC_KEY"] = PUBLIC_KEY
    print("✅ Clave pública cargada correctamente")
except Exception as e:
    print(f"⚠️ No se pudo cargar la clave pública: {e}")
    app.config["PUBLIC_KEY"] = None

# Configurar cliente LTI y OpenAI
app.config["LTI_CLIENT_IDS"] = LTI_CLIENT_IDS

# Registrar blueprints
app.register_blueprint(main_bp)
app.register_blueprint(lti_bp)
app.register_blueprint(api_bp)

# Iniciar el servidor
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))