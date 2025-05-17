# openai_utils/uploader.py

import os
import shutil
import openai
from openai import OpenAI
from config import OPENAI_API_KEY, VECTOR_STORE_ID, TEMP_DIR

openai.api_key = OPENAI_API_KEY
client = OpenAI()

# Solo aceptaremos archivos tipo documento
EXTENSIONES_DOCUMENTO = {
    "pdf", "doc", "docx", "xlsx", "csv", "txt", "md", "json", "r", "xls"
}

EXTENSIONES_DOCUMENTO_NC = {
    "pdf", "doc", "docx", "xlsx", "txt", "md", "json"
}

def es_documento_permitido(path):
    ext = os.path.splitext(path)[1][1:].lower()
    return ext in EXTENSIONES_DOCUMENTO

def preparar_archivo_para_openai(path):
    ext = os.path.splitext(path)[1][1:].lower()
    if ext in EXTENSIONES_DOCUMENTO_NC:
        return path  # ya es compatible

    # Si no es compatible, intento convertir a .txt si es texto plano
    nuevo_path = os.path.join(TEMP_DIR, os.path.basename(path)) + ".txt"
    print(f"⚠️ Archivo .{ext} no soportado directamente. Creando copia .txt: {nuevo_path}")

    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as original:
            contenido = original.read()
        with open(nuevo_path, 'w', encoding='utf-8') as convertido:
            convertido.write(contenido)
        return nuevo_path
    except Exception as e:
        raise Exception(f"No se pudo convertir {path} a .txt: {e}")

def subir_y_asociar_archivo(path):
    if not es_documento_permitido(path):
        raise Exception(f"Archivo ignorado por tipo no permitido: {os.path.basename(path)}")

    try:
        path_preparado = preparar_archivo_para_openai(path)
        file_name = os.path.basename(path_preparado)
        print(f"📄 Subiendo archivo a OpenAI: {file_name}")

        try:
            with open(path_preparado, "rb") as f:
                uploaded_file = openai.files.create(file=f, purpose="assistants")
        finally:
            # Asegura que el archivo se cierre incluso si falla algo
            if 'f' in locals():
                f.close()

        file_id = uploaded_file.id
        print(f"✅ Subido. ID: {file_id}")

        # Asociar al vector store
        association = openai.vector_stores.files.create(
            vector_store_id=VECTOR_STORE_ID,
            file_id=file_id
        )
        print(f"🔗 Asociado al vector store: {association.id}")

        if path != path_preparado:
            os.remove(path_preparado)
            print(f"🪜 Eliminado temporal: {path_preparado}")

        return file_id

    except Exception as e:
        print(f"❌ No se subio el archivo: {os.path.basename(path)} → {str(e)}")
        raise

def listar_archivos_vector_store():
    """Lista los archivos asociados al vector store actual"""
    try:
        vs_files = client.vector_stores.files.list(vector_store_id=VECTOR_STORE_ID).data
        archivos = []
        for f in vs_files:
            file_info = client.files.retrieve(f.id)
            archivos.append({
                "id": f.id,
                "name": file_info.filename,
                "created_at": file_info.created_at
            })
        return archivos
    except Exception as e:
        print(f"❌ Error al listar archivos del vector store: {e}")
        return []
    
def extraer_fuentes(texto):
    patron = r"【\d+:\d+†(.*?)】"
    coincidencias = re.findall(patron, texto)
    return list(set(coincidencias))