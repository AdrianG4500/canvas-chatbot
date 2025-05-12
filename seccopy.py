from flask import Flask, request, jsonify, render_template
from config import ASSISTANT_ID, PORT, TEMP_DIR, VECTOR_STORE_ID, ASSISTANT_ID
from canvas.downloader import get_all_course_files, download_file
from openai_utils.uploader import subir_y_asociar_archivo, listar_archivos_vector_store
from db import init_db, get_db_connection, registrar_archivo
from markdown import markdown
from openai import OpenAI
import openai
import os
import time
import re

client = OpenAI()

app = Flask(__name__)




def limpiar_respuesta_openai(texto):
    # Elimina las referencias del estilo 【4:0†archivo.pdf】
    texto_limpio = re.sub(r"【\d+:\d+†(.*?)】", "", texto)

    # Reemplazar patrones comunes por formato más bonito
    texto_limpio = texto_limpio.replace("1.", "🔹")
    texto_limpio = texto_limpio.replace("2.", "🔹")
    texto_limpio = texto_limpio.replace("3.", "🔹")
    texto_limpio = texto_limpio.replace("4.", "🔹")
    texto_limpio = texto_limpio.replace("5.", "🔹")

    return texto_limpio.strip()


def limpiar_y_separar(texto):
    fuentes = extraer_fuentes(texto)
    texto_limpio = re.sub(r"【\d+:\d+†.*?】", "", texto)
    return texto_limpio.strip(), fuentes

def extraer_fuentes(texto):
    patron = r"【\d+:\d+†(.*?)】"
    coincidencias = re.findall(patron, texto)
    return list(set(coincidencias))


# === RUTA RAÍZ: Chat con el assistant ===
@app.route("/", methods=["GET", "POST"])
def index():
    respuesta_formateada = None  # Inicialización segura

    if request.method == "POST":
        try:
            pregunta = request.form["pregunta"]
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

            # Esperar respuesta sincronamente
            while run.status not in ["completed", "failed"]:
                time.sleep(1)
                run = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

            messages = openai.beta.threads.messages.list(thread_id=thread.id)
            respuesta_bruta = messages.data[0].content[0].text.value

            # Limpiar y separar fuentes
            texto_final, fuentes = limpiar_y_separar(respuesta_bruta)

            # Formatear con emojis y estructura básica
            respuesta_formateada = ""

            if texto_final:
                # Añadir título visual
                respuesta_formateada += "🎯 **Respuesta Detallada:**\n\n"

                # Dividir en párrafos, pero sin saltos múltiples
                parrafos = texto_final.split('\n')
                for p in parrafos:
                    if p.strip():
                        respuesta_formateada += f"{p}\n"    

                # Añadir fuentes al final
                if fuentes:
                    respuesta_formateada += "\n\n📚 **Fuentes utilizadas:**\n"
                    for i, fuente in enumerate(fuentes, 1):
                        respuesta_formateada += f"{i}. *{fuente}*\n"
            else:
                respuesta_formateada = "❌ No se encontró información clara para responder."

        except Exception as e:
            respuesta_formateada = f"⚠️ Error al obtener respuesta: {str(e)}"

    # Usar markdown solo si hay contenido
    if respuesta_formateada:
        respuesta_html = markdown(respuesta_formateada)
    else:
        respuesta_html = None

    return render_template("index.html", respuesta=respuesta_html)





# === DESCARGAR desde Canvas, SUBIR a OpenAI ===
@app.route("/descargar", methods=["GET"])
def descargar_y_subir():
    try:
        archivos_canvas = get_all_course_files()
        conn = get_db_connection()
        cursor = conn.cursor()
        subidos = []

        # === OBTENER ARCHIVOS DE LA DB ===
        cursor.execute("SELECT canvas_file_id FROM archivos_procesados")
        registros_db = cursor.fetchall()

        # Convertir a conjunto para comparar fácilmente
        ids_en_db = set(row[0] for row in registros_db)
        ids_en_canvas = set(str(archivo["id"]) for archivo in archivos_canvas)

        # === DETECTAR Y ELIMINAR ARCHIVOS ELIMINADOS EN CANVAS ===
        archivos_eliminados = ids_en_db - ids_en_canvas

        if archivos_eliminados:
            print(f"🗑️ Archivos eliminados en Canvas detectados: {len(archivos_eliminados)}")

        for canvas_file_id in archivos_eliminados:
            try:
                # Obtener file_id_openai desde la DB
                cursor.execute(
                    "SELECT file_id_openai FROM archivos_procesados WHERE canvas_file_id = ?",
                    (canvas_file_id,)
                )
                row = cursor.fetchone()
                file_id_openai = row[0] if row else None

                # Eliminar del vector store
                if file_id_openai:
                    client.vector_stores.files.delete(
                        vector_store_id=VECTOR_STORE_ID,
                        file_id=file_id_openai
                    )
                    openai.files.delete(file_id_openai)

                # Eliminar de la base de datos
                cursor.execute(
                    "DELETE FROM archivos_procesados WHERE canvas_file_id = ?",
                    (canvas_file_id,)
                )
                conn.commit()
                print(f"✅ Archivo eliminado (Canvas): {canvas_file_id}")

            except Exception as e:
                print(f"❌ Error al eliminar archivo {canvas_file_id}: {str(e)}")
        
        for archivo in archivos_canvas:
            canvas_file_id = str(archivo["id"])
            filename = archivo["filename"]
            updated_at = archivo.get("updated_at", "")

            # Ver si ya fue procesado
            cursor.execute('SELECT * FROM archivos_procesados WHERE canvas_file_id = ?', (canvas_file_id,))
            registro = cursor.fetchone()

            if registro:
                # Si no ha cambiado, saltar
                if registro[2] == updated_at:
                    print(f"🔁 Archivo sin cambios: {filename}")
                    continue
                else:
                    print(f"🔄 Archivo actualizado: {filename}")

            # Descargar y subir
            try:
                path = download_file(archivo)
                file_id = subir_y_asociar_archivo(path)
                os.remove(path)
                # Registrar o actualizar en DB
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

