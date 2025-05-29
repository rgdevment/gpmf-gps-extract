# GPMF Extractor: Extrae GPS desde Videos GoPro (Compatible con ReelSteady)

Este script de Python te permite extraer datos de telemetría GPS (específicamente el stream `GPS5`) desde archivos de vídeo `.mp4` generados por cámaras GoPro. Funciona incluso si los vídeos han sido unidos previamente usando **ReelSteady Joiner**, preservando la integridad de los metadatos.

El script genera archivos `.csv` y `.gpx` por cada vídeo procesado, conteniendo los puntos GPS. Estos archivos son ideales para importar en software de edición de vídeo como DaVinci Resolve (para telemetría en pantalla), visualizar en mapas, crear dashboards personalizados o para cualquier otro análisis de datos geoespaciales.

Utiliza `ExifTool` para la extracción inicial de metadatos en JSON y `gopro2gpx` (que a su vez usa `ffmpeg`) para la generación de los archivos CSV y GPX.

---

## ✨ Características Principales

* Extracción de datos GPS (`GPS5`) de vídeos GoPro.
* Compatibilidad con archivos `.mp4` unidos mediante ReelSteady Joiner.
* Generación de archivos `.csv` (valores separados por comas) con los datos GPS.
* Generación de archivos `.gpx` (formato de intercambio GPS estándar) para fácil importación.
* Procesamiento por lotes de todos los vídeos `.mp4` dentro de una carpeta raíz y sus subcarpetas.

---

## ✅ Requisitos Previos

Asegúrate de tener los siguientes componentes instalados en tu sistema:

### 1. Python
* **Versión:** 3.8 o superior.
* **Librerías Estándar Utilizadas por este Script:** El script principal (`extract_gps_gpmf.py`) utiliza módulos que vienen con Python por defecto, como `os`, `subprocess`, `json`, `pathlib`, `datetime`, `csv`, y `xml.etree.ElementTree`. No necesitas instalar nada adicional vía `pip` para estas librerías estándar.
    * *(Nota: Si tu script `extract_gps_gpmf.py` llegara a usar librerías externas, deberías listarlas aquí y proporcionar un archivo `requirements.txt` para él).*

### 2. Herramientas Externas del Sistema

Estas herramientas deben estar instaladas y accesibles desde la línea de comandos (en tu PATH).

