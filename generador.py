import json
import gzip
from datetime import datetime, timedelta

# 1. Calcular fechas de hoy y mañana restando 6 horas para Mérida (UTC-6)
ahora_utc = datetime.utcnow()
ahora_merida = ahora_utc - timedelta(hours=6)
manana_merida = ahora_merida + timedelta(days=1)

# Fechas en formato AAAAMMDD para el reproductor IPTV
hoy_str = ahora_merida.strftime("%Y%m%d")
manana_str = manana_merida.strftime("%Y%m%d")

# --- ¡AQUÍ ESTABA EL ERROR CORREGIDO! ---
# Cambiamos %l por %A para que detecte "Monday", "Tuesday", etc.
dia_hoy = ahora_merida.strftime("%A").strip()
dia_manana = manana_merida.strftime("%A").strip()

# 2. Leer tu archivo de programación semanal
with open("plantilla.json", "r", encoding="utf-8") as f:
    plantilla = json.load(f)

# 3. Iniciar la estructura XMLTV limpia
xml_lines = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<tv generator-info-name="GitHub_EPG_Merida">',
]

# Agregar los canales que declaraste en tu JSON
if "canales" in plantilla:
    for canal_id, canal_nombre in plantilla["canales"].items():
        xml_lines.append(f'  <channel id="{canal_id}"><display-name>{canal_nombre}</display-name></channel>')

def agregar_programas(dia_nombre, fecha_cadena):
    programas = plantilla.get(dia_nombre, [])
    lines = []
    for p in programas:
        # Estampa el horario de Mérida con la etiqueta "-0600" para que el reproductor no se desphase
        lines.append(f'  <programme start="{fecha_cadena}{p["start"]} -0600" stop="{fecha_cadena}{p["stop"]} -0600" channel="{p["channel"]}">')
        lines.append(f'    <title lang="es">{p["title"]}</title>')
        lines.append('  </programme>')
    return lines

# Inyectar la programación de hoy y la de mañana
xml_lines.extend(agregar_programas(dia_hoy, hoy_str))
xml_lines.extend(agregar_programas(dia_manana, manana_str))
xml_lines.append('</tv>')

xml_final = "\n".join(xml_lines)

# 4. Guardar y comprimir todo directamente en el archivo mx.xml.gz
with gzip.open("mx.xml.gz", "wb") as f:
    f.write(xml_final.encode("utf-8"))

print(f"¡EPG generado con éxito en GitHub para {dia_hoy} y {dia_manana}!")
