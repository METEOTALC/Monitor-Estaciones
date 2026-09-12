from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json
import re
import ssl
import subprocess
import time
import urllib.request

# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================
TOLERANCIA_MINUTOS = 12
ZONA_CHILE = ZoneInfo("America/Santiago")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "es-ES,es;q=0.9",
}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# ==========================================
# ESTACIONES DIRECTEMAR
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

# ==========================================
# FAROS WEATHER UNDERGROUND
# ==========================================
ESTACIONES_FAROS = [
    {
        "nombre": "Faro Isla Quiriquina",
        "id": "ITALCA20",
        "url": "https://www.wunderground.com/dashboard/pws/ITALCA20",
        "lat": -36.625,
        "lon": -73.033,
    },
    {
        "nombre": "Faro Punta Hualpén",
        "id": "IHUALP1",
        "url": "https://www.wunderground.com/dashboard/pws/IHUALP1",
        "lat": -36.745,
        "lon": -73.185,
    },
]


def obtener_hora_chile():
  return datetime.now(ZONA_CHILE)


def convertir_numero(valor):
  if valor is None:
    return None
  try:
    return float(str(valor).replace(",", "."))
  except (ValueError, TypeError):
    return None


def consultar_directemar(est):
  try:
    req = urllib.request.Request(est["url"], headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
      html = response.read().decode("utf-8", errors="ignore")

      texto_plano = re.sub(r"<[^>]+>", " ", html)
      texto_plano = (
          texto_plano.replace("\xa5", " ")
          .replace("\xa0", " ")
          .replace("&nbsp;", " ")
          .replace("&deg;", "°")
          .replace("&#176;", "°")
      )
      texto_plano = re.sub(r"\s+", " ", texto_plano).strip()

      temp, hum, viento = "--", "--", "--"

      temp_match = re.search(
          r"(?:Temperatura|Temperature)\s*[:]?\s*([\-]?\d+(?:[.,]\d+)?)",
          texto_plano,
          re.IGNORECASE,
      )
      if temp_match:
        val = convertir_numero(temp_match.group(1))
        if val is not None:
          temp = f"{val:.1f}°C"

      hum_match = re.search(
          r"(?:Humedad|Humidity|Hum|HR)[^\d]*(\d+(?:[.,]\d+)?)\s*%",
          texto_plano,
          re.IGNORECASE,
      )
      if hum_match:
        val = convertir_numero(hum_match.group(1))
        if val is not None and 0 <= val <= 100:
          hum = f"{val:.1f}%"

      if hum == "--":
        for m in re.findall(r"(\d+(?:[.,]\d+)?)\s*%", texto_plano):
          val = convertir_numero(m)
          if val is not None and 0 <= val <= 100:
            hum = f"{val:.1f}%"
            break

      viento_match = re.search(
          r"Wind\s*Speed\s*\(avg\)[^\d]*(\d+(?:[.,]\d+)?)\s*(?:kts|kt|knots)?",
          texto_plano,
          re.IGNORECASE,
      )
      if not viento_match:
        viento_match = re.search(
            r"Wind\s*Speed[^\d]*(\d+(?:[.,]\d+)?)\s*(?:kts|kt|knots)?",
            texto_plano,
            re.IGNORECASE,
        )
      if not viento_match:
        viento_match = re.search(
            r"Viento[^\d]*(\d+(?:[.,]\d+)?)\s*(?:kts|kt|knots)?",
            texto_plano,
            re.IGNORECASE,
        )

      if viento_match:
        val = convertir_numero(viento_match.group(1))
        if val is not None:
          viento = f"{val:.1f} kt"

      match_fecha = re.search(
          r"(?:Page\s+updated|Actualizado)\s+(\d{1,2}-\d{1,2}-\d{4}\s+\d{1,2}:\d{2}(?::\d{2})?)",
          texto_plano,
          re.IGNORECASE,
      )
      if not match_fecha:
        return False, "SIN DATOS VÁLIDOS", "N/D", temp, hum, viento

      fecha_str = match_fecha.group(1)
      formato_fecha = (
          "%d-%m-%Y %H:%M:%S" if fecha_str.count(":") == 2 else "%d-%m-%Y %H:%M"
      )
      fecha_estacion = datetime.strptime(fecha_str, formato_fecha).replace(
          tzinfo=ZONA_CHILE
      )
      dif_min = abs(
          (obtener_hora_chile() - fecha_estacion).total_seconds() / 60
      )

      if dif_min <= TOLERANCIA_MINUTOS or (170 <= dif_min <= 200):
        return True, "OPERATIVA", fecha_str, temp, hum, viento
      else:
        return (
            False,
            f"DESACTUALIZADA ({int(dif_min)} min)",
            fecha_str,
            temp,
            hum,
            viento,
        )

  except Exception as e:
    print(f"Error Directemar {est['nombre']}: {e}")
    return False, "SIN CONEXIÓN", "Error de red", "--", "--", "--"


def consultar_wunderground_web(est):
  for intento in range(3):
    try:
      req = urllib.request.Request(est["url"], headers=HEADERS)
      with urllib.request.urlopen(req, timeout=12, context=ctx) as response:
        html = response.read().decode("utf-8", errors="ignore")

        temp, hum, viento, ultimo = "--", "--", "--", "Reciente (Web)"

        # Extracción prioritaria apuntando al bloque de temperatura actual de la tarjeta principal (ej. 10,8 °C)
        temp_match = re.search(
            r'class=["\'][^"\']*metric-val[^"\']*["\'][^>]*>([0-9]+[.,][0-9]+)',
            html,
        )
        if not temp_match:
          temp_match = re.search(
              r"(?:current-temp|temperature|temp)[^>]*?([0-9]+[.,][0-9]+)\s*°?\s*C",
              html,
              re.IGNORECASE,
          )
        if not temp_match:
          temp_match = re.search(
              r'"metric"\s*:\s*\{\s*"temp"\s*:\s*([0-9]+[.,]?[0-9]*)', html
          )

        if temp_match:
          val = convertir_numero(temp_match.group(1))
          if val is not None:
            temp = f"{val:.1f}°C"

        hum_match = re.search(
            r'"humidity"\s*:\s*([0-9]+(?:\.[0-9]+)?)', html
        )
        if not hum_match:
          hum_match = re.search(r"Hum(?:edity)?.*?([0-9]+[.,][0-9]*)%", html, re.IGNORECASE)
        if hum_match:
          val = convertir_numero(hum_match.group(1))
          if val is not None:
            hum = f"{val:.1f}%"

        wind_match = re.search(r'"windSpeed"\s*:\s*([0-9\.]+)', html)
        if not wind_match:
          wind_match = re.search(r'wind-speed[^>]*?>([0-9]+[.,][0-9]*)', html, re.IGNORECASE)

        if wind_match:
          v_val = convertir_numero(wind_match.group(1))
          if v_val is not None:
            # Si viene en km/h como en la interfaz web de la captura, convertimos a nudos (/ 1.852)
            v_kt = v_val / 1.852
            viento = f"{v_kt:.1f} kt"

        time_match = re.search(r'"obsTimeLocal"\s*:\s*"([^"]+)"', html)
        if time_match:
          ultimo = time_match.group(1)

        if temp != "--" or hum != "--":
          return True, "OPERATIVA", temp, hum, viento, ultimo

    except Exception as e:
      print(f"Intento {intento+1} fallido para {est['nombre']}: {e}")
      time.sleep(2)

  # Plan B: API de Weather.com si falla el rastreo web directo
  try:
    alt_url = (
        f"https://api.weather.com/v2/pws/observations/current"
        f"?stationId={est['id']}&format=json&units=m&apiKey=e1f10a1e78da46f5b10a1e78da96f525"
    )
    req = urllib.request.Request(alt_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
      data = json.loads(response.read().decode("utf-8"))
      obs = data["observations"][0]
      metric = obs["metric"]

      temp_val = metric.get("temp")
      temp = f"{temp_val:.1f}°C" if temp_val is not None else "--"

      hum_val = obs.get("humidity")
      hum = f"{hum_val:.1f}%" if hum_val is not None else "--"

      viento_kmh = metric.get("windSpeed")
      if viento_kmh is not None:
        viento_kt = viento_kmh / 1.852
        viento = f"{viento_kt:.1f} kt"
      else:
        viento = "--"

      return True, "OPERATIVA", temp, hum, viento, "Reciente (API Alt)"
  except Exception as alt_e:
    print(f"Error en Plan B API Alt [{est['nombre']}]: {alt_e}")

  return False, "SIN CONEXIÓN", "--", "--", "--", "Error de red"


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
            color: '{color}', fillColor: '{color}', fillOpacity: 0.8, radius: 9
        }}).addTo(map).bindPopup("<b>{r['nombre']}</b><br>Estado: {r['estado']}<br>Temp: {r['temp']} | Hum: {r['hum']} | Viento: {r['viento']}<br>Reporte: {r['ultimo']}<br><a href='{r['url']}' target='_blank'>Abrir enlace ↗</a>");
        """

  for faro in resultados_faros:
    color = "green" if faro["ok"] else "red"
    markers_js += f"""
        L.circleMarker([{faro['lat']}, {faro['lon']}], {{
            color: '{color}', fillColor: '{color}', fillOpacity: 0.8, radius: 9
        }}).addTo(map).bindPopup("<b>{faro['nombre']}</b><br>Estado: {faro['estado']}<br>Temp: {r['temp'] if 'temp' in r else faro['temp']} | Hum: {faro['hum']} | Viento: {faro['viento']}<br>Reporte: {faro['ultimo']}<br><a href='{faro['url']}' target='_blank'>Abrir enlace ↗</a>");
        """

  cards_html = ""
  for r in resultados_directemar:
    clase = "ok" if r["ok"] else "error"
    icono = "🟢" if r["ok"] else "🔴"
    cards_html += f"""
        <a href="{r['url']}" target="_blank" class="card-link">
            <div class="card {clase}">
                <div class="card-header">
                    <span class="station-name">{r['nombre']}</span>
                    <span class="status-badge">{icono}</span>
                </div>
                <div class="weather-main">
                    <span class="temp-val">🌡️ {r['temp']}</span>
                </div>
                <div class="weather-info">
                    <span>💧 {r['hum']}</span> <span>🌬️ {r['viento']}</span>
                </div>
                <div class="time">Reporte: {r['ultimo']}</div>
                <div class="click-text">Ver estación ↗</div>
            </div>
        </a>
        """

  for faro in resultados_faros:
    clase = "ok" if faro["ok"] else "error"
    icono = "🟢" if faro["ok"] else "🔴"
    cards_html += f"""
        <a href="{faro['url']}" target="_blank" class="card-link">
            <div class="card {clase}">
                <div class="card-header">
                    <span class="station-name">{faro['nombre']}</span>
                    <span class="status-badge">{icono}</span>
                </div>
                <div class="weather-main">
                    <span class="temp-val">🌡️ {faro['temp']}</span>
                </div>
                <div class="weather-info">
                    <span>💧 {faro['hum']}</span> <span>🌬️ {faro['viento']}</span>
                </div>
                <div class="time">Reporte: {faro['ultimo']}</div>
                <div class="click-text">Ver estación ↗</div>
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="30">
    <title>Monitor de Estaciones Automáticas</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0b1120; color: #f8fafc; padding: 15px; margin: 0; }}
        h1 {{ text-align: center; color: #f1f5f9; margin-bottom: 0; font-size: 22px; line-height: 1.2; text-shadow: 0 2px 4px rgba(0,0,0,0.3); }}
        .subtitle-line2 {{ text-align: center; color: #38bdf8; margin-bottom: 6px; font-size: 16px; font-weight: bold; }}
        .subtitle {{ text-align: center; color: #94a3b8; margin-bottom: 12px; font-size: 12px; }}
        .summary {{ text-align: center; font-weight: bold; margin-bottom: 15px; color: #e2e8f0; font-size: 14px; background: rgba(255,255,255,0.05); padding: 6px; border-radius: 20px; max-width: 300px; margin-left: auto; margin-right: auto; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}
        @keyframes parpadeo {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.6; }} 100% {{ opacity: 1; }} }}
        body.alerta-activa {{ animation: parpadeo 1.5s infinite; }}
        .banner-alerta {{ background: linear-gradient(135deg, #ef4444, #dc2626); color: white; text-align: center; font-weight: bold; padding: 10px; border-radius: 8px; margin-bottom: 15px; font-size: 14px; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4); }}
        #map {{ height: 350px; width: 100%; max-width: 1200px; margin: 0 auto 20px auto; border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.1); }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; max-width: 1200px; margin: 0 auto; }}
        .card-link {{ text-decoration: none; color: inherit; display: block; }}
        
        .card {{ 
            border-radius: 16px; 
            padding: 16px; 
            background: linear-gradient(135deg, #1b3152 0%, #152238 50%, #222b3b 100%); 
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(256, 256, 256, 0.1); 
            border: 1px solid rgba(56, 189, 248, 0.18); 
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }}
        .card:hover {{ 
            transform: translateY(-4px); 
            box-shadow: 0 20px 35px -10px rgba(56, 189, 248, 0.35), inset 0 1px 0 rgba(256, 256, 256, 0.2); 
            border-color: rgba(56, 189, 248, 0.6);
            background: linear-gradient(135deg, #25426e 0%, #1a2a47 50%, #2b364a 100%);
        }}
        .card.ok {{ border-left: 5px solid #22c55e; }}
        .card.error {{ border-left: 5px solid #ef4444; }}
        
        .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }}
        .station-name {{ font-weight: bold; font-size: 15px; color: #f8fafc; line-height: 1.2; }}
        .status-badge {{ font-size: 12px; }}
        
        .weather-main {{ margin: 10px 0; }}
        .temp-val {{ font-size: 26px; font-weight: 700; color: #38bdf8; text-shadow: 0 2px 4px rgba(0,0,0,0.3); }}
        
        .weather-info {{ font-size: 0.95em; color: #cbd5e1; margin-top: 8px; background: rgba(15, 23, 42, 0.6); padding: 8px 10px; border-radius: 10px; display: flex; justify-content: space-between; font-weight: 600; border: 1px solid rgba(255,255,255,0.06); }}
        .time {{ font-size: 0.75em; color: #94a3b8; margin-top: 8px; }}
        .click-text {{ font-size: 0.7em; color: #38bdf8; margin-top: 4px; font-style: italic; text-align: right; opacity: 0.8; }}
        
        .footer-dev {{ background: linear-gradient(135deg, #1e40af, #1e3a8a); color: #f8fafc; text-align: center; font-weight: 600; padding: 10px 24px; border-radius: 30px; margin: 30px auto 15px auto; display: table; font-size: 13px; box-shadow: 0 4px 12px rgba(30, 64, 175, 0.4); border: 1px solid rgba(255,255,255,0.1); }}
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
            maxZoom: 12, attribution: '© OpenStreetMap contributors'
        }}).addTo(map);
        {markers_js}
    </script>
</body>
</html>"""

  with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
  print("✓ index.html actualizado correctamente.")


def ejecutar_monitoreo():
  print(
      f"\n--- [{obtener_hora_chile().strftime('%H:%M:%S')}] Verificando litoral"
      " ---"
  )
  resultados_directemar = []
  resultados_faros = []
  hubo_fallas = False

  for est in ESTACIONES_DIRECTEMAR:
    ok, estado, ultimo, temp, hum, viento = consultar_directemar(est)
    simbolo = "✓" if ok else "X"
    print(
        f"[{simbolo}] {est['nombre']}: {estado} | Temp: {temp}, Hum: {hum},"
        f" Viento: {viento}"
    )
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

  for faro in ESTACIONES_FAROS:
    ok, estado, temp, hum, viento, ultimo = consultar_wunderground_web(faro)
    simbolo = "✓" if ok else "X"
    print(
        f"[{simbolo}] {faro['nombre']} (Web/API): {estado} | Temp: {temp},"
        f" Hum: {hum}, Viento: {viento}"
    )
    if not ok:
      hubo_fallas = True
    resultados_faros.append({
        "nombre": faro["nombre"],
        "url": faro["url"],
        "lat": faro["lat"],
        "lon": faro["lon"],
        "ok": ok,
        "estado": estado,
        "ultimo": ultimo,
        "temp": temp,
        "hum": hum,
        "viento": viento,
    })

  generar_html(resultados_directemar, resultados_faros, hubo_fallas)
  subir_a_github()


def subir_a_github():
  try:
    print("Sincronizando cambios con GitHub...")
    subprocess.run(["git", "add", "index.html"], check=True)
    resultado = subprocess.run(
        [
            "git",
            "commit",
            "-m",
            (
                "Degradé sutil de tarjetas y extracción exacta de temperatura"
                " actual de faros [skip ci]"
            ),
        ],
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
      if "nothing to commit" in (resultado.stdout + resultado.stderr).lower():
        print("Sin cambios nuevos para subir.")
        return
    subprocess.run(["git", "push"], check=True)
    print("✓ Sincronización completada con éxito.")
  except subprocess.CalledProcessError as e:
    print(f"Error al sincronizar con Git: {e}")


if __name__ == "__main__":
  ejecutar_monitoreo()
