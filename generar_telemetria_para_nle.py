import gpxpy
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import timedelta
import numpy as np
import os

_local_ultima_elevacion_mostrada_texto = [None]

def animar_ruta_gpx_para_composicion(
    ruta_archivo_gpx,
    archivo_salida_video="telemetria_ruta.mp4",
    # --- Parámetros de apariencia y salida de la telemetría ---
    resolucion_telemetria_wh=(1280, 720),
    dpi_telemetria=100,
    color_fondo_chroma='lime', # Verde brillante para chroma key. Prueba 'blue' si hay mucho verde en tu ruta.
    color_ruta='white', # Color que resalte sobre el fondo chroma
    grosor_ruta=2.5,
    color_marcador='yellow', # Color que resalte
    tamano_marcador=8,
    color_borde_marcador='black',
    color_texto_altura='white',
    color_fondo_texto_altura='black',
    opacidad_fondo_texto_altura=0.6,
    tamano_fuente_altura=10,
    # --- Parámetros de animación y GPX ---
    intervalo_frames_ms_referencia=33, # Para ~30 FPS si no se sincroniza duración
    puntos_gpx_por_frame_anim=1,
    segundos_inicio_dibujo=0,
    ventana_promedio_altura_puntos=5, # Puntos GPX para el promedio móvil de altura
    umbral_actualizacion_altura_m=0.5 # Metros de cambio para actualizar texto de altura
    ):
    """
    Genera un video de telemetría (ruta GPX animada) sobre un fondo de color sólido
    (para chroma key), destinado a ser usado en un software de edición de video (NLE).
    La duración del video se sincroniza con la duración del track GPX.
    """
    global _local_ultima_elevacion_mostrada_texto
    _local_ultima_elevacion_mostrada_texto[0] = None # Reiniciar para esta animación

    try:
        print(f"Leyendo archivo GPX: {ruta_archivo_gpx}")
        with open(ruta_archivo_gpx, 'r', encoding='utf-8') as gpx_file_content:
            gpx = gpxpy.parse(gpx_file_content)

        if not gpx.tracks or not gpx.tracks[0].segments:
            print(f"No se encontraron tracks/segmentos en {ruta_archivo_gpx}.")
            return False

        all_points_data = []
        for segment in gpx.tracks[0].segments:
            for point in segment.points:
                if point.time and point.longitude is not None and point.latitude is not None:
                    all_points_data.append((point.longitude, point.latitude, point.time, point.elevation))

        if not all_points_data:
            print(f"No se encontraron puntos con datos válidos en {ruta_archivo_gpx}.")
            return False

        print(f"Total de puntos GPX leídos de {os.path.basename(ruta_archivo_gpx)}: {len(all_points_data)}")

        tiempo_primer_punto_gpx = all_points_data[0][2]
        tiempo_ultimo_punto_gpx = all_points_data[-1][2]
        tiempo_para_empezar_a_dibujar = tiempo_primer_punto_gpx + timedelta(seconds=segundos_inicio_dibujo)

        idx_primer_punto_a_dibujar = 0
        for i, p_data in enumerate(all_points_data):
            if p_data[2] >= tiempo_para_empezar_a_dibujar:
                idx_primer_punto_a_dibujar = i
                break
        else:
            if segundos_inicio_dibujo > 0 and len(all_points_data) > 0:
                 print("ADVERTENCIA: Todos los puntos están antes del tiempo de inicio de dibujo especificado.")
                 idx_primer_punto_a_dibujar = len(all_points_data) # No dibujará la línea
            elif len(all_points_data) == 0:
                 print("No hay puntos para dibujar.")
                 return False

        ancho_fig_pulgadas = resolucion_telemetria_wh[0] / dpi_telemetria
        alto_fig_pulgadas = resolucion_telemetria_wh[1] / dpi_telemetria

        fig, ax = plt.subplots(figsize=(ancho_fig_pulgadas, alto_fig_pulgadas), dpi=dpi_telemetria)
        fig.subplots_adjust(left=0, right=1, bottom=0, top=1, wspace=0, hspace=0)

        ax.set_facecolor(color_fondo_chroma)
        fig.patch.set_facecolor(color_fondo_chroma)
        ax.set_axis_off()

        puntos_para_limites = all_points_data[idx_primer_punto_a_dibujar:] if idx_primer_punto_a_dibujar < len(all_points_data) else all_points_data

        if puntos_para_limites:
            longitudes = [p[0] for p in puntos_para_limites]
            latitudes = [p[1] for p in puntos_para_limites]

            min_lon, max_lon = min(longitudes), max(longitudes)
            min_lat, max_lat = min(latitudes), max(latitudes)

            delta_lon = max_lon - min_lon
            delta_lat = max_lat - min_lat

            if delta_lon == 0: delta_lon = 0.0002 * resolucion_telemetria_wh[0]/resolucion_telemetria_wh[1] # Pequeño
            if delta_lat == 0: delta_lat = 0.0002

            margin_factor = 0.1 # 10% de margen
            ax.set_xlim(min_lon - delta_lon * margin_factor, max_lon + delta_lon * margin_factor)
            ax.set_ylim(min_lat - delta_lat * margin_factor, max_lat + delta_lat * margin_factor)
            ax.set_aspect('equal', adjustable='box')
        else:
            print("No hay puntos para establecer límites del gráfico. Usando límites por defecto.")
            ax.set_xlim(0,1)
            ax.set_ylim(0,1)


        line, = ax.plot([], [], lw=grosor_ruta, color=color_ruta, solid_capstyle='round')
        current_point_marker, = ax.plot([], [], 'o',
                                        color=color_marcador,
                                        markersize=tamano_marcador,
                                        markeredgecolor=color_borde_marcador,
                                        markeredgewidth=1)
        elevation_text = ax.text(0.03, 0.97, '', transform=ax.transAxes, fontsize=tamano_fuente_altura,
                                 color=color_texto_altura, verticalalignment='top', horizontalalignment='left',
                                 bbox=dict(boxstyle='round,pad=0.3', fc=color_fondo_texto_altura, alpha=opacidad_fondo_texto_altura))

        num_total_frames_animacion = (len(all_points_data) + puntos_gpx_por_frame_anim - 1) // puntos_gpx_por_frame_anim

        if num_total_frames_animacion == 0:
            print(f"No hay frames para animar en {os.path.basename(ruta_archivo_gpx)}.")
            plt.close(fig)
            return False

        # --- Sincronización de Duración ---
        intervalo_ms_final_animacion = intervalo_frames_ms_referencia
        fps_video_final = max(1.0, 1000.0 / intervalo_ms_final_animacion)

        if len(all_points_data) > 1:
            duracion_real_gpx_timedelta = tiempo_ultimo_punto_gpx - tiempo_primer_punto_gpx
            duracion_real_gpx_s = duracion_real_gpx_timedelta.total_seconds()

            if duracion_real_gpx_s > 0.001 and num_total_frames_animacion > 0: # Evitar división por cero o FPS muy altos
                intervalo_ms_calculado = (duracion_real_gpx_s * 1000.0) / num_total_frames_animacion
                # Limitar FPS máximo (ej. 120 FPS -> ~8ms) y mínimo (ej. 10 FPS -> 100ms)
                min_allowable_interval_ms = 8
                max_allowable_interval_ms = 100

                if intervalo_ms_calculado < min_allowable_interval_ms:
                    print(f"ADVERTENCIA ({os.path.basename(ruta_archivo_gpx)}): Intervalo {intervalo_ms_calculado:.2f}ms muy bajo (FPS muy alto). Usando {min_allowable_interval_ms}ms.")
                    intervalo_ms_final_animacion = min_allowable_interval_ms
                elif intervalo_ms_calculado > max_allowable_interval_ms:
                    print(f"ADVERTENCIA ({os.path.basename(ruta_archivo_gpx)}): Intervalo {intervalo_ms_calculado:.2f}ms muy alto (FPS muy bajo). Usando {max_allowable_interval_ms}ms.")
                    intervalo_ms_final_animacion = max_allowable_interval_ms
                else:
                    intervalo_ms_final_animacion = intervalo_ms_calculado

                fps_video_final = 1000.0 / intervalo_ms_final_animacion
                print(f"Telemetría ({os.path.basename(ruta_archivo_gpx)}): {num_total_frames_animacion} frames, Duración GPX: {duracion_real_gpx_s:.2f}s, Intervalo: {intervalo_ms_final_animacion:.2f}ms, FPS: {fps_video_final:.2f}.")
            elif duracion_real_gpx_s <= 0.001:
                 print(f"Duración GPX muy corta o cero ({os.path.basename(ruta_archivo_gpx)}). Usando intervalo de referencia: {intervalo_frames_ms_referencia}ms.")
        else: # Menos de 2 puntos
             print(f"Menos de 2 puntos en GPX ({os.path.basename(ruta_archivo_gpx)}). Usando intervalo de referencia: {intervalo_frames_ms_referencia}ms.")


        def init_anim():
            global _local_ultima_elevacion_mostrada_texto
            line.set_data([], [])
            current_point_marker.set_data([],[])
            elevation_text.set_text('')
            _local_ultima_elevacion_mostrada_texto[0] = None
            return line, current_point_marker, elevation_text

        def update_anim(frame_idx_anim):
            global _local_ultima_elevacion_mostrada_texto
            idx_gpx_actual = min((frame_idx_anim + 1) * puntos_gpx_por_frame_anim - 1, len(all_points_data) - 1)

            current_gpx_data = all_points_data[idx_gpx_actual]
            tiempo_actual_gpx = current_gpx_data[2]
            lon_marcador = current_gpx_data[0]
            lat_marcador = current_gpx_data[1]

            # Suavizado de altura
            idx_ventana_inicio = max(0, idx_gpx_actual - ventana_promedio_altura_puntos + 1)
            elevaciones_en_ventana = [p[3] for p in all_points_data[idx_ventana_inicio : idx_gpx_actual + 1] if p[3] is not None]

            alt_suavizada = np.mean(elevaciones_en_ventana) if elevaciones_en_ventana else None

            if alt_suavizada is not None:
                if _local_ultima_elevacion_mostrada_texto[0] is None or \
                   abs(alt_suavizada - _local_ultima_elevacion_mostrada_texto[0]) >= umbral_actualizacion_altura_m:
                    elevation_text.set_text(f'Altura: {alt_suavizada:.1f} m')
                    _local_ultima_elevacion_mostrada_texto[0] = alt_suavizada
            elif _local_ultima_elevacion_mostrada_texto[0] is not None: # Si antes había valor y ahora no
                elevation_text.set_text('Altura: N/A')
                _local_ultima_elevacion_mostrada_texto[0] = None

            # Dibujar línea y marcador
            if tiempo_actual_gpx >= tiempo_para_empezar_a_dibujar:
                lons_linea = [p[0] for p in all_points_data[idx_primer_punto_a_dibujar : idx_gpx_actual + 1]]
                lats_linea = [p[1] for p in all_points_data[idx_primer_punto_a_dibujar : idx_gpx_actual + 1]]
                line.set_data(lons_linea, lats_linea)
                current_point_marker.set_data([lon_marcador], [lat_marcador])
                current_point_marker.set_alpha(1)
            else: # Antes del tiempo de inicio de dibujo
                line.set_data([], [])
                current_point_marker.set_data([lon_marcador], [lat_marcador]) # Mostrar el punto "esperando"
                current_point_marker.set_alpha(0.4) # Atenuado

            if frame_idx_anim % max(1, (num_total_frames_animacion // 10)) == 0 : # Progreso más frecuente
                 print(f"  Procesando frame ({os.path.basename(ruta_archivo_gpx)}): {frame_idx_anim+1}/{num_total_frames_animacion}")

            return line, current_point_marker, elevation_text

        print(f"Creando animación ({resolucion_telemetria_wh[0]}x{resolucion_telemetria_wh[1]}) para {os.path.basename(ruta_archivo_gpx)}...")
        ani = animation.FuncAnimation(fig, update_anim,
                                      frames=num_total_frames_animacion,
                                      init_func=init_anim, blit=True,
                                      interval=intervalo_ms_final_animacion,
                                      repeat=False)
        try:
            print(f"Guardando telemetría en {archivo_salida_video} (H.264, {fps_video_final:.2f} FPS)...")
            ani.save(
                archivo_salida_video,
                writer='ffmpeg',
                fps=fps_video_final,
                codec='libx264',
                extra_args=['-crf', '23', '-preset', 'medium', '-pix_fmt', 'yuv420p'],
                savefig_kwargs={'facecolor': fig.get_facecolor(), 'pad_inches': 0, 'bbox_inches':'tight'}
            )
            print(f"Telemetría guardada: {archivo_salida_video}")
            return True
        except Exception as e:
            print(f"Error guardando telemetría para {os.path.basename(ruta_archivo_gpx)}: {e}")
            print("  Asegúrate que FFmpeg esté instalado y en el PATH.")
        finally:
            plt.close(fig)

    except FileNotFoundError:
        print(f"Error: No se encontró el archivo GPX: {ruta_archivo_gpx}")
    except Exception as e:
        print(f"Ocurrió un error general procesando {ruta_archivo_gpx}: {e}")
        import traceback
        traceback.print_exc()
    return False


def procesar_directorio_gpx_para_nle(directorio_raiz, params_animacion):
    """
    Escanea un directorio en busca de archivos .gpx y genera videos de telemetría
    para cada uno, usando los parámetros de animación dados.
    """
    archivos_gpx_encontrados = 0
    archivos_procesados_ok = 0
    archivos_con_fallo = 0

    print(f"Iniciando escaneo de GPX en: {directorio_raiz}")
    for dirpath, _, filenames in os.walk(directorio_raiz):
        for filename in filenames:
            if filename.lower().endswith(".gpx"):
                archivos_gpx_encontrados += 1
                ruta_completa_gpx = os.path.join(dirpath, filename)

                nombre_base_gpx = os.path.splitext(filename)[0]
                nombre_video_telemetria = f"{nombre_base_gpx}-telemetry.mp4"
                ruta_video_telemetria_salida = os.path.join(dirpath, nombre_video_telemetria)

                print("\n====================================================================")
                print(f"==> Procesando GPX: {ruta_completa_gpx}")
                print(f"    Salida de telemetría: {ruta_video_telemetria_salida}")
                print("====================================================================")

                if animar_ruta_gpx_para_composicion(
                        ruta_archivo_gpx=ruta_completa_gpx,
                        archivo_salida_video=ruta_video_telemetria_salida,
                        **params_animacion # Desempaquetar diccionario de parámetros
                    ):
                    archivos_procesados_ok +=1
                else:
                    archivos_con_fallo +=1
                print("--------------------------------------------------------------------\n")

    print("\n======= RESUMEN DEL PROCESAMIENTO DE TELEMETRÍA =======")
    print(f"Directorio escaneado: {directorio_raiz}")
    print(f"Total de archivos GPX encontrados: {archivos_gpx_encontrados}")
    print(f"Videos de telemetría generados exitosamente: {archivos_procesados_ok}")
    print(f"Archivos con fallo durante la generación: {archivos_con_fallo}")
    print("===================================================")


if __name__ == "__main__":

    directorio_raiz_a_procesar = "/ruta/a/tu/carpeta/con/gpx"

    # --- Parámetros para la generación de los videos de telemetría ---
    parametros_telemetria = {
        "resolucion_telemetria_wh": (1280, 720), # 720p
        "dpi_telemetria": 100,
        "color_fondo_chroma": 'lime', # Verde para chroma key
        "color_ruta": 'white',
        "grosor_ruta": 3, # Un poco más grueso para visibilidad
        "color_marcador": 'yellow',
        "tamano_marcador": 9,
        "color_borde_marcador": 'black',
        "color_texto_altura": 'white',
        "color_fondo_texto_altura": 'black',
        "opacidad_fondo_texto_altura": 0.6,
        "tamano_fuente_altura": 12, # Un poco más grande para 720p
        "intervalo_frames_ms_referencia": 33, # Apunta a ~30 FPS si la sincronización falla
        "puntos_gpx_por_frame_anim": 1, # Más suave si es 1
        "segundos_inicio_dibujo": 0,
        "ventana_promedio_altura_puntos": 10, # Promedio sobre más puntos para suavizar
        "umbral_actualizacion_altura_m": 0.5
    }

    if not os.path.isdir(directorio_raiz_a_procesar):
        print(f"Error: El directorio especificado '{directorio_raiz_a_procesar}' no existe o no es un directorio.")
        print("Por favor, verifica la ruta en la variable 'directorio_raiz_a_procesar'.")
    elif directorio_raiz_a_procesar == "/ruta/a/tu/carpeta/con/gpx": # Placeholder check
        print("Error: Debes cambiar 'directorio_raiz_a_procesar' en el script a la ruta real de tu carpeta con archivos GPX.")
    else:
        procesar_directorio_gpx_para_nle(
            directorio_raiz_a_procesar,
            parametros_telemetria
        )
