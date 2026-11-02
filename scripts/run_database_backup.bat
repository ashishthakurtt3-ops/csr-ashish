@echo off
cd /d "%~dp0\.."
title ImpactBridge Database Backup Utility

echo =====================================================================
echo      IMPACTBRIDGE AUTOMATED MYSQL BACKUP UTILITY
echo =====================================================================
echo.

if exist ".venv\Scripts\python.exe" (
    set "PY_CMD=.venv\Scripts\python.exe"
) else (
    set "PY_CMD=python"
)

echo [INFO] Creating verified MySQL database backup (Retention: 30 daily, 12 weekly)...
"%PY_CMD%" manage.py backup_database --daily-retention 30 --weekly-retention 12

echo.
echo [DONE] Database backup complete.
echo.

if "%1"=="--silent" goto end
if "%1"=="/silent" goto end
if "%1"=="--non-interactive" goto end
if "%1"=="/non-interactive" goto end
pause

:end
