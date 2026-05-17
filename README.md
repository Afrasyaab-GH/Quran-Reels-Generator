---
title: Quran Reels Generator
emoji: 📖
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Quran Reels Generator

Open-source Flask app to generate short Quran videos (Reels/Shorts/TikTok) with Arabic text, English translation overlay, and configurable visual styles.

## New in this workspace

- Full app source is available at project root (not only Space wrapper files).
- Local app run flow is documented for Windows.
- UI now includes Arabic/English interface toggle from the header button.

## Requirements

- Python 3.9+ (3.10+ recommended)
- FFmpeg installed and available in PATH
- ImageMagick installed

### Windows quick install (winget)

```powershell
winget install Gyan.FFmpeg
winget install ImageMagick.ImageMagick
```

## Run locally (Windows / PowerShell)

```powershell
cd D:\Projects\Quran-Reels-Generator
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

Open:

- http://127.0.0.1:7860

Or use the helper script:

```powershell
cd D:\Projects\Quran-Reels-Generator
.\run-local.ps1
```

## Run with Docker (Standalone App)

```powershell
cd D:\Projects\Quran-Reels-Generator
docker build -t quran-reels-local .
docker run --rm -p 7860:7860 quran-reels-local
```

Open:

- http://127.0.0.1:7860

Or with Docker Compose:

```powershell
cd D:\Projects\Quran-Reels-Generator
docker compose -f docker-compose.standalone.yml up -d --build
```

Stop:

```powershell
docker compose -f docker-compose.standalone.yml down
```

## Deploy as Hugging Face Space

This repository is already configured for Hugging Face Docker Spaces:

- Space metadata is in this `README.md` frontmatter.
- Container startup uses `start.sh` and respects `PORT`.
- Main image definition is `Dockerfile`.

For YouTube publishing in HF, set these Space secrets:

- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REDIRECT_URI` (your Space URL callback)

## Deploy as Separate App (non-HF)

Use either direct Docker or Compose on any VPS/cloud host.

Recommended file for server deployment:

- `docker-compose.standalone.yml`

Optional environment variables:

- `PEXELS_API_KEYS`
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REDIRECT_URI`

## Notes

- Fonts are loaded from the `fonts/` directory.
- Optional Pexels API key can be entered in settings for better background results.
- The app can work without a Pexels key using defaults/fallback logic.

## Tech stack

- Backend: Flask
- Processing: MoviePy + FFmpeg
- Audio: pydub
- Frontend: plain HTML/CSS/JS (`UI.html`)
