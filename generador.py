import json
import gzip
from datetime import datetime, timedelta

# 1. Calcular fechas de hoy y mañana
ahora = datetime.utcnow()
hoy_str = ahora.strftime("%Y%m%d")
manana_str = (ahora + timedelta(days=1)).strftime("%Y%m%d")

dia_hoy = ahora.strftime("%l").strip()
dia_manana = (ahora + timedelta(days=1)).strftime("%l").strip()

# 2. Leer la plantilla de programación
with open("plantilla.json", "r", encoding="utf-8") as f:
    plantilla = json.load(f)

# 3. Construir el archivo XML de la guía
xml_lines = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<tv generator-info-name="GitHub_EPG_Robot">',
    '  <channel id="Canal1.tv"><display-name>Mi Canal Fijo</display-name></channel>'
]

def agregar_programas(dia_nombre, fecha_cadena):
    programas = plantilla.get(dia_nombre, [])
    lines = []
    for p in programas:
        lines.append(f'  <programme start="{fecha_cadena}{p["start"]} +0000" stop="{fecha_cadena}{p["stop"]} +0000" channel="{p["channel"]}">')
        lines.append(f'    <title lang="es">{p["title"]}</title>')
        lines.append('  </programme>')
    return lines

# Inyectar bloques de hoy y mañana
xml_lines.extend(agregar_programas(dia_hoy, hoy_str))
xml_lines.extend(agregar_programas(dia_manana, manana_str))
xml_lines.append('</tv>')

xml_final = "\n".join(xml_lines)

# 4. Guardar comprimido directamente en formato .xml.gz
with gzip.open("mx.xml.gz", "wb") as f:
    f.write(xml_final.encode("utf-8"))

print("¡EPG mx.xml.gz generado con éxito!")

