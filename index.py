from zoneinfo import ZoneInfo
import time
import re
import urllib.request
import ssl
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DE ESTACIONES
# ==========================================
ESTACIONES_DIRECTEMAR = [
    {"nombre": "Capitanía de Puerto Constitución-7700", "url": "http://web.directemar.cl/met/jturno/estaciones/constitucion/index.htm", "lat": -35.333, "lon": -72.416},
    {"nombre": "Capitanía de Puerto Lirquén-7406", "url": "http://web.directemar.cl/met/jturno/estaciones/lirquen/index.htm", "lat": -36.716, "lon": -72.933},
    {"nombre": "Gobernación Marítima de Talcahuano", "url": "http://web.directemar.cl/met/jturno/estaciones/talcahuano/index.htm", "lat": -36.712, "lon": -73.115},
    {"nombre": "Capitanía de Puerto Coronel-7313", "url": "http://web.directemar.cl/met/jturno/estaciones/coronel/index.htm", "lat": -37.020, "lon": -73.150},
    {"nombre": "Capitanía de Puerto Lota-7373", "url": "http://web.directemar.cl/met/jturno/estaciones/lota/index.htm", "lat": -37.090, "lon": -73.150},
    {"nombre": "Capitanía de Puerto Lebu-7800", "url": "http://web.directemar.cl/met/jturno/estaciones/lebu/index.htm", "lat": -37.606, "lon": -73.650},
    {"nombre": "Capitanía de Puerto Carahue", "url": "http://web.directemar.cl/met/jturno/estaciones/carahue/index.htm", "lat": -38.788, "lon": -73.397},
    {"nombre": "Capitanía de Puerto Corral-1960", "url": "http://web.directemar.cl/met/jturno/estaciones/corral/index.htm", "lat": -39.883, "lon": -73.433}
]

ESTACIONES_FAROS = [
    {"nombre": "Faro Isla Quiriquina", "url": "https://www.wunderground.com/dashboard/pws/ITALCA20", "lat": -36.625, "lon": -73.033},
    {"nombre": "Faro Punta Hualpén", "url": "https://www.wunderground.com/dashboard/pws/IHUALP1", "lat": -36.745, "lon": -73.185}
]

