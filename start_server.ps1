# CSR Job Intelligence - Start Server Script
# Run this from the project directory

$projectPath = "D:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)"
$pythonExe = Join-Path $projectPath ".venv\Scripts\python.exe"
$managePy = Join-Path $projectPath "manage.py"

Write-Host "Starting CSR & Job Intelligence Server..." -ForegroundColor Green
Write-Host "Project directory: $projectPath" -ForegroundColor Yellow

& $pythonExe $managePy runserver 127.0.0.1:8000 --insecure