"""
Desktop launcher for Quran Reels Generator.

Pipeline:
  1. Set up crash handler -> writes traceback to user-data/logs/
  2. Show a minimal Tk splash window immediately
  3. (Windows) verify Edge WebView2 runtime is installed; offer to download if not
  4. Start Flask in a background thread on a free localhost port
  5. Wait for server to respond
  6. Close splash, open pywebview native window
"""

from __future__ import annotations

import os
import sys
import socket
import threading
import time
import logging
import traceback
import datetime
import webbrowser
from urllib.request import urlopen
from urllib.error import URLError


APP_NAME = "Quran Reels Generator"
APP_WIDTH = 1180
APP_HEIGHT = 820
IS_WINDOWS = os.name == "nt"


# ---------------------------------------------------------------------------
# Logging / crash handler
# ---------------------------------------------------------------------------

def _user_data_dir() -> str:
    """Resolve user-data dir the same way main.py does, without importing it."""
    env = os.environ.get("QURAN_REELS_DATA_DIR", "").strip()
    if env:
        return env
    if not getattr(sys, "frozen", False):
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if IS_WINDOWS:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "QuranReels")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/QuranReels")
    return os.path.join(
        os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"),
        "QuranReels",
    )


USER_DATA = _user_data_dir()
LOG_DIR = os.path.join(USER_DATA, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "launcher.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("launcher")


def _write_crash(exc: BaseException) -> str:
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(LOG_DIR, f"crash-{stamp}.log")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"Quran Reels Generator crash at {stamp}\n")
            f.write(f"Python: {sys.version}\nPlatform: {sys.platform}\n\n")
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
        log.error("Crash log: %s", path)
    except Exception:
        pass
    return path


def _install_excepthook() -> None:
    def hook(exc_type, exc, tb):
        path = _write_crash(exc)
        msg = f"{APP_NAME} encountered a fatal error.\n\nDetails saved to:\n{path}"
        try:
            if IS_WINDOWS:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, msg, APP_NAME, 0x10)
            else:
                print(msg, file=sys.stderr)
        except Exception:
            pass
    sys.excepthook = hook


# ---------------------------------------------------------------------------
# WebView2 runtime check (Windows)
# ---------------------------------------------------------------------------

WEBVIEW2_DOWNLOAD_URL = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"


def _has_webview2() -> bool:
    """Check the registry for an installed WebView2 evergreen runtime."""
    if not IS_WINDOWS:
        return True
    try:
        import winreg
    except ImportError:
        return True
    keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"),
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"),
    ]
    for hive, path in keys:
        try:
            with winreg.OpenKey(hive, path) as k:
                val, _ = winreg.QueryValueEx(k, "pv")
                if val and val != "0.0.0.0":
                    return True
        except OSError:
            continue
    return False


def _prompt_webview2_install() -> None:
    if not IS_WINDOWS:
        return
    import ctypes
    msg = (
        "Microsoft Edge WebView2 runtime is required to display this app.\n\n"
        "Click OK to open the download page in your browser.\n"
        "(One-time install, ~2 MB bootstrapper. Restart this app after installing.)"
    )
    MB_OKCANCEL = 0x01
    MB_ICONWARNING = 0x30
    result = ctypes.windll.user32.MessageBoxW(0, msg, APP_NAME, MB_OKCANCEL | MB_ICONWARNING)
    if result == 1:  # IDOK
        webbrowser.open(WEBVIEW2_DOWNLOAD_URL)


# ---------------------------------------------------------------------------
# Splash window (PyInstaller native pyi_splash - shown by the bootloader
# before Python even starts; gracefully no-op in dev mode)
# ---------------------------------------------------------------------------

try:
    import pyi_splash  # type: ignore  # only available in frozen builds with Splash()
    _HAS_SPLASH = True
except ImportError:
    pyi_splash = None  # type: ignore
    _HAS_SPLASH = False


class Splash:
    def show(self) -> None:
        # pyi_splash is already visible at this point (shown by bootloader)
        return

    def set_status(self, text: str) -> None:
        if _HAS_SPLASH and pyi_splash is not None:
            try:
                pyi_splash.update_text(text)
            except Exception:
                pass

    def close(self) -> None:
        if _HAS_SPLASH and pyi_splash is not None:
            try:
                pyi_splash.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Flask server thread
# ---------------------------------------------------------------------------

