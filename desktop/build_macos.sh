#!/usr/bin/env bash
# ============================================================
#  Build macOS .app bundle + .dmg
#  Run on macOS only. Requires: python 3.10+, ffmpeg (brew), create-dmg
#  Usage:  bash desktop/build_macos.sh
# ============================================================
set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT_ROOT="$(pwd)"

echo "[1/5] Python: $(which python3)"
PY=python3

echo "[2/5] Installing build dependencies..."
$PY -m pip install -q -r requirements.txt
$PY -m pip install -q -r desktop/requirements-desktop.txt

# Stage bundled ffmpeg if available (brew install ffmpeg)
mkdir -p desktop/ffmpeg
if command -v ffmpeg >/dev/null 2>&1; then
    echo "[3/5] Staging bundled ffmpeg from $(which ffmpeg)"
    cp "$(which ffmpeg)"  desktop/ffmpeg/ffmpeg
    cp "$(which ffprobe)" desktop/ffmpeg/ffprobe
    chmod +x desktop/ffmpeg/ffmpeg desktop/ffmpeg/ffprobe
else
    echo "[3/5] ffmpeg not on PATH - skipping bundle. Install with: brew install ffmpeg"
fi

echo "[4/5] Running PyInstaller..."
rm -rf build dist
$PY -m PyInstaller desktop/QuranReels.spec --noconfirm

if [ ! -d "dist/QuranReels.app" ]; then
    echo "ERROR: dist/QuranReels.app not produced" >&2
    exit 1
fi
echo "      .app ready: dist/QuranReels.app"

echo "[5/5] Building .dmg..."
if command -v create-dmg >/dev/null 2>&1; then
    rm -f dist/QuranReels-1.0.0.dmg
    create-dmg \
        --volname "Quran Reels Generator" \
        --window-size 540 380 \
        --icon-size 96 \
        --icon "QuranReels.app" 130 180 \
        --app-drop-link 410 180 \
        "dist/QuranReels-1.0.0.dmg" \
        "dist/QuranReels.app" || echo "create-dmg failed, .app is still usable"
else
    echo "      create-dmg not installed. Install with: brew install create-dmg"
    echo "      You can still distribute dist/QuranReels.app directly (zip it)."
fi

echo ""
echo "Done. Note: unsigned .app will show 'cannot be opened' on first launch."
echo "Users must right-click -> Open -> Open, or run:"
echo "    xattr -dr com.apple.quarantine dist/QuranReels.app"
