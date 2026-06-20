"""
Audio processing — download, trim, mp3quran integration, silence detection.
"""
import os
import re
import json
import requests
from functools import lru_cache
from pydub import AudioSegment
from PIL import ImageFont
from config import EXEC_DIR
from quran_data import NEW_RECITERS_CONFIG, QURANCOM_RECITERS_MAP
from jobs import check_stop


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


def detect_silence(sound, thresh):
    t = 0
    while t < len(sound) and sound[t:t+10].dBFS < thresh: t += 10
    return t


def detect_leading_silence(sound, silence_threshold=-50.0, chunk_size=10):
    trim_ms = 0
    assert chunk_size > 0
    while trim_ms < len(sound) and sound[trim_ms:trim_ms+chunk_size].dBFS < silence_threshold:
        trim_ms += chunk_size
    return trim_ms


@lru_cache(maxsize=10)
def get_cached_font(font_path, size):
    try: return ImageFont.truetype(font_path, size)
    except: return ImageFont.load_default()


def load_quran_com_segments(surah, reciter_name):
    quran_com_id = QURANCOM_RECITERS_MAP.get(reciter_name)
    if not quran_com_id:
        return None
        
    cache_dir = os.path.join(EXEC_DIR, "cache_qurancom", str(quran_com_id))
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"{surah:03d}.json")
    
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARNING] Failed to load cached Quran.com timings from {cache_path}: {e}")
            
    # If not cached, fetch from Quran.com API
    try:
        url = f"https://api.quran.com/api/v4/chapter_recitations/{quran_com_id}/{surah}?segments=true"
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            timestamps = data.get('audio_file', {}).get('timestamps', [])
            audio_url = data.get('audio_file', {}).get('audio_url')
            
            # Map into a simplified dictionary
            result = {
                'audio_url': audio_url,
                'verses': {}
            }
            for item in timestamps:
                verse_key = item.get('verse_key')  # e.g. "1:1"
                if ':' in verse_key:
                    ayah_num = verse_key.split(':')[1]
                    result['verses'][ayah_num] = {
                        'start': item.get('timestamp_from'),
                        'end': item.get('timestamp_to'),
                        'segments': item.get('segments', []) # list of [word_index, start_ms, end_ms]
                    }
                
            # Write to cache
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False)
            return result
    except Exception as e:
        print(f"[ERROR] Failed to fetch Quran.com timings for surah {surah}, reciter {reciter_name}: {e}")
        
    return None


def download_quran_com_audio(quran_com_id, surah, audio_url, job_id):
    cache_dir = os.path.join(EXEC_DIR, "cache_qurancom", str(quran_com_id))
    os.makedirs(cache_dir, exist_ok=True)
    full_audio_path = os.path.join(cache_dir, f"{surah:03d}.mp3")
    
    if not os.path.exists(full_audio_path) or os.path.getsize(full_audio_path) == 0:
        smart_download(audio_url, full_audio_path, job_id)
        
    return full_audio_path


def process_quran_com_audio(reciter_name, surah, ayah, idx, workspace_dir, job_id):
    quran_com_id = QURANCOM_RECITERS_MAP.get(reciter_name)
    q_data = load_quran_com_segments(surah, reciter_name)
    if not q_data or str(ayah) not in q_data['verses']:
        return None
        
    audio_url = q_data['audio_url']
    if not audio_url:
        return None
        
    full_audio_path = download_quran_com_audio(quran_com_id, surah, audio_url, job_id)
    
    verse_timing = q_data['verses'][str(ayah)]
    start_ms = verse_timing['start']
    end_ms = verse_timing['end']
    
    check_stop(job_id)
    # Load and trim
    seg = AudioSegment.from_file(full_audio_path)[start_ms:end_ms]
    out = os.path.join(workspace_dir, f'part{idx}.wav')
    seg.export(out, format="wav")
    return out


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


def download_audio(reciter_key, surah, ayah, idx, workspace_dir, job_id, word_highlight=False):
    if word_highlight and reciter_key in QURANCOM_RECITERS_MAP:
        out = process_quran_com_audio(reciter_key, surah, ayah, idx, workspace_dir, job_id)
        if out:
            return out

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
            t = re.sub(r'^بِسْمِ \S+ \S+ \S+\s*', '', t).strip()
        return t
    except: return "Text Error"


TRANSLATION_EDITIONS = {
    'en': 'en.sahih',
    'ur': 'ur.jalandhry',
    'fr': 'fr.hamidullah',
    'es': 'es.cortes',
    'id': 'id.indonesian'
}


def get_translation_text(surah, ayah, translation_lang='en'):
    edition = TRANSLATION_EDITIONS.get(translation_lang, 'en.sahih')
    try:
        return requests.get(f'http://api.alquran.cloud/v1/ayah/{surah}:{ayah}/{edition}').json()['data']['text']
    except Exception as e:
        print(f"[ERROR] Failed to fetch translation for {surah}:{ayah} ({edition}): {e}")
        return ""

