# Building the Desktop App

This folder packages the Flask + MoviePy app as a **native desktop application** using `pywebview` (window) + `PyInstaller` (bundling).

The bundle launches Flask on a free localhost port and opens it in a native window — no console, no browser tab, no Python install required for end users.

---

## Quick start (Windows)

```powershell
.\desktop\build_windows.ps1
```

Output:
- `dist\QuranReels\` — runnable folder (double-click `QuranReels.exe`)
- `dist\QuranReels-Setup-0.2.4.exe` — installer (if NSIS is installed)

First build takes 3–8 minutes. Total size ~400–600 MB.

## macOS

```bash
bash desktop/build_macos.sh
```
Output: `dist/QuranReels.app` and (optionally) `dist/QuranReels-1.0.0.dmg`.

## Linux

```bash
bash desktop/build_linux.sh
```
Output: `dist/QuranReels/` and (optionally) `dist/QuranReels-1.0.0-x86_64.AppImage`.

---

## Prerequisites per platform

| Platform | Required | Optional (for installer) |
|---|---|---|
| Windows | Python 3.10+, FFmpeg (bundled automatically) | [NSIS](https://nsis.sourceforge.io/) |
| macOS   | Python 3.10+ (`brew install python`), `brew install ffmpeg` | `brew install create-dmg` |
| Linux   | Python 3.10+, `sudo apt install ffmpeg python3-gi gir1.2-webkit2-4.0` | `appimagetool` |

> **Important:** PyInstaller cannot cross-compile. You must build each OS bundle on that OS (or in a VM/CI).

---

## What's in the bundle

```
dist/QuranReels/
├── QuranReels.exe           # launcher
├── _internal/               # Python runtime + all packages
├── UI.html                  # main UI
├── fonts/                   # bundled Arabic + English fonts
└── ffmpeg/                  # bundled ffmpeg + ffprobe (~80 MB)
```

User-writable data goes to a separate folder (preserved across uninstall/update):

| OS | User data location |
|---|---|
| Windows | `%APPDATA%\QuranReels\` |
| macOS   | `~/Library/Application Support/QuranReels/` |
| Linux   | `~/.local/share/QuranReels/` |

This holds: `quran_jobs.db`, `outputs/`, `temp_workspaces/`, `local_bgs/`, `vision/`, and an optional `pexels_key.txt`.

---

## Customizing icons

Place your icons in `desktop/`:
- `icon.ico` — Windows (multi-resolution .ico)
- `icon.icns` — macOS
- `icon.png` — Linux (256×256 PNG)

If absent, default OS icons are used.

---

## Bundling a Pexels key (optional, per-build)

Create `%APPDATA%\QuranReels\pexels_key.txt` on the user's machine (or have your installer write it). The launcher auto-loads it as `PEXELS_API_KEYS` env var.

For per-user setup, users can also paste the key into the in-app banner.

---

## Security & "safe" distribution

**Windows SmartScreen** will show "Unrecognized publisher" on first launch:
- Per-user installer (default in our NSIS script) avoids UAC entirely
- For a clean "verified publisher" experience, buy a **code-signing certificate** (~$200/yr from SSL.com, Sectigo, DigiCert). Then sign with:
  ```powershell
  signtool sign /fd SHA256 /a /tr http://timestamp.digicert.com /td SHA256 dist\QuranReels-Setup-1.0.0.exe
  ```

**macOS Gatekeeper** blocks unsigned apps. Users can bypass with right-click → Open, or you can:
- Get an [Apple Developer ID](https://developer.apple.com/) ($99/yr)
- `codesign --deep --force --options runtime --sign "Developer ID Application: …" dist/QuranReels.app`
- Notarize with `xcrun notarytool submit`

**Linux** has no equivalent — AppImage runs anywhere.

**Antivirus false positives** are common with PyInstaller. Mitigations:
- Use one-folder mode (default in our spec) instead of `--onefile` — far fewer FPs
- Submit a clean build to Microsoft Defender via [submit.microsoft.com](https://www.microsoft.com/en-us/wdsi/filesubmission)
- Strip UPX compression (disabled in our spec)

---

## Distributing via Hugging Face Spaces

You can attach release binaries to your Space repository:

1. Build the installer/bundle on each OS
2. Commit them to a `releases/` folder in the Space repo, **or**
3. Push them to a **GitHub Releases** page on a companion repo and link from the Space README

HF Space file storage limit is 50 GB (free tier), and each file ≤ 5 GB.

Sample README section to add to your Space:
```markdown
## 💻 Desktop App

Download the offline desktop version:
- 🪟 [Windows installer (450 MB)](./releases/QuranReels-Setup-0.2.4.exe)
- 🍎 [macOS app (.dmg, 480 MB)](./releases/QuranReels-0.2.4.dmg)
- 🐧 [Linux AppImage (430 MB)](./releases/QuranReels-0.2.4-x86_64.AppImage)
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Window opens then closes immediately | Run the .exe from a terminal to see stderr |
| "No module named X" at runtime | Add `X` to `hiddenimports` in `QuranReels.spec` |
| Huge bundle (>800 MB) | Check `excludes=` list; remove unused heavy deps |
| Antivirus quarantine | Use one-folder mode, sign the binary, submit for whitelisting |
| pywebview window blank | On Linux ensure WebKitGTK installed; on Windows ensure Edge WebView2 runtime |
| MoviePy `IndexError: list index out of range` | FFmpeg not found inside bundle — ensure `desktop/ffmpeg/ffmpeg.exe` was staged before build |

---

## Testing the launcher without building

```powershell
python desktop\launcher.py
```

This runs Flask + pywebview from source — useful for verifying everything works before the long PyInstaller build.