TOLERANCIA_MINUTOS = 12

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def consultar_directemar(est):
    try:
        req = urllib.request.Request(est["url"], headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8, context=ctx) as response:
            html = response.read().decode('utf-8', errors='ignore')
            match = re.search(r'page updated\s+(\d{1,2}-\d{1,2}-\d{4}\s+\d{1,2}:\d{2})', html, re.IGNORECASE)
            if match:
                utc_z = ZoneInfo("UTC")
                chile_tz = ZoneInfo("America/Santiago")
                
                fecha_str_utc = match.group(1)
                fecha_estacion_utc = datetime.strptime(fecha_str_utc, "%d-%m-%Y %H:%M").replace(tzinfo=utc_tz) 
                fecha_estacion_chile = fecha_estacion_utc.astimezone(chile_tz)

                fecha_str = fecha_estacion_chile.strftime("%d-%m-%Y %H:%M)
                dif_min = int((datatime.now(chile_tz) - fecha_estacion_chile).total_seconds() / 60)
                
                if dif_min <= TOLERANCIA_MINUTOS:
                    return True, "OPERATIVA", fecha_str
                else:
                    return False, f"DESACTUALIZADA ({dif_min} min)", fecha_str
        return False, "SIN DATOS VÁLIDOS", "N/D"
    except Exception:
        return False, "SIN CONEXIÓN", "Error de red"

def generar_html(resultados_directemar, hay_alerta):
    total_estaciones = len(resultados_directemar) + len(ESTACIONES_FAROS)
    operativas = sum(1 for r in resultados_directemar if r["ok"])
    
    markers_js = ""
    for r in resultados_directemar:
        color = "green" if r["ok"] else "red"
        markers_js += f"""
        L.circleMarker([{r['lat']}, {r['lon']}], {{
            color: '{color}',
            fillColor: '{color}',
            fillOpacity: 0.8,
            radius: 9
        }}).addTo(map).bindPopup("<b>{r['nombre']}</b><br>Estado: {r['estado']}<br>Reporte: {r['ultimo']}<br><a href='{r['url']}' target='_blank'>Abrir enlace ↗</a>");
        """

    for faro in ESTACIONES_FAROS:
        markers_js += f"""
        L.circleMarker([{faro['lat']}, {faro['lon']}], {{
            color: 'blue',
            fillColor: '#3498db',
            fillOpacity: 0.8,
            radius: 8
        }}).addTo(map).bindPopup("<b>{faro['nombre']}</b><br>Acceso Directo PWS<br><a href='{faro['url']}' target='_blank'>Abrir enlace ↗</a>");
        """

    cards_html = ""
    for r in resultados_directemar:
        clase = "ok" if r["ok"] else "error"
        icono = "🟢" if r["ok"] else "🔴"
        cards_html += f"""
        <a href="{r['url']}" target="_blank" class="card-link">
            <div class="card {clase}">
                <strong>{r['nombre']}</strong>
                <div class="status">{icono} {r['estado']}</div>
                <div class="time">Último reporte: {r['ultimo']}</div>
                <div class="click-text">Clic para abrir ↗</div>
            </div>
        </a>
        """

    for faro in ESTACIONES_FAROS:
        cards_html += f"""
        <a href="{faro['url']}" target="_blank" class="card-link">
            <div class="card warning">
                <strong>{faro['nombre']}</strong>
                <div class="status">🔵 ACCESO PWS</div>
                <div class="time">Revisión manual</div>
                <div class="click-text">Clic para abrir ↗</div>
            </div>
        </a>
        """

    alerta_class = "alerta-activa" if hay_alerta else ""
    alerta_banner = '<div class="banner-alerta">⚠️ ¡ATENCIÓN: HAY ESTACIONES CON FALLAS O DESACTUALIZADAS! ⚠️</div>' if hay_alerta else ''

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="30">
    <title>Mapa Estaciones Automaticas - Constitución a Corral</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body {{ font-family: Arial, sans-serif; background-color: #f4f6f9; padding: 15px; margin: 0; }}
        h1 {{ text-align: center; color: #1a252f; margin-bottom: 0px; font-size: 22px; line-height: 1.1; }}
        .subtitle-line2 {{ text-align: center; color: #1a252f; margin-bottom: 10px; font-size: 18px; font-weight: bold; }}
        .subtitle {{ text-align: center; color: #7f8c8d; margin-bottom: 10px; font-size: 13px; }}
        .summary {{ text-align: center; font-weight: bold; margin-bottom: 15px; color: #2c3e50; font-size: 15px; }}
        
        @keyframes parpadeo {{
            0% {{ background-color: #f4f6f9; }}
            50% {{ background-color: #fadbd8; }}
            100% {{ background-color: #f4f6f9; }}
        }}
        body.alerta-activa {{ animation: parpadeo 1.5s infinite; }}
        
        .banner-alerta {{ background-color: #e74c3c; color: white; text-align: center; font-weight: bold; padding: 8px; border-radius: 6px; margin-bottom: 15px; font-size: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}

        #map {{ height: 400px; width: 100%; max-width: 1200px; margin: 0 auto 20px auto; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.2); }}

        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; max-width: 1200px; margin: 0 auto; }}
        .card-link {{ text-decoration: none; color: inherit; display: block; }}
        .card {{ border-radius: 8px; padding: 12px; background: white; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border-left: 6px solid #ccc; transition: transform 0.2s; }}
        .card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.15); }}
        .card.ok {{ border-left-color: #2ecc71; }}
        .card.error {{ border-left-color: #e74c3c; }}
        .card.warning {{ border-left-color: #3498db; }}
        .status {{ font-weight: bold; margin-top: 4px; font-size: 13px; }}
        .ok .status {{ color: #27ae60; }}
        .error .status {{ color: #c0392b; }}
        .warning .status {{ color: #2980b9; }}
        .time {{ font-size: 0.8em; color: #7f8c8d; margin-top: 4px; }}
        .click-text {{ font-size: 0.7em; color: #95a5a6; margin-top: 6px; font-style: italic; text-align: right; }}

        .footer-dev {{ background: linear-gradient(to bottom, #1f618d, #154360); color: white; text-align: center; font-weight: 500; padding: 10px 30px; border-radius: 25px; margin: 30px auto 15px auto; display: table; font-size: 14px; box-shadow: 0 3px 6px rgba(0,0,0,0.2); }}
    </style>
</head>
<body class="{alerta_class}">
    <h1>Monitor de Estaciones Automáticas</h1>
    <div class="subtitle-line2">Centro Zonal de Meteorología Marina de Talcahuano</div>
    <div class="subtitle">Última verificación: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} (Tolerancia: {TOLERANCIA_MINUTOS} min)</div>
    {alerta_banner}
    <div class="summary">Estaciones Operativas: {operativas} de {len(resultados_directemar)} | Total Accesos: {total_estaciones}</div>

    <div id="map"></div>

    <div class="grid">
        {cards_html}
    </div>

    <div style="text-align: center;">
        <div class="footer-dev">Desarrollado por Sgto 2° (Met.) Luis Diego Achurra Garcés</div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        var map = L.map('map').setView([-37.5, -73.2], 7);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 12,
            attribution: '© OpenStreetMap contributors'
        }}).addTo(map);
        {markers_js}
    </script>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✓ Archivo 'index.html' generado correctamente.")

def ejecutar_monitoreo():
    print(f"\n--- [{datetime.now().strftime('%H:%M:%S')}] Verificando mapa litoral ---")
    resultados_directemar = []
    hubo_fallas = False
    
    for est in ESTACIONES_DIRECTEMAR:
        ok, estado, ultimo = consultar_directemar(est)
        simbolo = "✓" if ok else "X"
        print(f"[{simbolo}] {est['nombre']}: {estado} ({ultimo})")
        
        if not ok:
            hubo_fallas = True

        resultados_directemar.append({
            "nombre": est["nombre"], 
            "url": est["url"], 
            "lat": est["lat"],
            "lon": est["lon"],
            "ok": ok, 
            "estado": estado, 
            "ultimo": ultimo
        })

    generar_html(resultados_directemar, hubo_fallas)

if __name__ == "__main__":
    ejecutar_monitoreo()
