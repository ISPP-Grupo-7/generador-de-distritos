import os
import geopandas as gpd
import json
import uuid
from shapely.geometry import mapping, shape, Polygon, MultiPolygon
import numpy as np
from tqdm import tqdm
import math
import voronoi_utils
import sys
import matplotlib.pyplot as plt

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
        # Generar puntos aleatorios dentro del polígono para usar como semillas
        puntos = voronoi_utils.generar_puntos_dentro_poligono(poligono, num_divisiones)
        
        # Si no hay suficientes puntos, reducir el número de divisiones
        if len(puntos) < num_divisiones:
            print(f"Advertencia: No se pueden generar {num_divisiones} puntos en el polígono. Se usarán {len(puntos)} divisiones.")
            num_divisiones = len(puntos)
        
        if num_divisiones <= 1:
            return [poligono]
        
        # Generar diagrama de Voronoi
        return voronoi_utils.poligonos_voronoi(puntos, poligono)
    except Exception as e:
        print(f"Error al dividir polígono: {e}")
        # En caso de error, devolver el polígono original
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
    # Filtrar la comunidad autónoma
    ccaa = gdf_ccaa[gdf_ccaa['NATCODE'] == codigo_ccaa]
    
    if ccaa.empty:
        print(f"No se encontró la comunidad autónoma con código {codigo_ccaa}")
        return
    
    nombre_ccaa = ccaa.iloc[0]['NAMEUNIT']
    print(f"\nProcesando comunidad autónoma: {nombre_ccaa} (código {codigo_ccaa})")
    
    # Filtrar municipios de esta comunidad autónoma
    # Los códigos NATCODE de municipios comienzan con el código de la comunidad autónoma
    municipios_ccaa = gdf_municipios[gdf_municipios['NATCODE'].str.startswith(codigo_ccaa[:2])]
    
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
    for idx, municipio in tqdm(municipios_ccaa.iterrows(), total=len(municipios_ccaa), desc="Procesando municipios"):
        # Extraer nombre y geometría del municipio
        nombre_municipio = municipio['NAMEUNIT']
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
                
                # Añadir identificador a cada distrito
                for j, distrito in enumerate(distritos_poligono):
                    distritos.append((f"{nombre_municipio} - Parte {i+1} - Distrito {j+1}", distrito))
        else:
            if metodo_division == "voronoi":
                distritos_poligono = dividir_poligono_voronoi(geometria, num_distritos)
            else:
                distritos_poligono = dividir_poligono_grid(geometria, num_distritos)
            
            # Añadir identificador a cada distrito
            for j, distrito in enumerate(distritos_poligono):
                distritos.append((f"{nombre_municipio} - Distrito {j+1}", distrito))
        
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
    
    # Guardar el GeoJSON
    filename = f"{codigo_ccaa}_{nombre_ccaa.lower().replace(' ', '_')}.geojson"
    output_geojson = os.path.join(output_dir, filename)
    print(f"Guardando GeoJSON en: {output_geojson}")
    with open(output_geojson, 'w', encoding='utf-8') as f:
        json.dump(geojson_data, f, ensure_ascii=False, indent=2)
    
    print(f"Archivo GeoJSON creado exitosamente. Contiene {total_distritos} distritos.")
    
    # Mostrar visualización
    if visualizar:
        plt.title(f"Distritos de {nombre_ccaa}")
        plt.savefig(os.path.join(output_dir, f"{codigo_ccaa}_{nombre_ccaa.lower().replace(' ', '_')}.png"))
        plt.close()

def main():
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
    output_dir = "geojson_comunidades_distritos"
    os.makedirs(output_dir, exist_ok=True)
    
    # Método de división (voronoi o grid)
    metodo_division = "voronoi"
    if len(sys.argv) > 1 and sys.argv[1] in ["voronoi", "grid"]:
        metodo_division = sys.argv[1]
    
    print(f"Usando método de división: {metodo_division}")
    
    # Obtener comunidades autónomas
    gdf_ccaa = obtener_comunidades_autonomas(shapefile_ccaa)
    gdf_municipios = obtener_municipios(shapefile_municipios)
    
    # Lista de comunidades autónomas
    codigos_ccaa = gdf_ccaa['NATCODE'].unique()
    
    # Si se proporciona un código de comunidad autónoma como argumento, procesar solo esa comunidad
    if len(sys.argv) > 1 and sys.argv[1] not in ["voronoi", "grid"]:
        codigo_ccaa = sys.argv[1]
        if codigo_ccaa in codigos_ccaa:
            procesar_comunidad_autonoma(gdf_ccaa, gdf_municipios, codigo_ccaa, output_dir, metodo_division)
        else:
            print(f"No se encontró la comunidad autónoma con código {codigo_ccaa}")
            print(f"Comunidades disponibles: {codigos_ccaa}")
    else:
        # Procesar todas las comunidades autónomas
        for codigo_ccaa in codigos_ccaa:
            procesar_comunidad_autonoma(gdf_ccaa, gdf_municipios, codigo_ccaa, output_dir, metodo_division)
    
    print("Proceso completado.")

if __name__ == "__main__":
    main() 