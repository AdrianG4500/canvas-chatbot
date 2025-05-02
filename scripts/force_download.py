import requests

url = "http://localhost:5000/descargar"
response = requests.get(url)
print(response.json())