import requests

url = "https://www.runtime.tv/?section=epgchannelssection" # Cambia esto por la URL que estás usando actualmente

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

response = requests.get(url, headers=headers)

print(f"Código de estado HTTP: {response.status_code}")
print("Primeros 500 caracteres de la respuesta:")
print(response.text[:500])

# Intentar procesar solo si el estado es correcto
if response.status_code == 200:
    try:
        data = response.json()
        print("¡Éxito! La respuesta es un JSON válido.")
    except Exception as e:
        print(f"Error al convertir a JSON: {e}")
else:
    print("El servidor rechazó la petición o la página no existe.")
