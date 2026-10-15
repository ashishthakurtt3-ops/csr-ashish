@echo off
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo Requesting Administrator privileges to start MySQL80 service...
    powershell -Command "Start-Process cmd -ArgumentList '/c net start MySQL80 & echo Service started! & timeout /t 3' -Verb RunAs"
    exit /b
)
net start MySQL80
pause
