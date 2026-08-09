import gzip
import xml.etree.ElementTree as ET
from datetime import datetime
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

URL = "https://www.reportv.com.ar/finder/index/3129/MnTip-Programacion"

def parse_time(time_str):
    now = datetime.now()
    try:
        # Limpia formatos de texto del tipo "10:30hs." o "09:45 hs"
        time_str = time_str.lower().replace("hs.", "").replace("hs", "").strip()
        hours, minutes = time_str.split(":")
        dt = now.replace(hour=int(hours), minute=int(minutes), second=0, microsecond=0)
        return dt.strftime("%Y%m%d%H%M%S +0000")
    except Exception:
        return now.strftime("%Y%m%d%H%M%S +0000")

def main():
    print("Iniciando navegador virtual para cargar ReporTV...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.goto(URL, wait_until="networkidle")
        # Espera de 8 segundos para garantizar que el JavaScript cargue todo el texto de la grilla
        page.wait_for_timeout(8000) 
        
        html_content = page.content()
        browser.close()
        
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extraemos absolutamente todo el texto visible renderizado en la pagina
    texto_pagina = soup.get_text(" ", strip=True)
    
    # Creamos la estructura XMLTV base
    tv = ET.Element("tv", {"generator-info-name": "StarTV EPG Parser"})
    
    # Expresión regular diseñada para detectar la estructura de canales de ReporTV Finder:
    # Ejemplo: {IMAGEN TELEVISION} IMAGEN TELEVISION - 103 o CANAL 5 - 105.
    patron_canales = r"\{([^}]+)\}\s*([^-\n]+)-\s*(\d+)"
    canales_encontrados = re.findall(patron_canales, texto_pagina)
    
    print(f"Texto total analizado: {len(texto_pagina)} caracteres.")
    print(f"Canales detectados por patrones: {len(canales_encontrados)}")
    
    canales_procesados = set()
    programas_agregados = 0

    # Si la expresión regular por llaves falla, hacemos un parseo alternativo por bloques de texto limpios
    if not canales_encontrados:
        print("Buscando por bloques de texto alternativos...")
        # Fragmentamos el texto por puntos y comas o guiones comunes en la plataforma
        bloques = [b.strip() for b in texto_pagina.split(";") if b.strip()]
        for bloque in bloques:
            # Detecta si el bloque contiene un canal con numero y formato de hora (Ej: CANAL 5 - 105 ... 10:00hs)
            if "-" in bloque and "hs" in bloque.lower():
                partes = bloque.split(".")
                for parte in partes:
                    if "-" in parte and "hs" in parte.lower():
                        # Extraer canal básico
                        info_canal = parte.split("-")[0].strip()
                        channel_id = info_canal.replace(" ", "_").lower().replace("ñ", "n")
                        
                        if channel_id and channel_id not in canales_procesados:
                            channel_el = ET.SubElement(tv, "channel", id=channel_id)
                            ET.SubElement(channel_el, "display-name").text = info_canal
                            canales_procesados.add(channel_id)
                            
                        # Buscar hora y titulo tentativo dentro del fragmento
                        horas = re.findall(r"(\d{2}:\d{2})\s*hs", parte, re.IGNORECASE)
                        hora_inicio = horas[0] if horas else "00:00"
                        titulo = parte.split("hs")[-1].strip() if horas else parte
                        
                        if len(channel_id) > 1 and titulo:
                            start_formatted = parse_time(hora_inicio)
                            prog_el = ET.SubElement(tv, "programme", start=start_formatted, stop=start_formatted, channel=channel_id)
                            ET.SubElement(prog_el, "title", lang="es").text = titulo[:60] # Acorta titulos basura muy largos
                            programas_agregados += 1
    else:
        # Si encontro la estructura nativa de llaves de la API interna de ReporTV
        for canal_tag, canal_nombre, canal_numero in canales_encontrados:
            channel_id = f"canal_{canal_numero}"
            canal_nombre_limpio = canal_nombre.strip()
            
            if channel_id not in canales_procesados:
                channel_el = ET.SubElement(tv, "channel", id=channel_id)
                ET.SubElement(channel_el, "display-name").text = f"{canal_nombre_limpio} ({canal_numero})"
                canales_procesados.add(channel_id)
            
            # Buscar horarios relacionados cerca del bloque del canal
            # Buscaremos segmentos de texto asociados a este canal en la pagina
            pos = texto_pagina.find(f"{{{canal_tag}}}")
            fragmento = texto_pagina[pos:pos+500] # Analiza los siguientes 500 caracteres del canal
            
            horas = re.findall(r"(\d{2}:\d{2})\s*hs", fragmento, re.IGNORECASE)
            if horas:
                for hora in horas:
                    start_formatted = parse_time(hora)
                    prog_el = ET.SubElement(tv, "programme", start=start_formatted, stop=start_formatted, channel=channel_id)
                    # Tomar texto posterior a la hora como titulo tentativo del programa
                    ET.SubElement(prog_el, "title", lang="es").text = f"Programacion {canal_nombre_limpio}"
                    programas_agregados += 1

    # Compresion en GZIP obligatoria para IPTV
    xml_data = ET.tostring(tv, encoding="utf-8")
    with gzip.open("guia-starttv.xml.gz", "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n' + xml_data)
        
    print(f"Proceso finalizado con exito. Canales XML creados: {len(canales_procesados)}. Programas mapeados: {programas_agregados}")

if __name__ == "__main__":
    main()
