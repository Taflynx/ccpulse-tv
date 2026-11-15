"""Pixel-art Claude critter + animated GIFs for a 240x240 GeekMagic display."""
from PIL import Image, ImageDraw
import math

W = H = 240
BG = (18, 18, 20)
ORANGE = (217, 119, 87)
DARK = (20, 20, 20)
CREAM = (240, 230, 215)
ACCENT = (255, 190, 120)

# 14 x 8 cell sprite. '#' body, 'e' eye, '.' empty
BODY = [
    "..##########..",
    "..##e####e##..",
    "####e####e####",
    "####e####e####",
    "..##########..",
    "..##########..",
]
LEGS_A = ["...#.#..#.#...", "...#.#..#.#..."]
LEGS_B = ["....#.#..#.#..", "....#.#..#.#.."]
LEGS_C = ["..#..#..#..#..", ".#...#..#...#."]


def sprite(eyes="open", legs=LEGS_A, arms_up=False):
    rows = [list(r) for r in BODY]
    if eyes == "closed":
        for r in (1, 2, 3):
            for c in range(14):
                if rows[r][c] == "e":
                    rows[r][c] = "#" if r != 3 else "e"
    if eyes == "happy":  # ^ ^
        for r in (1, 2, 3):
            for c in range(14):
                if rows[r][c] == "e":
                    rows[r][c] = "#"
        for c in (4, 9):
            rows[2][c] = "e"
            rows[3][c - 1] = "e"
            rows[3][c + 1] = "e"
    if arms_up:
        for r in (2, 3):
            for c in (0, 1, 12, 13):
                rows[r][c] = "."
        for r in (0, 1):
            for c in (0, 1, 12, 13):
                rows[r][c] = "#"
    return ["".join(r) for r in rows] + legs


def draw_sprite(d, rows, x, y, px=10):
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch == ".":
                continue
            col = ORANGE if ch == "#" else DARK
            d.rectangle([x + c * px, y + r * px, x + c * px + px - 1, y + r * px + px - 1], fill=col)


def spark(d, cx, cy, r, angle, color=ORANGE):
    """Claude-style starburst."""
    for i in range(8):
        a = angle + i * math.pi / 4
        ln = r if i % 2 == 0 else r * 0.6
        d.line([cx, cy, cx + math.cos(a) * ln, cy + math.sin(a) * ln], fill=color, width=4)


def frame():
    im = Image.new("RGB", (W, H), BG)
    return im, ImageDraw.Draw(im)


def ground(d, y=200):
    d.rectangle([0, y, W, y + 2], fill=(45, 45, 50))


SX = (W - 140) // 2  # sprite x when centered
SY = 110


def anim_idle():
    frames = []
    for i in range(24):
        im, d = frame()
        ground(d)
        bob = round(math.sin(i / 24 * 2 * math.pi) * 3)
        eyes = "closed" if i in (17, 18) else "open"
        draw_sprite(d, sprite(eyes), SX, SY + bob)
        frames.append(im)
    return frames, 90


