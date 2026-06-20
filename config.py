"""
Configuration, paths, constants, FFmpeg/ImageMagick setup.
All directory creation and binary resolution happens at import time.
"""
import os
import sys
import shutil

# ==========================================
# 🔧 ImageMagick Discovery (before moviepy import)
# ==========================================
_im_candidates = ["magick", "convert"] if os.name == "nt" else ["convert", "magick"]
_im_env = os.environ.get("IMAGEMAGICK_BINARY", "").strip()
if _im_env:
    _is_valid_path = os.path.isfile(_im_env)
    if not (_is_valid_path or _im_env == "auto-detect"):
        _resolved_cmd = shutil.which(_im_env)
        if _resolved_cmd and os.path.isfile(_resolved_cmd):
            _im_env = _resolved_cmd
        else:
            _im_env = ""
if not _im_env:
    _resolved_candidates = [shutil.which(c) for c in _im_candidates]
    _im_env = next((p for p in _resolved_candidates if p and os.path.isfile(p)), "auto-detect")
if os.name == "nt" and _im_env.lower() == "convert":
    _im_env = "auto-detect"
os.environ["IMAGEMAGICK_BINARY"] = _im_env

# مهم لـ OAuth مع HuggingFace (HTTPS خارجي، HTTP داخلي)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# ==========================================
# 🔧 FFmpeg Path Configuration
# ==========================================
def _bundled_bin_dirs():
    dirs = []
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        dirs.extend([
            os.path.join(exe_dir, "ffmpeg"),
            os.path.join(exe_dir, "bin"),
            exe_dir,
        ])
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            dirs.extend([
                os.path.join(meipass, "ffmpeg"),
                os.path.join(meipass, "bin"),
                meipass,
            ])
    return dirs

_ffmpeg_ext = ".exe" if os.name == "nt" else ""
_bundled_ffmpeg = [os.path.join(d, "ffmpeg" + _ffmpeg_ext) for d in _bundled_bin_dirs()]
_bundled_ffprobe = [os.path.join(d, "ffprobe" + _ffmpeg_ext) for d in _bundled_bin_dirs()]

_FFMPEG_CANDIDATES = _bundled_ffmpeg + [
    r"D:\Tools\ffmpeg\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe",
    r"C:\ffmpeg\bin\ffmpeg.exe",
    "ffmpeg",  # fallback: rely on system PATH
]
_FFPROBE_CANDIDATES = _bundled_ffprobe + [
    r"D:\Tools\ffmpeg\ffmpeg-8.1.1-full_build\bin\ffprobe.exe",
    r"C:\ffmpeg\bin\ffprobe.exe",
    "ffprobe",
]

def _resolve_binary(candidates):
    import shutil as _shutil
    for c in candidates:
        if os.path.isfile(c):
            return c
        if _shutil.which(c):
            return c
    return candidates[-1]  # last resort

FFMPEG_PATH = _resolve_binary(_FFMPEG_CANDIDATES)
FFPROBE_PATH = _resolve_binary(_FFPROBE_CANDIDATES)

# Tell moviepy where ffmpeg lives
from moviepy.config import change_settings
change_settings({"FFMPEG_BINARY": FFMPEG_PATH})

# Tell pydub where ffmpeg/ffprobe live
from pydub import AudioSegment
AudioSegment.converter = FFMPEG_PATH
AudioSegment.ffprobe = FFPROBE_PATH

# Also inject into PATH for any subprocess calls
_ffmpeg_bin_dir = os.path.dirname(FFMPEG_PATH)
if _ffmpeg_bin_dir and _ffmpeg_bin_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _ffmpeg_bin_dir + os.pathsep + os.environ.get("PATH", "")

# ==========================================
# ⚙️ Directory Configuration
# ==========================================
def app_dir():
    if getattr(sys, "frozen", False): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

EXEC_DIR = app_dir()
# When frozen by PyInstaller onefile, bundled read-only assets live in _MEIPASS
BUNDLE_DIR = getattr(sys, "_MEIPASS", EXEC_DIR)

# User-writable data dir: env override -> platform default -> EXEC_DIR (dev)
def _default_user_data_dir():
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "QuranReels")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/QuranReels")
    return os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "QuranReels")

_env_data = os.environ.get("QURAN_REELS_DATA_DIR", "").strip()
if _env_data:
    USER_DATA_DIR = _env_data
elif getattr(sys, "frozen", False):
    USER_DATA_DIR = _default_user_data_dir()
else:
    USER_DATA_DIR = EXEC_DIR  # dev mode: keep legacy behavior
os.makedirs(USER_DATA_DIR, exist_ok=True)

# API Keys
PEXELS_KEYS_STR = os.environ.get("PEXELS_API_KEYS", "")
PEXELS_API_KEYS = [k.strip() for k in PEXELS_KEYS_STR.split(",") if k.strip()]

# Directories
LOCAL_BGS_DIR = os.path.join(USER_DATA_DIR, "local_bgs")
os.makedirs(LOCAL_BGS_DIR, exist_ok=True)

FFMPEG_EXE = FFMPEG_PATH
os.environ["FFMPEG_BINARY"] = FFMPEG_EXE

default_imagemagick = "magick" if os.name == "nt" else "convert"
try:
    change_settings({"IMAGEMAGICK_BINARY": os.getenv("IMAGEMAGICK_BINARY", default_imagemagick)})
except:
    pass

