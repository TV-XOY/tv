import json
import gzip
from datetime import datetime, timedelta

# 1. Calcular fechas de hoy y mañana restando 6 horas para Mérida (UTC-6)
ahora_utc = datetime.utcnow()
ahora_merida = ahora_utc - timedelta(hours=6)
manana_merida = ahora_merida + timedelta(days=1)

hoy_str = ahora_merida.strftime("%Y%m%d")
manana_str = manana_merida.strftime("%Y%m%d")

dia_hoy = ahora_merida.strftime("%A").strip()
dia_manana = manana_merida.strftime("%A").strip()

# 2. Leer tu archivo de programación plantilla.json
with open("plantilla.json", "r", encoding="utf-8") as f:
    plantilla = json.load(f)

# 3. Iniciar la estructura XMLTV con tu firma oficial de TV XOY
xml_lines = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<!-- Codigo by TV XOY generado por Gemini super IA -->',
    '<tv generator-info-name="Codigo by TV XOY generado por Gemini super IA">',
]

# Agregar los canales declarados
if "canales" in plantilla:
    for canal_id, canal_nombre in plantilla["canales"].items():
        xml_lines.append(f'  <channel id="{canal_id}"><display-name>{canal_nombre}</display-name></channel>')

def agregar_programas(dia_nombre, fecha_cadena):
    programas = plantilla.get(dia_nombre, [])
    lines = []
    for p in programas:
        lines.append(f'  <programme start="{fecha_cadena}{p["start"]} -0600" stop="{fecha_cadena}{p["stop"]} -0600" channel="{p["channel"]}">')
        lines.append(f'    <title lang="es">{p["title"]}</title>')
        
        # --- ¡AQUÍ ESTÁ LA CORRECCIÓN DE INYECCIÓN DE SINOPSIS E IMAGEN! ---
        if "desc" in p and p["desc"].strip():
            lines.append(f'    <desc lang="es">{p["desc"]}</desc>')
        if "icon" in p and p["icon"].strip():
            lines.append(f'    <icon src="{p["icon"]}" />')
            
        lines.append('  </programme>')
    return lines

# Inyectar programación de hoy y mañana
xml_lines.extend(agregar_programas(dia_hoy, hoy_str))
xml_lines.extend(agregar_programas(dia_manana, manana_str))
xml_lines.append('</tv>')

xml_final = "\n".join(xml_lines)

# 4. Guardar comprimido directamente en formato mx.xml.gz
with gzip.open("mx.xml.gz", "wb") as f:
    f.write(xml_final.encode("utf-8"))

print(f"¡EPG Premium generado con éxito para {dia_hoy} y {dia_manana}!")
