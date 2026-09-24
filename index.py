from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json
import os
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
ARCHIVO_HISTORIAL = "historial_presion.json"

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
        "nombre": "Capitanía de Puerto Constitución",
        "url": (
            "http://web.directemar.cl/met/jturno/estaciones/constitucion/index.htm"
        ),
        "lat": -35.3241667,
        "lon": -72.40805555,
    },
    {
        "nombre": "Capitanía de Puerto Lirquén",
        "url": "http://web.directemar.cl/met/jturno/estaciones/lirquen/index.htm",
        "lat": -36.7027778,
        "lon": -72.9775,
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
        "nombre": "Capitanía de Puerto Coronel",
        "url": "http://web.directemar.cl/met/jturno/estaciones/coronel/index.htm",
        "lat": -37.020,
        "lon": -73.150,
    },
    {
        "nombre": "Capitanía de Puerto Lota",
        "url": "http://web.directemar.cl/met/jturno/estaciones/lota/index.htm",
        "lat": -37.090,
        "lon": -73.150,
    },
    {
        "nombre": "Capitanía de Puerto Lebu",
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
        "nombre": "Capitanía de Puerto Corral",
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
        "lat": -36.607,
        "lon": -73.049,
    },
    {
        "nombre": "Faro Punta Hualpén",
        "id": "IHUALP1",
        "url": "https://www.wunderground.com/dashboard/pws/IHUALP1",
        "lat": -36.745,
        "lon": -73.185,
    },
]

# ==========================================
# ESTACIONES IFOP / API JSON
# ==========================================
ESTACIONES_IFOP = [
    {
        "nombre": "Faro Cabo Carranza",
        "url": "https://giscc.ifop.cl/doma_met/",
        "api_url": "https://giscc.ifop.cl/siom-enoscc//get_est_met/22",
        "lat": -35.5608333,
        "lon": -72.6177777,
    },
    {
        "nombre": "Faro Isla Mocha",
        "url": "https://giscc.ifop.cl/doma_met/",
        "api_url": "https://giscc.ifop.cl/siom-enoscc//get_est_met/34",
        "lat": -38.3849472,
        "lon": -73.8688523,
    },
]

ORDEN_ESTACIONES = [
    "Capitanía de Puerto Constitución",
    "Faro Punta Carranza",
    "Capitanía de Puerto Lirquén",
    "Faro Isla Quiriquina",
    "Gobernación Marítima de Talcahuano",
    "Faro Punta Hualpén",
    "Capitanía de Puerto Coronel",
    "Capitanía de Puerto Lota",
    "Capitanía de Puerto Lebu",
    "Isla Mocha",
    "Capitanía de Puerto Carahue",
    "Capitanía de Puerto Corral",
]


def obtener_hora_chile():
  return datetime.now(ZONA_CHILE)


def convertir_numero(valor):
  if valor is None:
    return None
  try:
    val_str = str(valor).strip()
    if any(
        c in val_str.lower()
        for c in ["color", "purple", "line", "data", "{", "}"]
    ):
      return None
    return float(val_str.replace(",", "."))
  except (ValueError, TypeError):
    return None


def formatear_direccion(dir_str):
  if not dir_str:
    return ""
  d = str(dir_str).upper().strip()
  if any(c in d.lower() for c in ["color", "purple", "line", "data", "{", "}"]):
    return ""
  if len(d) == 3:
    return f"{d[0]}/{d[1:]}"
  return d


def grados_a_cardinal(grados):
  if grados is None:
    return "N/D"
  direcciones = [
      "N",
      "NNE",
      "NE",
      "ENE",
      "E",
      "ESE",
      "SE",
      "SSE",
      "S",
      "SSW",
      "SW",
      "WSW",
      "W",
      "WNW",
      "NW",
      "NNW",
  ]
  indice = int((grados + 11.25) / 22.5) % 16
  return formatear_direccion(direcciones[indice])


