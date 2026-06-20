# ============================================================
#  Build the Windows desktop bundle + installer
#  Usage:  .\desktop\build_windows.ps1
#  Output: dist\QuranReels\ (folder) + dist\QuranReels-Setup-1.0.0.exe
# ============================================================
[CmdletBinding()]
param(
    [switch]$SkipInstaller,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Quran Reels - Windows Desktop Build     " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Locate Python
$pyCmd = Get-Command python -ErrorAction SilentlyContinue
$pyPath = if ($pyCmd) { $pyCmd.Source } else { $null }
$pythonCandidates = @(
    "D:\Tools\Miniconda\python.exe",
    $pyPath
)
$pythonExe = $pythonCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $pythonExe) { Write-Error "Python not found"; exit 1 }
Write-Host "[1/5] Python: $pythonExe" -ForegroundColor Green

# 2. Install build deps
Write-Host "[2/5] Installing build dependencies..." -ForegroundColor Green
& $pythonExe -m pip install -q -r requirements.txt
& $pythonExe -m pip install -q -r desktop\requirements-desktop.txt
if ($LASTEXITCODE -ne 0) { Write-Error "pip install failed"; exit 1 }

# 3. Optional: stage bundled ffmpeg (so users don't need it pre-installed)
$ffmpegStageDir = Join-Path $PSScriptRoot "ffmpeg"
if (-not (Test-Path $ffmpegStageDir)) {
    New-Item -ItemType Directory -Path $ffmpegStageDir | Out-Null
}
$ffmpegSrc = "D:\Tools\ffmpeg\ffmpeg-8.1.1-full_build\bin"
if (Test-Path "$ffmpegSrc\ffmpeg.exe") {
    Write-Host "[3/5] Staging bundled ffmpeg from $ffmpegSrc" -ForegroundColor Green
    Copy-Item "$ffmpegSrc\ffmpeg.exe"  $ffmpegStageDir -Force
    Copy-Item "$ffmpegSrc\ffprobe.exe" $ffmpegStageDir -Force
} else {
    Write-Host "[3/5] No local ffmpeg found - skipping bundle. App will require system ffmpeg." -ForegroundColor Yellow
}

# 4. Clean previous builds
if ($Clean) {
    Write-Host "[3.5] Cleaning previous build/dist..." -ForegroundColor DarkGray
    Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
}

# 5. Run PyInstaller
Write-Host "[4/5] Running PyInstaller (this can take 3-8 minutes)..." -ForegroundColor Green
& $pythonExe -m PyInstaller desktop\QuranReels.spec --noconfirm
if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller failed"; exit 1 }

$bundleExe = "dist\QuranReels\QuranReels.exe"
if (-not (Test-Path $bundleExe)) { Write-Error "Bundle missing: $bundleExe"; exit 1 }
$bundleSize = [math]::Round((Get-ChildItem dist\QuranReels -Recurse | Measure-Object Length -Sum).Sum / 1MB, 1)
Write-Host "      Bundle ready: dist\QuranReels\ ($bundleSize MB)" -ForegroundColor Green

# 6. NSIS installer
if (-not $SkipInstaller) {
    $nsisCmd = Get-Command makensis -ErrorAction SilentlyContinue
    $makensis = if ($nsisCmd) { $nsisCmd.Source } else { $null }
    if (-not $makensis) {
        $nsisCandidates = @(
            "C:\Program Files (x86)\NSIS\makensis.exe",
            "C:\Program Files\NSIS\makensis.exe"
        )
        $makensis = $nsisCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    }
    if ($makensis) {
        Write-Host "[5/5] Building installer via NSIS..." -ForegroundColor Green
        & $makensis desktop\installer_windows.nsi
        if ($LASTEXITCODE -eq 0) {
            $installer = Get-ChildItem dist\QuranReels-Setup-*.exe -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($installer) {
                $sizeMB = [math]::Round($installer.Length / 1MB, 1)
                Write-Host "      Installer ready: $($installer.FullName) ($sizeMB MB)" -ForegroundColor Green
            }
        } else { Write-Warning "NSIS compilation failed" }
    } else {
        Write-Host "[5/5] NSIS not installed - skipping installer. Get it at https://nsis.sourceforge.io/" -ForegroundColor Yellow
        Write-Host "      Bundle is still usable: launch dist\QuranReels\QuranReels.exe directly." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Done." -ForegroundColor Cyan