AudioSegment.converter = FFMPEG_EXE
AudioSegment.ffmpeg = FFMPEG_EXE

# Asset Paths (fonts and UI.html are read-only; live in BUNDLE_DIR when frozen)
FONT_DIR = os.path.join(BUNDLE_DIR, "fonts")
FONT_PATH_ARABIC = os.path.join(FONT_DIR, "Arabic.otf")
FONT_PATH_ENGLISH = os.path.join(FONT_DIR, "English.otf")
VISION_DIR = os.path.join(USER_DATA_DIR, "vision")
UI_PATH = os.path.join(BUNDLE_DIR, "UI.html")

# ✅ الخطوط العربية المتاحة
AVAILABLE_FONTS = {
    'Arabic': os.path.join(FONT_DIR, "Arabic.otf"),
    'Classic': os.path.join(FONT_DIR, "Classic.ttf"),
    'Amiri': os.path.join(FONT_DIR, "Amiri.ttf"),
    'Uthmani': os.path.join(FONT_DIR, "Uthmani.ttf"),
}

# ✅ خط Amiri للأقواس (بيدعم الأقواس المزخرفة)
FONT_PATH_BRACKETS = os.path.join(FONT_DIR, "Amiri.ttf")

# ✅ الخطوط الإنجليزية المتاحة
AVAILABLE_FONTS_EN = {
    'English': os.path.join(FONT_DIR, "English.otf"),
    'Cinzel': os.path.join(FONT_DIR, "Cinzel.ttf"),
    'Playfair': os.path.join(FONT_DIR, "Playfair.ttf"),
    'Lora': os.path.join(FONT_DIR, "Lora.ttf"),
}

def get_font_path(font_name):
    """الحصول على مسار الخط العربي بناءً على الاسم"""
    return AVAILABLE_FONTS.get(font_name, FONT_PATH_ARABIC)

def get_font_path_en(font_name):
    """الحصول على مسار الخط الإنجليزي بناءً على الاسم"""
    return AVAILABLE_FONTS_EN.get(font_name, FONT_PATH_ENGLISH)

# Master Temp Directory (user-writable when bundled)
BASE_TEMP_DIR = os.path.join(USER_DATA_DIR, "temp_workspaces")
OUTPUTS_DIR = os.path.join(USER_DATA_DIR, "outputs")
os.makedirs(BASE_TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(VISION_DIR, exist_ok=True)

def _resolve_videos_download_dir():
    fallback = os.path.join(os.path.expanduser("~"), "Videos", "QuranReels")
    if os.name != "nt":
        return fallback
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\QuranReels") as key:
            val, _ = winreg.QueryValueEx(key, "VideosDir")
            if val:
                return val
    except Exception:
        pass
    return fallback

VIDEOS_DOWNLOAD_DIR = _resolve_videos_download_dir()
os.makedirs(VIDEOS_DOWNLOAD_DIR, exist_ok=True)

# Database Path
DB_PATH = os.path.join(USER_DATA_DIR, "quran_jobs.db")

# 📁 مجلد تخزين التوقيتات
TIMINGS_CACHE_DIR = os.path.join(EXEC_DIR, "cache_timings")

# ==========================================
# 🎵 Audio Filter Profiles
# ==========================================
# فلتر تحسين الصوت (بدون extrastereo عشان ميسببش صدى)
STUDIO_DRY_FILTER = (
    "highpass=f=60, "
    "equalizer=f=200:width_type=h:width=200:g=3, "
    "equalizer=f=8000:width_type=h:width=1000:g=2, "
    "acompressor=threshold=-21dB:ratio=4:attack=200:release=1000, "
    "loudnorm=I=-16:TP=-1.5:LRA=11"
)

AUDIO_FILTER_PROFILES = {
    'studio': STUDIO_DRY_FILTER,
    'mobile': (
        "highpass=f=70, "
        "equalizer=f=220:width_type=h:width=180:g=2, "
        "acompressor=threshold=-20dB:ratio=3.5:attack=150:release=700, "
        "loudnorm=I=-16:TP=-1.5:LRA=9"
    ),
    'youtube': (
        "highpass=f=60, "
        "equalizer=f=180:width_type=h:width=220:g=2, "
        "equalizer=f=6500:width_type=h:width=1200:g=1.5, "
        "acompressor=threshold=-19dB:ratio=3.8:attack=120:release=800, "
        "loudnorm=I=-14:TP=-1.0:LRA=8"
    ),
    'tiktok': (
        "highpass=f=70, "
        "equalizer=f=240:width_type=h:width=200:g=2.5, "
        "equalizer=f=7500:width_type=h:width=1200:g=2, "
        "acompressor=threshold=-20dB:ratio=4:attack=100:release=600, "
        "loudnorm=I=-15:TP=-1.0:LRA=8"
    ),
}

# ==========================================
# 📺 YouTube Configuration
# ==========================================
YOUTUBE_CLIENT_ID = os.environ.get('YOUTUBE_CLIENT_ID', '')
YOUTUBE_CLIENT_SECRET = os.environ.get('YOUTUBE_CLIENT_SECRET', '')
YOUTUBE_REDIRECT_URI = os.environ.get('YOUTUBE_REDIRECT_URI', '')
YOUTUBE_SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

# ✅ كشف بيئة HuggingFace
IS_HUGGINGFACE = bool(os.environ.get('SPACE_ID')) or bool(os.environ.get('SPACE_AUTHOR_NAME'))
