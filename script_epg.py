import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import gzip
from datetime import datetime

URL = "https://www.reportv.com.ar/finder/index/3129/MnTip-Programacion"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def parse_time(time_str):
    # Formatea la hora actual con el horario del programa para el estandar XMLTV
    now = datetime.now()
    try:
        hours, minutes = time_str.replace("hs.", "").strip().split(":")
        dt = now.replace(hour=int(hours), minute=int(minutes), second=0, microsecond=0)
        return dt.strftime("%Y%m%d%H%M%S +0000")
    except Exception:
        return now.strftime("%Y%m%d%H%M%S +0000")

def main():
    response = requests.get(URL, headers=headers)
    if response.status_code != 200:
        print(f"Error al acceder a la pagina: {response.status_code}")
        return
        
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Crear la raiz del documento XMLTV
    tv = ET.Element("tv", {"generator-info-name": "StarTV EPG Grabber"})
    
    # Buscar elementos de canales y programas en el HTML de ReporTV
    # Adaptado a la estructura estandar del contenedor de filas del Finder
    filas = soup.find_all("tr") or soup.find_all("div", class_="row") 
    
    canales_procesados = set()
    
    # Procesar filas para extraer canales y programas
    for idx, fila in enumerate(filas):
        texto = fila.get_text(separator="|", strip=True).split("|")
        # El Finder suele estructurar: [Nombre Canal, Titulo Programa, Hora Inicio, Hora Fin]
        if len(texto) >= 3:
            channel_name = texto[0]
            title_prog = texto[1]
            hora_inicio = texto[2]
            
            channel_id = channel_name.replace(" ", "_").lower()
            
            # Registrar el canal si no se ha hecho
            if channel_id not in canales_procesados:
                channel_el = ET.SubElement(tv, "channel", id=channel_id)
                ET.SubElement(channel_el, "display-name").text = channel_name
                canales_procesados.add(channel_id)
            
            # Registrar el programa
            start_formatted = parse_time(hora_inicio)
            prog_el = ET.SubElement(tv, "programme", start=start_formatted, stop=start_formatted, channel=channel_id)
            ET.SubElement(prog_el, "title", lang="es").text = title_prog

    # Guardar en archivo comprimido .xml.gz
    xml_data = ET.tostring(tv, encoding="utf-8")
    with gzip.open("guia-starttv.xml.gz", "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n' + xml_data)
        
    print("Archivo guia-starttv.xml.gz generado con exito.")

if __name__ == "__main__":
    main()
