# routes/main_routes.py
from flask import Blueprint, render_template, request, session, jsonify, redirect, logging
from config import CONS_LIMIT
from canvas.downloader import get_all_course_files, download_file
from openai_utils.uploader import subir_y_asociar_archivo, listar_archivos_vector_store
#models
from models.db import registrar_consulta
from models.db import get_db_connection, registrar_archivo, get_nro_consultas
from models.db import obtener_datos_curso
from models.db import registrar_consulta_completa
#utils
from utils.helpers import limpiar_respuesta_openai, limpiar_y_separar, extraer_fuentes
from utils.messages import generar_respuesta_formateada
from markdown import markdown
#services
from services.consulta_service import obtener_respuesta_openai
#import others
import openai
import time
import re
import os

main_bp = Blueprint('main', __name__)


#Main Page
@main_bp.route("/", methods=["GET", "POST"])
def index():
    respuesta_formateada = None
    # Obtener course_id y user_id de la sesión
    course_id = session.get("course_id")
    
    if not course_id:
        respuesta_formateada = "⚠️ Esta aplicación debe usarse desde Canvas."
        return render_template("index.html", respuesta=markdown(respuesta_formateada))
    
    try:
        curso_data = obtener_datos_curso(course_id)
    except Exception as e:
        print(f"❌ Error obteniendo datos del curso: {e}")
        return "Curso no encontrado. Verifica que tengas permisos.", 403

    user_id = session.get("user_id")
    ASSISTANT_ID = curso_data["assistant_id"]
    VECTOR_STORE_ID = curso_data["vector_store_id"]

    # Verificar si el usuario y curso están definidos
    if request.method == "POST":
        if not user_id or not course_id:
            respuesta_formateada = "⚠️ No se pudo identificar al usuario o curso."
        else:
            if registrar_consulta(user_id, course_id) is False:
                respuesta_formateada = "🚫 Has alcanzado el límite mensual de consultas. Vuelve el próximo mes."
            else:
                cantidad = get_nro_consultas(user_id, course_id)
                consultas_restantes = CONS_LIMIT - cantidad
                try:
                    # Obtener pregunta del formulario
                    pregunta = request.form.get("pregunta", "").strip()

                    if not pregunta:
                        respuesta_formateada = "⚠️ La pregunta no puede estar vacía."
                    else:
                        # Obtener respuesta de OpenAI
                        texto_final, fuentes = obtener_respuesta_openai(pregunta, ASSISTANT_ID)
                        respuesta_formateada = ""
                        if texto_final:
                            # Obtener nombre y curso desde sesión
                            user_name = session.get('user_full_name', 'Estudiante')
                            course_name = session.get('course_name', 'este curso')
                            respuesta_formateada = generar_respuesta_formateada(
                                user_name, course_name, cantidad, consultas_restantes, texto_final, fuentes
                            )
                            # Registrar en historial
                            registrar_consulta_completa(
                                user_id=user_id,
                                course_id=course_id,
                                user_full_name=user_name,
                                course_name=course_name,
                                pregunta=pregunta,
                                respuesta=texto_final
                            )
                        else:
                            respuesta_formateada = "❌ No se encontró información clara para responder."
                except Exception as e:
                    respuesta_formateada = f"⚠️ Error al obtener respuesta: {str(e)}"
    respuesta_html = markdown(respuesta_formateada) if respuesta_formateada else None
    return render_template("index.html", respuesta=respuesta_html)