# === VER archivos subidos al vector store ===
@app.route("/archivos_subidos", methods=["GET"])
def archivos_subidos():
    try:
        archivos = listar_archivos_vector_store()
        return jsonify({"total": len(archivos), "archivos": archivos})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin")
def admin():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Listar archivos procesados en la base de datos
    cursor.execute("SELECT * FROM archivos_procesados")
    registros_db = cursor.fetchall()

    # 2. Listar archivos en el vector store actual
    try:
        archivos_vs = listar_archivos_vector_store()
    except Exception as e:
        archivos_vs = []
        print(f"⚠️ Error al obtener archivos del vector store: {e}")

    conn.close()

    return render_template(
        "admin.html",
        registros=registros_db,
        archivos_vs=archivos_vs
    )

@app.route("/eliminar/<canvas_file_id>", methods=["POST"])
def eliminar_archivo(canvas_file_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener registro de la DB
    cursor.execute("SELECT file_id_openai FROM archivos_procesados WHERE canvas_file_id = ?", (canvas_file_id,))
    row = cursor.fetchone()
    file_id_openai = row[0] if row else None

    # Eliminar del vector store si existe
    if file_id_openai:
        try:
            openai.vector_stores.files.delete(
                vector_store_id=VECTOR_STORE_ID,
                file_id=file_id_openai
            )
            openai.files.delete(file_id_openai)
        except Exception as e:
            print(f"❌ Error al eliminar de OpenAI: {e}")

    # Eliminar de la base de datos
    cursor.execute("DELETE FROM archivos_procesados WHERE canvas_file_id = ?", (canvas_file_id,))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "message": "Archivo eliminado"})

# LTI IMPLEMENTATION

@app.route('/.well-known/jwks.json')
def jwks():
    with open('.well-known/jwks.json', 'r') as f:
        return f.read(), 200, {'Content-Type': 'application/json'}


@app.route('/lti/init')
@app.route('/lti/login')
def lti_login():
    iss = request.args.get('iss')  # Issuer (Canvas)
    client_id = request.args.get('client_id')  # Client ID del tool
    response_mode = request.args.get('response_mode') or 'form_post'
    response_type = request.args.get('response_type') or 'id_token'
    scope = request.args.get('scope') or 'openid'
    redirect_uri = request.args.get('redirect_uri')  # Esta debe estar registrada en tu Developer Key
    nonce = request.args.get('nonce')  # Lo usaremos después
    state = request.args.get('state')  # Estado de sesión

    print("📥 Iniciando Login")
    print("Issuer:", iss)
    print("Redirect URI:", redirect_uri)
    print("Nonce:", nonce)

    # Aquí redirigimos a /lti/callback con datos mínimos
    return redirect(f"{redirect_uri}?state={state}&id_token=FAKE_JWT_TOKEN")

@app.route('/lti/launch', methods=['POST'])
def lti_launch():
    id_token = request.form.get('id_token')
    state = request.form.get('state')

    if not id_token:
        return "❌ No se recibió id_token", 400

    try:
        import jwt
        decoded = jwt.decode(id_token, options={"verify_signature": False})

        username = decoded.get('name', 'Estudiante')
        course = decoded.get('https://purl.imsglobal.org/spec/claim/context', {}).get('label', 'Curso Desconocido')

        return render_template("lti.html", username=username, course=course, decoded=decoded)
    except Exception as e:
        return f"❌ Error al decodificar el token: {str(e)}", 400

@app.route('/lti/callback')
def lti_callback():
    id_token = request.args.get('id_token')
    state = request.args.get('state')

    if not id_token:
        return "❌ No se recibió id_token", 400

    try:
        # Por ahora mostramos el token recibido
        print("📨 Token recibido:")
        print(id_token)

        # Decodificar sin verificar firma (SOLO PARA PRUEBAS)
        import jwt
        decoded = jwt.decode(id_token, options={"verify_signature": False})

        username = decoded.get('name', 'Estudiante')
        course = decoded.get('https://purl.imsglobal.org/spec/claim/context', {}).get('label', 'Curso Desconocido')

        return render_template("lti.html", username=username, course=course, decoded=decoded)
    except Exception as e:
        return f"❌ Error al decodificar el token: {str(e)}", 400
    


# === EJECUTAR SERVIDOR ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
