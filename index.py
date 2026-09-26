import urllib.request
import json
import ssl
from datetime import datetime
import pytz

# Configuración de zona horaria y seguridad SSL
ZONA_CHILE = pytz.timezone("America/Santiago")
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
}

def obtener_hora_chile():
    return datetime.now(ZONA_CHILE)

def convertir_numero(val):
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def grados_a_cardinal(grados):
    if grados is None:
        return ""
    val = int((grados / 22.5) + 0.5)
    cardinales = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return cardinales[(val % 16)]

def formatear_direccion(dir_str):
    if not dir_str:
        return ""
    return str(dir_str).strip().upper()

def consultar_ifop(est):
    try:
        req = urllib.request.Request(est["api_url"], headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
            texto_raw = response.read().decode("utf-8")
            data = json.loads(texto_raw)

            # --- DEPURACIÓN: Ver las claves disponibles y muestra del JSON ---
            print(f"\n--- DEBUG IFOP [{est['nombre']}] ---")
            if isinstance(data, dict):
                print("Claves principales encontradas:", list(data.keys()))
                for k, serie in data.items():
                    if isinstance(serie, dict):
                        lista_data = serie.get("data", [])
                        if isinstance(lista_data, list) and len(lista_data) > 0:
                            print(f"  -> Serie '{k}': {len(lista_data)} registros. Último elemento: {lista_data[0]}")
            # -------------------------------------------------------------

            if isinstance(data, dict):
                def extraer_datos_serie():
                    val_t, fecha_t, val_p, p_pasado, val_v, val_r, val_d, val_pp = None, None, None, None, None, None, None, None
                    hoy_chile = obtener_hora_chile().date()
                    
                    for k, serie in data.items():
                        if isinstance(serie, dict):
                            k_lower = k.lower().strip()
                            lista_data = serie.get("data", [])
                            
                            if isinstance(lista_data, list) and len(lista_data) > 0:
                                item_data = lista_data[0]
                                if isinstance(item_data, dict) and "y" in item_data:
                                    y_vals = item_data["y"]
                                    x_vals = item_data.get("x", [])
                                    if isinstance(y_vals, list) and len(y_vals) > 0:
                                        actual = y_vals[-1]
                                        f_act = x_vals[-1] if x_vals and len(x_vals) > 0 else None
                                        
                                        if any(sub in k_lower for sub in ["temp", "temperatura", "ta", "t_aire"]):
                                            val_t, fecha_t = actual, f_act
                                        elif any(sub in k_lower for sub in ["pres", "presion", "barom", "qfe", "qff"]):
                                            val_p = actual
                                            if len(y_vals) >= 180:
                                                p_pasado = y_vals[-180]
                                            elif len(y_vals) > 1:
                                                p_pasado = y_vals[0]
                                        elif any(sub in k_lower for sub in ["dir_viento", "dd", "dir", "direccion"]):
                                            val_d = actual
                                        elif any(sub in k_lower for sub in ["ff", "viento", "speed", "vel", "intensidad"]):
                                            val_v = actual
                                        elif any(sub in k_lower for sub in ["racha", "ráfaga", "rafaga", "gust", "max", "fx", "vmax", "vel_max"]):
                                            val_r = actual
                                        elif any(sub in k_lower for sub in ["lluvia", "pp", "precip", "precipitacion", "agua", "acum", "mm", "rain"]):
                                            valores_hoy = []
                                            if isinstance(x_vals, list) and len(x_vals) == len(y_vals):
                                                for xv, yv in zip(x_vals, y_vals):
                                                    if yv is not None and isinstance(yv, (int, float)):
                                                        try:
                                                            if isinstance(xv, (int, float)):
                                                                dt = datetime.fromtimestamp(xv / 1000.0 if xv > 1e11 else xv, tz=ZONA_CHILE)
                                                            elif isinstance(xv, str):
                                                                dt = datetime.fromisoformat(xv.replace('Z', '+00:00')).astimezone(ZONA_CHILE)
                                                            else:
                                                                dt = None
                                                            
                                                            if dt and dt.date() == hoy_chile:
                                                                valores_hoy.append(yv)
                                                        except Exception:
                                                            pass
                                            
                                            if valores_hoy:
                                                val_pp = max(valores_hoy)
                                            else:
                                                val_pp = y_vals[-1]

                    return val_t, fecha_t, val_p, p_pasado, val_v, val_r, val_d, val_pp

                temp_val, fecha_temp, pres_val, pres_pasado_val, viento_val, racha_val, dir_val, pp_val = extraer_datos_serie()

                temp_f = convertir_numero(temp_val)
                temp = f"{temp_f:.1f}°C" if temp_f is not None else "--"

                pres_f = convertir_numero(pres_val)
                tendencia_ifop = ""
                if pres_f is not None:
                    p_pasado_f = convertir_numero(pres_pasado_val)
                    if p_pasado_f is not None:
                        dif = pres_f - p_pasado_f
                        if dif > 0.2: tendencia_ifop = " ↗"
                        elif dif < -0.2: tendencia_ifop = " ↘"
                        else: tendencia_ifop = " ➔"
                    pres = f"{pres_f:.1f} hPa{tendencia_ifop}"
                else:
                    pres = "--"

                viento_f = convertir_numero(viento_val)
                viento = f"{viento_f:.1f} kt" if viento_f is not None else "--"

                racha_f = convertir_numero(racha_val)
                racha = f"{racha_f:.1f} kt" if racha_f is not None else "--"

                pp_f = convertir_numero(pp_val)
                precipitacion = f"{pp_f:.1f} mm" if pp_f is not None else "--"

                dir_num = convertir_numero(dir_val)
                if dir_num is not None:
                    dir_viento = grados_a_cardinal(dir_num)
                else:
                    dir_viento = formatear_direccion(str(dir_val)) if dir_val is not None else ""

                fecha_str = str(fecha_temp) if fecha_temp else "Reciente"
                es_valido = (temp_f is not None or viento_f is not None or pres_f is not None or pp_f is not None)
                estado_txt = "OPERATIVA" if es_valido else "SIN DATOS VÁLIDOS"

                return es_valido, estado_txt, fecha_str, temp, pres, viento, dir_viento, racha, precipitacion

            return False, "DATOS NO VÁLIDOS", "Estructura desconocida", "--", "--", "--", "", "--", "--"

    except Exception as e:
        print(f"Error IFOP [{est['nombre']}]: {e}")
        return False, "SIN CONEXIÓN", str(e)[:30], "--", "--", "--", "", "--", "--"


def generar_html(estaciones_resultados, markers_js):
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="30">
    <title>Monitor de Estaciones Automáticas</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        :root {{
            --bg-color: #f4f6f9;
            --text-color: #1e293b;
            --h1-color: #0f2942;
            --card-bg-ok: linear-gradient(135deg, #dbeafe 0%, #cbd5e1 55%, #94a3b8 100%);
            --card-border-ok: #94a3b8;
            --card-bg-error: linear-gradient(135deg, #fee2e2 0%, #fecaca 55%, #f87171 100%);
            --card-border-error: #f87171;
            --item-bg: rgba(255, 255, 255, 0.9);
            --item-text: #0f172a;
            --summary-bg: #ffffff;
            --summary-border: #cbd5e1;
            --summary-text: #0f2942;
        }}

        [data-theme="dark"] {{
            --bg-color: #0b0f19;
            --text-color: #f8fafc;
            --h1-color: #38bdf8;
            --card-bg-ok: linear-gradient(135deg, #1e293b 0%, #0f172a 55%, #020617 100%);
            --card-border-ok: #334155;
            --card-bg-error: linear-gradient(135deg, #450a0a 0%, #291515 55%, #1a0505 100%);
            --card-border-error: #7f1d1d;
            --item-bg: rgba(15, 23, 42, 0.85);
            --item-text: #f8fafc;
            --summary-bg: #1e293b;
            --summary-border: #334155;
            --summary-text: #38bdf8;
        }}

        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: var(--bg-color); color: var(--text-color); padding: 15px; margin: 0; transition: background-color 0.4s ease, color 0.4s ease; }}
        h1 {{ text-align: center; color: var(--h1-color); margin-bottom: 0; font-size: 22px; line-height: 1.2; font-weight: 700; }}
        .subtitle-line2 {{ text-align: center; color: #1e40af; margin-bottom: 6px; font-size: 16px; font-weight: bold; }}
        [data-theme="dark"] .subtitle-line2 {{ color: #60a5fa; }}
        .subtitle {{ text-align: center; color: #64748b; margin-bottom: 12px; font-size: 12px; }}
        [data-theme="dark"] .subtitle {{ color: #94a3b8; }}
        
        .summary {{ text-align: center; font-weight: bold; margin-bottom: 15px; color: var(--summary-text); font-size: 14px; background: var(--summary-bg); padding: 6px 16px; border-radius: 20px; max-width: 280px; margin-left: auto; margin-right: auto; box-shadow: 0 2px 6px rgba(0,0,0,0.06); border: 1px solid var(--summary-border); }}
        
        @keyframes parpadeoFondo {{ 
            0% {{ background-color: var(--bg-color); }} 
            50% {{ background-color: #fca5a5; }} 
            100% {{ background-color: var(--bg-color); }} 
        }}
        body.alerta-activa {{ animation: parpadeoFondo 1.5s infinite; }}

        .banner-alerta {{ background: linear-gradient(135deg, #ef4444, #dc2626); color: white; text-align: center; font-weight: bold; padding: 10px; border-radius: 8px; margin-bottom: 15px; font-size: 14px; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3); }}
        #map {{ height: 350px; width: 100%; max-width: 1200px; margin: 0 auto 20px auto; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); border: 1px solid var(--summary-border); }}
        
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
            background: var(--card-bg-ok); 
            border: 1px solid var(--card-border-ok);
            border-left: 6px solid #16a34a; 
        }}
        .card.error {{ 
            background: var(--card-bg-error); 
            border: 1px solid var(--card-border-error);
            border-left: 6px solid #dc2626; 
        }}
        .card:hover {{ 
            transform: translateY(-3px); 
            box-shadow: 0 8px 20px rgba(30, 64, 175, 0.2); 
        }}
        
        .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 4px; }}
        .station-name {{ font-weight: bold; font-size: 13.5px; color: var(--item-text); line-height: 1.1; }}
        .status-badge {{ font-size: 11px; }}
        
        .card-body-content {{
            display: flex;
            flex-direction: column;
            gap: 4px;
            margin: 4px 0;
        }}
        .row-top, .row-bottom {{
            display: grid;
            gap: 4px;
        }}
        .row-top {{
            grid-template-columns: 1.1fr 1fr 1fr;
        }}
        .row-bottom {{
            grid-template-columns: 1fr 1fr;
        }}
        
        .item-box {{
            background: var(--item-bg);
            padding: 4px 2px;
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            text-align: center;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            white-space: nowrap;
            color: var(--item-text);
        }}
        .temp-box {{
            font-size: 0.85em;
            font-weight: 800;
            color: var(--item-text);
        }}
        
        .card-footer-info {{ display: flex; justify-content: space-between; align-items: center; margin-top: 2px; border-top: 1px solid rgba(150, 150, 150, 0.3); padding-top: 3px; }}
        .time {{ font-size: 0.68em; color: var(--text-color); opacity: 0.8; }}
        .click-text {{ font-size: 0.68em; color: #38bdf8; font-weight: bold; font-style: italic; }}
        
        /* Botón Flotante de Modo Nocturno */
        .theme-toggle-btn {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: linear-gradient(135deg, #0f2942, #1e3a8a);
            color: white;
            border: none;
            border-radius: 50px;
            padding: 10px 18px;
            font-size: 13px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            z-index: 9999;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: transform 0.2s ease;
        }}
        .theme-toggle-btn:hover {{
            transform: scale(1.05);
        }}

        .footer-dev {{ background: linear-gradient(135deg, #0f2942, #1e3a8a); color: #f8fafc; text-align: center; font-weight: 600; padding: 10px 24px; border-radius: 30px; margin: 30px auto 15px auto; display: table; font-size: 13px; box-shadow: 0 4px 12px rgba(15, 41, 66, 0.2); border: 1px solid rgba(255,255,255,0.15); }}
    </style>
</head>
<body>
    <h1>MONITOR DE ESTACIONES METEOROLÓGICAS AUTOMÁTICAS</h1>
    <div class="subtitle-line2">Red de Observación de Superficie</div>
    <div class="subtitle">Actualización automática cada 30 segundos</div>
    
    <div class="summary">
        Estaciones Operativas: {sum(1 for e in estaciones_resultados if e[0])} / {len(estaciones_resultados)}
    </div>

    <div id="map"></div>

    <div class="grid">
"""
    # Aquí iría el bucle que dibuja cada tarjeta en tu script original...
    # (Se mantiene exactamente igual al que ya usas para generar las tarjetas)

    html += f"""
    </div>

    <button class="theme-toggle-btn" onclick="toggleTheme()" id="themeBtn">
        🌙 Modo Noche
    </button>

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

        // Lógica de Modo Oscuro / Claro
        function toggleTheme() {{
            const htmlElement = document.documentElement;
            const btn = document.getElementById('themeBtn');
            if (htmlElement.getAttribute('data-theme') === 'dark') {{
                htmlElement.removeAttribute('data-theme');
                localStorage.setItem('theme', 'light');
                btn.innerHTML = '🌙 Modo Noche';
            }} else {{
                htmlElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
                btn.innerHTML = '☀️ Modo Día';
            }}
        }}

        // Cargar preferencia guardada al iniciar
        window.addEventListener('DOMContentLoaded', () => {{
            const savedTheme = localStorage.getItem('theme');
            const btn = document.getElementById('themeBtn');
            if (savedTheme === 'dark') {{
                document.documentElement.setAttribute('data-theme', 'dark');
                btn.innerHTML = '☀️ Modo Día';
            }}
        }});
    </script>
</body>
</html>
"""
    return html
