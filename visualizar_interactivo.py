import os
import sys
import folium
import json
import geopandas as gpd
import random
import colorsys
import unicodedata
import re
import branca.colormap as cm
from folium.plugins import Search, MeasureControl, Fullscreen, MousePosition

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

def calcular_estadisticas_zonas(gdf):
    """
    Calcula estadísticas sobre las zonas (área, perímetro, etc.)
    
    Args:
        gdf: GeoDataFrame con las zonas
    
    Returns:
        GeoDataFrame con estadísticas adicionales
    """
    # Calcular área aproximada en km²
    gdf['area_km2'] = gdf.geometry.area * 111 * 111  # Conversión aproximada de grados a km²
    
    # Calcular perímetro aproximado en km
    gdf['perimetro_km'] = gdf.geometry.boundary.length * 111  # Conversión aproximada de grados a km
    
    # Calcular compacidad (ratio área/perímetro²)
    gdf['compacidad'] = (4 * 3.14159 * gdf['area_km2']) / (gdf['perimetro_km'] ** 2)
    
    # Extraer municipio
    gdf['municipio'] = gdf['name'].apply(lambda x: x.split('-')[0].strip() if '-' in x else x)
    
    return gdf

def visualizar_geojson_interactivo(geojson_file):
    """
    Crea un mapa interactivo avanzado a partir de un archivo GeoJSON
    
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
    
    # Calcular estadísticas
    gdf = calcular_estadisticas_zonas(gdf)
    
    # Crear un mapa centrado en los datos
    bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2
    
    # Crear mapa base
    m = folium.Map(location=[center_lat, center_lon], zoom_start=9, 
                   tiles='CartoDB positron')
    
    # Añadir diferentes capas base
    folium.TileLayer('CartoDB dark_matter', name='CartoDB Dark').add_to(m)
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
    folium.TileLayer('Stamen Terrain', name='Stamen Terrain').add_to(m)
    folium.TileLayer('Stamen Toner', name='Stamen Toner').add_to(m)
    
    # Agrupar por municipio para asignar colores similares
    municipios = {}
    for idx, row in gdf.iterrows():
        municipio = row['municipio']
        if municipio not in municipios:
            municipios[municipio] = []
        municipios[municipio].append(idx)
    
    # Generar colores por municipio
    colores_municipios = {}
    paleta = generar_paleta_colores(len(municipios))
    for i, municipio in enumerate(municipios.keys()):
        colores_municipios[municipio] = paleta[i]
    
    # Crear grupos de características para organizarlas
    feature_groups = {}
    
    # Colormap para compacidad
    compacidad_min = gdf['compacidad'].min()
    compacidad_max = gdf['compacidad'].max()
    colormap = cm.LinearColormap(
        ['red', 'yellow', 'green'], 
        vmin=compacidad_min, 
        vmax=compacidad_max,
        caption='Índice de Compacidad'
    )
    
    # Añadir cada zona al mapa
    for idx, row in gdf.iterrows():
        nombre = row['name']
        municipio = row['municipio']
        area_km2 = row['area_km2']
        perimetro_km = row['perimetro_km']
        compacidad = row['compacidad']
        
        # Colorear por municipio con variación
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
        
        # Determinar el grupo al que pertenece (por municipio)
        if municipio not in feature_groups:
            feature_groups[municipio] = folium.FeatureGroup(name=f"Municipio: {municipio}")
            feature_groups[municipio].add_to(m)
        
        # Crear HTML personalizado para el popup
        popup_html = f"""
        <div style="width: 300px; max-height: 300px; overflow-y: auto;">
            <h4 style="text-align: center; font-weight: bold;">{nombre}</h4>
            <hr>
            <table style="width: 100%;">
                <tr>
                    <td style="font-weight: bold;">Municipio:</td>
                    <td>{municipio}</td>
                </tr>
                <tr>
                    <td style="font-weight: bold;">Área:</td>
                    <td>{area_km2:.2f} km²</td>
                </tr>
                <tr>
                    <td style="font-weight: bold;">Perímetro:</td>
                    <td>{perimetro_km:.2f} km</td>
                </tr>
                <tr>
                    <td style="font-weight: bold;">Compacidad:</td>
                    <td>{compacidad:.3f}</td>
                </tr>
                <tr>
                    <td style="font-weight: bold;">ID:</td>
                    <td>{row['id']}</td>
                </tr>
            </table>
            <hr>
            <div style="text-align: center; font-size: 0.9em; font-style: italic;">
                Haz clic en cualquier parte del mapa para cerrar
            </div>
        </div>
        """
        
        # Crear popup personalizado
        popup = folium.Popup(folium.Html(popup_html, script=True), max_width=350)
        
        # Añadir la zona al mapa
        zona = folium.GeoJson(
            row.geometry,
            name=nombre,
            style_function=lambda x, color=color: {
                'fillColor': color,
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.6
            },
            highlight_function=lambda x: {
                'weight': 3,
                'color': 'white',
                'fillOpacity': 0.8
            },
            tooltip=nombre,
            popup=popup
        )
        zona.add_to(feature_groups[municipio])
        
        # Almacenar para la función de búsqueda
        zona.properties = {
            'name': nombre,
            'municipio': municipio,
            'area': f"{area_km2:.2f}",
            'search_text': f"{nombre} {municipio}"
        }
    
    # Añadir control de búsqueda
    search = Search(
        layer=feature_groups,
        geom_type='Polygon',
        placeholder='Buscar zona o municipio',
        collapsed=False,
        search_label='name',
        search_zoom=13
    )
    m.add_child(search)
    
    # Añadir controles adicionales
    m.add_child(MeasureControl(position='topright', primary_length_unit='kilometers'))
    m.add_child(Fullscreen(position='topright'))
    
    # Añadir coordenadas del cursor
    MousePosition().add_to(m)
    
    # Añadir leyenda de compacidad
    m.add_child(colormap)
    
    # Añadir control de capas
    folium.LayerControl(collapsed=False).add_to(m)
    
    # Sanitizar el nombre de la región para el nombre de archivo
    region_name_sanitizado = sanitizar_nombre_archivo(region_name)
    
    # Obtener directorio y nombre base del archivo de entrada
    input_dir = os.path.dirname(geojson_file)
    input_base = os.path.basename(geojson_file).split('.')[0]
    
    # Añadir información de metadatos
    title_html = f'''
    <h3 align="center" style="font-size:16px"><b>{region_name} - Mapa de Zonas</b></h3>
    <p align="center" style="font-size:12px">Total de zonas: {len(gdf)} | Total de municipios: {len(municipios)}</p>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Guardar el mapa en un archivo HTML
    output_html = os.path.join(input_dir, f"{input_base}_mapa_interactivo.html")
    print(f"Guardando mapa en: {output_html}")
    m.save(output_html)
    
    print(f"Mapa interactivo creado exitosamente. Abre {output_html} en tu navegador para visualizarlo.")
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
        visualizar_geojson_interactivo(geojson_file)
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
                visualizar_geojson_interactivo(geojson_files[seleccion-1])
            else:
                print("Selección no válida.")
        except ValueError:
            print("Por favor, introduce un número válido.")

if __name__ == "__main__":
    main() 