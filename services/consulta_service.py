from datetime import datetime
from models.db import get_db_connection
import logging
import openai
import time
from utils.helpers import limpiar_respuesta_openai, limpiar_y_separar
from flask import session

def obtener_respuesta_openai(pregunta, ASSISTANT_ID):
    logging.info(f"📝 Pregunta: {pregunta}")
    logging.info(f"🤖 Asistente ID: {ASSISTANT_ID}")
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
    logging.info(f"✅ Respuesta obtenida: {texto_final}")
    logging.info(f"📚 Fuentes: {fuentes}")
    return texto_final, fuentes
