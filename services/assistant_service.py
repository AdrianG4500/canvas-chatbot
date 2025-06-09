from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def crear_nuevo_asistente(nombre_curso):
    vector_store = client.vector_stores.create(name=f"Vector Store - {nombre_curso}")
    assistant = client.beta.assistants.create(
        name=f"Asistente - {nombre_curso}",
        instructions="Eres un asistente especializado en este curso.",
        model="gpt-4.1",
        tools=[{"type": "file_search"}],
        tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
    )
    return {
        "assistant_id": assistant.id,
        "vector_store_id": vector_store.id
    }