def gestionar_historial_presion(nombre_estacion, presion_actual):
  ahora = obtener_hora_chile()
  historial = {}
  if os.path.exists(ARCHIVO_HISTORIAL):
    try:
      with open(ARCHIVO_HISTORIAL, "r", encoding="utf-8") as f:
        historial = json.load(f)
    except Exception:
      historial = {}

  if nombre_estacion not in historial:
    historial[nombre_estacion] = []

  registros = historial[nombre_estacion]
  registros.append({"t": ahora.timestamp(), "p": presion_actual})

  limite_tiempo = ahora.timestamp() - (3.5 * 3600)
  registros = [r for r in registros if r["t"] >= limite_tiempo]
  historial[nombre_estacion] = registros

  try:
    with open(ARCHIVO_HISTORIAL, "w", encoding="utf-8") as f:
      json.dump(historial, f)
  except Exception:
    pass

  if presion_actual is None:
    return ""

  objetivo_t = ahora.timestamp() - (3 * 3600)
  candidatos = [r for r in registros if abs(r["t"] - objetivo_t) <= (45 * 60)]

  if not candidatos:
    candidatos_antiguos = [r for r in registros if r["t"] <= objetivo_t + 1800]
    if candidatos_antiguos:
      presion_pasada = candidatos_antiguos[0]["p"]
    else:
      return ""
  else:
    candidatos.sort(key=lambda x: abs(x["t"] - objetivo_t))
    presion_pasada = candidatos[0]["p"]

  if presion_pasada is None:
    return ""

  dif = presion_actual - presion_pasada

  if dif > 0.2:
    return " ↗"
  elif dif < -0.2:
    return " ↘"
  else:
    return " ➔"


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

      temp, pres, viento, dir_viento, racha = "--", "--", "--", "", "--"
      pres_val = None

      # Temperatura
      temp_match = re.search(
          r"(?:Temperatura|Temperature)\s*[:]?\s*([\-]?\d+(?:[.,]\d+)?)",
          texto_plano,
          re.IGNORECASE,
      )
      if temp_match:
        val = convertir_numero(temp_match.group(1))
        if val is not None:
          temp = f"{val:.1f}°C"

      # Presión
      pres_match = re.search(
          r"(?:Barometer|Presi[oó]n)[^\d]*([\-]?\d+(?:[.,]\d+)?)\s*(?:hPa|mb)?",
          texto_plano,
          re.IGNORECASE,
      )
      if pres_match:
        pres_val = convertir_numero(pres_match.group(1))
        if pres_val is not None:
          tendencia = gestionar_historial_presion(est["nombre"], pres_val)
          pres = f"{pres_val:.1f} hPa{tendencia}"

      # Búsqueda robusta de Dirección de Viento en Directemar
      bearing_match = re.search(
          r"Wind\s*Bearing[^\d]*\d+(?:[.,]\d+)?\s*°?\s*([N,S,E,W]{1,3})",
          texto_plano,
          re.IGNORECASE,
      )
      if not bearing_match:
        bearing_match = re.search(
            r"(?:Direcci[oó]n\s*Viento|Wind\s*Direction)[^\w]*([N,S,E,W]{1,3})",
            texto_plano,
            re.IGNORECASE,
        )
      if not bearing_match:
        bearing_match = re.search(
            r"(?:Direcci[oó]n|Dir)[^\w]*(?:del\s*)?(?:Viento)?[^\w]*([N,S,E,W]{1,3})",
            texto_plano,
            re.IGNORECASE,
        )
      if not bearing_match:
        deg_match = re.search(
            r"(?:Direcci[oó]n|Dir|Wind\s*Direction|Bearing)[^\d]*(\d+(?:[.,]\d+)?)\s*°",
            texto_plano,
            re.IGNORECASE,
        )
        if deg_match:
          grados_val = convertir_numero(deg_match.group(1))
          if grados_val is not None:
            dir_viento = grados_a_cardinal(grados_val)

      if bearing_match and not dir_viento:
        dir_viento = formatear_direccion(bearing_match.group(1))

      # Búsqueda robusta de Velocidad de Viento
      viento_match = re.search(
          r"Wind\s*Speed\s*\(avg\)[^\d]*(\d+(?:[.,]\d+)?)\s*(?:kts|kt|knots|nudos)?",
          texto_plano,
          re.IGNORECASE,
      )
      if not viento_match:
        viento_match = re.search(
            r"Wind\s*Speed[^\d]*(\d+(?:[.,]\d+)?)\s*(?:kts|kt|knots|nudos)?",
            texto_plano,
            re.IGNORECASE,
        )
      if not viento_match:
        viento_match = re.search(
            r"Viento[^\d]*(\d+(?:[.,]\d+)?)\s*(?:kts|kt|knots|nudos)?",
            texto_plano,
            re.IGNORECASE,
        )

      if viento_match:
        val = convertir_numero(viento_match.group(1))
        if val is not None:
          viento = f"{val:.1f} kt"

      # Búsqueda robusta de Racha / Ráfaga
      racha_match = re.search(
          r"(?:Wind\s*Speed\s*\(gust\)|Gust|Racha|Ráfaga|Rafaga)[^\d]*(\d+(?:[.,]\d+)?)\s*(?:kts|kt|knots|nudos)?",
          texto_plano,
          re.IGNORECASE,
      )
      if racha_match:
        val = convertir_numero(racha_match.group(1))
        if val is not None:
          racha = f"{val:.1f} kt"

      match_fecha = re.search(
          r"(?:Page\s+updated|Actualizado)\s+(\d{1,2}-\d{1,2}-\d{4}\s+\d{1,2}:\d{2}(?::\d{2})?)",
          texto_plano,
          re.IGNORECASE,
      )
      if not match_fecha:
        return (
            False,
            "SIN DATOS VÁLIDOS",
            "N/D",
            temp,
            pres,
            viento,
            dir_viento,
            racha,
        )

      fecha_str = match_fecha.group(1)

      # CORRECCIÓN PARA LA HORA 00: (agrega el cero faltante si viene como "0:00:00")
      partes_f = fecha_str.split()
      if len(partes_f) == 2:
        fecha_p, hora_p = partes_f
        sub_hora = hora_p.split(":")
        if len(sub_hora[0]) == 1:
          sub_hora[0] = "0" + sub_hora[0]
          fecha_str = f"{fecha_p} {':'.join(sub_hora)}"

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
        return True, "OPERATIVA", fecha_str, temp, pres, viento, dir_viento, racha
      else:
        return (
            False,
            f"DESACTUALIZADA ({int(dif_min)} min)",
            fecha_str,
            temp,
            pres,
            viento,
            dir_viento,
            racha,
        )

  except Exception as e:
    print(f"Error Directemar {est['nombre']}: {e}")
    return False, "SIN CONEXIÓN", "Error de red", "--", "--", "--", "", "--"


