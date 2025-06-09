# routes/api_routes.py
from flask import Blueprint, jsonify, request
from openai_utils.uploader import listar_archivos_vector_store

api_bp = Blueprint('api', __name__)

@api_bp.route("/archivos_subidos", methods=["GET"])
def archivos_subidos():
    try:
        archivos = listar_archivos_vector_store()
        return jsonify({"total": len(archivos), "archivos": archivos})
    except Exception as e:
        return jsonify({"error": str(e)}), 500