#!/usr/bin/env python3
"""
Turns a photo into a dot portrait for the hero card -> data/portrait.json

    pip install pillow
    python scripts/make_portrait.py C:\\path\\to\\photo.jpg

Options:
    --invert        use this if the dots come out as a negative (light subject on a dark background)
    --contrast 1.6  make the face stand out more (default 1.5)
    --cols 46       dot columns (default 46; more = more detail, bigger file)

Best photo: face centred, shoulders visible, plain light background, good light.
Keep the original photo OUTSIDE the repo folder. Only the dots get committed.
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

OUT = Path(__file__).resolve().parent.parent / "data" / "portrait.json"
ASPECT = 0.8        # width / height of the portrait
PITCH = 4.6         # distance between dots in the card (px)

ap = argparse.ArgumentParser()
ap.add_argument("photo")
ap.add_argument("--invert", action="store_true")
ap.add_argument("--contrast", type=float, default=1.5)
ap.add_argument("--cols", type=int, default=46)
args = ap.parse_args()

img = ImageOps.exif_transpose(Image.open(args.photo)).convert("L")
w, h = img.size

# crop to 4:5, keeping the upper part of the photo (faces are usually near the top)
if w / h > ASPECT:                       # too wide -> trim the sides
    nw = int(h * ASPECT)
    x0 = (w - nw) // 2
    img = img.crop((x0, 0, x0 + nw, h))
else:                                    # too tall -> trim mostly the bottom
    nh = int(w / ASPECT)
    y0 = int((h - nh) * 0.25)
    img = img.crop((0, y0, w, y0 + nh))

cols = args.cols
rows = round(cols / ASPECT)
img = img.resize((cols, rows), Image.LANCZOS)
img = ImageOps.autocontrast(img, cutoff=2)
img = ImageEnhance.Contrast(img).enhance(args.contrast)

max_r = PITCH * 0.52
dots = []
for row in range(rows):
    for col in range(cols):
        v = img.getpixel((col, row)) / 255
        darkness = v if args.invert else 1 - v
        r = max_r * (darkness ** 1.2)
        if r >= 0.4:
            dots.append([row, col, round(r, 2)])

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"cols": cols, "rows": rows, "pitch": PITCH, "dots": dots}),
               encoding="utf-8")
print(f"Saved {len(dots)} dots ({cols}x{rows}) -> {OUT}")
print("Now run: python scripts/render_readme_cards.py")
