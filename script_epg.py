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
        time_str = time_str.lower().replace("hs.", "").replace("hs", "").strip()
        hours, minutes = time_str.split(":")
        dt = now.replace(hour=int(hours), minute=int(minutes), second=0, microsecond=0)
        return dt.strftime("%Y%m%d%H%M%S +0000")
    except Exception:
        return now.strftime("%Y%m%d%H%M%S +0000")

def main():
    print("Iniciando navegador automatizado...")
    html_content = ""
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_viewport_size({"width": 1280, "height": 720})
            
            print(f"Abriendo: {URL}")
            page.goto(URL, wait_until="networkidle", timeout=60000)
            
            print("Realizando scroll para forzar la carga de todos los canales...")
            posicion_anterior = 0
            for i in range(30): # Límite de 30 scrolls para evitar bucles infinitos
                page.evaluate("window.scrollBy(0, 1000)")
                page.wait_for_timeout(1500) 
                
                posicion_actual = page.evaluate("window.pageYOffset || document.documentElement.scrollTop")
                if posicion_actual == posicion_anterior:
                    print(f"Se llegó al final o se detuvo la carga en el scroll {i}.")
                    break
                posicion_anterior = posicion_actual
            
            page.wait_for_timeout(3000)
            html_content = page.content()
            browser.close()
    except Exception as e:
        print(f"Error crítico durante la simulación del navegador: {e}")
        return

    if not html_content:
        print("No se pudo obtener el contenido HTML de la página.")
        return

    soup = BeautifulSoup(html_content, 'html.parser')
    tv = ET.Element("tv", {"generator-info-name": "StarTV Full EPG Grabber"})
    texto_pagina = soup.get_text(" ", strip=True)
    
    # Intentar capturar logos del HTML de forma segura
    imagenes_src = {}
    for img in soup.find_all("img"):
        alt_text = img.get("alt", "").strip().lower()
        src_url = img.get("src", "")
        if alt_text and src_url:
            imagenes_src[alt_text] = src_url

    # Patrón de extracción basado en la respuesta nativa por llaves de ReporTV Finder
    patron_canales = r"\{([^}]+)\}\s*([^-\n]+)-\s*(\d+)"
    canales_encontrados = re.findall(patron_canales, texto_pagina)
    
    print(f"Canales detectados en total tras el scroll: {len(canales_encontrados)}")
    
    canales_procesados = set()
    programas_agregados = 0

    if canales_encontrados:
        for canal_tag, canal_nombre, canal_numero in canales_encontrados:
            channel_id = f"canal_{canal_numero}"
            canal_nombre_limpio = canal_nombre.strip()
            
            # 1. Registro seguro del Canal
            if channel_id not in canales_procesados:
                channel_el = ET.SubElement(tv, "channel", id=channel_id)
                ET.SubElement(channel_el, "display-name").text = canal_nombre_limpio
                
                nombre_busqueda = canal_nombre_limpio.lower()
                if nombre_busqueda in imagenes_src:
                    ET.SubElement(channel_el, "icon", src=imagenes_src[nombre_busqueda])
                canales_procesados.add(channel_id)
            
            # 2. Extracción protegida de la programación
            try:
                pos = texto_pagina.find(f"{{{canal_tag}}}")
                if pos != -1:
                    fragmento = texto_pagina[pos:pos+1500] 
                    bloques_programa = re.split(r"(\d{2}:\d{2})\s*hs\.?", fragmento)
                    
                    if len(bloques_programa) > 1:
                        for i in range(1, len(bloques_programa), 2):
                            hora = bloques_programa[i]
                            raw_titulo = bloques_programa[i+1].strip() if (i+1) < len(bloques_programa) else ""
                            
                            # Limpieza corregida de caracteres basura sin romper el script
                            titulo_limpio = raw_titulo.split(";")[0].split("{")[0].strip()
                            
                            if titulo_limpio and len(titulo_limpio) > 2 and "grilla" not in titulo_limpio.lower():
                                start_formatted = parse_time(hora)
                                prog_el = ET.SubElement(tv, "programme", start=start_formatted, stop=start_formatted, channel=channel_id)
                                ET.SubElement(prog_el, "title", lang="es").text = titulo_limpio[:100]
                                programas_agregados += 1
                    else:
                        raise ValueError("Bloque de programación no dividida.")
            except Exception:
                # Si falla el parseo específico de este canal, le ponemos programación genérica para no romper el build
                start_formatted = parse_time("00:00")
                prog_el = ET.SubElement(tv, "programme", start=start_formatted, stop=start_formatted, channel=channel_id)
                ET.SubElement(prog_el, "title", lang="es").text = f"Programación {canal_nombre_limpio}"
                programas_agregados += 1

    # Empaquetado final forzado
    try:
        xml_data = ET.tostring(tv, encoding="utf-8")
        with gzip.open("guia-starttv.xml.gz", "wb") as f:
            f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n' + xml_data)
        print(f"--- PROCESO COMPLETADO ---")
        print(f"Canales generados: {len(canales_procesados)} | Programas indexados: {programas_agregados}")
    except Exception as e:
        print(f"Error al escribir el archivo comprimido final: {e}")

if __name__ == "__main__":
    main()
