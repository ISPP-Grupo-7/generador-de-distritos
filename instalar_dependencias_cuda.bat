@echo off
echo Instalando dependencias para procesamiento geoespacial con GPU...
echo Este script instalara los paquetes necesarios para acelerar el procesamiento usando la RTX 4070.

REM Instalar dependencias base
echo Instalando dependencias base...
py -m pip install -r requirements.txt

REM Configurar para CUDA 12.8 (la versión instalada)
set CUDA_VERSION=12.8

REM Instalar CuPy para la versión de CUDA detectada
echo Instalando CuPy para CUDA %CUDA_VERSION%...
py -m pip install cupy-cuda12x

REM Intentar instalar PyTorch con soporte CUDA como opción alternativa
echo Instalando PyTorch con soporte CUDA...
py -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

echo.
echo Instalacion completada. Ahora puedes ejecutar el script con aceleracion GPU:
echo py main.py
echo.
pause 