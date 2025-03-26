import os
import json
from tqdm import tqdm
import sys

def unir_archivos_geojson(directorio, archivo_salida):
    """
    Une todos los archivos GeoJSON en un solo archivo.
    
    Args:
        directorio: Ruta del directorio con los archivos GeoJSON
        archivo_salida: Nombre del archivo GeoJSON de salida
    """
    # Estructura para el GeoJSON unificado
    geojson_unificado = {
        "type": "FeatureCollection",
        "features": []
    }
    
    # Verificar si el directorio existe
    if not os.path.exists(directorio):
        print(f"Error: El directorio {directorio} no existe.")
        if directorio == "geojson_comunidades_renombradas":
            print("Primero debe ejecutar renombrar_geojson.py para crear el directorio.")
        return False
    
    # Obtener todos los archivos GeoJSON
    archivos = [f for f in os.listdir(directorio) if f.endswith('.geojson')]
    
    if len(archivos) == 0:
        print(f"No se encontraron archivos GeoJSON en {directorio}.")
        return False
    
    print(f"Uniendo {len(archivos)} archivos GeoJSON...")
    
    # Procesar cada archivo
    total_caracteristicas = 0
    for archivo in tqdm(archivos):
        ruta_completa = os.path.join(directorio, archivo)
        
        try:
            # Cargar el archivo GeoJSON
            with open(ruta_completa, 'r', encoding='utf-8') as f:
                datos = json.load(f)
            
            # Extraer nombre de la comunidad del nombre del archivo
            nombre_comunidad = archivo.replace('.geojson', '')
            
            # Añadir las características al GeoJSON unificado
            if 'features' in datos and len(datos['features']) > 0:
                # Añadir propiedad de origen a cada característica
                for feature in datos['features']:
                    if 'properties' not in feature:
                        feature['properties'] = {}
                    feature['properties']['origen'] = nombre_comunidad
                
                geojson_unificado['features'].extend(datos['features'])
                num_caracteristicas = len(datos['features'])
                total_caracteristicas += num_caracteristicas
                print(f"  - Añadido {num_caracteristicas} elementos de {nombre_comunidad}")
            else:
                print(f"Advertencia: No se encontraron características en {archivo} o formato inesperado.")
        
        except Exception as e:
            print(f"Error al procesar {archivo}: {str(e)}")
    
    # Verificar si hay características
    if len(geojson_unificado['features']) == 0:
        print("No se encontraron características en los archivos GeoJSON.")
        return False
    
    # Guardar el GeoJSON unificado
    print(f"Guardando {total_caracteristicas} características en total...")
    with open(archivo_salida, 'w', encoding='utf-8') as f:
        json.dump(geojson_unificado, f)
    
    print(f"GeoJSON unificado guardado en: {archivo_salida}")
    return True

if __name__ == "__main__":
    # Determinar qué directorio usar
    directorio_original = "geojson_comunidades_zonas"
    directorio_renombrado = "geojson_comunidades_renombradas"
    archivo_salida = "espana_completa.geojson"
    
    if os.path.exists(directorio_renombrado) and len(os.listdir(directorio_renombrado)) > 0:
        print(f"Usando directorio de archivos renombrados: {directorio_renombrado}")
        directorio_geojson = directorio_renombrado
    elif os.path.exists(directorio_original):
        print(f"Directorio renombrado no encontrado o vacío, usando directorio original: {directorio_original}")
        directorio_geojson = directorio_original
    else:
        print("No se encontró ningún directorio con archivos GeoJSON.")
        sys.exit(1)
    
    # Unir archivos GeoJSON
    unir_archivos_geojson(directorio_geojson, archivo_salida)
    
    print("\nProceso completado. Para visualizar los datos, ejecute visualizar_comunidades.py") 