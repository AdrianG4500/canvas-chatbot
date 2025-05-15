# routes/lti_routes.py

from flask import Blueprint, request, render_template, session, current_app, redirect
import jwt
from datetime import datetime, timedelta
import secrets

lti_bp = Blueprint('lti', __name__)

CLAIM_TOOL_PLATFORM = "https://purl.imsglobal.org/spec/claim/tool_platform "
CLAIM_CONTEXT = "https://purl.imsglobal.org/spec/claim/context "
CLAIM_DEPLOYMENT_ID = "https://purl.imsglobal.org/spec/claim/deployment_id "

@lti_bp.route('/.well-known/jwks.json')
def jwks():
    with open('.well-known/jwks.json', 'r') as f:
        return f.read(), 200, {'Content-Type': 'application/json'}



@lti_bp.route('/lti/init')
@lti_bp.route('/lti/login')
def lti_login():
    print("🔑 Iniciando /lti/login")

    # Bandera: ¿Está cargada la PRIVATE_KEY?
    if not hasattr(current_app, 'PRIVATE_KEY') or current_app.PRIVATE_KEY is None:
        print("❌ Bandera 1: PRIVATE_KEY no disponible")
        return "Clave privada no cargada", 500

    PRIVATE_KEY = current_app.PRIVATE_KEY

    # Obtener id_token desde URL
    id_token = request.args.get('id_token')
    state = request.args.get('state')

    if not id_token:
        print("❌ No se recibió id_token en la URL")
        return "Falta id_token", 400

    try:
        # Decodificar sin verificar firma (para desarrollo)
        decoded = jwt.decode(id_token, options={"verify_signature": False})
        print("📄 Token decodificado:", decoded)

        # Validar audience
        aud = decoded.get('aud')
        if aud not in current_app.config.get("LTI_CLIENT_IDS", []):
            print(f"❌ client_id NO autorizado: {aud}")
            return "client_id no autorizado", 400

        # Extraer target_link_uri
        target_link_uri = decoded.get("https://purl.imsglobal.org/spec/lti/claim/target_link_uri ")
        if not target_link_uri:
            print("❌ target_link_uri no encontrado")
            return "target_link_uri requerido", 400

        # Extraer datos esenciales
        iss = decoded.get("iss")
        sub = decoded.get("sub")
        nonce = decoded.get("nonce")
        deployment_id = decoded.get(CLAIM_DEPLOYMENT_ID, "default-deployment")
        context = decoded.get(CLAIM_CONTEXT, {})

        now = datetime.utcnow()
        new_payload = {
            "iss": "http://localhost:5000",
            "aud": aud,
            "exp": now + timedelta(minutes=5),
            "iat": now,
            "nonce": nonce,
            "sub": sub,
            CLAIM_DEPLOYMENT_ID: deployment_id,
            CLAIM_TOOL_PLATFORM: {
                "guid": "vle.uni.ac.uk",
                "name": "Canvas Instructure",
                "product_family_code": "canvas",
                "version": "X2.0"
            },
            CLAIM_CONTEXT: context,
            "given_name": decoded.get("given_name"),
            "family_name": decoded.get("family_name"),
            "email": decoded.get("email"),
            "name": decoded.get("name"),
            "roles": decoded.get("roles", []),
        }

        # Firmar nuevo token
        new_id_token = jwt.encode(
            new_payload,
            PRIVATE_KEY,
            algorithm="RS256",
            headers={
                "alg": "RS256",
                "typ": "JWT",
                "kid": "6ox0b5ag4w"
            }
        )

        print("✅ Nuevo id_token generado correctamente")
        return redirect(f"{target_link_uri}?state={state}&id_token={new_id_token}")

    except jwt.PyJWTError as e:
        print(f"❌ Error al procesar el token: {e}")
        return f"❌ Error al procesar login: {e}", 400


@lti_bp.route("/lti/launch", methods=["POST"])
def lti_launch():
    id_token = request.form.get("id_token")
    if not id_token:
        return "❌ No se recibió id_token", 400

    try:
        # Usar PUBLIC_KEY si está definida
        public_key = current_app.config.get("PUBLIC_KEY", None)
        if not public_key:
            print("⚠️ Advertencia: No se encontró PUBLIC_KEY → saltando verificación de firma")

        # Decodificar sin verificar firma (desarrollo)
        decoded = jwt.decode(id_token, options={"verify_signature": False}, audience="test_client_canvas_123")
        print("📄 Token lanzado:", decoded)

        session["user_id"] = decoded.get("sub")
        session["course_id"] = decoded.get(CLAIM_CONTEXT, {}).get("id")
        username = decoded.get("name", "Usuario")
        course = decoded.get(CLAIM_CONTEXT, {}).get("label", "Curso Desconocido")

        return render_template("lti.html", username=username, course=course, decoded=decoded)

    except jwt.ExpiredSignatureError:
        return "❌ Token expirado", 400
    except jwt.InvalidAudienceError:
        return "❌ Audience inválido", 400
    except Exception as e:
        return f"❌ Error al procesar launch: {str(e)}", 500



@lti_bp.route('/lti/callback')
def lti_callback():
    id_token = request.args.get('id_token')
    if not id_token:
        return "❌ No se recibió id_token", 400

    try:
        decoded = jwt.decode(id_token, options={"verify_signature": False})
        username = decoded.get("name", "Usuario")
        course = decoded.get(CLAIM_CONTEXT, {}).get("label", "Curso Desconocido")
        return render_template("lti.html", username=username, course=course, decoded=decoded)
    except Exception as e:
        return f"❌ Error al decodificar el token: {str(e)}", 400