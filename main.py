import os
import geopandas as gpd
import json
import uuid
from shapely.geometry import mapping, shape, Polygon, MultiPolygon, Point
import numpy as np
from tqdm import tqdm
import math
import random
import sys
import matplotlib.pyplot as plt
import folium
import colorsys
import concurrent.futures
import multiprocessing
import unicodedata
import re
import time
import traceback  # Para trackear errores en detalle

# Variables globales para GPU
gpu_disponible = False
gpu_info = None
gpu_utils_importado = False

# Importar funciones optimizadas para GPU si están disponibles
try:
    from gpu_voronoi_utils import (verificar_gpu_disponible, 
                                  generar_puntos_dentro_poligono_gpu, 
                                  mejorar_puntos_aleatorios_gpu,
                                  optimizar_divisiones_voronoi_gpu)
    gpu_utils_importado = True
except ImportError:
    gpu_utils_importado = False
    print("Módulo gpu_voronoi_utils no encontrado. Utilizando funciones CPU estándar.")

# ----------------------------------------
# UTILIDADES PARA DIAGRAMA DE VORONOI
# ----------------------------------------

def generar_puntos_dentro_poligono(poligono, n_puntos):
    """
    Genera n_puntos puntos aleatorios dentro del polígono.
    
    Args:
        poligono: Polígono (shapely.geometry.Polygon)
        n_puntos: Número de puntos a generar
    
    Returns:
        Lista de puntos (x, y)
    """
    # Obtener bounding box del polígono
    minx, miny, maxx, maxy = poligono.bounds
    
    # Lista para almacenar los puntos generados
    puntos = []
    intentos_maximos = n_puntos * 1000  # Límite de intentos para evitar bucles infinitos
    intentos = 0
    
    # Generar puntos aleatorios dentro del polígono
    while len(puntos) < n_puntos and intentos < intentos_maximos:
        # Generar punto aleatorio dentro del bounding box
        x = random.uniform(minx, maxx)
        y = random.uniform(miny, maxy)
        punto = Point(x, y)
        
        # Verificar si el punto está dentro del polígono
        if poligono.contains(punto):
            puntos.append((x, y))
        
        intentos += 1
    
    return puntos

def poligonos_voronoi(puntos, poligono_limite):
    """
    Genera un diagrama de Voronoi y recorta las regiones por el polígono límite.
    
    Args:
        puntos: Lista de puntos (x, y)
        poligono_limite: Polígono que limita las regiones (shapely.geometry.Polygon)
    
    Returns:
        Lista de polígonos correspondientes a las regiones de Voronoi
    """
    from scipy.spatial import Voronoi
    
    # Si no hay suficientes puntos, devolver el polígono original
    if len(puntos) <= 1:
        return [poligono_limite]
    
    # Convertir puntos a array numpy
    puntos_np = np.array(puntos)
    
    # Obtener bounding box del polígono
    minx, miny, maxx, maxy = poligono_limite.bounds
    
    # Calcular el tamaño del bounding box
    ancho = maxx - minx
    alto = maxy - miny
    
    # Crear puntos adicionales fuera del polígono para cerrar regiones de Voronoi
    puntos_adicionales = [
        (minx - ancho, miny - alto),
        (minx - ancho, maxy + alto),
        (maxx + ancho, miny - alto),
        (maxx + ancho, maxy + alto),
        (minx - ancho, (miny + maxy) / 2),
        (maxx + ancho, (miny + maxy) / 2),
        ((minx + maxx) / 2, miny - alto),
        ((minx + maxx) / 2, maxy + alto)
    ]
    
    # Añadir puntos adicionales
    puntos_voronoi = np.vstack([puntos_np, puntos_adicionales])
    
    # Calcular diagrama de Voronoi
    vor = Voronoi(puntos_voronoi)
    
    # Lista para almacenar las regiones de Voronoi
    regiones_voronoi = []
    
    # Procesar regiones de Voronoi para los puntos originales (no los adicionales)
    for i in range(len(puntos)):
        # Obtener región de Voronoi para el punto i
        region_index = vor.point_region[i]
        region_vertices = vor.regions[region_index]
        
        # Verificar si la región es válida
        if -1 not in region_vertices and len(region_vertices) > 0:
            # Obtener coordenadas de los vértices
            polygon_vertices = [vor.vertices[v] for v in region_vertices]
            
            # Crear polígono
            poligono_voronoi = Polygon(polygon_vertices)
            
            # Intersectar con el polígono límite
            region_recortada = poligono_voronoi.intersection(poligono_limite)
            
            # Añadir a la lista si la intersección es válida
            if not region_recortada.is_empty:
                if isinstance(region_recortada, Polygon):
                    regiones_voronoi.append(region_recortada)
                elif isinstance(region_recortada, MultiPolygon):
                    # Si la intersección es un multipolígono, añadir cada parte
                    for geom in region_recortada.geoms:
                        regiones_voronoi.append(geom)
    
    # Si no se generaron regiones, devolver el polígono original
    if not regiones_voronoi:
        return [poligono_limite]
    
    return regiones_voronoi

# ----------------------------------------
# FUNCIONES PARA DIVIDIR MUNICIPIOS
# ----------------------------------------

