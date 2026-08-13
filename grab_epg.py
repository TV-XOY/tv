import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime

url = "https://www.runtime.tv/?section=epgchannelssection"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    # Procesamos el HTML con BeautifulSoup en vez de usar .json()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Creamos la cabecera XML para el archivo EPG
    tv = ET.Element('tv')
    
    # --- EJEMPLO DE BÚSQUEDA ---
    # Aquí debes inspeccionar las clases HTML reales de Runtime.
    # Por ejemplo, si los canales están en etiquetas div con clase 'channel-item':
    canales_html = soup.find_all('div', class_='channel-item') 
    
    for idx, item in enumerate(canales_html):
        channel_name = item.find('span', class_='channel-name').text.strip()
        channel_id = f"runtime.{idx}"
        
        # Añadir canal al XML
        channel = ET.SubElement(tv, 'channel', id=channel_id)
        display_name = ET.SubElement(channel, 'display-name')
        display_name.text = channel_name
        
        # Repetir lógica similar para los bloques de programas del canal...
        
    # Guardar el archivo definitivo
    tree = ET.ElementTree(tv)
    tree.write("runtime_epg.xml", encoding="utf-8", xml_declaration=True)
    print("¡EPG XML generado con éxito a partir de la web!")
else:
    print(f"Error en la conexión web: Código {response.status_code}")
