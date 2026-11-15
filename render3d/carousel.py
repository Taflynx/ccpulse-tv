#!/usr/bin/env python3
"""Turn docs/renders/*.jpg into one auto-advancing carousel image (animated WebP) for the README:
each slide holds, cross-fades into the next, with page dots at the bottom. Also writes thumbnails.

  python3 render3d/carousel.py
"""
import os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(ROOT, "docs", "renders")
SLIDES = ["hero", "desk", "close", "trio"]
W, H = 1200, 750
HOLD_MS, FADE_FRAMES, FADE_MS = 3200, 10, 45


def dots(im, active):
    im = im.convert("RGBA")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    n, r, gap = len(SLIDES), 6, 22
    x0 = W // 2 - (n - 1) * gap // 2
    y = H - 28
    d.rounded_rectangle([x0 - 20, y - 16, x0 + (n - 1) * gap + 20, y + 16], radius=16, fill=(0, 0, 0, 90))
    for i in range(n):
        cx = x0 + i * gap
        if i == active:
            d.rounded_rectangle([cx - 11, y - r, cx + 11, y + r], radius=r, fill=(255, 255, 255, 235))
        else:
            d.ellipse([cx - r + 1, y - r + 1, cx + r - 1, y + r - 1], fill=(255, 255, 255, 110))
    return Image.alpha_composite(im, ov).convert("RGB")


def main():
    imgs = [Image.open(os.path.join(R, s + ".jpg")).convert("RGB").resize((W, H), Image.Resampling.LANCZOS) for s in SLIDES]
    frames, durs = [], []
    for i, im in enumerate(imgs):
        frames.append(dots(im, i)); durs.append(HOLD_MS)
        nxt = imgs[(i + 1) % len(imgs)]
        for k in range(1, FADE_FRAMES + 1):
            t = k / (FADE_FRAMES + 1)
            t = t * t * (3 - 2 * t)  # smoothstep
            frames.append(dots(Image.blend(im, nxt, t), i if t < 0.5 else (i + 1) % len(imgs)))
            durs.append(FADE_MS)
    out = os.path.join(R, "carousel.webp")
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=durs, loop=0, quality=82, method=6)
    print("wrote", os.path.relpath(out, ROOT), os.path.getsize(out) // 1024, "KB")
    for s, im in zip(SLIDES, imgs):
        t = im.resize((280, 175), Image.Resampling.LANCZOS)
        p = os.path.join(R, s + "_thumb.jpg")
        t.save(p, quality=86)
    print("wrote thumbnails")


if __name__ == "__main__":
    main()
