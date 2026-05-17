# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Quran Reels Generator desktop build.

Usage (from project root):
    pyinstaller desktop/QuranReels.spec --noconfirm

Produces a one-folder bundle under dist/QuranReels/ that contains
the launcher executable, all assets, and (if present) a bundled ffmpeg.
"""
import os
import sys
import platform
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, copy_metadata

PROJECT_ROOT = os.path.abspath(os.path.dirname(SPECPATH))  # noqa: F821
IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

APP_NAME = "QuranReels"
ICON_FILE = None
if IS_WIN:
    _ico = os.path.join(PROJECT_ROOT, "desktop", "icon.ico")
    ICON_FILE = _ico if os.path.isfile(_ico) else None
elif IS_MAC:
    _icns = os.path.join(PROJECT_ROOT, "desktop", "icon.icns")
    ICON_FILE = _icns if os.path.isfile(_icns) else None

# ---- read-only data files bundled into the app ----
datas = [
    (os.path.join(PROJECT_ROOT, "UI.html"), "."),
    (os.path.join(PROJECT_ROOT, "fonts"), "fonts"),
]

# Splash icon (for Tk splash window) — bundled at root
_splash_icon = os.path.join(PROJECT_ROOT, "desktop", "icon_512.png")
if os.path.isfile(_splash_icon):
    datas.append((_splash_icon, "."))

# Optional bundled ffmpeg/ffprobe (place binaries in desktop/ffmpeg/ before build)
_ffmpeg_dir = os.path.join(PROJECT_ROOT, "desktop", "ffmpeg")
if os.path.isdir(_ffmpeg_dir):
    datas.append((_ffmpeg_dir, "ffmpeg"))

# MoviePy / PIL / scipy data files
for pkg in ("moviepy", "imageio", "imageio_ffmpeg"):
    try:
        datas.extend(collect_data_files(pkg))
    except Exception:
        pass

# Package metadata (importlib.metadata lookups at runtime — moviepy/imageio need these)
for pkg in (
    "imageio",
    "imageio_ffmpeg",
    "moviepy",
    "decorator",
    "proglog",
    "tqdm",
    "numpy",
    "Pillow",
    "flask",
    "flask_limiter",
    "flask_cors",
    "pydub",
    "requests",
    "deep_translator",
    "pywebview",
):
    try:
        datas.extend(copy_metadata(pkg))
    except Exception:
        pass

# ---- hidden imports (heavy/dynamic modules PyInstaller may miss) ----
hiddenimports = [
    # Refactored app modules (sibling to main.py at project root)
    "main",
    "config",
    "quran_data",
    "i18n",
    "utils",
    "database",
    "jobs",
    "audio",
    "video",
    "routes",
    "batch",
    "youtube_integration",
]
for pkg in (
    "flask",
    "flask_limiter",
    "flask_cors",
    "engineio",
    "socketio",
    "moviepy.editor",
    "moviepy.video.fx.all",
    "moviepy.audio.fx.all",
    "PIL._tkinter_finder",
    "scipy.signal",
    "scipy.ndimage",
    "pydub",
    "webview",
):
    try:
        hiddenimports.extend(collect_submodules(pkg))
    except Exception:
        pass

block_cipher = None

VERSION_FILE = os.path.join(PROJECT_ROOT, "desktop", "version_info.txt")
if not os.path.isfile(VERSION_FILE):
    VERSION_FILE = None

a = Analysis(  # noqa: F821
    [os.path.join(PROJECT_ROOT, "desktop", "launcher.py")],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "notebook",
        "IPython",
        "pytest",
        "test",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

# ---- PyInstaller native splash (shown by bootloader, no Tk needed) ----
_splash_png = os.path.join(PROJECT_ROOT, "desktop", "splash.png")
splash = None
if IS_WIN and os.path.isfile(_splash_png):
    splash = Splash(  # noqa: F821
        _splash_png,
        binaries=a.binaries,
        datas=a.datas,
        text_pos=(20, 270),
        text_size=10,
        text_color="white",
        always_on_top=True,
    )

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    *([splash] if splash else []),
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,            # windowed app, no console flash
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_FILE,
    version=VERSION_FILE,
)

coll = COLLECT(  # noqa: F821
    exe,
    *([splash.binaries] if splash else []),
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)

# macOS .app bundle
if IS_MAC:
    app = BUNDLE(  # noqa: F821
        coll,
        name=f"{APP_NAME}.app",
        icon=ICON_FILE,
        bundle_identifier="com.quranreels.desktop",
        info_plist={
            "CFBundleShortVersionString": "1.0.0",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "10.14",
        },
    )
