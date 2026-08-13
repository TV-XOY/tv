import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# 1. Obtener los datos (Runtime suele usar APIs internas en JSON)
url = "https://api-ott.runtime.tv" # Cambia por la URL exacta de la API detectada en la pestaña Network del navegador
response = requests.get(url)
data = response.json()

# 2. Crear la estructura básica de un archivo XMLTV
tv = ET.Element('tv')

# Aquí recorres la respuesta JSON para mapear los canales y programas
for channel_data in data.get('channels', []):
    channel = ET.SubElement(tv, 'channel', id=channel_data['id'])
    display_name = ET.SubElement(channel, 'display-name')
    display_name.text = channel_data['name']
    
    for prog in channel_data.get('programs', []):
        programme = ET.SubElement(tv, 'programme', 
                                  start=prog['start_time'], 
                                  stop=prog['end_time'], 
                                  channel=channel_data['id'])
        title = ET.SubElement(programme, 'title')
        title.text = prog['title']

# 3. Guardar el archivo resultante
tree = ET.ElementTree(tv)
tree.write("runtime_epg.xml", encoding="utf-8", xml_declaration=True)
