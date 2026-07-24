param(
    [ValidateSet("start", "stop", "restart", "status", "logs")]
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ProductionEnv = Join-Path $ProjectRoot ".env.production"
$ProductionEnvExample = Join-Path $ProjectRoot ".env.production.example"
$SecretDirectory = Join-Path $PSScriptRoot "secrets"
$PasswordFile = Join-Path $SecretDirectory "auth_password"

function Invoke-Compose {
    param([string[]]$Arguments)

    & docker compose --env-file $ProductionEnv @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed with exit code $LASTEXITCODE."
    }
}

function Initialize-DeploymentFiles {
    if (-not (Test-Path -LiteralPath $ProductionEnv)) {
        Copy-Item -LiteralPath $ProductionEnvExample -Destination $ProductionEnv
        Write-Host "Created .env.production. Review model and port settings before public use." -ForegroundColor Yellow
    }

    if (-not (Test-Path -LiteralPath $PasswordFile)) {
        New-Item -ItemType Directory -Path $SecretDirectory -Force | Out-Null
        $securePassword = Read-Host "Create the RAG Studio password (at least 12 characters)" -AsSecureString
        $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
        try {
            $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
            if ($plainPassword.Length -lt 12) {
                throw "The deployment password must contain at least 12 characters."
            }
            $utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
            [IO.File]::WriteAllText($PasswordFile, $plainPassword, $utf8WithoutBom)
        }
        finally {
            if ($pointer -ne [IntPtr]::Zero) {
                [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
            }
            $plainPassword = $null
        }
        Write-Host "Created deploy/secrets/auth_password." -ForegroundColor Green
    }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is not installed or is not available in PATH."
}

Set-Location $ProjectRoot

switch ($Action) {
    "start" {
        Initialize-DeploymentFiles
        Invoke-Compose @("up", "--detach", "--build")
        Invoke-Compose @("ps")
        Write-Host "RAG Studio: http://127.0.0.1:8080" -ForegroundColor Green
    }
    "stop" {
        Invoke-Compose @("down")
    }
    "restart" {
        Initialize-DeploymentFiles
        Invoke-Compose @("up", "--detach", "--build", "--force-recreate")
        Invoke-Compose @("ps")
    }
    "status" {
        Invoke-Compose @("ps")
    }
    "logs" {
        Invoke-Compose @("logs", "--follow", "--tail", "200")
    }
}
