@echo off
cd /d "%~dp0"
title ImpactBridge Enterprise Django Portal (Port 8000)
echo =====================================================================
echo      IMPACTBRIDGE ENTERPRISE DJANGO ARCHITECTURE ^& INTELLIGENCE
echo =====================================================================
echo.

:: 1. Detect Python / Virtual Environment
if exist "%~dp0.venv\Scripts\python.exe" (
    echo [OK] Using project virtual environment: .venv
    set "PY_CMD=%~dp0.venv\Scripts\python.exe"
) else (
    echo [INFO] Virtual environment not found, trying system Python...
    set "PY_CMD=python"
)

:: 2. Free port 8000 if already occupied
echo [INFO] Checking port 8000...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo [INFO] Freeing port 8000 (PID: %%a)...
    taskkill /F /PID %%a >nul 2>&1
)

:: 3. Launch browser automatically after a short delay in background
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8000"

:: 4. Start Django Production-Ready Server
echo.
echo =====================================================================
echo  * Enterprise Portal:      http://localhost:8000
echo  * Custom Admin Portal:    http://localhost:8000/admin-portal/
echo  * Django Admin Panel:     http://localhost:8000/django-admin/
echo  * Admin login:           user 'admin' (set the password with: python manage.py changepassword admin)
echo =====================================================================
echo.
echo [INFO] Starting Django Web Server on http://127.0.0.1:8000...
echo [INFO] Keep this window OPEN while using the platform. Press CTRL+C to stop.
echo.

"%PY_CMD%" manage.py runserver 127.0.0.1:8000

echo.
echo [SERVER STOPPED] If you see an error above, press any key to close.
pause
