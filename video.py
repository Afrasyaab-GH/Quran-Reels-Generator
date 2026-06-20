"""
Video pipeline — build_video_task, text clips, backgrounds, visual effects.
This is the core rendering engine extracted from main.py lines 1223-2155.
"""
import os
import re
import gc
import math
import json
import time
import uuid
import shutil
import random
import traceback
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance
from deep_translator import GoogleTranslator
from moviepy.editor import (
    ImageClip, VideoFileClip, AudioFileClip,
    CompositeVideoClip, ColorClip, concatenate_videoclips
)
from moviepy.audio.AudioClip import concatenate_audioclips

from config import (
    EXEC_DIR, VISION_DIR, LOCAL_BGS_DIR, OUTPUTS_DIR,
    PEXELS_API_KEYS, FONT_PATH_ARABIC, FONT_PATH_ENGLISH, FONT_PATH_BRACKETS,
    get_font_path, get_font_path_en,
)

try:
    import arabic_reshaper
    from bidi.algorithm import get_display as _bidi_display
    _reshaper_config = {
        'delete_harakat': False,
        'support_harakat': True,
        'delete_tatweel': False,
    }
    _arabic_reshaper_instance = arabic_reshaper.ArabicReshaper(configuration=_reshaper_config)
    def _reshape_arabic(s: str) -> str:
        """Reshape + apply RTL bidi so PIL renders Arabic correctly."""
        return _bidi_display(_arabic_reshaper_instance.reshape(s))
except ImportError:
    _arabic_reshaper_instance = None
    _bidi_display = lambda x: x
    def _reshape_arabic(s: str) -> str:  # fallback: no-op
        return s
from quran_data import (
    VERSE_COUNTS, SAFE_TOPICS, RECITER_ID_TO_NAME, QURANCOM_RECITERS_MAP,
    choose_background_query, get_surah_name,
)
from utils import _as_bool, to_arabic_numeral, split_into_chunks, build_audio_filter_chain
from jobs import (
    get_job, check_stop, update_job_status, update_job_metadata,
    ScopedQuranLogger, JOBS, JOBS_LOCK,
)
from audio import download_audio, get_text, get_translation_text, smart_download, get_cached_font
from database import db_update_job, db_get_job, db_add_history

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
        main_text = _reshape_arabic(text[:bracket_match.start()].strip())
        bracket_text = _reshape_arabic('﴾' + bracket_match.group(1)[1:-1] + '﴿')
    else:
        main_text = _reshape_arabic(text)
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


def get_word_timings(surah, ayah, reciter_name, duration, full_ar_text):
    """
    Get word-by-word timing for the ayah.
    Returns a list of (word_start_relative, word_end_relative) relative to the start of the ayah audio in seconds.
    """
    # 1. Try Quran.com cached timings
    from audio import load_quran_com_segments
    q_data = load_quran_com_segments(surah, reciter_name)
    if q_data and str(ayah) in q_data['verses']:
        verse_timing = q_data['verses'][str(ayah)]
        ayah_start_ms = verse_timing['start']
        segments = verse_timing.get('segments', [])
        
        # segments is a list of [word_idx, start_ms, end_ms]
        if segments:
            timings = []
            for item in segments:
                # Relative time in seconds
                w_start = max(0.0, (item[1] - ayah_start_ms) / 1000.0)
                w_end = max(0.0, (item[2] - ayah_start_ms) / 1000.0)
                timings.append((w_start, w_end))
            return timings
            
    # 2. Fallback: Proportional character-length estimation
    words = full_ar_text.split()
    if not words:
        return []
        
    lengths = [len(w) for w in words]
    total_len = sum(lengths)
    if total_len == 0:
        return [(0.0, duration)] * len(words)
        
    timings = []
    current_time = 0.0
    for length in lengths:
        word_dur = (length / total_len) * duration
        timings.append((current_time, current_time + word_dur))
        current_time += word_dur
        
    return timings


