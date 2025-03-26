import os
import sys
import folium
import json
import geopandas as gpd
import random
import colorsys
import unicodedata
import re

def sanitizar_nombre_archivo(nombre):
    """
    Sanitiza un nombre para usarlo como nombre de archivo eliminando caracteres especiales
    
    Args:
        nombre: Nombre a sanitizar
    
    Returns:
        Nombre sanitizado
    """
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

def visualizar_geojson(geojson_file):
    """
    Crea un mapa interactivo a partir de un archivo GeoJSON
    
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
    
    # Añadir cada zona al mapa
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
        
        # Añadir una pequeña variación para cada zona del mismo municipio
        variacion = random.randint(-15, 15)
        r = max(0, min(255, r + variacion))
        g = max(0, min(255, g + variacion))
        b = max(0, min(255, b + variacion))
        
        color = f'#{r:02x}{g:02x}{b:02x}'
        
        # Añadir la zona al mapa
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
    
    # Sanitizar el nombre de la región para el nombre de archivo
    region_name_sanitizado = sanitizar_nombre_archivo(region_name)
    
    # Obtener directorio y nombre base del archivo de entrada
    input_dir = os.path.dirname(geojson_file)
    input_base = os.path.basename(geojson_file).split('.')[0]
    
    # Guardar el mapa en un archivo HTML
    output_html = os.path.join(input_dir, f"{input_base}_mapa.html")
    print(f"Guardando mapa en: {output_html}")
    m.save(output_html)
    
    print(f"Mapa creado exitosamente. Abre {output_html} en tu navegador para visualizarlo.")
    return output_html

def buscar_geojson_archivos():
    """
    Busca archivos GeoJSON en los directorios de salida
    
    Returns:
        Lista de rutas a archivos GeoJSON
    """
    archivos = []
    
    # Buscar en el directorio geojson_comunidades_zonas
    dir_comunidades = "geojson_comunidades_zonas"
    if os.path.exists(dir_comunidades):
        for archivo in os.listdir(dir_comunidades):
            if archivo.endswith(".geojson"):
                archivos.append(os.path.join(dir_comunidades, archivo))
    
    # Si no hay archivos, buscar en el directorio raíz
    if not archivos:
        for archivo in os.listdir('.'):
            if archivo.endswith(".geojson"):
                archivos.append(archivo)
    
    return archivos

def main():
    # Si se proporciona un archivo GeoJSON como argumento, visualizarlo
    if len(sys.argv) > 1:
        geojson_file = sys.argv[1]
        visualizar_geojson(geojson_file)
    else:
        # Buscar archivos GeoJSON disponibles
        geojson_files = buscar_geojson_archivos()
        
        if not geojson_files:
            print("No se encontraron archivos GeoJSON. Ejecuta primero main.py.")
            return
        
        # Mostrar los archivos disponibles
        print("Archivos GeoJSON disponibles:")
        for i, archivo in enumerate(geojson_files):
            print(f"{i+1}. {archivo}")
        
        # Preguntar cuál visualizar
        try:
            seleccion = int(input("\nSelecciona el número del archivo a visualizar (o 0 para salir): "))
            if seleccion == 0:
                return
            if 1 <= seleccion <= len(geojson_files):
                visualizar_geojson(geojson_files[seleccion-1])
            else:
                print("Selección no válida.")
        except ValueError:
            print("Por favor, introduce un número válido.")

if __name__ == "__main__":
    main() 