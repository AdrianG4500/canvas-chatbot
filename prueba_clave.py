# prueba_clave.py
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

try:
    with open("private_key.pem", "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )
    print("✅ Clave privada cargada correctamente")
except Exception as e:
    print(f"❌ Error al cargar la clave: {e}")