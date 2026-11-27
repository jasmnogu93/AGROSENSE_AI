@echo off
title AgroSense AI - Servidor FastAPI + Supabase + MQTT
cd /d "%~dp0backend"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No se encontro el entorno virtual en: %~dp0backend\.venv
    pause
    exit /b 1
)

echo ============================================================================
echo   AGROSENSE AI — INICIANDO SERVIDOR (FastAPI + Supabase Cloud + MQTT)
echo ============================================================================
echo   Dashboard Web (Local) : http://localhost:8000
echo   API Swagger Docs      : http://localhost:8000/docs
echo   Estado Orquideas JSON : http://localhost:8000/api/v1/services/field/status
echo ============================================================================
echo   Para detener el servidor presiona CTRL + C (o cierra esta ventana).
echo.

:: Abre automaticamente el navegador despues de 3 segundos en segundo plano
start "" /b cmd /c "ping -n 4 127.0.0.1 >nul && start http://localhost:8000"

".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