#Descargar y subir archivos
@main_bp.route("/descargar", methods=["GET"])
def descargar_y_subir():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener todos los cursos registrados
        cursor.execute("SELECT course_id, vector_store_id FROM cursos")
        cursos_registrados = cursor.fetchall()

        if not cursos_registrados:
            return jsonify({"error": "❌ No hay cursos registrados."}), 400

        resultados_totales = {}

        for curso_row in cursos_registrados:
            course_id = curso_row[0]
            VECTOR_STORE_ID = curso_row[1]

            print(f"\n🔄 Procesando curso: {course_id}")

            # Obtener archivos de Canvas para este curso
            try:
                archivos_canvas = get_all_course_files(course_id)
            except Exception as e:
                print(f"❌ Error obteniendo archivos de Canvas para {course_id}: {str(e)}")
                continue

            ids_en_canvas = set(str(archivo["id"]) for archivo in archivos_canvas)

            # Archivos en DB para este curso
            cursor.execute("SELECT canvas_file_id FROM archivos_procesados WHERE course_id = ?", (course_id,))
            registros_db = cursor.fetchall()
            ids_en_db = set(row[0] for row in registros_db)

            archivos_eliminados = ids_en_db - ids_en_canvas
            if archivos_eliminados:
                print(f"🗑️ Eliminando {len(archivos_eliminados)} archivos eliminados en Canvas")

            for canvas_file_id in archivos_eliminados:
                try:
                    cursor.execute(
                        "SELECT file_id_openai FROM archivos_procesados WHERE canvas_file_id = ? AND course_id = ?",
                        (canvas_file_id, course_id)
                    )
                    row = cursor.fetchone()
                    file_id_openai = row[0] if row else None

                    if file_id_openai:
                        openai.vector_stores.files.delete(vector_store_id=VECTOR_STORE_ID, file_id=file_id_openai)
                        openai.files.delete(file_id_openai)

                    cursor.execute(
                        "DELETE FROM archivos_procesados WHERE canvas_file_id = ? AND course_id = ?",
                        (canvas_file_id, course_id)
                    )
                    conn.commit()
                    print(f"✅ Archivo eliminado: {canvas_file_id}")
                except Exception as e:
                    print(f"❌ Error al eliminar archivo {canvas_file_id}: {str(e)}")

            # Procesar archivos nuevos/actualizados
            subidos_por_curso = []

            for archivo in archivos_canvas:
                canvas_file_id = str(archivo["id"])
                filename = archivo["filename"]
                updated_at = archivo.get("updated_at", "")

                cursor.execute('''
                    SELECT * FROM archivos_procesados 
                    WHERE canvas_file_id = ? AND course_id = ?
                ''', (canvas_file_id, course_id))
                registro = cursor.fetchone()

                if registro and registro[2] == updated_at:
                    print(f"🔁 Sin cambios: {filename}")
                    continue

                try:
                    path = download_file(archivo)
                    file_id = subir_y_asociar_archivo(path, VECTOR_STORE_ID)
                    os.remove(path)

                    registrar_archivo(cursor, canvas_file_id, filename, updated_at, file_id, course_id)
                    conn.commit()
                    subidos_por_curso.append({"archivo": filename, "file_id": file_id})
                except Exception as e:
                    print(f"❌ Error con {filename}: {str(e)}")
                    subidos_por_curso.append({"archivo": filename, "error": str(e)})

            resultados_totales[course_id] = subidos_por_curso

        conn.close()
        return jsonify({
            "status": "ok",
            "resultados_por_curso": resultados_totales
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

#Admin Page
@main_bp.route("/admin")
def admin():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener todos los cursos
    cursor.execute("SELECT course_id, nombre, assistant_id, vector_store_id FROM cursos")
    cursos_completos = cursor.fetchall()

    # Obtener todos los archivos procesados
    cursor.execute("SELECT * FROM archivos_procesados")
    registros_db = cursor.fetchall()

    # Obtener historial completo de consultas
    cursor.execute('''
        SELECT user_full_name, course_name, pregunta, respuesta, timestamp 
        FROM historial_consultas 
        ORDER BY timestamp DESC LIMIT 50
    ''')
    historial = cursor.fetchall()

    # Obtener todas las consultas mensuales
    cursor.execute("SELECT user_id, course_id, mes, total FROM consultas ORDER BY mes DESC")
    registros_consulta = cursor.fetchall()

    # Preparar archivos por curso
    archivos_por_curso = {}
    for curso in cursos_completos:
        course_id = curso[0]
        vector_store_id = curso[3]

        archivos_por_curso[course_id] = {
            "nombre": curso[1],
            "archivos": listar_archivos_vector_store(vector_store_id),
            "vector_store_id": vector_store_id
        }

    conn.close()

    return render_template("admin.html",
                           registros=registros_db,
                           historial=historial,
                           consultas=registros_consulta,
                           cursos=cursos_completos,
                           archivos_por_curso=archivos_por_curso)

#Eliminar archivo
@main_bp.route("/eliminar/<canvas_file_id>", methods=["POST"])
def eliminar_archivo(canvas_file_id):
    course_id = session.get("course_id")
    curso_data = obtener_datos_curso(course_id)

    if not curso_data:
        return jsonify({"error": "❌ Curso no configurado"}), 400

    VECTOR_STORE_ID = curso_data["vector_store_id"]
    
    # Verificar que el canvas_file_id sea válido
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_id_openai FROM archivos_procesados WHERE canvas_file_id = ?", (canvas_file_id,))
    row = cursor.fetchone()
    file_id_openai = row[0] if row else None
    # Verificar que el archivo exista en la base de datos
    if file_id_openai:
        try:
            openai.vector_stores.files.delete(vector_store_id=VECTOR_STORE_ID, file_id=file_id_openai)
            openai.files.delete(file_id_openai)
        except Exception as e:
            print(f"❌ Error al eliminar de OpenAI: {e}")

    # Eliminar de la base de datos
    cursor.execute("DELETE FROM archivos_procesados WHERE canvas_file_id = ?", (canvas_file_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "Archivo eliminado"})

#Ruta temporal para pruebas locales
@main_bp.route("/test")
def iniciar_sesion_local():
    """Ruta temporal para pruebas locales"""
    session["user_id"] = "local_user_123"
    session["course_id"] = "91340000000002198"  # Un curso ya registrado
    session["user_full_name"] = "Desarrollador Local"
    session["course_name"] = "Curso de Prueba - Local"
    print("🔑 Sesión iniciada localmente con usuario de prueba.")
    return redirect("/")