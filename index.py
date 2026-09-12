def consultar_directemar(est):
  try:
    req = urllib.request.Request(est["url"], headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
      html = response.read().decode("utf-8", errors="ignore")

      temp, hum, viento = "--", "--", "--"

      # Limpieza estándar para fecha y textos generales
      texto_plano = re.sub(r"<[^>]+>", " ", html)
      texto_plano = (
          texto_plano.replace("\xa5", " ")
          .replace("\xa0", " ")
          .replace("&nbsp;", " ")
      )
      texto_plano = re.sub(r"\s+", " ", texto_plano).strip()

      # Búsqueda específica en HTML tabular para Temperatura
      # Busca patrones comunes en las celdas de Directemar (etiqueta seguida de celda con valor o texto cercano)
      temp_match = re.search(
          r"(?:Temperatura|Temp\.?)[^<\d]*([\-]?\d+(?:[.,]\d+)?)",
          texto_plano,
          re.IGNORECASE,
      )
      if not temp_match:
        # Búsqueda general de respaldos si la etiqueta exacta varía
        temp_match = re.search(
            r"([\-]?\d+(?:[.,]\d+)?)\s*[°º]\s*C", html, re.IGNORECASE
        )
      if not temp_match:
        temp_match = re.search(
            r"\b([1-3]\d(?:[.,]\d+)?)\s*°", texto_plano, re.IGNORECASE
        )

      if temp_match:
        val = convertir_numero(temp_match.group(1))
        if val is not None and -10 < val < 45:  # Filtro lógico de temperatura
          temp = f"{val:.1f}°C"

      # Humedad
      hum_match = re.search(
          r"(?:Humidity|Humedad)[^<\d]*(\d+(?:[.,]\d+)?)\s*%",
          texto_plano,
          re.IGNORECASE,
      )
      if not hum_match:
        hum_match = re.search(
            r"(\d+(?:[.,]\d+)?)\s*%", texto_plano, re.IGNORECASE
        )

      if hum_match:
        val = convertir_numero(hum_match.group(1))
        if val is not None and 0 <= val <= 100:
          hum = f"{val:.1f}%"

      # Viento promedio (evitando rachas)
      partes_viento = re.split(r"racha|gust", texto_plano, flags=re.IGNORECASE)
      viento_match = re.search(
          r"(?:Viento|Wind)[^<\d]*(\d+(?:[.,]\d+)?)\s*(?:kts|kt)",
          partes_viento[0],
          re.IGNORECASE,
      )
      if not viento_match:
        viento_match = re.search(
            r"(\d+(?:[.,]\d+)?)\s*(?:kts|kt)", partes_viento[0], re.IGNORECASE
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
