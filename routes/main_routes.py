# routes/main_routes.py
from flask import Blueprint, render_template, request, session, jsonify
from config import ASSISTANT_ID, VECTOR_STORE_ID
from canvas.downloader import get_all_course_files, download_file
from openai_utils.uploader import subir_y_asociar_archivo, listar_archivos_vector_store
from db import registrar_consulta
from db import get_db_connection, registrar_archivo, get_nro_consultas
from markdown import markdown
import openai
import time
import re
import os

main_bp = Blueprint('main', __name__)

def limpiar_respuesta_openai(texto):
    texto_limpio = re.sub(r"【\d+:\d+†(.*?)】", "", texto)
    texto_limpio = texto_limpio.replace("1.", "🔹").replace("2.", "🔹").replace("3.", "🔹")
    return texto_limpio.strip()

def limpiar_y_separar(texto):
    fuentes = extraer_fuentes(texto)
    texto_limpio = re.sub(r"【\d+:\d+†.*?】", "", texto)
    return texto_limpio.strip(), fuentes

def extraer_fuentes(texto):
    patron = r"【\d+:\d+†(.*?)】"
    coincidencias = re.findall(patron, texto)
    return list(set(coincidencias))



@main_bp.route("/", methods=["GET", "POST"])
def index():
    respuesta_formateada = None
    user_id = session.get("user_id")
    course_id = session.get("course_id")
    if request.method == "POST":
        if not user_id or not course_id:
            respuesta_formateada = "⚠️ No se pudo identificar al usuario o curso."
        else:
            if registrar_consulta(user_id, course_id) is False:
                respuesta_formateada = "🚫 Has alcanzado el límite mensual de 10 consultas. Vuelve el próximo mes."
            else:
                cantidad = get_nro_consultas(user_id, course_id)
                consultas_restantes = 10 - cantidad
                try:
                    pregunta = request.form.get("pregunta", "").strip()

                    if not pregunta:
                        respuesta_formateada = "⚠️ La pregunta no puede estar vacía."
                    else:
                        thread = openai.beta.threads.create()
                        openai.beta.threads.messages.create(
                            thread_id=thread.id,
                            role="user",
                            content=pregunta
                        )
                        run = openai.beta.threads.runs.create(
                            thread_id=thread.id,
                            assistant_id=ASSISTANT_ID
                        )
                        while run.status not in ["completed", "failed"]:
                            time.sleep(1)
                            run = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
                        messages = openai.beta.threads.messages.list(thread_id=thread.id)
                        respuesta_bruta = messages.data[0].content[0].text.value
                        texto_final, fuentes = limpiar_y_separar(respuesta_bruta)

                        respuesta_formateada = ""
                        if texto_final:
                            respuesta_formateada += "🎯 **Respuesta Detallada:**\n\n"
                            # Limpiar múltiples saltos de línea
                            texto_final = re.sub(r'\n{2,}', '\n', texto_final)

                            # Unir líneas con viñetas mal cortadas (por ejemplo "*\nContenido" -> "* Contenido")
                            texto_final = re.sub(r'\*\s*\n\s*', '* ', texto_final)

                            # Unir enumeraciones mal cortadas (por ejemplo "1.\nTexto" -> "1. Texto")
                            texto_final = re.sub(r'(\d+)\.\s*\n\s*', r'\1. ', texto_final)

                            # Volver a separar en párrafos más limpios
                            parrafos = texto_final.split('\n')
                            for p in parrafos:
                                if p.strip():
                                    respuesta_formateada += f"{p.strip()}\n"
                            respuesta_formateada += f"\n✅ Has realizado **{cantidad}** de **10** consultas este mes. Te quedan **{consultas_restantes}**."
                            if fuentes:
                                respuesta_formateada += "\n📚 **Fuentes utilizadas:**\n"
                                for i, fuente in enumerate(fuentes, 1):
                                    respuesta_formateada += f"{i}. *{fuente}*\n"
                        else:
                            respuesta_formateada = "❌ No se encontró información clara para responder."
                except Exception as e:
                    respuesta_formateada = f"⚠️ Error al obtener respuesta: {str(e)}"

    respuesta_html = markdown(respuesta_formateada) if respuesta_formateada else None
    return render_template("index.html", respuesta=respuesta_html)

