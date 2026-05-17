# Quran Reels Generator - Deployment & Usage Guide

## 🌐 HuggingFace Space (Production)

**Live URL**: https://huggingface.co/spaces/Habib-HF/Quran-Reels-Generator

Status: **Building** (Docker build in progress, ~5-10 minutes)

The Space is configured to:
- Auto-build from Docker image every git push
- Run gunicorn production server on port 7860
- Support persistent storage for jobs and cache

---

## 🖥️ Local Development (Windows)

### Quick Start

```powershell
cd D:\Projects\Quran-Reels-Generator
.\run-local.ps1
```

The script will:
1. ✅ Auto-detect Python (Miniconda at `D:\Tools\Miniconda`)
2. ✅ Auto-install ffmpeg if missing (to `D:\Tools\ffmpeg`)
3. ✅ Install all dependencies via pip
4. ✅ Auto-open browser to http://127.0.0.1:7860/UI.html

### Manual Start (if script fails)

```powershell
# Ensure ffmpeg is on PATH
$env:PATH = "D:\Tools\ffmpeg\ffmpeg-8.1.1-full_build\bin;" + $env:PATH

# Run server
python main.py
```

Then open: http://127.0.0.1:7860/UI.html

---

## 📋 Features Implemented

### ✅ Bilingual i18n (Arabic/English)
- **Backend**: `tr_api(key, lang, **kwargs)` returns localized error/info strings
- **Frontend**: `CURRENT_LANG` persisted in localStorage, language toggle reloads config
- **API responses**: `/api/config`, `/api/history`, `/api/estimate-duration`, `/api/batch/*` all return localized surah names, duration formats, status messages

### ✅ FFmpeg Auto-Configuration
- Detects ffmpeg at: `D:\Tools\ffmpeg\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe` (Windows)
- Falls back to system PATH or HF Spaces default location
- Configured for moviepy, pydub, and subprocess calls

### ✅ Python 3.13 Compatibility
- Pillow bumped to `11.2.1` (was `9.5.0` — broke on Python 3.13)
- audioop-lts shim added for pydub support

### ✅ Video Generation
- Audio loading works (ffmpeg configured)
- Background clips now have duration set (fixes moviepy `.loop()` error)
- Tested with multiple reciter modes

### ✅ UI/UX Polish
- Favicon 404 suppressed (returns 204 No Content)
- Language toggle in header with persistent state
- Responsive design for desktop/mobile

---

## 🔧 Configuration

### Environment Variables
- `PORT` — Server port (default: 7860)
- `FLASK_ENV` — Set to `production` for gunicorn, `development` for flask dev server
- `OAUTHLIB_INSECURE_TRANSPORT=1` — Already set for OAuth over HTTP in local/Space

### Database
- **Location**: `./quran_jobs.db` (SQLite)
- **Tables**: `jobs`, `history`, `batch_jobs`, `batch_items`
- Auto-initializes on first run

### Caches
- **Audio**: `./cache_mp3quran/` — Cached full surah MP3 files + timings JSON
- **Videos**: `./temp_workspaces/` — Temporary workspace per job (auto-cleaned)
- **Backgrounds**: `./outputs/` — Final output videos

---

## 🚀 Deployment to HF Space

### Automatic (Post-Commit)
```powershell
git add -A
git commit -m "your message"
git push origin main
```
HF Space will auto-trigger Docker build (note: requires git credentials to be cached)

### Manual Upload (Always Works)
```powershell
python -c "
from huggingface_hub import upload_folder
upload_folder(
    folder_path='.',
    repo_id='Habib-HF/Quran-Reels-Generator',
    repo_type='space',
)
"
```

---

## 📊 Project Structure

```
D:\Projects\Quran-Reels-Generator/
├── main.py                    # Flask backend (2800+ lines)
├── UI.html                    # Single-file frontend (3700+ lines)
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker image (Python 3.9 + ffmpeg + ImageMagick)
├── start.sh                   # Production server script (gunicorn)
├── run-local.ps1              # Local launcher (Windows)
├── fonts/                     # Arabic/English fonts (8 files)
├── cache_mp3quran/            # Cached audio files
├── temp_workspaces/           # Job workspace directories
└── README.md                  # Project docs
```

---

## 🐛 Troubleshooting

### FFmpeg Not Found
```powershell
# Check installation
ffmpeg -version

# If missing, run local launcher which auto-installs:
.\run-local.ps1
```

### Video Generation Fails
- Check server logs for error messages
- Ensure Pexels API key is set (or leave blank for default backgrounds)
- Verify audio URLs are accessible (everyayah.com or mp3quran.net)

### Language Toggle Not Working
- Clear localStorage: Press F12 → Application → Clear Storage
- Reload page

### Browser Shows Blank
- Check browser console (F12) for JavaScript errors
- Verify API responses: Open Network tab and check `/api/config` response

---

## 📝 Next Steps

1. **Test video generation locally** — Try: Surah 1 (Al-Fatiha), Ayahs 1-5
2. **Check HF Space build status** — https://huggingface.co/spaces/Habib-HF/Quran-Reels-Generator/logs
3. **Share the Space link** — Works with other users (no credentials needed)
4. **Optional**: Configure Pexels API key for custom backgrounds

---

## 📞 Support

- **API Docs**: Visit http://127.0.0.1:7860 and check Network tab
- **Logs**: Server terminal shows all request/error logs
- **GitHub Issues**: (Once repo is public)

---

**Last Updated**: May 17, 2026
**Version**: 0.2.4
