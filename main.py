import re
import sys
import io
import os
import uuid
import shutil
import threading
import time
import datetime
import logging
import traceback
import gc
import math
import random
import requests
import json
import sqlite3
import zipfile
from functools import lru_cache  # ✅ Added for caching
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# مهم لـ OAuth مع HuggingFace (HTTPS خارجي، HTTP داخلي)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
from flask import Flask, request, jsonify, send_file, g
from flask_cors import CORS
from contextlib import contextmanager

# Configure ImageMagick discovery before importing moviepy.editor.
# This prevents import-time crashes on fresh Windows setups.
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
    # Windows "convert" can resolve to a non-ImageMagick utility.
    _im_env = "auto-detect"
os.environ["IMAGEMAGICK_BINARY"] = _im_env

# Media Processing Imports
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import PIL.Image

# Patch for older PIL versions if needed
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import (
    ImageClip, VideoFileClip, AudioFileClip, 
    CompositeVideoClip, ColorClip, concatenate_videoclips
)
from moviepy.audio.AudioClip import concatenate_audioclips
from moviepy.config import change_settings
from proglog import ProgressBarLogger
from pydub import AudioSegment
from deep_translator import GoogleTranslator

# ==========================================
# 🔧 FFmpeg Path Configuration
# ==========================================
# Explicit paths so app works even when ffmpeg is not on the system PATH yet
# When bundled by PyInstaller, look beside the executable / in _MEIPASS first.
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
change_settings({"FFMPEG_BINARY": FFMPEG_PATH})

# Tell pydub where ffmpeg/ffprobe live
AudioSegment.converter = FFMPEG_PATH
AudioSegment.ffprobe = FFPROBE_PATH

# Also inject into PATH for any subprocess calls
_ffmpeg_bin_dir = os.path.dirname(FFMPEG_PATH)
if _ffmpeg_bin_dir and _ffmpeg_bin_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _ffmpeg_bin_dir + os.pathsep + os.environ.get("PATH", "")

# ==========================================
# ⚙️ Configuration & Setup
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

def _as_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ('1', 'true', 'yes', 'on')
    return default

def build_audio_filter_chain(profile='studio', use_denoise=False, use_deess=False):
    base = AUDIO_FILTER_PROFILES.get(str(profile or 'studio').lower(), STUDIO_DRY_FILTER)
    filters = [base]
    if _as_bool(use_denoise):
        filters.insert(0, "afftdn=nf=-25")
    if _as_bool(use_deess):
        filters.append("deesser=i=0.45:m=0.5:f=0.5:s=o")
    return ", ".join(filters)


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

PEXELS_KEYS_STR = os.environ.get("PEXELS_API_KEYS", "")
PEXELS_API_KEYS = [k.strip() for k in PEXELS_KEYS_STR.split(",") if k.strip()]

LOCAL_BGS_DIR = os.path.join(USER_DATA_DIR, "local_bgs")
os.makedirs(LOCAL_BGS_DIR, exist_ok=True)

FFMPEG_EXE = "ffmpeg"
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

API_I18N = {
    'invalid_data': {
        'ar': 'بيانات غير صحيحة',
        'en': 'Invalid request data',
    },
    'job_not_found': {
        'ar': 'المهمة غير موجودة',
        'en': 'Job not found',
    },
    'file_not_found': {
        'ar': 'الملف غير موجود',
        'en': 'File not found',
    },
    'no_items_provided': {
        'ar': 'لم يتم إرسال عناصر للدفعة',
        'en': 'No items provided',
    },
    'batch_id_required': {
        'ar': 'مطلوب batchId',
        'en': 'batchId is required',
    },
    'batch_not_found': {
        'ar': 'الدفعة غير موجودة',
        'en': 'Batch not found',
    },
    'cannot_cancel_completed_batch': {
        'ar': 'لا يمكن إلغاء دفعة مكتملة',
        'en': 'Cannot cancel completed batch',
    },
    'youtube_not_configured': {
        'ar': 'ميزة يوتيوب غير مُعدة. اضبط متغيرات البيئة YOUTUBE_CLIENT_ID و YOUTUBE_CLIENT_SECRET.',
        'en': 'YouTube integration is not configured. Set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET.',
    },
    'failed_auth_url': {
        'ar': 'فشل إنشاء رابط المصادقة',
        'en': 'Failed to generate auth URL',
    },
    'missing_session_or_job': {
        'ar': 'sessionId أو jobId مفقود',
        'en': 'Missing sessionId or jobId',
    },
    'video_not_found': {
        'ar': 'الفيديو غير موجود',
        'en': 'Video not found',
    },
    'video_file_not_found': {
        'ar': 'ملف الفيديو غير موجود',
        'en': 'Video file not found',
    },
    'youtube_not_authorized': {
        'ar': 'الحساب غير مرتبط بيوتيوب',
        'en': 'Not authorized with YouTube',
    },
    'schedule_too_far': {
        'ar': 'لا يمكن جدولة الفيديو لأكثر من 6 أشهر في المستقبل',
        'en': 'Video cannot be scheduled more than 6 months in the future',
    },
    'schedule_time_error': {
        'ar': 'خطأ في وقت الجدولة: {detail}',
        'en': 'Schedule time error: {detail}',
    },
    'invalid_surah_range': {
        'ar': 'رقم السورة يجب أن يكون بين 1 و 114، تم إرسال: {surah}',
        'en': 'Surah number must be between 1 and 114. Received: {surah}',
    },
    'invalid_start_ayah': {
        'ar': 'آية البداية يجب أن تكون أكبر من 0، تم إرسال: {start_ayah}',
        'en': 'Start ayah must be greater than 0. Received: {start_ayah}',
    },
    'invalid_ayah_order': {
        'ar': 'آية البداية ({start_ayah}) أكبر من آية النهاية ({end_ayah})',
        'en': 'Start ayah ({start_ayah}) cannot be greater than end ayah ({end_ayah})',
    },
    'end_ayah_out_of_range': {
        'ar': 'سورة {surah_name} تحتوي على {max_verses} آية فقط، تم طلب آية {end_ayah}',
        'en': 'Surah {surah_name} has only {max_verses} ayahs, but ayah {end_ayah} was requested',
    },
    'youtube_upload_failed': {
        'ar': 'فشل رفع الفيديو إلى يوتيوب: {detail}',
        'en': 'YouTube upload failed: {detail}',
    },
    'unexpected_server_error': {
        'ar': 'حدث خطأ غير متوقع في الخادم',
        'en': 'Unexpected server error occurred',
    },
}


def get_request_lang(payload=None):
    if isinstance(payload, dict):
        lang = str(payload.get('lang', '')).lower()
        if lang in ('ar', 'en'):
            return lang

    q_lang = str(request.args.get('lang', '')).lower()
    if q_lang in ('ar', 'en'):
        return q_lang

    accept = str(request.headers.get('Accept-Language', '')).lower()
    if accept.startswith('en'):
        return 'en'
    return 'ar'


def tr_api(key, lang='ar', **kwargs):
    value = API_I18N.get(key, {}).get(lang) or API_I18N.get(key, {}).get('ar') or key
    if kwargs:
        try:
            return value.format(**kwargs)
        except Exception:
            return value
    return value

# ==========================================
# 🗄️ Database Setup (SQLite for Persistence)
# ==========================================
DB_PATH = os.path.join(USER_DATA_DIR, "quran_jobs.db")

def get_db():
    """Get database connection for current request"""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(exception):
    """Close database connection at end of request"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database tables with session support"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Jobs table - for persistence across restarts (مع دعم session_id)
    c.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL DEFAULT 'pending',
        percent INTEGER DEFAULT 0,
        eta TEXT DEFAULT '--:--',
        output_path TEXT,
        error TEXT,
        should_stop INTEGER DEFAULT 0,
        created_at REAL,
        completed_at REAL,
        config_json TEXT,
        workspace TEXT,
        session_id TEXT
    )''')
    
    # History table - for user download history (مع دعم session_id)
    c.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT,
        title TEXT,
        reciter TEXT,
        surah INTEGER,
        start_ayah INTEGER,
        end_ayah INTEGER,
        quality TEXT,
        fps TEXT,
        download_filename TEXT,
        created_at REAL,
        session_id TEXT,
        FOREIGN KEY (job_id) REFERENCES jobs(id)
    )''')
    
    # Batch jobs table - for batch export
    c.execute('''CREATE TABLE IF NOT EXISTS batch_jobs (
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL DEFAULT 'pending',
        total_jobs INTEGER DEFAULT 0,
        completed_jobs INTEGER DEFAULT 0,
        failed_jobs INTEGER DEFAULT 0,
        current_job_id TEXT,
        current_job_index INTEGER DEFAULT 0,
        config_json TEXT,
        created_at REAL,
        started_at REAL,
        completed_at REAL
    )''')
    
    # Batch items table - individual jobs in a batch
    c.execute('''CREATE TABLE IF NOT EXISTS batch_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id TEXT,
        job_id TEXT,
        position INTEGER,
        surah INTEGER,
        start_ayah INTEGER,
        end_ayah INTEGER,
        status TEXT DEFAULT 'pending',
        output_path TEXT,
        error TEXT,
        created_at REAL,
        FOREIGN KEY (batch_id) REFERENCES batch_jobs(id),
        FOREIGN KEY (job_id) REFERENCES jobs(id)
    )''')
    
    # Migration: إضافة session_id للجداول القديمة لو مش موجودة
    try:
        c.execute("SELECT session_id FROM jobs LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE jobs ADD COLUMN session_id TEXT")
        print("✅ Added session_id to jobs table")
    
    try:
        c.execute("SELECT session_id FROM history LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE history ADD COLUMN session_id TEXT")
        print("✅ Added session_id to history table")
    
    # Migration: إضافة output_path و error لـ batch_items
    try:
        c.execute("SELECT output_path FROM batch_items LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE batch_items ADD COLUMN output_path TEXT")
        print("✅ Added output_path to batch_items table")
    
    try:
        c.execute("SELECT error FROM batch_items LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE batch_items ADD COLUMN error TEXT")
        print("✅ Added error to batch_items table")
    
    # Migration: إضافة video_started_at لـ batch_items
    try:
        c.execute("SELECT video_started_at FROM batch_items LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE batch_items ADD COLUMN video_started_at REAL")
        print("✅ Added video_started_at to batch_items table")
    
    # Migration: إضافة avg_video_time لـ batch_jobs
    try:
        c.execute("SELECT avg_video_time FROM batch_jobs LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE batch_jobs ADD COLUMN avg_video_time REAL")
        print("✅ Added avg_video_time to batch_jobs table")
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

def db_create_job(job_id, workspace, config=None, session_id=None):
    """Create a new job in database with session support"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO jobs (id, status, percent, created_at, workspace, config_json, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)''', 
              (job_id, 'pending', 0, time.time(), workspace, json.dumps(config) if config else None, session_id))
    conn.commit()
    conn.close()

def db_update_job(job_id, **kwargs):
    """Update job in database"""
    if not kwargs:
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [job_id]
    
    c.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()

def db_get_job(job_id):
    """Get job from database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def db_get_all_jobs(status=None, limit=50):
    """Get all jobs, optionally filtered by status"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if status:
        c.execute("SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?", (status, limit))
    else:
        c.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,))
    
    rows = c.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def db_get_pending_jobs():
    """Get all pending/processing jobs for recovery"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM jobs WHERE status IN ('pending', 'processing')")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def db_add_history(job_id, title, reciter, surah, start_ayah, end_ayah, quality, fps, filename, session_id=None):
    """Add entry to history with session support"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO history (job_id, title, reciter, surah, start_ayah, end_ayah, quality, fps, download_filename, created_at, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (job_id, title, reciter, surah, start_ayah, end_ayah, quality, fps, filename, time.time(), session_id))
    conn.commit()
    conn.close()

def db_get_history(limit=20, session_id=None):
    """Get history entries filtered by session"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if session_id:
        # فلترة حسب session_id
        c.execute('''SELECT h.*, j.output_path, j.status 
                     FROM history h 
                     LEFT JOIN jobs j ON h.job_id = j.id 
                     WHERE h.session_id = ?
                     ORDER BY h.created_at DESC LIMIT ?''', (session_id, limit))
    else:
        # بدون فلترة (للتوافق مع الإصدارات القديمة)
        c.execute('''SELECT h.*, j.output_path, j.status 
                     FROM history h 
                     LEFT JOIN jobs j ON h.job_id = j.id 
                     ORDER BY h.created_at DESC LIMIT ?''', (limit,))
    
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def db_cleanup_old_jobs(hours=24):
    """Clean up jobs older than specified hours"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    threshold = time.time() - (hours * 3600)
    
    # Get old completed jobs
    c.execute("SELECT id, workspace, output_path FROM jobs WHERE created_at < ? AND status IN ('complete', 'error', 'cancelled')", (threshold,))
    old_jobs = c.fetchall()
    
    # Clean up files
    for job in old_jobs:
        # حذف مجلد العمل المؤقت
        if job['workspace'] and os.path.exists(job['workspace']):
            try:
                shutil.rmtree(job['workspace'], ignore_errors=True)
            except:
                pass
        
        # حذف ملف الفيديو النهائي من outputs
        if job['output_path'] and os.path.exists(job['output_path']):
            try:
                os.remove(job['output_path'])
            except:
                pass
    
    # Delete from database
    c.execute("DELETE FROM jobs WHERE created_at < ? AND status IN ('complete', 'error', 'cancelled')", (threshold,))
    c.execute("DELETE FROM history WHERE created_at < ?", (threshold,))
    
    conn.commit()
    conn.close()
    print(f"🧹 Cleaned up {len(old_jobs)} old jobs and their video files")

# ==========================================
# 📦 Batch Job Management Functions
# ==========================================

