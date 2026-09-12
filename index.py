from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json
import re
import ssl
import subprocess
import time
import urllib.request


# ============================================================
# CONFIGURACIÓN WEATHER UNDERGROUND (PWS)
# ============================================================
# IMPORTANTE:
# No compartas tu API Key públicamente.
# Pega aquí tu API Key de Weather Underground.
WU_API_KEY = "9214a7502910484094a750291048405d"


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

TOLERANCIA_MINUTOS = 12
INTERVALO_VERIFICACION_SEGUNDOS = 300   # 5 minutos
REFRESH_PAGINA_SEGUNDOS = 30            # actualización del navegador

# True = no muestra en consola la lectura de cada estación.
# Solo muestra resumen y estaciones con problemas.
VERIFICACION_SILENCIOSA = True

ZONA_CHILE = ZoneInfo("America/Santiago")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


# ============================================================
# ESTACIONES DIRECTEMAR
# ============================================================

ESTACIONES_DIRECTEMAR = [
    {
        "nombre": "Capitanía de Puerto Constitución-7700",
        "url": "http://web.directemar.cl/met/jturno/estaciones/constitucion/index.htm",
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
        "url": "http://web.directemar.cl/met/jturno/estaciones/talcahuano/index.htm",
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


# ============================================================
# FAROS WEATHER UNDERGROUND
# ============================================================

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


# ============================================================
# HORA CHILE
# ============================================================

def obtener_hora_chile():
    return datetime.now(ZONA_CHILE)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def convertir_numero(valor):
    if valor is None:
        return None

    try:
        return float(str(valor).replace(",", "."))
    except (ValueError, TypeError):
        return None


def formato_numero(valor, decimales=1):
    numero = convertir_numero(valor)

    if numero is None:
        return "--"

    return f"{numero:.{decimales}f}"


def escapar_html(texto):
    texto = str(texto)
    return (
        texto.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


# ============================================================
# DIRECTEMAR
# ============================================================

def consultar_directemar(est):

    try:
        req = urllib.request.Request(
            est["url"],
            headers=HEADERS
        )

        with urllib.request.urlopen(
            req,
            timeout=10,
            context=ctx
        ) as response:

            html = response.read().decode(
                "utf-8",
                errors="ignore"
            )

        texto_plano = re.sub(
            r"<[^>]+>",
            " ",
            html
        )

        texto_plano = (
            texto_plano
            .replace("\xa0", " ")
            .replace("&nbsp;", " ")
        )

        texto_plano = re.sub(
            r"\s+",
            " ",
            texto_plano
        ).strip()

        # ----------------------------------------------------
        # TEMPERATURA
        # ----------------------------------------------------

        temp = "--"

        temp_match = re.search(
            r"Temperature\s*\|?\s*"
            r"([\-]?\d+(?:[.,]\d+)?)\s*°?\s*C",
            texto_plano,
            re.IGNORECASE
        )

        if temp_match:
            valor = convertir_numero(temp_match.group(1))

            if valor is not None:
                temp = f"{valor:.1f}°C"

        # Respaldo por si una página está en español.
        if temp == "--":
            temp_match = re.search(
                r"(?:Temperatura|Temp\.?)\s*"
                r"[:|]?\s*([\-]?\d+(?:[.,]\d+)?)"
                r"\s*°?\s*C",
                texto_plano,
                re.IGNORECASE
            )

            if temp_match:
                valor = convertir_numero(temp_match.group(1))

                if valor is not None:
                    temp = f"{valor:.1f}°C"

        # ----------------------------------------------------
        # HUMEDAD RELATIVA
        # ----------------------------------------------------
        # IMPORTANTE:
        # Se busca específicamente "Humidity".
        # Así evitamos tomar Dew Point por error.

        hum = "--"

        hum_match = re.search(
            r"Humidity\s*\|?\s*"
            r"(\d+(?:[.,]\d+)?)\s*%",
            texto_plano,
            re.IGNORECASE
        )

        if not hum_match:
            hum_match = re.search(
                r"Humedad\s*(?:Relativa)?\s*\|?\s*"
                r"(\d+(?:[.,]\d+)?)\s*%",
                texto_plano,
                re.IGNORECASE
            )

        if hum_match:
            valor = convertir_numero(hum_match.group(1))

            if valor is not None:
                hum = f"{valor:.1f}%"

        # ----------------------------------------------------
        # VIENTO PROMEDIO
        # ----------------------------------------------------
        # DIRECTEMAR utiliza:
        # Wind Speed (avg) ... kts

        viento = "--"

        viento_match = re.search(
            r"Wind\s*Speed\s*\(\s*avg\s*\)\s*\|?\s*"
            r"(\d+(?:[.,]\d+)?)\s*kts",
            texto_plano,
            re.IGNORECASE
        )

        if viento_match:
            valor = convertir_numero(viento_match.group(1))

            if valor is not None:
                viento = f"{valor:.1f} kt"

        # Respaldo adicional.
        if viento == "--":
            viento_match = re.search(
                r"(?:Wind\s*Speed|Velocidad\s*del\s*viento|Viento)"
                r".{0,30}?(\d+(?:[.,]\d+)?)\s*(?:kts|kt)",
                texto_plano,
                re.IGNORECASE
            )

            if viento_match:
                valor = convertir_numero(viento_match.group(1))

                if valor is not None:
                    viento = f"{valor:.1f} kt"

        # ----------------------------------------------------
        # HORA DE ACTUALIZACIÓN
        # ----------------------------------------------------

        match_fecha = re.search(
            r"Page\s+updated\s+"
            r"(\d{1,2}-\d{1,2}-\d{4}\s+\d{1,2}:\d{2}"
            r"(?::\d{2})?)",
            texto_plano,
            re.IGNORECASE
        )

        if not match_fecha:
            return (
                False,
                "SIN DATOS VÁLIDOS",
                "N/D",
                temp,
                hum,
                viento
            )

        fecha_str = match_fecha.group(1)

        formato_fecha = (
            "%d-%m-%Y %H:%M:%S"
            if fecha_str.count(":") == 2
            else "%d-%m-%Y %H:%M"
        )

        fecha_estacion = datetime.strptime(
            fecha_str,
            formato_fecha
        ).replace(tzinfo=ZONA_CHILE)

        ahora = obtener_hora_chile()

        dif_min = (
            ahora - fecha_estacion
        ).total_seconds() / 60

        dif_min = abs(dif_min)

        # Mantiene compatibilidad con estaciones que eventualmente
        # puedan entregar la hora con una diferencia aproximada de 3 h.
        dentro_tolerancia = (
            dif_min <= TOLERANCIA_MINUTOS
            or 170 <= dif_min <= 200
        )

        if dentro_tolerancia:
            ok = True
            estado = "OPERATIVA"
        else:
            ok = False
            estado = f"DESACTUALIZADA ({int(dif_min)} min)"

        return (
            ok,
            estado,
            fecha_str,
            temp,
            hum,
            viento
        )

    except Exception as e:

        if not VERIFICACION_SILENCIOSA:
            print(
                f"Error Directemar {est['nombre']}: {e}"
            )

        return (
            False,
            "SIN CONEXIÓN",
            "Error de red",
            "--",
            "--",
            "--"
        )


# ============================================================
# WEATHER UNDERGROUND - OBSERVACIÓN ACTUAL
# ============================================================

def consultar_wunderground_actual(station_id):

    url = (
        "https://api.weather.com/v2/pws/"
        "observations/current"
        f"?stationId={station_id}"
        "&format=json"
        "&units=m"
        "&numericPrecision=decimal"
        f"&apiKey={WU_API_KEY}"
    )

    req = urllib.request.Request(
        url,
        headers=HEADERS
    )

    with urllib.request.urlopen(
        req,
        timeout=10,
        context=ctx
    ) as response:

        return json.loads(
            response.read().decode("utf-8")
        )


# ============================================================
# WEATHER UNDERGROUND - HISTORIAL RÁPIDO 24 H
# ============================================================

def consultar_wunderground_24h(station_id):

    url = (
        "https://api.weather.com/v2/pws/"
        "observations/all/1day"
        f"?stationId={station_id}"
        "&format=json"
        "&units=m"
        "&numericPrecision=decimal"
        f"&apiKey={WU_API_KEY}"
    )

    req = urllib.request.Request(
        url,
        headers=HEADERS
    )

    with urllib.request.urlopen(
        req,
        timeout=10,
        context=ctx
    ) as response:

        return json.loads(
            response.read().decode("utf-8")
        )


# ============================================================
# FECHA DE WEATHER UNDERGROUND
# ============================================================

def obtener_fecha_observacion_wu(obs):

    obs_utc = obs.get("obsTimeUtc")

    if obs_utc:

        try:

            if obs_utc.endswith("Z"):
                obs_utc = obs_utc[:-1] + "+00:00"

            fecha = datetime.fromisoformat(
                obs_utc
            )

            if fecha.tzinfo is None:
                fecha = fecha.replace(
                    tzinfo=timezone.utc
                )

            return fecha.astimezone(
                ZONA_CHILE
            )

        except Exception:
            pass

    epoch = obs.get("epoch")

    if epoch:

        try:
            return datetime.fromtimestamp(
                float(epoch),
                timezone.utc
            ).astimezone(
                ZONA_CHILE
            )
        except Exception:
            pass

    return None


# ============================================================
# WEATHER UNDERGROUND - FAROS
# ============================================================

def consultar_wunderground_pws( station_id, nombre_faro ):

    try:

        # ----------------------------------------------------
        # PRIMERO: OBSERVACIÓN ACTUAL
        # ----------------------------------------------------

        data = consultar_wunderground_actual(
            station_id
        )

        observations = data.get(
            "observations",
            []
        )

        fuente = "actual"

        # ----------------------------------------------------
        # SI NO HAY OBSERVACIÓN ACTUAL,
        # CONSULTAMOS LAS ÚLTIMAS 24 HORAS
        # ----------------------------------------------------

        if not observations:

            data = consultar_wunderground_24h(
                station_id
            )

            observations = data.get(
                "observations",
                []
            )

            fuente = "historial 24 h"

        if not observations:

            return (
                False,
                "SIN CONEXIÓN",
                "--",
                "--",
                "--",
                "N/D"
            )

        # La observación más reciente.
        observations.sort(
            key=lambda x: x.get("epoch", 0),
            reverse=True
        )

        obs = observations[0]

        fecha_obs = obtener_fecha_observacion_wu(
            obs
        )

        ahora = obtener_hora_chile()

        # ----------------------------------------------------
        # DATOS METEOROLÓGICOS
        # ----------------------------------------------------

        metric = obs.get(
            "metric",
            {}
        )

        # Temperatura
        temp = metric.get("temp")

        if temp is None:
            temp = metric.get("tempAvg")

        temp_num = convertir_numero(temp)

        temp_str = (
            f"{temp_num:.1f}°C"
            if temp_num is not None
            else "--"
        )

        # Humedad
        # IMPORTANTE:
        # Weather Underground entrega humidity
        # en el nivel superior de la observación.

        hum = obs.get("humidity")

        if hum is None:
            hum = obs.get("humidityAvg")

        hum_num = convertir_numero(hum)

        hum_str = (
            f"{hum_num:.1f}%"
            if hum_num is not None
            else "--"
        )

        # Viento
        # En current: metric.windSpeed = km/h
        # En historial: metric.windspeedAvg = km/h

        wind = metric.get("windSpeed")

        if wind is None:
            wind = metric.get("windspeedAvg")

        wind_num = convertir_numero(wind)

        if wind_num is not None:
            viento_kt = wind_num / 1.852
            viento_str = f"{viento_kt:.1f} kt"
        else:
            viento_str = "--"

        # ----------------------------------------------------
        # ÚLTIMA OBSERVACIÓN
        # ----------------------------------------------------

        if fecha_obs:

            diferencia = (
                ahora - fecha_obs
            ).total_seconds() / 60

            diferencia = abs(diferencia)

            ultimo = fecha_obs.strftime(
                "%d-%m-%Y %H:%M:%S"
            )

            diferencia_int = int(diferencia)

        else:

            diferencia = 9999
            diferencia_int = 9999
            ultimo = "N/D"

        # ----------------------------------------------------
        # ESTADO DEL FARO
        # ----------------------------------------------------

        if diferencia <= TOLERANCIA_MINUTOS:

            ok = True
            estado = "OPERATIVA"

        else:

            ok = False
            estado = (
                f"DESACTUALIZADA "
                f"({diferencia_int} min)"
            )

        if not VERIFICACION_SILENCIOSA:

            print(
                f"[WU] {nombre_faro}: "
                f"{estado} | "
                f"Temp: {temp_str} | "
                f"Hum: {hum_str} | "
                f"Viento: {viento_str} | "
                f"Último: {ultimo} | "
                f"Fuente: {fuente}"
            )

        return (
            ok,
            estado,
            temp_str,
            hum_str,
            viento_str,
            ultimo
        )

    except Exception as e:

        if not VERIFICACION_SILENCIOSA:

            print(
                f"Excepción WU PWS "
                f"[{nombre_faro}]: {e}"
            )

        return (
            False,
            "SIN CONEXIÓN",
            "--",
            "--",
            "--",
            "N/D"
        )


# ============================================================
# GENERAR HTML
# ============================================================

def generar_html( resultados_directemar, resultados_faros, hay_alerta ):

    total_estaciones = (
        len(resultados_directemar)
        + len(resultados_faros)
    )

    operativas = (
        sum(
            1
            for r in resultados_directemar
            if r["ok"]
        )
        +
        sum(
            1
            for f in resultados_faros
            if f["ok"]
        )
    )

    # --------------------------------------------------------
    # MARCADORES DEL MAPA
    # --------------------------------------------------------

    markers_js = ""

    for r in resultados_directemar:

        color = "green" if r["ok"] else "red"

        markers_js += f""" L.circleMarker( [{r['lat']}, {r['lon']}], {{ color: '{color}', fillColor: '{color}', fillOpacity: 0.8, radius: 9 }} ).addTo(map).bindPopup( "<b>{escapar_html(r['nombre'])}</b><br>" "Estado: {escapar_html(r['estado'])}<br>" "Temp: {escapar_html(r['temp'])} | " "Hum: {escapar_html(r['hum'])} | " "Viento: {escapar_html(r['viento'])}<br>" "Reporte: {escapar_html(r['ultimo'])}<br>" "<a href='{r['url']}' target='_blank'>" "Abrir enlace ↗</a>" ); """

    for faro in resultados_faros:

        color = "green" if faro["ok"] else "red"

        markers_js += f""" L.circleMarker( [{faro['lat']}, {faro['lon']}], {{ color: '{color}', fillColor: '{color}', fillOpacity: 0.8, radius: 9 }} ).addTo(map).bindPopup( "<b>{escapar_html(faro['nombre'])}</b><br>" "Estado: {escapar_html(faro['estado'])}<br>" "Temp: {escapar_html(faro['temp'])} | " "Hum: {escapar_html(faro['hum'])} | " "Viento: {escapar_html(faro['viento'])}<br>" "Reporte: {escapar_html(faro['ultimo'])}<br>" "<a href='{faro['url']}' target='_blank'>" "Abrir enlace ↗</a>" ); """

    # --------------------------------------------------------
    # TARJETAS
    # --------------------------------------------------------

    cards_html = ""

    for r in resultados_directemar:

        clase = "ok" if r["ok"] else "error"
        icono = "🟢" if r["ok"] else "🔴"

        cards_html += f""" <a href="{r['url']}" target="_blank" class="card-link"> <div class="card {clase}"> <strong> {escapar_html(r['nombre'])} </strong> <div class="status"> {icono} {escapar_html(r['estado'])} </div> <div class="weather-info"> <span>🌡️ {escapar_html(r['temp'])}</span> <span>💧 {escapar_html(r['hum'])}</span> <span>🌬️ {escapar_html(r['viento'])}</span> </div> <div class="time"> Último reporte: {escapar_html(r['ultimo'])} </div> <div class="click-text"> Clic para abrir ↗ </div> </div> </a> """

    for faro in resultados_faros:

        clase = "ok" if faro["ok"] else "error"
        icono = "🟢" if faro["ok"] else "🔴"

        cards_html += f""" <a href="{faro['url']}" target="_blank" class="card-link"> <div class="card {clase}"> <strong> {escapar_html(faro['nombre'])} </strong> <div class="status"> {icono} {escapar_html(faro['estado'])} </div> <div class="weather-info"> <span>🌡️ {escapar_html(faro['temp'])}</span> <span>💧 {escapar_html(faro['hum'])}</span> <span>🌬️ {escapar_html(faro['viento'])}</span> </div> <div class="time"> Último reporte: {escapar_html(faro['ultimo'])} </div> <div class="click-text"> Clic para abrir ↗ </div> </div> </a> """

    # --------------------------------------------------------
    # ALERTA
    # --------------------------------------------------------

    alerta_class = "alerta-activa" if hay_alerta else ""

    if hay_alerta:

        alerta_banner = (
            '<div class="banner-alerta">'
            '⚠️ ¡ATENCIÓN: HAY ESTACIONES '
            'CON FALLAS O DESACTUALIZADAS! ⚠️'
            '</div>'
        )

    else:

        alerta_banner = ""

    hora_actual_chile = (
        obtener_hora_chile()
        .strftime("%d-%m-%Y %H:%M:%S")
    )

    # --------------------------------------------------------
    # HTML
    # --------------------------------------------------------

    html = f"""<!DOCTYPE html> <html lang="es"> <head> <meta charset="UTF-8"> <meta name="viewport" content="width=device-width, initial-scale=1.0"> <meta http-equiv="refresh" content="{REFRESH_PAGINA_SEGUNDOS}"> <title> Monitor de Estaciones Automáticas </title> <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" > <style> body {{ font-family: Arial, sans-serif; background-color: #f4f6f9; padding: 10px; margin: 0; }} h1 {{ text-align: center; color: #1a252f; margin-bottom: 0; font-size: 20px; line-height: 1.1; }} .subtitle-line2 {{ text-align: center; color: #1a252f; margin-bottom: 6px; font-size: 16px; font-weight: bold; }} .subtitle {{ text-align: center; color: #7f8c8d; margin-bottom: 8px; font-size: 12px; }} .summary {{ text-align: center; font-weight: bold; margin-bottom: 12px; color: #2c3e50; font-size: 14px; }} @keyframes parpadeo {{ 0% {{ background-color: #f4f6f9; }} 50% {{ background-color: #fadbd8; }} 100% {{ background-color: #f4f6f9; }} }} body.alerta-activa {{ animation: parpadeo 1.5s infinite; }} .banner-alerta {{ background-color: #e74c3c; color: white; text-align: center; font-weight: bold; padding: 8px; border-radius: 6px; margin-bottom: 12px; font-size: 14px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }} #map {{ height: 350px; width: 100%; max-width: 1200px; margin: 0 auto 15px auto; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.2); }} .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 10px; max-width: 1200px; margin: 0 auto; }} .card-link {{ text-decoration: none; color: inherit; display: block; }} .card {{ border-radius: 8px; padding: 10px; background: white; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border-left: 6px solid #ccc; transition: transform 0.2s; }} .card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.15); }} .card.ok {{ border-left-color: #2ecc71; }} .card.error {{ border-left-color: #e74c3c; }} .status {{ font-weight: bold; margin-top: 3px; font-size: 12px; }} .ok .status {{ color: #27ae60; }} .error .status {{ color: #c0392b; }} .weather-info {{ font-size: 0.9em; color: #34495e; margin-top: 5px; font-weight: bold; background: #f8f9fa; padding: 5px; border-radius: 4px; display: flex; justify-content: space-around; }} .time {{ font-size: 0.75em; color: #7f8c8d; margin-top: 4px; }} .click-text {{ font-size: 0.65em; color: #95a5a6; margin-top: 4px; font-style: italic; text-align: right; }} .footer-dev {{ background: linear-gradient( to bottom, #1f618d, #154360 ); color: white; text-align: center; font-weight: 500; padding: 8px 20px; border-radius: 20px; margin: 25px auto 10px auto; display: table; font-size: 13px; box-shadow: 0 3px 6px rgba(0,0,0,0.2); }} </style> </head> <body class="{alerta_class}"> <h1> Monitor de Estaciones Automáticas </h1> <div class="subtitle-line2"> Centro Zonal de Meteorología Marina de Talcahuano </div> <div class="subtitle"> Última verificación: {hora_actual_chile} (Tolerancia: {TOLERANCIA_MINUTOS} min) </div> {alerta_banner} <div class="summary"> Estaciones Operativas: {operativas} de {total_estaciones} </div> <div id="map"></div> <div class="grid"> {cards_html} </div> <div style="text-align: center;"> <div class="footer-dev"> Desarrollado por Sgto 2° (Met.) Luis Diego Achurra Garcés </div> </div> <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"> </script> <script> var map = L.map('map') .setView([-37.5, -73.2], 7); L.tileLayer( 'https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ maxZoom: 12, attribution: '© OpenStreetMap contributors' }} ).addTo(map); {markers_js} </script> </body> </html> """

    with open(
        "index.html",
        "w",
        encoding="utf-8"
    ) as f:

        f.write(html)

    print("✓ index.html actualizado.")


# ============================================================
# SINCRONIZAR CON GITHUB
# ============================================================

def subir_a_github():

    try:

        subprocess.run(
            ["git", "add", "index.html"],
            check=True
        )

        # Si no hay cambios, git commit devuelve error.
        # Lo tratamos como una situación normal.
        resultado_commit = subprocess.run(
            [
                "git",
                "commit",
                "-m",
                (
                    "Actualizacion monitor estaciones "
                    "[skip ci]"
                )
            ],
            capture_output=True,
            text=True
        )

        if resultado_commit.returncode != 0:

            mensaje = (
                resultado_commit.stdout
                + resultado_commit.stderr
            )

            if (
                "nothing to commit" in mensaje.lower()
                or "no changes added" in mensaje.lower()
            ):
                print(
                    "Sin cambios nuevos para subir a GitHub."
                )
                return

            print(
                "Error al crear commit:"
            )
            print(mensaje)
            return

        subprocess.run(
            ["git", "push"],
            check=True
        )

        print(
            "✓ Cambios sincronizados con GitHub."
        )

    except subprocess.CalledProcessError as e:

        print(
            f"Error al sincronizar con Git: {e}"
        )


# ============================================================
# MONITOREO COMPLETO
# ============================================================

def ejecutar_monitoreo():

    hora_inicio = obtener_hora_chile().strftime(
        "%H:%M:%S"
    )

    print(
        f"\n--- [{hora_inicio}] "
        f"Verificación silenciosa del litoral ---"
    )

    resultados_directemar = []
    resultados_faros = []

    estaciones_con_falla = []


    # --------------------------------------------------------
    # DIRECTEMAR
    # --------------------------------------------------------

    for est in ESTACIONES_DIRECTEMAR:

        (
            ok,
            estado,
            ultimo,
            temp,
            hum,
            viento
        ) = consultar_directemar(est)

        resultado = {
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
        }

        resultados_directemar.append(resultado)

        if not ok:
            estaciones_con_falla.append(
                f"{est['nombre']} -> {estado}"
            )


    # --------------------------------------------------------
    # FAROS
    # --------------------------------------------------------

    for faro in ESTACIONES_FAROS:

        (
            ok,
            estado,
            temp,
            hum,
            viento,
            ultimo
        ) = consultar_wunderground_pws(
            faro["station_id"],
            faro["nombre"]
        )

        resultado = {
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
        }

        resultados_faros.append(resultado)

        if not ok:
            estaciones_con_falla.append(
                f"{faro['nombre']} -> {estado}"
            )


    # --------------------------------------------------------
    # ALERTA GENERAL
    # --------------------------------------------------------

    hubo_fallas = len(estaciones_con_falla) > 0


    # --------------------------------------------------------
    # MOSTRAR SOLO RESUMEN
    # --------------------------------------------------------

    if hubo_fallas:

        print("⚠️ ESTACIONES CON PROBLEMAS:")

        for falla in estaciones_con_falla:
            print(f" • {falla}")

    else:

        print(
            "✓ Todas las estaciones están "
            "dentro de la tolerancia."
        )


    # --------------------------------------------------------
    # GENERAR PÁGINA
    # --------------------------------------------------------

    generar_html(
        resultados_directemar,
        resultados_faros,
        hubo_fallas
    )


    # --------------------------------------------------------
    # GITHUB
    # --------------------------------------------------------

    subir_a_github()


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

if __name__ == "__main__":

    if (
        not WU_API_KEY
        or WU_API_KEY == "PEGA_AQUI_TU_API_KEY"
    ):

        print(
            "\n⚠️ Falta ingresar la API Key de "
            "Weather Underground."
        )

        print(
            "Edita la línea WU_API_KEY al comienzo "
            "del script."
        )

        input(
            "\nPresiona ENTER para cerrar..."
        )

    else:

        print(
            "============================================"
        )
        print(
            " MONITOR DE ESTACIONES AUTOMÁTICAS"
        )
        print(
            " Verificación automática cada 5 minutos"
        )
        print(
            "============================================"
        )

        while True:

            try:

                ejecutar_monitoreo()

                proxima = (
                    obtener_hora_chile()
                    + timedelta(
                        seconds=INTERVALO_VERIFICACION_SEGUNDOS
                    )
                ).strftime("%H:%M:%S")

                print(
                    f"Próxima verificación: {proxima}"
                )

                print(
                    "Esperando 5 minutos...\n"
                )

                time.sleep(
                    INTERVALO_VERIFICACION_SEGUNDOS
                )

            except KeyboardInterrupt:

                print(
                    "\nMonitor detenido por el usuario."
                )

                break

            except Exception as e:

                print(
                    f"\n⚠️ Error general: {e}"
                )

                print(
                    "El monitor intentará nuevamente "
                    "en 30 segundos."
                )

                time.sleep(30)
