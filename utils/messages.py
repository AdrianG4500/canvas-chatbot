#utils/messages.py
import re
from config import CONS_LIMIT

# Mensajes generales
ERROR_NO_USUARIO_CURSO = "⚠️ No se pudo identificar al usuario o curso."
ERROR_LIMITE_CONSULTAS = "🚫 Has alcanzado el límite mensual de consultas. Vuelve el próximo mes."
ERROR_DESCARGA_ARCHIVO = "❌ Error al descargar archivo"
ERROR_SUBIDA_OPENAI = "❌ Error al subir archivo a OpenAI"

# Saludos personalizados
SALUDO_ESTUDIANTE = "Hola {user_name}, de {course_name}. Esta es tu respuesta:"

 # Saludo personalizado
def generar_respuesta_formateada(user_name, course_name, cantidad, consultas_restantes, texto_final, fuentes):
    saludo = f"¡Hola {user_name}!, de {course_name}. Aqui tienes tu respuesta:\n\n"
    
    # Limpiar y formatear el resto de la respuesta
    texto_final = re.sub(r'\n{2,}', '\n', texto_final)
    texto_final = re.sub(r'\*\s*\n\s*', '* ', texto_final)
    texto_final = re.sub(r'(\d+)\.\s*\n\s*', r'\1. ', texto_final)

    parrafos = texto_final.split('\n')
    cuerpo_respuesta = ""
    for p in parrafos:
        if p.strip():
            cuerpo_respuesta += f"{p.strip()}\n"

    # Construir respuesta completa
    respuesta_formateada = saludo + "🎯 **Respuesta Detallada:**\n\n" + cuerpo_respuesta

    # Agregar info de consultas restantes
    respuesta_formateada += f"\n✅ Has realizado **{cantidad}** de **{CONS_LIMIT}** consultas este mes. Te quedan **{consultas_restantes}**."
    
    # Agregar fuentes si las hay
    if fuentes:
        respuesta_formateada += "\n📚 **Fuentes utilizadas:**\n"
        for i, fuente in enumerate(fuentes, 1):
            respuesta_formateada += f"{i}. *{fuente}*\n"
    
    return respuesta_formateada.strip()