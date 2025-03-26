import os
import sys
import folium
import json
import geopandas as gpd
import random
import branca.colormap as cm
import colorsys

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
    output_html = f"{os.path.splitext(geojson_file)[0]}_mapa_distritos.html"
    print(f"Guardando mapa en: {output_html}")
    m.save(output_html)
    
    print(f"Mapa creado exitosamente. Abre {output_html} en tu navegador para visualizarlo.")
    return output_html

def main():
    # Si se proporciona un archivo GeoJSON como argumento, visualizarlo
    if len(sys.argv) > 1:
        geojson_file = sys.argv[1]
        visualizar_geojson_distritos(geojson_file)
    else:
        # Buscar archivos GeoJSON en el directorio geojson_comunidades_distritos
        geojson_dir = "geojson_comunidades_distritos"
        if not os.path.exists(geojson_dir):
            print(f"El directorio {geojson_dir} no existe. Ejecuta primero dividir_municipios.py")
            return
        
        geojson_files = [os.path.join(geojson_dir, f) for f in os.listdir(geojson_dir) 
                         if f.endswith('.geojson')]
        
        if not geojson_files:
            print(f"No se encontraron archivos GeoJSON en {geojson_dir}")
            return
        
        # Visualizar el primer archivo GeoJSON encontrado
        print(f"Archivos GeoJSON disponibles: {len(geojson_files)}")
        print("Visualizando el primer archivo encontrado. Para visualizar otro archivo, proporciona su ruta como argumento.")
        visualizar_geojson_distritos(geojson_files[0])

if __name__ == "__main__":
    main() 