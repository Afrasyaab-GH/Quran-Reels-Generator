"""
Internationalization — API translations, language detection, duration formatting.
"""
from flask import request

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
