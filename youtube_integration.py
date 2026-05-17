"""
YouTube OAuth integration - auth, upload, scheduling.
"""
import os
import json
import time
import traceback
from flask import request, jsonify
from config import YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REDIRECT_URI, YOUTUBE_SCOPES
from i18n import get_request_lang, tr_api
from database import db_get_job

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

def youtube_disconnect():
    """قطع الاتصال بـ YouTube"""
    session_id = request.json.get('sessionId')
    
    if session_id and session_id in YOUTUBE_TOKENS:
        del YOUTUBE_TOKENS[session_id]
    
    return jsonify({'ok': True})


def register_youtube_routes(app, limiter=None):
    """Register all YouTube routes on the Flask app."""
    app.add_url_rule("/api/youtube/auth-url", "youtube_auth_url", youtube_auth_url)
    app.add_url_rule("/api/youtube/callback", "youtube_callback", youtube_callback)
    app.add_url_rule("/api/youtube/status", "youtube_status", youtube_status)
    app.add_url_rule("/api/youtube/redirect-uri", "youtube_redirect_uri", youtube_redirect_uri)
    app.add_url_rule("/api/youtube/upload", "youtube_upload", youtube_upload, methods=["POST"])
    app.add_url_rule("/api/youtube/disconnect", "youtube_disconnect", youtube_disconnect, methods=["POST"])
