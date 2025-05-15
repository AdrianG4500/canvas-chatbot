# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Variables de entorno
CANVAS_TOKEN = os.getenv("CANVAS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 5000))

# Canvas
CANVAS_BASE_URL = 'https://canvas.instructure.com/api/v1'
COURSE_ID = '91340000000002198'

# OpenAI
ASSISTANT_ID = "asst_ryh6oDCgELAkuGctOQSul9ar"
VECTOR_STORE_ID = "vs_67efafcb3f988191a08a2c7e07ee73e7"

# LTI
LTI_CLIENT_IDS = ["test_client_canvas_123"]

# Ruta a la base de datos
DB_PATH = os.getenv("DB_PATH", "archivos.db")

# Ruta temporal para archivos
TEMP_DIR = "/tmp"


