import struct
import csv
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import subprocess
from pathlib import Path
import json

def parse_gps5_simplified(binary_data):
    gps_points = []
    block_size = 20  # 5 * 4 bytes (float)
    for i in range(0, len(binary_data) - block_size, 4):
        try:
            chunk = binary_data[i:i+block_size]
            lat, lon, alt, speed, _ = struct.unpack('>fffff', chunk)
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                gps_points.append((lat, lon, alt, speed))
        except struct.error:
            continue
    return gps_points

def save_csv(gps_data, output_csv):
    with open(output_csv, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Latitude', 'Longitude', 'Altitude', 'Speed'])
        for row in gps_data:
            writer.writerow(row)

def save_gpx(gps_data, output_gpx):
    gpx = ET.Element('gpx', version="1.1", creator="gpmf-extractor", xmlns="http://www.topografix.com/GPX/1/1")
    trk = ET.SubElement(gpx, 'trk')
    trkseg = ET.SubElement(trk, 'trkseg')

    for lat, lon, alt, _ in gps_data:
        trkpt = ET.SubElement(trkseg, 'trkpt', lat=str(lat), lon=str(lon))
        ele = ET.SubElement(trkpt, 'ele')
        ele.text = str(alt)
        time = ET.SubElement(trkpt, 'time')
        time.text = datetime.now(timezone.utc).isoformat()

    tree = ET.ElementTree(gpx)
    tree.write(output_gpx, encoding='utf-8', xml_declaration=True)

def find_gpmd_stream_index(video_path):
    cmd = ["ffprobe", "-v", "error", "-select_streams", "d", "-show_entries", "stream=index,codec_tag_string", "-of", "json", str(video_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, check=True, text=True)
        info = json.loads(result.stdout)
        for stream in info.get("streams", []):
            if stream.get("codec_tag_string") == "gpmd":
                return stream["index"]
    except Exception as e:
        print(f"ffprobe error en {video_path}: {e}")
    return None

def extract_gpmf_bin(video_path, output_bin):
    stream_index = find_gpmd_stream_index(video_path)
    if stream_index is None:
        print(f"No se encontró stream GPMD en {video_path}")
        return False

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-map", f"0:{stream_index}",
        "-c", "copy",
        "-f", "data",
        str(output_bin)
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        print(f"Error al extraer GPMF de {video_path}")
        return False

def process_video(video_path):
    parent_dir = video_path.parent
    stem = video_path.stem
    output_bin = parent_dir / f"{stem}_gpmf.bin"
    output_csv = parent_dir / f"{stem}_gps_data.csv"
    output_gpx = parent_dir / f"{stem}_gps_data.gpx"

    print(f"Procesando: {video_path}")

    if not extract_gpmf_bin(video_path, output_bin):
        return

    with open(output_bin, 'rb') as f:
        binary_data = f.read()

    gps_data = parse_gps5_simplified(binary_data)
    print(f"  → Puntos GPS encontrados: {len(gps_data)}")

    save_csv(gps_data, output_csv)
    save_gpx(gps_data, output_gpx)
    print(f"  → Archivos generados: {output_csv.name}, {output_gpx.name}\n")

def main():
    root_dir = Path("/Users/rgdevment/Desktop/tests")
    mp4_files = list(root_dir.rglob("*.mp4"))

    for video_path in mp4_files:
        process_video(video_path)

if __name__ == '__main__':
    main()
