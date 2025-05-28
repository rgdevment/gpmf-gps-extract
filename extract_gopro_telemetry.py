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

    # Check if gpx.fmt exists if a specific path is given, or assume it's findable by ExifTool
    if not os.path.basename(gpx_format_file) == gpx_format_file: # if it's a path
        if not os.path.exists(gpx_format_file):
            print(f"WARNING: GPX format file '{gpx_format_file}' not found. GPX generation may fail if it's not in ExifTool's path or current directory.")
    else:
        # If just "gpx.fmt", assume it's in the current dir or ExifTool will find it.
        # For robustness, you might want to ensure it's copied to CWD or provide full path.
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
                    "-G1",           # Mantenemos -G para ver los grupos
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
                output_gpx_filepath = os.path.join(foldername, f"{base_filename}.gpx")
                cmd_gpx = [
                    exiftool_executable,
                    "-p",
                    gpx_format_file, # Use the variable for the format file path
                    "-ee",
                    mp4_filepath
                ]

                print(f"Processing for GPX: {mp4_filepath}...")
                try:
                    # ExifTool with -p redirects its output to stdout, so we capture it.
                    result_gpx = subprocess.run(cmd_gpx, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')

                    if result_gpx.stdout.strip(): # Check if there's actual content
                        with open(output_gpx_filepath, 'w', encoding='utf-8') as f_gpx:
                            f_gpx.write(result_gpx.stdout)
                        print(f"  SUCCESS: GPX file saved to {output_gpx_filepath}")
                        files_processed_gpx += 1
                    else:
                        print(f"  WARNING: ExifTool produced empty GPX output for {mp4_filepath}. (Is GPS data present?)")

                except subprocess.CalledProcessError as e:
                    print(f"  ERROR: ExifTool failed (GPX generation) for {mp4_filepath}.")
                    # print(f"  Stderr: {e.stderr[:200]}...") # Uncomment for more error details
                except FileNotFoundError: # Should have been caught by JSON part
                    print(f"CRITICAL ERROR: ExifTool executable not found at '{exiftool_executable}'.")
                    return
                except Exception as e_gpx: # Catch any other unexpected errors during GPX part
                    print(f"  An unexpected error occurred during GPX generation for {mp4_filepath}: {e_gpx}")


    print("\n--- Summary ---")
    print(f"Found {files_found} MP4 files.")
    print(f"Successfully generated {files_processed_json} JSON telemetry files.")
    print(f"Successfully generated {files_processed_gpx} GPX files.")
    print("Extraction complete.")

if __name__ == "__main__":
    # --- CONFIGURATION ---
    target_gopro_folder = "/Users/mhidalgorg/Desktop/tests"
    exiftool_path = "exiftool"

    # Path to your gpx.fmt file.
    # If gpx.fmt is in the same directory as this Python script, you can just use "gpx.fmt".
    # Otherwise, provide the full path to gpx.fmt.
    # Ejemplo: "C:\\ruta\\a\\gpx.fmt" o "/home/usuario/scripts/gpx.fmt"
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
