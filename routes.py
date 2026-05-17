"""
Flask API routes - generate, progress, download, history, config, health.
"""
import os
import json
import time
import datetime
import sqlite3
import shutil
import threading
import requests
from flask import request, jsonify, send_file
from config import (
    EXEC_DIR, OUTPUTS_DIR, UI_PATH, PEXELS_API_KEYS, DB_PATH,
)
from i18n import get_request_lang, tr_api, format_duration
from quran_data import (
    VERSE_COUNTS, RECITERS_MAP, RECITER_ID_TO_NAME,
    NEW_RECITERS_CONFIG, MP3QURAN_IDS, ValidationError,
    validate_ayah_range, get_surah_name, get_surah_list,
    smart_estimate_by_length,
)
from database import (
    db_get_job, db_update_job, db_get_history, db_add_history,
    db_get_pending_jobs, db_cleanup_old_jobs,
)
from jobs import (
    create_job, get_job, update_job_status, JOBS, JOBS_LOCK,
)
from video import build_video_task

START_TIME = time.time()

# ═══════════════════════════════════════
# ⏱️ API: Estimate Duration (المدة التقريبية الفعلية)
# ═══════════════════════════════════════
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

def ui(): return send_file(UI_PATH) if os.path.exists(UI_PATH) else "API Running"

# ✅ HuggingFace Health Check Endpoint - مهم جداً!
# HuggingFace بتعمل ping على الـ '/' route عشان تتأكد إن التطبيق شغال
def hf_health():
    """HuggingFace Spaces health check endpoint"""
    return '', 200

def favicon():
    """Return empty 204 for favicon requests to suppress browser 404 errors"""
    return '', 204

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

def prog(): 
    job = get_job(request.args.get('jobId'))
    if job:
        # Add download URL if complete
        if job.get('status') == 'complete' and job.get('output_path'):
            job['download_url'] = f"/api/download?jobId={job['id']}"
    return jsonify(job)

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

def get_history_route():
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

def get_job_by_id(job_id):
    """Get specific job details"""
    lang = get_request_lang()
    job = get_job(job_id)
    if not job:
        return jsonify({'error': tr_api('job_not_found', lang)}), 404
    return jsonify(job)

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


def register_routes(app, limiter):
    """Register all core routes on the Flask app."""
    app.teardown_appcontext(lambda exc: None)  # DB teardown registered in main.py
    # UI
    app.add_url_rule("/", "ui", ui)
    app.add_url_rule("/healthz", "hf_health", hf_health)
    app.add_url_rule("/favicon.ico", "favicon", favicon)
    # Core API
    app.add_url_rule("/api/generate", "gen", limiter.limit("20 per hour")(gen), methods=["POST"])
    app.add_url_rule("/api/progress", "prog", limiter.exempt(prog))
    app.add_url_rule("/api/download", "download_result", download_result)
    app.add_url_rule("/api/cancel", "cancel_process", cancel_process, methods=["POST"])
    app.add_url_rule("/api/history", "get_history", get_history_route)
    app.add_url_rule("/api/history/<int:history_id>", "delete_history_item", delete_history_item, methods=["DELETE"])
    app.add_url_rule("/api/history/clear", "clear_all_history", clear_all_history, methods=["POST"])
    app.add_url_rule("/api/my-jobs", "get_my_jobs", get_my_jobs)
    app.add_url_rule("/api/job/<job_id>", "get_job_by_id", get_job_by_id)
    app.add_url_rule("/api/config", "conf", conf)
    app.add_url_rule("/api/health", "health_check", health_check)
    app.add_url_rule("/api/estimate-duration", "estimate_duration", limiter.limit("100 per hour")(estimate_duration), methods=["POST"])
