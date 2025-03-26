import os
import json
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import numpy as np
from shapely.geometry import shape
from tqdm import tqdm
import sys
import random
import colorsys
import time
import multiprocessing
import concurrent.futures
from functools import partial

def cargar_geojson(archivo):
    """
    Carga un archivo GeoJSON y retorna sus datos.
    
    Args:
        archivo: Ruta al archivo GeoJSON
    
    Returns:
        Datos del GeoJSON o None si hay error
    """
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error al cargar el archivo {archivo}: {str(e)}")
        return None

def generar_colores_variados(color_base, num_variaciones):
    """
    Genera variaciones de un color base.
    
    Args:
        color_base: Color base en formato RGB (tupla de 3 valores entre 0 y 1)
        num_variaciones: Número de variaciones a generar
    
    Returns:
        Lista de colores variados en formato RGB
    """
    # Convertir RGB a HSV
    h, s, v = colorsys.rgb_to_hsv(*color_base)
    
    colores = []
    
    # Generar variaciones manteniendo el tono pero alterando saturación y valor
    for i in range(num_variaciones):
        # Variar saturación en un rango pequeño para mantener la tonalidad básica
        nueva_s = max(0.3, min(1.0, s + (random.random() * 0.4 - 0.2)))
        
        # Variar valor (brillo) pero evitando colores demasiado oscuros o claros
        nueva_v = max(0.5, min(0.9, v + (random.random() * 0.5 - 0.25)))
        
        # Convertir de vuelta a RGB
        nuevo_rgb = colorsys.hsv_to_rgb(h, nueva_s, nueva_v)
        colores.append(nuevo_rgb)
    
    return colores

def obtener_colores_comunidades():
    """
    Genera colores distintivos para cada comunidad autónoma.
    
    Returns:
        Diccionario con nombres de comunidades como claves y colores RGB como valores
    """
    # Lista de colores base distintivos en formato RGB (valores de 0 a 1)
    colores_base = [
        (0.8, 0.2, 0.2),  # Rojo
        (0.2, 0.7, 0.2),  # Verde
        (0.2, 0.2, 0.8),  # Azul
        (0.8, 0.8, 0.2),  # Amarillo
        (0.8, 0.2, 0.8),  # Magenta
        (0.2, 0.8, 0.8),  # Cian
        (0.6, 0.4, 0.2),  # Marrón
        (0.5, 0.3, 0.7),  # Púrpura
        (0.3, 0.5, 0.2),  # Verde oliva
        (0.8, 0.5, 0.2),  # Naranja
        (0.7, 0.2, 0.4),  # Granate
        (0.2, 0.5, 0.5),  # Turquesa
        (0.5, 0.5, 0.5),  # Gris
        (0.7, 0.4, 0.7),  # Lavanda
        (0.4, 0.7, 0.4),  # Verde menta
        (0.8, 0.6, 0.5),  # Salmón
        (0.5, 0.5, 0.8),  # Azul acero
        (0.3, 0.3, 0.3),  # Gris oscuro
        (0.9, 0.9, 0.5)   # Beige
    ]
    
    # Nombres de las comunidades autónomas
    comunidades = [
        "andalucia", "aragon", "principado_de_asturias", "islas_baleares", 
        "canarias", "cantabria", "castilla_y_leon", "castilla_la_mancha", 
        "cataluna_catalunya", "comunidad_valenciana", "extremadura", "galicia", 
        "comunidad_de_madrid", "region_de_murcia", "comunidad_foral_de_navarra", 
        "pais_vasco_euskadi", "la_rioja", "ciudad_autonoma_de_ceuta", 
        "ciudad_autonoma_de_melilla", "territorios_no_asociados_a_ninguna_autonomia"
    ]
    
    # Asignar colores a comunidades
    colores_comunidades = {}
    for i, comunidad in enumerate(comunidades):
        colores_comunidades[comunidad] = colores_base[i % len(colores_base)]
    
    return colores_comunidades

