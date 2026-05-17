"""
Quran data: verse counts, surah names, reciters configuration, validation.
"""
import os
import random
from config import EXEC_DIR

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
    from i18n import tr_api
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
OLD_RECITERS_MAP = {}

# 🎯 MP3Quran IDs للقراء (للتوقيتات الدقيقة) — auto-derived from NEW_RECITERS_CONFIG
MP3QURAN_IDS = {name: rid for name, (rid, _url) in NEW_RECITERS_CONFIG.items()}

# خريطة عكسية لتحويل الـ ID للاسم العربي
RECITER_ID_TO_NAME = {v: k for k, v in OLD_RECITERS_MAP.items()}
# إضافة أسماء القراء الجدد (الاسم العربي = الاسم العربي)
for name in NEW_RECITERS_CONFIG.keys():
    RECITER_ID_TO_NAME[name] = name

RECITERS_MAP = {**{k: k for k in NEW_RECITERS_CONFIG.keys()}, **OLD_RECITERS_MAP}

# ✅ خريطة من الـ ID (اللي في OLD_RECITERS_MAP) للـ mp3quran ID (لو موجود)
OLD_RECITER_TO_MP3QURAN_ID = {
    'Yasser_Ad-Dussary_128kbps': None,
    'Maher_AlMuaiqly_64kbps': None,
    'Nasser_Alqatami_128kbps': None,
    'Minshawy_Murattal_128kbps': None,
}

# 📖 نصوص الآيات للحساب الذكي (مختصر - أهم السور)
AYAH_TEXTS_CACHE = {}

def load_ayah_texts():
    """تحميل نصوص الآيات من ملف أو API"""
    global AYAH_TEXTS_CACHE
    if AYAH_TEXTS_CACHE:
        return AYAH_TEXTS_CACHE
    
    # محاولة التحميل من ملف محلي
    import json
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
        'Alafasy_64kbps': 0.12,
        'Abu_Bakr_Ash-Shaatree_128kbps': 0.10,
        'Yasser_Ad-Dussary_128kbps': 0.10,
        'Abdurrahmaan_As-Sudais_64kbps': 0.09,
        'Maher_AlMuaiqly_64kbps': 0.10,
        'Saood_ash-Shuraym_64kbps': 0.10,
        'Nasser_Alqatami_128kbps': 0.11,
        'Minshawy_Murattal_128kbps': 0.11,
        'احمد النفيس': 0.10,
        'وديع اليماني': 0.11,
        'بندر بليلة': 0.10,
        'ادريس أبكر': 0.09,
        'منصور السالمي': 0.10,
        'رعد الكردي': 0.10,
        'أحمد العجمي': 0.09,
        'محمود خليل الحصري': 0.11,
    }
    
    BASE_TIME = 1.5
    time_per_char = READER_SPEEDS.get(reciter_key, 0.10)
    ayah_length = estimate_ayah_length(surah, ayah)
    duration = BASE_TIME + (ayah_length * time_per_char)
    return max(duration, 2.0)

def estimate_ayah_length(surah, ayah):
    """
    تقدير طول الآية بناءً على إحصائيات السورة
    """
    SURAH_AVG_LENGTHS = {
        1: 20, 2: 150, 3: 120, 36: 80, 55: 40,
        67: 35, 78: 45, 112: 15, 113: 20, 114: 20,
    }
    
    avg_length = SURAH_AVG_LENGTHS.get(surah, 50)
    verse_count = VERSE_COUNTS.get(surah, 100)
    position_ratio = ayah / verse_count
    
    if surah in [2, 3, 4]:
        if position_ratio < 0.3:
            avg_length *= 1.3
        elif position_ratio > 0.8:
            avg_length *= 0.8
    
    return int(avg_length)
