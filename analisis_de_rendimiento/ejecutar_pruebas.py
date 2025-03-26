import os
import subprocess
import shutil
import time
import glob
import re
from datetime import datetime

# Configuración de las pruebas
CONFIGS = [
    {"nombre": "CPU-Preciso-Voronoi", "params": ["cpu", "preciso", "voronoi"]},
    {"nombre": "CPU-Preciso-Grid", "params": ["cpu", "preciso", "grid"]},
    {"nombre": "CPU-Rapido-Voronoi", "params": ["cpu", "rapido", "voronoi"]},
    {"nombre": "CPU-Rapido-Grid", "params": ["cpu", "rapido", "grid"]},
    {"nombre": "GPU-Preciso-Voronoi", "params": ["gpu", "preciso", "voronoi"]},
    {"nombre": "GPU-Preciso-Grid", "params": ["gpu", "preciso", "grid"]},
    {"nombre": "GPU-Rapido-Voronoi", "params": ["gpu", "rapido", "voronoi"]},
    {"nombre": "GPU-Rapido-Grid", "params": ["gpu", "rapido", "grid"]},
]

# Comunidades autónomas pequeñas para pruebas rápidas
COMUNIDADES_PRUEBA = [
    "34170000000",  # La Rioja
    "34060000000",  # Cantabria
    "34180000000",  # Ceuta
    "34190000000",  # Melilla
]

# Carpeta para resultados
RESULTADOS_DIR = "analisis_de_rendimiento/resultados/geojson"
LOGS_DIR = "analisis_de_rendimiento/resultados/logs"

def setup_directorios():
    """Crea las carpetas necesarias para guardar los resultados."""
    os.makedirs(RESULTADOS_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    print(f"Directorios de resultados creados: {RESULTADOS_DIR}, {LOGS_DIR}")

def limpiar_directorio_geojson():
    """Limpia el directorio de archivos GeoJSON antes de cada prueba."""
    geojson_dir = "geojson_comunidades_zonas"
    if os.path.exists(geojson_dir):
        for archivo in os.listdir(geojson_dir):
            if archivo.endswith(".geojson"):
                os.remove(os.path.join(geojson_dir, archivo))
        print("Directorio GeoJSON limpiado.")
    else:
        os.makedirs(geojson_dir, exist_ok=True)
        print("Directorio GeoJSON creado.")

def guardar_archivos_geojson(config_nombre, comunidad):
    """
    Copia los archivos GeoJSON generados a la carpeta de resultados
    con un prefijo que identifica la configuración.
    """
    geojson_dir = "geojson_comunidades_zonas"
    geojson_files = glob.glob(os.path.join(geojson_dir, f"{comunidad}_*.geojson"))
    
    if not geojson_files:
        print(f"No se encontraron archivos GeoJSON para la comunidad {comunidad}")
        return []
    
    archivos_copiados = []
    for geojson_file in geojson_files:
        nombre_archivo = os.path.basename(geojson_file)
        nuevo_nombre = f"{config_nombre}_{nombre_archivo}"
        nuevo_path = os.path.join(RESULTADOS_DIR, nuevo_nombre)
        
        try:
            shutil.copy2(geojson_file, nuevo_path)
            archivos_copiados.append(nuevo_path)
            print(f"Archivo copiado: {nuevo_path}")
        except Exception as e:
            print(f"Error al copiar {geojson_file}: {e}")
    
    return archivos_copiados

def ejecutar_prueba(config, comunidad):
    """
    Ejecuta main.py con los parámetros especificados,
    espera a que termine y guarda los resultados.
    """
    limpiar_directorio_geojson()
    
    print(f"\n{'='*80}")
    print(f"Ejecutando prueba: {config['nombre']} - Comunidad: {comunidad}")
    print(f"{'='*80}")
    
    # Construir el comando
    comando = ["python", "main.py"] + config["params"] + [comunidad]
    print(f"Comando: {' '.join(comando)}")
    
    # Iniciar temporizador
    tiempo_inicio = time.time()
    
    # Log file para guardar la salida
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOGS_DIR, f"log_{config['nombre']}_{comunidad}_{timestamp}.txt")
    
    try:
        # Ejecutar comando y guardar salida en archivo log
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"Comando: {' '.join(comando)}\n")
            f.write(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Ejecutar el comando
            proceso = subprocess.Popen(
                comando,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Capturar salida en tiempo real
            for line in proceso.stdout:
                print(line, end='')  # Mostrar en consola
                f.write(line)  # Guardar en archivo log
            
            # Capturar errores
            for line in proceso.stderr:
                print(f"ERROR: {line}", end='')
                f.write(f"ERROR: {line}")
            
            # Esperar a que termine
            proceso.wait()
            
            # Guardar código de salida
            codigo_salida = proceso.returncode
            f.write(f"\nCódigo de salida: {codigo_salida}\n")
        
        # Calcular tiempo total
        tiempo_total = time.time() - tiempo_inicio
        print(f"Tiempo total: {tiempo_total:.2f} segundos")
        
        # Guardar archivos GeoJSON generados
        archivos_guardados = guardar_archivos_geojson(config['nombre'], comunidad)
        
        return {
            "config": config['nombre'],
            "comunidad": comunidad,
            "tiempo_total": tiempo_total,
            "codigo_salida": codigo_salida,
            "log_file": log_file,
            "archivos_guardados": archivos_guardados
        }
    
    except Exception as e:
        print(f"Error al ejecutar prueba: {e}")
        return {
            "config": config['nombre'],
            "comunidad": comunidad,
            "tiempo_total": time.time() - tiempo_inicio,
            "codigo_salida": -1,
            "log_file": log_file,
            "archivos_guardados": []
        }

def main():
    """Función principal que ejecuta todas las pruebas secuencialmente."""
    print("Iniciando ejecución de pruebas...")
    
    # Crear directorios para resultados
    setup_directorios()
    
    # Lista para almacenar resultados
    resultados = []
    
    # Ejecutar cada prueba para cada comunidad
    for comunidad in COMUNIDADES_PRUEBA:
        for config in CONFIGS:
            resultado = ejecutar_prueba(config, comunidad)
            resultados.append(resultado)
    
    # Guardar resumen de ejecuciones
    resumen_file = os.path.join(LOGS_DIR, f"resumen_ejecucion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    with open(resumen_file, 'w', encoding='utf-8') as f:
        f.write("RESUMEN DE EJECUCIONES\n")
        f.write("=====================\n\n")
        
        for res in resultados:
            f.write(f"Config: {res['config']}\n")
            f.write(f"Comunidad: {res['comunidad']}\n")
            f.write(f"Tiempo: {res['tiempo_total']:.2f} segundos\n")
            f.write(f"Código de salida: {res['codigo_salida']}\n")
            f.write(f"Log: {res['log_file']}\n")
            f.write(f"Archivos guardados: {len(res['archivos_guardados'])}\n")
            f.write("\n" + "-"*50 + "\n\n")
    
    print(f"\nEjecución completa. Resumen guardado en: {resumen_file}")
    print(f"Se han guardado los archivos GeoJSON en: {RESULTADOS_DIR}")
    print(f"Los logs detallados se encuentran en: {LOGS_DIR}")
    
    # Sugerir siguiente paso
    print("\nPara realizar el análisis comparativo, ejecute:")
    print("python analisis_de_rendimiento/comparar_resultados.py")

if __name__ == "__main__":
    main() 