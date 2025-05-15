# routes/__init__.py
from flask import Blueprint

main_bp = Blueprint('main', __name__)
lti_bp = Blueprint('lti', __name__)
api_bp = Blueprint('api', __name__)

# Importar las rutas para registrarlas
from routes.main_routes import main_bp
from routes.lti_routes import lti_bp
from routes.api_routes import api_bp

blueprints = [main_bp, lti_bp, api_bp]