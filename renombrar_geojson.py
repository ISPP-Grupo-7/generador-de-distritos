import os
import shutil
import re

def renombrar_archivos_geojson(directorio_origen, directorio_destino=None):
    """
    Renombra los archivos GeoJSON eliminando los códigos con guiones bajos.
    
    Args:
        directorio_origen: Ruta del directorio que contiene los archivos GeoJSON originales.
        directorio_destino: Ruta del directorio donde se guardarán los archivos renombrados.
                            Si es None, se sobrescribirán los archivos originales.
    """
    # Verificar que el directorio de origen existe
    if not os.path.exists(directorio_origen):
        print(f"Error: El directorio de origen '{directorio_origen}' no existe.")
        return False
    
    # Crear directorio de destino si no existe y es diferente al de origen
    if directorio_destino and not os.path.exists(directorio_destino):
        os.makedirs(directorio_destino)
        print(f"Directorio de destino '{directorio_destino}' creado.")
    
    # Obtener la lista de archivos en el directorio
    archivos = [f for f in os.listdir(directorio_origen) if f.endswith('.geojson')]
    
    if not archivos:
        print(f"No se encontraron archivos GeoJSON en '{directorio_origen}'.")
        return False
    
    print(f"Procesando {len(archivos)} archivos GeoJSON...")
    archivos_procesados = 0
    
    for archivo in archivos:
        # Extraer el nombre sin el código (todo lo que viene después del primer guion bajo)
        match = re.search(r'^\d+_(.+\.geojson)$', archivo)
        if match:
            nuevo_nombre = match.group(1)
            
            ruta_origen = os.path.join(directorio_origen, archivo)
            
            if directorio_destino:
                ruta_destino = os.path.join(directorio_destino, nuevo_nombre)
                shutil.copy2(ruta_origen, ruta_destino)
                print(f"Archivo copiado y renombrado: {archivo} -> {nuevo_nombre}")
                archivos_procesados += 1
            else:
                ruta_destino = os.path.join(directorio_origen, nuevo_nombre)
                # Verificar si el archivo de destino ya existe
                if os.path.exists(ruta_destino) and ruta_origen != ruta_destino:
                    print(f"Advertencia: El archivo {nuevo_nombre} ya existe. No se sobrescribirá.")
                else:
                    os.rename(ruta_origen, ruta_destino)
                    print(f"Archivo renombrado: {archivo} -> {nuevo_nombre}")
                    archivos_procesados += 1
        else:
            print(f"El archivo '{archivo}' no coincide con el patrón 'código_nombre.geojson'. Se mantendrá igual.")
    
    print(f"\nResumen: {archivos_procesados} de {len(archivos)} archivos procesados.")
    
    if directorio_destino:
        print(f"Los archivos renombrados se encuentran en: {directorio_destino}")
    
    return archivos_procesados > 0

if __name__ == "__main__":
    directorio_geojson = "geojson_comunidades_zonas"
    
    if not os.path.exists(directorio_geojson):
        print(f"Advertencia: El directorio '{directorio_geojson}' no existe.")
        opcion = input("¿Desea especificar un directorio diferente? (s/n): ")
        if opcion.lower() == 's':
            directorio_geojson = input("Introduzca la ruta del directorio: ")
        else:
            print("Operación cancelada.")
            exit()
    
    print("\n1. Sobrescribir archivos originales")
    print("2. Crear copias renombradas en un nuevo directorio")
    
    try:
        opcion = int(input("\nSeleccione una opción (1/2): "))
        
        if opcion == 1:
            # Opción 1: Sobrescribir archivos originales
            confirmacion = input("¿Está seguro que desea sobrescribir los archivos originales? (s/n): ")
            if confirmacion.lower() == 's':
                renombrar_archivos_geojson(directorio_geojson)
            else:
                print("Operación cancelada.")
        elif opcion == 2:
            # Opción 2: Crear copias renombradas en un nuevo directorio
            directorio_destino = "geojson_comunidades_renombradas"
            directorio_personalizado = input(f"Directorio de destino [{directorio_destino}]: ")
            if directorio_personalizado:
                directorio_destino = directorio_personalizado
            
            renombrar_archivos_geojson(directorio_geojson, directorio_destino)
        else:
            print("Opción no válida.")
    except ValueError:
        print("Por favor, introduzca un número válido.")
    
    print("\nProceso completado. Ahora puede ejecutar unir_geojson.py para unir todos los archivos.") 