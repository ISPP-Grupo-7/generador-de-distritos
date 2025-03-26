import os
import sys
import shutil
import glob
import subprocess
import argparse
from datetime import datetime
import time

# Rutas principales
RESULTADOS_DIR = os.path.join("analisis_de_rendimiento", "resultados")
GEOJSON_DIR = os.path.join(RESULTADOS_DIR, "geojson")
LOGS_DIR = os.path.join(RESULTADOS_DIR, "logs")
ANALISIS_DIR = os.path.join(RESULTADOS_DIR, "analisis")

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

# Todas las comunidades autónomas
TODAS_COMUNIDADES = [
    "34010000000",  # Andalucía
    "34020000000",  # Aragón
    "34030000000",  # Principado de Asturias
    "34040000000",  # Islas Baleares
    "34060000000",  # Cantabria
    "34070000000",  # Castilla y León
    "34080000000",  # Castilla-La Mancha
    "34090000000",  # Cataluña
    "34100000000",  # Comunidad Valenciana
    "34110000000",  # Extremadura
    "34120000000",  # Galicia
    "34130000000",  # Comunidad de Madrid
    "34140000000",  # Región de Murcia
    "34150000000",  # Comunidad Foral de Navarra
    "34160000000",  # País Vasco
    "34170000000",  # La Rioja
    "34180000000",  # Ceuta
    "34190000000",  # Melilla
]

