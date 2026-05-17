"""
Shared utility functions used across multiple modules.
"""


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


def to_arabic_numeral(num):
    """تحويل الأرقام الإنجليزية لعربية"""
    arabic_digits = '٠١٢٣٤٥٦٧٨٩'
    return ''.join(arabic_digits[int(d)] for d in str(num))


# 🆕 دالة تقطيع النصوص للريلز (5 كلمات كحد أقصى للسطر)
def split_into_chunks(text, words_per_chunk=5):
    words = text.split()
    if not words: return []
    return [" ".join(words[i:i + words_per_chunk]) for i in range(0, len(words), words_per_chunk)]


def build_audio_filter_chain(profile='studio', use_denoise=False, use_deess=False):
    from config import AUDIO_FILTER_PROFILES, STUDIO_DRY_FILTER
    base = AUDIO_FILTER_PROFILES.get(str(profile or 'studio').lower(), STUDIO_DRY_FILTER)
    filters = [base]
    if _as_bool(use_denoise):
        filters.insert(0, "afftdn=nf=-25")
    if _as_bool(use_deess):
        filters.append("deesser=i=0.45:m=0.5:f=0.5:s=o")
    return ", ".join(filters)