def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_server(url: str, timeout: float = 45.0, splash: "Splash | None" = None) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=1.5) as r:
                if r.status == 200:
                    return True
        except (URLError, ConnectionResetError, OSError):
            if splash:
                elapsed = int(timeout - (deadline - time.time()))
                splash.set_status(f"Loading engine... ({elapsed}s)")
            time.sleep(0.4)
    return False


def _configure_environment() -> None:
    """Auto-load persisted Pexels key if present."""
    if not os.environ.get("PEXELS_API_KEYS"):
        key_file = os.path.join(USER_DATA, "pexels_key.txt")
        if os.path.isfile(key_file):
            try:
                with open(key_file, "r", encoding="utf-8") as f:
                    key = f.read().strip()
                if key:
                    os.environ["PEXELS_API_KEYS"] = key
                    log.info("Loaded PEXELS_API_KEYS from %s", key_file)
            except Exception as e:
                log.warning("Could not read %s: %s", key_file, e)


_FLASK_ERROR: "BaseException | None" = None


def _run_flask(port: int) -> None:
    global _FLASK_ERROR
    try:
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        os.environ.setdefault("FLASK_ENV", "production")
        log.info("Importing main module...")
        import main  # noqa: F401
        log.info("main imported OK; starting Flask on port %d", port)
        main.app.run(host="127.0.0.1", port=port, threaded=True, use_reloader=False)
    except BaseException as e:
        _FLASK_ERROR = e
        log.exception("Flask thread crashed")
        _write_crash(e)


def _thread_excepthook(args) -> None:  # type: ignore[no-untyped-def]
    global _FLASK_ERROR
    _FLASK_ERROR = args.exc_value
    log.error(
        "Unhandled thread exception in %s",
        getattr(args.thread, "name", "?"),
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )
    try:
        _write_crash(args.exc_value)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def _main() -> int:
    log.info("==== Launch %s ====", datetime.datetime.now().isoformat())
    log.info("frozen=%s exe=%s", bool(getattr(sys, "frozen", False)), sys.executable)
    log.info("USER_DATA=%s", USER_DATA)
    try:
        threading.excepthook = _thread_excepthook  # type: ignore[assignment]
    except Exception:
        pass

    if IS_WINDOWS and not _has_webview2():
        log.warning("WebView2 runtime missing")
        _prompt_webview2_install()
        return 2

    splash = Splash()
    splash.show()
    splash.set_status("Loading configuration...")

    _configure_environment()

    splash.set_status("Starting backend...")
    port = _find_free_port()
    url = f"http://127.0.0.1:{port}/"
    log.info("Flask URL: %s", url)

    server_thread = threading.Thread(target=_run_flask, args=(port,), daemon=True)
    server_thread.start()

    if not _wait_for_server(url, timeout=45.0, splash=splash):
        splash.close()
        if _FLASK_ERROR is not None:
            log.error("Server failed to start: %r", _FLASK_ERROR)
            if IS_WINDOWS:
                try:
                    import ctypes
                    ctypes.windll.user32.MessageBoxW(
                        0,
                        f"{APP_NAME} backend failed to start.\n\n"
                        f"{type(_FLASK_ERROR).__name__}: {_FLASK_ERROR}\n\n"
                        f"See logs in:\n{LOG_DIR}",
                        APP_NAME, 0x10,
                    )
                except Exception:
                    pass
            return 1
        log.error("Server did not respond in 45s; opening in browser")
        webbrowser.open(url)
        try:
            server_thread.join()
        except KeyboardInterrupt:
            pass
        return 1

    splash.set_status("Opening window...")
    time.sleep(0.2)
    splash.close()

    try:
        import webview  # type: ignore
        webview.create_window(
            APP_NAME,
            url,
            width=APP_WIDTH,
            height=APP_HEIGHT,
            min_size=(900, 600),
            confirm_close=False,
            text_select=True,
        )
        webview.start(gui=None, debug=False)
        return 0
    except Exception:
        log.exception("pywebview failed; falling back to default browser")
        webbrowser.open(url)
        try:
            server_thread.join()
        except KeyboardInterrupt:
            pass
        return 0


def main_entry() -> int:
    _install_excepthook()
    try:
        return _main()
    except SystemExit:
        raise
    except BaseException as e:
        path = _write_crash(e)
        try:
            if IS_WINDOWS:
                import ctypes
                ctypes.windll.user32.MessageBoxW(
                    0,
                    f"{APP_NAME} failed to start.\n\nLog: {path}",
                    APP_NAME, 0x10,
                )
        except Exception:
            pass
        return 99


if __name__ == "__main__":
    sys.exit(main_entry())
