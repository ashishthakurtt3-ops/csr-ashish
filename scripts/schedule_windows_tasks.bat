@echo off
cd /d "%~dp0\.."
title ImpactBridge Task Scheduler Setup

echo =====================================================================
echo      IMPACTBRIDGE WINDOWS TASK SCHEDULER INSTALLER
echo =====================================================================
echo.
echo This script registers two background tasks in Windows Task Scheduler:
echo   1. ImpactBridge_Daily_Database_Backup (Daily at 02:00 AM)
echo   2. ImpactBridge_Hourly_Subscription_Renewals (Every 1 hour)
echo.

set "PROJ_DIR=%CD%"
set "PY_CMD=%PROJ_DIR%\.venv\Scripts\python.exe"

if not exist "%PY_CMD%" (
    echo [ERROR] Virtual environment Python not found at %PY_CMD%!
    pause
    exit /b 1
)

echo [1/2] Registering Daily Database Backup Task...
schtasks /create /tn "ImpactBridge_Daily_Database_Backup" /tr "\"%PY_CMD%\" \"%PROJ_DIR%\manage.py\" backup_database --retention 14" /sc daily /st 02:00 /f

echo [2/2] Registering Hourly Subscription Renewals Task...
schtasks /create /tn "ImpactBridge_Hourly_Subscription_Renewals" /tr "\"%PY_CMD%\" \"%PROJ_DIR%\manage.py\" process_subscription_renewals" /sc hourly /f

echo.
echo =====================================================================
echo [SUCCESS] Windows scheduled tasks registered successfully!
echo To review them, open taskschd.msc or run: schtasks /query /tn "ImpactBridge*"
echo =====================================================================
pause

