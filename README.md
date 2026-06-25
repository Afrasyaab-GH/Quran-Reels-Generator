---
title: Quran Reels Generator
emoji: 🕌
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# 📖 Quran Reels Generator

[![Live Space](https://img.shields.io/badge/Live_Space-HuggingFace_Space-blue?style=for-the-badge&logo=huggingface)](https://huggingface.co/spaces/Habib-HF/Quran-Reels-Generator) 
[![GitHub Repository](https://img.shields.io/badge/GitHub-Repository-black?style=for-the-badge&logo=github)](https://github.com/Afrasyaab-GH/Quran-Reels-Generator)
[![Latest Release](https://img.shields.io/github/v/release/Afrasyaab-GH/Quran-Reels-Generator?include_prereleases&style=for-the-badge&logo=github)](https://github.com/Afrasyaab-GH/Quran-Reels-Generator/releases/latest) 
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

**Quran Reels Generator** is a powerful, open-source automation platform designed to help content creators, da'wah pages, and developers instantly generate stunning, high-retention short-form videos (Reels, TikToks, Shorts) of Quranic recitations.

With a fully automated media pipeline, the app syncs Arabic Quranic text, fetches high-quality background videos, applies audio enhancements, overlays translations, and compiles high-definition vertical videos ready for social media publishing.

> 🚀 **Deploy & Run Anywhere:** **Windows Desktop App (No Install)** · **Self-Hosted Docker** · **Hugging Face Web Space**
>
> 🌐 **Live Web Application:** [https://huggingface.co/spaces/Habib-HF/Quran-Reels-Generator](https://huggingface.co/spaces/Habib-HF/Quran-Reels-Generator)
>
> 💻 **GitHub Repository:** [https://github.com/Afrasyaab-GH/Quran-Reels-Generator](https://github.com/Afrasyaab-GH/Quran-Reels-Generator)

---

## 📥 Download for Windows

| Build | Size | When to use |
|---|---|---|
| **[QuranReels-Setup-x.y.z.exe](https://github.com/Afrasyaab-GH/Quran-Reels-Generator/releases/latest)** | ~127 MB | Per-user installer (no admin needed). Adds Start Menu shortcut. |
| **[QuranReels-Portable-Windows.zip](https://github.com/Afrasyaab-GH/Quran-Reels-Generator/releases/latest)** | ~184 MB | Unzip and run `QuranReels.exe` — no install. |

**Requirements:** Windows 10/11 (64-bit) · Microsoft Edge WebView2 runtime (the app will prompt to install it if missing — ~2 MB).

*FFmpeg is bundled. No Python installation required.*

---

## 🌐 Try the Web App

Run on Hugging Face Spaces: **[Habib-HF/Quran-Reels-Generator](https://huggingface.co/spaces/Habib-HF/Quran-Reels-Generator)**

---

## ✨ Key Features & Capabilities

*   **Custom Verse Ranges:** Select any Surah and Ayah range to render.
*   **Word-by-Word Highlight Sync:** Active Arabic words highlight in sync with the recitation audio (utilizing Quran.com APIs and smart fallback proportional timing).
*   **Multilingual Translations:** Choose translation overlays in **English (Sahih International), Urdu (Jalandhry), French (Hamidullah), Spanish (Cortes), and Indonesian (Kemenag)**.
*   **Interactive Style Presets:** Customize fonts, sizing, colors, outline widths, and shadows. Save custom styles as presets or choose from built-in themes (Default, Emerald, Royal Gold, Cyber Neon).
*   **Multiple Reciters:** Supports 15+ top reciters (Mishary Al-Afasy, Al-Sudais, Al-Shuraim, Abu Bakr Al-Shatri, Maher Al-Muaiqly, Mansour Al-Salimi, and more).
*   **Advanced Audio Mastering:** Built-in audio filters for dry studio, mobile, YouTube, and TikTok profiles, with optional background noise reduction (denoising) and sibilance reduction (de-essing).
*   **Dynamic Visual Backgrounds:** Fetches royalty-free vertical background clips from Pexels/Pixabay based on search queries, with procedural animated gradient fallback when API keys are not supplied.
*   **Social Media Ready:** High-definition vertical 9:16 aspect ratio (also supports 1:1 square and 16:9 landscape options).
*   **Direct YouTube Upload:** Publish directly to YouTube Shorts via built-in Google OAuth flow.

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
