import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# 1. Obtener los datos (Runtime suele usar APIs internas en JSON)
url = "https://api-ott.runtime.tv/getvideosegments?banners=0&connection=wifi&days=3&device_height=900&device_id=37ab0879dbae63a4&device_ifa=00000000-0000-0000-0000-000000000000&device_manufacturer=samsung&device_model=SM-X910N&device_type=tablet&device_width=1600&dnt=0&for_user=0&image_format=widescreen&image_width=457&language=es&linear_channel_id=16107&parent_id=16107&parent_type=linear_channel&partner=android&platform=android&session_id=4a287f46603c892e457ec23c11e3886f09e9497c&start=0&timestamp=1786664580&timezone=-0600&use_device_width_widescreen=1&version=15.332&sign=rLbuS0uJ3X%2Fpb59wwBdm5JJeU35jT%252BVEZ7rQVuv3ST0%3D" # Cambia por la URL exacta de la API detectada en la pestaña Network del navegador
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