def procesar_feature(feature, i, color_variado, simplificacion=0.0001):
    """
    Procesa un feature y devuelve los datos para dibujar el polígono.
    
    Args:
        feature: Feature GeoJSON a procesar
        i: Índice para seleccionar el color
        color_variado: Color para este feature
        simplificacion: Factor de simplificación para reducir la complejidad de los polígonos
    
    Returns:
        Diccionario con datos para dibujar el polígono o None si hay error
    """
    try:
        # Obtener geometría
        geom = shape(feature['geometry'])
        
        # Simplificar la geometría para mejorar el rendimiento
        if simplificacion > 0:
            geom = geom.simplify(simplificacion, preserve_topology=True)
        
        # Seleccionar color para este distrito
        color = color_variado
        
        # Obtener coordenadas
        poligonos = []
        if geom.geom_type == 'Polygon':
            exterior_x, exterior_y = geom.exterior.xy
            poligonos.append((exterior_x, exterior_y, []))
            # Añadir agujeros
            for interior in geom.interiors:
                xi, yi = interior.xy
                poligonos[-1][2].append((xi, yi))
        elif geom.geom_type == 'MultiPolygon':
            for poligono in geom.geoms:
                exterior_x, exterior_y = poligono.exterior.xy
                interiores = []
                for interior in poligono.interiors:
                    xi, yi = interior.xy
                    interiores.append((xi, yi))
                poligonos.append((exterior_x, exterior_y, interiores))
        
        # Obtener nombre si está disponible
        nombre = feature.get('properties', {}).get('name', '')
        
        return {
            'poligonos': poligonos,
            'color': color,
            'nombre': nombre
        }
    except Exception as e:
        nombre = feature.get('properties', {}).get('name', 'Sin nombre')
        print(f"Error al procesar feature {nombre}: {str(e)}")
        return None

def dibujar_feature(ax, datos_poligono):
    """
    Dibuja un feature en el eje proporcionado.
    
    Args:
        ax: Eje de matplotlib donde dibujar
        datos_poligono: Datos del polígono a dibujar
    """
    if not datos_poligono:
        return
    
    for exterior_x, exterior_y, interiores in datos_poligono['poligonos']:
        # Dibujar el polígono exterior
        ax.fill(exterior_x, exterior_y, color=datos_poligono['color'], 
                alpha=0.7, edgecolor='black', linewidth=0.2)
        
        # Dibujar agujeros (interiores)
        for xi, yi in interiores:
            ax.fill(xi, yi, color='white', alpha=1.0)

def procesar_comunidad_paralelo(features, nombre_comunidad, color_base, simplificacion=0.0001):
    """
    Procesa todos los features de una comunidad en paralelo.
    
    Args:
        features: Lista de features a procesar
        nombre_comunidad: Nombre de la comunidad
        color_base: Color base para la comunidad
        simplificacion: Factor de simplificación de geometrías
    
    Returns:
        Tupla con (nombre_comunidad, lista de datos de polígonos, color_base)
    """
    # Generar variaciones del color para cada distrito
    num_features = len(features)
    colores_variados = generar_colores_variados(color_base, num_features)
    
    # Procesar features en paralelo
    poligonos_datos = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Crear una función parcial con los argumentos fijos
        func = partial(procesar_feature, simplificacion=simplificacion)
        # Mapear la función a cada feature con su índice y color correspondiente
        resultados = executor.map(func, features, range(len(features)), 
                                [colores_variados[i % len(colores_variados)] for i in range(len(features))])
        
        # Recoger resultados
        poligonos_datos = list(filter(None, resultados))
    
    return (nombre_comunidad, poligonos_datos, color_base)

