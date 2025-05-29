# Filename: animar_gpx_matplotlib_sincronizado.py
import gpxpy
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import timedelta

def animar_ruta_gpx_sincronizada(ruta_archivo_gpx,
                                 archivo_salida_video="ruta_animada_sincro.mp4",
                                 intervalo_frames_ms=100,
                                 puntos_gpx_por_frame_anim=1,
                                 segundos_inicio_dibujo=0):
    """
    Lee un archivo GPX y crea una animación sincronizada.
    La animación dura el total del track, pero el dibujo de la ruta
    puede empezar después de 'segundos_inicio_dibujo'.

    Args:
        ruta_archivo_gpx (str): Ruta al archivo GPX.
        archivo_salida_video (str): Nombre del archivo de video de salida.
        intervalo_frames_ms (int): Milisegundos entre frames de la animación.
        puntos_gpx_por_frame_anim (int): Cuántos puntos GPX reales corresponden a un frame de animación.
        segundos_inicio_dibujo (int): Segundos desde el inicio del track GPX antes de empezar a dibujar la ruta.
    """
    try:
        print(f"Leyendo archivo GPX: {ruta_archivo_gpx}")
        with open(ruta_archivo_gpx, 'r', encoding='utf-8') as gpx_file_content:
            gpx = gpxpy.parse(gpx_file_content)

        if not gpx.tracks or not gpx.tracks[0].segments:
            print("No se encontraron tracks/segmentos.")
            return

        all_points_raw = [] # Lista de (lon, lat, time)
        for segment in gpx.tracks[0].segments:
            for point in segment.points:
                if point.time and point.longitude is not None and point.latitude is not None:
                    all_points_raw.append((point.longitude, point.latitude, point.time))

        if not all_points_raw:
            print("No se encontraron puntos con datos válidos (lon, lat, time) en el GPX.")
            return
        print(f"Total de puntos GPX leídos: {len(all_points_raw)}")

        # Determinar el tiempo de inicio real del track y el tiempo para empezar a dibujar
        tiempo_primer_punto_gpx = all_points_raw[0][2]
        tiempo_para_empezar_a_dibujar = tiempo_primer_punto_gpx + timedelta(seconds=segundos_inicio_dibujo)

        if segundos_inicio_dibujo > 0:
            print(f"La animación comenzará a dibujar la ruta a partir de: {tiempo_para_empezar_a_dibujar} ({segundos_inicio_dibujo}s después del inicio del GPX).")
        else:
            print("La animación dibujará la ruta desde el inicio del GPX.")

        # Encontrar el índice del primer punto que se dibujará
        idx_primer_punto_a_dibujar = 0
        for i, p_data in enumerate(all_points_raw):
            if p_data[2] >= tiempo_para_empezar_a_dibujar:
                idx_primer_punto_a_dibujar = i
                break
        else: # Si todos los puntos son antes del tiempo_para_empezar_a_dibujar (ej. segundos_inicio_dibujo es muy grande)
            if segundos_inicio_dibujo > 0 :
                 print("ADVERTENCIA: Todos los puntos están antes del tiempo de inicio de dibujo especificado. Se dibujará una animación en blanco o solo el último estado.")
                 # Podríamos optar por no dibujar nada o dibujar el último punto si la duración del skip es mayor que la del track
                 idx_primer_punto_a_dibujar = len(all_points_raw) # No dibujará nada


        # Puntos que realmente se usarán para establecer los límites del mapa
        puntos_visibles_para_limites = all_points_raw[idx_primer_punto_a_dibujar:]

        fig, ax = plt.subplots(figsize=(10, 8))

        if puntos_visibles_para_limites:
            longitudes_visibles = [p[0] for p in puntos_visibles_para_limites]
            latitudes_visibles = [p[1] for p in puntos_visibles_para_limites]
            margin_lon = (max(longitudes_visibles) - min(longitudes_visibles)) * 0.05 if len(longitudes_visibles) > 1 and max(longitudes_visibles) != min(longitudes_visibles) else 0.01
            margin_lat = (max(latitudes_visibles) - min(latitudes_visibles)) * 0.05 if len(latitudes_visibles) > 1 and max(latitudes_visibles) != min(latitudes_visibles) else 0.01
            ax.set_xlim(min(longitudes_visibles) - margin_lon, max(longitudes_visibles) + margin_lon)
            ax.set_ylim(min(latitudes_visibles) - margin_lat, max(latitudes_visibles) + margin_lat)
        else: # Si no hay puntos visibles, establecer límites por defecto o basados en todos los puntos crudos
            print("No hay puntos visibles para establecer límites del mapa; usando límites basados en todos los datos si existen.")
            if all_points_raw:
                all_lons = [p[0] for p in all_points_raw]
                all_lats = [p[1] for p in all_points_raw]
                ax.set_xlim(min(all_lons) - 0.01, max(all_lons) + 0.01)
                ax.set_ylim(min(all_lats) - 0.01, max(all_lats) + 0.01)


        ax.set_xlabel("Longitud")
        ax.set_ylabel("Latitud")
        ax.set_title(f"Ruta (Dibujo inicia tras {segundos_inicio_dibujo}s)")
        ax.set_aspect('equal', adjustable='box')
        ax.grid(True)

        line, = ax.plot([], [], lw=2, color='dodgerblue', alpha=0.8)
        current_point_marker, = ax.plot([], [], 'o', color='red', markersize=5)

        # El número total de frames de animación se basa en TODOS los puntos GPX
        num_total_frames_animacion = (len(all_points_raw) + puntos_gpx_por_frame_anim - 1) // puntos_gpx_por_frame_anim

        def init_animation():
            line.set_data([], [])
            current_point_marker.set_data([],[])
            return line, current_point_marker

        def update_animation(frame_idx_anim): # Este es el índice del frame de la animación
            # Determinar el índice del último punto GPX a considerar para este frame de animación
            idx_ultimo_gpx_a_considerar = min( (frame_idx_anim + 1) * puntos_gpx_por_frame_anim -1 , len(all_points_raw) - 1)

            punto_gpx_actual_data = all_points_raw[idx_ultimo_gpx_a_considerar]
            tiempo_punto_gpx_actual = punto_gpx_actual_data[2]

            lon_actual_marcador = punto_gpx_actual_data[0]
            lat_actual_marcador = punto_gpx_actual_data[1]

            if tiempo_punto_gpx_actual >= tiempo_para_empezar_a_dibujar:
                # Recopilar puntos para la línea desde el inicio del dibujo hasta el punto actual
                puntos_linea_lons = []
                puntos_linea_lats = []
                # Iteramos desde el primer punto que se debe dibujar hasta el punto actual de esta iteración
                for i in range(idx_primer_punto_a_dibujar, idx_ultimo_gpx_a_considerar + 1):
                    puntos_linea_lons.append(all_points_raw[i][0])
                    puntos_linea_lats.append(all_points_raw[i][1])

                line.set_data(puntos_linea_lons, puntos_linea_lats)
                current_point_marker.set_data([lon_actual_marcador], [lat_actual_marcador])
                current_point_marker.set_alpha(1) # Hacer visible el marcador
            else:
                # Antes del tiempo de inicio de dibujo, no dibujamos la línea
                line.set_data([], [])
                # Y el marcador puede estar oculto o en el primer punto general
                current_point_marker.set_data([lon_actual_marcador], [lat_actual_marcador]) # Mostrar dónde estamos "esperando"
                current_point_marker.set_alpha(0.3) # Hacerlo tenue o invisible
                # o current_point_marker.set_data([],[]) # para ocultarlo completamente

            if frame_idx_anim % (num_total_frames_animacion // 20 + 1) == 0 :
                 print(f"  Procesando frame de animación: {frame_idx_anim+1}/{num_total_frames_animacion} (Corresponde a punto GPX ~{idx_ultimo_gpx_a_considerar+1})")
            return line, current_point_marker

        if num_total_frames_animacion == 0:
            print("No hay frames para animar.")
            plt.close(fig)
            return

        print(f"Creando animación con {num_total_frames_animacion} frames totales (basado en todos los puntos GPX)...")
        ani = animation.FuncAnimation(fig, update_animation, frames=num_total_frames_animacion,
                                      init_func=init_animation, blit=True,
                                      interval=intervalo_frames_ms, repeat=False)
        try:
            fps_video = max(1, 1000 / intervalo_frames_ms)
            print(f"Guardando animación en {archivo_salida_video} con {fps_video:.2f} FPS...")
            ani.save(archivo_salida_video, fps=fps_video, progress_callback=lambda cf, tf: print(f"  Guardando frame {cf+1}/{tf}...") if cf % (tf // 10 + 1) == 0 else None)
            print(f"¡Animación guardada exitosamente en {archivo_salida_video}!")
        except Exception as e:
            print(f"Error guardando la animación: {e}")
            print("Asegúrate de tener FFmpeg instalado y en el PATH.")
        finally:
            plt.close(fig)

    except FileNotFoundError:
        print(f"Error: No se encontró el archivo GPX en la ruta: {ruta_archivo_gpx}")
    except Exception as e:
        print(f"Ocurrió un error general: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    mi_archivo_gpx = "/Users//Desktop/tests/9/GH010005_joined.gpx.gpx" #
    nombre_video_salida = "/Users//Desktop/tests/9/mi_animacion_gpx_sincronizada.mp4"

    intervalo_ms = 50
    puntos_gpx_por_frame = 5
    segundos_para_empezar_dibujo = 0

    animar_ruta_gpx_sincronizada(mi_archivo_gpx,
                                    archivo_salida_video=nombre_video_salida,
                                    intervalo_frames_ms=intervalo_ms,
                                    puntos_gpx_por_frame_anim=puntos_gpx_por_frame,
                                    segundos_inicio_dibujo=segundos_para_empezar_dibujo)
