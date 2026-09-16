@echo off
chcp 65001 >nul
title Instalacion - Gestion de Inventario
cd /d "%~dp0"

echo ============================================
echo   Instalacion - Gestion de Inventario
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado.
    echo Descargalo desde: https://www.python.org/downloads/
    echo Marca la opcion "Add Python to PATH" al instalar.
    echo.
    pause
    exit /b 1
)

echo [1/3] Creando entorno virtual...
if not exist "venv\Scripts\python.exe" (
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
) else (
    echo       El entorno virtual ya existe.
)

echo [2/3] Instalando dependencias...
venv\Scripts\python.exe -m pip install --upgrade pip >nul
venv\Scripts\pip.exe install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Fallo la instalacion de dependencias.
    pause
    exit /b 1
)

echo [3/3] Inicializando base de datos...
venv\Scripts\python.exe -c "from app.database import init_db; init_db(); print('       Base de datos lista.')"

echo.
echo ============================================
echo   Instalacion completada con exito.
echo   Ejecuta iniciar.bat para abrir la app.
echo ============================================
echo.
pause
