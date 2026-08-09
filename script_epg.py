import gzip
import xml.etree.ElementTree as ET
from datetime import datetime
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

URL = "https://www.reportv.com.ar/finder/index/3129/MnTip-Programacion"

def parse_time(time_str):
    now = datetime.now()
    try:
        # Intenta limpiar formatos comunes de hora como "14:30 hs."
        hours, minutes = time_str.replace("hs.", "").replace("hs", "").strip().split(":")
        dt = now.replace(hour=int(hours), minute=int(minutes), second=0, microsecond=0)
        return dt.strftime("%Y%m%d%H%M%S +0000")
    except Exception:
        return now.strftime("%Y%m%d%H%M%S +0000")

def main():
    print("Iniciando navegador virtual...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print(f"Cargando la url: {URL}")
        page.goto(URL, wait_until="networkidle")
        
        # Espera explicita de 6 segundos para asegurar que la grilla dinamica cargue
        page.wait_for_timeout(6000) 
        
        # Capturamos el HTML real ya renderizado por JavaScript
        html_content = page.content()
        browser.close()
        
    soup = BeautifulSoup(html_content, 'html.parser')
    tv = ET.Element("tv", {"generator-info-name": "StarTV EPG Grabber"})
    
    # ReporTV Finder suele renderizar los canales dentro de tablas (.table) o filas de clases específicas
    # Buscamos filas de datos comunes de grillas de programacion
    filas = soup.find_all("tr")
    
    if not filas:
        # Intento alternativo si usan divs en lugar de tablas en la nueva version
        filas = soup.find_all("div", class_="row")
        
    print(f"Filas encontradas para procesar: {len(filas)}")
    
    canales_procesados = set()
    programas_agregados = 0
    
    for fila in filas:
        texto = [t.strip() for t in fila.get_text(separator="|", strip=True).split("|") if t.strip()]
        
        # Filtrado basico para extraer (Canal, Programa, Hora)
        if len(texto) >= 2:
            # Estructura tentativa basada en la visualizacion clasica del Finder
            channel_name = texto[0]
            title_prog = texto[1]
            hora_inicio = texto[2] if len(texto) > 2 else "00:00"
            
            channel_id = channel_name.replace(" ", "_").lower().replace("ñ", "n")
            
            if channel_id not in canales_procesados and len(channel_id) > 1:
                channel_el = ET.SubElement(tv, "channel", id=channel_id)
                ET.SubElement(channel_el, "display-name").text = channel_name
                canales_procesados.add(channel_id)
            
            if len(channel_id) > 1:
                start_formatted = parse_time(hora_inicio)
                prog_el = ET.SubElement(tv, "programme", start=start_formatted, stop=start_formatted, channel=channel_id)
                ET.SubElement(prog_el, "title", lang="es").text = title_prog
                programas_agregados += 1

    # Empaquetado y compresion en GZIP
    xml_data = ET.tostring(tv, encoding="utf-8")
    with gzip.open("guia-starttv.xml.gz", "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n' + xml_data)
        
    print(f"Proceso completado. Canales: {len(canales_procesados)}. Programas: {programas_agregados}")

if __name__ == "__main__":
    main()
