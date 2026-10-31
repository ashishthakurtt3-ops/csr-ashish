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

echo [INFO] Creating verified MySQL database backup and pruning old files...
"%PY_CMD%" manage.py backup_database --retention 10

echo.
echo [DONE] Database backup complete.
echo.
pause

