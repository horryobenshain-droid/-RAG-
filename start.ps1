$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonPath = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$BackendUrl = "http://127.0.0.1:8000/health"
$FrontendUrl = "http://127.0.0.1:8501"

function Test-HttpOk {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    }
    catch {
        return $false
    }
}

function Wait-HttpOk {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpOk $Url) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

if (-not (Test-Path $PythonPath)) {
    Write-Error "Virtual environment not found. Run: python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt"
}

if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
    Copy-Item (Join-Path $ProjectRoot ".env.example") (Join-Path $ProjectRoot ".env")
    Write-Host "Created .env from .env.example. Please edit model settings if needed." -ForegroundColor Yellow
}

if (Test-HttpOk $BackendUrl) {
    Write-Host "Backend already running: http://127.0.0.1:8000" -ForegroundColor Green
}
else {
    Write-Host "Starting backend..." -ForegroundColor Cyan
    Start-Process `
        -FilePath $PythonPath `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden | Out-Null

    if (-not (Wait-HttpOk $BackendUrl 45)) {
        Write-Error "Backend startup timed out. Try manually: uvicorn app.main:app --reload --port 8000"
    }
}

if (Test-HttpOk $FrontendUrl) {
    Write-Host "Frontend already running: http://127.0.0.1:8501" -ForegroundColor Green
}
else {
    Write-Host "Starting frontend..." -ForegroundColor Cyan
    Start-Process `
        -FilePath $PythonPath `
        -ArgumentList "-m", "streamlit", "run", "ui/streamlit_app.py", "--server.address=127.0.0.1", "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false" `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden | Out-Null

    if (-not (Wait-HttpOk $FrontendUrl 45)) {
        Write-Error "Frontend startup timed out. Try manually: .\.venv\Scripts\python.exe -m streamlit run ui/streamlit_app.py"
    }
}

Start-Process $FrontendUrl
Write-Host "Opened app: $FrontendUrl" -ForegroundColor Green