* **FFmpeg (y FFprobe):** Necesario para `gopro2gpx`.
    * **macOS (usando Homebrew):**
        ```bash
        brew install ffmpeg
        ```
    * **Linux (Debian/Ubuntu):**
        ```bash
        sudo apt update && sudo apt install ffmpeg
        ```
    * **Windows:** Descarga desde [ffmpeg.org](https://ffmpeg.org/download.html) y añade la carpeta `bin` a tu PATH.
    * **Verificación:**
        ```bash
        ffmpeg -version
        ffprobe -version
        ```

* **ExifTool:** Necesario para la extracción de metadatos JSON.
    * **macOS (usando Homebrew):**
        ```bash
        brew install exiftool
        ```
    * **Linux (Debian/Ubuntu):**
        ```bash
        sudo apt update && sudo apt install libimage-exiftool-perl
        ```
    * **Windows:** Descarga desde [exiftool.org](https://exiftool.org/install.html#Windows) (la versión ejecutable de Windows).
    * **Verificación:**
        ```bash
        exiftool -ver
        ```

### 3. `gopro2gpx` (Como dependencia de este proyecto)

Este proyecto utiliza la herramienta `gopro2gpx` de `juanmcasillas` para procesar los datos GPMD y generar los archivos GPX/CSV. Para que tu script `extract_gps_gpmf.py` pueda llamarlo, te recomendamos instalarlo dentro del entorno virtual de este proyecto:

1.  **Clona el repositorio de `gopro2gpx`** (puedes hacerlo en una subcarpeta `deps` dentro de tu proyecto GPMF Extractor, o en cualquier otro lugar accesible):
    ```bash
    git clone [https://github.com/juanmcasillas/gopro2gpx.git](https://github.com/juanmcasillas/gopro2gpx.git) ruta/deseada/para/gopro2gpx_source
    ```

2.  **Configura el Entorno Virtual para GPMF Extractor (este proyecto):**
    Si aún no lo has hecho, crea y activa un entorno virtual en la carpeta raíz de *este* proyecto (`GPMF Extractor`):
    ```bash
    cd ruta/a/tu/proyecto/GPMF_Extractor
    python3 -m venv .venv
    source .venv/bin/activate  # En macOS/Linux
    pip install -r requirements.txt
    ```

3.  **Instala `gopro2gpx` en el Entorno Virtual Activo:**
    Con el entorno virtual de *tu proyecto GPMF Extractor activado*, navega a la carpeta donde clonaste `gopro2gpx` y usa `pip` para instalarlo. Esto también instalará sus dependencias Python (definidas en su `setup.py`) dentro de tu `.venv`.
    ```bash
    cd ruta/deseada/para/gopro2gpx_source
    pip3 install .
    cd - # Vuelve a tu directorio anterior
    ```
    Esto hará que el comando `gopro2gpx` esté disponible cuando el `.venv` de tu proyecto GPMF Extractor esté activo.

### 4. ReelSteady Joiner (Opcional)

Si necesitas unir varios archivos `.mp4` de GoPro (por ejemplo, capítulos de una grabación larga) sin perder la telemetría GPMD, te recomendamos usar **ReelSteady Joiner**. Esto es crucial para que la telemetría del vídeo unido sea coherente.
* Puedes encontrarlo aquí: [rubegartor/ReelSteady-Joiner](https://github.com/rubegartor/ReelSteady-Joiner)

---

## 🏁 Uso del Script

1.  **Prepara tus Vídeos:**
    Coloca los vídeos `.mp4` (ya sean originales de la GoPro o unidos con ReelSteady Joiner) en una carpeta. El script explorará esta carpeta y todas sus subcarpetas. Ejemplo de estructura:
    ```
    /ruta/a/tus/videos_gopro/
    ├── ViajeAlaska/
    │   ├── GH010001_joined.mp4
    │   └── GH010002.MP4
    └── SalidaLocal/
        └── GH010003_joined.mp4
    ```

2.  **Configura el Script (Recomendado: Usar Argumentos de Línea de Comandos):**
    En lugar de editar el script directamente, te recomiendo modificar `extract_gps_gpmf.py` para que acepte la carpeta raíz como un argumento de línea de comandos. Aquí un ejemplo de cómo podrías hacerlo usando `argparse`:

    ```python
    # Dentro de extract_gps_gpmf.py (ejemplo de cómo añadir argparse)
    import argparse
    from pathlib import Path

    if __name__ == "__main__":
        parser = argparse.ArgumentParser(description="Extrae telemetría GPS de vídeos GoPro.")
        parser.add_argument("root_dir", type=str, help="Carpeta raíz que contiene los vídeos MP4.")
        # Podrías añadir más argumentos, como para el sufijo de los archivos de salida
        # parser.add_argument("--output_suffix", type=str, default="_gps_data", help="Sufijo para los archivos GPX/CSV generados.")
        args = parser.parse_args()

        root_path = Path(args.root_dir)
        # output_suffix = args.output_suffix

        # Llama a tu función principal de extracción aquí, pasando root_path
        # ej: extract_all_telemetry(root_path, output_suffix=output_suffix)
        # ... (tu lógica de script) ...
    ```
    Si no implementas argumentos, entonces sí tendrías que editar la variable `root_dir` dentro del script como indicabas:
    ```python
    # En extract_gps_gpmf.py
    root_dir = Path("/ruta/a/tus/videos_gopro")
    # output_suffix = "_gps_data" # Define si quieres un sufijo
    ```

3.  **Ejecuta el Script:**
    Asegúrate de que tu entorno virtual (donde instalaste `gopro2gpx`) esté activo:
    ```bash
    source .venv/bin/activate # O el comando equivalente para tu SO
    ```
    Luego, ejecuta el script:
    * Si implementaste `argparse`:
        ```bash
        python3 extract_gps_gpmf.py "/ruta/a/tus/videos_gopro"
        # O con sufijo:
        # python3 extract_gps_gpmf.py "/ruta/a/tus/videos_gopro" --output_suffix _mi_telemetria
        ```
    * Si no, y editaste `root_dir` en el script:
        ```bash
        python3 extract_gps_gpmf.py
        ```

4.  **Archivos Generados:**
    Por cada archivo `.mp4` procesado, encontrarás un archivo `.csv` y un archivo `.gpx` en la misma carpeta que el vídeo original.
    * Si tu script `extract_gps_gpmf.py` usa el `base_filename` como prefijo para `gopro2gpx` (como discutimos), los nombres serían:
        ```
        GH010001_joined.csv
        GH010001_joined.gpx
        ```
    * Si estás añadiendo un sufijo (como `_gps_data` que tenías en tu ejemplo), asegúrate de que tu script lo implemente al llamar a `gopro2gpx` (modificando el `output_file_prefix`) o renombrando los archivos después. Por ejemplo, si el prefijo es `os.path.join(foldername, f"{base_filename}{output_suffix}")`, entonces los archivos se llamarían:
        ```
        GH010001_joined_gps_data.csv
        GH010001_joined_gps_data.gpx
        ```

---

## 📄 Descripción de los Archivos de Salida

* **Archivo `.csv`:**
    Contiene los datos GPS en un formato tabular simple, fácil de importar en hojas de cálculo o para análisis con scripts. Las columnas típicas generadas por `gopro2gpx` son: `latitude`, `longitude`, `elevation`, `time`, `hr`, `name`, `cadence`, `speed`, `distance`, `power`, `temperature`. *(Nota: `hr`, `cadence`, `power`, y `temperature` podrían aparecer con valor `0` si los datos no están presentes o no son capturados por defecto por `gopro2gpx`)*.

* **Archivo `.gpx`:**
    Un archivo XML estándar para datos GPS. Contiene un track (`<trk>`) con múltiples puntos de track (`<trkpt>`), cada uno con latitud, longitud, elevación y tiempo. `gopro2gpx` también puede incluir extensiones (como `gpxtpx:TrackPointExtension`) para datos adicionales como velocidad, frecuencia cardíaca, etc., aunque estos también podrían ser cero si no están disponibles.

---

## 🔧 Solución de Problemas (Troubleshooting)

* **`ffmpeg` / `ffprobe` / `exiftool` / `gopro2gpx` no encontrado:** Asegúrate de que estas herramientas estén correctamente instaladas y que sus ubicaciones estén en la variable de entorno `PATH` de tu sistema, o que `gopro2gpx` esté instalado en el entorno virtual activo.
* **Errores de Permiso al ejecutar `gopro2gpx`:** Si llamas a `gopro2gpx.py` directamente, asegúrate de hacerlo con `python3 gopro2gpx.py ...`. Si usas el comando `gopro2gpx` después de instalarlo con `pip install .` en tu venv, no deberías tener problemas de permisos.
* **No se generan archivos de salida:** Verifica los mensajes en la consola. `gopro2gpx` y `exiftool` suelen dar información si no encuentran datos de telemetría en el vídeo. Asegúrate de que los vídeos de entrada realmente contengan metadatos GPMD.