@main_bp.route("/descargar", methods=["GET"])
def descargar_y_subir():
    try:
        archivos_canvas = get_all_course_files()
        conn = get_db_connection()
        cursor = conn.cursor()
        subidos = []

        cursor.execute("SELECT canvas_file_id FROM archivos_procesados")
        registros_db = cursor.fetchall()
        ids_en_db = set(row[0] for row in registros_db)
        ids_en_canvas = set(str(archivo["id"]) for archivo in archivos_canvas)

        archivos_eliminados = ids_en_db - ids_en_canvas
        if archivos_eliminados:
            print(f"🗑️ Archivos eliminados en Canvas detectados: {len(archivos_eliminados)}")

        for canvas_file_id in archivos_eliminados:
            try:
                cursor.execute("SELECT file_id_openai FROM archivos_procesados WHERE canvas_file_id = ?", (canvas_file_id,))
                row = cursor.fetchone()
                file_id_openai = row[0] if row else None

                if file_id_openai:
                    openai.vector_stores.files.delete(vector_store_id=VECTOR_STORE_ID, file_id=file_id_openai)
                    openai.files.delete(file_id_openai)

                cursor.execute("DELETE FROM archivos_procesados WHERE canvas_file_id = ?", (canvas_file_id,))
                conn.commit()
                print(f"✅ Archivo eliminado (Canvas): {canvas_file_id}")

            except Exception as e:
                print(f"❌ Error al eliminar archivo {canvas_file_id}: {str(e)}")

        for archivo in archivos_canvas:
            canvas_file_id = str(archivo["id"])
            filename = archivo["filename"]
            updated_at = archivo.get("updated_at", "")

            cursor.execute('SELECT * FROM archivos_procesados WHERE canvas_file_id = ?', (canvas_file_id,))
            registro = cursor.fetchone()

            if registro:
                if registro[2] == updated_at:
                    print(f"🔁 Archivo sin cambios: {filename}")
                    continue
                else:
                    print(f"🔄 Archivo actualizado: {filename}")

            try:
                path = download_file(archivo)
                file_id = subir_y_asociar_archivo(path)
                os.remove(path)
                registrar_archivo(cursor, canvas_file_id, filename, updated_at, file_id)
                conn.commit()
                subidos.append({"archivo": filename, "file_id": file_id})
            except Exception as e:
                print(f"❌ Error: {filename} → {str(e)}")
                subidos.append({"archivo": filename, "error": str(e)})

        conn.close()
        return jsonify({"archivos_subidos": subidos})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main_bp.route("/admin")
def admin():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM archivos_procesados")
    registros_db = cursor.fetchall()

    try:
        archivos_vs = listar_archivos_vector_store()
    except Exception as e:
        archivos_vs = []
        print(f"⚠️ Error al obtener archivos del vector store: {e}")

    cursor.execute("SELECT user_id, course_id, mes, total FROM consultas ORDER BY mes DESC")
    registros_consulta = cursor.fetchall()

    conn.close()
    return render_template("admin.html", registros=registros_db, archivos_vs=archivos_vs, consultas=registros_consulta)

@main_bp.route("/eliminar/<canvas_file_id>", methods=["POST"])
def eliminar_archivo(canvas_file_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_id_openai FROM archivos_procesados WHERE canvas_file_id = ?", (canvas_file_id,))
    row = cursor.fetchone()
    file_id_openai = row[0] if row else None

    if file_id_openai:
        try:
            openai.vector_stores.files.delete(vector_store_id=VECTOR_STORE_ID, file_id=file_id_openai)
            openai.files.delete(file_id_openai)
        except Exception as e:
            print(f"❌ Error al eliminar de OpenAI: {e}")

    cursor.execute("DELETE FROM archivos_procesados WHERE canvas_file_id = ?", (canvas_file_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "Archivo eliminado"})