# canvas/downloader.py

import os
import requests
from config import CANVAS_TOKEN, CANVAS_BASE_URL, COURSE_ID, TEMP_DIR

def get_all_course_files():
    headers = { "Authorization": f"Bearer {CANVAS_TOKEN}" }
    url = f"{CANVAS_BASE_URL}/courses/{COURSE_ID}/files"
    params = {'per_page': 100}
    todos_los_archivos = []

    while url:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            raise Exception(f"Error al obtener archivos: {response.text}")
        archivos = response.json()
        todos_los_archivos.extend(archivos)

        # Procesar encabezado Link para detectar si hay otra página
        next_url = None
        if 'Link' in response.headers:
            links = response.headers['Link'].split(',')
            for link in links:
                if 'rel=\"next\"' in link:
                    next_url = link[link.find('<') + 1:link.find('>')]
                    break
        url = next_url
        params = None

    return todos_los_archivos

def download_file(file_info):
    file_name = file_info['filename'].replace(' ', '_')
    download_url = file_info['url']

    response = requests.get(download_url, headers={
        "Authorization": f"Bearer {CANVAS_TOKEN}"
    })

    if response.status_code != 200:
        raise Exception(f"Error al descargar archivo: {response.text}")

    # Asegurar que /tmp exista en local
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

    file_path = os.path.join(TEMP_DIR, file_name)
    with open(file_path, 'wb') as f:
        f.write(response.content)

    return file_path
