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

# ── 3.5 Load / prompt for API keys (persisted to .env.local.ps1) ─────────────
$envFile = Join-Path $PSScriptRoot ".env.local.ps1"
if (Test-Path $envFile) {
    Write-Host "[3.5/4] Loading saved API keys from .env.local.ps1" -ForegroundColor DarkGray
    . $envFile
}

if (-not $env:PEXELS_API_KEYS -or $env:PEXELS_API_KEYS.Trim().Length -lt 10) {
    Write-Host ""
    Write-Host "  No PEXELS_API_KEYS set. Videos will use procedural animated backgrounds." -ForegroundColor Yellow
    Write-Host "  Get a free key at https://www.pexels.com/api/ (takes ~30s)." -ForegroundColor Yellow
    $pexInput = Read-Host "W8CSsQysKYGNabsluBJQRoVwUkCg32ha6QFCzzFb3lxdrukxvbBTOqEx"
    if ($pexInput -and $pexInput.Trim().Length -ge 10) {
        $env:PEXELS_API_KEYS = $pexInput.Trim()
        $line = '$env:PEXELS_API_KEYS = "' + $pexInput.Trim() + '"'
        Add-Content -Path $envFile -Value $line -Encoding UTF8
        Write-Host "  Saved to .env.local.ps1 — will auto-load next time." -ForegroundColor Green
    }
}

if ($env:PEXELS_API_KEYS) {
    Write-Host "[3.5/4] Pexels: key loaded (length=$($env:PEXELS_API_KEYS.Length))" -ForegroundColor Green
}
if ($env:PIXABAY_API_KEY) {
    Write-Host "[3.5/4] Pixabay: key loaded" -ForegroundColor Green
}

# Verify ImageMagick command for optional MoviePy tooling paths
$validImageMagick = $false
if ($env:IMAGEMAGICK_BINARY) {
    if ((Test-Path $env:IMAGEMAGICK_BINARY) -or ($env:IMAGEMAGICK_BINARY -eq "auto-detect")) {
        $validImageMagick = $true
    }
}

if (-not $validImageMagick) {
    if (Get-Command magick -ErrorAction SilentlyContinue) {
        $env:IMAGEMAGICK_BINARY = (Get-Command magick).Source
    } elseif (Get-Command convert -ErrorAction SilentlyContinue) {
        $convertPath = (Get-Command convert).Source
        if ($convertPath -and ($convertPath -match "ImageMagick")) {
            $env:IMAGEMAGICK_BINARY = $convertPath
        } else {
            $env:IMAGEMAGICK_BINARY = "auto-detect"
        }
    } else {
        Write-Host "[3/4] ImageMagick not found - installing via winget..." -ForegroundColor Yellow
        winget install --id ImageMagick.ImageMagick -e --accept-package-agreements --accept-source-agreements
        if (Get-Command magick -ErrorAction SilentlyContinue) {
            $env:IMAGEMAGICK_BINARY = (Get-Command magick).Source
        } elseif (Get-Command convert -ErrorAction SilentlyContinue) {
            $convertPath = (Get-Command convert).Source
            if ($convertPath -and ($convertPath -match "ImageMagick")) {
                $env:IMAGEMAGICK_BINARY = $convertPath
            } else {
                $env:IMAGEMAGICK_BINARY = "auto-detect"
            }
        } else {
            # Keep app import-safe even if command is not yet visible in current shell PATH.
            $env:IMAGEMAGICK_BINARY = "auto-detect"
            Write-Host "[3/4] ImageMagick still not visible in PATH; continuing with fallback (auto-detect)." -ForegroundColor Yellow
        }
    }
}

# ── 4. Start server + open browser ───────────────────────────────────────────
$url = "http://127.0.0.1:$Port/"
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
$env:PORT = "$Port"
& $pythonExe main.py
