from datetime import datetime, timedelta
import hashlib
import hmac
import json
import re
import ssl
import subprocess
import time
import urllib.request

# ==========================================
# CONFIGURACIÓN DE CREDENCIALES WEATHERLINK V2
# ==========================================
WL_API_KEY = "pa73dvpxib2q7ki1ixnzvx0ti0atyrpk"
WL_API_SECRET = "yzpyohbu6cnqxmunczgffa2fx80bjdal"

# ==========================================
# CONFIGURACIÓN DE ESTACIONES
# ==========================================
ESTACIONES_DIRECTEMAR = [
    {
        "nombre": "Capitanía de Puerto Constitución-7700",
        "url": (
            "http://web.directemar.cl/met/jturno/estaciones/constitucion/index.htm"
        ),
        "lat": -35.333,
        "lon": -72.416,
    },
    {
        "nombre": "Capitanía de Puerto Lirquén-7406",
        "url": "http://web.directemar.cl/met/jturno/estaciones/lirquen/index.htm",
        "lat": -36.716,
        "lon": -72.933,
    },
    {
        "nombre": "Gobernación Marítima de Talcahuano",
        "url": (
            "http://web.directemar.cl/met/jturno/estaciones/talcahuano/index.htm"
        ),
        "lat": -36.712,
        "lon": -73.115,
    },
    {
        "nombre": "Capitanía de Puerto Coronel-7313",
        "url": "http://web.directemar.cl/met/jturno/estaciones/coronel/index.htm",
        "lat": -37.020,
        "lon": -73.150,
    },
    {
        "nombre": "Capitanía de Puerto Lota-7373",
        "url": "http://web.directemar.cl/met/jturno/estaciones/lota/index.htm",
        "lat": -37.090,
        "lon": -73.150,
    },
    {
        "nombre": "Capitanía de Puerto Lebu-7800",
        "url": "http://web.directemar.cl/met/jturno/estaciones/lebu/index.htm",
        "lat": -37.606,
        "lon": -73.650,
    },
    {
        "nombre": "Capitanía de Puerto Carahue",
        "url": "http://web.directemar.cl/met/jturno/estaciones/carahue/index.htm",
        "lat": -38.788,
        "lon": -73.397,
    },
    {
        "nombre": "Capitanía de Puerto Corral-1960",
        "url": "http://web.directemar.cl/met/jturno/estaciones/corral/index.htm",
        "lat": -39.883,
        "lon": -73.433,
    },
]

ESTACIONES_FAROS = [
    {
        "nombre": "Faro Isla Quiriquina",
        "url": "https://www.wunderground.com/dashboard/pws/ITALCA20",
        "station_id": "178202",
        "lat": -36.625,
        "lon": -73.033,
    },
    {
        "nombre": "Faro Punta Hualpén",
        "url": "https://www.wunderground.com/dashboard/pws/IHUALP1",
        "station_id": "236994",
        "lat": -36.745,
        "lon": -73.185,
    },
]

TOLERANCIA_MINUTOS = 12

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def obtener_hora_chile():
  # Ajusta la hora UTC del servidor restando 3 horas para obtener la hora local de Chile
  return datetime.utcnow() - timedelta(hours=3)


def consultar_directemar(est):
  try:
    req = urllib.request.Request(est["url"], headers=HEADERS)
    with urllib.request.urlopen(req, timeout=8, context=ctx) as response:
      html = response.read().decode("utf-8", errors="ignore")
      match = re.search(
          r"page updated\s+(\d{1,2}-\d{1,2}-\d{4}\s+\d{1,2}:\d{2})",
          html,
          re.IGNORECASE,
      )

      temp = "--"
      hum = "--"
      viento = "--"

      if match:
        fecha_str = match.group(1)
        fecha_estacion = datetime.strptime(fecha_str, "%d-%m-%Y %H:%M")
        dif_min = int(
            abs((obtener_hora_chile() - fecha_estacion).total_seconds()) / 60
        )

        if dif_min <= TOLERANCIA_MINUTOS or (170 <= dif_min <= 200):
          return True, "OPERATIVA", fecha_str, temp, hum, viento
        else:
          return False, f"DESACTUALIZADA ({dif_min} min)", fecha_str, temp, hum, viento
    return False, "SIN DATOS VÁLIDOS", "N/D", "--", "--", "--"
  except Exception:
    return False, "SIN CONEXIÓN", "Error de red", "--", "--", "--"


