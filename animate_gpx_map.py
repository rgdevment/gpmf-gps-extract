import gpxpy
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import timedelta
import contextily as cx
from pyproj import Transformer
import numpy as np
import os

# Variable para almacenar la última altura mostrada y forzar la primera actualización
# Usamos una lista para que sea mutable y modificable dentro de update_animation
# Se reiniciará al principio de cada llamada a animar_ruta_gpx_sincronizada
_local_ultima_elevacion_mostrada_texto = [None]

def animar_ruta_gpx_sincronizada(ruta_archivo_gpx,
                                 archivo_salida_video="ruta_animada_mapa_refinado.mp4",
                                 intervalo_frames_ms_referencia=50,
                                 puntos_gpx_por_frame_anim=1,
                                 segundos_inicio_dibujo=0,
                                 map_source=cx.providers.OpenStreetMap.Mapnik,
                                 ventana_promedio_altura_puntos=5,
                                 umbral_actualizacion_altura_m=0.5,
                                 grosor_linea=4,
                                 tamano_punto=10
                                 ):
    global _local_ultima_elevacion_mostrada_texto
    _local_ultima_elevacion_mostrada_texto[0] = None

    try:
        print(f"Leyendo archivo GPX: {ruta_archivo_gpx}")
        with open(ruta_archivo_gpx, 'r', encoding='utf-8') as gpx_file_content:
            gpx = gpxpy.parse(gpx_file_content)

        if not gpx.tracks or not gpx.tracks[0].segments:
            print(f"No se encontraron tracks/segmentos en {ruta_archivo_gpx}.")
            return False

        all_points_raw_latlon = []
        for segment in gpx.tracks[0].segments:
            for point in segment.points:
                if point.time and point.longitude is not None and point.latitude is not None:
                    all_points_raw_latlon.append((point.longitude, point.latitude, point.time, point.elevation))

        if not all_points_raw_latlon:
            print(f"No se encontraron puntos con datos válidos en {ruta_archivo_gpx}.")
            return False

        print(f"Total de puntos GPX leídos de {os.path.basename(ruta_archivo_gpx)}: {len(all_points_raw_latlon)}")

        transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
        all_points_projected = []
        for lon, lat, time, ele in all_points_raw_latlon:
            x, y = transformer.transform(lon, lat)
            all_points_projected.append((x, y, time, ele))

        _all_points_data_for_animation = all_points_projected

        if not _all_points_data_for_animation: # Chequeo adicional por si la transformación falla o filtra todo
            print(f"No quedaron puntos después de la proyección para {ruta_archivo_gpx}.")
            return False

        tiempo_primer_punto_gpx = _all_points_data_for_animation[0][2]
        tiempo_ultimo_punto_gpx = _all_points_data_for_animation[-1][2]
        tiempo_para_empezar_a_dibujar = tiempo_primer_punto_gpx + timedelta(seconds=segundos_inicio_dibujo)

        idx_primer_punto_a_dibujar = 0
        for i, p_data in enumerate(_all_points_data_for_animation):
            if p_data[2] >= tiempo_para_empezar_a_dibujar:
                idx_primer_punto_a_dibujar = i
                break
        else:
            if segundos_inicio_dibujo > 0 and len(_all_points_data_for_animation) > 0 :
                 print("ADVERTENCIA: Todos los puntos están antes del tiempo de inicio de dibujo especificado.")
                 idx_primer_punto_a_dibujar = len(_all_points_data_for_animation)
            elif len(_all_points_data_for_animation) == 0:
                 print("No hay puntos para dibujar.")
                 return False


        fig, ax = plt.subplots(figsize=(10, 8))
        fig.subplots_adjust(left=0, right=1, bottom=0, top=1, wspace=0, hspace=0)

        puntos_visibles_proyectados_para_limites = _all_points_data_for_animation[idx_primer_punto_a_dibujar:]

        if puntos_visibles_proyectados_para_limites:
            coords_x_visibles = [p[0] for p in puntos_visibles_proyectados_para_limites]
            coords_y_visibles = [p[1] for p in puntos_visibles_proyectados_para_limites]
            min_x, max_x = min(coords_x_visibles), max(coords_x_visibles)
            min_y, max_y = min(coords_y_visibles), max(coords_y_visibles)
            margin_x = (max_x - min_x) * 0.05 if max_x != min_x else 100
            margin_y = (max_y - min_y) * 0.05 if max_y != min_y else 100
            ax.set_xlim(min_x - margin_x, max_x + margin_x)
            ax.set_ylim(min_y - margin_y, max_y + margin_y)
        elif _all_points_data_for_animation:
            all_x = [p[0] for p in _all_points_data_for_animation]
            all_y = [p[1] for p in _all_points_data_for_animation]
            ax.set_xlim(min(all_x) - 100, max(all_x) + 100)
            ax.set_ylim(min(all_y) - 100, max(all_y) + 100)
        else:
            print("No hay datos para establecer límites del mapa.")
            plt.close(fig)
            return False


        print(f"Añadiendo mapa base usando: {map_source} para {os.path.basename(ruta_archivo_gpx)}")
        try:
            cx.add_basemap(ax, crs="EPSG:3857", source=map_source, zoom='auto')
        except Exception as e:
            print(f"Error al añadir el mapa base para {os.path.basename(ruta_archivo_gpx)}: {e}")

        ax.set_axis_off()

        line, = ax.plot([], [], lw=grosor_linea, color='dodgerblue', alpha=0.8, zorder=5)
        current_point_marker, = ax.plot([], [], 'o', color='red', markersize=tamano_punto, markeredgecolor='white', zorder=6)

        elevation_text = ax.text(0.02, 0.98, '', transform=ax.transAxes, fontsize=10,
                                 color='black', verticalalignment='top',
                                 bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7), zorder=7)

        num_total_frames_animacion = (len(_all_points_data_for_animation) + puntos_gpx_por_frame_anim - 1) // puntos_gpx_por_frame_anim

        if num_total_frames_animacion == 0:
            print(f"No hay frames para animar en {os.path.basename(ruta_archivo_gpx)}.")
            plt.close(fig)
            return False

        intervalo_ms_final_animacion = intervalo_frames_ms_referencia
        fps_video_final = max(1, 1000 / intervalo_ms_final_animacion)

        if len(_all_points_data_for_animation) > 1:
            duracion_real_gpx_timedelta = tiempo_ultimo_punto_gpx - tiempo_primer_punto_gpx
            duracion_real_gpx_s = duracion_real_gpx_timedelta.total_seconds()
            print(f"Duración real del track GPX ({os.path.basename(ruta_archivo_gpx)}): {duracion_real_gpx_timedelta} ({duracion_real_gpx_s:.2f} segundos).")

            if duracion_real_gpx_s > 0 and num_total_frames_animacion > 0:
                intervalo_ms_calculado = (duracion_real_gpx_s * 1000.0) / num_total_frames_animacion
                min_intervalo_ms = 20 # Minimum interval in ms (equivalent to 50 FPS)
                if intervalo_ms_calculado < min_intervalo_ms:
                    print(f"ADVERTENCIA (archivo: {os.path.basename(ruta_archivo_gpx)}): Intervalo ({intervalo_ms_calculado:.2f} ms) muy bajo. Usando {min_intervalo_ms} ms.")
                    intervalo_ms_final_animacion = min_intervalo_ms
                else:
                    intervalo_ms_final_animacion = intervalo_ms_calculado
                fps_video_final = 1000.0 / intervalo_ms_final_animacion
                print(f"Para sincronizar ({os.path.basename(ruta_archivo_gpx)}): {num_total_frames_animacion} frames, intervalo: {intervalo_ms_final_animacion:.2f} ms, FPS: {fps_video_final:.2f}.")
            elif duracion_real_gpx_s <= 0:
                 print(f"Duración GPX cero o negativa ({os.path.basename(ruta_archivo_gpx)}). Usando intervalo de referencia.")
        elif len(_all_points_data_for_animation) == 1:
             print(f"Solo 1 punto en GPX ({os.path.basename(ruta_archivo_gpx)}). Usando intervalo de referencia.")

        def init_animation_batch():
            global _local_ultima_elevacion_mostrada_texto
            line.set_data([], [])
            current_point_marker.set_data([],[])
            elevation_text.set_text('')
            _local_ultima_elevacion_mostrada_texto[0] = None
            return line, current_point_marker, elevation_text

        def update_animation_batch(frame_idx_anim):
            global _local_ultima_elevacion_mostrada_texto
            idx_ultimo_gpx_a_considerar = min( (frame_idx_anim + 1) * puntos_gpx_por_frame_anim -1 , len(_all_points_data_for_animation) - 1)

            punto_gpx_actual_data = _all_points_data_for_animation[idx_ultimo_gpx_a_considerar]
            tiempo_punto_gpx_actual = punto_gpx_actual_data[2]
            x_actual_marcador = punto_gpx_actual_data[0]
            y_actual_marcador = punto_gpx_actual_data[1]

            idx_inicio_ventana = max(0, idx_ultimo_gpx_a_considerar - ventana_promedio_altura_puntos + 1)
            elevaciones_ventana = []
            for i in range(idx_inicio_ventana, idx_ultimo_gpx_a_considerar + 1):
                ele = _all_points_data_for_animation[i][3]
                if ele is not None:
                    elevaciones_ventana.append(ele)

            elevacion_suavizada_actual = None
            if elevaciones_ventana:
                elevacion_suavizada_actual = np.mean(elevaciones_ventana)

            actualizar_texto_altura = False
            if elevacion_suavizada_actual is not None:
                if _local_ultima_elevacion_mostrada_texto[0] is None or \
                   abs(elevacion_suavizada_actual - _local_ultima_elevacion_mostrada_texto[0]) >= umbral_actualizacion_altura_m:
                    actualizar_texto_altura = True
            elif _local_ultima_elevacion_mostrada_texto[0] is not None: # Si antes había altura y ahora no, actualizar a N/A
                 actualizar_texto_altura = True

            if actualizar_texto_altura:
                if elevacion_suavizada_actual is not None:
                    elevation_text.set_text(f'Altura: {elevacion_suavizada_actual:.1f} m')
                    _local_ultima_elevacion_mostrada_texto[0] = elevacion_suavizada_actual
                else:
                    elevation_text.set_text('Altura: N/A')
                    _local_ultima_elevacion_mostrada_texto[0] = None # Resetear para futura comparación

            if tiempo_punto_gpx_actual >= tiempo_para_empezar_a_dibujar:
                puntos_linea_x = []
                puntos_linea_y = []
                # Asegurarse de que idx_primer_punto_a_dibujar no sea mayor que idx_ultimo_gpx_a_considerar
                for i in range(idx_primer_punto_a_dibujar, idx_ultimo_gpx_a_considerar + 1):
                    puntos_linea_x.append(_all_points_data_for_animation[i][0])
                    puntos_linea_y.append(_all_points_data_for_animation[i][1])
                line.set_data(puntos_linea_x, puntos_linea_y)
                current_point_marker.set_data([x_actual_marcador], [y_actual_marcador])
                current_point_marker.set_alpha(1) # Visible
            else: # Puntos antes del inicio del dibujo
                line.set_data([], []) # No dibujar línea aún
                current_point_marker.set_data([x_actual_marcador], [y_actual_marcador]) # Mostrar el punto
                current_point_marker.set_alpha(0.3) # Pero hacerlo semitransparente

            # Progress printing
            if num_total_frames_animacion > 0 and frame_idx_anim % max(1, (num_total_frames_animacion // 20)) == 0 : # Print progress roughly 20 times
                 print(f"  Procesando frame ({os.path.basename(ruta_archivo_gpx)}): {frame_idx_anim+1}/{num_total_frames_animacion}")

            return line, current_point_marker, elevation_text

        print(f"Creando animación para {os.path.basename(ruta_archivo_gpx)} con {num_total_frames_animacion} frames totales...")
        ani = animation.FuncAnimation(fig, update_animation_batch, frames=num_total_frames_animacion,
                                      init_func=init_animation_batch, blit=True, # blit=True para optimizar
                                      interval=intervalo_ms_final_animacion, # Intervalo entre frames en milisegundos
                                      repeat=False) # No repetir la animación
        try:
            print(f"Guardando animación en {archivo_salida_video} con {fps_video_final:.2f} FPS...")
            # Usar un writer que soporte transparencia si es necesario, ej. ffmpeg con codec adecuado
            ani.save(
                archivo_salida_video,
                fps=fps_video_final,
                savefig_kwargs={ # Argumentos para guardar cada frame
                    'transparent': True, # Fondo transparente si el formato de video lo soporta
                    'facecolor': 'none', # Sin color de fondo para la figura
                },
                progress_callback=lambda cf, tf: print(f"  Guardando frame ({os.path.basename(ruta_archivo_gpx)}) {cf+1}/{tf}...") if tf > 0 and cf % max(1, (tf // 10)) == 0 else None # Print progress roughly 10 times
            )
            print(f"¡Animación guardada exitosamente en {archivo_salida_video}!")
            if num_total_frames_animacion > 0 and fps_video_final > 0:
                duracion_video_esperada_s = num_total_frames_animacion / fps_video_final
                print(f"Duración esperada del video ({os.path.basename(ruta_archivo_gpx)}): {duracion_video_esperada_s:.2f} segundos.")
            return True # Indicar éxito
        except Exception as e:
            print(f"Error guardando la animación para {os.path.basename(ruta_archivo_gpx)}: {e}")
        finally:
            plt.close(fig) # Asegurarse de cerrar la figura para liberar memoria

    except FileNotFoundError:
        print(f"Error: No se encontró el archivo GPX en la ruta: {ruta_archivo_gpx}")
    except Exception as e:
        print(f"Ocurrió un error general procesando {ruta_archivo_gpx}: {e}")
        import traceback
        traceback.print_exc() # Imprime el stack trace completo para depuración

    return False # Indicar fallo

def procesar_directorio_gpx(directorio_raiz,
                            intervalo_ref, puntos_frame, seg_inicio, map_src,
                            ventana_altura, umbral_altura,
                            # NUEVOS PARÁMETROS para pasar a la función de animación
                            grosor_linea_lote, tamano_punto_lote
                            ):
    """
    Escanea un directorio y sus subdirectorios en busca de archivos .gpx,
    y los procesa para generar videos de telemetría.
    """
    archivos_gpx_encontrados = 0
    archivos_procesados_ok = 0
    archivos_con_fallo = 0

    print(f"Iniciando escaneo de GPX en el directorio: {directorio_raiz}")
    for dirpath, dirnames, filenames in os.walk(directorio_raiz):
        for filename in filenames:
            if filename.lower().endswith(".gpx"):
                archivos_gpx_encontrados += 1
                ruta_completa_gpx = os.path.join(dirpath, filename)

                # Crear nombre de video de salida en la misma carpeta que el GPX
                nombre_base_gpx = os.path.splitext(filename)[0]
                nombre_video_salida = f"{nombre_base_gpx}-gps.mp4" # Puedes cambiar el sufijo si quieres
                ruta_completa_video = os.path.join(dirpath, nombre_video_salida)

                print("\n====================================================================")
                print(f"==> Procesando archivo GPX: {ruta_completa_gpx}")
                print(f"    Video de salida: {ruta_completa_video}")
                print("====================================================================")

                if animar_ruta_gpx_sincronizada(
                        ruta_archivo_gpx=ruta_completa_gpx,
                        archivo_salida_video=ruta_completa_video,
                        intervalo_frames_ms_referencia=intervalo_ref,
                        puntos_gpx_por_frame_anim=puntos_frame,
                        segundos_inicio_dibujo=seg_inicio,
                        map_source=map_src,
                        ventana_promedio_altura_puntos=ventana_altura,
                        umbral_actualizacion_altura_m=umbral_altura,
                        grosor_linea=grosor_linea_lote,
                        tamano_punto=tamano_punto_lote
                    ):
                    archivos_procesados_ok +=1
                else:
                    archivos_con_fallo +=1

                print("--------------------------------------------------------------------\n")


    print("\n======= RESUMEN DEL PROCESAMIENTO POR LOTES =======")
    print(f"Directorio escaneado: {directorio_raiz}")
    print(f"Total de archivos GPX encontrados: {archivos_gpx_encontrados}")
    print(f"Archivos procesados exitosamente: {archivos_procesados_ok}")
    print(f"Archivos con fallo durante el procesamiento: {archivos_con_fallo}")
    print("===================================================")


if __name__ == "__main__":

    directorio_raiz_a_procesar = "/Volumes/LaCie/GoPro"

    intervalo_referencia_ms_lote = 50
    puntos_gpx_por_frame_lote = 5
    segundos_para_empezar_dibujo_lote = 0
    # map_provider_lote = cx.providers.CartoDB.Positron
    map_provider_lote = cx.providers.OpenStreetMap.Mapnik
    # map_provider_lote = cx.providers.Esri.WorldImagery # Satelital

    # Parámetros para el suavizado y actualización de la altura
    ventana_puntos_altura_lote = 10     # Número de puntos GPX para promediar la altura
    umbral_cambio_altura_lote = 25.0
    grosor_linea_principal_lote = 12     # Grosor de la línea de la ruta (ej: 4 o 5)
    tamano_punto_actual_lote = 16       # Tamaño del marcador del punto actual (ej: 10 o 12)

    # --- Fin de la Configuración ---

    if not os.path.isdir(directorio_raiz_a_procesar):
        print(f"Error: El directorio especificado '{directorio_raiz_a_procesar}' no existe o no es un directorio.")
        print("Por favor, verifica la ruta en la variable 'directorio_raiz_a_procesar' dentro del script.")
    else:
        procesar_directorio_gpx(
            directorio_raiz_a_procesar,
            intervalo_ref=intervalo_referencia_ms_lote,
            puntos_frame=puntos_gpx_por_frame_lote,
            seg_inicio=segundos_para_empezar_dibujo_lote,
            map_src=map_provider_lote,
            ventana_altura=ventana_puntos_altura_lote,
            umbral_altura=umbral_cambio_altura_lote,
            grosor_linea_lote=grosor_linea_principal_lote,
            tamano_punto_lote=tamano_punto_actual_lote
        )
