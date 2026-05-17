"""Generate desktop/splash.png (480x300 PNG used by PyInstaller's native splash)."""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "splash.png")
W, H = 480, 300
BG = (15, 118, 110, 255)      # emerald
GOLD = (255, 229, 160, 255)
WHITE = (255, 255, 255, 255)

img = Image.new("RGBA", (W, H), BG)
d = ImageDraw.Draw(img)

# Try to overlay the existing icon
icon_path = os.path.join(os.path.dirname(OUT), "icon_512.png")
if os.path.isfile(icon_path):
    try:
        ico = Image.open(icon_path).convert("RGBA")
        ico.thumbnail((110, 110), Image.LANCZOS)
        img.paste(ico, ((W - ico.width) // 2, 36), ico)
    except Exception:
        pass

def _font(size: int):
    for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()

title = "Quran Reels Generator"
sub = "Loading\u2026"
f1 = _font(22)
f2 = _font(12)

tw = d.textlength(title, font=f1)
d.text(((W - tw) // 2, 168), title, font=f1, fill=GOLD)

sw = d.textlength(sub, font=f2)
d.text(((W - sw) // 2, 210), sub, font=f2, fill=WHITE)

# Thin gold divider
d.rectangle([(W // 2 - 60, 200), (W // 2 + 60, 201)], fill=GOLD)

img.save(OUT, "PNG")
print(f"Wrote {OUT}")