def obtener_comunidades_autonomas(input_shapefile_recintos_autonomicos):
    """
    Obtiene la lista de comunidades autónomas del shapefile
    
    Args:
        input_shapefile_recintos_autonomicos: Ruta al shapefile de recintos autonómicos
    
    Returns:
        GeoDataFrame con las comunidades autónomas
    """
    print(f"Leyendo comunidades autónomas de: {input_shapefile_recintos_autonomicos}")
    gdf_ccaa = gpd.read_file(input_shapefile_recintos_autonomicos)
    
    # Asegurarse de que está en el sistema de coordenadas correcto (WGS84)
    if gdf_ccaa.crs != "EPSG:4326":
        print(f"Convirtiendo de {gdf_ccaa.crs} a EPSG:4326 (WGS84)")
        gdf_ccaa = gdf_ccaa.to_crs("EPSG:4326")
    
    return gdf_ccaa

def obtener_municipios(input_shapefile_municipios):
    """
    Obtiene todos los municipios del shapefile
    
    Args:
        input_shapefile_municipios: Ruta al shapefile de municipios
    
    Returns:
        GeoDataFrame con todos los municipios
    """
    print(f"Leyendo municipios de: {input_shapefile_municipios}")
    gdf_municipios = gpd.read_file(input_shapefile_municipios)
    
    # Asegurarse de que está en el sistema de coordenadas correcto (WGS84)
    if gdf_municipios.crs != "EPSG:4326":
        print(f"Convirtiendo de {gdf_municipios.crs} a EPSG:4326 (WGS84)")
        gdf_municipios = gdf_municipios.to_crs("EPSG:4326")
    
    return gdf_municipios

def determinar_numero_distritos(area_km2, poblacion=None):
    """
    Determina el número de distritos en que se debe dividir un municipio
    basado en su área y opcionalmente en su población
    
    Args:
        area_km2: Área del municipio en km²
        poblacion: Población del municipio (opcional)
    
    Returns:
        Número de distritos a crear
    """
    # Valores base para diferentes tamaños de municipios
    if area_km2 < 10:  # Muy pequeño
        num_distritos = 5
    elif area_km2 < 50:  # Pequeño
        num_distritos = 15
    elif area_km2 < 100:  # Mediano
        num_distritos = 25
    elif area_km2 < 500:  # Grande
        num_distritos = 50
    else:  # Muy grande (capitales de provincia, etc.)
        num_distritos = 100
    
    # Ajustar por población si está disponible
    if poblacion is not None:
        if poblacion > 500000:  # Grandes ciudades
            num_distritos = max(num_distritos, 150)
        elif poblacion > 200000:
            num_distritos = max(num_distritos, 100)
        elif poblacion > 100000:
            num_distritos = max(num_distritos, 75)
        elif poblacion > 50000:
            num_distritos = max(num_distritos, 50)
    
    return num_distritos

def dividir_poligono_voronoi(poligono, num_divisiones):
    """
    Divide un polígono en múltiples partes aproximadamente iguales usando Voronoi
    
    Args:
        poligono: Polígono a dividir (shapely.geometry.Polygon)
        num_divisiones: Número de divisiones a crear
    
    Returns:
        Lista de polígonos (shapely.geometry.Polygon)
    """
    try:
        # Verificar si el polígono es válido
        if not poligono.is_valid:
            print(f"Advertencia: Polígono no válido. Devolviendo polígono original.")
            return [poligono]
        
        # Verificar si el polígono es demasiado pequeño
        minx, miny, maxx, maxy = poligono.bounds
        if (maxx - minx) < 0.00001 or (maxy - miny) < 0.00001:
            print(f"Advertencia: Polígono demasiado pequeño para dividir. Devolviendo polígono original.")
            return [poligono]
            
        # Si el número de divisiones es 1 o menos, devolver el polígono original
        if num_divisiones <= 1:
            return [poligono]
            
        # Intentar usar GPU para generar puntos aleatorios si está disponible
        if gpu_disponible and gpu_utils_importado:
            # Generar puntos optimizados con GPU
            puntos = mejorar_puntos_aleatorios_gpu(poligono, num_divisiones)
        else:
            # Método CPU original
            puntos = generar_puntos_dentro_poligono(poligono, num_divisiones)
        
        # Si no hay suficientes puntos, probar con grid como alternativa
        if len(puntos) < num_divisiones:
            print(f"Advertencia: No se pueden generar {num_divisiones} puntos en el polígono. Se usarán {len(puntos)} divisiones.")
            
            # Si no se generó ningún punto, intentar con el método grid
            if len(puntos) == 0:
                print(f"Intentando dividir con método grid...")
                return dividir_poligono_grid(poligono, num_divisiones)
                
            num_divisiones = len(puntos)
        
        if num_divisiones <= 1:
            return [poligono]
        
        # Generar diagrama de Voronoi
        return poligonos_voronoi(puntos, poligono)
    except Exception as e:
        print(f"Error al dividir polígono: {e}")
        traceback.print_exc()  # Imprimir el traceback completo para depuración
        # En caso de error, intentar con el método grid
        try:
            print(f"Intentando dividir con método grid después de error...")
            return dividir_poligono_grid(poligono, num_divisiones)
        except Exception as e2:
            print(f"Error también al dividir con grid: {e2}")
            # En caso de error con grid también, devolver el polígono original
            return [poligono]

