import json
import sys
import os
import glob

def contar_zonas_geojson(geojson_file):
    """
    Cuenta el número de zonas (features) en un archivo GeoJSON.
    
    Args:
        geojson_file: Ruta al archivo GeoJSON
    
    Returns:
        Número de zonas en el archivo
    """
    try:
        with open(geojson_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            num_zonas = len(data['features'])
            return num_zonas
    except Exception as e:
        print(f"Error al leer el archivo {geojson_file}: {e}")
        return 0

def analizar_directorio_geojson(directorio="geojson_comunidades_zonas"):
    """
    Analiza todos los archivos GeoJSON en un directorio y cuenta las zonas.
    
    Args:
        directorio: Directorio donde buscar archivos GeoJSON
    """
    if not os.path.exists(directorio):
        print(f"El directorio {directorio} no existe.")
        return
    
    geojson_files = glob.glob(os.path.join(directorio, "*.geojson"))
    
    if not geojson_files:
        print(f"No se encontraron archivos GeoJSON en {directorio}.")
        return
    
    total_zonas = 0
    resultados = []
    
    print(f"\nAnálisis de zonas en archivos GeoJSON de {directorio}:")
    print(f"\n{'='*80}")
    print(f"{'Archivo':<60} | {'Zonas':>10}")
    print(f"{'-'*80}")
    
    for archivo in sorted(geojson_files):
        nombre_archivo = os.path.basename(archivo)
        num_zonas = contar_zonas_geojson(archivo)
        total_zonas += num_zonas
        resultados.append((nombre_archivo, num_zonas))
        
        # Imprimir resultado
        print(f"{nombre_archivo:<60} | {num_zonas:>10,}")
    
    print(f"{'-'*80}")
    print(f"{'TOTAL':<60} | {total_zonas:>10,}")
    print(f"{'='*80}")
    
    return total_zonas, resultados

def main():
    """Función principal."""
    # Si se proporciona un archivo como argumento, analizar solo ese archivo
    if len(sys.argv) > 1:
        archivo = sys.argv[1]
        if os.path.exists(archivo):
            num_zonas = contar_zonas_geojson(archivo)
            print(f"El archivo {archivo} contiene {num_zonas:,} zonas.")
        else:
            print(f"El archivo {archivo} no existe.")
    # Si no, analizar todos los archivos en el directorio predeterminado
    else:
        analizar_directorio_geojson()

if __name__ == "__main__":
    main() 