def anim_walk():
    frames = []
    n = 40
    for i in range(n):
        im, d = frame()
        ground(d)
        x = -140 + round((W + 140) * i / (n - 1))
        legs = LEGS_A if (i // 2) % 2 == 0 else LEGS_B
        bob = 0 if (i // 2) % 2 == 0 else -4
        draw_sprite(d, sprite("open", legs), x, SY + bob)
        frames.append(im)
    return frames, 70


def anim_jump():
    frames = []
    n = 20
    for i in range(n):
        im, d = frame()
        ground(d)
        t = i / n
        h = max(0, math.sin(t * 2 * math.pi)) * 55
        up = h > 5
        draw_sprite(d, sprite("open", LEGS_C if up else LEGS_A, arms_up=up), SX, SY - round(h))
        if up:
            for k, (sx, sy) in enumerate([(40, 60), (200, 50), (25, 130), (215, 120)]):
                spark(d, sx, sy, 8 + (i + k) % 3 * 3, i / 3, ACCENT)
        frames.append(im)
    return frames, 60


def anim_sleep():
    frames = []
    n = 30
    for i in range(n):
        im, d = frame()
        ground(d)
        breathe = 2 if (i // 8) % 2 else 0
        draw_sprite(d, sprite("closed"), SX, SY + breathe)
        for k in range(3):
            p = ((i + k * 10) % n) / n
            zx = 175 + round(p * 35)
            zy = 100 - round(p * 80)
            s = 6 + round(p * 10)
            c = tuple(int(BG[j] + (CREAM[j] - BG[j]) * (1 - p)) for j in range(3))
            d.line([zx, zy, zx + s, zy], fill=c, width=3)
            d.line([zx + s, zy, zx, zy + s], fill=c, width=3)
            d.line([zx, zy + s, zx + s, zy + s], fill=c, width=3)
        frames.append(im)
    return frames, 110


def anim_think():
    frames = []
    n = 24
    for i in range(n):
        im, d = frame()
        ground(d)
        draw_sprite(d, sprite("open"), SX, SY)
        spark(d, 120, 55, 26, i / n * math.pi / 2)
        dots = (i // 4) % 4
        for k in range(dots):
            d.ellipse([92 + k * 22, 92, 100 + k * 22, 100], fill=CREAM)
        frames.append(im)
    return frames, 80


ANIMS = {
    "clawd_idle": anim_idle,
    "clawd_walk": anim_walk,
    "clawd_jump": anim_jump,
    "clawd_sleep": anim_sleep,
    "clawd_think": anim_think,
}


def _lzw_block(pim, min_code=8):
    """GIF LZW image data (min-code-size byte + sub-blocks + terminator) for a P-mode frame,
    using the frame's indices as-is against the global palette."""
    data = pim.tobytes()
    clear, eoi = 1 << min_code, (1 << min_code) + 1
    out, acc, nbits = bytearray(), 0, 0
    size = min_code + 1

    def emit(code):
        nonlocal acc, nbits
        acc |= code << nbits
        nbits += size
        while nbits >= 8:
            out.append(acc & 0xFF)
            acc >>= 8
            nbits -= 8

    table = {bytes([i]): i for i in range(clear)}
    nxt = eoi + 1
    emit(clear)
    w = bytes([data[0]])
    for k in data[1:]:
        wk = w + bytes([k])
        if wk in table:
            w = wk
            continue
        emit(table[w])
        if nxt < 4096:
            table[wk] = nxt
            nxt += 1
            if nxt > (1 << size) and size < 12:
                size += 1
        else:
            emit(clear)
            table = {bytes([i]): i for i in range(clear)}
            nxt, size = eoi + 1, min_code + 1
        w = bytes([k])
    emit(table[w])
    emit(eoi)
    if nbits:
        out.append(acc & 0xFF)
    blocks = bytearray([min_code])
    for i in range(0, len(out), 255):
        chunk = out[i:i + 255]
        blocks += bytes([len(chunk)]) + chunk
    return bytes(blocks + b"\x00")


def save_gif(frames, ms, path, colors=64):
    """Full-frame GIF with one global 256-color palette (what the GeekMagic decoder expects:
    no cropped delta frames, no local palettes)."""
    import struct
    w, h = frames[0].size
    sample = Image.new("RGB", (w, h * len(frames)))
    for k, f in enumerate(frames):
        sample.paste(f, (0, k * h))
    ref = sample.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    pal = (ref.getpalette()[: colors * 3] + [0] * 768)[:768]
    ref.putpalette(pal)
    out = bytearray(b"GIF89a" + struct.pack("<HHBBB", w, h, 0xF7, 0, 0) + bytes(pal))
    out += b"\x21\xFF\x0BNETSCAPE2.0\x03\x01\x00\x00\x00"
    for f in frames:
        q = f.quantize(palette=ref, dither=Image.Dither.NONE)
        out += b"\x21\xF9\x04" + bytes([0x04]) + struct.pack("<H", max(2, ms // 10)) + b"\x00\x00"
        out += b"\x2C" + struct.pack("<HHHHB", 0, 0, w, h, 0)
        out += _lzw_block(q)
    out += b"\x3B"
    open(path, "wb").write(out)


if __name__ == "__main__":
    import sys, os
    out = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(out, exist_ok=True)
    for name, fn in ANIMS.items():
        frames, ms = fn()
        p = os.path.join(out, name + ".gif")
        save_gif(frames, ms, p)
        print(p, os.path.getsize(p) // 1024, "KB")
