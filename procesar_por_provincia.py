import os
import geopandas as gpd
import json
from shapely.geometry import mapping
import uuid
import sys

def obtener_provincias(input_shapefile):
    """
    Obtiene la lista de provincias disponibles en el shapefile
    
    Args:
        input_shapefile: Ruta al shapefile de municipios
    
    Returns:
        Lista de códigos de provincia
    """
    gdf = gpd.read_file(input_shapefile)
    if 'CODNUT3' in gdf.columns:
        # Los códigos NUT3 corresponden a provincias en España
        return sorted(gdf['CODNUT3'].unique())
    elif 'NATCODE' in gdf.columns:
        # NATCODE también puede contener códigos de provincia
        # Los códigos de provincia en España son de 2 dígitos
        return sorted(gdf['NATCODE'].apply(lambda x: x[:2]).unique())
    else:
        print("No se encontraron columnas para identificar provincias")
        return []

def procesar_por_provincia(input_shapefile, output_dir, codigo_provincia):
    """
    Procesa un shapefile de municipios filtrando por provincia y lo convierte en un GeoJSON
    
    Args:
        input_shapefile: Ruta al shapefile de municipios
        output_dir: Directorio donde se guardarán los archivos GeoJSON
        codigo_provincia: Código de la provincia a procesar
    """
    # Crear directorio de salida si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Leer el shapefile con geopandas
    print(f"Leyendo shapefile: {input_shapefile}")
    gdf = gpd.read_file(input_shapefile)
    
    # Filtrar por provincia
    if 'CODNUT3' in gdf.columns:
        provincia_gdf = gdf[gdf['CODNUT3'] == codigo_provincia]
        nombre_provincia = provincia_gdf['NAMEUNIT'].iloc[0] if not provincia_gdf.empty and 'NAMEUNIT' in provincia_gdf.columns else f"Provincia_{codigo_provincia}"
    elif 'NATCODE' in gdf.columns:
        provincia_gdf = gdf[gdf['NATCODE'].apply(lambda x: x[:2]) == codigo_provincia]
        nombre_provincia = provincia_gdf['NAMEUNIT'].iloc[0] if not provincia_gdf.empty and 'NAMEUNIT' in provincia_gdf.columns else f"Provincia_{codigo_provincia}"
    else:
        print("No se encontraron columnas para filtrar por provincia")
        return
    
    if provincia_gdf.empty:
        print(f"No se encontraron municipios para la provincia con código {codigo_provincia}")
        return
    
    # Asegurarse de que está en el sistema de coordenadas correcto (WGS84)
    if provincia_gdf.crs != "EPSG:4326":
        print(f"Convirtiendo de {provincia_gdf.crs} a EPSG:4326 (WGS84)")
        provincia_gdf = provincia_gdf.to_crs("EPSG:4326")
    
    # Crear la estructura del GeoJSON
    geojson_data = {
        "type": "FeatureCollection",
        "region_name": nombre_provincia,
        "features": []
    }
    
    # Procesar cada municipio
    print(f"Procesando {len(provincia_gdf)} municipios de la provincia {nombre_provincia}...")
    for idx, row in provincia_gdf.iterrows():
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
    output_geojson = os.path.join(output_dir, f"municipios_{nombre_provincia.lower().replace(' ', '_')}.geojson")
    print(f"Guardando GeoJSON en: {output_geojson}")
    with open(output_geojson, 'w', encoding='utf-8') as f:
        json.dump(geojson_data, f, ensure_ascii=False, indent=4)
    
    print(f"Archivo GeoJSON creado exitosamente. Contiene {len(geojson_data['features'])} distritos.")

def main():
    # Definir las rutas de los archivos
    input_shapefile = os.path.join("lineas_limite", "SHP_ETRS89", "recintos_municipales_inspire_peninbal_etrs89", 
                                  "recintos_municipales_inspire_peninbal_etrs89.shp")
    
    # Verificar que el archivo existe
    if not os.path.exists(input_shapefile):
        print(f"El archivo {input_shapefile} no existe. Asegúrate de tener la estructura de carpetas correcta.")
        return
    
    # Directorio para guardar los archivos GeoJSON
    output_dir = "geojson_municipios"
    
    # Si se proporciona un código de provincia como argumento, procesar solo esa provincia
    if len(sys.argv) > 1:
        codigo_provincia = sys.argv[1]
        procesar_por_provincia(input_shapefile, output_dir, codigo_provincia)
    else:
        # Obtener lista de provincias
        provincias = obtener_provincias(input_shapefile)
        print(f"Provincias disponibles: {provincias}")
        
        # Procesar cada provincia
        for codigo_provincia in provincias:
            procesar_por_provincia(input_shapefile, output_dir, codigo_provincia)
    
    print("Proceso completado.")

if __name__ == "__main__":
    main() 