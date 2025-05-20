# routes/lti_routes.py

from flask import Blueprint, request, render_template, session, current_app, redirect
import jwt
import requests
import json
import logging
from datetime import datetime, timedelta
import secrets
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from urllib.parse import urlencode
from config import CANVAS_ISSUER, CANVAS_JWKS_URL, CANVAS_CLIENT_ID, CANVAS_DEPLOYMENT_ID


lti_bp = Blueprint('lti', __name__, url_prefix="/lti")

CLAIM_CONTEXT = "https://purl.imsglobal.org/spec/lti/claim/context"

LTI_MESSAGE_HINT = "My LTI message hint!"  # Bien usado

# Cargar clave pública desde archivo PEM
def load_public_key():
    try:
        with open("public_key.pem", "rb") as f:
            public_key = serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )
        return public_key
    except Exception as e:
        logging.info(f"❌ Error cargando clave pública: {e}")
        return None


@lti_bp.route('/.well-known/jwks.json')
def jwks():
    with open('.well-known/jwks.json', 'r') as f:
        jwks_data = json.load(f)
    return jwks_data, 200, {'Content-Type': 'application/json'}

# LTI Login (GET,POST)
@lti_bp.route("/login", methods=["GET", "POST"])
def login():
    logging.info(f"📥 Método recibido en /lti/login: {request.method}")
    # Generar state y nonce aleatorios
    if request.method == "POST":
        # Canvas a veces envía parámetros como form-data en POST
        data = request.form
    else:
        data = request.args

    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)
    session['state'] = state
    session['nonce'] = nonce

    logging.info("📩 Datos recibidos en /lti/login:")
    logging.info(dict(data))

    # Asegura los parámetros obligatorios
    iss = data.get("iss")
    login_hint = data.get("login_hint")
    target_link_uri = data.get("target_link_uri")
    lti_message_hint = data.get("lti_message_hint", "")
    client_id = data.get("client_id")
    lti_deployment_id = data.get("lti_deployment_id", "")

    if not all([login_hint, target_link_uri, client_id]):
        return "Faltan parámetros", 400
    
    #base_url = iss.rstrip("/") + "/auth?"
    base_url = "https://ucb.instructure.com/auth?"
    
    # ✅ Redirigimos a la autenticación real de la plataforma
    params = {
        "scope": "openid",
        "response_type": "id_token",
        "client_id": client_id,
        "redirect_uri": target_link_uri,
        "login_hint": login_hint,
        "state": state,
        "nonce": nonce,
        "response_mode": "form_post",
        "prompt": "none",  # Cambia a "login" para debug si quieres
        "lti_message_hint": lti_message_hint,
        "lti_deployment_id": lti_deployment_id,
        "id_token_signed_response_alg": "RS256"
    }

    auth_url = base_url + urlencode(params)

    logging.info(auth_url)
    return redirect(auth_url)

@lti_bp.route("/launch", methods=["GET","POST"])  
def launch():
    if request.method == "GET":
        return "❌ Error: Canvas debe enviar POST, no GET", 405
    logging.info("✅ POST recibido")


    logging.info("✅ Launch iniciado")

    received_state = request.form.get('state')
    expected_state = session.get('state')

    if not received_state or received_state != expected_state:
        logging.info(f"❌ State no coincide: esperado {expected_state} - recibido {received_state}")
        return "Estado inválido", 400


    #print("⭐Args:", dict(request.args))
    #print("🔵Form:", dict(request.form))
    #print("🔻Headers:", dict(request.headers))
    #print("📢 Data cruda:", request.get_data())

    id_token = request.form.get('id_token')

    if not id_token:
        logging.info("❌ No se recibió id_token")
        return "Falta id_token", 400

    try:
         # CONFIG DE PRODUCCIÓN DESDE CONFIG
        jwks_url = CANVAS_JWKS_URL
        client_id = CANVAS_CLIENT_ID
        issuer = CANVAS_ISSUER
        deployment_id_expected = CANVAS_DEPLOYMENT_ID

        # Obtener claves públicas
        jwks = requests.get(jwks_url).json()
        public_keys = {
            key["kid"]: jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
            for key in jwks["keys"]
        }
        unverified_header = jwt.get_unverified_header(id_token)

        #print(f"🔐 Encabezado sin verificar: {unverified_header}")
        #print(f"📥 JWKS obtenida desde {jwks_url}: {jwks}")
        #print(f"📌 Claves disponibles (kids): {list(public_keys.keys())}")
        #print(f"🔍 Se buscará kid: {unverified_header.get('kid')}")

        key = public_keys[unverified_header["kid"]]
         # Decodificar token
        decoded = jwt.decode(
            id_token,
            key=key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=issuer
        )

        

        if decoded.get("https://purl.imsglobal.org/spec/lti/claim/deployment_id") != deployment_id_expected:
            logging.info("❌ Deployment ID inválido")
            return "Deployment ID no válido", 400

        # Validación de nonce
        expected_nonce = session.get("nonce")
        received_nonce = decoded.get("nonce")

        if received_nonce != expected_nonce:
            logging.info(f"❌ Nonce inválido: esperado {expected_nonce} - recibido {received_nonce}")
            return "Nonce inválido", 400

        logging.info("✅ Token decodificado:")
        session['user_id'] = decoded.get('sub')
        session['course_id'] = decoded.get(CLAIM_CONTEXT, {}).get('id')

        logging.info(f"✅ Usuario autenticado: {session['user_id']}, Curso: {session['course_id']}")
        #print(decoded.keys())

        return redirect("/")
    except jwt.PyJWTError as e:
        logging.info(f"❌ Error JWT: {str(e)}")
        return f"❌ Error validando token: {str(e)}", 400
    except Exception as e:
        logging.info(f"❌ Error general: {str(e)}")
        return f"❌ Error interno: {str(e)}", 500