def visualizar_mapa_comunidades(archivo_geojson, archivo_salida=None, mostrar=True, 
                                resolucion=2000, simplificacion=0.0001, max_workers=None):
    """
    Visualiza un mapa de España con sus comunidades autónomas y distritos.
    
    Args:
        archivo_geojson: Ruta al archivo GeoJSON unificado
        archivo_salida: Ruta donde guardar la imagen generada (opcional)
        mostrar: Si es True, muestra la imagen en pantalla
        resolucion: Resolución de la imagen en píxeles (mayor = más detalle pero más lento)
        simplificacion: Factor de simplificación de geometrías (0 para no simplificar)
        max_workers: Número máximo de procesos a utilizar (None para usar todos los disponibles)
    """
    print("Cargando datos GeoJSON...")
    datos = cargar_geojson(archivo_geojson)
    
    if not datos or 'features' not in datos or len(datos['features']) == 0:
        print("No se encontraron características en el archivo GeoJSON.")
        return False
    
    print(f"Procesando {len(datos['features'])} elementos...")
    
    # Crear figura con tamaño adecuado para mostrar España
    plt.figure(figsize=(12, 10), dpi=150)  # Alta resolución
    ax = plt.gca()
    
    # Obtener colores para las comunidades
    colores_comunidades = obtener_colores_comunidades()
    
    # Agrupar características por comunidad
    comunidades_features = {}
    for feature in datos['features']:
        if 'properties' in feature and 'origen' in feature['properties']:
            origen = feature['properties']['origen']
            if origen not in comunidades_features:
                comunidades_features[origen] = []
            comunidades_features[origen].append(feature)
    
    # Preparar parámetros para procesamiento paralelo
    tareas = []
    for nombre_comunidad, features in comunidades_features.items():
        # Si el nombre_comunidad no está en colores_comunidades, asignar un color aleatorio
        if nombre_comunidad not in colores_comunidades:
            colores_comunidades[nombre_comunidad] = (
                random.random(),
                random.random(),
                random.random()
            )
        
        color_base = colores_comunidades[nombre_comunidad]
        tareas.append((features, nombre_comunidad, color_base, simplificacion))
    
    # Procesar cada comunidad en paralelo
    print("Procesando comunidades en paralelo...")
    start_time = time.time()
    
    # Establecer max_workers si no se especificó
    if max_workers is None:
        max_workers = min(multiprocessing.cpu_count(), len(tareas))
    
    resultados = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Mapear la función a cada tarea
        futuros = [executor.submit(procesar_comunidad_paralelo, *tarea) for tarea in tareas]
        
        # Mostrar progreso
        for i, futuro in enumerate(concurrent.futures.as_completed(futuros)):
            try:
                resultado = futuro.result()
                resultados.append(resultado)
                print(f"Progreso: {i+1}/{len(tareas)} comunidades procesadas")
            except Exception as e:
                print(f"Error en procesamiento paralelo: {str(e)}")
    
    print(f"Procesamiento paralelo completado en {time.time() - start_time:.2f} segundos")
    
    # Dibujar cada comunidad
    print("Dibujando comunidades...")
    parches_leyenda = []
    
    for nombre_comunidad, poligonos_datos, color_base in resultados:
        # Añadir a la leyenda
        parche = mpatches.Patch(color=color_base, label=nombre_comunidad.replace('_', ' ').title())
        parches_leyenda.append(parche)
        
        # Dibujar cada polígono
        for datos_poligono in poligonos_datos:
            dibujar_feature(ax, datos_poligono)
    
    # Configurar el gráfico
    plt.title("Mapa de España por Comunidades Autónomas")
    plt.axis('equal')
    plt.axis('off')  # Quitar ejes
    
    # Añadir leyenda en la esquina superior derecha con varias columnas si hay muchas comunidades
    num_columnas = max(1, len(parches_leyenda) // 10)
    plt.legend(handles=parches_leyenda, loc='upper right', bbox_to_anchor=(0.99, 0.99),
               ncol=num_columnas, fontsize='small')
    
    plt.tight_layout()
    
    # Guardar imagen si se especificó un archivo de salida
    if archivo_salida:
        print(f"Guardando imagen en {archivo_salida}...")
        plt.savefig(archivo_salida, dpi=300, bbox_inches='tight')
        print(f"Imagen guardada con éxito en {archivo_salida}")
    
    # Mostrar el mapa si se solicitó
    if mostrar:
        print("Mostrando mapa (cierra la ventana para continuar)...")
        plt.show()
    
    return True

def procesar_por_comunidades_separadas(archivo_geojson, directorio_salida='mapas_comunidades', 
                                      simplificacion=0.0001, max_workers=None):
    """
    Genera mapas individuales para cada comunidad autónoma.
    
    Args:
        archivo_geojson: Ruta al archivo GeoJSON unificado
        directorio_salida: Directorio donde guardar las imágenes generadas
        simplificacion: Factor de simplificación de geometrías
        max_workers: Número máximo de procesos a utilizar
    """
    # Crear directorio de salida si no existe
    if not os.path.exists(directorio_salida):
        os.makedirs(directorio_salida)
        print(f"Directorio creado: {directorio_salida}")
    
    print("Cargando datos GeoJSON...")
    datos = cargar_geojson(archivo_geojson)
    
    if not datos or 'features' not in datos or len(datos['features']) == 0:
        print("No se encontraron características en el archivo GeoJSON.")
        return
    
    # Agrupar características por comunidad
    comunidades_features = {}
    for feature in datos['features']:
        if 'properties' in feature and 'origen' in feature['properties']:
            origen = feature['properties']['origen']
            if origen not in comunidades_features:
                comunidades_features[origen] = []
            comunidades_features[origen].append(feature)
    
    # Obtener colores para las comunidades
    colores_comunidades = obtener_colores_comunidades()
    
    # Preparar tareas para procesamiento paralelo
    tareas = []
    for nombre_comunidad, features in comunidades_features.items():
        # Obtener color base para esta comunidad
        if nombre_comunidad not in colores_comunidades:
            color_base = (random.random(), random.random(), random.random())
        else:
            color_base = colores_comunidades[nombre_comunidad]
        
        archivo_salida = os.path.join(directorio_salida, f"{nombre_comunidad}.png")
        tareas.append((nombre_comunidad, features, color_base, archivo_salida, simplificacion))
    
    # Definir función para procesar una comunidad
    def procesar_una_comunidad(nombre_comunidad, features, color_base, archivo_salida, simplificacion):
        try:
            print(f"Procesando {nombre_comunidad} ({len(features)} elementos)...")
            
            # Crear figura nueva para esta comunidad
            fig, ax = plt.subplots(figsize=(10, 10), dpi=150)
            
            # Obtener datos de los polígonos
            _, poligonos_datos, _ = procesar_comunidad_paralelo(
                features, nombre_comunidad, color_base, simplificacion
            )
            
            # Dibujar cada polígono
            for datos_poligono in poligonos_datos:
                dibujar_feature(ax, datos_poligono)
                
                # Si tiene nombre, añadir etiqueta
                if datos_poligono['nombre']:
                    # Calcular centroide aproximado como promedio de coordenadas
                    centroid_x = np.mean(datos_poligono['poligonos'][0][0])
                    centroid_y = np.mean(datos_poligono['poligonos'][0][1])
                    plt.text(centroid_x, centroid_y, datos_poligono['nombre'], 
                             fontsize=6, ha='center', va='center', alpha=0.7)
            
            # Configurar el gráfico
            plt.title(f"Comunidad Autónoma: {nombre_comunidad.replace('_', ' ').title()}")
            plt.axis('equal')
            plt.axis('off')  # Quitar ejes
            
            # Guardar imagen
            plt.savefig(archivo_salida, dpi=300, bbox_inches='tight')
            plt.close(fig)  # Cerrar figura para liberar memoria
            
            print(f"Imagen guardada: {archivo_salida}")
            return True
        except Exception as e:
            print(f"Error al procesar {nombre_comunidad}: {str(e)}")
            return False
    
    # Procesar comunidades en paralelo
    if max_workers is None:
        max_workers = min(multiprocessing.cpu_count(), len(tareas))
    
    print(f"Procesando {len(tareas)} comunidades con {max_workers} procesos...")
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futuros = [executor.submit(procesar_una_comunidad, *tarea) for tarea in tareas]
        
        # Mostrar progreso
        for i, futuro in enumerate(concurrent.futures.as_completed(futuros)):
            try:
                futuro.result()
                print(f"Progreso: {i+1}/{len(tareas)} comunidades completadas")
            except Exception as e:
                print(f"Error en procesamiento paralelo: {str(e)}")

if __name__ == "__main__":
    archivo_geojson = "espana_completa.geojson"
    
    if not os.path.exists(archivo_geojson):
        print(f"El archivo {archivo_geojson} no existe.")
        print("Primero debe ejecutar unir_geojson.py para crear este archivo.")
        sys.exit(1)
    
    # Determinar el número de procesos a utilizar (por defecto, número de núcleos)
    num_procesos = multiprocessing.cpu_count()
    print(f"Sistema detectado con {num_procesos} núcleos disponibles")
    
    # Opciones de visualización
    print("\nOpciones de visualización:")
    print("1. Visualizar mapa completo de España")
    print("2. Generar mapas individuales por comunidad autónoma")
    print("3. Ambas opciones")
    
    try:
        opcion = int(input("\nSeleccione una opción (1/2/3): "))
        
        # Opciones de rendimiento
        simplificacion = float(input("\nIntroduzca factor de simplificación (0.0001 recomendado, 0 para no simplificar): ") or "0.0001")
        max_workers = int(input(f"\nNúmero de procesos a utilizar (máx. {num_procesos}, Enter para usar todos): ") or str(num_procesos))
        
        if opcion == 1 or opcion == 3:
            # Visualizar mapa completo
            archivo_salida = "mapa_espana_completo.png"
            visualizar_mapa_comunidades(archivo_geojson, archivo_salida, 
                                        simplificacion=simplificacion, 
                                        max_workers=max_workers)
        
        if opcion == 2 or opcion == 3:
            # Generar mapas individuales
            procesar_por_comunidades_separadas(archivo_geojson, 
                                              simplificacion=simplificacion, 
                                              max_workers=max_workers)
        
        if opcion not in [1, 2, 3]:
            print("Opción no válida.")
    
    except ValueError:
        print("Por favor, introduzca un número válido.")
    
    print("\nProceso completado.") 