# Análisis de Rendimiento: Conclusiones

*Generado automáticamente el 26-03-2025 05:09*

## Resumen General

Se analizaron un total de 32 ejecuciones del script en distintas configuraciones y comunidades autónomas.

- **Total de zonas generadas:** 70,239
- **Promedio de zonas por ejecución:** 2194.97
- **Tiempo promedio de ejecución:** 6.44 segundos
- **Eficiencia promedio:** 237.38 zonas/segundo

## Mejores Configuraciones

### Configuración Más Rápida
- **Configuración:** CPU-Preciso-Voronoi
- **Comunidad:** ciudad_autonoma_de_melilla
- **Tiempo:** 3.00 segundos
- **Zonas generadas:** 21
- **Eficiencia:** 7.00 zonas/segundo

### Configuración Más Eficiente
- **Configuración:** CPU-Rapido-Grid
- **Comunidad:** la_rioja
- **Tiempo:** 8.00 segundos
- **Zonas generadas:** 4728
- **Eficiencia:** 591.00 zonas/segundo

### Configuración con Mayor Número de Zonas
- **Configuración:** CPU-Preciso-Voronoi
- **Comunidad:** la_rioja
- **Tiempo:** 10.00 segundos
- **Zonas generadas:** 4904
- **Eficiencia:** 490.40 zonas/segundo

## Comparativa: CPU vs GPU

| Métrica | CPU | GPU | Diferencia (%) | Ganador |
|---------|-----|-----|----------------|--------|
| Tiempo promedio | 6.25s | 6.62s | 6.00% | CPU |
| Zonas promedio | 2201.19 | 2188.75 | 0.57% | CPU |
| Eficiencia | 247.21 z/s | 227.56 z/s | 7.95% | CPU |

### Conclusión CPU vs GPU

La CPU supera a la GPU en eficiencia en un 7.95%, siendo más efectiva para este tipo de procesamiento. Esto podría deberse a que la carga de trabajo no aprovecha completamente el paralelismo de la GPU o hay cuellos de botella en la transferencia de datos.

## Comparativa: Grid vs Voronoi

| Métrica | Grid | Voronoi | Diferencia (%) | Ganador |
|---------|------|---------|----------------|--------|
| Tiempo promedio | 6.06s | 6.81s | 12.37% | Grid |
| Zonas promedio | 2169.25 | 2220.69 | 2.37% | Voronoi |
| Eficiencia | 255.34 z/s | 219.43 z/s | 14.06% | Grid |

### Conclusión Grid vs Voronoi

El método Grid supera al método Voronoi en eficiencia en un 14.06%. Esto podría deberse a la menor complejidad computacional del algoritmo Grid, lo que permite procesar más zonas por unidad de tiempo.

## Comparativa: Preciso vs Rápido

| Métrica | Preciso | Rápido | Diferencia (%) | Ganador |
|---------|---------|--------|----------------|--------|
| Tiempo promedio | 6.62s | 6.25s | 5.66% | Rápido |
| Zonas promedio | 2195.44 | 2194.50 | 0.04% | Preciso |
| Eficiencia | 228.56 z/s | 246.21 z/s | 7.72% | Rápido |

### Conclusión Preciso vs Rápido

El modo Rápido supera al modo Preciso en eficiencia en un 7.72%, como era de esperar por su diseño. Sin embargo, el modo Preciso genera un 0.04% más de zonas, lo que sugiere una compensación entre precisión y velocidad.

## Recomendaciones Finales

### Configuración Óptima Recomendada

Basado en los análisis anteriores, la configuración óptima es: **CPU-Rapido-Grid**

Esta configuración combina CPU + Rapido + Grid, logrando el mejor equilibrio entre tiempo de procesamiento y número de zonas generadas.

### Caso de Uso: Procesamiento por Lotes

Para procesamiento por lotes de múltiples comunidades: **CPU-Rapido-Grid**

### Caso de Uso: Urgencia

Para necesidades urgentes donde el tiempo es crítico: **CPU-Rapido-Grid**

### Caso de Uso: Máxima Precisión

Para obtener el mayor número de zonas posible: **CPU-Preciso-Voronoi**

## Análisis por Tamaño de Comunidad

### Configuración Óptima por Tamaño de Comunidad

- Para comunidades **Pequeña**: CPU-Rapido-Voronoi
- Para comunidades **Mediana**: GPU-Rapido-Voronoi
- Para comunidades **Grande**: CPU-Rapido-Grid

## Gráficos Generados

Se han generado los siguientes gráficos comparativos:

1. `tiempo_por_configuracion.png` - Comparativa de tiempos por configuración
2. `zonas_por_configuracion.png` - Comparativa de zonas generadas por configuración
3. `eficiencia_por_configuracion.png` - Eficiencia (zonas/segundo) por configuración
4. `zonas_por_metodo.png`, `tiempo_por_metodo.png`, `eficiencia_por_metodo.png` - Comparativas de Grid vs Voronoi
5. `zonas_por_hardware.png`, `tiempo_por_hardware.png`, `eficiencia_por_hardware.png` - Comparativas de CPU vs GPU
6. `grid_vs_voronoi.png`, `cpu_vs_gpu.png` - Comparativas de Grid vs Voronoi y CPU vs GPU
7. `mapa_calor_eficiencia.png` - Mapa de calor de eficiencia por configuración
8. `relacion_tamano_tiempo.png` - Relación entre tamaño de comunidad y tiempo de procesamiento
