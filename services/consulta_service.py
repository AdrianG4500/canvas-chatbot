from datetime import datetime
from models.db import get_db_connection
import openai
import time
from utils.helpers import limpiar_respuesta_openai, limpiar_y_separar
from flask import session

def obtener_respuesta_openai(pregunta, assistant_id):
    thread = openai.beta.threads.create()
    openai.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=pregunta
    )
    run = openai.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )
    while run.status not in ["completed", "failed"]:
        time.sleep(1)
        run = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
    messages = openai.beta.threads.messages.list(thread_id=thread.id)
    respuesta_bruta = messages.data[0].content[0].text.value
    texto_final, fuentes = limpiar_y_separar(respuesta_bruta)
    return texto_final, fuentes
