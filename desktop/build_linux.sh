#!/usr/bin/env bash
# ============================================================
#  Build Linux desktop bundle + AppImage
#  Run on Linux only. Tested on Ubuntu 22.04+.
#  Usage:  bash desktop/build_linux.sh
# ============================================================
set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT_ROOT="$(pwd)"

echo "[1/5] Python: $(which python3)"
PY=python3

echo "[2/5] Installing build dependencies..."
$PY -m pip install -q -r requirements.txt
$PY -m pip install -q -r desktop/requirements-desktop.txt

# pywebview on Linux needs a GTK or Qt webengine backend.
# On Ubuntu/Debian: sudo apt install python3-gi gir1.2-webkit2-4.0 libwebkit2gtk-4.0-dev
# Or: pip install pyqt5 pyqtwebengine

mkdir -p desktop/ffmpeg
if command -v ffmpeg >/dev/null 2>&1; then
    echo "[3/5] Staging bundled ffmpeg from $(which ffmpeg)"
    cp "$(which ffmpeg)"  desktop/ffmpeg/ffmpeg
    cp "$(which ffprobe)" desktop/ffmpeg/ffprobe
    chmod +x desktop/ffmpeg/ffmpeg desktop/ffmpeg/ffprobe
else
    echo "[3/5] ffmpeg not on PATH - install with: sudo apt install ffmpeg"
fi

echo "[4/5] Running PyInstaller..."
rm -rf build dist
$PY -m PyInstaller desktop/QuranReels.spec --noconfirm

if [ ! -f "dist/QuranReels/QuranReels" ]; then
    echo "ERROR: dist/QuranReels/QuranReels not produced" >&2
    exit 1
fi
chmod +x dist/QuranReels/QuranReels
echo "      Bundle ready: dist/QuranReels/"

echo "[5/5] Packaging AppImage..."
APPDIR="dist/QuranReels.AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
cp -r dist/QuranReels/* "$APPDIR/usr/bin/"

cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/QuranReels" "$@"
EOF
chmod +x "$APPDIR/AppRun"

cat > "$APPDIR/QuranReels.desktop" <<EOF
[Desktop Entry]
Name=Quran Reels Generator
Exec=QuranReels
Icon=quran_reels
Type=Application
Categories=AudioVideo;Video;
EOF

# Placeholder icon (replace desktop/icon.png with your real icon)
if [ -f desktop/icon.png ]; then
    cp desktop/icon.png "$APPDIR/quran_reels.png"
else
    # 256x256 transparent placeholder
    python3 -c "from PIL import Image; Image.new('RGBA',(256,256)).save('$APPDIR/quran_reels.png')" 2>/dev/null || true
fi

if command -v appimagetool >/dev/null 2>&1; then
    appimagetool "$APPDIR" "dist/QuranReels-1.0.0-x86_64.AppImage"
    echo "      AppImage ready: dist/QuranReels-1.0.0-x86_64.AppImage"
else
    echo "      appimagetool not found. Install from:"
    echo "      https://github.com/AppImage/AppImageKit/releases"
    echo "      Bundle is still usable: dist/QuranReels/QuranReels"
fi

echo "Done."