def create_word_highlight_text_clip(text, duration, target_w, scale_factor=1.0, glow=False, style=None, font_path=None, word_timings=None):
    if style is None: style = {}
    if word_timings is None: word_timings = []
    
    color = style.get('arColor', '#ffffff')
    highlight_color = style.get('arHighlightColor', '#ffd700')
    size_mult = float(style.get('arSize', '1.0'))
    stroke_c = style.get('arOutC', '#000000')
    stroke_w = int(style.get('arOutW', '4'))
    has_shadow = style.get('arShadow', True)
    shadow_c = style.get('arShadowC', '#000000')
    
    # Use selected or default font
    if font_path is None:
        font_path = FONT_PATH_ARABIC
        
    font_boost = 1.15 if 'Arabic.otf' in font_path else 1.0
    final_fs = int(55 * scale_factor * size_mult * font_boost)
    font = get_cached_font(font_path, final_fs)
    font_brackets = get_cached_font(FONT_PATH_BRACKETS, final_fs)
    
    import re
    bracket_match = re.search(r'([﴾﴿]+.*[﴾﴿]+)$', text)
    if bracket_match:
        main_text = text[:bracket_match.start()].strip()
        bracket_text = '﴾' + bracket_match.group(1)[1:-1] + '﴿'
    else:
        main_text = text
        bracket_text = ""
        
    # Shape and BiDi for bracket text
    if bracket_text:
        bracket_display = _reshape_arabic(bracket_text)
    else:
        bracket_display = ""
        
    # Split text into words
    words = main_text.split()
    if not words:
        return create_text_clip(text, duration, target_w, scale_factor, glow, style, font_path)
        
    # Shape the entire main text first to preserve Uthmanic ligatures, then apply RTL bidi
    if _arabic_reshaper_instance:
        reshaped_main = _arabic_reshaper_instance.reshape(main_text)
    else:
        reshaped_main = main_text
    bidi_main = _bidi_display(reshaped_main)
    bidi_words = bidi_main.split()
    
    if len(bidi_words) != len(words):
        return create_text_clip(text, duration, target_w, scale_factor, glow, style, font_path)
        
    # Measure dimensions
    temp_img = Image.new('RGBA', (target_w, int(180 * scale_factor * size_mult)), (0,0,0,0))
    temp_draw = ImageDraw.Draw(temp_img)
    
    if bracket_display:
        bracket_w = temp_draw.textbbox((0, 0), bracket_display + " ", font=font_brackets, stroke_width=stroke_w)[2]
    else:
        bracket_w = 0
        
    total_main_w = temp_draw.textbbox((0, 0), bidi_main, font=font, stroke_width=stroke_w)[2]
    total_w = total_main_w + bracket_w
    
    x_start = (target_w - total_w) // 2
    curr_y = 20
    
    # Pre-render frames for each highlight state
    highlight_frames = {}
    
    highlight_frames_rgb = {}
    highlight_frames_mask = {}
    
    def render_state(active_orig_idx):
        img = Image.new('RGBA', (target_w, int(180 * scale_factor * size_mult)), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        
        # 1. Draw shadow
        if has_shadow:
            for offset in range(6, 0, -1):
                opacity = int(80 - offset * 10)
                shadow_color = (*[int(shadow_c.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)], opacity)
                
                if bracket_display:
                    draw.text((x_start+offset, curr_y+offset), bracket_display + " ", font=font_brackets, fill=shadow_color)
                    
                x_offset = x_start + bracket_w
                space_w = draw.textbbox((0, 0), " ", font=font)[2]
                for word in bidi_words:
                    word_w = draw.textbbox((0, 0), word, font=font)[2]
                    draw.text((x_offset+offset, curr_y+offset), word, font=font, fill=shadow_color)
                    x_offset += word_w + space_w
                    
            if bracket_display:
                draw.text((x_start+3, curr_y+3), bracket_display + " ", font=font_brackets, fill=(0, 0, 0, 180))
            x_offset = x_start + bracket_w
            space_w = draw.textbbox((0, 0), " ", font=font)[2]
            for word in bidi_words:
                word_w = draw.textbbox((0, 0), word, font=font)[2]
                draw.text((x_offset+3, curr_y+3), word, font=font, fill=(0, 0, 0, 180))
                x_offset += word_w + space_w
                
        # 2. Draw Glow
        if glow:
            if bracket_display:
                draw.text((x_start, curr_y), bracket_display + " ", font=font_brackets, fill=(255,255,255,40), stroke_width=stroke_w+4, stroke_fill=(255,255,255,20))
            x_offset = x_start + bracket_w
            space_w = draw.textbbox((0, 0), " ", font=font)[2]
            for bidi_idx, word in enumerate(bidi_words):
                word_w = draw.textbbox((0, 0), word, font=font)[2]
                orig_idx = len(words) - 1 - bidi_idx
                is_active = (orig_idx == active_orig_idx)
                glow_color = (255,255,255,40)
                glow_stroke = (255,255,255,20)
                draw.text((x_offset, curr_y), word, font=font, fill=glow_color, stroke_width=stroke_w+4, stroke_fill=glow_stroke)
                x_offset += word_w + space_w
                
        # 3. Draw Actual Text
        if bracket_display:
            draw.text((x_start, curr_y), bracket_display + " ", font=font_brackets, fill=color, stroke_width=stroke_w, stroke_fill=stroke_c)
            
        x_offset = x_start + bracket_w
        space_w = draw.textbbox((0, 0), " ", font=font)[2]
        for bidi_idx, word in enumerate(bidi_words):
            word_w = draw.textbbox((0, 0), word, font=font)[2]
            orig_idx = len(words) - 1 - bidi_idx
            is_active = (orig_idx == active_orig_idx)
            current_color = highlight_color if is_active else color
            draw.text((x_offset, curr_y), word, font=font, fill=current_color, stroke_width=stroke_w, stroke_fill=stroke_c)
            x_offset += word_w + space_w
            
        arr = np.array(img)
        rgb_arr = arr[:, :, :3]
        mask_arr = arr[:, :, 3].astype(np.float32) / 255.0
        return rgb_arr, mask_arr
        
    rgb, mask = render_state(None)
    highlight_frames_rgb[None] = rgb
    highlight_frames_mask[None] = mask
    for k in range(len(words)):
        rgb, mask = render_state(k)
        highlight_frames_rgb[k] = rgb
        highlight_frames_mask[k] = mask
        
    def make_frame(t):
        t_ms = t * 1000.0
        active_idx = None
        for k, (w_start, w_end) in enumerate(word_timings):
            if w_start <= t_ms <= w_end:
                active_idx = k
                break
        return highlight_frames_rgb.get(active_idx, highlight_frames_rgb[None])

    def make_mask_frame(t):
        t_ms = t * 1000.0
        active_idx = None
        for k, (w_start, w_end) in enumerate(word_timings):
            if w_start <= t_ms <= w_end:
                active_idx = k
                break
        return highlight_frames_mask.get(active_idx, highlight_frames_mask[None])
        
    from moviepy.editor import VideoClip
    clip = VideoClip(make_frame, duration=duration)
    mask_clip = VideoClip(make_mask_frame, ismask=True, duration=duration)
    clip = clip.set_mask(mask_clip)
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
def build_video_task(job_id, user_pexels_key, reciter_id, surah, start, end, quality, bg_query, fps, dynamic_bg, use_glow, use_vignette, aspect_ratio, style, font_name='Arabic', font_name_en='English', bg_effect='enhance', scene_pack='nature_calm', bg_crossfade_sec=0.5, adaptive_text_contrast=False, safe_area_guides=False, safe_area_padding_px=0, audio_profile='studio', audio_denoise=False, audio_deess=False, translation_lang='en', word_highlight=False):
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
                ap = download_audio(reciter_id, surah, ayah, i, workspace, job_id, word_highlight=word_highlight)
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
            full_en_text = get_translation_text(surah, ayah, translation_lang)
            
            # التحقق من وجود نص عربي
            if not full_ar_text or full_ar_text == "Text Error" or len(full_ar_text.strip()) == 0:
                print(f"[ERROR] Failed to get Arabic text for ayah {ayah}")
                continue  # Skip this ayah
            
            # Get word timing segments for the ayah
            word_timings = []
            if word_highlight:
                word_timings = get_word_timings(surah, ayah, reciter_id, full_audioclip.duration, full_ar_text)

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

                # Compute word timings relative to the start of this chunk in milliseconds
                chunk_words = ar_chunk.split()
                chunk_word_timings = []
                if word_highlight and word_timings:
                    start_word_idx = chunk_idx * 5
                    for w_idx in range(len(chunk_words)):
                        abs_idx = start_word_idx + w_idx
                        if abs_idx < len(word_timings):
                            w_t = word_timings[abs_idx]
                            r_start = max(0.0, (w_t[0] - current_audio_time) * 1000.0)
                            r_end = max(0.0, (w_t[1] - current_audio_time) * 1000.0)
                            chunk_word_timings.append((r_start, r_end))

                # د. إنشاء الكليبات البصرية (نستخدم actual_duration بدل chunk_duration)
                if word_highlight:
                    ac = create_word_highlight_text_clip(
                        display_ar, actual_duration, target_w, scale, use_glow,
                        style=chunk_style, font_path=font_path, word_timings=chunk_word_timings
                    )
                else:
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
        from database import _now_iso as _db_now
        db_update_job(job_id, output_path=final_output_path, status='complete', percent=100, completed_at=_db_now())
        
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
