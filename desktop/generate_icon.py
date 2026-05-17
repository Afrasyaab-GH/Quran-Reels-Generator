"""
Generate a multi-resolution placeholder icon.ico for the desktop build.
Run once:  python desktop/generate_icon.py
Output:    desktop/icon.ico, desktop/icon.png (Linux)
Replace with your real branded icon any time.
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
SIZES = [256, 128, 64, 48, 32, 16]

def make_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Rounded square gradient background (emerald → teal)
    r = max(2, size // 8)  # corner radius
    # Approximate gradient by drawing strips
    for y in range(size):
        t = y / max(1, size - 1)
        # emerald (#0f766e) -> teal (#134e4a)
        cr = int(15  + (19  - 15)  * t)
        cg = int(118 + (78  - 118) * t)
        cb = int(110 + (74  - 110) * t)
        d.line([(0, y), (size, y)], fill=(cr, cg, cb, 255))

    # Apply rounded mask
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=255)
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg.paste(img, (0, 0), mask)
    img = bg
    d = ImageDraw.Draw(img)

    # Crescent + star (simple Islamic motif) in gold
    gold = (255, 209, 102, 255)
    cx, cy = size // 2, size // 2
    R = int(size * 0.32)

    # Outer crescent disc
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=gold)
    # Inner disc offset to carve crescent
    off = int(R * 0.35)
    inner_r = int(R * 0.85)
    d.ellipse(
        [cx - inner_r + off, cy - inner_r, cx + inner_r + off, cy + inner_r],
        fill=(0, 0, 0, 0),
    )

    # Five-point star to the right (only visible at >= 48px)
    if size >= 48:
        import math
        sx = cx + int(R * 1.05)
        sy = cy - int(R * 0.05)
        sR = int(size * 0.09)
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rr = sR if i % 2 == 0 else sR * 0.42
            pts.append((sx + rr * math.cos(ang), sy + rr * math.sin(ang)))
        d.polygon(pts, fill=gold)

    return img


def main():
    images = [make_icon(s) for s in SIZES]
    ico_path = os.path.join(OUT_DIR, "icon.ico")
    images[0].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in SIZES],
        append_images=images[1:],
    )
    print(f"Wrote {ico_path}")

    png_path = os.path.join(OUT_DIR, "icon.png")
    images[0].save(png_path, format="PNG")
    print(f"Wrote {png_path}")

    # Also a 512px for splash window
    big = make_icon(512)
    splash_png = os.path.join(OUT_DIR, "icon_512.png")
    big.save(splash_png, format="PNG")
    print(f"Wrote {splash_png}")


if __name__ == "__main__":
    main()
