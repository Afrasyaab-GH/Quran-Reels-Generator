param(
    [int]$Port = 7860,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Quran Reels Generator - Local Launch   " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Locate Python ─────────────────────────────────────────────────────────
$pythonCandidates = @(
    "D:\Tools\Miniconda\python.exe",
    "D:\Tools\Miniconda\envs\base\python.exe",
    (Get-Command python -ErrorAction SilentlyContinue)?.Source
)
$pythonExe = $pythonCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $pythonExe) { $pythonExe = "python" }   # fallback: rely on PATH

Write-Host "[1/4] Python: $pythonExe" -ForegroundColor Green

# ── 2. Locate / install ffmpeg ────────────────────────────────────────────────
$ffmpegBin = "D:\Tools\ffmpeg\ffmpeg-8.1.1-full_build\bin"
if (Test-Path "$ffmpegBin\ffmpeg.exe") {
    Write-Host "[2/4] FFmpeg: $ffmpegBin" -ForegroundColor Green
    $env:PATH = "$ffmpegBin" + [IO.Path]::PathSeparator + $env:PATH
} elseif (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    Write-Host "[2/4] FFmpeg: found in system PATH" -ForegroundColor Green
} else {
    Write-Host "[2/4] FFmpeg not found — installing via winget..." -ForegroundColor Yellow
    winget install --id Gyan.FFmpeg -e --location "D:\Tools\ffmpeg" --accept-package-agreements --accept-source-agreements
    $env:PATH = "$ffmpegBin" + [IO.Path]::PathSeparator + $env:PATH
    Write-Host "[2/4] FFmpeg installed." -ForegroundColor Green
}

# ── 3. Install / verify dependencies ─────────────────────────────────────────
Write-Host "[3/4] Checking Python dependencies..." -ForegroundColor Green
& $pythonExe -m pip install -q -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Error "pip install failed. Check requirements.txt."
    exit 1
}

# ── 4. Start server + open browser ───────────────────────────────────────────
$url = "http://127.0.0.1:$Port/UI.html"
Write-Host "[4/4] Starting server on $url ..." -ForegroundColor Green
Write-Host ""
Write-Host "  Press Ctrl+C to stop." -ForegroundColor DarkGray
Write-Host ""

if (-not $NoBrowser) {
    # Open browser after 3-second delay (gives server time to start)
    Start-Job -ScriptBlock {
        param($u)
        Start-Sleep -Seconds 3
        Start-Process $u
    } -ArgumentList $url | Out-Null
}

$env:FLASK_APP  = "main.py"
$env:FLASK_ENV  = "production"
& $pythonExe main.py
