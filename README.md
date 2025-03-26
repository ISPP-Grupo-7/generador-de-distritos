# Procesador de Shapefiles para Aplicación de Mapas Gamificada

Este proyecto procesa shapefiles de divisiones administrativas de España para generar archivos GeoJSON optimizados para aplicaciones de mapas gamificadas. Divide los municipios en zonas más pequeñas, ideal para juegos basados en localización.

## Características principales

- Procesamiento de todas las comunidades autónomas de España
- División de municipios en distritos más pequeños (entre 25 y 100 según tamaño)
- Generación de un archivo GeoJSON por comunidad autónoma
- Traducción automática de nombres de catalán a español
- Visualización interactiva de resultados
- Aceleración por GPU (CUDA) para procesamiento más rápido
- Procesamiento paralelo para aprovechar múltiples núcleos de CPU

## Nuevas características (actualización)

- **Optimización avanzada para GPU**: Implementación de algoritmos específicamente optimizados para CUDA utilizando CuPy.
- **Visualización interactiva mejorada**: Mapas con controles avanzados, búsqueda, filtros por municipio y popups informativos.
- **Mayor robustez**: Gestión mejorada de errores para garantizar el procesamiento incluso con datos inconsistentes.
- **Medición de rendimiento**: Cronómetro integrado para comparar rendimiento entre CPU y GPU.
- **Estadísticas de zonas**: Cálculo automático de área, perímetro y compacidad de cada zona.
- **Herramientas de procesamiento GeoJSON**: Nuevos scripts para renombrar, unir y visualizar archivos GeoJSON de comunidades autónomas.

## Requisitos del sistema

- Python 3.7+
- Paquetes Python (ver requirements.txt)
- Para aceleración GPU:
  - NVIDIA GPU compatible con CUDA
  - CUDA 12.x instalado
  - CuPy 13.4.0 o superior compatible con su versión de CUDA

## Instalación

1. Clona este repositorio:
```
git clone <URL-del-repositorio>
cd <nombre-del-repositorio>
```

2. Instala las dependencias:
```
pip install -r requirements.txt
```

3. Para aceleración GPU (opcional pero recomendado):
   - En Windows: ejecuta `instalar_dependencias_cuda.bat` o `script_instalar_gpu.ps1`
   - En Linux/Mac: `pip install cupy-cuda12x`

## Estructura del proyecto

```
.
├── main.py                          # Script principal para procesamiento
├── gpu_voronoi_utils.py             # Funciones optimizadas para GPU
├── voronoi_utils.py                 # Funciones para generar diagramas Voronoi
├── visualizar_geojson.py            # Visualizador básico de GeoJSON
├── visualizar_interactivo.py        # Visualizador avanzado con características interactivas
├── visualizar_comunidades.py        # Visualizador de comunidades autónomas con colores diferenciados
├── unir_geojson.py                  # Une todos los archivos GeoJSON de comunidades en uno solo
├── renombrar_geojson.py             # Renombra archivos GeoJSON eliminando códigos numéricos
├── dividir_municipios.py            # Funciones para dividir municipios
├── procesar_municipios.py           # Procesamiento de municipios individuales
├── procesar_por_provincia.py        # Procesamiento por provincia
├── instalar_dependencias_cuda.bat   # Script de instalación para Windows
├── script_instalar_gpu.ps1          # Script PowerShell para instalación de dependencias GPU
├── requirements.txt                 # Dependencias del proyecto
├── geojson_comunidades_zonas/       # Directorio con archivos GeoJSON originales de comunidades
├── geojson_comunidades_renombradas/ # Directorio con archivos GeoJSON renombrados
└── lineas_limite/                   # Directorio con shapefiles de entrada
    └── SHP_ETRS89/                  # Shapefiles en sistema ETRS89
        ├── recintos_autonomicas_inspire_peninbal_etrs89/
        └── recintos_municipales_inspire_peninbal_etrs89/
```

## Uso

### Procesamiento completo

Para procesar todas las comunidades autónomas:

```
python main.py
```

### Procesamiento de una comunidad específica

Para procesar una comunidad autónoma específica por su código (ej. 34010000000 para Andalucía):

```
python main.py 34010000000
```

### Modos de procesamiento

El script ofrece varios modos de ejecución que se pueden combinar para adaptarse a diferentes necesidades:

#### 1. Modo de hardware

