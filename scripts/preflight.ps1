#requires -Version 5.1
<#
.SYNOPSIS
    Pre-deployment checks for the CSR Job Intelligence project.

.DESCRIPTION
    Runs bytecode compilation, migration drift detection, deployment checks,
    and a management-command import check. Stops at the first failure.
#>
$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = 'python'
}

function Invoke-Check {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    Write-Host "== $Label ==" -ForegroundColor Cyan
    & $python @Arguments
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED: $Label (exit $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Invoke-Check -Label 'compileall' -Arguments @('-m', 'compileall', '-q', 'config', 'modules', 'scripts')
Invoke-Check -Label 'makemigrations --check --dry-run' -Arguments @('manage.py', 'makemigrations', '--check', '--dry-run')
Invoke-Check -Label 'check --deploy' -Arguments @('manage.py', 'check', '--deploy')
Invoke-Check -Label 'verify_company_homepages --help' -Arguments @('manage.py', 'verify_company_homepages', '--help')

Write-Host 'Preflight passed.' -ForegroundColor Green
