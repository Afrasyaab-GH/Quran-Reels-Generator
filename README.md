---
title: Quran Reels Generator
emoji: ☪️
colorFrom: green
colorTo: emerald
sdk: docker
app_port: 7860
pinned: false
short_description: "Automated AI tool to generate beautiful Quranic Reels & Shorts"
tags:
  - quran
  - islam
  - video-generator
  - reels
  - tiktok
  - youtube-shorts
  - ffmpeg
  - python
  - automation
---

# 📖 Quran Reels Generator

[![Live App](https://img.shields.io/badge/Live_App-HuggingFace_Space-blue?style=for-the-badge&logo=huggingface)](https://huggingface.co/spaces/Habib-HF/Quran-Reels-Generator) [![Latest Release](https://img.shields.io/github/v/release/Afrasyaab-GH/Quran-Reels-Generator?include_prereleases&style=for-the-badge&logo=github)](https://github.com/Afrasyaab-GH/Quran-Reels-Generator/releases/latest) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

**Quran Reels Generator** is a powerful, open-source automation tool designed to help creators generate stunning, high-retention short-form videos (Reels, TikToks, Shorts) of Quranic recitations in seconds. 

Whether you're an Islamic content creator, a page admin, or just looking to share the message, this tool automates the entire video creation pipeline: fetching audio, syncing Arabic text with English translations, applying beautiful background visuals, and exporting vertical videos ready for social media.

> 🚀 **Available everywhere:** **Windows Desktop App** · **Self-Hosted Docker** · **Hugging Face Web Space**

---

## 📥 Download for Windows

| Build | Size | When to use |
|---|---|---|
| **[QuranReels-Setup-x.y.z.exe](https://github.com/Afrasyaab-GH/Quran-Reels-Generator/releases/latest)** | ~127 MB | Per-user installer (no admin needed). Adds Start Menu shortcut. |
| **[QuranReels-Portable-Windows.zip](https://github.com/Afrasyaab-GH/Quran-Reels-Generator/releases/latest)** | ~184 MB | Unzip and run `QuranReels.exe` — no install. |

**Requirements:** Windows 10/11 (64-bit) · Microsoft Edge WebView2 runtime (the app will prompt to install it if missing — ~2 MB).

FFmpeg is bundled. No Python install required.

---

## 🌐 Try the web demo

Run on Hugging Face Spaces: **[Habib-HF/Quran-Reels-Generator](https://huggingface.co/spaces/Habib-HF/Quran-Reels-Generator)**

---

## ✨ Features

- Choose any surah + ayah range
- Multiple reciters (Mishary, Husary, Al-Afasy, Sudais, Shuraim, and more)
- English translation overlay (Sahih International, Pickthall, Yusuf Ali, etc.)
- Automatic background video (Pexels) or procedural emerald/teal gradient fallback
- Optional Pexels API key for higher-quality backgrounds
- Vertical 9:16 output (Reels / Shorts / TikTok ready)
- Direct YouTube upload (OAuth)
- Arabic and English UI

---

## 🛠️ Run from source

### Prerequisites

- Python 3.10+ (3.12 recommended)
- FFmpeg in PATH
- ImageMagick (optional, for some text effects)

```powershell
# Windows
winget install Gyan.FFmpeg
winget install ImageMagick.ImageMagick
```

### Quick start (Windows / PowerShell)

```powershell
git clone https://github.com/Afrasyaab-GH/Quran-Reels-Generator.git
cd Quran-Reels-Generator
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Open <http://127.0.0.1:7860>.

Or use the helper:

```powershell
.\run-local.ps1            # default
.\run-local.ps1 -Port 7863 # custom port
.\run-local.ps1 -NoBrowser # don't auto-open
```

### Linux / macOS

```bash
git clone https://github.com/Afrasyaab-GH/Quran-Reels-Generator.git
cd Quran-Reels-Generator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

---

## 🐳 Run with Docker

```bash
docker build -t quran-reels .
docker run --rm -p 7860:7860 quran-reels
```

Or with Compose:

```bash
docker compose -f docker-compose.standalone.yml up -d --build
```

---

## 🔑 Optional environment variables

| Variable | Purpose |
|---|---|
| `PEXELS_API_KEYS` | Comma-separated Pexels API keys for background videos |
| `YOUTUBE_CLIENT_ID` | Google OAuth client ID for direct YouTube upload |
| `YOUTUBE_CLIENT_SECRET` | OAuth client secret |
| `YOUTUBE_REDIRECT_URI` | OAuth callback URL |
| `QURAN_REELS_DATA_DIR` | Override user-data dir (defaults to `%APPDATA%\QuranReels` on Win) |

---

## 🏗️ Build the Windows installer yourself

```powershell
.\desktop\build_windows.ps1                  # full build: bundle + installer
.\desktop\build_windows.ps1 -SkipInstaller   # bundle only
.\desktop\build_windows.ps1 -Clean           # wipe build/dist first
```

Outputs to `dist\QuranReels\QuranReels.exe` and `dist\QuranReels-Setup-x.y.z.exe`.

Requires:

- Python 3.12 with deps from `desktop/requirements-desktop.txt`
- [NSIS](https://nsis.sourceforge.io/) on PATH (for the installer)
- FFmpeg binaries copied to `desktop/ffmpeg/` (auto-detected from `D:\Tools\ffmpeg\` if present)

See [`desktop/BUILD.md`](desktop/BUILD.md) for details, cross-platform builds, and macOS/Linux scripts.

---

## 🤖 Continuous releases

Pushing a `v*` tag to GitHub triggers [`.github/workflows/build-desktop.yml`](.github/workflows/build-desktop.yml), which:

1. Builds on a `windows-latest` runner
2. Bundles FFmpeg + Python + WebView2-based UI
3. Compiles the NSIS installer
4. Publishes a GitHub Release with both installer and portable zip

```powershell
git tag v0.2.0
git push origin v0.2.0
# Release appears at /releases/tag/v0.2.0 in ~8-10 min
```

---

## 🧱 Tech stack

- **Backend:** Flask · MoviePy · FFmpeg · pydub · Pillow
- **Desktop:** pywebview · PyInstaller · NSIS · Edge WebView2
- **Frontend:** vanilla HTML/CSS/JS (`UI.html`)
- **CI:** GitHub Actions on `windows-latest`

---

## 📁 Project layout

```
Quran-Reels-Generator/
├── main.py                       # Flask app + video pipeline
├── UI.html                       # Single-page frontend
├── requirements.txt              # Web/runtime deps
├── Dockerfile                    # HF Space + standalone container
├── start.sh                      # Container entrypoint
├── run-local.ps1                 # Windows dev launcher
├── fonts/                        # Arabic + Latin fonts
├── desktop/                      # Windows desktop build pipeline
│   ├── launcher.py               # pywebview launcher + splash + WebView2 check
│   ├── QuranReels.spec           # PyInstaller spec
│   ├── installer_windows.nsi     # NSIS installer script
│   ├── build_windows.ps1         # Local build script
│   └── BUILD.md                  # Detailed build docs
└── .github/workflows/
    └── build-desktop.yml         # CI: tag → release
```

---

## 🤝 Contributing

Issues and PRs welcome. For desktop-related changes, please verify the build still succeeds with `.\desktop\build_windows.ps1 -SkipInstaller -Clean` before opening a PR.

---

## 📜 License

[MIT](LICENSE) — see [LICENSE](LICENSE) for full text.

The Holy Quran text and recitations are in the public domain. Translations remain the copyright of their respective publishers and are included under fair-use principles for non-commercial use.

---

## 🙏 Acknowledgements

- [mp3quran.net](https://mp3quran.net/) — reciter audio
- [AlQuran.cloud](https://alquran.cloud/) — Quran text API
- [Pexels](https://pexels.com/) — background videos
- [pywebview](https://pywebview.flowrl.com/) — desktop wrapper
- [PyInstaller](https://pyinstaller.org/) and [NSIS](https://nsis.sourceforge.io/) — packaging