def consultar_weatherlink_v2(station_id):
  try:
    t = str(int(time.time()))
    url_path = f"/v2/current/{station_id}"
    data_to_sign = f"api-key{WL_API_KEY}t{t}{url_path}"

    signature = hmac.new(
        WL_API_SECRET.encode("utf-8"),
        data_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    url = f"https://api.weatherlink.com{url_path}?api-key={WL_API_KEY}&t={t}&api-signature={signature}"

    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(url=url, timeout=8, context=ctx) as response:
      resultado = json.loads(response.read().decode("utf-8"))

      temp_c, hum, viento = "--", "--", "--"

      # Barrido flexible sobre todos los sensores y claves del JSON
      for sensor in resultado.get("sensors", []):
        for dat in sensor.get("data", []):
          for key, val in dat.items():
            if val is not None:
              if any(k in key.lower() for k in ["temp"]) and temp_c == "--":
                # Si viene en Fahrenheit (estándar Davis), convertir a Celsius
                temp_c = round((val - 32) * 5 / 9, 1)
              elif any(k in key.lower() for k in ["hum"]) and hum == "--":
                hum = val
              elif (
                  any(k in key.lower() for k in ["wind_speed", "wind_last"])
                  and viento == "--"
              ):
                viento = val

      if temp_c == "--" and hum == "--":
        return False, "--", "--", "--"

      return (
          True,
          f"{temp_c}°C" if temp_c != "--" else "--",
          f"{hum}%" if hum != "--" else "--",
          f"{viento} nud" if viento != "--" else "--",
      )
  except Exception as e:
    print(f"Error API WeatherLink para ID {station_id}: {e}")
    return False, "--", "--", "--"


def generar_html(resultados_directemar, resultados_faros, hay_alerta):
  total_estaciones = len(resultados_directemar) + len(resultados_faros)
  operativas = sum(1 for r in resultados_directemar if r["ok"]) + sum(
      1 for f in resultados_faros if f["ok"]
  )

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

  for faro in resultados_faros:
    color = "green" if faro["ok"] else "red"
    markers_js += f"""
        L.circleMarker([{faro['lat']}, {faro['lon']}], {{
            color: '{color}',
            fillColor: '{color}',
            fillOpacity: 0.8,
            radius: 8
        }}).addTo(map).bindPopup("<b>{faro['nombre']}</b><br>Temp: {faro['temp']}<br>Hum: {faro['hum']}<br>Viento: {faro['viento']}<br><a href='{faro['url']}' target='_blank'>Abrir enlace ↗</a>");
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
                <div class="weather-info">
                    <span>🌡️ {r['temp']}</span> | <span>💧 {r['hum']}</span> | <span>🌬️ {r['viento']}</span>
                </div>
                <div class="time">Último reporte: {r['ultimo']}</div>
                <div class="click-text">Clic para abrir ↗</div>
            </div>
        </a>
        """

  for faro in resultados_faros:
    clase = "ok" if faro["ok"] else "error"
    icono = "🟢" if faro["ok"] else "🔴"
    estado_txt = "OPERATIVA" if faro["ok"] else "SIN CONEXIÓN"
    cards_html += f"""
        <a href="{faro['url']}" target="_blank" class="card-link">
            <div class="card {clase}">
                <strong>{faro['nombre']}</strong>
                <div class="status">{icono} {estado_txt}</div>
                <div class="weather-info">
                    <span>🌡️ {faro['temp']}</span> | <span>💧 {faro['hum']}</span> | <span>🌬️ {faro['viento']}</span>
                </div>
                <div class="time">Fuente: WeatherLink API v2</div>
                <div class="click-text">Clic para abrir ↗</div>
            </div>
        </a>
        """

  alerta_class = "alerta-activa" if hay_alerta else ""
  alerta_banner = (
      '<div class="banner-alerta">⚠️ ¡ATENCIÓN: HAY ESTACIONES CON FALLAS O'
      " DESACTUALIZADAS! ⚠️</div>"
      if hay_alerta
      else ""
  )
  hora_actual_chile = obtener_hora_chile().strftime("%d-%m-%Y %H:%M:%S")

  html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="30">
    <title>Monitor de Estaciones Automáticas - Constitución a Corral</title>
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
        .status {{ font-weight: bold; margin-top: 4px; font-size: 13px; }}
        .ok .status {{ color: #27ae60; }}
        .error .status {{ color: #c0392b; }}
        .weather-info {{ font-size: 0.9em; color: #34495e; margin-top: 6px; font-weight: bold; background: #f8f9fa; padding: 4px; border-radius: 4px; }}
        .time {{ font-size: 0.8em; color: #7f8c8d; margin-top: 4px; }}
        .click-text {{ font-size: 0.7em; color: #95a5a6; margin-top: 6px; font-style: italic; text-align: right; }}

        .footer-dev {{ background: linear-gradient(to bottom, #1f618d, #154360); color: white; text-align: center; font-weight: 500; padding: 10px 30px; border-radius: 25px; margin: 30px auto 15px auto; display: table; font-size: 14px; box-shadow: 0 3px 6px rgba(0,0,0,0.2); }}
    </style>
</head>
<body class="{alerta_class}">
    <h1>Monitor de Estaciones Automáticas</h1>
    <div class="subtitle-line2">Centro Zonal de Meteorología Marina de Talcahuano</div>
    <div class="subtitle">Última verificación: {hora_actual_chile} (Tolerancia: {TOLERANCIA_MINUTOS} min)</div>
    {alerta_banner}
    <div class="summary">Estaciones Operativas: {operativas} de {total_estaciones}</div>

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
  print(
      f"\n--- [{obtener_hora_chile().strftime('%H:%M:%S')}] Verificando mapa"
      " litoral ---"
  )
  resultados_directemar = []
  resultados_faros = []
  hubo_fallas = False

  # Consultar Directemar
  for est in ESTACIONES_DIRECTEMAR:
    ok, estado, ultimo, temp, hum, viento = consultar_directemar(est)
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
        "ultimo": ultimo,
        "temp": temp,
        "hum": hum,
        "viento": viento,
    })

  # Consultar Faros mediante WeatherLink API v2
  for faro in ESTACIONES_FAROS:
    ok, temp, hum, viento = consultar_weatherlink_v2(faro["station_id"])
    simbolo = "✓" if ok else "X"
    print(f"[{simbolo}] {faro['nombre']} (WL): Temp {temp}, Hum {hum}")
    if not ok:
      hubo_fallas = True
    resultados_faros.append({
        "nombre": faro["nombre"],
        "url": faro["url"],
        "lat": faro["lat"],
        "lon": faro["lon"],
        "ok": ok,
        "temp": temp,
        "hum": hum,
        "viento": viento,
    })

  generar_html(resultados_directemar, resultados_faros, hubo_fallas)
  subir_a_github()


def subir_a_github():
  try:
    print("Subiendo cambios a GitHub...")
    subprocess.run(["git", "add", "index.html"], check=True)
    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "Actualización automática de clima desde API WeatherLink [skip ci]",
        ],
        check=True,
    )
    subprocess.run(["git", "push"], check=True)
    print("¡Cambios subidos a GitHub con éxito!")
  except subprocess.CalledProcessError as e:
    print(f"Error al sincronizar con Git: {e}")


if __name__ == "__main__":
  ejecutar_monitoreo()
