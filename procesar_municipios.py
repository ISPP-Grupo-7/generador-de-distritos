import os
import geopandas as gpd
import json
from shapely.geometry import mapping
import uuid

def procesar_municipios(input_shapefile, output_geojson, region_name):
    """
    Procesa un shapefile de municipios y lo convierte en un GeoJSON con la estructura solicitada
    
    Args:
        input_shapefile: Ruta al shapefile de municipios
        output_geojson: Ruta donde se guardará el archivo GeoJSON
        region_name: Nombre de la región para incluir en el GeoJSON
    """
    # Leer el shapefile con geopandas
    print(f"Leyendo shapefile: {input_shapefile}")
    gdf = gpd.read_file(input_shapefile)
    
    # Asegurarse de que está en el sistema de coordenadas correcto (WGS84)
    if gdf.crs != "EPSG:4326":
        print(f"Convirtiendo de {gdf.crs} a EPSG:4326 (WGS84)")
        gdf = gdf.to_crs("EPSG:4326")
    
    # Crear la estructura del GeoJSON
    geojson_data = {
        "type": "FeatureCollection",
        "region_name": region_name,
        "features": []
    }
    
    # Procesar cada municipio
    print(f"Procesando {len(gdf)} municipios...")
    for idx, row in gdf.iterrows():
        # Extraer propiedades del municipio
        name = row.get('NAMEUNIT', f"Distrito {idx + 1}")
        
        # Extraer la geometría
        geometry = mapping(row.geometry)
        
        # Crear un feature GeoJSON
        feature = {
            "type": "Feature",
            "properties": {
                "id": str(uuid.uuid4()),  # Generar un ID único
                "name": name,
                "description": "",
                "isUnlocked": False
            },
            "geometry": geometry
        }
        
        # Añadir el feature a la colección
        geojson_data["features"].append(feature)
    
    # Guardar el GeoJSON
    print(f"Guardando GeoJSON en: {output_geojson}")
    with open(output_geojson, 'w', encoding='utf-8') as f:
        json.dump(geojson_data, f, ensure_ascii=False, indent=4)
    
    print(f"Archivo GeoJSON creado exitosamente. Contiene {len(geojson_data['features'])} distritos.")

if __name__ == "__main__":
    # Definir las rutas de los archivos
    input_shapefile = os.path.join("lineas_limite", "SHP_ETRS89", "recintos_municipales_inspire_peninbal_etrs89", 
                                  "recintos_municipales_inspire_peninbal_etrs89.shp")
    
    # Verificar que el archivo existe
    if not os.path.exists(input_shapefile):
        print(f"El archivo {input_shapefile} no existe. Asegúrate de tener la estructura de carpetas correcta.")
        exit(1)
    
    # Procesar para toda España
    output_geojson = "municipios_espana.geojson"
    procesar_municipios(input_shapefile, output_geojson, "España")
    
    print("Proceso completado.") 