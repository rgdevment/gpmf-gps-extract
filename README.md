# GPMF Extractor: Extrae GPS desde videos GoPro (con ReelSteady)

Este script te permite extraer datos de telemetría GPS (`GPS5`) desde archivos `.mp4` generados por GoPro, incluso si han sido unidos usando **ReelSteady Joiner**.

Genera archivos `.csv` y `.gpx` con los puntos GPS, listos para ser usados en DaVinci Resolve, mapas, dashboards o overlays personalizados.

---

## ✅ Requisitos

### 1. Python 3.8 o superior
Con los siguientes módulos estándar:
- `struct`
- `csv`
- `xml.etree.ElementTree`
- `datetime`
- `subprocess`
- `pathlib`
- `json`

### 2. `ffmpeg` y `ffprobe`

Instálalos usando Homebrew en macOS:
```bash
brew install ffmpeg
```

Verifica que ambos estén accesibles:
```bash
which ffmpeg
which ffprobe
```

### 3. ReelSteady Joiner (opcional)

Si necesitas unir varios `.mp4` grabados por la GoPro sin perder la telemetría, usa:
- [https://github.com/rubegartor/ReelSteady-Joiner](https://github.com/rubegartor/ReelSteady-Joiner)

Esto asegura que los metadatos `gpmd` se mantengan en el `.mp4` final unido.

---

## 🏁 Uso

1. Coloca los videos `.mp4` (originales o unidos con ReelSteady) en una carpeta:

```
/Volumes/LaCie/GoPro/
└── Ride1/
    ├── GH010001_joined.mp4
    ├── GH010002_joined.mp4
    └── GH010003.MP4
```

2. Edita en el script `extract_gps_gpmf.py` la variable:
```python
root_dir = Path("/Volumes/LaCie/GoPro")
```

3. Ejecuta:
```bash
python3 extract_gps_gpmf.py
```

4. Obtendrás archivos `.csv` y `.gpx` al lado de cada `.mp4`:
```
GH010001_joined_gps_data.csv
GH010001_joined_gps_data.gpx
```

---

## 🧠 Notas técnicas

- El script detecta automáticamente el índice del stream `gpmd` mediante `ffprobe`, por lo que funciona con `.mp4` normales o unidos.
- El parser es heurístico y busca bloques de 5 `floats` que representen `[lat, lon, alt, speed, fix]`.
- No depende del software de GoPro ni requiere GUI.

---

## 🛠 Ideas futuras

- Mejorar el parser para detectar con precisión `SCAL`, `TMPC`, etc.
- Sincronizar timestamps reales si están disponibles.
- Exportar a formatos adicionales: GeoJSON, KML, etc.
