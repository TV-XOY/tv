import gzip
import xml.etree.ElementTree as ET
from datetime import datetime
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

URL = "https://www.reportv.com.ar/finder/index/3129/MnTip-Programacion"

def parse_time(time_str):
    now = datetime.now()
    try:
        # Convierte formatos "14:30 hs" o similares a estándar XMLTV
        time_str = time_str.lower().replace("hs.", "").replace("hs", "").strip()
        hours, minutes = time_str.split(":")
        dt = now.replace(hour=int(hours), minute=int(minutes), second=0, microsecond=0)
        return dt.strftime("%Y%m%d%H%M%S +0000")
    except Exception:
        return now.strftime("%Y%m%d%H%M%S +0000")

def main():
    print("Iniciando navegador automatizado Playwright...")
    html_content = ""
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_viewport_size({"width": 1440, "height": 900})
            
            print(f"Navegando a: {URL}")
            page.goto(URL, wait_until="networkidle", timeout=60000)
            
            # Forzamos la carga simulando scrolls pausados para el lazy-loading
            print("Bajando por la grilla para despertar los elementos dinámicos...")
            for i in range(15):
                page.evaluate("window.scrollBy(0, 1200)")
                page.wait_for_timeout(2000) # Espera técnica para que los canales aparezcan
                
            html_content = page.content()
            browser.close()
    except Exception as e:
        print(f"Error crítico en el navegador virtual: {e}")
        return

    if not html_content:
        print("Error: El HTML recuperado está vacío.")
        return

    soup = BeautifulSoup(html_content, 'html.parser')
    tv = ET.Element("tv", {"generator-info-name": "StarTV HTML-DOM Grabber"})
    
    # --- MÉTODO POR EXTRACCIÓN DE DOM (CONTENEDORES REALES) ---
    # ReporTV Finder organiza la grilla mediante filas de canales. Intentamos capturar los layouts más comunes:
    filas_canales = soup.find_all("div", class_=re.compile(r"channel|row|grid|item", re.I)) or soup.find_all("tr")
    print(f"Filas potenciales detectadas en el código: {len(filas_canales)}")
    
    canales_procesados = set()
    programas_agregados = 0

    # Si la estructura jerárquica no se detecta, mapeamos de forma plana pero buscando tags exactos
    # Buscamos nombres de canales e información adyacente
    for fila in filas_canales:
        texto_fila = fila.get_text(" | ", strip=True)
        # Ignorar encabezados comunes del sitio
        if "buscar" in texto_fila.lower() or "menú" in texto_fila.lower():
            continue
            
        # Intentamos extraer de forma limpia el nombre del canal y bloques de hora
        partes = [p.strip() for p in texto_fila.split("|") if p.strip()]
        
        if len(partes) >= 2:
            # Buscaremos si alguna de las partes contiene un patrón de hora (ej: 21:00)
            horas = [p for p in partes if re.search(r"\d{2}:\d{2}", p)]
            # Los bloques que no son horas ni números muy cortos suelen ser nombres de canal o programas
            textos_limpios = [p for p in partes if p not in horas and len(p) > 2]
            
            if textos_limpios and horas:
                canal_nombre = textos_limpios[0]
                channel_id = canal_nombre.lower().replace(" ", "_").replace("ñ", "n")
                channel_id = re.sub(r'[^a-z0-9_]', '', channel_id) # Limpieza estricta de ID
                
                # Registrar el canal si es nuevo
                if channel_id not in canales_procesados:
                    channel_el = ET.SubElement(tv, "channel", id=channel_id)
                    ET.SubElement(channel_el, "display-name").text = canal_nombre
                    
                    # Intentar inyectar su logo correspondiente buscando dentro de la misma fila
                    img_tag = fila.find("img")
                    if img_tag and img_tag.get("src"):
                        ET.SubElement(channel_el, "icon", src=img_tag.get("src"))
                        
                    canales_procesados.add(channel_id)
                
                # Asignar programas usando las horas detectadas
                for hora in horas:
                    titulo_programa = textos_limpios[1] if len(textos_limpios) > 1 else f"Programación {canal_nombre}"
                    start_formatted = parse_time(hora)
                    
                    prog_el = ET.SubElement(tv, "programme", start=start_formatted, stop=start_formatted, channel=channel_id)
                    ET.SubElement(prog_el, "title", lang="es").text = titulo_programa[:100]
                    programas_agregados += 1

    # --- MÉTODO DE RESPALDO ABSOLUTO SI EL ANTERIOR DA 0 CANALES ---
    if len(canales_procesados) == 0:
        print("La estructura DOM falló. Iniciando parseo de emergencia por bloques 'hs'...")
        # Buscaremos cualquier bloque de texto en la página que tenga formato de hora y lo ligaremos
        elementos_texto = soup.find_all(text=True)
        canal_actual = "canal_generico"
        
        for elem in elementos_texto:
            texto = elem.strip()
            if not texto or len(texto) < 3:
                continue
                
            # Si el texto parece un canal (Mayúsculas o nombres conocidos sin hora)
            if not re.search(r"\d{2}:\d{2}", texto) and len(texto) < 40 and texto.isupper():
                canal_actual = texto.lower().replace(" ", "_")
                if canal_actual not in canales_procesados:
                    channel_el = ET.SubElement(tv, "channel", id=canal_actual)
                    ET.SubElement(channel_el, "display-name").text = texto
                    canales_procesados.add(canal_actual)
            
            # Si el texto contiene horas, es un programa de ese último canal detectado
            elif re.search(r"\d{2}:\d{2}", texto):
                hora_match = re.search(r"(\d{2}:\d{2})", texto)
                if hora_match:
                    hora = hora_match.group(1)
                    titulo = texto.replace(hora, "").replace("hs", "").replace(".", "").strip()
                    if not titulo:
                        titulo = "Programación Regular"
                        
                    start_formatted = parse_time(hora)
                    prog_el = ET.SubElement(tv, "programme", start=start_formatted, stop=start_formatted, channel=canal_actual)
                    ET.SubElement(prog_el, "title", lang="es").text = titulo
                    programas_agregados += 1

    # Guardado del archivo comprimido obligatoriamente
    xml_data = ET.tostring(tv, encoding="utf-8")
    with gzip.open("guia-starttv.xml.gz", "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n' + xml_data)
        
    print(f"--- REPORTE FINAL ---")
    print(f"Canales añadidos con éxito al XML: {len(canales_procesados)}")
    print(f"Programas mapeados con éxito al XML: {programas_agregados}")

if __name__ == "__main__":
    main()