def dividir_poligono_grid(poligono, num_divisiones):
    """
    Divide un polígono en un grid aproximado
    
    Args:
        poligono: Polígono a dividir (shapely.geometry.Polygon)
        num_divisiones: Número aproximado de divisiones a crear
    
    Returns:
        Lista de polígonos (shapely.geometry.Polygon)
    """
    try:
        # Calcular el número de divisiones en cada eje
        lado = math.ceil(math.sqrt(num_divisiones))
        
        # Obtener bounding box del polígono
        minx, miny, maxx, maxy = poligono.bounds
        
        # Calcular tamaño de la celda
        ancho_celda = (maxx - minx) / lado
        alto_celda = (maxy - miny) / lado
        
        # Crear grid de celdas
        celdas = []
        for i in range(lado):
            for j in range(lado):
                # Crear celda
                x1 = minx + i * ancho_celda
                y1 = miny + j * alto_celda
                x2 = x1 + ancho_celda
                y2 = y1 + alto_celda
                celda = Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])
                
                # Intersectar con el polígono original
                interseccion = celda.intersection(poligono)
                if not interseccion.is_empty and interseccion.area > 0:
                    if isinstance(interseccion, Polygon):
                        celdas.append(interseccion)
                    elif isinstance(interseccion, MultiPolygon):
                        celdas.extend(list(interseccion.geoms))
        
        return celdas
    except Exception as e:
        print(f"Error al dividir polígono usando grid: {e}")
        return [poligono]

