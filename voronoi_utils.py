import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import Polygon, MultiPolygon, Point
import random

def generar_puntos_dentro_poligono(poligono, n_puntos):
    """
    Genera n_puntos puntos aleatorios dentro del polígono.
    
    Args:
        poligono: Polígono (shapely.geometry.Polygon)
        n_puntos: Número de puntos a generar
    
    Returns:
        Lista de puntos (x, y)
    """
    # Obtener bounding box del polígono
    minx, miny, maxx, maxy = poligono.bounds
    
    # Lista para almacenar los puntos generados
    puntos = []
    intentos_maximos = n_puntos * 1000  # Límite de intentos para evitar bucles infinitos
    intentos = 0
    
    # Generar puntos aleatorios dentro del polígono
    while len(puntos) < n_puntos and intentos < intentos_maximos:
        # Generar punto aleatorio dentro del bounding box
        x = random.uniform(minx, maxx)
        y = random.uniform(miny, maxy)
        punto = Point(x, y)
        
        # Verificar si el punto está dentro del polígono
        if poligono.contains(punto):
            puntos.append((x, y))
        
        intentos += 1
    
    return puntos

def poligonos_voronoi(puntos, poligono_limite):
    """
    Genera un diagrama de Voronoi y recorta las regiones por el polígono límite.
    
    Args:
        puntos: Lista de puntos (x, y)
        poligono_limite: Polígono que limita las regiones (shapely.geometry.Polygon)
    
    Returns:
        Lista de polígonos correspondientes a las regiones de Voronoi
    """
    # Si no hay suficientes puntos, devolver el polígono original
    if len(puntos) <= 1:
        return [poligono_limite]
    
    # Convertir puntos a array numpy
    puntos_np = np.array(puntos)
    
    # Obtener bounding box del polígono
    minx, miny, maxx, maxy = poligono_limite.bounds
    
    # Calcular el tamaño del bounding box
    ancho = maxx - minx
    alto = maxy - miny
    
    # Crear puntos adicionales fuera del polígono para cerrar regiones de Voronoi
    puntos_adicionales = [
        (minx - ancho, miny - alto),
        (minx - ancho, maxy + alto),
        (maxx + ancho, miny - alto),
        (maxx + ancho, maxy + alto),
        (minx - ancho, (miny + maxy) / 2),
        (maxx + ancho, (miny + maxy) / 2),
        ((minx + maxx) / 2, miny - alto),
        ((minx + maxx) / 2, maxy + alto)
    ]
    
    # Añadir puntos adicionales
    puntos_voronoi = np.vstack([puntos_np, puntos_adicionales])
    
    # Calcular diagrama de Voronoi
    vor = Voronoi(puntos_voronoi)
    
    # Lista para almacenar las regiones de Voronoi
    regiones_voronoi = []
    
    # Procesar regiones de Voronoi para los puntos originales (no los adicionales)
    for i in range(len(puntos)):
        # Obtener región de Voronoi para el punto i
        region_index = vor.point_region[i]
        region_vertices = vor.regions[region_index]
        
        # Verificar si la región es válida
        if -1 not in region_vertices and len(region_vertices) > 0:
            # Obtener coordenadas de los vértices
            polygon_vertices = [vor.vertices[v] for v in region_vertices]
            
            # Crear polígono
            poligono_voronoi = Polygon(polygon_vertices)
            
            # Intersectar con el polígono límite
            region_recortada = poligono_voronoi.intersection(poligono_limite)
            
            # Añadir a la lista si la intersección es válida
            if not region_recortada.is_empty:
                if isinstance(region_recortada, Polygon):
                    regiones_voronoi.append(region_recortada)
                elif isinstance(region_recortada, MultiPolygon):
                    # Si la intersección es un multipolígono, añadir cada parte
                    for geom in region_recortada.geoms:
                        regiones_voronoi.append(geom)
    
    # Si no se generaron regiones, devolver el polígono original
    if not regiones_voronoi:
        return [poligono_limite]
    
    return regiones_voronoi 