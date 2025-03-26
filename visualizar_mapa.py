import os
import sys
import folium
import json
import geopandas as gpd
import random

def generar_color_aleatorio():
    """Genera un color aleatorio en formato hexadecimal"""
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    return f'#{r:02x}{g:02x}{b:02x}'

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
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=8, 
                   tiles='CartoDB positron')
    
    # Añadir el GeoJSON al mapa
    folium.GeoJson(
        gdf,
        name=region_name,
        style_function=lambda x: {
            'fillColor': generar_color_aleatorio(),
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.7
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['name'],
            aliases=['Nombre:'],
            style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;")
        )
    ).add_to(m)
    
    # Añadir control de capas
    folium.LayerControl().add_to(m)
    
    # Guardar el mapa en un archivo HTML
    output_html = f"{os.path.splitext(geojson_file)[0]}_mapa.html"
    print(f"Guardando mapa en: {output_html}")
    m.save(output_html)
    
    print(f"Mapa creado exitosamente. Abre {output_html} en tu navegador para visualizarlo.")
    return output_html

def main():
    # Si se proporciona un archivo GeoJSON como argumento, visualizarlo
    if len(sys.argv) > 1:
        geojson_file = sys.argv[1]
        visualizar_geojson(geojson_file)
    else:
        # Buscar archivos GeoJSON en el directorio geojson_municipios
        geojson_dir = "geojson_municipios"
        if not os.path.exists(geojson_dir):
            print(f"El directorio {geojson_dir} no existe. Ejecuta primero procesar_por_provincia.py")
            return
        
        geojson_files = [os.path.join(geojson_dir, f) for f in os.listdir(geojson_dir) 
                         if f.endswith('.geojson')]
        
        if not geojson_files:
            print(f"No se encontraron archivos GeoJSON en {geojson_dir}")
            return
        
        # Visualizar el primer archivo GeoJSON encontrado
        print(f"Archivos GeoJSON disponibles: {len(geojson_files)}")
        print("Visualizando el primer archivo encontrado. Para visualizar otro archivo, proporciona su ruta como argumento.")
        visualizar_geojson(geojson_files[0])

if __name__ == "__main__":
    main() 