def setup_directorios():
    """Crea las carpetas necesarias para guardar los resultados."""
    os.makedirs(GEOJSON_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs(ANALISIS_DIR, exist_ok=True)
    print(f"Directorios de resultados creados en {RESULTADOS_DIR}")

def ejecutar_paso(comando, descripcion):
    """Ejecuta un comando de sistema y muestra el resultado."""
    print(f"\n{'='*80}")
    print(f"{descripcion}")
    print(f"Comando: {comando}")
    print(f"{'='*80}")
    
    try:
        resultado = subprocess.run(
            comando,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        print(resultado.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar el comando: {e}")
        print(f"Salida de error: {e.stderr}")
        return False

def ejecutar_prueba(config, comunidad):
    """Ejecuta una prueba con la configuración y comunidad específicas."""
    # Limpiar directorio geojson
    for archivo in glob.glob("../geojson_comunidades_zonas/*.geojson"):
        try:
            os.remove(archivo)
            print(f"Eliminado archivo: {archivo}")
        except Exception as e:
            print(f"Error al eliminar {archivo}: {e}")
    
    # Registrar inicio
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOGS_DIR, f"log_{config['nombre']}_{comunidad}_{timestamp}.txt")
    
    # Construir comando - ir a la carpeta raíz para ejecutar
    parametros = " ".join(config["params"])
    comando = f'cd .. && py main.py {parametros} {comunidad}'
    
    # Ejecutar comando y guardar salida
    print(f"\n{'='*80}")
    print(f"Ejecutando prueba: {config['nombre']} - Comunidad: {comunidad}")
    print(f"{'='*80}")
    print(f"Comando: {comando}")
    
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"Comando: {comando}\n")
        f.write(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Iniciar cronómetro
        tiempo_inicio = time.time()
        
        proceso = subprocess.Popen(
            comando,
            shell=True,
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
        
        # Calcular tiempo total
        tiempo_total = time.time() - tiempo_inicio
        horas, resto = divmod(tiempo_total, 3600)
        minutos, segundos = divmod(resto, 60)
        f.write(f"\nTiempo total de procesamiento: {int(horas):02d}:{int(minutos):02d}:{segundos:.2f}\n")
        
        # Guardar código de salida
        codigo_salida = proceso.returncode
        f.write(f"Código de salida: {codigo_salida}\n")
    
    # Copiar archivos geojson generados con prefijo de configuración
    archivos_guardados = []
    for geojson_file in glob.glob(f"../geojson_comunidades_zonas/{comunidad}_*.geojson"):
        try:
            nombre_archivo = os.path.basename(geojson_file)
            nuevo_nombre = f"{config['nombre']}_{nombre_archivo}"
            destino = os.path.join(GEOJSON_DIR, nuevo_nombre)
            shutil.copy2(geojson_file, destino)
            archivos_guardados.append(destino)
            print(f"Archivo copiado: {destino}")
        except Exception as e:
            print(f"Error al copiar {geojson_file}: {e}")
    
    return {
        "config": config['nombre'],
        "comunidad": comunidad,
        "codigo_salida": codigo_salida,
        "log_file": log_file,
        "archivos_guardados": archivos_guardados,
        "tiempo_ejecucion": tiempo_total
    }

def ejecutar_todas_pruebas():
    """Ejecuta todas las pruebas configuradas."""
    print("Iniciando ejecución de todas las pruebas...")
    
    # Asegurar que existen los directorios
    setup_directorios()
    
    # Lista para almacenar resultados
    resultados = []
    
    # Ejecutar cada prueba para cada comunidad
    for comunidad in COMUNIDADES_PRUEBA:  # Usar comunidades pequeñas de prueba
        for config in CONFIGS:
            try:
                resultado = ejecutar_prueba(config, comunidad)
                resultados.append(resultado)
            except Exception as e:
                print(f"Error en prueba {config['nombre']} - {comunidad}: {e}")
    
    # Guardar resumen de ejecuciones
    resumen_file = os.path.join(LOGS_DIR, f"resumen_ejecucion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    with open(resumen_file, 'w', encoding='utf-8') as f:
        f.write("RESUMEN DE EJECUCIONES\n")
        f.write("=====================\n\n")
        
        for res in resultados:
            f.write(f"Config: {res['config']}\n")
            f.write(f"Comunidad: {res['comunidad']}\n")
            f.write(f"Código de salida: {res['codigo_salida']}\n")
            f.write(f"Log: {res['log_file']}\n")
            f.write(f"Archivos guardados: {len(res['archivos_guardados'])}\n")
            f.write(f"Tiempo de ejecución: {res['tiempo_ejecucion']:.2f} segundos\n")
            f.write("\n" + "-"*50 + "\n\n")
    
    print(f"\nEjecución completa. Resumen guardado en: {resumen_file}")
    print(f"Se han guardado los archivos GeoJSON en: {GEOJSON_DIR}")
    print(f"Los logs detallados se encuentran en: {LOGS_DIR}")
    
    return resultados

def ejecutar_analisis():
    """Ejecuta el análisis de los resultados."""
    print("\nIniciando análisis de resultados...")
    
    # Verificar que existen archivos para analizar
    archivos_geojson = glob.glob(os.path.join(GEOJSON_DIR, "*.geojson"))
    if not archivos_geojson:
        print(f"No se encontraron archivos GeoJSON en {GEOJSON_DIR}")
        print("Primero debe ejecutar las pruebas.")
        return False
    
    # Ejecutar script de análisis
    return ejecutar_paso(
        f"py comparar_resultados.py", 
        "Analizando resultados y generando gráficos"
    )

def mostrar_ayuda():
    """Muestra la ayuda del script."""
    print("""
Análisis de Rendimiento para Generación de Zonas Geográficas
============================================================

Este script ejecuta pruebas de rendimiento para la generación de zonas geográficas
utilizando diferentes configuraciones de hardware (CPU/GPU), modos de ejecución
(Preciso/Rápido) y métodos de división (Grid/Voronoi).

Uso:
  py main2.py [opción]

Opciones:
  --ejecutar     Ejecuta todas las pruebas configuradas
  --analizar     Analiza los resultados de las pruebas ya ejecutadas
  --todo         Ejecuta las pruebas y luego realiza el análisis
  --ayuda        Muestra esta ayuda
  
Ejemplos:
  py main2.py --ejecutar     # Solo ejecuta las pruebas
  py main2.py --analizar     # Solo analiza resultados existentes
  py main2.py --todo         # Ejecuta pruebas y realiza análisis
    """)

def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(description='Análisis de rendimiento para generación de zonas geográficas', add_help=False)
    parser.add_argument('--ejecutar', action='store_true', help='Ejecuta todas las pruebas configuradas')
    parser.add_argument('--analizar', action='store_true', help='Analiza los resultados de las pruebas ya ejecutadas')
    parser.add_argument('--todo', action='store_true', help='Ejecuta las pruebas y luego realiza el análisis')
    parser.add_argument('--ayuda', action='store_true', help='Muestra la ayuda')
    
    # Si no hay argumentos, mostrar ayuda
    if len(sys.argv) == 1:
        mostrar_ayuda()
        return
    
    args = parser.parse_args()
    
    if args.ayuda:
        mostrar_ayuda()
        return
    
    if args.ejecutar or args.todo:
        ejecutar_todas_pruebas()
    
    if args.analizar or args.todo:
        ejecutar_analisis()
    
    if not (args.ejecutar or args.analizar or args.todo):
        print("Debe especificar al menos una opción. Use --ayuda para más información.")

if __name__ == "__main__":
    main() 