```
python main.py cpu        # Fuerza el uso de CPU (útil en sistemas con GPU limitada)
python main.py gpu        # Fuerza el uso de GPU (requiere CUDA y CuPy instalados)
```

#### 2. Método de división

```
python main.py voronoi    # Usa el método de Voronoi (más preciso, más lento)
python main.py grid       # Usa el método de Grid (menos preciso, más rápido)
```

#### 3. Modos optimizados

```
python main.py rapido     # Prioriza velocidad (usa grid y CPU por defecto)
python main.py preciso    # Prioriza precisión (usa voronoi y GPU si disponible)
```

Los diferentes modos se pueden combinar para personalizar el procesamiento:

```
python main.py 34010000000 gpu voronoi    # Procesa Andalucía usando GPU con método Voronoi
python main.py 34010000000 cpu grid       # Procesa Andalucía usando CPU con método Grid
python main.py gpu preciso                # Procesa todas las comunidades con GPU en modo preciso
python main.py cpu rapido 34010000000     # Procesa Andalucía con CPU en modo rápido
```

##### Combinaciones recomendadas:

- **Para máxima precisión**: `python main.py preciso gpu` (o simplemente `python main.py preciso`)
- **Para máxima velocidad**: `python main.py rapido cpu` (o simplemente `python main.py rapido`)
- **Para equilibrio en máquinas con GPU potente**: `python main.py gpu grid`
- **Para equilibrio en máquinas sin GPU**: `python main.py cpu voronoi`

El script detecta automáticamente el hardware disponible y selecciona la mejor configuración, pero estos modos permiten forzar comportamientos específicos.

### Visualización de resultados

Visualizador básico:
```
python visualizar_geojson.py geojson_comunidades_zonas/34010000000_andalucia.geojson
```

Visualizador interactivo mejorado:
```
python visualizar_interactivo.py geojson_comunidades_zonas/34010000000_andalucia.geojson
```

### Procesamiento de archivos GeoJSON de comunidades

#### Renombrar archivos GeoJSON (eliminar códigos numéricos)

Para renombrar los archivos GeoJSON de comunidades, eliminando los códigos numéricos al inicio:

```
python renombrar_geojson.py
```

Este script tomará los archivos con formato `34010000000_andalucia.geojson` y los renombrará como `andalucia.geojson` en una nueva carpeta `geojson_comunidades_renombradas`.

#### Unir todos los archivos GeoJSON en uno solo

Para combinar todos los archivos GeoJSON en un único archivo:

```
python unir_geojson.py
```

Este script leerá todos los archivos GeoJSON de comunidades autónomas (ya sea de la carpeta original o de la carpeta de archivos renombrados) y los combinará en un único archivo `espana_completa.geojson`.

#### Visualizar mapa con colores por comunidad y distritos

Para generar visualizaciones con cada comunidad autónoma en un color base distintivo y variaciones del mismo color para sus distritos internos:

```
python visualizar_comunidades.py
```

Este script ofrece varias opciones:
1. Generar un mapa completo de España con todas las comunidades
2. Generar mapas individuales por comunidad autónoma
3. Ambas opciones

Los mapas generados se guardan como archivos PNG de alta resolución.

## Funciones optimizadas para GPU

El módulo `gpu_voronoi_utils.py` ofrece implementaciones optimizadas para GPU de las funciones más intensivas, incluyendo:

- `generar_puntos_dentro_poligono_gpu()`: Generación acelerada de puntos aleatorios dentro de un polígono
- `optimizar_divisiones_voronoi_gpu()`: Optimización de distribución de puntos para Voronoi usando algoritmo Lloyd
- `calcular_distancias_poligono_gpu()`: Cálculo acelerado de distancias entre puntos y vértices

El sistema detecta automáticamente la disponibilidad de GPU y utiliza estas funciones optimizadas cuando es posible.

## Visualización interactiva mejorada

El nuevo visualizador interactivo (`visualizar_interactivo.py`) incluye:

- Agrupación de zonas por municipio
- Popups informativos con estadísticas de cada zona
- Búsqueda de zonas por nombre o municipio
- Herramientas de medición de distancias y áreas
- Diferentes capas base de mapas
- Indicador de coordenadas del cursor
- Leyenda de compacidad de zonas

## Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo LICENSE para más detalles.

## Agradecimientos

- Centro Nacional de Información Geográfica (CNIG) por los datos de líneas límite administrativas
- Desarrolladores de Geopandas, Shapely, Folium y CuPy por sus excelentes herramientas 