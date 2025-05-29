# Filename: extract_gopro_telemetry_plus_gpx.py
import os
import subprocess
import json

def extract_telemetry_and_gpx(root_folder, exiftool_executable="exiftool", gpx_format_file="gpx.fmt"):
    """
    Scans a root folder for .MP4 files, extracts telemetry to JSON using ExifTool,
    and also generates a GPX file using ExifTool with a format file.

    Args:
        root_folder (str): The path to the folder to scan.
        exiftool_executable (str): The path to the ExifTool executable.
        gpx_format_file (str): Path to the gpx.fmt file for ExifTool.
    """
    print(f"Starting telemetry extraction and GPX generation from: {root_folder}")
    files_processed_json = 0
    files_processed_gpx = 0
    files_found = 0

    if not os.path.basename(gpx_format_file) == gpx_format_file: # if it's a path
        if not os.path.exists(gpx_format_file):
            print(f"WARNING: GPX format file '{gpx_format_file}' not found. GPX generation may fail if it's not in ExifTool's path or current directory.")
    else:
        if not os.path.exists(gpx_format_file):
             print(f"INFO: '{gpx_format_file}' not found in script directory. Assuming ExifTool can find it elsewhere (e.g., its own directory or current working directory of execution).")


    for foldername, _, filenames in os.walk(root_folder):
        for filename in filenames:
            if filename.lower().endswith(".mp4"):
                files_found += 1
                mp4_filepath = os.path.join(foldername, filename)
                base_filename = os.path.splitext(filename)[0]

                # --- JSON Telemetry Extraction ---
                output_json_filepath = os.path.join(foldername, f"{base_filename}_telemetry.json")
                cmd_json = [
                    exiftool_executable,
                    "-ee",
                    "-n",
                    "-b",
                    "-G1",
                    "-x", "SourceFile",
                    "-x", "System:Directory",
                    "-json",
                    mp4_filepath
                ]

                print(f"\nProcessing for JSON: {mp4_filepath}...")
                try:
                    result_json = subprocess.run(cmd_json, capture_output=True, text=True, check=True, encoding='utf-8')
                    try:
                        metadata_list = json.loads(result_json.stdout)
                        if metadata_list and isinstance(metadata_list, list) and len(metadata_list) > 0:
                            with open(output_json_filepath, 'w', encoding='utf-8') as f_json:
                                json.dump(metadata_list[0], f_json, indent=4)
                            print(f"  SUCCESS: JSON telemetry saved to {output_json_filepath}")
                            files_processed_json += 1
                        else:
                            print(f"  WARNING: No valid metadata structure in ExifTool JSON output for {mp4_filepath}")
                    except json.JSONDecodeError:
                        print(f"  ERROR: Could not decode JSON from ExifTool for {mp4_filepath}")
                except subprocess.CalledProcessError as _:
                    print(f"  ERROR: ExifTool failed (JSON extraction) for {mp4_filepath}.")
                    # print(f"  Stderr: {e.stderr[:200]}...") # Uncomment for more error details
                except FileNotFoundError:
                    print(f"CRITICAL ERROR: ExifTool executable not found at '{exiftool_executable}'.")
                    return

                # --- GPX File Generation ---
                output_gpx_filepath = os.path.join(foldername, f"{base_filename}")

                expected_gpx_output_path = f"{output_gpx_filepath}.gpx"

                cmd_gpx = [
                    "gopro2gpx",
                    "--gpx",
                    "-s",              # Para skip bad points
                    mp4_filepath,
                    output_gpx_filepath
                ]

                print(f"Processing for GPX/CSV with gopro2gpx: {mp4_filepath}...")
                try:

                    result_gpx = subprocess.run(cmd_gpx, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')

                    # Verificamos si el archivo GPX fue creado
                    if os.path.exists(expected_gpx_output_path):
                        print(f"  SUCCESS: GPX file saved to {expected_gpx_output_path}")
                        files_processed_gpx += 1
                    else:
                        print(f"  WARNING: gopro2gpx ran but GPX file not found at {expected_gpx_output_path}.")
                        if result_gpx.stdout:
                            print(f"  gopro2gpx stdout: {result_gpx.stdout[:500]}")
                        if result_gpx.stderr:
                            print(f"  gopro2gpx stderr: {result_gpx.stderr[:500]}")

                except subprocess.CalledProcessError as e:
                    print(f"  ERROR: gopro2gpx failed for {mp4_filepath}.")
                    print(f"  Return code: {e.returncode}")
                    print(f"  Stdout: {e.stdout[:500] if e.stdout else 'None'}")
                    print(f"  Stderr: {e.stderr[:500] if e.stderr else 'None'}")
                except FileNotFoundError:
                    print("CRITICAL ERROR: gopro2gpx command not found. Is it installed and in your PATH?")
                    return
                except Exception as e_gpx:
                    print(f"  An unexpected error occurred during gopro2gpx execution for {mp4_filepath}: {e_gpx}")


    print("\n--- Summary ---")
    print(f"Found {files_found} MP4 files.")
    print(f"Successfully generated {files_processed_json} JSON telemetry files.")
    print(f"Successfully generated {files_processed_gpx} GPX files.")
    print("Extraction complete.")

if __name__ == "__main__":
    # --- CONFIGURATION ---
    target_gopro_folder = "/Volumes/LaCie/GoPro"
    exiftool_path = "exiftool"

    gpx_format_filepath = "gpx.fmt"
    # --- END CONFIGURATION ---

    if not os.path.exists(gpx_format_filepath) and gpx_format_filepath == "gpx.fmt":
        print(f"ADVERTENCIA: El archivo '{gpx_format_filepath}' no se encontró en el directorio actual.")
        print(f"Asegúrate de que '{gpx_format_filepath}' esté en el mismo directorio que este script,")
        print("o en el directorio desde donde ejecutas el script, o proporciona la ruta completa a 'gpx_format_filepath'.")
        print("ExifTool también podría encontrarlo si está en su propio directorio de fmt_files y lo llamas adecuadamente.")
        # You might want to add a more robust check or make the user confirm to continue

    extract_telemetry_and_gpx(target_gopro_folder,
                                exiftool_executable=exiftool_path,
                                gpx_format_file=gpx_format_filepath)
