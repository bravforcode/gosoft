$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$stateDir = Join-Path $repoRoot ".local-run"

function Stop-FromFile([string]$Name) {
    $pidFile = Join-Path $stateDir "$Name.pid"
    if (-not (Test-Path $pidFile)) {
        return
    }

    $pidValue = (Get-Content $pidFile -Raw).Trim()
    if ($pidValue) {
        Stop-Process -Id ([int]$pidValue) -Force -ErrorAction SilentlyContinue
    }

    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $stateDir "$Name.port") -Force -ErrorAction SilentlyContinue
}

Stop-FromFile -Name "backend"
Stop-FromFile -Name "frontend"

Write-Host "Local processes stopped."
