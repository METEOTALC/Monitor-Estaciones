from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json
import re
import ssl
import subprocess
import time
import urllib.request

# ==========================================
# CONFIGURACIÓN WEATHER UNDERGROUND (PWS)
# ==========================================
WU_API_KEY = "9219a7502910484094a7502910+8405d"

# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================
TOLERANCIA_MINUTOS = 12
ZONA_CHILE = ZoneInfo("America/Santiago")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
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
        "url": "https://www.wunderground.com/dashboard/pws/ITALCA20",
        "station_id": "ITALCA20",
        "lat": -36.625,
        "lon": -73.033,
    },
    {
        "nombre": "Faro Punta Hualpén",
        "url": "https://www.wunderground.com/dashboard/pws/IHUALP1",
        "station_id": "IHUALP1",
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

      # 1. Temperatura (Español o Inglés)
      temp_match = re.search(
          r"(?:Temperatura|Temperature|Temp)[^\d]*([\-]?\d+(?:[.,]\d+)?)\s*(?:[°º]\s*[cC]|C\b)?",
          texto_plano,
          re.IGNORECASE,
      )
      if not temp_match:
        temp_match = re.search(
            r"([\-]?\d+(?:[.,]\d+)?)\s*[°º]\s*[cC]",
            texto_plano,
            re.IGNORECASE,
        )

      if temp_match:
        val = convertir_numero(temp_match.group(1))
        if val is not None:
          temp = f"{val:.1f}°C"

      # 2. Humedad (Español o Inglés, con el % obligatorio)
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

      # 3. Viento Promedio (Busca estrictamente Wind Speed (avg))
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


def consultar_wunderground_pws(station_id, nombre_faro):
  try:
    api_key_segura = WU_API_KEY.replace("+", "%2B")
    url = f"https://api.weather.com/v2/pws/observations/current?stationId={station_id}&format=json&units=m&apiKey={api_key_segura}"

    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
      data = json.loads(response.read().decode("utf-8"))
      observations = data.get("observations", [])

      if not observations:
        return False, "SIN DATOS VÁLIDOS", "--", "--", "--", "N/D"

      obs = observations[0]
      metric = obs.get("metric", {})

      obs_utc = obs.get("obsTimeUtc")
      fecha_obs = None
      if obs_utc:
        try:
          if obs_utc.endswith("Z"):
            obs_utc = obs_utc[:-1] + "+00:00"
          fecha_obs = datetime.fromisoformat(obs_utc).astimezone(ZONA_CHILE)
        except Exception:
          pass

      temp = metric.get("temp")
      temp_num = convertir_numero(temp)
      temp_str = f"{temp_num:.1f}°C" if temp_num is not None else "--"

      hum = obs.get("humidity")
      hum_num = convertir_numero(hum)
      hum_str = f"{hum_num:.1f}%" if hum_num is not None else "--"

      wind = metric.get("windspeed")
      if wind is None:
        wind = metric.get("windSpeed")

      wind_num = convertir_numero(wind)
      if wind_num is not None:
        viento_kt = wind_num / 1.852
        viento_str = f"{viento_kt:.1f} kt"
      else:
        viento_str = "--"

      ahora = obtener_hora_chile()
      if fecha_obs:
        diferencia = abs((ahora - fecha_obs).total_seconds() / 60)
        diferencia_int = int(diferencia)
        ultimo_str = fecha_obs.strftime("%d-%m-%Y %H:%M:%S")

        if diferencia <= TOLERANCIA_MINUTOS:
          ok = True
          estado = "OPERATIVA"
        else:
          ok = False
          estado = f"DESACTUALIZADA ({diferencia_int} min)"
      else:
        ok = True
        estado = "OPERATIVA"
        ultimo_str = "Reciente (API)"

      return ok, estado, temp_str, hum_str, viento_str, ultimo_str

  except Exception as e:
    print(f"Excepción WU PWS [{nombre_faro}]: {e}")
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
        }}).addTo(map).bindPopup("<b>{faro['nombre']}</b><br>Estado: {faro['estado']}<br>Temp: {faro['temp']} | Hum: {faro['hum']} | Viento: {faro['viento']}<br>Reporte: {faro['ultimo']}<br><a href='{faro['url']}' target='_blank'>Abrir enlace ↗</a>");
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
                    <span>🌡️ {r['temp']}</span> <span>💧 {r['hum']}</span> <span>🌬️ {r['viento']}</span>
                </div>
                <div class="time">Último reporte: {r['ultimo']}</div>
                <div class="click-text">Clic para abrir ↗</div>
            </div>
        </a>
        """

  for faro in resultados_faros:
    clase = "ok" if faro["ok"] else "error"
    icono = "🟢" if faro["ok"] else "🔴"
    cards_html += f"""
        <a href="{faro['url']}" target="_blank" class="card-link">
            <div class="card {clase}">
                <strong>{faro['nombre']}</strong>
                <div class="status">{icono} {faro['estado']}</div>
                <div class="weather-info">
                    <span>🌡️ {faro['temp']}</span> <span>💧 {faro['hum']}</span> <span>🌬️ {faro['viento']}</span>
                </div>
                <div class="time">Último reporte: {faro['ultimo']}</div>
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="30">
    <title>Monitor de Estaciones Automáticas</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body {{ font-family: Arial, sans-serif; background-color: #f4f6f9; padding: 10px; margin: 0; }}
        h1 {{ text-align: center; color: #1a252f; margin-bottom: 0; font-size: 20px; line-height: 1.1; }}
        .subtitle-line2 {{ text-align: center; color: #1a252f; margin-bottom: 6px; font-size: 16px; font-weight: bold; }}
        .subtitle {{ text-align: center; color: #7f8c8d; margin-bottom: 8px; font-size: 12px; }}
        .summary {{ text-align: center; font-weight: bold; margin-bottom: 12px; color: #2c3e50; font-size: 14px; }}
        @keyframes parpadeo {{ 0% {{ background-color: #f4f6f9; }} 50% {{ background-color: #fadbd8; }} 100% {{ background-color: #f4f6f9; }} }}
        body.alerta-activa {{ animation: parpadeo 1.5s infinite; }}
        .banner-alerta {{ background-color: #e74c3c; color: white; text-align: center; font-weight: bold; padding: 8px; border-radius: 6px; margin-bottom: 12px; font-size: 14px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}
        #map {{ height: 350px; width: 100%; max-width: 1200px; margin: 0 auto 15px auto; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.2); }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 10px; max-width: 1200px; margin: 0 auto; }}
        .card-link {{ text-decoration: none; color: inherit; display: block; }}
        .card {{ border-radius: 8px; padding: 10px; background: white; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border-left: 6px solid #ccc; transition: transform 0.2s; }}
        .card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.15); }}
        .card.ok {{ border-left-color: #2ecc71; }}
        .card.error {{ border-left-color: #e74c3c; }}
        .status {{ font-weight: bold; margin-top: 3px; font-size: 12px; }}
        .ok .status {{ color: #27ae60; }}
        .error .status {{ color: #c0392b; }}
        .weather-info {{ font-size: 0.9em; color: #34495e; margin-top: 5px; font-weight: bold; background: #f8f9fa; padding: 5px; border-radius: 4px; display: flex; justify-content: space-around; }}
        .time {{ font-size: 0.75em; color: #7f8c8d; margin-top: 4px; }}
        .click-text {{ font-size: 0.65em; color: #95a5a6; margin-top: 4px; font-style: italic; text-align: right; }}
        .footer-dev {{ background: linear-gradient(to bottom, #1f618d, #154360); color: white; text-align: center; font-weight: 500; padding: 8px 20px; border-radius: 20px; margin: 25px auto 10px auto; display: table; font-size: 13px; box-shadow: 0 3px 6px rgba(0,0,0,0.2); }}
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
  print("✓ index.html actualizado.")


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
    ok, estado, temp, hum, viento, ultimo = consultar_wunderground_pws(
        faro["station_id"], faro["nombre"]
    )
    simbolo = "✓" if ok else "X"
    print(
        f"[{simbolo}] {faro['nombre']} (WU): {estado} | Temp: {temp}, Hum:"
        f" {hum}, Viento: {viento}"
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
                "Extracción precisa del Wind Speed (avg) evitando rachas [skip ci]"
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
