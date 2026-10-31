@echo off
cd /d "%~dp0\.."
title ImpactBridge Subscription Renewal Daemon

echo =====================================================================
echo      IMPACTBRIDGE SUBSCRIPTION AUTOMATED RENEWAL DAEMON
echo =====================================================================
echo.

if exist ".venv\Scripts\python.exe" (
    set "PY_CMD=.venv\Scripts\python.exe"
) else (
    set "PY_CMD=python"
)

echo [INFO] Starting renewal daemon in demo/test mode (polling every 60s)...
echo [INFO] Press CTRL+C to stop.
echo.

"%PY_CMD%" manage.py process_subscription_renewals --daemon --interval 60

pause

