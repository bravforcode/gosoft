$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$stateDir = Join-Path $repoRoot ".local-run"

function Read-Value([string]$Path) {
    if (Test-Path $Path) {
        return (Get-Content $Path -Raw).Trim()
    }

    return ""
}

function Test-Pid([string]$PidValue) {
    if (-not $PidValue) {
        return $false
    }

    $process = Get-Process -Id ([int]$PidValue) -ErrorAction SilentlyContinue
    return [bool]$process
}

function Test-Http([string]$Url) {
    try {
        Invoke-WebRequest -Uri $Url -TimeoutSec 2 | Out-Null
        return "ok"
    } catch {
        return "down"
    }
}

$backendPid = Read-Value (Join-Path $stateDir "backend.pid")
$frontendPid = Read-Value (Join-Path $stateDir "frontend.pid")
$backendPort = Read-Value (Join-Path $stateDir "backend.port")
$frontendPort = Read-Value (Join-Path $stateDir "frontend.port")

$rows = @(
    [pscustomobject]@{
        Service = "backend"
        Running = Test-Pid $backendPid
        Health = $(if ($backendPort) { Test-Http "http://127.0.0.1:$backendPort/health" } else { "unknown" })
        Port = $backendPort
        Pid = $backendPid
    },
    [pscustomobject]@{
        Service = "frontend"
        Running = Test-Pid $frontendPid
        Health = $(if ($frontendPort) { Test-Http "http://127.0.0.1:$frontendPort" } else { "unknown" })
        Port = $frontendPort
        Pid = $frontendPid
    }
)

$rows | Format-Table -AutoSize
