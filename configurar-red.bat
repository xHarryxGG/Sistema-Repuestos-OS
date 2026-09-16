@echo off
chcp 65001 >nul
title Configurar acceso en red - Gestion de Inventario

:: Requiere permisos de administrador
net session >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Este script debe ejecutarse como Administrador.
    echo.
    echo Clic derecho en configurar-red.bat ^> "Ejecutar como administrador"
    echo.
    pause
    exit /b 1
)

echo ============================================
echo   Configurar acceso en red local
echo ============================================
echo.
echo Agregando regla en el Firewall de Windows
echo para permitir conexiones al puerto 8000...
echo.

netsh advfirewall firewall delete rule name="Gestion Inventario" >nul 2>&1
netsh advfirewall firewall add rule name="Gestion Inventario" dir=in action=allow protocol=TCP localport=8000

if errorlevel 1 (
    echo [ERROR] No se pudo configurar el firewall.
    pause
    exit /b 1
)

echo [OK] Firewall configurado correctamente.
echo.
echo Desde otros dispositivos en la misma red WiFi/LAN,
echo abre en el navegador:
echo.
for /f "usebackq tokens=2 delims=:" %%i in (`ipconfig ^| findstr /c:"IPv4"`) do (
    echo   http://%%i:8000
)
echo.
echo Luego ejecuta iniciar.bat en esta PC.
echo.
pause
