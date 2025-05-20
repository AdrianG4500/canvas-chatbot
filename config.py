# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Variables de entorno
CANVAS_TOKEN = os.getenv("CANVAS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 5000))
SECRET_KEY = os.getenv('SECRET_KEY')

# Canvas
CANVAS_BASE_URL = 'https://canvas.instructure.com/api/v1'
COURSE_ID = '91340000000002198'

# OpenAI
ASSISTANT_ID = "asst_ryh6oDCgELAkuGctOQSul9ar"
VECTOR_STORE_ID = "vs_67efafcb3f988191a08a2c7e07ee73e7"

# lTI CONFIG 
CANVAS_ISSUER="https://canvas.instructure.com"
CANVAS_JWKS_URL="https://sso.canvaslms.com/api/lti/security/jwks"
# Actualizar esto en base a la LTI KEY
CANVAS_CLIENT_ID=os.getenv("CANVAS_CLIENT_ID")
CANVAS_DEPLOYMENT_ID=os.getenv("CANVAS_DEPLOYMENT_ID")
# OTHERS
AUTH_LOGIN_URL = "https://sso.canvaslms.com/api/lti/authorize_redirect"
TOKEN_URL = "https://sso.canvaslms.com/login/oauth2/token"

# LTI
LTI_CLIENT_IDS =os.getenv("CANVAS_CLIENT_ID")

# Ruta a la base de datos
DB_PATH = os.getenv("DB_PATH", "archivos.db")

# Cantidad de consultas
CONS_LIMIT = 20

# Ruta temporal para archivos
TEMP_DIR = "/tmp"


