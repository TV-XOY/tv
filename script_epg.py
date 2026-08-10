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
    with sync_playwright() as p:
        # Iniciamos Chromium de manera oculta
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Simulamos una pantalla estándar de PC para el renderizado correcto
        page.set_viewport_size({"width": 1280, height: 720})
        print(f"Abriendo: {URL}")
        page.goto(URL, wait_until="networkidle")
        
        # --- FUNCIÓN CRUCIAL: SCROLL AUTOMÁTICO HASTA EL FINAL ---
        print("Realizando scroll para forzar la carga de todos los canales...")
        posicion_anterior = 0
        while True:
            # Desplaza la página 1000 píxeles hacia abajo
            page.evaluate("window.scrollBy(0, 1000)")
            page.wait_for_timeout(1200) # Espera un segundo a que cargue el contenido nuevo
            
            # Verificamos si la altura de la página ha dejado de crecer
            posicion_actual = page.evaluate("window.pageYOffset || document.documentElement.scrollTop")
            if posicion_actual == posicion_anterior:
                print("Se llegó al final del catálogo de ReporTV.")
                break
            posicion_anterior = posicion_actual
        
        # Una espera final para asegurar las últimas imágenes y textos cargados
        page.wait_for_timeout(3000)
        html_content = page.content()
        browser.close()
        
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Creamos el documento XMLTV estándar para IPTV
    tv = ET.Element("tv", {"generator-info-name": "StarTV Full EPG Grabber"})
    
    # Extraemos el texto completo para el procesado de patrones
    texto_pagina = soup.get_text(" ", strip=True)
    
    # Patrón nativo de bloques de ReporTV Finder: {NOMBRE} CANAL - NUMERO
    patron_canales = r"\{([^}]+)\}\s*([^-\n]+)-\s*(\d+)"
    canales_encontrados = re.findall(patron_canales, texto_pagina)
    
    print(f"Canales detectados en total tras el scroll: {len(canales_encontrados)}")
    
    canales_procesados = set()
    programas_agregados = 0
    
    # También intentaremos buscar las imágenes (logos) de los canales si están disponibles en el HTML
    imagenes_src = {}
    for img in soup.find_all("img"):
        alt_text = img.get("alt", "").strip().lower()
        src_url = img.get("src", "")
        if alt_text and src_url:
            imagenes_src[alt_text] = src_url

    if canales_encontrados:
        for canal_tag, canal_nombre, canal_numero in canales_encontrados:
            channel_id = f"canal_{canal_numero}"
            canal_nombre_limpio = canal_nombre.strip()
            
            # 1. Agregar el canal al EPG con su respectiva información
            if channel_id not in canales_procesados:
                channel_el = ET.SubElement(tv, "channel", id=channel_id)
                ET.SubElement(channel_el, "display-name").text = f"{canal_nombre_limpio}"
                
                # Intentar asociar la imagen de logo capturada si existe coincidencia
                nombre_busqueda = canal_nombre_limpio.lower()
                if nombre_busqueda in imagenes_src:
                    ET.SubElement(channel_el, "icon", src=imagenes_src[nombre_busqueda])
                    
                canales_procesados.add(channel_id)
            
            # 2. Localizar y extraer programas y horarios dentro de su bloque de texto correspondiente
            pos = texto_pagina.find(f"{{{canal_tag}}}")
            # Cortamos un fragmento de texto adelante del canal para leer su programación
            fragmento = texto_pagina[pos:pos+1500] 
            
            # Buscamos estructuras del tipo: "Nombre Programa 18:30hs" o "18:30hs. Nombre Programa"
            bloques_programa = re.split(r"(\d{2}:\d{2})\s*hs\.?", fragmento)
            
            if len(bloques_programa) > 1:
                # Estructura limpia alternando horarios y títulos
                for i in range(1, len(bloques_programa), 2):
                    hora = bloques_programa[i]
                    # El título suele ser el texto continuo antes del siguiente corte
                    titulo = bloques_programa[i+1].strip() if (i+1) < len(bloques_programa) else ""
                    
                    # Limpieza básica para evitar títulos basura
                    titulo = titulo.split(";")[0].split("{")[0].strip()
                    
                    if titulo and len(titulo) > 2 and "grilla de canales" not in titulo.lower():
                        start_formatted = parse_time(hora)
                        prog_el = ET.SubElement(tv, "programme", start=start_formatted, stop=start_formatted, channel=channel_id)
                        ET.SubElement(prog_el, "title", lang="es").text = titulo[:100]
                        programas_agregados += 1
            else:
                # Respaldo si el formato de texto viene plano
                horas_genericas = re.findall(r"(\d{2}:\d{2})\s*hs", fragmento, re.IGNORECASE)
                for h in horas_genericas:
                    start_formatted = parse_time(h)
                    prog_el = ET.SubElement(tv, "programme", start=start_formatted, stop=start_formatted, channel=channel_id)
                    ET.SubElement(prog_el, "title", lang="es").text = f"Programación {canal_nombre_limpio}"
                    programas_agregados += 1

    # Guardado y compresión final en GZIP para que tu IPTV lo acepte
    xml_data = ET.tostring(tv, encoding="utf-8")
    with gzip.open("guia-starttv.xml.gz", "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n' + xml_data)
        
    print(f"--- GENERACIÓN EXITOSA ---")
    print(f"Total canales empaquetados: {len(canales_procesados)}")
    print(f"Total programas indexados: {programas_agregados}")

if __name__ == "__main__":
    main()
