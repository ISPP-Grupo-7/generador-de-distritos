import numpy as np
import cupy as cp
from scipy.spatial import Voronoi
from shapely.geometry import Polygon, MultiPolygon, Point
import random

def verificar_gpu_disponible():
    """
    Verifica si hay una GPU disponible y devuelve información sobre ella
    
    Returns:
        bool: True si hay GPU disponible, False en caso contrario
        dict: Información de la GPU (nombre, memoria total)
    """
    try:
        if cp.cuda.is_available():
            device_props = cp.cuda.runtime.getDeviceProperties(0)
            gpu_info = {
                "nombre": device_props["name"].decode('utf-8'),
                "memoria_total_gb": device_props["totalGlobalMem"] / (1024**3),
                "compute_capability": f"{device_props['major']}.{device_props['minor']}"
            }
            return True, gpu_info
        else:
            return False, None
    except Exception as e:
        print(f"Error al verificar GPU: {e}")
        return False, None

def generar_puntos_aleatorios_gpu(n, minx, miny, maxx, maxy):
    """
    Genera n puntos aleatorios en el rango especificado usando GPU
    
    Args:
        n: Número de puntos a generar
        minx, miny, maxx, maxy: Límites del área
    
    Returns:
        Tupla de arrays NumPy (x, y)
    """
    # Para lotes pequeños, usar NumPy es más eficiente debido al overhead de transferencia GPU
    if n < 1000:
        x = np.random.uniform(minx, maxx, n)
        y = np.random.uniform(miny, maxy, n)
        return x, y
    
    # Para lotes grandes, usar GPU
    try:
        # Generar coordenadas x e y aleatorias en GPU
        x = cp.random.uniform(minx, maxx, n)
        y = cp.random.uniform(miny, maxy, n)
        # Transferir de vuelta a CPU para procesamiento posterior
        return cp.asnumpy(x), cp.asnumpy(y)
    except Exception:
        # Si hay error con GPU, usar CPU
        x = np.random.uniform(minx, maxx, n)
        y = np.random.uniform(miny, maxy, n)
        return x, y

def generar_puntos_dentro_poligono_gpu(poligono, n_puntos, tamaño_lote=100000):
    """
    Versión acelerada por GPU de generar_puntos_dentro_poligono
    
    Args:
        poligono: Polígono (shapely.geometry.Polygon)
        n_puntos: Número de puntos a generar
        tamaño_lote: Tamaño de lote para generación de puntos (reducido para gestión de memoria)
    
    Returns:
        Lista de puntos (x, y)
    """
    # Verificar si el polígono es demasiado pequeño o inválido
    if not poligono.is_valid:
        print(f"Advertencia: Polígono no válido. Usando método CPU alternativo.")
        return []
    
    minx, miny, maxx, maxy = poligono.bounds
    
    # Si el polígono es demasiado pequeño, usar método CPU
    if (maxx - minx) < 0.00001 or (maxy - miny) < 0.00001:
        print(f"Advertencia: Polígono demasiado pequeño. Usando método CPU.")
        return []
    
    # Para polígonos pequeños o simples, usar CPU es más eficiente
    # Estimar complejidad basado en número de puntos en el exterior del polígono
    puntos_perimetro = len(poligono.exterior.coords)
    area = poligono.area
    complejidad = puntos_perimetro / area if area > 0 else float('inf')
    
    if puntos_perimetro < 20 or n_puntos < 10 or complejidad > 1000:
        try:
            # Usar CPU para polígonos simples
            puntos = []
            intentos = 0
            max_intentos = n_puntos * 100
            
            # Generar puntos en lotes para mejor rendimiento
            while len(puntos) < n_puntos and intentos < max_intentos:
                # Generar un lote de puntos
                lote_size = min(1000, (n_puntos - len(puntos)) * 2)
                x_batch, y_batch = np.random.uniform(minx, maxx, lote_size), np.random.uniform(miny, maxy, lote_size)
                
                # Verificar puntos en lote
                for i in range(lote_size):
                    punto = Point(x_batch[i], y_batch[i])
                    if poligono.contains(punto):
                        puntos.append((x_batch[i], y_batch[i]))
                        if len(puntos) >= n_puntos:
                            break
                
                intentos += lote_size
            return puntos
        except Exception:
            # Si hay error, continuar con GPU
            pass
    
    # Lista para almacenar los puntos generados
    puntos = []
    
    # Usar un tamaño de lote menor para evitar problemas de memoria
    # y reducir la latencia entre CPU y GPU
    batch_size = min(tamaño_lote, n_puntos * 5)
    intentos = 0
    max_intentos = n_puntos * 100  # Reducido para rendimiento
    
    try:
        while len(puntos) < n_puntos and intentos < max_intentos:
            # Generar un lote de puntos aleatorios usando GPU
            x_batch, y_batch = generar_puntos_aleatorios_gpu(batch_size, minx, maxx, miny, maxy)
            
            # Filtrar puntos en CPU (shapely no trabaja directamente con GPU)
            for i in range(len(x_batch)):
                try:
                    punto = Point(x_batch[i], y_batch[i])
                    if poligono.contains(punto):
                        puntos.append((x_batch[i], y_batch[i]))
                        if len(puntos) >= n_puntos:
                            break
                except Exception:
                    # Ignorar errores individuales de puntos
                    continue
            
            intentos += batch_size
            
            # Si después de muchos intentos sólo tenemos unos pocos puntos, aceptar lo que tenemos
            if intentos > max_intentos * 0.5 and len(puntos) > 0:
                print(f"Advertencia: Aceptando {len(puntos)} puntos después de {intentos} intentos.")
                break
    except Exception as e:
        print(f"Error en generación GPU: {e}. Cambiando a método CPU.")
        # Método de respaldo usando CPU
        puntos_cpu = []
        intentos_cpu = 0
        max_intentos_cpu = n_puntos * 100
        
        while len(puntos_cpu) < n_puntos and intentos_cpu < max_intentos_cpu:
            # Generar puntos en lotes para mejor rendimiento
            lote_size = min(1000, (n_puntos - len(puntos_cpu)) * 2)
            x_batch, y_batch = np.random.uniform(minx, maxx, lote_size), np.random.uniform(miny, maxy, lote_size)
            
            # Verificar puntos en lote
            for i in range(lote_size):
                try:
                    punto = Point(x_batch[i], y_batch[i])
                    if poligono.contains(punto):
                        puntos_cpu.append((x_batch[i], y_batch[i]))
                        if len(puntos_cpu) >= n_puntos:
                            break
                except Exception:
                    continue
            
            intentos_cpu += lote_size
        
        return puntos_cpu
    
    return puntos

