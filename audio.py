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
from quran_data import NEW_RECITERS_CONFIG
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
            t = re.sub(r'^بِسْمِ \S+ \S+ \S+\s*', '', t).strip()
        return t
    except: return "Text Error"


def get_en_text(surah, ayah):
    try: return requests.get(f'http://api.alquran.cloud/v1/ayah/{surah}:{ayah}/en.sahih').json()['data']['text']
    except: return ""