def consultar_wunderground_web(est):
  try:
    api_url = (
        f"https://api.weather.com/v2/pws/observations/current"
        f"?stationId={est['id']}&format=json&units=e&apiKey=e1f10a1e78da46f5b10a1e78da96f525"
    )
    req = urllib.request.Request(api_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
      data = json.loads(response.read().decode("utf-8"))
      obs = data["observations"][0]
      imperial = obs["imperial"]

      temp_f = imperial.get("temp")
      temp = (
          f"{(temp_f - 32.0) * 5.0 / 9.0:.1f}°C"
          if temp_f is not None
          else "--"
      )

      pres_inHg = imperial.get("pressure")
      pres = "--"
      if pres_inHg is not None:
        pres_val = pres_inHg * 33.86389
        tendencia = gestionar_historial_presion(est["nombre"], pres_val)
        pres = f"{pres_val:.1f} hPa{tendencia}"

      viento_mph = imperial.get("windSpeed")
      viento = (
          f"{viento_mph / 1.15077945:.1f} kt"
          if viento_mph is not None
          else "--"
      )

      gust_mph = imperial.get("windGust")
      racha = (
          f"{gust_mph / 1.15077945:.1f} kt"
          if gust_mph is not None
          else "--"
      )

      wind_dir_deg = obs.get("winddir")
      dir_viento = grados_a_cardinal(wind_dir_deg)

      obs_time = obs.get("obsTimeLocal", "Reciente")
      return (
          True,
          "OPERATIVA",
          temp,
          pres,
          viento,
          dir_viento,
          racha,
          str(obs_time),
      )
  except Exception as e:
    print(f"Error WU [{est['nombre']}]: {e}")

  return False, "SIN CONEXIÓN", "--", "--", "--", "", "--", "Error de red"


def consultar_ifop(est):
  try:
    req = urllib.request.Request(est["api_url"], headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
      texto_raw = response.read().decode("utf-8")
      data = json.loads(texto_raw)

      if isinstance(data, dict):

        def extraer_datos_serie():
          val_t, fecha_t, val_p, p_pasado, val_v, val_r, val_d = (
              None,
              None,
              None,
              None,
              None,
              None,
              None,
          )

          for k, serie in data.items():
            if isinstance(serie, dict) and "data" in serie:
              lista_data = serie["data"]
              if isinstance(lista_data, list) and len(lista_data) > 0:
                item_data = lista_data[0]
                if isinstance(item_data, dict) and "y" in item_data:
                  y_vals = item_data["y"]
                  x_vals = item_data.get("x", [])
                  if isinstance(y_vals, list) and len(y_vals) > 0:
                    actual = y_vals[-1]
                    f_act = x_vals[-1] if x_vals and len(x_vals) > 0 else None

                    k_lower = k.lower().strip()
                    if any(
                        sub in k_lower
                        for sub in ["temp", "temperatura", "ta", "t_aire"]
                    ):
                      val_t, fecha_t = actual, f_act
                    elif any(
                        sub in k_lower
                        for sub in ["pres", "presion", "barom", "qfe", "qff"]
                    ):
                      val_p = actual
                      if len(y_vals) >= 180:
                        p_pasado = y_vals[-180]
                      elif len(y_vals) > 1:
                        p_pasado = y_vals[0]
                    elif any(
                        sub in k_lower
                        for sub in ["dir_viento", "dd", "dir", "direccion"]
                    ):
                      val_d = actual
                    elif any(
                        sub in k_lower
                        for sub in [
                            "ff",
                            "viento",
                            "speed",
                            "vel",
                            "intensidad",
                        ]
                    ):
                      val_v = actual
                    elif any(
                        sub in k_lower
                        for sub in [
                            "racha",
                            "ráfaga",
                            "rafaga",
                            "gust",
                            "max",
                            "fx",
                            "vmax",
                            "vel_max",
                        ]
                    ):
                      val_r = actual

          return (
              val_t,
              fecha_t,
              val_p,
              p_pasado,
              val_v,
              val_r,
              val_d,
          )

        (
            temp_val,
            fecha_temp,
            pres_val,
            pres_pasado_val,
            viento_val,
            racha_val,
            dir_val,
        ) = extraer_datos_serie()

        temp_f = convertir_numero(temp_val)
        temp = f"{temp_f:.1f}°C" if temp_f is not None else "--"

        pres_f = convertir_numero(pres_val)
        tendencia_ifop = ""
        if pres_f is not None:
          p_pasado_f = convertir_numero(pres_pasado_val)
          if p_pasado_f is not None:
            dif = pres_f - p_pasado_f
            if dif > 0.2:
              tendencia_ifop = " ↗"
            elif dif < -0.2:
              tendencia_ifop = " ↘"
            else:
              tendencia_ifop = " ➔"
          pres = f"{pres_f:.1f} hPa{tendencia_ifop}"
        else:
          pres = "--"

        viento_f = convertir_numero(viento_val)
        viento = f"{viento_f:.1f} kt" if viento_f is not None else "--"

        racha_f = convertir_numero(racha_val)
        racha = f"{racha_f:.1f} kt" if racha_f is not None else "--"

        dir_num = convertir_numero(dir_val)
        if dir_num is not None:
          dir_viento = grados_a_cardinal(dir_num)
        else:
          dir_viento = (
              formatear_direccion(str(dir_val)) if dir_val is not None else ""
          )

        fecha_str = str(fecha_temp) if fecha_temp else "Reciente"
        es_valido = (
            temp_f is not None or viento_f is not None or pres_f is not None
        )
        estado_txt = "OPERATIVA" if es_valido else "SIN DATOS VÁLIDOS"

        return (
            es_valido,
            estado_txt,
            fecha_str,
            temp,
            pres,
            viento,
            dir_viento,
            racha,
        )

      return (
          False,
          "DATOS NO VÁLIDOS",
          "Estructura desconocida",
          "--",
          "--",
          "--",
          "",
          "--",
      )

  except Exception as e:
    return False, "SIN CONEXIÓN", str(e)[:30], "--", "--", "--", "", "--"


def generar_html(resultados_totales, hay_alerta):
  total_estaciones = len(resultados_totales)
  operativas = sum(1 for r in resultados_totales if r["ok"] is True)

  markers_js = ""
  for r in resultados_totales:
    color = "green" if r["ok"] else "red"
    dir_txt = f" ({r['dir_viento']})" if r["dir_viento"] else ""
    popup_txt = f"<b>{r['nombre']}</b><br>Estado: {r['estado']}<br>Temp: {r['temp']} | Viento: {r['viento']}{dir_txt} | Racha: {r['racha']} | Pres: {r['pres']}<br>Reporte: {r['ultimo']}<br><a href='{r['url']}' target='_blank'>Abrir enlace ↗</a>"

    markers_js += f"""
        L.circleMarker([{r['lat']}, {r['lon']}], {{
            color: '{color}', fillColor: '{color}', fillOpacity: 0.8, radius: 9
        }}).addTo(map).bindPopup("{popup_txt}");
        """

  cards_html = ""
  for r in resultados_totales:
    clase = "ok" if r["ok"] else "error"
    icono = "🔴" if not r["ok"] else "🟢"
    footer_texto = f"Reporte: {r['ultimo']}"

    if r["dir_viento"]:
      viento_contenido = (
          f'<span style="display: block; font-size: 0.65em; color: #1d4ed8;'
          f' font-weight: 800; line-height: 1.1;">🌬️ {r["dir_viento"]}</span>'
          f'<span style="display: block; font-size: 0.74em;'
          f' font-weight: 700; line-height: 1.1;">{r["viento"]}</span>'
      )
    else:
      viento_contenido = (
          '<span style="display: block; font-size: 0.65em; color: transparent;'
          ' font-weight: 800; line-height: 1.1; user-select: none;">-</span>'
          f'<span style="display: block; font-size: 0.74em;'
          f' font-weight: 700; line-height: 1.1;">{r["viento"]}</span>'
      )

    cuerpo_tarjeta = f"""
            <div class="card-body-content">
                <div class="temp-suelta">🌡️ {r['temp']}</div>
                <div class="weather-grid-3">
                    <div class="weather-item">{viento_contenido}</div>
                    <div class="weather-item"><span style="font-size: 0.74em; font-weight: 700;">💨 {r['racha']}</span></div>
                    <div class="weather-item"><span style="font-size: 0.70em; font-weight: 700;">⏲️ {r['pres']}</span></div>
                </div>
            </div>
        """

    cards_html += f"""
        <a href="{r['url']}" target="_blank" class="card-link">
            <div class="card {clase}">
                <div class="card-header">
                    <span class="station-name">{r['nombre']}</span>
                    <span class="status-badge">{icono}</span>
                </div>
                {cuerpo_tarjeta}
                <div class="card-footer-info">
                    <span class="time">{footer_texto}</span>
                    <span class="click-text">Ver ↗</span>
                </div>
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
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; color: #1e293b; padding: 15px; margin: 0; transition: background-color 0.5s ease; }}
        h1 {{ text-align: center; color: #0f2942; margin-bottom: 0; font-size: 22px; line-height: 1.2; font-weight: 700; }}
        .subtitle-line2 {{ text-align: center; color: #1e40af; margin-bottom: 6px; font-size: 16px; font-weight: bold; }}
        .subtitle {{ text-align: center; color: #64748b; margin-bottom: 12px; font-size: 12px; }}
        .summary {{ text-align: center; font-weight: bold; margin-bottom: 15px; color: #0f2942; font-size: 14px; background: #ffffff; padding: 6px 16px; border-radius: 20px; max-width: 280px; margin-left: auto; margin-right: auto; box-shadow: 0 2px 6px rgba(0,0,0,0.06); border: 1px solid #cbd5e1; }}
        
        @keyframes parpadeoFondo {{ 
            0% {{ background-color: #f4f6f9; }} 
            50% {{ background-color: #fca5a5; }} 
            100% {{ background-color: #f4f6f9; }} 
        }}
        body.alerta-activa {{ animation: parpadeoFondo 1.5s infinite; }}

        .banner-alerta {{ background: linear-gradient(135deg, #ef4444, #dc2626); color: white; text-align: center; font-weight: bold; padding: 10px; border-radius: 8px; margin-bottom: 15px; font-size: 14px; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3); }}
        #map {{ height: 350px; width: 100%; max-width: 1200px; margin: 0 auto 20px auto; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); border: 1px solid #cbd5e1; }}
        
        .grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); 
            gap: 15px; 
            max-width: 1200px; 
            margin: 0 auto; 
            align-items: stretch; 
        }}
        
        .card-link {{ text-decoration: none; color: inherit; display: flex; flex-direction: column; height: 100%; }}
        .card {{ 
            border-radius: 14px; 
            padding: 10px 10px; 
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); 
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            height: 100%; 
            box-sizing: border-box;
        }}
        .card.ok {{ 
            background: linear-gradient(135deg, #dbeafe 0%, #cbd5e1 55%, #94a3b8 100%); 
            border: 1px solid #94a3b8;
            border-left: 6px solid #16a34a; 
        }}
        .card.error {{ 
            background: linear-gradient(135deg, #fee2e2 0%, #fecaca 55%, #f87171 100%); 
            border: 1px solid #f87171;
            border-left: 6px solid #dc2626; 
        }}
        .card:hover {{ 
            transform: translateY(-3px); 
            box-shadow: 0 8px 20px rgba(30, 64, 175, 0.2); 
        }}
        .card.error:hover {{
            box-shadow: 0 8px 20px rgba(220, 38, 38, 0.3); 
        }}
        
        .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 4px; }}
        .station-name {{ font-weight: bold; font-size: 13.5px; color: #0f172a; line-height: 1.1; }}
        .status-badge {{ font-size: 11px; }}
        
        .card-body-content {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 4px;
            margin: 6px 0;
        }}
        .temp-suelta {{
            font-size: 0.90em;
            font-weight: 800;
            color: #0f172a;
            white-space: nowrap;
            display: flex;
            align-items: center;
        }}
        
        .weather-grid-3 {{ 
            display: grid; 
            grid-template-columns: 1fr 0.95fr 1.15fr; 
            gap: 2px; 
            flex: 1;
            align-items: stretch; 
        }}
        .weather-item {{ 
            color: #0f172a; 
            background: rgba(255, 255, 255, 0.9); 
            padding: 3px 1px; 
            border-radius: 6px; 
            border: 1px solid rgba(255, 255, 255, 0.95); 
            text-align: center; 
            white-space: nowrap; 
            display: flex; 
            flex-direction: column; 
            justify-content: center; 
            align-items: center; 
        }}
        
        .card-footer-info {{ display: flex; justify-content: space-between; align-items: center; margin-top: 2px; border-top: 1px solid rgba(255, 255, 255, 0.4); padding-top: 3px; }}
        .time {{ font-size: 0.68em; color: #334155; }}
        .click-text {{ font-size: 0.68em; color: #1d4ed8; font-weight: bold; font-style: italic; }}
        
        .footer-dev {{ background: linear-gradient(135deg, #0f2942, #1e3a8a); color: #f8fafc; text-align: center; font-weight: 600; padding: 10px 24px; border-radius: 30px; margin: 30px auto 15px auto; display: table; font-size: 13px; box-shadow: 0 4px 12px rgba(15, 41, 66, 0.2); border: 1px solid rgba(255,255,255,0.15); }}
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
  resultados_dict = {}
  hubo_fallas = False

  for est in ESTACIONES_DIRECTEMAR:
    ok, estado, ultimo, temp, pres, viento, dir_viento, racha = (
        consultar_directemar(est)
    )
    if not ok:
      hubo_fallas = True
    resultados_dict[est["nombre"]] = {
        "nombre": est["nombre"],
        "url": est["url"],
        "lat": est["lat"],
        "lon": est["lon"],
        "ok": ok,
        "estado": estado,
        "ultimo": ultimo,
        "temp": temp,
        "pres": pres,
        "viento": viento,
        "dir_viento": dir_viento,
        "racha": racha,
    }

  for faro in ESTACIONES_FAROS:
    ok, estado, temp, pres, viento, dir_viento, racha, ultimo = (
        consultar_wunderground_web(faro)
    )
    if not ok:
      hubo_fallas = True
    resultados_dict[faro["nombre"]] = {
        "nombre": faro["nombre"],
        "url": faro["url"],
        "lat": faro["lat"],
        "lon": faro["lon"],
        "ok": ok,
        "estado": estado,
        "ultimo": ultimo,
        "temp": temp,
        "pres": pres,
        "viento": viento,
        "dir_viento": dir_viento,
        "racha": racha,
    }

  for est_ifop in ESTACIONES_IFOP:
    ok, estado, ultimo, temp, pres, viento, dir_viento, racha = consultar_ifop(
        est_ifop
    )
    if not ok:
      hubo_fallas = True
    resultados_dict[est_ifop["nombre"]] = {
        "nombre": est_ifop["nombre"],
        "url": est_ifop["url"],
        "lat": est_ifop["lat"],
        "lon": est_ifop["lon"],
        "ok": ok,
        "estado": estado,
        "ultimo": ultimo,
        "temp": temp,
        "pres": pres,
        "viento": viento,
        "dir_viento": dir_viento,
        "racha": racha,
    }

  resultados_totales = [
      resultados_dict[nombre]
      for nombre in ORDEN_ESTACIONES
      if nombre in resultados_dict
  ]

  generar_html(resultados_totales, hubo_fallas)
  subir_a_github()


def subir_a_github():
  try:
    print("Sincronizando cambios con GitHub...")
    # SE MODIFICÓ AQUÍ PARA QUE TAMBIÉN SUBA EL HISTORIAL DE PRESIÓN AL REPOSITORIO
    subprocess.run(
        ["git", "add", "index.html", ARCHIVO_HISTORIAL], check=True
    )
    resultado = subprocess.run(
        [
            "git",
            "commit",
            "-m",
            (
                "Actualización de datos, corrección medianoche y persistencia"
                " de historial [skip ci]"
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