def calcular_distancias_poligono_gpu(puntos, vertices_poligono):
    """
    Calcula distancias entre puntos y vértices de un polígono usando GPU
    
    Args:
        puntos: Array de puntos (n, 2)
        vertices_poligono: Array de vértices del polígono (m, 2)
    
    Returns:
        Array de distancias (n, m)
    """
    # Transferir datos a GPU
    puntos_gpu = cp.array(puntos)
    vertices_gpu = cp.array(vertices_poligono)
    
    # Calcular distancias usando broadcasting
    num_puntos = puntos_gpu.shape[0]
    num_vertices = vertices_gpu.shape[0]
    
    # Reshape para broadcasting
    puntos_reshaped = puntos_gpu.reshape(num_puntos, 1, 2)
    vertices_reshaped = vertices_gpu.reshape(1, num_vertices, 2)
    
    # Calcular distancias euclidianas
    diff = puntos_reshaped - vertices_reshaped
    distancias = cp.sqrt(cp.sum(diff**2, axis=2))
    
    # Transferir resultado a CPU
    return cp.asnumpy(distancias)

def optimizar_divisiones_voronoi_gpu(puntos, poligono_limite, iteraciones=5):
    """
    Optimiza la ubicación de los puntos para el diagrama de Voronoi
    usando Lloyd's algorithm acelerado por GPU
    
    Args:
        puntos: Lista de puntos iniciales (x, y)
        poligono_limite: Polígono que limita las regiones
        iteraciones: Número de iteraciones de optimización
    
    Returns:
        Lista de puntos optimizados (x, y)
    """
    if len(puntos) <= 2:
        return puntos
    
    puntos_array = np.array(puntos)
    
    for _ in range(iteraciones):
        # Generar diagrama de Voronoi
        vor = Voronoi(puntos_array)
        nuevos_puntos = []
        
        # Para cada punto, calcular el centroide de su región de Voronoi
        for i, punto in enumerate(puntos_array):
            region_idx = vor.point_region[i]
            vertices_idx = vor.regions[region_idx]
            
            # Verificar que la región es válida
            if -1 not in vertices_idx and len(vertices_idx) > 2:
                vertices = vor.vertices[vertices_idx]
                
                # Crear polígono de Voronoi
                poligono_voronoi = Polygon(vertices)
                
                # Intersectar con el polígono límite
                region_recortada = poligono_voronoi.intersection(poligono_limite)
                
                if not region_recortada.is_empty:
                    # Calcular centroide
                    centroide = region_recortada.centroid
                    nuevos_puntos.append((centroide.x, centroide.y))
                else:
                    nuevos_puntos.append((punto[0], punto[1]))
            else:
                nuevos_puntos.append((punto[0], punto[1]))
        
        # Actualizar puntos para la siguiente iteración
        puntos_array = np.array(nuevos_puntos)
    
    return [(x, y) for x, y in puntos_array]

def mejorar_puntos_aleatorios_gpu(poligono, n_puntos):
    """
    Genera puntos aleatorios dentro del polígono y luego los optimiza
    para distribución más uniforme usando GPU
    
    Args:
        poligono: Polígono (shapely.geometry.Polygon)
        n_puntos: Número de puntos a generar
    
    Returns:
        Lista de puntos (x, y) optimizados
    """
    # Generar puntos aleatorios iniciales
    puntos = generar_puntos_dentro_poligono_gpu(poligono, n_puntos)
    
    # Si no hay suficientes puntos, intentar con método CPU
    if len(puntos) == 0:
        # Método de respaldo usando CPU
        puntos_cpu = []
        intentos_cpu = 0
        max_intentos_cpu = n_puntos * 100
        minx, miny, maxx, maxy = poligono.bounds
        
        while len(puntos_cpu) < n_puntos and intentos_cpu < max_intentos_cpu:
            x = random.uniform(minx, maxx)
            y = random.uniform(miny, maxy)
            punto = Point(x, y)
            try:
                if poligono.contains(punto):
                    puntos_cpu.append((x, y))
            except Exception:
                pass
            intentos_cpu += 1
            
        puntos = puntos_cpu
    
    # Si no hay suficientes puntos, devolver lo que tengamos
    if len(puntos) < 2:
        return puntos
    
    # Optimizar la ubicación de los puntos
    try:
        return optimizar_divisiones_voronoi_gpu(puntos, poligono)
    except Exception as e:
        print(f"Error al optimizar puntos: {e}. Usando puntos sin optimizar.")
        return puntos 