def db_create_batch(batch_id, total_jobs, config):
    """Create a new batch job in database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO batch_jobs (id, status, total_jobs, completed_jobs, failed_jobs, config_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)''', 
              (batch_id, 'pending', total_jobs, 0, 0, json.dumps(config), time.time()))
    conn.commit()
    conn.close()

def db_update_batch(batch_id, **kwargs):
    """Update batch job in database"""
    if not kwargs:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [batch_id]
    c.execute(f"UPDATE batch_jobs SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()

def db_get_batch(batch_id):
    """Get batch job from database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM batch_jobs WHERE id = ?", (batch_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def db_add_batch_item(batch_id, job_id, position, surah, start_ayah, end_ayah):
    """Add an item to batch"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO batch_items (batch_id, job_id, position, surah, start_ayah, end_ayah, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (batch_id, job_id, position, surah, start_ayah, end_ayah, 'pending', time.time()))
    conn.commit()
    conn.close()

def db_update_batch_item(batch_id, job_id, **kwargs):
    """Update batch item"""
    if not kwargs:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [batch_id, job_id]
    c.execute(f"UPDATE batch_items SET {set_clause} WHERE batch_id = ? AND job_id = ?", values)
    conn.commit()
    conn.close()

def db_get_batch_items(batch_id):
    """Get all items in a batch"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM batch_items WHERE batch_id = ? ORDER BY position", (batch_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def db_get_pending_batches():
    """Get all pending/running batches"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM batch_jobs WHERE status IN ('pending', 'running')")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Data Constants
VERSE_COUNTS = {1: 7, 2: 286, 3: 200, 4: 176, 5: 120, 6: 165, 7: 206, 8: 75, 9: 129, 10: 109, 11: 123, 12: 111, 13: 43, 14: 52, 15: 99, 16: 128, 17: 111, 18: 110, 19: 98, 20: 135, 21: 112, 22: 78, 23: 118, 24: 64, 25: 77, 26: 227, 27: 93, 28: 88, 29: 69, 30: 60, 31: 34, 32: 30, 33: 73, 34: 54, 35: 45, 36: 83, 37: 182, 38: 88, 39: 75, 40: 85, 41: 54, 42: 53, 43: 89, 44: 59, 45: 37, 46: 35, 47: 38, 48: 29, 49: 18, 50: 45, 51: 60, 52: 49, 53: 62, 54: 55, 55: 78, 56: 96, 57: 29, 58: 22, 59: 24, 60: 13, 61: 14, 62: 11, 63: 11, 64: 18, 65: 12, 66: 12, 67: 30, 68: 52, 69: 52, 70: 44, 71: 28, 72: 28, 73: 20, 74: 56, 75: 40, 76: 31, 77: 50, 78: 40, 79: 46, 80: 42, 81: 29, 82: 19, 83: 36, 84: 25, 85: 22, 86: 17, 87: 19, 88: 26, 89: 30, 90: 20, 91: 15, 92: 21, 93: 11, 94: 8, 95: 8, 96: 19, 97: 5, 98: 8, 99: 8, 100: 11, 101: 11, 102: 8, 103: 3, 104: 9, 105: 5, 106: 4, 107: 7, 108: 3, 109: 6, 110: 3, 111: 5, 112: 4, 113: 5, 114: 6}
SURAH_NAMES =['الفاتحة', 'البقرة', 'آل عمران', 'النساء', 'المائدة', 'الأنعام', 'الأعراف', 'الأنفال', 'التوبة', 'يونس', 'هود', 'يوسف', 'الرعد', 'إبراهيم', 'الحجر', 'النحل', 'الإسراء', 'الكهف', 'مريم', 'طه', 'الأنبياء', 'الحج', 'المؤمنون', 'النور', 'الفرقان', 'الشعراء', 'النمل', 'القصص', 'العنكبوت', 'الروم', 'لقمان', 'السجدة', 'الأحزاب', 'سبأ', 'فاطر', 'يس', 'الصافات', 'ص', 'الزمر', 'غافر', 'فصلت', 'الشورى', 'الزخرف', 'الدخان', 'الجاثية', 'الأحقاف', 'محمد', 'الفتح', 'الحجرات', 'ق', 'الذاريات', 'الطور', 'النجم', 'القمر', 'الرحمن', 'الواقعة', 'الحديد', 'المجادلة', 'الحشر', 'الممتحنة', 'الصف', 'الجمعة', 'المنافقون', 'التغابن', 'الطلاق', 'التحريم', 'الملك', 'القلم', 'الحاقة', 'المعارج', 'نوح', 'الجن', 'المزمل', 'المدثر', 'القيامة', 'الإنسان', 'المرسلات', 'النبأ', 'النازعات', 'عبس', 'التكوير', 'الانفطار', 'المطففين', 'الانشقاق', 'البروج', 'الطارق', 'الأعلى', 'الغاشية', 'الفجر', 'البلد', 'الشمس', 'الليل', 'الضحى', 'الشرح', 'التين', 'العلق', 'القدر', 'البينة', 'الزلزلة', 'العاديات', 'القارعة', 'التكاثر', 'العصر', 'الهمزة', 'الفيل', 'قريش', 'الماعون', 'الكوثر', 'الكافرون', 'النصر', 'المسد', 'الإخلاص', 'الفلق', 'الناس']


def get_surah_name(surah_num, lang='ar'):
    if 1 <= surah_num <= len(SURAH_NAMES):
        arabic_name = SURAH_NAMES[surah_num - 1]
        if lang == 'en':
            return f"Surah {surah_num} ({arabic_name})"
        return arabic_name
    if lang == 'en':
        return f"Surah {surah_num}"
    return f"سورة {surah_num}"


def get_surah_list(lang='ar'):
    if lang == 'en':
        return [f"Surah {idx + 1} ({name})" for idx, name in enumerate(SURAH_NAMES)]
    return SURAH_NAMES

# ✅ مواضيع آمنة للخلفيات العشوائية (للـ Batch Export)
SAFE_TOPICS = ['sky clouds timelapse', 'galaxy stars space', 'ocean waves slow motion', 'forest trees drone', 'waterfall nature', 'mountains fog', 'mosque architecture', 'islamic pattern', 'nature landscape', 'sunrise golden hour', 'night stars milky way', 'desert sand dunes', 'autumn forest', 'spring flowers', 'rain drops', 'snow falling', 'northern lights aurora', 'lake reflection', 'river flowing', 'birds flying sunset']

SCENE_PACK_QUERIES = {
    'nature_calm': ['nature landscape', 'forest trees drone', 'waterfall nature', 'lake reflection'],
    'night_sky': ['night stars milky way', 'galaxy stars space', 'northern lights aurora'],
    'ocean': ['ocean waves slow motion', 'sea horizon sunset', 'river flowing'],
    'desert': ['desert sand dunes', 'golden hour dunes', 'mountains fog'],
}

def choose_background_query(custom_query, scene_pack):
    if custom_query and str(custom_query).strip():
        return custom_query
    pack_key = str(scene_pack or '').strip().lower()
    pack_queries = SCENE_PACK_QUERIES.get(pack_key)
    if pack_queries:
        return random.choice(pack_queries)
    return random.choice(SAFE_TOPICS)

# ==========================================
# ✅ Input Validation - التحقق من صحة المدخلات
# ==========================================
class ValidationError(Exception):
    """استثناء مخصص لأخطاء التحقق"""
    pass

def validate_ayah_range(surah, start_ayah, end_ayah, lang='ar'):
    """
    التحقق من صحة نطاق الآيات
    يرجع True لو صحيح، أو يرفع ValidationError لو فيه خطأ
    """
    # التحقق من رقم السورة
    if not (1 <= surah <= 114):
        raise ValidationError(tr_api('invalid_surah_range', lang, surah=surah))
    
    # التحقق من أن آية البداية موجبة
    if start_ayah < 1:
        raise ValidationError(tr_api('invalid_start_ayah', lang, start_ayah=start_ayah))
    
    # التحقق من ترتيب الآيات
    if start_ayah > end_ayah:
        raise ValidationError(tr_api('invalid_ayah_order', lang, start_ayah=start_ayah, end_ayah=end_ayah))
    
    # التحقق من عدد آيات السورة
    max_verses = VERSE_COUNTS.get(surah, 286)
    if end_ayah > max_verses:
        surah_name = get_surah_name(surah, lang)
        raise ValidationError(tr_api('end_ayah_out_of_range', lang, surah_name=surah_name, max_verses=max_verses, end_ayah=end_ayah))
    
    # تحذير لو عدد الآيات كبير (أكثر من 20)
    ayah_count = end_ayah - start_ayah + 1
    if ayah_count > 20:
        print(f"⚠️ تحذير: عدد الآيات ({ayah_count}) كبير جداً - قد يستغرق وقتاً طويلاً")
    
    return True

# 🚀 Reciters Config — verified against https://mp3quran.net/api/v3/reciters (Hafs - Murattal)
NEW_RECITERS_CONFIG = {
    # ── المشاهير ──
    'مشاري العفاسي': (123, "https://server8.mp3quran.net/afs/"),
    'عبدالرحمن السديس': (54, "https://server11.mp3quran.net/sds/"),
    'سعود الشريم': (31, "https://server7.mp3quran.net/shur/"),
    'ماهر المعيقلي': (102, "https://server12.mp3quran.net/maher/"),
    'ياسر الدوسري': (92, "https://server11.mp3quran.net/yasser/"),
    'ناصر القطامي': (86, "https://server6.mp3quran.net/qtm/"),
    'عبدالباسط عبدالصمد': (51, "https://server7.mp3quran.net/basit/"),
    'محمد صديق المنشاوي': (112, "https://server10.mp3quran.net/minsh/"),
    'محمود خليل الحصري': (118, "https://server13.mp3quran.net/husr/"),
    'سعد الغامدي': (30, "https://server7.mp3quran.net/s_gmd/"),
    'هاني الرفاعي': (89, "https://server8.mp3quran.net/hani/"),
    'علي الحذيفي': (74, "https://server9.mp3quran.net/hthfi/"),
    'إسلام صبحي': (253, "https://server14.mp3quran.net/islam/Rewayat-Hafs-A-n-Assem/"),
    # ── قراء معروفون ──
    'أبو بكر الشاطري': (4, "https://server11.mp3quran.net/shatri/"),
    'أحمد بن علي العجمي': (5, "https://server10.mp3quran.net/ajm/"),
    'إدريس أبكر': (12, "https://server6.mp3quran.net/abkr/"),
    'خالد الجليل': (20, "https://server10.mp3quran.net/jleel/"),
    'خليفة الطنيجي': (24, "https://server12.mp3quran.net/tnjy/"),
    'صلاح بو خاطر': (46, "https://server8.mp3quran.net/bu_khtr/"),
    'عبدالله الجهني': (62, "https://server13.mp3quran.net/jhn/"),
    'عبدالله المطرود': (59, "https://server8.mp3quran.net/mtrod/"),
    'علي جابر': (76, "https://server11.mp3quran.net/a_jbr/"),
    'فارس عباد': (81, "https://server8.mp3quran.net/frs_a/"),
    'محمد أيوب': (109, "https://server8.mp3quran.net/ayyub/"),
    'محمد جبريل': (111, "https://server8.mp3quran.net/jbrl/"),
    'محمود علي البنا': (121, "https://server8.mp3quran.net/bna/"),
    'توفيق الصايغ': (17, "https://server6.mp3quran.net/twfeeq/"),
    'سامي الدوسري': (35, "https://server8.mp3quran.net/sami_dosr/"),
    'أحمد الحذيفي': (205, "https://server8.mp3quran.net/ahmad_huth/"),
    # ── قراء النخبة الجدد ──
    'أحمد النفيس': (259, "https://server16.mp3quran.net/nufais/Rewayat-Hafs-A-n-Assem/"),
    'وديع اليمني': (219, "https://server6.mp3quran.net/wdee3/"),
    'بندر بليلة': (217, "https://server6.mp3quran.net/balilah/"),
    'منصور السالمي': (245, "https://server14.mp3quran.net/mansor/"),
    'رعد الكردي': (221, "https://server6.mp3quran.net/kurdi/"),
}

# Legacy alt-source map kept for backward compatibility with cached jobs.
# Names duplicated in NEW_RECITERS_CONFIG above are intentionally NOT listed here
# so the verified mp3quran URL is used.
OLD_RECITERS_MAP = {}

# 🎯 MP3Quran IDs للقراء (للتوقيتات الدقيقة) — auto-derived from NEW_RECITERS_CONFIG
MP3QURAN_IDS = {name: rid for name, (rid, _url) in NEW_RECITERS_CONFIG.items()}

# 📁 مجلد تخزين التوقيتات
TIMINGS_CACHE_DIR = os.path.join(EXEC_DIR, "cache_timings")

# خريطة عكسية لتحويل الـ ID للاسم العربي
RECITER_ID_TO_NAME = {v: k for k, v in OLD_RECITERS_MAP.items()}
# إضافة أسماء القراء الجدد (الاسم العربي = الاسم العربي)
for name in NEW_RECITERS_CONFIG.keys():
    RECITER_ID_TO_NAME[name] = name

RECITERS_MAP = {**{k: k for k in NEW_RECITERS_CONFIG.keys()}, **OLD_RECITERS_MAP}

# ✅ خريطة من الـ ID (اللي في OLD_RECITERS_MAP) للـ mp3quran ID (لو موجود)
# القراء القدام اللي عندهم توقيتات في mp3quran
OLD_RECITER_TO_MP3QURAN_ID = {
    'Yasser_Ad-Dussary_128kbps': None,      # مش موجود في mp3quran
    'Maher_AlMuaiqly_64kbps': None,          # مش موجود في mp3quran  
    'Nasser_Alqatami_128kbps': None,         # مش موجود في mp3quran
    'Minshawy_Murattal_128kbps': None,       # مش موجود في mp3quran
}

# 📖 نصوص الآيات للحساب الذكي (مختصر - أهم السور)
AYAH_TEXTS_CACHE = {}

def load_ayah_texts():
    """تحميل نصوص الآيات من ملف أو API"""
    global AYAH_TEXTS_CACHE
    if AYAH_TEXTS_CACHE:
        return AYAH_TEXTS_CACHE
    
    # محاولة التحميل من ملف محلي
    quran_file = os.path.join(EXEC_DIR, "quran_text.json")
    if os.path.exists(quran_file):
        try:
            with open(quran_file, 'r', encoding='utf-8') as f:
                AYAH_TEXTS_CACHE = json.load(f)
            return AYAH_TEXTS_CACHE
        except:
            pass
    return {}

def smart_estimate_by_length(surah, ayah, reciter_key):
    """
    حساب ذكي للمدة بناءً على طول الآية
    
    المعادلة: duration = base_time + (char_count × time_per_char)
    """
    # متوسط سرعة القراءة لكل قارئ (حرف/ثانية)
    READER_SPEEDS = {
        'Alafasy_64kbps': 0.12,           # العفاسي بطيء - 0.12 ث/حرف
        'Abu_Bakr_Ash-Shaatree_128kbps': 0.10,
        'Yasser_Ad-Dussary_128kbps': 0.10,
        'Abdurrahmaan_As-Sudais_64kbps': 0.09,
        'Maher_AlMuaiqly_64kbps': 0.10,
        'Saood_ash-Shuraym_64kbps': 0.10,
        'Nasser_Alqatami_128kbps': 0.11,
        'Minshawy_Murattal_128kbps': 0.11,
        # القراء الجدد
        'احمد النفيس': 0.10,
        'وديع اليماني': 0.11,
        'بندر بليلة': 0.10,
        'ادريس أبكر': 0.09,
        'منصور السالمي': 0.10,
        'رعد الكردي': 0.10,
        'أحمد العجمي': 0.09,
        'محمود خليل الحصري': 0.11,
    }
    
    # وقت ثابت (بداية + نهاية + وقفات)
    BASE_TIME = 1.5  # ثانية
    
    # سرعة القارئ (افتراضي 0.10 ث/حرف)
    time_per_char = READER_SPEEDS.get(reciter_key, 0.10)
    
    # طول الآية التقريبي
    # نستخدم متوسط طول الآية حسب موقعها في السورة
    ayah_length = estimate_ayah_length(surah, ayah)
    
    # الحساب
    duration = BASE_TIME + (ayah_length * time_per_char)
    
    return max(duration, 2.0)  # أدنى حد 2 ثانية

def estimate_ayah_length(surah, ayah):
    """
    تقدير طول الآية بناءً على إحصائيات السورة
    """
    # متوسط أطوال الآيات لكل سورة (من بيانات حقيقية)
    SURAH_AVG_LENGTHS = {
        1: 20,   # الفاتحة - آيات قصيرة
        2: 150,  # البقرة - آيات طويلة
        3: 120,  # آل عمران
        36: 80,  # يس
        55: 40,  # الرحمن
        67: 35,  # الملك
        78: 45,  # النبأ
        112: 15, # الإخلاص - قصيرة جداً
        113: 20, # الفلق
        114: 20, # الناس
    }
    
    # المتوسط الافتراضي
    avg_length = SURAH_AVG_LENGTHS.get(surah, 50)
    
    # تعديل حسب موقع الآية
    verse_count = VERSE_COUNTS.get(surah, 100)
    position_ratio = ayah / verse_count
    
    # الآيات في بداية السورة غالباً أطول في السور المدنية
    # والآيات في النهاية أقصر في بعض السور
    if surah in [2, 3, 4]:  # سور مدنية طويلة
        if position_ratio < 0.3:
            avg_length *= 1.3  # البداية أطول
        elif position_ratio > 0.8:
            avg_length *= 0.8  # النهاية أقصر
    
    return int(avg_length)

app = Flask(__name__, static_folder=EXEC_DIR)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 🛡️ Rate Limiter - حماية من الإفراط في الطلبات
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["5000 per day", "1000 per hour"],
    storage_uri="memory://",  # تخزين في الذاكرة
)

app.teardown_appcontext(close_db)

# ==========================================
# 🧠 Job Management (RAM + SQLite for Persistence)
# ==========================================
JOBS = {}  # RAM cache for fast access
JOBS_LOCK = threading.Lock()

# ==========================================
def create_job(config=None, session_id=None):
    """Create a new job - stores in RAM and SQLite with session support"""
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(BASE_TEMP_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    # Store in RAM for fast access
    with JOBS_LOCK:
        JOBS[job_id] = {
            'id': job_id, 
            'percent': 0, 
            'status': 'pending', 
            'eta': '--:--', 
            'is_running': True, 
            'is_complete': False, 
            'output_path': None, 
            'error': None, 
            'should_stop': False, 
            'created_at': time.time(), 
            'workspace': job_dir,
            'session_id': session_id,
            'background_source_used': 'unknown',
            'background_fetch_error': None
        }
    
    # Store in SQLite for persistence
    db_create_job(job_id, job_dir, config, session_id)
    
    return job_id

def update_job_status(job_id, percent, status, eta=None):
    """Update job status - RAM + SQLite"""
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id]['percent'] = percent
            JOBS[job_id]['status'] = status
            if eta: JOBS[job_id]['eta'] = eta
    
    # Update in SQLite ( throttled - every 5% or on completion)
    if percent % 5 == 0 or percent >= 100 or 'complete' in status.lower() or 'error' in status.lower():
        db_data = {'percent': percent, 'status': status}
        if eta:
            db_data['eta'] = eta
        db_update_job(job_id, **db_data)

def update_job_metadata(job_id, **kwargs):
    """Update lightweight in-memory metadata fields for diagnostics."""
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(kwargs)

def get_job(job_id):
    """Get job - try RAM first, then SQLite"""
    with JOBS_LOCK:
        if job_id in JOBS:
            return JOBS[job_id]
    
    # Not in RAM, try SQLite
    db_job = db_get_job(job_id)
    if db_job:
        # Reconstruct job dict for compatibility
        return {
            'id': db_job['id'],
            'percent': db_job['percent'],
            'status': db_job['status'],
            'eta': db_job['eta'],
            'is_running': db_job['status'] in ('pending', 'processing'),
            'is_complete': db_job['status'] == 'complete',
            'output_path': db_job['output_path'],
            'error': db_job['error'],
            'should_stop': bool(db_job['should_stop']),
            'created_at': db_job['created_at'],
            'workspace': db_job['workspace'],
            'background_source_used': db_job.get('background_source_used', 'unknown') if isinstance(db_job, dict) else 'unknown',
            'background_fetch_error': db_job.get('background_fetch_error') if isinstance(db_job, dict) else None
        }
    return None

def check_stop(job_id):
    """Check if job should stop"""
    job = get_job(job_id)
    if not job:
        # Job not found in RAM or SQLite - might have been cleaned up
        # Don't raise error, just log and continue (job might have been completed)
        print(f"[WARNING] Job {job_id} not found in check_stop - assuming completed or cleaned up")
        return
    if job.get('should_stop', False):
        raise Exception("Stopped by user")

def cleanup_job(job_id):
    """Remove job from RAM (keep in SQLite for history)"""
    with JOBS_LOCK:
        job = JOBS.pop(job_id, None)
    # Don't delete files - keep them for download
    # Files will be cleaned up by background_cleanup after 12h

class ScopedQuranLogger(ProgressBarLogger):
    def __init__(self, job_id):
        super().__init__()
        self.job_id = job_id
        self.start_time = None

    def bars_callback(self, bar, attr, value, old_value=None):
        if bar == 't':
            check_stop(self.job_id)
            total = self.bars[bar]['total']
            if total > 0:
                percent = int((value / total) * 100)
                if self.start_time is None: self.start_time = time.time()
                elapsed = time.time() - self.start_time
                rem_str = "00:00"
                if elapsed > 0 and value > 0:
                    rate = value / elapsed
                    remaining = (total - value) / rate
                    rem_str = str(datetime.timedelta(seconds=int(remaining)))[2:] if remaining > 0 else "00:00"
                update_job_status(self.job_id, percent, f"جاري التصدير... {percent}%", eta=rem_str)

# ==========================================
# 🛠️ Helper Functions & Optimization
# ==========================================

@lru_cache(maxsize=10)
def get_cached_font(font_path, size):
    try: return ImageFont.truetype(font_path, size)
    except: return ImageFont.load_default()

def detect_silence(sound, thresh):
    t = 0
    while t < len(sound) and sound[t:t+10].dBFS < thresh: t += 10
    return t

def smart_download(url, dest_path, job_id):
    check_stop(job_id)
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(dest_path, 'wb') as f:
                counter = 0
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk: 
                        f.write(chunk)
                        counter += 1
                        if counter % 100 == 0: 
                            check_stop(job_id)
        # Verify file was downloaded
        if not os.path.exists(dest_path) or os.path.getsize(dest_path) == 0:
            raise Exception(f"Downloaded file is empty or missing: {dest_path}")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to download {url}: {e}")
        raise Exception(f"Failed to download: {url}")

def detect_leading_silence(sound, silence_threshold=-50.0, chunk_size=10):
    trim_ms = 0
    assert chunk_size > 0
    while trim_ms < len(sound) and sound[trim_ms:trim_ms+chunk_size].dBFS < silence_threshold:
        trim_ms += chunk_size
    return trim_ms

def process_mp3quran_audio(reciter_name, surah, ayah, idx, workspace_dir, job_id):
    reciter_id, server_url = NEW_RECITERS_CONFIG[reciter_name]
    cache_dir = os.path.join(EXEC_DIR, "cache_mp3quran", str(reciter_id))
    os.makedirs(cache_dir, exist_ok=True)
    full_audio_path = os.path.join(cache_dir, f"{surah:03d}.mp3")
    timings_path = os.path.join(cache_dir, f"{surah:03d}.json")

    if not os.path.exists(full_audio_path) or not os.path.exists(timings_path):
        smart_download(f"{server_url}{surah:03d}.mp3", full_audio_path, job_id)
        check_stop(job_id)
        t_data = requests.get(f"https://mp3quran.net/api/v3/ayat_timing?surah={surah}&read={reciter_id}").json()
        timings = {item['ayah']: {'start': item['start_time'], 'end': item['end_time']} for item in t_data}
        with open(timings_path, 'w') as f: json.dump(timings, f)

    with open(timings_path, 'r') as f:
        t = json.load(f)[str(ayah)]
    
    check_stop(job_id)
    seg = AudioSegment.from_file(full_audio_path)[t['start']:t['end']]
    
    # ✅ حفظ بصيغة WAV لتجنب MP3 padding
    out = os.path.join(workspace_dir, f'part{idx}.wav')
    seg.export(out, format="wav")
    
    return out

def download_audio(reciter_key, surah, ayah, idx, workspace_dir, job_id):
    if reciter_key in NEW_RECITERS_CONFIG:
        return process_mp3quran_audio(reciter_key, surah, ayah, idx, workspace_dir, job_id)
    
    # للقراء القدام (everyayah.com) - ننزل MP3 ونحوله لـ WAV
    url = f'https://everyayah.com/data/{reciter_key}/{surah:03d}{ayah:03d}.mp3'
    temp_mp3 = os.path.join(workspace_dir, f'part{idx}_temp.mp3')
    smart_download(url, temp_mp3, job_id)
    
    snd = AudioSegment.from_file(temp_mp3)
    start, end = detect_silence(snd, snd.dBFS-20), detect_silence(snd.reverse(), snd.dBFS-20)
    trimmed = snd[max(0, start-30):len(snd)-max(0, end-30)]
    
    # ✅ حفظ بصيغة WAV بدون fade أو silence
    out = os.path.join(workspace_dir, f'part{idx}.wav')
    trimmed.export(out, format="wav")
    
    # نحذف الـ temp MP3
    if os.path.exists(temp_mp3): os.remove(temp_mp3)
    
    return out

def get_text(surah, ayah):
    try:
        t = requests.get(f'https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/quran-simple').json()['data']['text']
        if surah not in [1, 9] and ayah == 1:
            # إصلاح: حذف البسملة كاملة (بسم الله الرحمن الرحيم)
            # النمط يطابق 4 كلمات: بسم + الله + الرحمن + الرحيم
            t = re.sub(r'^بِسْمِ \S+ \S+ \S+\s*', '', t).strip()
        return t
    except: return "Text Error"

def get_en_text(surah, ayah):
    try: return requests.get(f'http://api.alquran.cloud/v1/ayah/{surah}:{ayah}/en.sahih').json()['data']['text']
    except: return ""

# 🆕 دالة تقطيع النصوص للريلز (5 كلمات كحد أقصى للسطر)
def split_into_chunks(text, words_per_chunk=5):
    words = text.split()
    if not words: return []
    return [" ".join(words[i:i + words_per_chunk]) for i in range(0, len(words), words_per_chunk)]

def to_arabic_numeral(num):
    """تحويل الأرقام الإنجليزية لعربية"""
    arabic_digits = '٠١٢٣٤٥٦٧٨٩'
    return ''.join(arabic_digits[int(d)] for d in str(num))

def create_vignette_mask(w, h):
    Y, X = np.ogrid[:h, :w]
    mask = np.clip((np.sqrt((X - w/2)**2 + (Y - h/2)**2) / np.sqrt((w/2)**2 + (h/2)**2)) * 1.16, 0, 1) ** 3 
    mask_img = np.zeros((h, w, 4), dtype=np.uint8)
    mask_img[:, :, 3] = (mask * 255).astype(np.uint8)
    return ImageClip(mask_img, ismask=False)

def apply_background_effects(clip, effect_type='enhance', strength=1.0):
    """تحسين الخلفيات بتأثيرات بصرية / Enhance backgrounds with visual effects"""
    try:
        def process_frame(frame):
            frame = frame.astype(np.float32)
            
            if effect_type == 'enhance':
                # ✅ تحسين التباين والسطوع مع الحفاظ على الألوان الطبيعية
                frame = frame / 255.0
                # زيادة السطوع قليلاً للوضوح
                frame = np.clip(frame * (1.05 * strength), 0, 1)
                # زيادة التباين بدقة
                mean = frame.mean()
                frame = mean + (frame - mean) * (1.2 * strength)
                frame = np.clip(frame, 0, 1) * 255
                
            elif effect_type == 'blur_soft':
                # ✅ تمويه ناعم لتحسين وضوح النصوص (blur background for text readability)
                from scipy.ndimage import gaussian_filter
                blur_amount = int(3 * strength)
                for c in range(min(3, frame.shape[2])):  # فقط RGB (تجاهل Alpha)
                    frame[:,:,c] = gaussian_filter(frame[:,:,c] / 255.0, blur_amount) * 255
                    
            elif effect_type == 'darken':
                # ✅ تغميق الخلفية مع الحفاظ على التفاصيل
                frame = frame / 255.0
                frame = frame * (0.85 * strength + 0.15)  # تقليل السطوع
                frame = np.clip(frame, 0, 1) * 255
                
            elif effect_type == 'saturate':
                # ✅ زيادة تشبع الألوان للحصول على ألوان غنية
                from PIL import Image, ImageEnhance
                img = Image.fromarray(frame.astype(np.uint8))
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(1.3 * strength)
                frame = np.array(img).astype(np.float32)
                
            return frame.astype(np.uint8)
        
        # تطبيق التأثير على كل إطار
        return clip.fl_image(process_frame)
    except:
        return clip  # إذا حدث خطأ، أرجع الـ clip الأصلي

def fetch_from_multiple_sources(query, count, aspect_ratio='9:16', job_id=None):
    """جلب الخلفيات من مصادر متعددة / Fetch backgrounds from multiple sources"""
    all_videos = []
    
    # المصدر الأول: Pexels (الأساسي)
    try:
        pexels_videos = fetch_video_pool("", query, count=count, job_id=job_id, aspect_ratio=aspect_ratio)
        all_videos.extend(pexels_videos)
    except:
        pass
    
    # المصدر الثاني: محاولة Pixabay إذا لم نجد ما يكفي
    try:
        if len(all_videos) < count:
            pixabay_key = os.environ.get("PIXABAY_API_KEY", "")
            if pixabay_key:
                url = f"https://pixabay.com/api/videos/?key={pixabay_key}&q={query}&per_page={count}"
                r = requests.get(url, timeout=10)
                if r.status_code == 200:
                    for vid in r.json().get('hits', [])[:count - len(all_videos)]:
                        check_stop(job_id)
                        # اختيار أفضل جودة
                        best_file = max(vid.get('videos', {}).values(), 
                                      key=lambda x: x.get('width', 0) * x.get('height', 0))
                        path = os.path.join(VISION_DIR, f"pixabay_bg_{vid['id']}.mp4")
                        if not os.path.exists(path):
                            smart_download(best_file['url'], path, job_id)
                        all_videos.append(path)
    except:
        pass
    
    return all_videos if all_videos else []

def create_gradient_overlay(w, h, color_top=(0, 0, 0), color_bottom=(0, 0, 0), opacity=0.3):
    """إنشاء تدرج لوني / Create gradient overlay for better text contrast"""
    img = Image.new('RGB', (w, h))
    pixels = img.load()
    
    for y in range(h):
        ratio = y / h
        r = int(color_top[0] * (1 - ratio) + color_bottom[0] * ratio)
        g = int(color_top[1] * (1 - ratio) + color_bottom[1] * ratio)
        b = int(color_top[2] * (1 - ratio) + color_bottom[2] * ratio)
        
        for x in range(w):
            pixels[x, y] = (r, g, b)
    
    return ImageClip(np.array(img)).set_opacity(opacity)

# ==========================================
# � Procedural Animated Background (no API needed)
# ==========================================
# Palettes of (top_color, bottom_color) — used when no video sources are available.
_PROCEDURAL_PALETTES = [
    ((20, 30, 80),   (120, 50, 130)),   # twilight purple
    ((10, 30, 60),   (60, 130, 180)),   # ocean blue
    ((50, 20, 80),   (180, 80, 120)),   # mystic aurora
    ((30, 60, 90),   (200, 140, 80)),   # desert dusk
    ((15, 45, 50),   (90, 180, 160)),   # emerald mist
    ((40, 20, 60),   (220, 110, 60)),   # sunset glow
    ((10, 20, 40),   (50, 90, 180)),    # midnight sky
    ((25, 50, 30),   (130, 180, 90)),   # forest dawn
]

def _radial_gradient_frame(w, h, top_rgb, bot_rgb, cx_ratio=0.5, cy_ratio=0.3, radius_ratio=1.2):
    """Generate a single radial-vertical gradient frame as a numpy array (uint8 RGB)."""
    # Vertical gradient base
    ys = np.linspace(0, 1, h, dtype=np.float32).reshape(h, 1)
    base = (np.array(top_rgb, dtype=np.float32) * (1 - ys) +
            np.array(bot_rgb, dtype=np.float32) * ys)            # h x 3
    img = np.tile(base.reshape(h, 1, 3), (1, w, 1))              # h x w x 3
    # Radial highlight (subtle glow)
    cx, cy = int(w * cx_ratio), int(h * cy_ratio)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    max_r = max(w, h) * radius_ratio
    glow = np.clip(1.0 - dist / max_r, 0.0, 1.0) ** 2          # h x w
    highlight = np.array([255, 230, 200], dtype=np.float32) * 0.18
    img += glow[..., None] * highlight
    return np.clip(img, 0, 255).astype(np.uint8)

def create_procedural_bg(w, h, duration, seed=None):
    """Beautiful animated gradient background — guaranteed fallback when no videos found.
    Slowly drifts the highlight position and blends two palettes for a calm cinematic feel.
    """
    rng = random.Random(seed)
    pal_a = rng.choice(_PROCEDURAL_PALETTES)
    pal_b = rng.choice(_PROCEDURAL_PALETTES)
    # Pre-render 6 keyframes and let MoviePy interpolate via a make_frame closure.
    n_keys = 6
    keys = []
    for i in range(n_keys):
        t = i / (n_keys - 1)
        top = tuple(int(pal_a[0][c] * (1 - t) + pal_b[0][c] * t) for c in range(3))
        bot = tuple(int(pal_a[1][c] * (1 - t) + pal_b[1][c] * t) for c in range(3))
        cx = 0.3 + 0.4 * t
        cy = 0.25 + 0.15 * math.sin(t * math.pi)
        keys.append(_radial_gradient_frame(w, h, top, bot, cx, cy))

    def make_frame(t):
        # Map t in [0, duration] to a position in [0, n_keys - 1]
        pos = (t / max(duration, 0.01)) * (n_keys - 1)
        i0 = int(pos)
        i1 = min(i0 + 1, n_keys - 1)
        a = pos - i0
        return (keys[i0].astype(np.float32) * (1 - a) +
                keys[i1].astype(np.float32) * a).astype(np.uint8)

    from moviepy.editor import VideoClip
    return VideoClip(make_frame, duration=duration)

# ==========================================
# �🎨 Visual Elements
# ==========================================

def create_text_clip(text, duration, target_w, scale_factor=1.0, glow=False, style=None, font_path=None):
    if style is None: style = {}

    color = style.get('arColor', '#ffffff')
    size_mult = float(style.get('arSize', '1.0'))
    stroke_c = style.get('arOutC', '#000000')
    stroke_w = int(style.get('arOutW', '4'))
    has_shadow = style.get('arShadow', True)  # ✅ مفعّل افتراضياً
    shadow_c = style.get('arShadowC', '#000000')

    # ✅ استخدام الخط المختار أو الافتراضي
    if font_path is None:
        font_path = FONT_PATH_ARABIC

    # ✅ تكبير الخط الافتراضي (UthmanTN1) عشانه صغير بطبيعته
    font_boost = 1.15 if 'Arabic.otf' in font_path else 1.0

    # الخط كبير لأنه سطر واحد
    final_fs = int(55 * scale_factor * size_mult * font_boost)
    font = get_cached_font(font_path, final_fs)

    # ✅ خط Amiri للأقواس المزخرفة (بيظهرها صح)
    font_brackets = get_cached_font(FONT_PATH_BRACKETS, final_fs)

    # ✅ فصل النص عن الأقواس المزخرفة
    import re
    bracket_match = re.search(r'([﴾﴿]+.*[﴾﴿]+)$', text)
    if bracket_match:
        main_text = text[:bracket_match.start()].strip()
        bracket_text = '﴾' + bracket_match.group(1)[1:-1] + '﴿'
    else:
        main_text = text
        bracket_text = ""

    img = Image.new('RGBA', (target_w, int(180 * scale_factor * size_mult)), (0,0,0,0))
    draw = ImageDraw.Draw(img)

    # حساب عرض النص الكامل
    if bracket_text:
        bracket_w = draw.textbbox((0, 0), bracket_text + " ", font=font_brackets, stroke_width=stroke_w)[2]
        main_w = draw.textbbox((0, 0), main_text, font=font, stroke_width=stroke_w)[2]
        total_w = main_w + bracket_w
    else:
        bracket_w = 0
        main_w = 0
        total_w = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_w)[2]

    x = (target_w - total_w) // 2
    curr_y = 20

    # ✅ الأقواس على اليمين، النص على الشمال
    if has_shadow:
        for offset in range(6, 0, -1):
            opacity = int(80 - offset * 10)
            shadow_color = (*[int(shadow_c.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)], opacity)
            # ✅ نرسم الأقواس أولاً (على اليمين)
            if bracket_text:
                draw.text((x+offset, curr_y+offset), bracket_text + " ", font=font_brackets, fill=shadow_color)
            # ثم النص (على الشمال)
            if main_text:
                draw.text((x + bracket_w + offset, curr_y+offset), main_text, font=font, fill=shadow_color)
        # ظل داخلي
        if bracket_text:
            draw.text((x+3, curr_y+3), bracket_text + " ", font=font_brackets, fill=(0, 0, 0, 180))
        if main_text:
            draw.text((x + bracket_w + 3, curr_y+3), main_text, font=font, fill=(0, 0, 0, 180))

    if glow:
        if bracket_text:
            draw.text((x, curr_y), bracket_text + " ", font=font_brackets, fill=(255,255,255,40), stroke_width=stroke_w+4, stroke_fill=(255,255,255,20))
        if main_text:
            draw.text((x + bracket_w, curr_y), main_text, font=font, fill=(255,255,255,40), stroke_width=stroke_w+4, stroke_fill=(255,255,255,20))

    # ✅ رسم الأقواس أولاً (على اليمين)
    if bracket_text:
        draw.text((x, curr_y), bracket_text + " ", font=font_brackets, fill=color, stroke_width=stroke_w, stroke_fill=stroke_c)

    # ثم رسم النص (على الشمال)
    if main_text:
        draw.text((x + bracket_w, curr_y), main_text, font=font, fill=color, stroke_width=stroke_w, stroke_fill=stroke_c)
    else:
        draw.text((x, curr_y), text, font=font, fill=color, stroke_width=stroke_w, stroke_fill=stroke_c)

    clip = ImageClip(np.array(img)).set_duration(duration)
    return clip

def create_english_clip(text, duration, target_w, scale_factor=1.0, glow=False, style=None, font_path=None):
    if style is None: style = {}

    color = style.get('enColor', '#FFD700')
    size_mult = float(style.get('enSize', '1.0'))
    stroke_c = style.get('enOutC', '#000000')
    stroke_w = int(style.get('enOutW', '3'))
    has_shadow = style.get('enShadow', True)  # ✅ مفعّل افتراضياً
    shadow_c = style.get('enShadowC', '#000000')

    # ✅ استخدام الخط المختار أو الافتراضي
    if font_path is None:
        font_path = FONT_PATH_ENGLISH

    final_fs = int(32 * scale_factor * size_mult)
    font = get_cached_font(font_path, final_fs)
    
    h = int(150 * size_mult)
    img = Image.new('RGBA', (target_w, h), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    y_pos = 20
    # ✅ ظل متعدد الطبقات للنص الإنجليزي
    if has_shadow:
        # طبقة ظل خارجية ناعمة
        for offset in range(4, 0, -1):
            opacity = int(70 - offset * 12)
            shadow_color = (*[int(shadow_c.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)], opacity)
            draw.text((target_w/2 + offset, y_pos + offset), text, font=font, fill=shadow_color, align='center', anchor="ma")
        # طبقة ظل داخلية حادة
        draw.text((target_w/2 + 2, y_pos + 2), text, font=font, fill=(0, 0, 0, 160), align='center', anchor="ma")

    draw.text((target_w/2, y_pos), text, font=font, fill=color, align='center', anchor="ma", stroke_width=stroke_w, stroke_fill=stroke_c)
    
    # ✅ Fade يتم التحكم فيه من خارج الدالة
    clip = ImageClip(np.array(img)).set_duration(duration)
    return clip

def fetch_video_pool(user_key, custom_query, count=1, job_id=None, aspect_ratio='9:16'):
    pool =[]
    active_key = user_key if user_key and len(user_key) > 10 else random.choice(PEXELS_API_KEYS) if PEXELS_API_KEYS else ""

    # ✅ تحديد اتجاه الفيديو حسب الأبعاد
    if aspect_ratio == '16:9':
        orientation = 'landscape'  # أفقي
        video_filter = lambda vf: vf['width'] > vf['height']  # فيديو أفقي
    elif aspect_ratio == '1:1':
        orientation = 'square'  # مربع
        video_filter = lambda vf: True  # أي فيديو
    else:
        orientation = 'portrait'  # عمودي (الافتراضي)
        video_filter = lambda vf: vf['height'] > vf['width']  # فيديو عمودي
    
    # ✅ الكلمات الآمنة المسموح بها
    SAFE_WHITELIST =[
        'nature', 'sky', 'sea', 'ocean', 'water', 'rain', 'cloud', 'mountain',
        'forest', 'tree', 'star', 'galaxy', 'space', 'moon',
        'sun', 'sunset', 'sunrise', 'mosque', 'islam', 'kaaba', 'makkah',
        'snow', 'winter', 'landscape', 'river', 'fog', 'mist', 'earth', 'bird'
    ]

    # ✅ مواضيع آمنة جاهزة (نسخة محلية من SAFE_TOPICS)
    safe_topics = SAFE_TOPICS

    # 🚫 كلمات خطيرة - لو موجودة في النتيجة نرفضها
    BLACKLIST_WORDS = [
        'woman', 'women', 'girl', 'lady', 'female', 'model',
        'man', 'men', 'boy', 'male', 'guy',
        'person', 'people', 'human', 'child', 'baby', 'kid',
        'face', 'portrait', 'selfie', 'couple', 'family',
        'handsome', 'beautiful girl', 'beautiful woman'
    ]

    # ✅ كلمات إيجابية - نضيفها للـ query
    POSITIVE_WORDS = ['empty', 'pure', 'minimalist', 'tranquil', 'serene']

    # دالة فلترة الفيديوهات
    def is_video_safe(vid):
        """نتأكد إن الفيديو مفيهوش ناس من خلال URL و description"""
        url = vid.get('url', '').lower()
        description = vid.get('description', '').lower()
        combined = f"{url} {description}"
        
        for bad_word in BLACKLIST_WORDS:
            if bad_word in combined:
                return False
        return True

    if custom_query and len(custom_query) > 2:
        try: 
            q_trans = GoogleTranslator(source='auto', target='en').translate(custom_query.strip()).lower()
            is_safe = any(safe_word in q_trans for safe_word in SAFE_WHITELIST)
            # ✅ نضيف كلمات إيجابية بدل السلبية
            positive = random.choice(POSITIVE_WORDS)
            q = f"{q_trans} landscape scenery {positive}" if is_safe else random.choice(safe_topics)
        except: 
            q = random.choice(safe_topics)
    else:
        q = random.choice(safe_topics)

    def select_video_file(video_files):
        if aspect_ratio == '16:9':
            return next((vf for vf in video_files if vf['width'] <= 1920 and vf['width'] >= vf['height']), None)
        if aspect_ratio == '1:1':
            return next((vf for vf in video_files if vf['width'] <= 1080), None)
        return next((vf for vf in video_files if vf['width'] <= 1080 and vf['height'] > vf['width']), None)

    def is_photo_safe(photo):
        text = f"{photo.get('url', '')} {photo.get('alt', '')}".lower()
        for bad_word in BLACKLIST_WORDS:
            if bad_word in text:
                return False
        return True

    if active_key:
        try:
            check_stop(job_id)
            # ✅ استخدام الـ orientation المناسب حسب الأبعاد
            pexels_orientation = 'landscape' if aspect_ratio == '16:9' else ('square' if aspect_ratio == '1:1' else 'portrait')
            url = f"https://api.pexels.com/videos/search?query={q}&per_page={count+10}&page={random.randint(1, 10)}&orientation={pexels_orientation}"
            r = requests.get(url, headers={'Authorization': active_key}, timeout=10)
            if r.status_code == 200:
                vids = r.json().get('videos',[])
                random.shuffle(vids)
                for vid in vids:
                    if len(pool) >= count: break
                    check_stop(job_id)
                    
                    # 🚫 فلترة: نتأكد إن الفيديو آمن
                    if not is_video_safe(vid):
                        continue  # نتخطى الفيديو ده
                    
                    # ✅ اختيار الفيديو المناسب حسب الأبعاد
                    f = select_video_file(vid['video_files'])
                    if not f and vid['video_files']: f = vid['video_files'][0]
                    if f:
                        path = os.path.join(VISION_DIR, f"bg_{vid['id']}.mp4")
                        if not os.path.exists(path): smart_download(f['link'], path, job_id)
                        pool.append(path)
        except: pass

    # ✅ Fallback to Pexels photos if enough videos were not found.
    if active_key and len(pool) < count:
        try:
            check_stop(job_id)
            pexels_orientation = 'landscape' if aspect_ratio == '16:9' else ('square' if aspect_ratio == '1:1' else 'portrait')
            needed = max(1, (count - len(pool)) + 8)
            url = f"https://api.pexels.com/v1/search?query={q}&per_page={needed}&page={random.randint(1, 10)}&orientation={pexels_orientation}"
            r = requests.get(url, headers={'Authorization': active_key}, timeout=10)
            if r.status_code == 200:
                photos = r.json().get('photos', [])
                random.shuffle(photos)
                for photo in photos:
                    if len(pool) >= count:
                        break
                    check_stop(job_id)
                    if not is_photo_safe(photo):
                        continue
                    src = photo.get('src', {})
                    img_url = src.get('large2x') or src.get('large') or src.get('original') or src.get('medium')
                    if not img_url:
                        continue
                    img_id = photo.get('id', uuid.uuid4().hex)
                    path = os.path.join(VISION_DIR, f"bg_photo_{img_id}.jpg")
                    if not os.path.exists(path):
                        smart_download(img_url, path, job_id)
                    pool.append(path)
        except:
            pass

    if not pool:
        try:
            local_files =[os.path.join(LOCAL_BGS_DIR, f) for f in os.listdir(LOCAL_BGS_DIR) if f.lower().endswith(('.mp4', '.mov', '.mkv', '.jpg', '.jpeg', '.png', '.webp'))]
            if local_files: pool = random.choices(local_files, k=count)
        except: pass
            
    return pool

def _is_image_asset(path):
    return str(path).lower().endswith((".jpg", ".jpeg", ".png", ".webp"))

def detect_background_source(path):
    """Classify the selected background source for diagnostics."""
    if not path:
        return 'procedural'

    normalized_path = os.path.normpath(str(path)).lower()
    vision_norm = os.path.normpath(VISION_DIR).lower()
    local_norm = os.path.normpath(LOCAL_BGS_DIR).lower()
    filename = os.path.basename(normalized_path)

    if normalized_path.startswith(local_norm):
        return 'local'
    if normalized_path.startswith(vision_norm):
        if filename.startswith('pixabay_bg_'):
            return 'pixabay_video'
        if filename.startswith('bg_photo_'):
            return 'pexels_photo'
        if filename.startswith('bg_'):
            return 'pexels_video'
        return 'vision_asset'
    return 'external_asset'

def _prepare_background_clip(path, target_w, target_h, aspect_ratio, bg_effect='enhance', duration=600):
    """Create a normalized background clip from a video or image asset."""
    if _is_image_asset(path):
        bg_clip = ImageClip(path).set_duration(duration)
        if aspect_ratio == '16:9':
            bg_clip = bg_clip.resize(width=target_w)
        else:
            bg_clip = bg_clip.resize(height=target_h)
        bg_clip = bg_clip.crop(width=target_w, height=target_h, x_center=bg_clip.w/2, y_center=bg_clip.h/2).set_duration(duration)
    else:
        bg_clip = VideoFileClip(path)
        if aspect_ratio == '16:9':
            bg_clip = bg_clip.resize(width=target_w)
        else:
            bg_clip = bg_clip.resize(height=target_h)
        video_duration = bg_clip.duration
        bg_clip = bg_clip.crop(width=target_w, height=target_h, x_center=bg_clip.w/2, y_center=bg_clip.h/2).set_duration(video_duration)

    if bg_effect != 'none':
        bg_clip = apply_background_effects(bg_clip, effect_type=bg_effect, strength=1.1)

    final_duration = bg_clip.duration
    gradient = create_gradient_overlay(target_w, target_h,
                                    color_top=(0, 0, 0),
                                    color_bottom=(0, 0, 0),
                                    opacity=0.35)
    return CompositeVideoClip([bg_clip, gradient.set_duration(final_duration)]).set_duration(final_duration)

def estimate_frame_luminance(frame):
    if frame is None:
        return 0.5
    arr = np.asarray(frame)
    if arr.ndim < 3:
        return float(np.clip(arr.mean() / 255.0, 0.0, 1.0))
    rgb = arr[..., :3].astype(np.float32)
    lum = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]).mean() / 255.0
    return float(np.clip(lum, 0.0, 1.0))

def build_contrast_adaptive_style(style, luminance):
    s = dict(style or {})
    ar_out = int(float(s.get('arOutW', 4)))
    en_out = int(float(s.get('enOutW', 3)))

    if luminance >= 0.70:
        s['arOutW'] = str(min(10, max(ar_out, 6)))
        s['enOutW'] = str(min(10, max(en_out, 5)))
        s['arOutC'] = '#000000'
        s['enOutC'] = '#000000'
    elif luminance <= 0.35:
        s['arColor'] = s.get('arColor', '#ffffff') or '#ffffff'
        s['enColor'] = s.get('enColor', '#FFD700') or '#FFD700'
        s['arOutW'] = str(min(10, max(ar_out, 4)))
        s['enOutW'] = str(min(10, max(en_out, 3)))
        s['arOutC'] = '#000000'
        s['enOutC'] = '#000000'

    s['arShadow'] = True
    s['enShadow'] = True
    s['arShadowC'] = '#000000'
    s['enShadowC'] = '#000000'
    return s

# ==========================================
# ⚡ Optimized Video Builder (Segmented / Chunked)
# ==========================================
def build_video_task(job_id, user_pexels_key, reciter_id, surah, start, end, quality, bg_query, fps, dynamic_bg, use_glow, use_vignette, aspect_ratio, style, font_name='Arabic', font_name_en='English', bg_effect='enhance', scene_pack='nature_calm', bg_crossfade_sec=0.5, adaptive_text_contrast=False, safe_area_guides=False, safe_area_padding_px=0, audio_profile='studio', audio_denoise=False, audio_deess=False):
    job = get_job(job_id)
    if not job:
        raise Exception(f"Job {job_id} not found - cannot process video")

    workspace = job['workspace']
    if not workspace:
        raise Exception(f"Job {job_id} has no workspace")

    # ✅ تحديد مسار الخط
    font_path = get_font_path(font_name)
    font_path_en = get_font_path_en(font_name_en)
    bg_query = choose_background_query(bg_query, scene_pack)
    text_crossfade = min(0.8, max(0.15, float(bg_crossfade_sec) * 0.7))
    bg_crossfade_sec = min(1.2, max(0.0, float(bg_crossfade_sec)))
    safe_pad = int(max(0, safe_area_padding_px if _as_bool(safe_area_guides) else 0))
    adaptive_text_contrast = _as_bool(adaptive_text_contrast)

    # تحديد الأبعاد بناءً على aspect_ratio و quality
    # 9:16 = ريلز/تيك توك (portrait), 1:1 = سوير (square), 16:9 = يوتيوب (landscape)
    if aspect_ratio == '1:1':
        # مربع (سوير/انستجرام)
        target_w, target_h = (1080, 1080) if quality == '1080' else (720, 720)
    elif aspect_ratio == '16:9':
        # أفقي (يوتيوب)
        target_w, target_h = (1920, 1080) if quality == '1080' else (1280, 720)
    else:
        # 9:16 - الافتراضي (ريلز/تيك توك)
        target_w, target_h = (1080, 1920) if quality == '1080' else (720, 1280)
    
    scale = 1.0 if quality == '1080' else 0.67
    last = min(end if end else start+9, VERSE_COUNTS.get(surah, 286))
    total_ayahs = (last - start) + 1
    
    # مصفوفات لتخزين الملفات المفتوحة لإغلاقها في الـ finally لعدم تسريب الذاكرة
    audio_clips_to_close =[]
    video_clips_to_close = []
    final_segments =[]
    update_job_metadata(job_id, background_source_used='unknown', background_fetch_error=None)

    try:
        # 1. Fetch Backgrounds (with multiple sources)
        vpool = []
        fetch_error = None
        try:
            vpool = fetch_from_multiple_sources(bg_query, count=total_ayahs if dynamic_bg else 1, aspect_ratio=aspect_ratio, job_id=job_id)
        except Exception as ex:
            fetch_error = f"multi_source: {ex}"

        if not vpool:
            try:
                vpool = fetch_video_pool(user_pexels_key, bg_query, count=total_ayahs if dynamic_bg else 1, job_id=job_id, aspect_ratio=aspect_ratio)
            except Exception as ex:
                fetch_error = f"pexels_direct: {ex}" if not fetch_error else f"{fetch_error} | pexels_direct: {ex}"

        if fetch_error:
            update_job_metadata(job_id, background_fetch_error=fetch_error)
        
        # 2. Prepare Base Background with Enhancements
        if not vpool:
            # ✅ لا توجد فيديوهات → خلفية إجرائية متحركة جميلة (بديل بدون مفاتيح API)
            print(f"[INFO] No video backgrounds available — generating procedural animated background for job {job_id}")
            update_job_status(job_id, 2, 'Generating animated background (no API key set)...')
            base_bg_clip = create_procedural_bg(target_w, target_h, duration=600, seed=hash(job_id) & 0xFFFF)
            video_clips_to_close.append(base_bg_clip)
            update_job_metadata(job_id, background_source_used='procedural')
        else:
            source_used = detect_background_source(vpool[0])
            update_job_metadata(job_id, background_source_used=source_used)
            base_bg_clip = _prepare_background_clip(vpool[0], target_w, target_h, aspect_ratio, bg_effect=bg_effect, duration=600)
            video_clips_to_close.append(base_bg_clip)

        overlays_static =[ColorClip((target_w, target_h), color=(0,0,0)).set_opacity(0.15)]  # ✅ قللناه من 0.45 لأن التدرج يوفر الحماية
        if use_vignette:
            overlays_static.append(create_vignette_mask(target_w, target_h))

        current_bg_time = 0.0
        
        # 4. معالجة الآيات 
        for i, ayah in enumerate(range(start, last+1)):
            check_stop(job_id)
            update_job_status(job_id, int((i / total_ayahs) * 80), f'Processing Ayah {ayah}...')

            # تحميل الصوت مع التحقق
            try:
                ap = download_audio(reciter_id, surah, ayah, i, workspace, job_id)
                if not os.path.exists(ap):
                    raise Exception(f"Audio file not found: {ap}")
                full_audioclip = AudioFileClip(ap)
                if full_audioclip.duration <= 0:
                    raise Exception(f"Invalid audio duration: {full_audioclip.duration}")
                audio_clips_to_close.append(full_audioclip)
            except Exception as audio_err:
                print(f"[ERROR] Audio download/processing failed for ayah {ayah}: {audio_err}")
                continue  # Skip this ayah and continue with the next

            full_ar_text = get_text(surah, ayah)
            full_en_text = get_en_text(surah, ayah)
            
            # التحقق من وجود نص عربي
            if not full_ar_text or full_ar_text == "Text Error" or len(full_ar_text.strip()) == 0:
                print(f"[ERROR] Failed to get Arabic text for ayah {ayah}")
                continue  # Skip this ayah
            
            # تقطيع النصوص (العربي والإنجليزي)
            ar_chunks = split_into_chunks(full_ar_text, words_per_chunk=5)
            
            # التحقق من وجود قطع
            if not ar_chunks or len(ar_chunks) == 0:
                print(f"[ERROR] No text chunks created for ayah {ayah}")
                continue  # Skip this ayah
                
            en_words = full_en_text.split()
            avg_en_per_ar = len(en_words) / len(ar_chunks) if len(ar_chunks) > 0 else 0
            
            current_audio_time = 0.0
            
            # فتح فيديو الخلفية مرة واحدة للآية (إذا كان متغيراً) لتقليل استهلاك الرام
            if dynamic_bg and i < len(vpool):
                ayah_bg_clip = _prepare_background_clip(vpool[i % len(vpool)], target_w, target_h, aspect_ratio, bg_effect=bg_effect, duration=600)
                video_clips_to_close.append(ayah_bg_clip)
                ayah_bg_time = 0.0

            # الدوران على قطع الآية (السطور)
            # الدوران على قطع الآية (السطور)
            for chunk_idx, ar_chunk in enumerate(ar_chunks):
                
                # 1. تحديد وقت النهاية بدقة شديدة
                if chunk_idx == len(ar_chunks) - 1:
                    t_end = full_audioclip.duration # القطعة الأخيرة تاخد كل الباقي
                else:
                    ratio = len(ar_chunk.replace(" ", "")) / max(1, len(full_ar_text.replace(" ", "")))
                    t_end = min(current_audio_time + (ratio * full_audioclip.duration), full_audioclip.duration)

                # حماية من الأوقات الصفرية
                if t_end - current_audio_time <= 0.05: 
                    t_end = min(current_audio_time + 0.1, full_audioclip.duration)

                # 2. قص الصوت
                chunk_audio = full_audioclip.subclip(current_audio_time, t_end)
                # بدون أي fade - الصوت الأصلي أنظف
                
                # 🚀 3. الحل الجذري: نعتمد وقت الصوت الفعلي كأساس لوقت الفيديو!
                actual_duration = chunk_audio.duration
                if actual_duration <= 0: continue
                
                # ج. اقتطاع الترجمة الإنجليزية
                start_en = int(chunk_idx * avg_en_per_ar)
                end_en = int((chunk_idx + 1) * avg_en_per_ar)
                if chunk_idx == len(ar_chunks) - 1:
                    en_chunk = " ".join(en_words[start_en:])
                    display_ar = f"{ar_chunk} ﴿{to_arabic_numeral(ayah)}﴾"  # رقم آية عربي بأقواس مزخرفة
                else:
                    en_chunk = " ".join(en_words[start_en:end_en])
                    display_ar = ar_chunk

                # د. إنشاء Style للقطعة (اختياري: adaptive contrast)
                chunk_style = dict(style or {})
                if adaptive_text_contrast:
                    try:
                        sample_clip = ayah_bg_clip if (dynamic_bg and i < len(vpool)) else base_bg_clip
                        sample_time = ayah_bg_time if (dynamic_bg and i < len(vpool)) else current_bg_time
                        frame_sample = sample_clip.get_frame(sample_time)
                        chunk_style = build_contrast_adaptive_style(chunk_style, estimate_frame_luminance(frame_sample))
                    except Exception:
                        pass

                # د. إنشاء الكليبات البصرية (نستخدم actual_duration بدل chunk_duration)
                ac = create_text_clip(display_ar, actual_duration, target_w, scale, use_glow, style=chunk_style, font_path=font_path)
                ec = create_english_clip(en_chunk, actual_duration, target_w, scale, use_glow, style=chunk_style, font_path=font_path_en)
                
                # ✅ Crossfade للنص
                TEXT_FADE = text_crossfade  # مدة crossfade النص
                ac = ac.crossfadein(TEXT_FADE).crossfadeout(TEXT_FADE)
                ec = ec.crossfadein(TEXT_FADE).crossfadeout(TEXT_FADE)
                
                is_first_chunk = (chunk_idx == 0)
                is_last_chunk = (chunk_idx == len(ar_chunks) - 1)

                # هـ. تحديد المواقع
                ar_size_mult = float(chunk_style.get('arSize', '1.0'))
                base_y = 0.35 if ar_size_mult <= 1.2 else 0.30
                ar_y_pos = target_h * base_y

                if safe_pad > 0:
                    max_ar_y = max(safe_pad, target_h - safe_pad - ac.h - ec.h - int(8 * scale))
                    ar_y_pos = min(max(ar_y_pos, safe_pad), max_ar_y)

                ec_y_pos = ar_y_pos + ac.h + (2 * scale)
                if safe_pad > 0:
                    ec_y_pos = min(ec_y_pos, target_h - safe_pad - ec.h)

                ac = ac.set_position(('center', ar_y_pos))
                ec = ec.set_position(('center', ec_y_pos))

                # و. معالجة الخلفية للقطعة (نستخدم actual_duration)
                # ✅ الخلفية تتغير فقط بين الآيات (مش كل سطر)
                if dynamic_bg and i < len(vpool):
                    bg_slice = ayah_bg_clip.loop().subclip(ayah_bg_time, ayah_bg_time + actual_duration)
                    # ✅ Fade للخلفية فقط بين الآيات (أول وآخر chunk في الآية كلها)
                    if is_first_chunk: 
                        bg_slice = bg_slice.fadein(bg_crossfade_sec)
                    if is_last_chunk: 
                        bg_slice = bg_slice.fadeout(bg_crossfade_sec)
                    ayah_bg_time += actual_duration
                else:
                    bg_slice = base_bg_clip.loop().subclip(current_bg_time, current_bg_time + actual_duration)
                    current_bg_time += actual_duration
                
                # ز. تجميع القطعة
                segment_overlays =[o.set_duration(actual_duration) for o in overlays_static]
                full_segment = CompositeVideoClip([bg_slice] + segment_overlays + [ac, ec]).set_audio(chunk_audio)
                final_segments.append(full_segment)

                # تحديث الوقت للقطعة القادمة
                current_audio_time = t_end

        # 5. الدمج والرندر النهائي
        # التحقق من وجود مقاطع للدمج
        if not final_segments or len(final_segments) == 0:
            raise Exception("لم يتم إنشاء أي مقاطع فيديو - قد يكون هناك مشكلة في تحميل الصوت أو النصوص")

        update_job_status(job_id, 85, "Merging All Chunks...")
        
        # 🧪 تجربة: فصل الصوت والفيديو ودمجهم بشكل منفصل
        # نجمع audio clips لوحدها
        audio_clips = [seg.audio for seg in final_segments]
        
        # ندمج الصوت بـ concatenate_audioclips (أدق في التعامل مع الصوت)
        merged_audio = concatenate_audioclips(audio_clips)
        
        # نشيل الصوت من الفيديو clips وندمج الفيديو لوحده
        # استخدام method="chain" بدل "compose" لتجنب overlap تلقائي
        video_clips_no_audio = [seg.set_audio(None) for seg in final_segments]
        final_video = concatenate_videoclips(video_clips_no_audio, method="chain")
        
        # نربط الصوت المدمج الجديد بالفيديو
        final_video = final_video.set_audio(merged_audio)
        
        # ✅ Fade للصوت معطل مؤقتاً - يمكن يسبب مشاكل في الدمج
        # AUDIO_FADE = 0.5
        # final_video = final_video.audio_fadein(AUDIO_FADE).audio_fadeout(AUDIO_FADE)
        
        # حفظ الفيديو النهائي في مجلد outputs
        final_output_path = os.path.join(OUTPUTS_DIR, f"{job_id}.mp4")
        temp_mix_path = os.path.join(workspace, f"temp_mix_{job_id}.mp4")
        
        # 🎬 إعدادات الضغط (قيم ثابتة للحصول على أفضل توازن)
        # CRF 24 = جودة عالية مع ضغط ممتاز (مثالي للقرآن - نص ثابت + خلفية)
        # Preset medium = ضغط أفضل بـ 5% مع وقت إضافي معقول
        # Audio 128k = نفس جودة السماع مع توفير 33%
        crf_value = 24
        preset_value = 'medium'
        
        update_job_status(job_id, 90, "Rendering Video (Mixing)...")
        final_video.write_videofile(
            temp_mix_path, 
            fps=fps, 
            codec='libx264', 
            audio_codec='aac', 
            audio_bitrate='128k',
            preset=preset_value,
            threads=os.cpu_count() or 4,
            ffmpeg_params=['-crf', str(crf_value)],
            logger=ScopedQuranLogger(job_id)
        )

        # 6. معالجة الصوت النهائية (Mastering)
        update_job_status(job_id, 98, "Mastering Audio...")
        audio_filter_chain = build_audio_filter_chain(audio_profile, audio_denoise, audio_deess)
        cmd = (
            f'ffmpeg -y -i "{temp_mix_path}" '
            f'-af "{audio_filter_chain}" '
            f'-c:v copy '
            f'-c:a aac -b:a 128k '
            f'"{final_output_path}"'
        )
        
        if os.system(cmd) != 0: 
            # في حال فشل الفلتر لأي سبب، نستخدم النسخة الأصلية
            shutil.move(temp_mix_path, final_output_path)
        else:
            if os.path.exists(temp_mix_path): os.remove(temp_mix_path)

        with JOBS_LOCK: 
            if job_id in JOBS:
                JOBS[job_id].update({'output_path': final_output_path, 'is_complete': True, 'is_running': False, 'percent': 100, 'status': "complete"})
            else:
                # أضف للـ RAM لو مش موجودة
                JOBS[job_id] = {'id': job_id, 'output_path': final_output_path, 'is_complete': True, 'is_running': False, 'percent': 100, 'status': "complete"}
        
        # Update in SQLite and add to history
        db_update_job(job_id, output_path=final_output_path, status='complete', percent=100, completed_at=time.time())
        
        # Get config from DB to add to history
        db_job = db_get_job(job_id)
        if db_job and db_job.get('config_json'):
            try:
                config = json.loads(db_job['config_json'])
                surah = config.get('surah', 1)
                start_ayah = config.get('startAyah', 1)
                end_ayah = config.get('endAyah', start_ayah)
                reciter_id = config.get('reciter', 'Unknown')
                quality = config.get('quality', '720')
                fps = config.get('fps', '20')
                session_id = config.get('session_id')  # استخراج session_id
                
                # تحويل الـ ID للاسم العربي
                reciter_name = RECITER_ID_TO_NAME.get(reciter_id, reciter_id)
                
                lang_pref = config.get('lang', 'ar')
                surah_name = get_surah_name(surah, lang_pref)
                # العنوان: اسم السورة (الآيات) | اسم القارئ
                if lang_pref == 'en':
                    title = f"Quran recitation {surah_name} ({start_ayah}-{end_ayah}) by {reciter_name} #quran #shorts"
                else:
                    title = f"قرآن كريم {surah_name} ({start_ayah}-{end_ayah}) بصوت القارئ {reciter_name} #قران_كريم #quran #shorts"
                filename = f"Quran_{surah}_{start_ayah}.mp4"
                
                db_add_history(job_id, title, reciter_name, surah, start_ayah, end_ayah, quality, fps, filename, session_id)
            except Exception as e:
                print(f"Error adding to history: {e}")

    except Exception as e:
        msg = str(e)
        traceback.print_exc()
        status = "cancelled" if msg == "Stopped" else "error"
        with JOBS_LOCK: 
            if job_id in JOBS:
                JOBS[job_id].update({'error': msg, 'status': status, 'is_running': False})
            else:
                # أضف للـ RAM لو مش موجودة
                JOBS[job_id] = {'id': job_id, 'error': msg, 'status': status, 'is_running': False, 'percent': 0}
        # Update in SQLite
        db_update_job(job_id, status=status, error=msg)
    
    finally:
        # ═══════════════════════════════════════
        # 🧹 Memory Cleanup - تنظيف الذاكرة والملفات
        # ═══════════════════════════════════════
        
        # 1. إغلاق جميع الـ clips المفتوحة
        for ac in audio_clips_to_close:
            try: ac.close()
            except: pass
            
        for vc in video_clips_to_close:
            try: vc.close()
            except: pass
            
        try:
            if 'final_video' in locals(): final_video.close()
            for s in final_segments: s.close()
        except: pass
        
        # 2. تنظيف الـ numpy arrays المؤقتة
        try:
            if 'frame' in locals():
                del frame
            if 'bg_array' in locals():
                del bg_array
        except: pass
        
        # 3. تنظيف ذاكرة بايثون (مرتين للتأكد)
        gc.collect()
        gc.collect()
        
        # 4. حذف جميع الملفات المؤقتة
        try:
            # حذف مجلد العمل المؤقت بالكامل
            if workspace and os.path.exists(workspace):
                shutil.rmtree(workspace, ignore_errors=True)
                print(f"🧹 Cleaned workspace: {job_id}")
            
            # حذف ملفات الـ cache بعد كل عملية
            # cache_mp3quran - ملفات الصوت المحملة
            cache_mp3_dir = os.path.join(EXEC_DIR, "cache_mp3quran")
            if os.path.exists(cache_mp3_dir):
                shutil.rmtree(cache_mp3_dir, ignore_errors=True)
                os.makedirs(cache_mp3_dir, exist_ok=True)
                print(f"🧹 Cleaned cache_mp3quran")
            
            # vision - فيديوهات الخلفية المحملة من Pexels
            if os.path.exists(VISION_DIR):
                for f in os.listdir(VISION_DIR):
                    fpath = os.path.join(VISION_DIR, f)
                    try:
                        if os.path.isfile(fpath):
                            os.remove(fpath)
                        elif os.path.isdir(fpath):
                            shutil.rmtree(fpath, ignore_errors=True)
                    except: pass
                print(f"🧹 Cleaned vision backgrounds")
                
            # حذف ملفات temp_timings المؤقتة
            timings_cache = os.path.join(EXEC_DIR, "cache_timings")
            if os.path.exists(timings_cache):
                # نحتفظ بالملفات اللي أقل من ساعة
                now = time.time()
                for f in os.listdir(timings_cache):
                    fpath = os.path.join(timings_cache, f)
                    try:
                        if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) > 3600:
                            os.remove(fpath)
                    except: pass
                print(f"🧹 Cleaned old timings cache")
                
        except Exception as cleanup_err:
            print(f"⚠️ Cleanup error: {cleanup_err}")
        
        # 5. تنظيف نهائي للذاكرة
        gc.collect()
        print(f"✅ Memory cleanup completed for job: {job_id}")

# ═══════════════════════════════════════
# ⏱️ API: Estimate Duration (المدة التقريبية الفعلية)
# ═══════════════════════════════════════
@app.route('/api/estimate-duration', methods=['POST'])
@limiter.limit("100 per hour")  # 🛡️ 100 طلب في الساعة (خفيف)
def estimate_duration():
    """حساب المدة الفعلية للفيديو بناءً على توقيت الصوت"""
    lang = 'ar'
    try:
        d = request.json
        lang = get_request_lang(d)
        reciter = d.get('reciter', '')
        surah = int(d.get('surah', 1))
        start_ayah = int(d.get('startAyah', 1))
        end_ayah = int(d.get('endAyah', start_ayah))
        
        total_duration_ms = 0
        
        # 🎯 تحويل الـ reciter للاسم العربي (لو كان ID)
        reciter_name = RECITER_ID_TO_NAME.get(reciter, reciter)
        
        # 🎯 محاولة استخدام MP3Quran API للجميع
        reciter_id = None
        
        # القراء الجدد
        if reciter in NEW_RECITERS_CONFIG:
            reciter_id = NEW_RECITERS_CONFIG[reciter][0]
        # القراء القدام - نبحث في MP3QURAN_IDS بالاسم العربي
        elif reciter_name in MP3QURAN_IDS:
            reciter_id = MP3QURAN_IDS[reciter_name]
        
        if reciter_id:
            # ✅ عندنا ID - نستخدم mp3quran timing API
            cache_dir = os.path.join(EXEC_DIR, "cache_mp3quran", str(reciter_id))
            os.makedirs(cache_dir, exist_ok=True)
            timings_path = os.path.join(cache_dir, f"{surah:03d}.json")
            
            # تحميل الـ timings لو مش موجودة
            if not os.path.exists(timings_path):
                try:
                    t_data = requests.get(
                        f"https://mp3quran.net/api/v3/ayat_timing?surah={surah}&read={reciter_id}",
                        timeout=10
                    ).json()
                    timings = {item['ayah']: {'start': item['start_time'], 'end': item['end_time']} for item in t_data}
                    with open(timings_path, 'w') as f:
                        json.dump(timings, f)
                except Exception as e:
                    print(f"[Estimate] mp3quran API failed: {e}")
                    timings = None
            else:
                with open(timings_path, 'r') as f:
                    timings = json.load(f)
            
            # حساب المدة
            TEXT_FADE_PER_AYAH = 0.7  # crossfade in + out لكل آية
            ayah_count = 0
            if timings:
                for ayah in range(start_ayah, end_ayah + 1):
                    ayah_str = str(ayah)
                    if ayah_str in timings:
                        start_time = timings[ayah_str]['start']
                        end_time = timings[ayah_str]['end']
                        duration_ms = end_time - start_time
                        total_duration_ms += duration_ms
                        ayah_count += 1
                    else:
                        # fallback ذكي
                        total_duration_ms += int(smart_estimate_by_length(surah, ayah, reciter_name) * 1000)
                        ayah_count += 1
                # إضافة crossfade لكل آية
                total_duration_ms += int(ayah_count * TEXT_FADE_PER_AYAH * 1000)
            else:
                # fallback ذكي
                for ayah in range(start_ayah, end_ayah + 1):
                    total_duration_ms += int(smart_estimate_by_length(surah, ayah, reciter_name) * 1000)
                # إضافة crossfade
                total_duration_ms += int((end_ayah - start_ayah + 1) * TEXT_FADE_PER_AYAH * 1000)
        
        else:
            # ❌ مفيش ID - نستخدم الحساب الذكي
            TEXT_FADE_PER_AYAH = 0.7  # crossfade in + out لكل آية
            ayah_count = end_ayah - start_ayah + 1
            for ayah in range(start_ayah, end_ayah + 1):
                duration = smart_estimate_by_length(surah, ayah, reciter_name)
                total_duration_ms += int(duration * 1000)
            # إضافة crossfade
            total_duration_ms += int(ayah_count * TEXT_FADE_PER_AYAH * 1000)
        
        # تحويل المدة لصيغة مقروءة
        total_seconds = total_duration_ms // 1000
        
        return jsonify({
            'ok': True,
            'durationMs': total_duration_ms,
            'durationSeconds': total_seconds,
            'formatted': format_duration(total_seconds, lang)
        })
        
    except Exception as e:
        print(f"[Estimate] Error: {e}")
        return jsonify({'ok': False, 'error': tr_api('invalid_data', lang, detail=str(e))})

def format_duration(seconds, lang='ar'):
    """تحويل الثواني لصيغة مقروءة"""
    if lang == 'en':
        if seconds < 60:
            return f"{seconds}s"
        if seconds < 3600:
            mins = seconds // 60
            secs = seconds % 60
            if secs > 0:
                return f"{mins}m {secs}s"
            return f"{mins} min"
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        if mins > 0:
            return f"{hours}h {mins}m"
        return f"{hours}h"

    if seconds < 60:
        return f"{seconds} ثانية"
    if seconds < 3600:
        mins = seconds // 60
        secs = seconds % 60
        if secs > 0:
            return f"{mins} د {secs} ث"
        return f"{mins} دقيقة"
    hours = seconds // 3600
    mins = (seconds % 3600) // 60
    if mins > 0:
        return f"{hours} س {mins} د"
    return f"{hours} ساعة"

# ═══════════════════════════════════════
# 🏥 API: Health Check - للمراقبة
# ═══════════════════════════════════════
START_TIME = time.time()  # لتتبع وقت التشغيل

@app.route('/api/health')
def health_check():
    """
    Endpoint للمراقبة - يرجع حالة السيرفر
    يُستخدم من أدوات المراقبة للتأكد من أن الخدمة تعمل
    """
    try:
        # عدد العمليات النشطة
        active_jobs = len([j for j in JOBS.values() if j.get('is_running')])
        
        # عدد العمليات المكتملة اليوم
        today = datetime.date.today().isoformat()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM history WHERE date(created_at) = ?", (today,))
        today_count = c.fetchone()[0]
        conn.close()
        
        # الذاكرة المستخدمة (تقريبية)
        import psutil
        memory_percent = psutil.virtual_memory().percent
        memory_used = round(psutil.virtual_memory().used / (1024**3), 2)  # GB
    except:
        active_jobs = len([j for j in JOBS.values() if j.get('is_running')])
        today_count = 0
        memory_percent = 0
        memory_used = 0
    
    uptime_seconds = int(time.time() - START_TIME)
    uptime_hours = uptime_seconds // 3600
    uptime_mins = (uptime_seconds % 3600) // 60
    lang = get_request_lang()
    uptime_str = f"{uptime_hours}h {uptime_mins}m" if lang == 'en' else f"{uptime_hours}س {uptime_mins}د"
    
    return jsonify({
        'status': 'healthy',
        'uptime': uptime_str,
        'uptime_seconds': uptime_seconds,
        'active_jobs': active_jobs,
        'videos_today': today_count,
        'memory': {
            'percent': memory_percent,
            'used_gb': memory_used
        },
        'timestamp': datetime.datetime.now().isoformat()
    })

@app.route('/')
def ui(): return send_file(UI_PATH) if os.path.exists(UI_PATH) else "API Running"

# ✅ HuggingFace Health Check Endpoint - مهم جداً!
# HuggingFace بتعمل ping على الـ '/' route عشان تتأكد إن التطبيق شغال
@app.route('/healthz')
def hf_health():
    """HuggingFace Spaces health check endpoint"""
    return '', 200

@app.route('/favicon.ico')
def favicon():
    """Return empty 204 for favicon requests to suppress browser 404 errors"""
    return '', 204

@app.route('/api/generate', methods=['POST'])
@limiter.limit("20 per hour")  # 🛡️ 20 فيديو في الساعة
def gen():
    d = request.json
    lang = get_request_lang(d)
    
    # استخراج session_id من الطلب
    session_id = d.get('sessionId')
    
    # ✅ التحقق من صحة المدخلات
    try:
        surah = int(d['surah'])
        start_ayah = int(d['startAyah'])
        end_ayah = int(d.get('endAyah', start_ayah))
        
        # التحقق من نطاق الآيات
        validate_ayah_range(surah, start_ayah, end_ayah, lang)
    except ValidationError as ve:
        return jsonify({'ok': False, 'error': str(ve)}), 400
    except (ValueError, KeyError) as e:
        return jsonify({'ok': False, 'error': f"{tr_api('invalid_data', lang)}: {str(e)}"}), 400
    
    # Create job with config for persistence
    config = {
        'surah': surah,
        'startAyah': start_ayah,
        'endAyah': end_ayah,
        'reciter': d['reciter'],
        'quality': d.get('quality', '720'),
        'fps': d.get('fps', '20'),
        'bgQuery': d.get('bgQuery', ''),
        'dynamicBg': d.get('dynamicBg', False),
        'useGlow': d.get('useGlow', False),
        'useVignette': d.get('useVignette', False),
        'backgroundEffect': d.get('backgroundEffect', 'enhance'),
        'scenePack': d.get('scenePack', 'nature_calm'),
        'bgCrossfadeSec': d.get('bgCrossfadeSec', 0.5),
        'adaptiveTextContrast': d.get('adaptiveTextContrast', False),
        'safeAreaGuides': d.get('safeAreaGuides', False),
        'safeAreaPaddingPx': d.get('safeAreaPaddingPx', 0),
        'audioProfile': d.get('audioProfile', 'studio'),
        'audioDenoise': d.get('audioDenoise', False),
        'audioDeEss': d.get('audioDeEss', False),
        'font': d.get('font', 'Arabic'),
        'fontEn': d.get('fontEn', 'English'),
        'pexelsKey': d.get('pexelsKey', ''),
        'style': d.get('style', {}),
        'lang': lang,
        'session_id': session_id
    }

    job_id = create_job(config, session_id)
    style_settings = d.get('style', {})

    # Update status to processing
    update_job_status(job_id, 0, 'processing')

    threading.Thread(
        target=build_video_task,
        args=(
            job_id,
            d.get('pexelsKey', ''),
            d['reciter'],
            surah,
            start_ayah,
            end_ayah,
            d.get('quality','720'),
            d.get('bgQuery',''),
            int(d.get('fps',20)),
            d.get('dynamicBg',False),
            d.get('useGlow',False),
            d.get('useVignette',False),
            d.get('aspectRatio','9:16'),
            style_settings,
            d.get('font', 'Arabic'),
            d.get('fontEn', 'English'),
            d.get('backgroundEffect', 'enhance'),
            d.get('scenePack', 'nature_calm'),
            d.get('bgCrossfadeSec', 0.5),
            d.get('adaptiveTextContrast', False),
            d.get('safeAreaGuides', False),
            d.get('safeAreaPaddingPx', 0),
            d.get('audioProfile', 'studio'),
            d.get('audioDenoise', False),
            d.get('audioDeEss', False)
        ),
        daemon=True
    ).start()
    
    return jsonify({'ok': True, 'jobId': job_id})

@app.route('/api/progress')
@limiter.exempt
def prog(): 
    job = get_job(request.args.get('jobId'))
    if job:
        # Add download URL if complete
        if job.get('status') == 'complete' and job.get('output_path'):
            job['download_url'] = f"/api/download?jobId={job['id']}"
    return jsonify(job)

@app.route('/api/download')
def download_result():
    lang = get_request_lang()
    job = get_job(request.args.get('jobId'))
    if not job:
        return jsonify({'error': tr_api('job_not_found', lang)}), 404
    
    output_path = job.get('output_path')
    if not output_path or not os.path.exists(output_path):
        return jsonify({'error': tr_api('file_not_found', lang)}), 404
    
    # Get filename from history or use default
    filename = f"Quran_video_{request.args.get('jobId')[:8]}.mp4"
    return send_file(output_path, as_attachment=True, download_name=filename)

@app.route('/api/cancel', methods=['POST'])
def cancel_process():
    d = request.json
    job_id = d.get('jobId')
    if job_id:
        with JOBS_LOCK:
            if job_id in JOBS:
                JOBS[job_id]['should_stop'] = True
                JOBS[job_id]['status'] = 'cancelling'
        # Update in SQLite
        db_update_job(job_id, should_stop=1, status='cancelling')
    return jsonify({'ok': True})

@app.route('/api/history')
def get_history():
    """Get user's video history from database filtered by session"""
    limit = request.args.get('limit', 20, type=int)
    session_id = request.args.get('sessionId')  # استخراج session_id من الطلب
    lang = get_request_lang()
    history = db_get_history(limit, session_id)
    
    result = []
    for h in history:
        # اسم السورة من القائمة
        surah_num = h['surah'] if h['surah'] else 1
        surah_name = get_surah_name(surah_num, lang)
        
        item = {
            'id': h['id'],
            'jobId': h['job_id'],
            'title': h['title'],
            'reciter': h['reciter'],
            'surah': h['surah'],
            'surahName': surah_name,  # اسم السورة
            'startAyah': h['start_ayah'],
            'endAyah': h['end_ayah'],
            'quality': h['quality'],
            'fps': h['fps'],
            'filename': h['download_filename'],
            'status': h['status'],
            'createdAt': h['created_at'],
        }
        
        # Add download URL if video exists
        if h['output_path'] and os.path.exists(h['output_path']):
            item['downloadUrl'] = f"/api/download?jobId={h['job_id']}"
        
        result.append(item)
    
    return jsonify({'ok': True, 'history': result})

@app.route('/api/history/<int:history_id>', methods=['DELETE'])
def delete_history_item(history_id):
    """Delete a single history item"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get the history item first to clean up files
    c.execute("SELECT job_id FROM history WHERE id = ?", (history_id,))
    row = c.fetchone()
    
    if row:
        job_id = row[0]
        # Delete from history
        c.execute("DELETE FROM history WHERE id = ?", (history_id,))
        # Also delete the job if exists
        c.execute("SELECT workspace FROM jobs WHERE id = ?", (job_id,))
        job_row = c.fetchone()
        if job_row and job_row[0]:
            workspace = job_row[0]
            if os.path.exists(workspace):
                try:
                    shutil.rmtree(workspace, ignore_errors=True)
                except:
                    pass
        c.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'ok': True})

@app.route('/api/history/clear', methods=['POST'])
def clear_all_history():
    """Clear history for current session only"""
    data = request.json or {}
    session_id = data.get('sessionId')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if session_id:
        # حذف history للجلسة الحالية فقط
        c.execute("SELECT job_id FROM history WHERE session_id = ?", (session_id,))
        job_ids = [row[0] for row in c.fetchall()]
        
        # حذف ملفات الفيديو والـ workspaces
        for job_id in job_ids:
            c.execute("SELECT workspace, output_path FROM jobs WHERE id = ?", (job_id,))
            job_row = c.fetchone()
            if job_row:
                workspace, output_path = job_row
                if workspace and os.path.exists(workspace):
                    try:
                        shutil.rmtree(workspace, ignore_errors=True)
                    except:
                        pass
                if output_path and os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except:
                        pass
        
        # حذف من history و jobs للجلسة فقط
        c.execute("DELETE FROM history WHERE session_id = ?", (session_id,))
        c.execute("DELETE FROM jobs WHERE session_id = ?", (session_id,))
    else:
        # حذف الكل (للتوافق مع الإصدارات القديمة)
        c.execute("SELECT workspace FROM jobs WHERE workspace IS NOT NULL")
        workspaces = c.fetchall()
        
        for ws in workspaces:
            if ws[0] and os.path.exists(ws[0]):
                try:
                    shutil.rmtree(ws[0], ignore_errors=True)
                except:
                    pass
        
        c.execute("DELETE FROM history")
        c.execute("DELETE FROM jobs")
    
    conn.commit()
    conn.close()
    
    # Also clear RAM for this session
    with JOBS_LOCK:
        if session_id:
            # حذف jobs الخاصة بالجلسة فقط
            for job_id in job_ids:
                JOBS.pop(job_id, None)
        else:
            JOBS.clear()
    
    return jsonify({'ok': True})

@app.route('/api/my-jobs')
def get_my_jobs():
    """Get all jobs for current session (from SQLite)"""
    status = request.args.get('status')  # pending, processing, complete, error
    session_id = request.args.get('sessionId')
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if session_id:
        if status:
            c.execute("SELECT * FROM jobs WHERE session_id = ? AND status = ? ORDER BY created_at DESC LIMIT 50", (session_id, status))
        else:
            c.execute("SELECT * FROM jobs WHERE session_id = ? ORDER BY created_at DESC LIMIT 50", (session_id,))
    else:
        if status:
            c.execute("SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT 50", (status,))
        else:
            c.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 50")
    
    rows = c.fetchall()
    conn.close()
    
    result = []
    for j in rows:
        j_dict = dict(j)
        item = {
            'id': j_dict['id'],
            'status': j_dict['status'],
            'percent': j_dict['percent'],
            'eta': j_dict['eta'],
            'createdAt': j_dict['created_at'],
            'completedAt': j_dict['completed_at'],
        }
        
        # Add download URL if complete
        if j_dict['status'] == 'complete' and j_dict['output_path'] and os.path.exists(j_dict['output_path']):
            item['downloadUrl'] = f"/api/download?jobId={j_dict['id']}"
        
        if j_dict['error']:
            item['error'] = j_dict['error']
        
        result.append(item)
    
    return jsonify({'ok': True, 'jobs': result})

@app.route('/api/job/<job_id>')
def get_job_by_id(job_id):
    """Get specific job details"""
    lang = get_request_lang()
    job = get_job(job_id)
    if not job:
        return jsonify({'error': tr_api('job_not_found', lang)}), 404
    return jsonify(job)

@app.route('/api/config')
def conf():
    lang = get_request_lang()
    return jsonify({
        'surahs': get_surah_list(lang),
        'verseCounts': VERSE_COUNTS,
        'reciters': RECITERS_MAP,
        'has_pexels_key': bool(PEXELS_API_KEYS),
        'has_pixabay_key': bool(os.environ.get('PIXABAY_API_KEY', '').strip()),
    })

# ==========================================
# 🔧 Utility Functions
# ==========================================

def background_cleanup():
    """Cleanup old jobs and files every 10 minutes"""
    while True:
        time.sleep(600)  # Every 10 minutes
        try:
            db_cleanup_old_jobs(hours=12)  # Clean jobs older than 12 hours
            print("🧹 Background cleanup completed (12 hour expiry)")
        except Exception as e:
            print(f"Cleanup error: {e}")

def recover_pending_jobs():
    """Resume pending/processing jobs on server restart"""
    pending = db_get_pending_jobs()
    
    if not pending:
        return
    
    print(f"🔄 Found {len(pending)} pending jobs - resuming...")
    
    for job in pending:
        job_id = job['id']
        
        # Check if workspace still exists
        workspace = job.get('workspace')
        if not workspace or not os.path.exists(workspace):
            print(f"⚠️ Job {job_id} workspace missing - marking as error")
            db_update_job(job_id, status='error', error='Workspace deleted')
            continue
        
        # Get config
        config_json = job.get('config_json')
        if not config_json:
            print(f"⚠️ Job {job_id} has no config - marking as error")
            db_update_job(job_id, status='error', error='Config missing')
            continue
        
        try:
            config = json.loads(config_json)
            
            # Reset job status
            db_update_job(job_id, status='pending', percent=0)
            
            # Re-add to RAM
            with JOBS_LOCK:
                JOBS[job_id] = {
                    'id': job_id,
                    'percent': 0,
                    'status': 'pending',
                    'eta': '--:--',
                    'is_running': True,
                    'is_complete': False,
                    'output_path': None,
                    'error': None,
                    'should_stop': False,
                    'created_at': job.get('created_at', time.time()),
                    'workspace': workspace
                }
            
            # Start processing in background
            style_settings = config.get('style', {})
            
            def start_job(jid, cfg, style):
                threading.Thread(
                    target=build_video_task,
                    args=(
                        jid,
                        cfg.get('pexelsKey', ''),
                        cfg.get('reciter', ''),
                        int(cfg.get('surah', 1)),
                        int(cfg.get('startAyah', 1)),
                        int(cfg.get('endAyah', 0)),
                        cfg.get('quality', '720'),
                        cfg.get('bgQuery', ''),
                        int(cfg.get('fps', 20)),
                        cfg.get('dynamicBg', False),
                        cfg.get('useGlow', False),
                        cfg.get('useVignette', False),
                        cfg.get('aspectRatio', '9:16'),
                        style,
                        cfg.get('font', 'Arabic'),
                        cfg.get('fontEn', 'English'),
                        cfg.get('backgroundEffect', 'enhance'),
                        cfg.get('scenePack', 'nature_calm'),
                        cfg.get('bgCrossfadeSec', 0.5),
                        cfg.get('adaptiveTextContrast', False),
                        cfg.get('safeAreaGuides', False),
                        cfg.get('safeAreaPaddingPx', 0),
                        cfg.get('audioProfile', 'studio'),
                        cfg.get('audioDenoise', False),
                        cfg.get('audioDeEss', False)
                    ),
                    daemon=True
                ).start()
            
            # Delay start to allow server to fully initialize
            threading.Timer(2.0, start_job, args=(job_id, config, style_settings)).start()
            
            print(f"✅ Job {job_id} resumed successfully")
            
        except Exception as e:
            print(f"❌ Failed to resume job {job_id}: {e}")
            db_update_job(job_id, status='error', error=str(e))
    
    print(f"🚀 Resume complete - {len(pending)} jobs restarted")

# ==========================================
# 📦 Batch Export System - Multiple Batches in Parallel
# ==========================================

BATCH_QUEUE = []  # قائمة الانتظار
BATCH_QUEUE_LOCK = threading.Lock()
ACTIVE_BATCHES = {}  # الباتشات النشطة
MAX_PARALLEL_BATCHES = 3  # عدد الدفعات المتوازية (كل مستخدم دفعته)

def process_single_batch(batch_id):
    """معالجة دفعة واحدة - فيديو ورا فيديو (تسلسلي)"""
    try:
        print(f"🎬 Starting batch: {batch_id[:8]}...")
        db_update_batch(batch_id, status='running', started_at=time.time())
        
        # معالجة الـ items
        items = db_get_batch_items(batch_id)
        print(f"  📋 Batch {batch_id[:8]}: {len(items)} videos to process")
        
        for item in items:
            try:
                # التحقق من الإيقاف
                batch = db_get_batch(batch_id)
                if batch and batch.get('status') == 'cancelled':
                    print(f"⚠️ Batch {batch_id[:8]}... cancelled")
                    break
                
                job_id = item['job_id']
                
                # الحصول على الـ config
                job = db_get_job(job_id)
                config = None
                
                # أولوية: من الـ job نفسه
                if job and job.get('config_json'):
                    try:
                        config = json.loads(job['config_json'])
                    except:
                        pass
                
                # ثانوية: من batch config (fallback)
                if not config:
                    batch_data = db_get_batch(batch_id)
                    if batch_data and batch_data.get('config_json'):
                        try:
                            config = json.loads(batch_data['config_json'])
                            # دمج بيانات الـ item الحالي
                            config['surah'] = item['surah']
                            config['startAyah'] = item['start_ayah']
                            config['endAyah'] = item['end_ayah']
                        except:
                            pass
                
                if not config:
                    print(f"  ❌ Job {job_id[:8]}... has no config")
                    db_update_batch_item(batch_id, job_id, status='error', error='Config missing')
                    batch = db_get_batch(batch_id)
                    db_update_batch(batch_id, failed_jobs=(batch['failed_jobs'] or 0) + 1)
                    continue
                
                config = json.loads(job['config_json'])
                
                # ✅ اختيار Query حسب الإعدادات (custom query -> scene pack -> safe fallback)
                selected_bg_query = choose_background_query(config.get('bgQuery', ''), config.get('scenePack', 'nature_calm'))
                
                # تحديث حالة الـ item مع وقت البداية
                video_start_time = time.time()
                db_update_batch_item(batch_id, job_id, status='processing', video_started_at=video_start_time)
                db_update_batch(batch_id, current_job_id=job_id, current_job_index=item['position'])
                
                print(f"  🎬 [{item['position'] + 1}/{len(items)}] Surah {item['surah']}, Ayah {item['start_ayah']} | Query: {selected_bg_query}")
                
                # معالجة الفيديو
                style_settings = config.get('style', {})

                # تحديث config_json في الـ job (لو كان فاضيه من الـ fallback)
                if job and not job.get('config_json'):
                    db_update_job(job_id, config_json=json.dumps(config))

                build_video_task(
                    job_id,
                    config.get('pexelsKey', ''),
                    config.get('reciter', ''),
                    item['surah'],
                    item['start_ayah'],
                    item['end_ayah'],
                    config.get('quality', '720'),
                    selected_bg_query,
                    int(config.get('fps', 20)),
                    config.get('dynamicBg', False),
                    config.get('useGlow', False),
                    config.get('useVignette', False),
                    config.get('aspectRatio', '9:16'),
                    style_settings,
                    config.get('font', 'Arabic'),
                    config.get('fontEn', 'English'),
                    config.get('backgroundEffect', 'enhance'),
                    config.get('scenePack', 'nature_calm'),
                    config.get('bgCrossfadeSec', 0.5),
                    config.get('adaptiveTextContrast', False),
                    config.get('safeAreaGuides', False),
                    config.get('safeAreaPaddingPx', 0),
                    config.get('audioProfile', 'studio'),
                    config.get('audioDenoise', False),
                    config.get('audioDeEss', False)
                )
                
                # حساب وقت الفيديو
                video_time = time.time() - video_start_time
                
                # إعادة الحصول على الـ job بعد المعالجة
                updated_job = db_get_job(job_id)
                output_path = updated_job.get('output_path') if updated_job else None
                
                # تحديث حالة الـ item
                db_update_batch_item(batch_id, job_id, status='complete', output_path=output_path)
                
                # تحديث الـ batch counter ومتوسط الوقت
                batch = db_get_batch(batch_id)
                completed = (batch['completed_jobs'] or 0) + 1
                old_avg = batch.get('avg_video_time') or 0
                new_avg = ((old_avg * (completed - 1)) + video_time) / completed
                db_update_batch(batch_id, completed_jobs=completed, avg_video_time=new_avg)
                print(f"  ✅ [{item['position'] + 1}/{len(items)}] Done! ({video_time:.1f}s)")
                
            except Exception as item_error:
                print(f"  ❌ Video {item.get('position', '?') + 1} failed: {item_error}")
                traceback.print_exc()
                try:
                    db_update_batch_item(batch_id, item['job_id'], status='error', error=str(item_error))
                    batch = db_get_batch(batch_id)
                    db_update_batch(batch_id, failed_jobs=(batch['failed_jobs'] or 0) + 1)
                except:
                    pass
        
        # إنهاء الباتش
        batch = db_get_batch(batch_id)
        db_update_batch(batch_id, status='complete', completed_at=time.time())
        print(f"📦 Batch {batch_id[:8]}... complete: {batch['completed_jobs']}/{batch['total_jobs']} videos")
        
    except Exception as e:
        print(f"❌ Batch {batch_id[:8]}... error: {e}")
        traceback.print_exc()
        db_update_batch(batch_id, status='error', error=str(e))
    
    finally:
        # إزالة من ACTIVE_BATCHES
        with BATCH_QUEUE_LOCK:
            if batch_id in ACTIVE_BATCHES:
                del ACTIVE_BATCHES[batch_id]
        print(f"🔄 Batch {batch_id[:8]}... released slot (active: {len(ACTIVE_BATCHES)})")

def process_batch_queue():
    """مراقبة قائمة الانتظار وتشغيل دفعات متعددة بالتوازي"""
    print("📦 Batch processor started - can run up to 3 batches in parallel")
    
    while True:
        try:
            # عدد الدفعات النشطة
            active_count = len(ACTIVE_BATCHES)
            
            # لو فيه مكان لدفعات جديدة
            if active_count < MAX_PARALLEL_BATCHES:
                # البحث عن دفعة pending في الـ queue
                with BATCH_QUEUE_LOCK:
                    for batch_id in BATCH_QUEUE[:]:  # نسخة من القائمة
                        # تجاهل لو الدفعة دي شغالة
                        if batch_id in ACTIVE_BATCHES:
                            continue
                        
                        # التحقق من الحالة
                        batch = db_get_batch(batch_id)
                        if not batch:
                            BATCH_QUEUE.remove(batch_id)
                            continue
                        
                        # لو الدفعة مكتملة أو ملغاة
                        if batch['status'] in ['complete', 'cancelled']:
                            BATCH_QUEUE.remove(batch_id)
                            continue
                        
                        # لو الدفعة pending - نبدأها
                        if batch['status'] == 'pending':
                            ACTIVE_BATCHES[batch_id] = True
                            print(f"🚀 Starting batch {batch_id[:8]}... (active: {active_count + 1}/{MAX_PARALLEL_BATCHES})")
                            
                            # تشغيل في thread منفصل
                            t = threading.Thread(
                                target=process_single_batch,
                                args=(batch_id,),
                                daemon=True
                            )
                            t.start()
                            break  # نبدأ دفعة واحدة كل مرة
            
            # استراحة قصيرة
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Batch queue error: {e}")
            time.sleep(2)

def recover_pending_batches():
    """استئناف الباتشات المعلقة"""
    pending = db_get_pending_batches()
    
    if not pending:
        return
    
    print(f"📦 Found {len(pending)} pending/running batches - checking...")
    
    for batch in pending:
        batch_id = batch['id']
        
        # لو الباتش في حالة running - نعمله reset لـ pending
        # لأن مفيش معالجة شغالة حالياً (السيرفر لسه شغال)
        if batch['status'] == 'running':
            print(f"  🔄 Resetting stuck batch {batch_id[:8]}... from 'running' to 'pending'")
            db_update_batch(batch_id, status='pending')
        
        with BATCH_QUEUE_LOCK:
            if batch_id not in BATCH_QUEUE:
                BATCH_QUEUE.append(batch_id)
        
        print(f"  ✅ Batch {batch_id[:8]}... queued for processing")

@app.route('/api/batch/create', methods=['POST'])
@limiter.limit("5 per hour")  # 🛡️ 5 دفعات في الساعة
def create_batch():
    """إنشاء باتش جديد من فيديوهات متعددة - كل فيديو بإعداداته الخاصة"""
    d = request.json
    lang = get_request_lang(d)

    items = d.get('items', [])  # قائمة الفيديوهات [{surah, startAyah, endAyah, reciter, dynamicBg, useGlow, useVignette, aspectRatio, font, fontEn}, ...]
    session_id = d.get('sessionId')

    print(f"📥 Batch create request received: {len(items)} items")

    if not items:
        print("❌ No items provided")
        return jsonify({'ok': False, 'error': tr_api('no_items_provided', lang)}), 400

    # الإعدادات العامة (fallback)
    global_config = {
        'reciter': d.get('reciter'),
        'quality': d.get('quality', '720'),
        'fps': d.get('fps', 20),
        'dynamicBg': d.get('dynamicBg', True),
        'useGlow': d.get('useGlow', True),
        'useVignette': d.get('useVignette', True),
        'backgroundEffect': d.get('backgroundEffect', 'enhance'),
        'scenePack': d.get('scenePack', 'nature_calm'),
        'bgCrossfadeSec': d.get('bgCrossfadeSec', 0.5),
        'adaptiveTextContrast': d.get('adaptiveTextContrast', False),
        'safeAreaGuides': d.get('safeAreaGuides', False),
        'safeAreaPaddingPx': d.get('safeAreaPaddingPx', 0),
        'audioProfile': d.get('audioProfile', 'studio'),
        'audioDenoise': d.get('audioDenoise', False),
        'audioDeEss': d.get('audioDeEss', False),
        'aspectRatio': d.get('aspectRatio', '9:16'),
        'font': d.get('font', 'Arabic'),
        'fontEn': d.get('fontEn', 'English'),
        'bgQuery': d.get('bgQuery', ''),
        'pexelsKey': d.get('pexelsKey', ''),
        'style': d.get('style', {}),
        'session_id': session_id
    }

    # إنشاء الباتش
    batch_id = str(uuid.uuid4())
    db_create_batch(batch_id, len(items), global_config)
    print(f"📦 Created batch: {batch_id}")

    # إنشاء الـ jobs والـ items
    for i, item in enumerate(items):
        # دمج الإعدادات الخاصة بالـ item مع الإعدادات العامة
        job_config = global_config.copy()
        job_config['surah'] = item['surah']
        job_config['startAyah'] = item['startAyah']
        job_config['endAyah'] = item['endAyah']

        # الإعدادات الخاصة بالـ item (لو موجودة)
        if item.get('reciter'):
            job_config['reciter'] = item['reciter']
        if item.get('dynamicBg') is not None:
            job_config['dynamicBg'] = item['dynamicBg']
        if item.get('useGlow') is not None:
            job_config['useGlow'] = item['useGlow']
        if item.get('useVignette') is not None:
            job_config['useVignette'] = item['useVignette']
        if item.get('backgroundEffect'):
            job_config['backgroundEffect'] = item['backgroundEffect']
        if item.get('aspectRatio'):
            job_config['aspectRatio'] = item['aspectRatio']
        if item.get('font'):
            job_config['font'] = item['font']
        if item.get('fontEn'):
            job_config['fontEn'] = item['fontEn']
        if item.get('fps'):
            job_config['fps'] = item['fps']
        if item.get('quality'):
            job_config['quality'] = item['quality']
        if item.get('bgQuery'):
            job_config['bgQuery'] = item['bgQuery']
        if item.get('scenePack'):
            job_config['scenePack'] = item['scenePack']
        if item.get('bgCrossfadeSec') is not None:
            job_config['bgCrossfadeSec'] = item['bgCrossfadeSec']
        if item.get('adaptiveTextContrast') is not None:
            job_config['adaptiveTextContrast'] = item['adaptiveTextContrast']
        if item.get('safeAreaGuides') is not None:
            job_config['safeAreaGuides'] = item['safeAreaGuides']
        if item.get('safeAreaPaddingPx') is not None:
            job_config['safeAreaPaddingPx'] = item['safeAreaPaddingPx']
        if item.get('audioProfile'):
            job_config['audioProfile'] = item['audioProfile']
        if item.get('audioDenoise') is not None:
            job_config['audioDenoise'] = item['audioDenoise']
        if item.get('audioDeEss') is not None:
            job_config['audioDeEss'] = item['audioDeEss']

        job_id = create_job(job_config, session_id)
        db_add_batch_item(batch_id, job_id, i, item['surah'], item['startAyah'], item['endAyah'])
        print(f"  ✅ Created job {i+1}/{len(items)}: {job_id[:8]}...")
    
    # إضافة للقائمة
    with BATCH_QUEUE_LOCK:
        BATCH_QUEUE.append(batch_id)
        print(f"📋 Added batch {batch_id} to queue. Queue length: {len(BATCH_QUEUE)}")
    
    print(f"✅ Batch {batch_id} ready with {len(items)} videos")
    
    return jsonify({
        'ok': True,
        'batchId': batch_id,
        'totalJobs': len(items),
        'items': items
    })

@app.route('/api/batch/status')
@limiter.exempt
def get_batch_status():
    """الحصول على حالة الباتش"""
    batch_id = request.args.get('batchId')
    lang = get_request_lang()
    
    if not batch_id:
        return jsonify({'ok': False, 'error': tr_api('batch_id_required', lang)}), 400
    
    batch = db_get_batch(batch_id)
    if not batch:
        return jsonify({'ok': False, 'error': tr_api('batch_not_found', lang)}), 404
    
    items = db_get_batch_items(batch_id)
    
    # إضافة معلومات كل فيديو
    items_info = []
    current_video = None
    current_item_started_at = None
    
    for item in items:
        job = db_get_job(item['job_id'])
        item_info = {
            'position': item['position'],
            'surah': item['surah'],
            'startAyah': item['start_ayah'],
            'endAyah': item['end_ayah'],
            'status': item['status'],
            'jobId': item['job_id'],
            'percent': job.get('percent', 0) if job else 0,
            'downloadUrl': f"/api/download?jobId={item['job_id']}" if item['status'] == 'complete' and job and job.get('output_path') else None
        }
        items_info.append(item_info)
        
        # تحديد الفيديو الحالي
        if item['status'] == 'processing':
            current_video = item_info
            current_item_started_at = item.get('video_started_at')
    
    # حساب الوقت المتبقي
    remaining_time = None
    remaining_videos = batch['total_jobs'] - (batch['completed_jobs'] or 0) - (batch['failed_jobs'] or 0)
    
    if batch['status'] == 'running':
        avg_time = batch.get('avg_video_time') or 45  # افتراض 45 ثانية لو مفيش متوسط
        remaining_time = int(remaining_videos * avg_time)
        
        # لو فيه فيديو حالي، نطرح الوقت اللي فات
        if current_item_started_at:
            elapsed = time.time() - current_item_started_at
            remaining_time = max(0, remaining_time - int(elapsed))
    
    # الحصول على اسم السورة للفيديو الحالي
    surah_name = None
    if current_video:
        surah_idx = current_video['surah'] - 1  # السور مرقمة من 1، الـ list من 0
        surah_name = get_surah_name(current_video['surah'], lang)
    
    return jsonify({
        'ok': True,
        'batch': {
            'id': batch['id'],
            'status': batch['status'],
            'totalJobs': batch['total_jobs'],
            'completedJobs': batch['completed_jobs'],
            'failedJobs': batch['failed_jobs'],
            'currentJobIndex': batch['current_job_index'],
            'createdAt': batch['created_at'],
            'startedAt': batch.get('started_at'),
            'completedAt': batch.get('completed_at'),
            'avgVideoTime': batch.get('avg_video_time'),
            'remainingTime': remaining_time,
            'remainingVideos': remaining_videos,
            'currentVideo': {
                'surahName': surah_name,
                'surah': current_video['surah'] if current_video else None,
                'ayah': current_video['startAyah'] if current_video else None,
                'position': current_video['position'] if current_video else None
            } if current_video else None,
            'items': items_info
        }
    })

@app.route('/api/batch/list')
def list_batches():
    """الحصول على قائمة الباتشات للجلسة"""
    session_id = request.args.get('sessionId')
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if session_id:
        # الحصول على jobs الخاصة بالجلسة ثم الباتشات
        c.execute('''
            SELECT DISTINCT b.* FROM batch_jobs b
            JOIN batch_items bi ON b.id = bi.batch_id
            JOIN jobs j ON bi.job_id = j.id
            WHERE j.session_id = ?
            ORDER BY b.created_at DESC LIMIT 20
        ''', (session_id,))
    else:
        c.execute("SELECT * FROM batch_jobs ORDER BY created_at DESC LIMIT 20")
    
    rows = c.fetchall()
    conn.close()
    
    batches = []
    for row in rows:
        b = dict(row)
        batches.append({
            'id': b['id'],
            'status': b['status'],
            'totalJobs': b['total_jobs'],
            'completedJobs': b['completed_jobs'],
            'failedJobs': b['failed_jobs'],
            'createdAt': b['created_at'],
            'completedAt': b.get('completed_at')
        })
    
    return jsonify({'ok': True, 'batches': batches})

@app.route('/api/batch/cancel', methods=['POST'])
def cancel_batch():
    """إلغاء باتش"""
    d = request.json
    lang = get_request_lang(d)
    batch_id = d.get('batchId')
    
    if not batch_id:
        return jsonify({'ok': False, 'error': tr_api('batch_id_required', lang)}), 400
    
    batch = db_get_batch(batch_id)
    if not batch:
        return jsonify({'ok': False, 'error': tr_api('batch_not_found', lang)}), 404
    
    if batch['status'] in ['complete', 'cancelled']:
        return jsonify({'ok': False, 'error': tr_api('cannot_cancel_completed_batch', lang)}), 400
    
    db_update_batch(batch_id, status='cancelled', completed_at=time.time())
    
    # إيقاف الـ job الحالي
    if batch.get('current_job_id'):
        with JOBS_LOCK:
            if batch['current_job_id'] in JOBS:
                JOBS[batch['current_job_id']]['should_stop'] = True
    
    # إزالة من القائمة
    with BATCH_QUEUE_LOCK:
        if batch_id in BATCH_QUEUE:
            BATCH_QUEUE.remove(batch_id)
    
    return jsonify({'ok': True})

# ==========================================
# 📺 YouTube Integration
# ==========================================

# YouTube OAuth Configuration
# يجب استبدال هذه القيم بالقيم الخاصة بك من Google Cloud Console
YOUTUBE_CLIENT_ID = os.environ.get('YOUTUBE_CLIENT_ID', '')
YOUTUBE_CLIENT_SECRET = os.environ.get('YOUTUBE_CLIENT_SECRET', '')
# مهم: يجب ضبط هذا المتغير على URL التطبيق الفعلي
# مثال: https://username-spacename.hf.space
YOUTUBE_REDIRECT_URI = os.environ.get('YOUTUBE_REDIRECT_URI', '')

# Scopes المطلوبة
YOUTUBE_SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

# تخزين الـ tokens في الذاكرة (يمكن نقله لقاعدة البيانات لاحقاً)
YOUTUBE_TOKENS = {}  # session_id -> credentials

def get_base_url():
    """الحصول على الـ base URL ديناميكياً من الطلب"""
    # أولوية لـ X-Forwarded headers (للـ reverse proxies زي Hugging Face)
    forwarded_host = request.headers.get('X-Forwarded-Host')
    forwarded_proto = request.headers.get('X-Forwarded-Proto', 'https')
    
    if forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}"
    
    # fallback للـ host العادي
    host = request.headers.get('Host', 'localhost:7860')
    
    # HuggingFace Spaces دائماً تستخدم https
    if 'hf.space' in host:
        proto = 'https'
    else:
        proto = 'https' if request.scheme == 'https' else 'http'
    
    return f"{proto}://{host}"

def get_youtube_redirect_uri():
    """الحصول على redirect URI"""
    # أولوية لـ environment variable
    if YOUTUBE_REDIRECT_URI:
        redirect_uri = YOUTUBE_REDIRECT_URI
        if not redirect_uri.endswith('/api/youtube/callback'):
            redirect_uri = redirect_uri.rstrip('/') + '/api/youtube/callback'
        return redirect_uri
    
    # fallback للكشف التلقائي
    base_url = get_base_url()
    redirect_uri = f"{base_url}/api/youtube/callback"
    
    # طباعة تحذير مهم
    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║ ⚠️  YOUTUBE REDIRECT URI NOTICE                               ║
    ╠══════════════════════════════════════════════════════════════╣
    ║ Redirect URI: {redirect_uri:<47} ║
    ║                                                              ║
    ║ Add this URL to Google Cloud Console:                        ║
    ║ APIs & Services > Credentials > OAuth 2.0 Client IDs         ║
    ║ > Authorized redirect URIs                                   ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    return redirect_uri

def get_youtube_auth_url(session_id):
    """إنشاء رابط المصادقة"""
    if not YOUTUBE_CLIENT_ID:
        return None
    
    redirect_uri = get_youtube_redirect_uri()
    print(f"[YouTube] Using redirect URI: {redirect_uri}")
    
    # استخدام طريقة بسيطة - URL مباشر
    from urllib.parse import urlencode, quote
    
    params = {
        'client_id': YOUTUBE_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': ' '.join(YOUTUBE_SCOPES),
        'access_type': 'offline',
        'prompt': 'consent',  # مهم جداً: يضمن الحصول على refresh_token جديد
        'include_granted_scopes': 'true',
        'state': session_id
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"
    return auth_url

def get_youtube_service(session_id):
    """الحصول على خدمة YouTube للمستخدم"""
    if session_id not in YOUTUBE_TOKENS:
        return None
    
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        
        creds_data = YOUTUBE_TOKENS[session_id]
        
        # التحقق من وجود refresh_token
        if not creds_data.get('refresh_token'):
            print(f"[YouTube] No refresh_token found for session, deleting invalid token")
            del YOUTUBE_TOKENS[session_id]
            return None
        
        credentials = Credentials(
            token=creds_data['token'],
            refresh_token=creds_data['refresh_token'],
            token_uri='https://oauth2.googleapis.com/token',
            client_id=YOUTUBE_CLIENT_ID,
            client_secret=YOUTUBE_CLIENT_SECRET,
            scopes=YOUTUBE_SCOPES
        )
        
        return build('youtube', 'v3', credentials=credentials)
    except Exception as e:
        print(f"[YouTube] Error getting service: {e}")
        # حذف token التالف إذا كان الخطأ متعلق بـ credentials
        if 'refresh_token' in str(e).lower() or 'credentials' in str(e).lower():
            if session_id in YOUTUBE_TOKENS:
                del YOUTUBE_TOKENS[session_id]
                print(f"[YouTube] Deleted invalid token for session: {session_id[:20]}...")
        return None

@app.route('/api/youtube/auth-url')
def youtube_auth_url():
    """الحصول على رابط المصادقة"""
    session_id = request.args.get('sessionId')
    lang = get_request_lang()
    
    if not YOUTUBE_CLIENT_ID:
        return jsonify({
            'ok': False, 
            'error': tr_api('youtube_not_configured', lang),
            'needsConfig': True
        })
    
    # التحقق من وجود token صالح
    if session_id and session_id in YOUTUBE_TOKENS:
        return jsonify({'ok': True, 'alreadyAuthorized': True})
    
    auth_url = get_youtube_auth_url(session_id)
    if auth_url:
        return jsonify({'ok': True, 'authUrl': auth_url})
    else:
        return jsonify({'ok': False, 'error': tr_api('failed_auth_url', lang)})

@app.route('/api/youtube/callback')
def youtube_callback():
    """استقبال callback من Google OAuth"""
    from google_auth_oauthlib.flow import Flow
    import urllib.parse
    
    # الحصول على state (session_id)
    state = request.args.get('state')
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        return f'''
        <html>
        <head><title>خطأ</title></head>
        <body style="font-family:Arial; text-align:center; padding:50px;">
            <h2 style="color:red;">❌ فشل في المصادقة</h2>
            <p>{error}</p>
            <p>يمكنك إغلاق هذه الصفحة</p>
            <script>setTimeout(() => window.close(), 3000);</script>
        </body>
        </html>
        '''
    
    # الحصول على redirect URI ديناميكي (قبل try عشان يبقى متاح في exception)
    redirect_uri = get_youtube_redirect_uri()
    print(f"[YouTube] Callback using redirect URI: {redirect_uri}")
    
    try:
        
        flow = Flow.from_client_config({
            'web': {
                'client_id': YOUTUBE_CLIENT_ID,
                'client_secret': YOUTUBE_CLIENT_SECRET,
                'redirect_uris': [redirect_uri],
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token'
            }
        }, scopes=YOUTUBE_SCOPES)
        
        flow.redirect_uri = redirect_uri
        flow.fetch_token(authorization_response=request.url)
        
        credentials = flow.credentials
        
        # التحقق من وجود refresh_token
        if not credentials.refresh_token:
            print(f"[YouTube] WARNING: No refresh_token received!")
            return f'''
            <html>
            <head><title>خطأ</title></head>
            <body style="font-family:Arial; text-align:center; padding:50px; background:#1a1a1a; color:#fff; direction:rtl;">
                <h2 style="color:#f59e0b;">⚠️ لم يتم الحصول على refresh_token</h2>
                <p>يرجى إعادة المحاولة والموافقة على جميع الأذونات</p>
                <p style="color:#888;">تأكد من الضغط على "Allow" في صفحة الموافقة</p>
                <script>setTimeout(() => window.close(), 5000);</script>
            </body>
            </html>
            '''
        
        # تخزين الـ token
        YOUTUBE_TOKENS[state] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        print(f"[YouTube] Token stored for session: {state[:20]}...")
        print(f"[YouTube] refresh_token present: {bool(credentials.refresh_token)}")
        
        return f'''
        <html>
        <head><title>تم بنجاح</title></head>
        <body style="font-family:Arial; text-align:center; padding:50px; background:#1a1a1a; color:#fff;">
            <h2 style="color:#22c55e;">✅ تم ربط حساب YouTube بنجاح!</h2>
            <p>يمكنك الآن نشر فيديوهاتك على يوتيوب</p>
            <p style="color:#888;">يمكنك إغلاق هذه الصفحة والعودة للتطبيق</p>
            <script>
                // إرسال رسالة للنافذة الأب
                if (window.opener) {{
                    window.opener.postMessage({{ type: 'youtube_auth_success' }}, '*');
                }}
                setTimeout(() => window.close(), 2000);
            </script>
        </body>
        </html>
        '''
        
    except Exception as e:
        error_str = str(e)
        print(f"[YouTube] OAuth callback error: {e}")
        import traceback
        traceback.print_exc()
        
        # رسالة خاصة لخطأ redirect_uri_mismatch
        if 'redirect_uri_mismatch' in error_str.lower() or 'mismatch' in error_str.lower():
            return f'''
            <html>
            <head><title>خطأ في الإعدادات</title></head>
            <body style="font-family:Arial; text-align:center; padding:50px; background:#1a1a1a; color:#fff; direction:rtl;">
                <h2 style="color:#f59e0b;">⚠️ خطأ في إعدادات Google OAuth</h2>
                <p>الـ Redirect URI غير مطابق</p>
                <div style="background:#333; padding:15px; border-radius:8px; margin:20px 0; text-align:left; direction:ltr;">
                    <p style="margin:0; color:#888;">Redirect URI المطلوب:</p>
                    <p style="margin:5px 0; color:#22c55e; word-break:break-all;">{redirect_uri}</p>
                </div>
                <p style="color:#888; font-size:14px;">
                    أضف هذا URL في Google Cloud Console:<br>
                    APIs & Services → Credentials → OAuth 2.0 Client IDs<br>
                    → Authorized redirect URIs
                </p>
                <script>setTimeout(() => window.close(), 10000);</script>
            </body>
            </html>
            '''
        
        return f'''
        <html>
        <head><title>خطأ</title></head>
        <body style="font-family:Arial; text-align:center; padding:50px; background:#1a1a1a; color:#fff;">
            <h2 style="color:red;">❌ حدث خطأ</h2>
            <p>{error_str}</p>
            <script>setTimeout(() => window.close(), 5000);</script>
        </body>
        </html>
        '''

@app.route('/api/youtube/status')
def youtube_status():
    """التحقق من حالة الاتصال بـ YouTube"""
    session_id = request.args.get('sessionId')
    
    if not YOUTUBE_CLIENT_ID:
        return jsonify({'ok': True, 'configured': False, 'authorized': False})
    
    authorized = session_id in YOUTUBE_TOKENS
    
    # الحصول على redirect URI لعرضه للمستخدم
    current_redirect_uri = get_youtube_redirect_uri()
    
    return jsonify({
        'ok': True, 
        'configured': bool(YOUTUBE_CLIENT_ID),
        'authorized': authorized,
        'redirectUri': current_redirect_uri
    })

@app.route('/api/youtube/redirect-uri')
def youtube_redirect_uri():
    """الحصول على redirect URI المطلوب (لل debug)"""
    return jsonify({
        'ok': True,
        'redirectUri': get_youtube_redirect_uri(),
        'instructions': {
            'ar': 'أضف هذا URL في Google Cloud Console: APIs & Services > Credentials > OAuth 2.0 Client IDs > Authorized redirect URIs',
            'en': 'Add this URL to Google Cloud Console: APIs & Services > Credentials > OAuth 2.0 Client IDs > Authorized redirect URIs'
        }
    })

@app.route('/api/youtube/upload', methods=['POST'])
def youtube_upload():
    """رفع فيديو على YouTube مع دعم الجدولة"""
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    from datetime import datetime, timezone, timedelta
    
    data = request.json
    lang = get_request_lang(data)
    session_id = data.get('sessionId')
    job_id = data.get('jobId')
    title = data.get('title', '')
    description = data.get('description', '')
    tags = data.get('tags', [])
    privacy_status = data.get('privacyStatus', 'unlisted')  # public, unlisted, private, scheduled
    schedule_time = data.get('scheduleTime')  # ISO format datetime string
    
    if not session_id or not job_id:
        return jsonify({'ok': False, 'error': tr_api('missing_session_or_job', lang)}), 400
    
    # الحصول على الفيديو
    job = db_get_job(job_id)
    if not job or not job.get('output_path'):
        return jsonify({'ok': False, 'error': tr_api('video_not_found', lang)}), 404
    
    video_path = job['output_path']
    if not os.path.exists(video_path):
        return jsonify({'ok': False, 'error': tr_api('video_file_not_found', lang)}), 404
    
    # الحصول على خدمة YouTube
    youtube = get_youtube_service(session_id)
    if not youtube:
        return jsonify({'ok': False, 'error': tr_api('youtube_not_authorized', lang), 'needsAuth': True}), 401
    
    try:
        # تحديد حالة الخصوصية الفعلية
        # ملاحظة: 'scheduled' ليست قيمة صالحة لـ privacyStatus
        # للجدولة نستخدم 'private' مع publishAt
        if privacy_status == 'scheduled':
            actual_privacy = 'private'  # للجدولة: private أولاً
        else:
            actual_privacy = privacy_status
        publish_at = None
        
        if privacy_status == 'scheduled' and schedule_time:
            # للجدولة: تحويل الوقت المحلي لـ UTC بشكل صحيح
            try:
                print(f"[YouTube] Raw schedule_time received: {schedule_time}")
                
                # تحويل الـ string لـ datetime object
                # دعم صيغ متعددة
                try:
                    # صيغة ISO مع timezone
                    local_dt = datetime.fromisoformat(schedule_time.replace('Z', '+00:00'))
                except:
                    # صيغة بدون timezone - نفترض توقيت المستخدم المحلي
                    local_dt = datetime.fromisoformat(schedule_time)
                
                # الوقت الحالي UTC
                now_utc = datetime.now(timezone.utc)
                
                # تحويل لـ UTC بشكل صحيح
                if local_dt.tzinfo is None:
                    # الوقت بدون timezone - نفترض أنه توقيت محلي للمستخدم
                    # نعتبره UTC ولكن نتحقق إذا كان في الماضي
                    utc_dt = local_dt
                    
                    # التحقق: إذا كان الوقت أقل من الآن + ساعة، نعتبر أن المستخدم أرسل وقت محلي
                    # ونحوله من توقيت مصر/السعودية (UTC+2/3) لـ UTC
                    test_min = now_utc.replace(tzinfo=None) + timedelta(hours=1)
                    if utc_dt < test_min:
                        # على الأرجح الوقت محلي، نحوله لـ UTC بافتراض UTC+3
                        print("[YouTube] Time seems to be local, converting from UTC+3")
                        utc_dt = local_dt - timedelta(hours=3)
                else:
                    # تحويل من التوقيت المحلي لـ UTC
                    utc_dt = local_dt.astimezone(timezone.utc).replace(tzinfo=None)
                
                # تنسيق الوقت بصيغة YouTube المطلوبة (RFC 3339)
                publish_at = utc_dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
                
                # التحقق أن الوقت في المستقبل (على الأقل 30 دقيقة للجدولة)
                # YouTube يتطلب 10 دقائق، لكن نزيد احتياطاً للرفع
                now_utc_naive = now_utc.replace(tzinfo=None)
                min_time = now_utc_naive + timedelta(minutes=30)
                
                print(f"[YouTube] Parsed UTC time: {utc_dt}")
                print(f"[YouTube] Current UTC: {now_utc_naive}")
                print(f"[YouTube] Min allowed: {min_time}")
                print(f"[YouTube] Final publishAt: {publish_at}")
                
                if utc_dt < min_time:
                    # بدل الرفض، نعدل الوقت تلقائياً
                    utc_dt = now_utc_naive + timedelta(hours=1)
                    publish_at = utc_dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
                    print(f"[YouTube] Time too close, auto-adjusted to: {publish_at}")
                
                # الحد الأقصى للجدولة هو 6 أشهر
                max_time = now_utc_naive + timedelta(days=180)
                if utc_dt > max_time:
                    return jsonify({
                        'ok': False,
                        'error': tr_api('schedule_too_far', lang)
                    }), 400
                
            except Exception as e:
                print(f"[YouTube] Schedule time error: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'ok': False, 'error': tr_api('schedule_time_error', lang, detail=str(e))}), 400
        
        # إعداد الـ body
        body = {
            'snippet': {
                'title': title[:100],  # YouTube limit
                'description': description[:5000],  # YouTube limit
                'tags': tags[:500],  # YouTube limit
                'categoryId': '22'  # People & Blogs
            },
            'status': {
                'privacyStatus': 'private' if publish_at else actual_privacy,  # للجدولة: private أولاً
                'selfDeclaredMadeForKids': False
            }
        }
        
        # للجدولة: نرفع الفيديو كـ private مع تحديد publishAt
        # YouTube سيقوم بنشره تلقائياً في الوقت المحدد
        if publish_at:
            body['status']['publishAt'] = publish_at
            print(f"[YouTube] Video will be scheduled for: {publish_at}")
        
        print(f"[YouTube] Uploading video: {title[:50]}...")
        print(f"[YouTube] Privacy: {body['status']['privacyStatus']}")
        if publish_at:
            print(f"[YouTube] Scheduled for: {publish_at}")
        
        # رفع الفيديو
        media = MediaFileUpload(
            video_path,
            mimetype='video/mp4',
            resumable=True,
            chunksize=1024*1024  # 1MB chunks
        )
        
        request_obj = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )
        
        response = request_obj.execute()
        
        video_id = response['id']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        return jsonify({
            'ok': True,
            'videoId': video_id,
            'videoUrl': video_url,
            'title': response['snippet']['title'],
            'scheduled': bool(publish_at),
            'scheduledTime': publish_at
        })
        
    except HttpError as e:
        error_body = json.loads(e.content.decode('utf-8'))
        error_msg = error_body.get('error', {}).get('message', str(e))
        print(f"[YouTube] Upload error: {error_msg}")
        return jsonify({'ok': False, 'error': tr_api('youtube_upload_failed', lang, detail=error_msg)}), 400
    except Exception as e:
        print(f"[YouTube] Upload error: {e}")
        return jsonify({'ok': False, 'error': tr_api('unexpected_server_error', lang)}), 500

@app.route('/api/youtube/disconnect', methods=['POST'])
def youtube_disconnect():
    """قطع الاتصال بـ YouTube"""
    session_id = request.json.get('sessionId')
    
    if session_id and session_id in YOUTUBE_TOKENS:
        del YOUTUBE_TOKENS[session_id]
    
    return jsonify({'ok': True})

# ==========================================
# 🚀 Application Startup (Correct Order!)
# ==========================================

# ✅ كشف بيئة HuggingFace
IS_HUGGINGFACE = bool(os.environ.get('SPACE_ID')) or bool(os.environ.get('SPACE_AUTHOR_NAME'))

# 1. Initialize database FIRST (before any threads)
print("📦 Initializing database...")
init_db()

# 2. Handle pending jobs from previous session
if IS_HUGGINGFACE:
    # ✅ على HuggingFace: تنظيف بس المشlugل - مستني الباتشات تاني
    print("🔄 HuggingFace detected - cleaning stale single jobs...")
    try:
        stale_jobs = db_get_pending_jobs()
        for job in stale_jobs:
            # شيك لو الـ job ده مش جزء من batch
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT batch_id FROM batch_items WHERE job_id = ?", (job['id'],))
            batch_check = c.fetchone()
            conn.close()
            
            if batch_check is None:
                # ده job فردي (مش جزء من batch) - نلغيه
                db_update_job(job['id'], status='error', error='Server restarted (HuggingFace sleep)')
            else:
                # ده جزء من batch - نسيبه_pending عشان batch processor يعالجه
                pass
        
        if stale_jobs:
            print(f"🧹 Checked {len(stale_jobs)} stale jobs (batch jobs preserved)")
        
        # إعادة الباتشات اللي كانت running لـ pending
        stale_batches = db_get_pending_batches()
        for batch in stale_batches:
            if batch['status'] == 'running':
                db_update_batch(batch['id'], status='pending')
                print(f"  🔄 Reset batch {batch['id'][:8]}... to 'pending'")
    except Exception as e:
        print(f"⚠️ Failed to clean stale jobs: {e}")
else:
    # على السيرفر المحلي: استئناف الـ jobs كالعادي
    print("🔄 Recovering pending jobs...")
    try:
        recover_pending_jobs()
    except Exception as e:
        print(f"⚠️ Failed to recover pending jobs: {e}")

    print("📦 Recovering pending batches...")
    try:
        recover_pending_batches()
    except Exception as e:
        print(f"⚠️ Failed to recover pending batches: {e}")

# 3. Start background threads AFTER database is ready
print("🧵 Starting background threads...")

# Start batch processor thread
batch_thread = threading.Thread(target=process_batch_queue, daemon=True, name="BatchProcessor")
batch_thread.start()
print("✅ Batch processor thread started")

# Start cleanup thread
cleanup_thread = threading.Thread(target=background_cleanup, daemon=True, name="CleanupThread")
cleanup_thread.start()
print("✅ Cleanup thread started")

print("🚀 Quran Reels Generator ready!")

if __name__ == "__main__":
    print("🚀 Starting Flask development server...")
    port = int(os.environ.get("PORT", "7860"))
    app.run(host='0.0.0.0', port=port, threaded=True)


