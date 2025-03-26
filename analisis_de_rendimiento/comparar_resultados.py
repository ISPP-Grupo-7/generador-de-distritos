import os
import json
import glob
import re
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from datetime import datetime

# Configuración de directorios
GEOJSON_DIR = "analisis_de_rendimiento/resultados/geojson"
ANALISIS_DIR = "analisis_de_rendimiento/resultados/analisis"
LOGS_DIR = "analisis_de_rendimiento/resultados/logs"

# Asegurar que existen los directorios
os.makedirs(ANALISIS_DIR, exist_ok=True)

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

def obtener_tiempo_ejecucion(config, comunidad):
    """
    Obtiene el tiempo de ejecución de los archivos de log.
    
    Args:
        config: Nombre de la configuración
        comunidad: Código de la comunidad autónoma
    
    Returns:
        Tiempo de ejecución en segundos
    """
    log_files = glob.glob(os.path.join(LOGS_DIR, f"log_{config}_{comunidad}_*.txt"))
    
    if not log_files:
        print(f"No se encontraron logs para la config {config} en comunidad {comunidad}")
        return 0
    
    # Usar el log más reciente
    log_file = sorted(log_files)[-1]
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            contenido = f.read()
            # Buscar tiempo total reportado
            tiempo_match = re.search(r"Tiempo total de procesamiento: (\d+):(\d+):([\d\.]+)", contenido)
            if tiempo_match:
                horas, minutos, segundos = map(float, tiempo_match.groups())
                return horas * 3600 + minutos * 60 + segundos
            
            # Si no está el formato específico, buscar el tiempo total genérico
            tiempo_match = re.search(r"Tiempo total: ([\d\.]+) segundos", contenido)
            if tiempo_match:
                return float(tiempo_match.group(1))
    except Exception as e:
        print(f"Error al leer log {log_file}: {e}")
    
    return 0

