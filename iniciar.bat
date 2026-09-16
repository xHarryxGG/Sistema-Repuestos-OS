@echo off
chcp 65001 >nul
title Gestion de Inventario
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo.
    echo [AVISO] No se encontro el entorno virtual.
    echo Ejecuta primero instalar.bat
    echo.
    pause
    exit /b 1
)

echo ============================================
echo   Gestion de Inventario y Ventas
echo ============================================
echo.
echo   En esta PC:     http://localhost:8000
echo.
echo   Desde otros dispositivos en la red:
for /f "usebackq tokens=2 delims=:" %%i in (`ipconfig ^| findstr /c:"IPv4"`) do (
    echo                   http://%%i:8000
)
echo.
echo   Para detener el servidor: Ctrl+C
echo.
echo   Si otros dispositivos no conectan, ejecuta
echo   configurar-red.bat como Administrador.
echo ============================================
echo.
echo   Abriendo el navegador en 3 segundos...
echo.

start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8000"

venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo.
echo Servidor detenido.
pause