def procesar_comunidad_autonoma(gdf_ccaa, gdf_municipios, codigo_ccaa, output_dir, metodo_division="voronoi", visualizar=False):
    """
    Procesa una comunidad autónoma, dividiendo sus municipios en distritos más pequeños
    
    Args:
        gdf_ccaa: GeoDataFrame con todas las comunidades autónomas
        gdf_municipios: GeoDataFrame con todos los municipios
        codigo_ccaa: Código de la comunidad autónoma a procesar
        output_dir: Directorio donde se guardarán los archivos GeoJSON
        metodo_division: Método de división de polígonos ('voronoi' o 'grid')
        visualizar: Si se debe visualizar el resultado con matplotlib
    """
    try:
        # Filtrar la comunidad autónoma
        ccaa = gdf_ccaa[gdf_ccaa['NATCODE'] == codigo_ccaa]
        
        if ccaa.empty:
            print(f"No se encontró la comunidad autónoma con código {codigo_ccaa}")
            return
        
        nombre_ccaa = ccaa.iloc[0]['NAMEUNIT']
        
        # Traducciones de nombres de comunidades autónomas de catalán a español
        traducciones = {
            "Illes Balears": "Islas Baleares",
            "Catalunya": "Cataluña",
            "Euskadi": "País Vasco",
            "Comunitat Valenciana": "Comunidad Valenciana",
            "Galicia/Galiza": "Galicia"
        }
        
        # Aplicar traducción si existe
        if nombre_ccaa in traducciones:
            nombre_ccaa = traducciones[nombre_ccaa]
        
        print(f"\nProcesando comunidad autónoma: {nombre_ccaa} (código {codigo_ccaa})")
        
        # Filtrar municipios de esta comunidad autónoma correctamente
        # Extraer el código de la comunidad autónoma del NATCODE (los primeros 2 dígitos)
        codigo_ccaa_prefijo = codigo_ccaa[:2]
        
        # Obtener la geometría de la comunidad autónoma para filtrar espacialmente
        geometria_ccaa = ccaa.geometry.iloc[0]
        
        # Filtrar los municipios que están dentro de la comunidad autónoma espacialmente
        # y que tienen el prefijo correcto en su NATCODE
        municipios_dentro = gdf_municipios[gdf_municipios.intersects(geometria_ccaa)]
        municipios_ccaa = municipios_dentro[municipios_dentro['NATCODE'].str.startswith(codigo_ccaa_prefijo)]
        
        if municipios_ccaa.empty:
            print(f"No se encontraron municipios para la comunidad autónoma {nombre_ccaa}")
            return
        
        print(f"Encontrados {len(municipios_ccaa)} municipios en {nombre_ccaa}")
        
        # Crear la estructura del GeoJSON
        geojson_data = {
            "type": "FeatureCollection",
            "region_name": nombre_ccaa,
            "features": []
        }
        
        # Para visualización
        if visualizar:
            fig, ax = plt.subplots(figsize=(15, 15))
            ccaa.plot(ax=ax, color='none', edgecolor='black', linewidth=2)
        
        # Procesar cada municipio
        total_distritos = 0
        with tqdm(total=len(municipios_ccaa), desc=f"Procesando municipios de {nombre_ccaa}") as pbar:
            for idx, municipio in municipios_ccaa.iterrows():
                try:
                    # Extraer nombre y geometría del municipio
                    nombre_municipio = municipio['NAMEUNIT']
                    
                    # Traducir nombres de municipios si están en catalán u otros idiomas
                    # Aquí se podrían añadir más traducciones si fuera necesario
                    
                    geometria = municipio.geometry
                    
                    # Calcular área en km²
                    area_km2 = geometria.area * 111 * 111  # Conversión aproximada de grados a km²
                    
                    # Determinar número de distritos
                    num_distritos = determinar_numero_distritos(area_km2)
                    
                    # Lista para almacenar los distritos generados
                    distritos = []
                    
                    # Manejar MultiPolygon vs Polygon
                    if isinstance(geometria, MultiPolygon):
                        for i, poligono in enumerate(geometria.geoms):
                            # Determinar número de distritos para este polígono basado en su área relativa
                            area_poligono = poligono.area
                            area_total = geometria.area
                            num_distritos_poligono = max(1, int(num_distritos * (area_poligono / area_total)))
                            
                            if metodo_division == "voronoi":
                                distritos_poligono = dividir_poligono_voronoi(poligono, num_distritos_poligono)
                            else:
                                distritos_poligono = dividir_poligono_grid(poligono, num_distritos_poligono)
                            
                            # Añadir identificador a cada distrito - cambiando "Parte" por "Distrito"
                            for j, distrito in enumerate(distritos_poligono):
                                distritos.append((f"{nombre_municipio} - Distrito {i+1} - Zona {j+1}", distrito))
                    else:
                        if metodo_division == "voronoi":
                            distritos_poligono = dividir_poligono_voronoi(geometria, num_distritos)
                        else:
                            distritos_poligono = dividir_poligono_grid(geometria, num_distritos)
                        
                        # Añadir identificador a cada distrito
                        for j, distrito in enumerate(distritos_poligono):
                            distritos.append((f"{nombre_municipio} - Zona {j+1}", distrito))
                    
                    # Añadir distritos al GeoJSON
                    for nombre_distrito, geometria_distrito in distritos:
                        # Crear un feature GeoJSON
                        feature = {
                            "type": "Feature",
                            "properties": {
                                "id": str(uuid.uuid4()),
                                "name": nombre_distrito,
                                "description": "",
                                "isUnlocked": False
                            },
                            "geometry": mapping(geometria_distrito)
                        }
                        
                        # Añadir el feature a la colección
                        geojson_data["features"].append(feature)
                        
                        # Para visualización
                        if visualizar:
                            x, y = geometria_distrito.exterior.xy
                            ax.fill(x, y, alpha=0.5)
                    
                    total_distritos += len(distritos)
                    pbar.update(1)
                except Exception as e:
                    print(f"Error al procesar municipio {municipio['NAMEUNIT']}: {e}")
                    traceback.print_exc()  # Imprimir el traceback completo
                    pbar.update(1)
                    continue
        
        # Sanitizar el nombre de la comunidad autónoma para el nombre de archivo
        # Eliminar tildes y otros caracteres especiales
        def sanitizar_nombre_archivo(nombre):
            # Convertir a minúsculas
            nombre = nombre.lower()
            
            # Normalizar (descomponer caracteres acentuados)
            nombre = unicodedata.normalize('NFKD', nombre)
            
            # Eliminar acentos y caracteres no ASCII
            nombre = ''.join([c for c in nombre if not unicodedata.combining(c)])
            
            # Reemplazar espacios y caracteres no alfanuméricos por guiones bajos
            nombre = re.sub(r'[^a-z0-9]', '_', nombre)
            
            # Eliminar guiones bajos múltiples
            nombre = re.sub(r'_+', '_', nombre)
            
            # Eliminar guiones bajos al principio y al final
            nombre = nombre.strip('_')
            
            return nombre
        
        nombre_archivo = sanitizar_nombre_archivo(nombre_ccaa)
        
        # Guardar el GeoJSON
        filename = f"{codigo_ccaa}_{nombre_archivo}.geojson"
        output_geojson = os.path.join(output_dir, filename)
        print(f"Guardando GeoJSON en: {output_geojson}")
        
        try:
            with open(output_geojson, 'w', encoding='utf-8') as f:
                json.dump(geojson_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error al guardar el archivo GeoJSON: {e}")
            traceback.print_exc()  # Imprimir el traceback completo
            # Intentar guardar con una versión reducida (sin indent)
            try:
                print("Intentando guardar versión sin formato...")
                with open(output_geojson, 'w', encoding='utf-8') as f:
                    json.dump(geojson_data, f, ensure_ascii=False)
                print("Archivo guardado sin formato (sin indentación).")
            except Exception as e2:
                print(f"Error al guardar versión sin formato: {e2}")
        
        print(f"Archivo GeoJSON creado exitosamente. Contiene {total_distritos} zonas.")
        
        # Mostrar visualización
        if visualizar:
            plt.title(f"Zonas de {nombre_ccaa}")
            plt.savefig(os.path.join(output_dir, f"{codigo_ccaa}_{nombre_archivo}.png"))
            plt.close()
        
        return output_geojson
    
    except Exception as e:
        print(f"Error general al procesar la comunidad autónoma {codigo_ccaa}: {e}")
        traceback.print_exc()  # Imprimir el traceback completo
        return None

# ----------------------------------------
# FUNCIONES PARA VISUALIZACIÓN
# ----------------------------------------

def generar_paleta_colores(n):
    """
    Genera una paleta de n colores visualmente distintos
    
    Args:
        n: Número de colores a generar
    
    Returns:
        Lista de colores en formato hexadecimal
    """
    colores = []
    for i in range(n):
        # Usar HSV para generar colores distintos
        h = i / n
        s = 0.7 + random.random() * 0.3  # Saturación entre 0.7 y 1.0
        v = 0.7 + random.random() * 0.3  # Valor entre 0.7 y 1.0
        
        # Convertir a RGB
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        
        # Convertir a hexadecimal
        color_hex = f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'
        colores.append(color_hex)
    
    return colores

def visualizar_geojson_distritos(geojson_file):
    """
    Crea un mapa interactivo a partir de un archivo GeoJSON de distritos
    
    Args:
        geojson_file: Ruta al archivo GeoJSON a visualizar
    """
    # Verificar que el archivo existe
    if not os.path.exists(geojson_file):
        print(f"El archivo {geojson_file} no existe.")
        return
    
    # Leer el archivo GeoJSON
    print(f"Leyendo GeoJSON: {geojson_file}")
    try:
        # Intentar primero con geopandas que es más robusto para GeoJSON grandes
        gdf = gpd.read_file(geojson_file)
        with open(geojson_file, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
            region_name = geojson_data.get('region_name', 'Región')
    except Exception as e:
        print(f"Error al leer el archivo GeoJSON: {e}")
        return
    
    # Crear un mapa centrado en los datos
    bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=9, 
                   tiles='CartoDB positron')
    
    # Agrupar por municipio para asignar colores similares
    municipios = {}
    for idx, row in gdf.iterrows():
        nombre = row['name']
        # Extraer nombre del municipio (antes del primer '-')
        municipio = nombre.split('-')[0].strip() if '-' in nombre else nombre
        if municipio not in municipios:
            municipios[municipio] = []
        municipios[municipio].append(idx)
    
    # Generar colores por municipio
    colores_municipios = {}
    paleta = generar_paleta_colores(len(municipios))
    for i, municipio in enumerate(municipios.keys()):
        colores_municipios[municipio] = paleta[i]
    
    # Añadir cada distrito al mapa
    for idx, row in gdf.iterrows():
        nombre = row['name']
        # Extraer nombre del municipio
        municipio = nombre.split('-')[0].strip() if '-' in nombre else nombre
        
        # Obtener color base del municipio y añadir una variación
        color_base = colores_municipios[municipio]
        # Convertir color hex a RGB
        r = int(color_base[1:3], 16)
        g = int(color_base[3:5], 16)
        b = int(color_base[5:7], 16)
        
        # Añadir una pequeña variación para cada distrito del mismo municipio
        variacion = random.randint(-15, 15)
        r = max(0, min(255, r + variacion))
        g = max(0, min(255, g + variacion))
        b = max(0, min(255, b + variacion))
        
        color = f'#{r:02x}{g:02x}{b:02x}'
        
        # Añadir el distrito al mapa
        folium.GeoJson(
            row.geometry,
            name=nombre,
            style_function=lambda x, color=color: {
                'fillColor': color,
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.6
            },
            tooltip=nombre
        ).add_to(m)
    
    # Añadir control de capas
    folium.LayerControl().add_to(m)
    
    # Guardar el mapa en un archivo HTML
    output_html = f"{os.path.splitext(geojson_file)[0]}_mapa_zonas.html"
    print(f"Guardando mapa en: {output_html}")
    m.save(output_html)
    
    print(f"Mapa creado exitosamente. Abre {output_html} en tu navegador para visualizarlo.")
    return output_html

# ----------------------------------------
# FUNCIONES PARA PROCESAMIENTO PARALELO
# ----------------------------------------

def procesar_comunidad_autonoma_wrapper(args):
    """
    Wrapper para la función procesar_comunidad_autonoma para poder usarla en ProcessPoolExecutor
    
    Args:
        args: Tupla con los argumentos para procesar_comunidad_autonoma
    
    Returns:
        Resultado de procesar_comunidad_autonoma
    """
    return procesar_comunidad_autonoma(*args)

# ----------------------------------------
# FUNCIÓN PRINCIPAL
# ----------------------------------------

def main():
    # Iniciar cronómetro
    tiempo_inicio = time.time()
    
    # ----------------------------------------
    # VERIFICAR ARGUMENTOS DE LÍNEA DE COMANDOS
    # ----------------------------------------
    
    # Forzar modo CPU o GPU si se especifica como argumento
    forzar_cpu = False
    forzar_gpu = False
    modo_rapido = False
    modo_preciso = False
    codigo_ccaa_especifico = None
    metodo_division = "voronoi"
    
    # Procesar argumentos de línea de comandos
    for arg in sys.argv[1:]:
        arg_lower = arg.lower()
        if arg_lower == "cpu":
            forzar_cpu = True
            print("Modo CPU forzado por línea de comandos")
        elif arg_lower == "gpu":
            forzar_gpu = True
            print("Modo GPU forzado por línea de comandos")
        elif arg_lower in ["voronoi", "grid"]:
            metodo_division = arg_lower
            print(f"Método de división: {metodo_division}")
        elif arg_lower == "rapido":
            modo_rapido = True
            print("Modo rápido activado: se priorizará la velocidad sobre la precisión")
        elif arg_lower == "preciso":
            modo_preciso = True
            print("Modo preciso activado: se priorizará la precisión sobre la velocidad")
        elif len(arg) >= 8:  # Posible código de comunidad autónoma
            codigo_ccaa_especifico = arg
    
    # No permitir ambos modos a la vez
    if modo_rapido and modo_preciso:
        print("ADVERTENCIA: Los modos rápido y preciso son mutuamente excluyentes. Desactivando ambos.")
        modo_rapido = False
        modo_preciso = False
    
    # Directorio base
    base_dir = "lineas_limite"
    
    # Shapefiles
    shapefile_ccaa = os.path.join(base_dir, "SHP_ETRS89", "recintos_autonomicas_inspire_peninbal_etrs89", 
                                 "recintos_autonomicas_inspire_peninbal_etrs89.shp")
    
    shapefile_municipios = os.path.join(base_dir, "SHP_ETRS89", "recintos_municipales_inspire_peninbal_etrs89", 
                                       "recintos_municipales_inspire_peninbal_etrs89.shp")
    
    # Verificar que los archivos existen
    if not os.path.exists(shapefile_ccaa):
        print(f"El archivo {shapefile_ccaa} no existe. Asegúrate de tener la estructura de carpetas correcta.")
        return
    
    if not os.path.exists(shapefile_municipios):
        print(f"El archivo {shapefile_municipios} no existe. Asegúrate de tener la estructura de carpetas correcta.")
        return
    
    # Directorio para guardar los archivos GeoJSON
    output_dir = "geojson_comunidades_zonas"
    os.makedirs(output_dir, exist_ok=True)
    
    # Obtener comunidades autónomas y municipios
    gdf_ccaa = obtener_comunidades_autonomas(shapefile_ccaa)
    gdf_municipios = obtener_municipios(shapefile_municipios)
    
    # ----------------------------------------
    # AJUSTAR PARÁMETROS SEGÚN EL MODO
    # ----------------------------------------
    
    # Variables globales para ajustar el comportamiento según el modo
    global gpu_disponible, gpu_info
    
    # Configuración para modo rápido
    if modo_rapido:
        # En modo rápido, usar grid en lugar de voronoi si no se especificó lo contrario
        if metodo_division == "voronoi" and not "voronoi" in sys.argv[1:]:
            metodo_division = "grid"
            print(f"Modo rápido: cambiando método de división a {metodo_division}")
        
        # En modo rápido, preferir CPU si no se especificó GPU
        if not forzar_gpu:
            forzar_cpu = True
            print("Modo rápido: forzando uso de CPU para mayor velocidad (más eficiente para este caso de uso)")
    
    # Configuración para modo preciso
    if modo_preciso:
        # En modo preciso, usar voronoi en lugar de grid si no se especificó lo contrario
        if metodo_division == "grid" and not "grid" in sys.argv[1:]:
            metodo_division = "voronoi"
            print(f"Modo preciso: cambiando método de división a {metodo_division}")
        
        # En modo preciso, preferir GPU si no se especificó CPU y GPU está disponible
        if not forzar_cpu and gpu_utils_importado:
            disponible, _ = verificar_gpu_disponible()
            if disponible:
                forzar_gpu = True
                print("Modo preciso: intentando usar GPU para mayor precisión")
    
    # ----------------------------------------
    # DETECCIÓN DE GPU MEJORADA
    # ----------------------------------------

    # Si se fuerza el modo CPU, no intentar detectar GPU
    if forzar_cpu:
        gpu_disponible = False
        print("Usando modo CPU como se especificó")
    else:
        # Intentar detectar GPU solo si no se forzó modo CPU
        # Primero comprobar con nuestras utilidades especializadas
        if gpu_utils_importado:
            try:
                gpu_disponible, gpu_info = verificar_gpu_disponible()
                if gpu_disponible:
                    print(f"GPU detectada: {gpu_info['nombre']} ({gpu_info['memoria_total_gb']:.2f} GB)")
                    print(f"Compute Capability: {gpu_info['compute_capability']}")
                    print("Usando funciones optimizadas para GPU")
            except Exception as e:
                print(f"Error al verificar GPU con funciones personalizadas: {e}")
                gpu_disponible = False
        
        # Si no se detectó con nuestras utilidades, probar otros métodos
        if not gpu_disponible and not forzar_cpu:
            try:
                import cupy as cp
                import cupyx
                
                # Verificar si CUDA está disponible
                if cp.cuda.is_available():
                    # Obtener información de la GPU
                    device_props = cp.cuda.runtime.getDeviceProperties(0)
                    gpu_nombre = device_props["name"].decode('utf-8')
                    gpu_memoria = device_props["totalGlobalMem"] / (1024**3)  # Convertir a GB
                    
                    print(f"Utilizando aceleración GPU con CuPy en: {gpu_nombre} ({gpu_memoria:.2f} GB)")
                    gpu_disponible = True
                    gpu_info = {
                        "nombre": gpu_nombre,
                        "memoria_total_gb": gpu_memoria
                    }
                    
                    # Reemplazar la función original con la versión GPU
                    if not gpu_utils_importado:
                        generar_puntos_dentro_poligono_original = generar_puntos_dentro_poligono
                        
                        # Función para generar puntos aleatorios usando CuPy
                        def gpu_generar_puntos_aleatorios(n, minx, miny, maxx, maxy):
                            """Genera n puntos aleatorios en el rango especificado usando GPU"""
                            # Generar coordenadas x e y aleatorias en GPU
                            x = cp.random.uniform(minx, maxx, n)
                            y = cp.random.uniform(miny, maxy, n)
                            # Transferir de vuelta a CPU para procesamiento posterior
                            return cp.asnumpy(x), cp.asnumpy(y)
                        
                        # Reemplazar la función normal por la versión GPU
                        def generar_puntos_dentro_poligono_gpu(poligono, n_puntos):
                            """Versión acelerada por GPU de generar_puntos_dentro_poligono"""
                            # Obtener bounding box del polígono
                            minx, miny, maxx, maxy = poligono.bounds
                            
                            # Lista para almacenar los puntos generados
                            puntos = []
                            
                            # Generar lotes de puntos en GPU y filtrar en CPU
                            batch_size = min(100000, n_puntos * 10)  # Tamaño de lote óptimo
                            intentos = 0
                            max_intentos = n_puntos * 10000
                            
                            while len(puntos) < n_puntos and intentos < max_intentos:
                                # Generar un lote de puntos aleatorios usando GPU
                                x_batch, y_batch = gpu_generar_puntos_aleatorios(batch_size, minx, maxx, miny, maxy)
                                
                                # Filtrar puntos en CPU (shapely no trabaja directamente con GPU)
                                for i in range(len(x_batch)):
                                    punto = Point(x_batch[i], y_batch[i])
                                    if poligono.contains(punto):
                                        puntos.append((x_batch[i], y_batch[i]))
                                        if len(puntos) >= n_puntos:
                                            break
                                
                                intentos += batch_size
                            
                            return puntos
                        
                        # Reemplazar la función original con la versión GPU
                        generar_puntos_dentro_poligono = generar_puntos_dentro_poligono_gpu
                else:
                    print("CUDA está instalado pero no disponible. Verificando otras opciones de GPU...")
            except ImportError:
                print("CuPy no está instalado. Verificando otras opciones de GPU...")
            except Exception as e:
                print(f"Error al inicializar CuPy: {e}")
                print("Continuando con funciones CPU estándar.")
    
    # Si se forzó el modo GPU pero no se detectó GPU, mostrar advertencia
    if forzar_gpu and not gpu_disponible:
        print("ADVERTENCIA: Se solicitó modo GPU pero no se pudo detectar una GPU compatible. Intente instalar CUDA y CuPy.")
        print("Continuando en modo CPU...")
    
    # Forzar GPU si se especificó como argumento y se pudo detectar
    if forzar_gpu and not gpu_disponible:
        # Intentar con otras bibliotecas
        if not gpu_disponible and forzar_gpu:
            try:
                import cudf
                import cuspatial
                
                print("Utilizando aceleración GPU con RAPIDS (cuDF/cuSpatial)")
                # Aquí se podrían añadir optimizaciones específicas para RAPIDS/cuspatial
                gpu_disponible = True
            except ImportError:
                print("RAPIDS no está instalado. Intente instalar RAPIDS para procesamiento GPU.")
        
        if not gpu_disponible and forzar_gpu:
            try:
                # Intentar usar PyTorch si está disponible
                import torch
                if torch.cuda.is_available():
                    device = torch.device("cuda:0")
                    gpu_nombre = torch.cuda.get_device_name(0)
                    gpu_memoria = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                    
                    print(f"Utilizando aceleración limitada GPU con PyTorch en: {gpu_nombre} ({gpu_memoria:.2f} GB)")
                    
                    # Función para generar puntos aleatorios usando PyTorch
                    def torch_generar_puntos_aleatorios(n, minx, miny, maxx, maxy):
                        # Generar coordenadas x e y aleatorias en GPU
                        x = torch.rand(n, device=device) * (maxx - minx) + minx
                        y = torch.rand(n, device=device) * (maxy - miny) + miny
                        # Transferir de vuelta a CPU
                        return x.cpu().numpy(), y.cpu().numpy()
                    
                    # Implementar la versión GPU con PyTorch
                    def generar_puntos_dentro_poligono_torch(poligono, n_puntos):
                        # Obtener bounding box del polígono
                        minx, miny, maxx, maxy = poligono.bounds
                        
                        # Lista para almacenar los puntos generados
                        puntos = []
                        
                        # Generar lotes de puntos en GPU y filtrar en CPU
                        batch_size = min(100000, n_puntos * 10)
                        intentos = 0
                        max_intentos = n_puntos * 20
                        
                        while len(puntos) < n_puntos and intentos < max_intentos:
                            # Generar un lote de puntos aleatorios usando PyTorch
                            x_batch, y_batch = torch_generar_puntos_aleatorios(batch_size, minx, maxx, miny, maxy)
                            
                            # Filtrar puntos en CPU
                            for i in range(len(x_batch)):
                                punto = Point(x_batch[i], y_batch[i])
                                if poligono.contains(punto):
                                    puntos.append((x_batch[i], y_batch[i]))
                                    if len(puntos) >= n_puntos:
                                        break
                            
                            intentos += batch_size
                        
                        return puntos
                    
                    # Reemplazar la función original con la versión PyTorch
                    generar_puntos_dentro_poligono_original = generar_puntos_dentro_poligono
                    generar_puntos_dentro_poligono = generar_puntos_dentro_poligono_torch
                    
                    gpu_disponible = True
                    print("Optimizaciones GPU activadas para generación de puntos aleatorios (PyTorch).")
                else:
                    print("PyTorch está instalado pero CUDA no está disponible.")
            except ImportError:
                print("PyTorch no está instalado. No se pudo activar el modo GPU.")
                if forzar_gpu:
                    print("ADVERTENCIA: No se pudo encontrar ninguna biblioteca GPU compatible. Ejecutando en modo CPU.")
    
    print(f"Modo de procesamiento: {'GPU' if gpu_disponible else 'CPU'}")
    
    # Lista de comunidades autónomas
    codigos_ccaa = gdf_ccaa['NATCODE'].unique()
    
    # Si se proporciona un código de comunidad autónoma específico
    if codigo_ccaa_especifico:
        if codigo_ccaa_especifico in codigos_ccaa:
            print(f"Procesando solo la comunidad autónoma con código: {codigo_ccaa_especifico}")
            geojson_file = procesar_comunidad_autonoma(gdf_ccaa, gdf_municipios, codigo_ccaa_especifico, output_dir, metodo_division)
            # Visualizar el resultado
            if geojson_file:
                visualizar_geojson_distritos(geojson_file)
        else:
            print(f"No se encontró la comunidad autónoma con código {codigo_ccaa_especifico}")
            print(f"Comunidades disponibles: {codigos_ccaa}")
    else:
        # Determinar el número óptimo de trabajadores basado en GPU vs CPU
        if gpu_disponible:
            # Si hay GPU, procesar secuencialmente para aprovechar toda la memoria GPU
            # Esto evita fragmentación y competición por recursos GPU
            print(f"Procesando {len(codigos_ccaa)} comunidades autónomas secuencialmente con GPU")
            
            resultados = []
            for i, codigo_ccaa in enumerate(codigos_ccaa):
                print(f"Procesando comunidad {i+1} de {len(codigos_ccaa)}")
                geojson_file = procesar_comunidad_autonoma(gdf_ccaa, gdf_municipios, codigo_ccaa, output_dir, metodo_division, False)
                resultados.append(geojson_file)
                
                # Liberar memoria GPU después de cada comunidad
                if 'cp' in globals():
                    cp.get_default_memory_pool().free_all_blocks()
                if 'torch' in globals() and 'cuda' in dir(torch):
                    torch.cuda.empty_cache()
                    
        else:
            # Si no hay GPU, procesar en paralelo con CPU
            num_workers = min(16, len(codigos_ccaa), multiprocessing.cpu_count())
            print(f"Procesando {len(codigos_ccaa)} comunidades autónomas con {num_workers} hilos en paralelo (CPU)")
            
            # Preparar argumentos para cada comunidad autónoma
            args_list = [(gdf_ccaa, gdf_municipios, codigo_ccaa, output_dir, metodo_division, False) 
                         for codigo_ccaa in codigos_ccaa]
            
            # Lista para almacenar los resultados
            resultados = []
            
            # Procesar en paralelo con límite de tiempo para evitar bloqueos
            with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
                # Iniciar las tareas y obtener los futuros
                futures = [executor.submit(procesar_comunidad_autonoma_wrapper, args) for args in args_list]
                
                # Monitorear el progreso
                completados = 0
                for future in concurrent.futures.as_completed(futures):
                    try:
                        geojson_file = future.result(timeout=600)  # Timeout de 10 minutos por comunidad
                        completados += 1
                        resultados.append(geojson_file)
                        print(f"Completado {completados}/{len(codigos_ccaa)} comunidades autónomas")
                    except concurrent.futures.TimeoutError:
                        print(f"Timeout al procesar una comunidad autónoma. Continuando con las demás.")
                    except Exception as e:
                        print(f"Error al procesar una comunidad autónoma: {e}")
    
    # Calcular tiempo total
    tiempo_total = time.time() - tiempo_inicio
    horas, resto = divmod(tiempo_total, 3600)
    minutos, segundos = divmod(resto, 60)
    
    # Listar archivos generados
    archivos_generados = [f for f in os.listdir(output_dir) if f.endswith(".geojson")]
    
    print("\nProceso completado. Se han generado los siguientes archivos:")
    for file in archivos_generados:
        print(f" - {os.path.join(output_dir, file)}")
    
    print(f"\nTiempo total de procesamiento: {int(horas):02d}:{int(minutos):02d}:{int(segundos):02.2f}")
    print(f"Transformación completada con éxito: {len(archivos_generados)} archivos GeoJSON generados")
    
    print("\n====== AYUDA ======")
    print("\nEste script acepta los siguientes parámetros:")
    print("\n1. Código de comunidad autónoma:")
    print(f"   py {__file__} 34010000000  # Ejemplo para Andalucía")
    
    print("\n2. Modo de hardware:")
    print(f"   py {__file__} cpu          # Fuerza el uso de CPU")
    print(f"   py {__file__} gpu          # Fuerza el uso de GPU")
    
    print("\n3. Método de división:")
    print(f"   py {__file__} voronoi      # Usa el método de Voronoi (más preciso, más lento)")
    print(f"   py {__file__} grid         # Usa el método de Grid (menos preciso, más rápido)")
    
    print("\n4. Optimización automática:")
    print(f"   py {__file__} rapido       # Prioriza velocidad (usa grid y CPU por defecto)")
    print(f"   py {__file__} preciso      # Prioriza precisión (usa voronoi y GPU si disponible)")
    
    print("\nLos parámetros se pueden combinar:")
    print(f"   py {__file__} 34010000000 cpu rapido  # Procesa Andalucía con CPU en modo rápido")
    
    print("\nPara visualizar un archivo GeoJSON ya generado:")
    print(f"   py visualizar_geojson.py geojson_comunidades_zonas/34010000000_andalucia.geojson")

if __name__ == "__main__":
    main() 