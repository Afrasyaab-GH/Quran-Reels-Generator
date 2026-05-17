"""
Batch export system - multiple batches in parallel.
"""
import os
import json
import time
import uuid
import threading
import traceback
from flask import request, jsonify
from config import EXEC_DIR, PEXELS_API_KEYS
from i18n import get_request_lang, tr_api
from database import (
    db_create_batch, db_update_batch, db_get_batch,
    db_add_batch_item, db_update_batch_item, db_get_batch_items,
    db_get_pending_batches, db_get_job, db_update_job,
)
from jobs import create_job, get_job, JOBS, JOBS_LOCK
from quran_data import (
    choose_background_query, get_surah_name, RECITER_ID_TO_NAME,
)
import sqlite3
from config import DB_PATH

# Lazy-load the heavy video pipeline to keep app startup fast.
_build_video_task_cached = None


def _get_build_video_task():
    global _build_video_task_cached
    if _build_video_task_cached is None:
        from video import build_video_task as _build_video_task  # local import by design
        _build_video_task_cached = _build_video_task
    return _build_video_task_cached

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

                _get_build_video_task()(
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


def register_batch_routes(app, limiter=None):
    """Register all batch routes on the Flask app."""
    if limiter:
        app.add_url_rule("/api/batch/create", "create_batch", limiter.limit("5 per hour")(create_batch), methods=["POST"])
    else:
        app.add_url_rule("/api/batch/create", "create_batch", create_batch, methods=["POST"])
    app.add_url_rule("/api/batch/status", "get_batch_status", get_batch_status)
    app.add_url_rule("/api/batch/list", "list_batches", list_batches)
    app.add_url_rule("/api/batch/cancel", "cancel_batch", cancel_batch, methods=["POST"])
