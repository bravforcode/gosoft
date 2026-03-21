param(
    [ValidateSet("all", "backend", "frontend")]
    [string]$Target = "all",
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5175,
    [bool]$WithHistory = $true,
    [bool]$SkipStartupTasks = $false
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$stateDir = Join-Path $repoRoot ".local-run"
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"

function Ensure-Directory([string]$Path) {
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Write-Utf8([string]$Path, [string]$Value) {
    Set-Content -Path $Path -Value $Value -Encoding utf8
}

function Get-PythonCommand {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return @("py", "-3")
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return @("python")
    }

    throw "Python 3 was not found on PATH."
}

function New-Venv([string]$VenvDir) {
    $pythonCommand = Get-PythonCommand
    if ($pythonCommand.Length -gt 1) {
        & $pythonCommand[0] $pythonCommand[1] -m venv $VenvDir
        return
    }

    & $pythonCommand[0] -m venv $VenvDir
}

function Stop-Port([int]$Port) {
    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
        foreach ($connection in $connections) {
            Stop-Process -Id $connection.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    } catch {
    }
}

function Wait-Http([string]$Url, [int]$Attempts = 90) {
    for ($index = 0; $index -lt $Attempts; $index++) {
        try {
            Invoke-WebRequest -Uri $Url -TimeoutSec 2 | Out-Null
            return
        } catch {
            Start-Sleep -Seconds 1
        }
    }

    throw "Timed out waiting for $Url"
}

function Ensure-BackendEnv([string]$BackendEnvPath, [int]$FrontendPortValue, [bool]$SkipTasksValue) {
    if (Test-Path $BackendEnvPath) {
        return
    }

    $secretKey = -join ((1..4) | ForEach-Object { [guid]::NewGuid().ToString("N") })
    $apiKey = -join ((1..2) | ForEach-Object { [guid]::NewGuid().ToString("N") })
    $skipValue = $SkipTasksValue.ToString().ToLowerInvariant()
    $allowedOrigins = @(
        "http://127.0.0.1:$FrontendPortValue",
        "http://localhost:$FrontendPortValue",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost"
    ) | ConvertTo-Json -Compress

    $content = @"
APP_NAME=Smart Inventory Vision
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=$secretKey
API_KEY=$apiKey
DATABASE_URL=sqlite+aiosqlite:///./data/siv.db
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=30
CAMERA_0_URL=0
CAMERA_0_NAME=Main Entrance Camera
CAMERA_0_ZONE=Zone A
CAMERA_PROCESSING_FPS=2.0
CAMERA_DISPLAY_FPS=25.0
YOLO_MODEL_PATH=yolov8n.pt
YOLO_CONFIDENCE_THRESHOLD=0.45
CLAUDE_VISION_ENABLED=false
CLAUDE_ANALYSIS_INTERVAL=10
CLAUDE_MODEL=claude-sonnet-4-20250514
STOCK_LOW_THRESHOLD=0.50
STOCK_CRITICAL_THRESHOLD=0.25
STOCK_EMPTY_THRESHOLD=0.10
AUTO_PO_APPROVAL_LIMIT=5000
ALLOWED_ORIGINS=$allowedOrigins
DEMO_MODE=true
SKIP_STARTUP_TASKS=$skipValue
"@

    Write-Utf8 -Path $BackendEnvPath -Value $content.Trim() + "`n"
}

Ensure-Directory $stateDir
Ensure-Directory (Join-Path $backendDir "data")
Ensure-Directory (Join-Path $backendDir "data\evidence")

$backendPidFile = Join-Path $stateDir "backend.pid"
$frontendPidFile = Join-Path $stateDir "frontend.pid"
$backendPortFile = Join-Path $stateDir "backend.port"
$frontendPortFile = Join-Path $stateDir "frontend.port"
$backendLog = Join-Path $stateDir "backend.log"
$backendErrLog = Join-Path $stateDir "backend.err.log"
$frontendLog = Join-Path $stateDir "frontend.log"
$frontendErrLog = Join-Path $stateDir "frontend.err.log"
$backendEnvPath = Join-Path $backendDir ".env"

if ($Target -in @("all", "backend")) {
    Stop-Port -Port $BackendPort

    $venvDir = Join-Path $backendDir ".venv"
    if (-not (Test-Path $venvDir)) {
        New-Venv -VenvDir $venvDir
    }

    Ensure-BackendEnv -BackendEnvPath $backendEnvPath -FrontendPortValue $FrontendPort -SkipTasksValue $SkipStartupTasks

    $venvPython = Join-Path $venvDir "Scripts\python.exe"

    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r (Join-Path $backendDir "requirements.txt")

    $seedArgs = @((Join-Path $backendDir "scripts\seed_database.py"))
    if ($WithHistory) {
        $seedArgs += "--with-history"
    }
    & $venvPython $seedArgs

    $backendProcess = Start-Process `
        -FilePath $venvPython `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$BackendPort") `
        -WorkingDirectory $backendDir `
        -RedirectStandardOutput $backendLog `
        -RedirectStandardError $backendErrLog `
        -PassThru

    Write-Utf8 -Path $backendPidFile -Value "$($backendProcess.Id)"
    Write-Utf8 -Path $backendPortFile -Value "$BackendPort"
    Wait-Http -Url "http://127.0.0.1:$BackendPort/health"
}

if ($Target -in @("all", "frontend")) {
    Stop-Port -Port $FrontendPort

    Push-Location $frontendDir
    try {
        if (Test-Path (Join-Path $frontendDir "package-lock.json")) {
            & npm.cmd ci
        } else {
            & npm.cmd install
        }
    } finally {
        Pop-Location
    }

    Write-Utf8 -Path (Join-Path $frontendDir ".env.local") -Value @("VITE_API_URL=http://127.0.0.1:$BackendPort", "VITE_WS_URL=ws://127.0.0.1:$BackendPort") -join "`n"

    $frontendProcess = Start-Process `
        -FilePath "npm.cmd" `
        -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "$FrontendPort", "--strictPort") `
        -WorkingDirectory $frontendDir `
        -RedirectStandardOutput $frontendLog `
        -RedirectStandardError $frontendErrLog `
        -PassThru

    Write-Utf8 -Path $frontendPidFile -Value "$($frontendProcess.Id)"
    Write-Utf8 -Path $frontendPortFile -Value "$FrontendPort"
    Wait-Http -Url "http://127.0.0.1:$FrontendPort"
}

Write-Host ""
Write-Host "Local stack ready"
Write-Host "Backend : http://127.0.0.1:$BackendPort"
Write-Host "Frontend: http://127.0.0.1:$FrontendPort"