def analizar_resultados():
    """
    Analiza los archivos GeoJSON guardados y recopila datos de rendimiento.
    
    Returns:
        DataFrame con los datos analizados
    """
    print("Analizando resultados de las pruebas...")
    
    # Verificar que existen archivos para analizar
    archivos_geojson = glob.glob(os.path.join(GEOJSON_DIR, "*.geojson"))
    if not archivos_geojson:
        print(f"No se encontraron archivos GeoJSON en {GEOJSON_DIR}")
        print("Ejecute primero el script ejecutar_pruebas.py")
        return None
    
    # Lista para almacenar los resultados
    resultados = []
    
    # Patrón para extraer la configuración y la comunidad del nombre de archivo
    patron = r"([\w-]+)_(\d+)_(.+)\.geojson"
    
    # Procesar cada archivo
    for archivo in archivos_geojson:
        nombre_archivo = os.path.basename(archivo)
        match = re.match(patron, nombre_archivo)
        
        if not match:
            print(f"Formato de nombre no reconocido: {nombre_archivo}")
            continue
        
        config, comunidad, nombre_comunidad = match.groups()
        
        # Contar zonas
        num_zonas = contar_zonas_geojson(archivo)
        
        # Obtener tiempo de ejecución
        tiempo_ejecucion = obtener_tiempo_ejecucion(config, comunidad)
        
        # Extraer características de la configuración
        hardware = "GPU" if "GPU" in config else "CPU"
        modo = "Preciso" if "Preciso" in config else "Rápido"
        metodo = "Voronoi" if "Voronoi" in config else "Grid"
        
        # Guardar resultados
        resultados.append({
            "config": config,
            "comunidad": comunidad,
            "nombre_comunidad": nombre_comunidad,
            "hardware": hardware,
            "modo": modo,
            "metodo": metodo,
            "zonas": num_zonas,
            "tiempo": tiempo_ejecucion,
            "eficiencia": num_zonas / tiempo_ejecucion if tiempo_ejecucion > 0 else 0,
            "archivo": nombre_archivo
        })
    
    # Convertir a DataFrame
    df = pd.DataFrame(resultados)
    
    # Guardar resultados en CSV
    csv_path = os.path.join(ANALISIS_DIR, f"resultados_analisis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    df.to_csv(csv_path, index=False)
    print(f"Datos guardados en {csv_path}")
    
    return df

def generar_graficos(df):
    """
    Genera gráficos comparativos a partir de los datos analizados.
    
    Args:
        df: DataFrame con los datos analizados
    """
    print("Generando gráficos comparativos...")
    
    if df is None or df.empty:
        print("No hay datos para generar gráficos.")
        return
    
    # Configurar estilo de los gráficos
    plt.style.use('seaborn-v0_8-darkgrid')
    
    # 1. Tiempo promedio por configuración
    plt.figure(figsize=(14, 8))
    tiempo_por_config = df.groupby('config')['tiempo'].mean().sort_values()
    ax = tiempo_por_config.plot(kind='bar', color=plt.cm.viridis(np.linspace(0, 1, len(tiempo_por_config))))
    plt.title('Tiempo promedio de procesamiento por configuración', fontsize=16)
    plt.ylabel('Tiempo (segundos)', fontsize=14)
    plt.xlabel('Configuración', fontsize=14)
    plt.xticks(rotation=45, ha='right', fontsize=12)
    plt.tight_layout()
    
    # Añadir valores en las barras
    for i, v in enumerate(tiempo_por_config):
        ax.text(i, v + v*0.02, f"{v:.2f}s", ha='center', fontsize=10)
    
    plt.savefig(os.path.join(ANALISIS_DIR, 'tiempo_por_configuracion.png'), dpi=300)
    
    # 2. Número de zonas promedio por configuración
    plt.figure(figsize=(14, 8))
    zonas_por_config = df.groupby('config')['zonas'].mean().sort_values(ascending=False)
    ax = zonas_por_config.plot(kind='bar', color=plt.cm.plasma(np.linspace(0, 1, len(zonas_por_config))))
    plt.title('Número promedio de zonas generadas por configuración', fontsize=16)
    plt.ylabel('Número de zonas', fontsize=14)
    plt.xlabel('Configuración', fontsize=14)
    plt.xticks(rotation=45, ha='right', fontsize=12)
    plt.tight_layout()
    
    # Añadir valores en las barras
    for i, v in enumerate(zonas_por_config):
        ax.text(i, v + v*0.02, f"{int(v)}", ha='center', fontsize=10)
    
    plt.savefig(os.path.join(ANALISIS_DIR, 'zonas_por_configuracion.png'), dpi=300)
    
    # 3. Eficiencia: zonas/segundo por configuración
    plt.figure(figsize=(14, 8))
    eficiencia_por_config = df.groupby('config')['eficiencia'].mean().sort_values(ascending=False)
    ax = eficiencia_por_config.plot(kind='bar', color=plt.cm.cividis(np.linspace(0, 1, len(eficiencia_por_config))))
    plt.title('Eficiencia: Zonas por segundo por configuración', fontsize=16)
    plt.ylabel('Zonas por segundo', fontsize=14)
    plt.xlabel('Configuración', fontsize=14)
    plt.xticks(rotation=45, ha='right', fontsize=12)
    plt.tight_layout()
    
    # Añadir valores en las barras
    for i, v in enumerate(eficiencia_por_config):
        ax.text(i, v + v*0.02, f"{v:.2f}", ha='center', fontsize=10)
    
    plt.savefig(os.path.join(ANALISIS_DIR, 'eficiencia_por_configuracion.png'), dpi=300)
    
    # 4. Comparativa por método (Grid vs Voronoi)
    plt.figure(figsize=(12, 10))
    sns.boxplot(x='metodo', y='zonas', data=df, palette='Set3')
    plt.title('Comparativa de zonas generadas: Grid vs Voronoi', fontsize=16)
    plt.ylabel('Número de zonas', fontsize=14)
    plt.xlabel('Método', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(ANALISIS_DIR, 'zonas_por_metodo.png'), dpi=300)
    
    plt.figure(figsize=(12, 10))
    sns.boxplot(x='metodo', y='tiempo', data=df, palette='Set2')
    plt.title('Comparativa de tiempo: Grid vs Voronoi', fontsize=16)
    plt.ylabel('Tiempo (segundos)', fontsize=14)
    plt.xlabel('Método', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(ANALISIS_DIR, 'tiempo_por_metodo.png'), dpi=300)
    
    plt.figure(figsize=(12, 10))
    sns.boxplot(x='metodo', y='eficiencia', data=df, palette='Set1')
    plt.title('Comparativa de eficiencia: Grid vs Voronoi', fontsize=16)
    plt.ylabel('Zonas por segundo', fontsize=14)
    plt.xlabel('Método', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(ANALISIS_DIR, 'eficiencia_por_metodo.png'), dpi=300)
    
    # 5. Comparativa por hardware (CPU vs GPU)
    plt.figure(figsize=(12, 10))
    sns.boxplot(x='hardware', y='zonas', data=df, palette='rocket')
    plt.title('Comparativa de zonas generadas: CPU vs GPU', fontsize=16)
    plt.ylabel('Número de zonas', fontsize=14)
    plt.xlabel('Hardware', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(ANALISIS_DIR, 'zonas_por_hardware.png'), dpi=300)
    
    plt.figure(figsize=(12, 10))
    sns.boxplot(x='hardware', y='tiempo', data=df, palette='mako')
    plt.title('Comparativa de tiempo: CPU vs GPU', fontsize=16)
    plt.ylabel('Tiempo (segundos)', fontsize=14)
    plt.xlabel('Hardware', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(ANALISIS_DIR, 'tiempo_por_hardware.png'), dpi=300)
    
    plt.figure(figsize=(12, 10))
    sns.boxplot(x='hardware', y='eficiencia', data=df, palette='flare')
    plt.title('Comparativa de eficiencia: CPU vs GPU', fontsize=16)
    plt.ylabel('Zonas por segundo', fontsize=14)
    plt.xlabel('Hardware', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(ANALISIS_DIR, 'eficiencia_por_hardware.png'), dpi=300)
    
    # 6. Gráfico combinado: Grid vs Voronoi para diferentes configuraciones
    plt.figure(figsize=(16, 10))
    sns.barplot(x='config', y='tiempo', hue='metodo', data=df, palette='coolwarm')
    plt.title('Comparativa Grid vs Voronoi por configuración', fontsize=16)
    plt.ylabel('Tiempo (segundos)', fontsize=14)
    plt.xlabel('Configuración', fontsize=14)
    plt.xticks(rotation=45, ha='right', fontsize=12)
    plt.legend(title='Método', fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(ANALISIS_DIR, 'grid_vs_voronoi.png'), dpi=300)
    
    # 7. Gráfico combinado: CPU vs GPU para diferentes configuraciones
    plt.figure(figsize=(16, 10))
    sns.barplot(x='config', y='tiempo', hue='hardware', data=df, palette='viridis')
    plt.title('Comparativa CPU vs GPU por configuración', fontsize=16)
    plt.ylabel('Tiempo (segundos)', fontsize=14)
    plt.xlabel('Configuración', fontsize=14)
    plt.xticks(rotation=45, ha='right', fontsize=12)
    plt.legend(title='Hardware', fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(ANALISIS_DIR, 'cpu_vs_gpu.png'), dpi=300)
    
    # 8. Mapa de calor de eficiencia
    plt.figure(figsize=(14, 10))
    # Crear una tabla pivote para el mapa de calor
    heatmap_data = df.pivot_table(
        values='eficiencia', 
        index=['hardware', 'modo'], 
        columns=['metodo'], 
        aggfunc='mean'
    )
    sns.heatmap(heatmap_data, annot=True, fmt=".2f", cmap="YlGnBu", linewidths=.5)
    plt.title('Mapa de calor de eficiencia por configuración', fontsize=16)
    plt.tight_layout()
    plt.savefig(os.path.join(ANALISIS_DIR, 'mapa_calor_eficiencia.png'), dpi=300)
    
    # 9. Comparativa de tamaño de comunidades vs tiempo
    plt.figure(figsize=(14, 10))
    scatter = sns.scatterplot(
        x='zonas', 
        y='tiempo', 
        hue='config', 
        size='eficiencia',
        sizes=(50, 400),
        alpha=0.7,
        data=df
    )
    plt.title('Relación entre tamaño de comunidad y tiempo de procesamiento', fontsize=16)
    plt.xlabel('Número de zonas', fontsize=14)
    plt.ylabel('Tiempo (segundos)', fontsize=14)
    plt.legend(title='Configuración', fontsize=10, bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(ANALISIS_DIR, 'relacion_tamano_tiempo.png'), dpi=300)
    
    print(f"Gráficos guardados en {ANALISIS_DIR}")

def generar_conclusiones(df):
    """
    Genera un archivo README con conclusiones basadas en los datos analizados.
    
    Args:
        df: DataFrame con los datos analizados
    """
    print("Generando conclusiones...")
    
    if df is None or df.empty:
        print("No hay datos para generar conclusiones.")
        return
    
    # Calcular estadísticas
    stats = {
        "total_zonas": df['zonas'].sum(),
        "media_zonas": df['zonas'].mean(),
        "max_zonas": df['zonas'].max(),
        "min_zonas": df['zonas'].min(),
        "media_tiempo": df['tiempo'].mean(),
        "max_tiempo": df['tiempo'].max(),
        "min_tiempo": df['tiempo'].min(),
        "mejor_eficiencia": df.loc[df['eficiencia'].idxmax()],
        "peor_eficiencia": df.loc[df['eficiencia'].idxmin()]
    }
    
    # Análisis por hardware
    analisis_hardware = df.groupby('hardware').agg({
        'tiempo': 'mean',
        'zonas': 'mean',
        'eficiencia': 'mean'
    }).to_dict('index')
    
    # Análisis por método
    analisis_metodo = df.groupby('metodo').agg({
        'tiempo': 'mean',
        'zonas': 'mean',
        'eficiencia': 'mean'
    }).to_dict('index')
    
    # Análisis por modo
    analisis_modo = df.groupby('modo').agg({
        'tiempo': 'mean',
        'zonas': 'mean',
        'eficiencia': 'mean'
    }).to_dict('index')
    
    # Mejores configuraciones por categoría
    mejor_tiempo = df.iloc[df['tiempo'].idxmin()]
    mejor_zonas = df.iloc[df['zonas'].idxmax()]
    mejor_eficiencia = df.iloc[df['eficiencia'].idxmax()]
    
    # Generar el archivo README
    readme_path = os.path.join(ANALISIS_DIR, 'README.md')
    
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(f"# Análisis de Rendimiento: Conclusiones\n\n")
        f.write(f"*Generado automáticamente el {datetime.now().strftime('%d-%m-%Y %H:%M')}*\n\n")
        
        f.write("## Resumen General\n\n")
        f.write(f"Se analizaron un total de {len(df)} ejecuciones del script en distintas configuraciones y comunidades autónomas.\n\n")
        f.write(f"- **Total de zonas generadas:** {stats['total_zonas']:,}\n")
        f.write(f"- **Promedio de zonas por ejecución:** {stats['media_zonas']:.2f}\n")
        f.write(f"- **Tiempo promedio de ejecución:** {stats['media_tiempo']:.2f} segundos\n")
        f.write(f"- **Eficiencia promedio:** {df['eficiencia'].mean():.2f} zonas/segundo\n\n")
        
        f.write("## Mejores Configuraciones\n\n")
        
        f.write("### Configuración Más Rápida\n")
        f.write(f"- **Configuración:** {mejor_tiempo['config']}\n")
        f.write(f"- **Comunidad:** {mejor_tiempo['nombre_comunidad']}\n")
        f.write(f"- **Tiempo:** {mejor_tiempo['tiempo']:.2f} segundos\n")
        f.write(f"- **Zonas generadas:** {mejor_tiempo['zonas']}\n")
        f.write(f"- **Eficiencia:** {mejor_tiempo['eficiencia']:.2f} zonas/segundo\n\n")
        
        f.write("### Configuración Más Eficiente\n")
        f.write(f"- **Configuración:** {mejor_eficiencia['config']}\n")
        f.write(f"- **Comunidad:** {mejor_eficiencia['nombre_comunidad']}\n")
        f.write(f"- **Tiempo:** {mejor_eficiencia['tiempo']:.2f} segundos\n")
        f.write(f"- **Zonas generadas:** {mejor_eficiencia['zonas']}\n")
        f.write(f"- **Eficiencia:** {mejor_eficiencia['eficiencia']:.2f} zonas/segundo\n\n")
        
        f.write("### Configuración con Mayor Número de Zonas\n")
        f.write(f"- **Configuración:** {mejor_zonas['config']}\n")
        f.write(f"- **Comunidad:** {mejor_zonas['nombre_comunidad']}\n")
        f.write(f"- **Tiempo:** {mejor_zonas['tiempo']:.2f} segundos\n")
        f.write(f"- **Zonas generadas:** {mejor_zonas['zonas']}\n")
        f.write(f"- **Eficiencia:** {mejor_zonas['eficiencia']:.2f} zonas/segundo\n\n")
        
        # Comparativa CPU vs GPU
        f.write("## Comparativa: CPU vs GPU\n\n")
        f.write("| Métrica | CPU | GPU | Diferencia (%) | Ganador |\n")
        f.write("|---------|-----|-----|----------------|--------|\n")
        
        cpu_tiempo = analisis_hardware['CPU']['tiempo']
        gpu_tiempo = analisis_hardware['GPU']['tiempo']
        diff_tiempo = ((cpu_tiempo - gpu_tiempo) / cpu_tiempo) * 100
        ganador_tiempo = "GPU" if gpu_tiempo < cpu_tiempo else "CPU"
        
        cpu_zonas = analisis_hardware['CPU']['zonas']
        gpu_zonas = analisis_hardware['GPU']['zonas']
        diff_zonas = ((gpu_zonas - cpu_zonas) / cpu_zonas) * 100
        ganador_zonas = "GPU" if gpu_zonas > cpu_zonas else "CPU"
        
        cpu_eficiencia = analisis_hardware['CPU']['eficiencia']
        gpu_eficiencia = analisis_hardware['GPU']['eficiencia']
        diff_eficiencia = ((gpu_eficiencia - cpu_eficiencia) / cpu_eficiencia) * 100
        ganador_eficiencia = "GPU" if gpu_eficiencia > cpu_eficiencia else "CPU"
        
        f.write(f"| Tiempo promedio | {cpu_tiempo:.2f}s | {gpu_tiempo:.2f}s | {abs(diff_tiempo):.2f}% | {ganador_tiempo} |\n")
        f.write(f"| Zonas promedio | {cpu_zonas:.2f} | {gpu_zonas:.2f} | {abs(diff_zonas):.2f}% | {ganador_zonas} |\n")
        f.write(f"| Eficiencia | {cpu_eficiencia:.2f} z/s | {gpu_eficiencia:.2f} z/s | {abs(diff_eficiencia):.2f}% | {ganador_eficiencia} |\n\n")
        
        f.write("### Conclusión CPU vs GPU\n\n")
        if ganador_eficiencia == "GPU":
            f.write(f"La GPU supera a la CPU en eficiencia en un {abs(diff_eficiencia):.2f}%, logrando procesar más zonas en menos tiempo. ")
            f.write(f"Es recomendable utilizar GPU para cargas de trabajo intensivas o comunidades grandes.\n\n")
        else:
            f.write(f"La CPU supera a la GPU en eficiencia en un {abs(diff_eficiencia):.2f}%, siendo más efectiva para este tipo de procesamiento. ")
            f.write(f"Esto podría deberse a que la carga de trabajo no aprovecha completamente el paralelismo de la GPU o hay cuellos de botella en la transferencia de datos.\n\n")
        
        # Comparativa Grid vs Voronoi
        f.write("## Comparativa: Grid vs Voronoi\n\n")
        f.write("| Métrica | Grid | Voronoi | Diferencia (%) | Ganador |\n")
        f.write("|---------|------|---------|----------------|--------|\n")
        
        grid_tiempo = analisis_metodo['Grid']['tiempo']
        voronoi_tiempo = analisis_metodo['Voronoi']['tiempo']
        diff_tiempo = ((grid_tiempo - voronoi_tiempo) / grid_tiempo) * 100
        ganador_tiempo = "Voronoi" if voronoi_tiempo < grid_tiempo else "Grid"
        
        grid_zonas = analisis_metodo['Grid']['zonas']
        voronoi_zonas = analisis_metodo['Voronoi']['zonas']
        diff_zonas = ((voronoi_zonas - grid_zonas) / grid_zonas) * 100
        ganador_zonas = "Voronoi" if voronoi_zonas > grid_zonas else "Grid"
        
        grid_eficiencia = analisis_metodo['Grid']['eficiencia']
        voronoi_eficiencia = analisis_metodo['Voronoi']['eficiencia']
        diff_eficiencia = ((voronoi_eficiencia - grid_eficiencia) / grid_eficiencia) * 100
        ganador_eficiencia = "Voronoi" if voronoi_eficiencia > grid_eficiencia else "Grid"
        
        f.write(f"| Tiempo promedio | {grid_tiempo:.2f}s | {voronoi_tiempo:.2f}s | {abs(diff_tiempo):.2f}% | {ganador_tiempo} |\n")
        f.write(f"| Zonas promedio | {grid_zonas:.2f} | {voronoi_zonas:.2f} | {abs(diff_zonas):.2f}% | {ganador_zonas} |\n")
        f.write(f"| Eficiencia | {grid_eficiencia:.2f} z/s | {voronoi_eficiencia:.2f} z/s | {abs(diff_eficiencia):.2f}% | {ganador_eficiencia} |\n\n")
        
        f.write("### Conclusión Grid vs Voronoi\n\n")
        if ganador_eficiencia == "Voronoi":
            f.write(f"El método Voronoi supera al método Grid en eficiencia en un {abs(diff_eficiencia):.2f}%, ")
            f.write(f"lo que sugiere que la división mediante diagramas de Voronoi es más efectiva para generar zonas geográficas. ")
            f.write(f"Además, Voronoi genera un {abs(diff_zonas):.2f}% más de zonas en promedio.\n\n")
        else:
            f.write(f"El método Grid supera al método Voronoi en eficiencia en un {abs(diff_eficiencia):.2f}%. ")
            f.write(f"Esto podría deberse a la menor complejidad computacional del algoritmo Grid, lo que permite procesar más zonas por unidad de tiempo.\n\n")
        
        # Comparativa por modo (Preciso vs Rápido)
        f.write("## Comparativa: Preciso vs Rápido\n\n")
        f.write("| Métrica | Preciso | Rápido | Diferencia (%) | Ganador |\n")
        f.write("|---------|---------|--------|----------------|--------|\n")
        
        preciso_tiempo = analisis_modo['Preciso']['tiempo']
        rapido_tiempo = analisis_modo['Rápido']['tiempo']
        diff_tiempo = ((preciso_tiempo - rapido_tiempo) / preciso_tiempo) * 100
        ganador_tiempo = "Rápido" if rapido_tiempo < preciso_tiempo else "Preciso"
        
        preciso_zonas = analisis_modo['Preciso']['zonas']
        rapido_zonas = analisis_modo['Rápido']['zonas']
        diff_zonas = ((rapido_zonas - preciso_zonas) / preciso_zonas) * 100
        ganador_zonas = "Rápido" if rapido_zonas > preciso_zonas else "Preciso"
        
        preciso_eficiencia = analisis_modo['Preciso']['eficiencia']
        rapido_eficiencia = analisis_modo['Rápido']['eficiencia']
        diff_eficiencia = ((rapido_eficiencia - preciso_eficiencia) / preciso_eficiencia) * 100
        ganador_eficiencia = "Rápido" if rapido_eficiencia > preciso_eficiencia else "Preciso"
        
        f.write(f"| Tiempo promedio | {preciso_tiempo:.2f}s | {rapido_tiempo:.2f}s | {abs(diff_tiempo):.2f}% | {ganador_tiempo} |\n")
        f.write(f"| Zonas promedio | {preciso_zonas:.2f} | {rapido_zonas:.2f} | {abs(diff_zonas):.2f}% | {ganador_zonas} |\n")
        f.write(f"| Eficiencia | {preciso_eficiencia:.2f} z/s | {rapido_eficiencia:.2f} z/s | {abs(diff_eficiencia):.2f}% | {ganador_eficiencia} |\n\n")
        
        f.write("### Conclusión Preciso vs Rápido\n\n")
        if ganador_eficiencia == "Rápido":
            f.write(f"El modo Rápido supera al modo Preciso en eficiencia en un {abs(diff_eficiencia):.2f}%, como era de esperar por su diseño. ")
            if ganador_zonas == "Preciso":
                f.write(f"Sin embargo, el modo Preciso genera un {abs(diff_zonas):.2f}% más de zonas, lo que sugiere una compensación entre precisión y velocidad.\n\n")
            else:
                f.write(f"Además, el modo Rápido genera un {abs(diff_zonas):.2f}% más de zonas, lo que lo convierte en la opción preferible en la mayoría de casos.\n\n")
        else:
            f.write(f"Sorprendentemente, el modo Preciso supera al modo Rápido en eficiencia en un {abs(diff_eficiencia):.2f}%. ")
            f.write(f"Esto podría deberse a un mejor uso de los recursos computacionales o a la implementación específica de los algoritmos.\n\n")
        
        # Recomendaciones finales
        f.write("## Recomendaciones Finales\n\n")
        
        # Determinar la mejor configuración general basada en eficiencia
        mejor_config = df.groupby('config')['eficiencia'].mean().idxmax()
        hardware, modo, metodo = mejor_config.split('-')
        
        f.write(f"### Configuración Óptima Recomendada\n\n")
        f.write(f"Basado en los análisis anteriores, la configuración óptima es: **{mejor_config}**\n\n")
        f.write(f"Esta configuración combina {hardware} + {modo} + {metodo}, logrando el mejor equilibrio entre tiempo de procesamiento y número de zonas generadas.\n\n")
        
        f.write("### Caso de Uso: Procesamiento por Lotes\n\n")
        mejor_eficiencia_config = df.groupby('config')['eficiencia'].mean().idxmax()
        f.write(f"Para procesamiento por lotes de múltiples comunidades: **{mejor_eficiencia_config}**\n\n")
        
        f.write("### Caso de Uso: Urgencia\n\n")
        mejor_tiempo_config = df.groupby('config')['tiempo'].mean().idxmin()
        f.write(f"Para necesidades urgentes donde el tiempo es crítico: **{mejor_tiempo_config}**\n\n")
        
        f.write("### Caso de Uso: Máxima Precisión\n\n")
        mejor_zonas_config = df.groupby('config')['zonas'].mean().idxmax()
        f.write(f"Para obtener el mayor número de zonas posible: **{mejor_zonas_config}**\n\n")
        
        # Conclusiones sobre el tamaño de las comunidades
        f.write("## Análisis por Tamaño de Comunidad\n\n")
        
        # Categorizar comunidades por tamaño (zonas)
        df['tamano_categoria'] = pd.qcut(df['zonas'], 3, labels=['Pequeña', 'Mediana', 'Grande'])
        
        # Analizar rendimiento por categoría de tamaño
        analisis_tamano = df.groupby(['tamano_categoria', 'config'])['eficiencia'].mean().unstack()
        mejor_config_por_tamano = analisis_tamano.idxmax(axis=1).to_dict()
        
        f.write("### Configuración Óptima por Tamaño de Comunidad\n\n")
        for tamano, config in mejor_config_por_tamano.items():
            f.write(f"- Para comunidades **{tamano}**: {config}\n")
        
        f.write("\n## Gráficos Generados\n\n")
        f.write("Se han generado los siguientes gráficos comparativos:\n\n")
        f.write("1. `tiempo_por_configuracion.png` - Comparativa de tiempos por configuración\n")
        f.write("2. `zonas_por_configuracion.png` - Comparativa de zonas generadas por configuración\n")
        f.write("3. `eficiencia_por_configuracion.png` - Eficiencia (zonas/segundo) por configuración\n")
        f.write("4. `zonas_por_metodo.png`, `tiempo_por_metodo.png`, `eficiencia_por_metodo.png` - Comparativas de Grid vs Voronoi\n")
        f.write("5. `zonas_por_hardware.png`, `tiempo_por_hardware.png`, `eficiencia_por_hardware.png` - Comparativas de CPU vs GPU\n")
        f.write("6. `grid_vs_voronoi.png`, `cpu_vs_gpu.png` - Comparativas de Grid vs Voronoi y CPU vs GPU\n")
        f.write("7. `mapa_calor_eficiencia.png` - Mapa de calor de eficiencia por configuración\n")
        f.write("8. `relacion_tamano_tiempo.png` - Relación entre tamaño de comunidad y tiempo de procesamiento\n")
    
    print(f"Conclusiones guardadas en {readme_path}")

def main():
    """Función principal."""
    print("Iniciando análisis comparativo de resultados...")
    
    # Analizar resultados
    df = analizar_resultados()
    
    if df is not None and not df.empty:
        # Generar gráficos
        generar_graficos(df)
        
        # Generar conclusiones
        generar_conclusiones(df)
        
        print("\nAnálisis completo. Revise los resultados en la carpeta:")
        print(ANALISIS_DIR)
    else:
        print("\nNo se pudieron analizar los resultados. Asegúrese de haber ejecutado correctamente el script ejecutar_pruebas.py")

if __name__ == "__main__":
    main() 