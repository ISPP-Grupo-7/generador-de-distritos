# Script de instalación de dependencias GPU para RTX 4070 (CUDA 12.8)
Write-Host "Instalando dependencias para procesamiento geoespacial con GPU..." -ForegroundColor Green
Write-Host "Este script instalará los paquetes necesarios para acelerar el procesamiento usando la RTX 4070." -ForegroundColor Green
Write-Host ""

# Instalar dependencias base
Write-Host "Instalando dependencias base..." -ForegroundColor Cyan
py -m pip install -r requirements.txt

# Configurar para CUDA 12.8
$CUDA_VERSION = "12.8"
Write-Host "Configurado para CUDA $CUDA_VERSION" -ForegroundColor Cyan

# Instalar CuPy para CUDA 12.x (compatible con 12.8)
Write-Host "Instalando CuPy para CUDA $CUDA_VERSION..." -ForegroundColor Cyan
py -m pip install cupy-cuda12x==13.4.0

# Intentar instalar PyTorch con soporte CUDA como opción alternativa
Write-Host "Instalando PyTorch con soporte CUDA..." -ForegroundColor Cyan
py -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

Write-Host ""
Write-Host "Instalación completada. Ahora puedes ejecutar el script con aceleración GPU:" -ForegroundColor Green
Write-Host "py main.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "El programa debería detectar automáticamente tu GPU RTX 4070 y utilizarla para acelerar el procesamiento." -ForegroundColor Green
Write-Host ""
Write-Host "Para comprobar que CuPy detecta correctamente la GPU, ejecuta:" -ForegroundColor Cyan
Write-Host "py -c 'import cupy as cp; print(cp.cuda.get_device_properties(0))'" -ForegroundColor Yellow

# Pausa para que el usuario pueda leer el mensaje
Write-Host ""
Write-Host "Presiona cualquier tecla para continuar..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") 