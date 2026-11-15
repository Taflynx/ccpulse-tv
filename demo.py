#!/usr/bin/env python3
"""Build the README / GitHub Pages assets from the real renderers, with sample data.

  python3 demo.py        -> docs/screens/*.png, docs/media/*.gif, docs/demo.gif
"""
import datetime, os, shutil, sys, time
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import boot, clawd, clock_screen, usage_screen  # noqa: E402

DOCS = os.path.join(HERE, "docs")
SCREENS = os.path.join(DOCS, "screens")
MEDIA = os.path.join(DOCS, "media")

NOW_MS = time.time() * 1000
H = 3600 * 1000
SAMPLE_USAGE = {
    "cycles": [
        {"key": "five_hour", "source": "official", "used": 0.34, "elapsed": 0.62, "end": NOW_MS + 1.9 * H},
        {"key": "seven_day", "source": "official", "used": 0.71, "elapsed": 0.55, "end": NOW_MS + 75.5 * H},
    ],
    "official": {"available": True, "fetchedAt": NOW_MS},
}
SAMPLE_WEATHER = {
    "current": {"temperature_2m": 14.2, "apparent_temperature": 12.6, "weather_code": 2, "is_day": 1},
    "daily": {"temperature_2m_max": [16.4, 13.1], "temperature_2m_min": [8.2, 7.5], "weather_code": [2, 61]},
}
SAMPLE_NOW = datetime.datetime(2026, 11, 15, 9, 41)


def jpg_to_img(render):
    p = os.path.join(MEDIA, "_tmp.png")
    render(p)
    im = Image.open(p).convert("RGB")
    os.remove(p)
    return im


def big(im, k=2):
    return im.resize((im.width * k, im.height * k), Image.Resampling.BOX)


# ---------- device mockup ----------
def device(screen, scale=2):
    """A stylised mini-TV around a 240x240 screen image."""
    s = screen.resize((int(240 * scale), int(240 * scale)), Image.Resampling.BOX)
    sw = s.width
    pad, bez = 46, 16
    bw, bh = sw + 2 * (pad + bez), sw + 2 * (pad + bez) + 40
    W, Hh = bw + 80, bh + 70
    im = Image.new("RGB", (W, Hh), (13, 17, 23))
    # soft shadow
    sh = Image.new("L", (W, Hh), 0)
    ImageDraw.Draw(sh).rounded_rectangle([50, 52, W - 50, Hh - 8], radius=42, fill=150)
    im.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(18)))
    d = ImageDraw.Draw(im)
    x0, y0 = 40, 24
    # body with a subtle vertical gradient
    body = Image.new("RGB", (bw, bh))
    bd = ImageDraw.Draw(body)
    for y in range(bh):
        t = y / bh
        bd.line([0, y, bw, y], fill=(int(64 - 22 * t), int(64 - 22 * t), int(70 - 22 * t)))
    mask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, bw - 1, bh - 1], radius=36, fill=255)
    im.paste(body, (x0, y0), mask)
    d.rounded_rectangle([x0, y0, x0 + bw - 1, y0 + bh - 1], radius=36, outline=(92, 92, 100), width=2)
    # screen bezel
    sx, sy = x0 + pad, y0 + pad
    d.rounded_rectangle([sx, sy, sx + sw + 2 * bez, sy + sw + 2 * bez], radius=18, fill=(6, 6, 8))
    im.paste(s, (sx + bez, sy + bez))
    # glass highlight
    gl = Image.new("L", (sw, sw), 0)
    ImageDraw.Draw(gl).polygon([(0, 0), (sw * .55, 0), (0, sw * .42)], fill=16)
    im.paste((255, 255, 255), (sx + bez, sy + bez), gl)
    # power LED + feet
    ly = y0 + bh - 30
    d.ellipse([x0 + bw // 2 - 4, ly, x0 + bw // 2 + 4, ly + 8], fill=(217, 119, 87))
    for fx in (x0 + 50, x0 + bw - 90):
        d.rounded_rectangle([fx, y0 + bh - 4, fx + 40, y0 + bh + 10], radius=5, fill=(40, 40, 45))
    return im


def gif_frames(path):
    g = Image.open(path)
    out = []
    for i in range(g.n_frames):
        g.seek(i)
        out.append((g.convert("RGB"), g.info.get("duration", 80)))
    return out


def main():
    os.makedirs(SCREENS, exist_ok=True)
    os.makedirs(MEDIA, exist_ok=True)

    usage = jpg_to_img(lambda p: usage_screen.render(SAMPLE_USAGE, p))
    clock_screen.CITY = "London"
    clock = jpg_to_img(lambda p: clock_screen.render(p, now=SAMPLE_NOW, w=SAMPLE_WEATHER))

    # device-format GIFs (what gets uploaded) + browser copies for the simulator
    gifs = {}
    for name, fn in list(clawd.ANIMS.items()) + [("boot", lambda: (boot.frames(), 90))]:
        frames, ms = fn()
        p = os.path.join(MEDIA, name + ".gif")
        clawd.save_gif(frames, ms, p)
        gifs[name] = [(f, ms) for f in frames]
    usage.save(os.path.join(MEDIA, "claude_usage.png"))
    clock.save(os.path.join(MEDIA, "clock.png"))

    # 2x screenshots
    big(usage).save(os.path.join(SCREENS, "usage.png"))
    big(clock).save(os.path.join(SCREENS, "clock.png"))
    for name in ("clawd_walk", "clawd_jump", "clawd_sleep", "clawd_think", "clawd_idle", "boot"):
        fr = gifs[name]
        big(fr[len(fr) // 2 if name != "boot" else -1][0]).save(os.path.join(SCREENS, name + ".png"))

    # weather icon sheet
    keys = list(clock_screen.PIX)
    sheet = Image.new("RGB", (len(keys) * 80 + 10, 90), clawd.BG)
    sd = ImageDraw.Draw(sheet)
    for i, k in enumerate(keys):
        clock_screen.pix_icon(sd, k, 10 + i * 80, 15, px=5)
    big(sheet).save(os.path.join(SCREENS, "weather_icons.png"))

    # the hero: device playing its rotation
    seq = []
    seq += [(device(f), ms) for f, ms in gifs["boot"]]
    seq += [(device(usage), 2600)]
    seq += [(device(f), ms) for f, ms in gifs["clawd_walk"]]
    seq += [(device(clock), 2600)]
    for name in ("clawd_jump", "clawd_think"):
        reps = 2 if name == "clawd_jump" else 1
        seq += [(device(f), ms) for f, ms in gifs[name]] * reps
    seq += [(device(f), ms) for f, ms in gifs["clawd_sleep"]]
    frames = [f for f, _ in seq]
    durs = [ms for _, ms in seq]
    frames[0].save(os.path.join(DOCS, "demo.gif"), save_all=True, append_images=frames[1:],
                   duration=durs, loop=0, optimize=True)
    device(usage).save(os.path.join(SCREENS, "device.png"))

    # fonts for the web simulator
    os.makedirs(os.path.join(DOCS, "fonts"), exist_ok=True)
    for f in ("LiberationSans-Bold.ttf", "LiberationSans-Regular.ttf"):
        shutil.copy(os.path.join(HERE, "fonts", f), os.path.join(DOCS, "fonts", f))
    for root, _, files in os.walk(DOCS):
        for f in sorted(files):
            p = os.path.join(root, f)
            print(f"{os.path.relpath(p, HERE):40s} {os.path.getsize(p) // 1024:6d} KB")


if __name__ == "__main__":
    main()
