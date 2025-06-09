# utils/helpers.py
import re

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