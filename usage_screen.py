"""Render Claude usage (from `ccpulse pace -j`) as a 240x240 JPEG."""
import json, os, subprocess, sys, time, datetime
from PIL import Image, ImageDraw, ImageFont
from clawd import sprite, draw_sprite, ORANGE, BG

F = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts") + "/"
def font(sz, bold=True):
    return ImageFont.truetype(F + ("LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"), sz)

GREY = (140, 140, 150)
TEXT = (235, 235, 240)
TRACK = (50, 50, 58)
STATUS = {"ok": (90, 200, 120), "warn": (240, 190, 70), "critical": (235, 85, 70)}
LABELS = {"seven_day": "WEEKLY", "five_hour": "5-HOUR", "seven_day_fable_cap": "FABLE CAP",
          "seven_day_opus": "OPUS WEEKLY", "seven_day_sonnet": "SONNET WEEKLY"}


def load():
    """Usage cycles from ccpulse (https://github.com/Taflynx/ccpulse). CCPULSE_BIN overrides the binary."""
    os.environ["PATH"] = (os.environ.get("PATH") or "/usr/local/bin:/usr/bin:/bin") + os.pathsep + os.path.expanduser("~/.local/bin")
    out = subprocess.run([os.environ.get("CCPULSE_BIN", "ccpulse"), "pace", "-j"], capture_output=True, text=True, timeout=120).stdout
    return json.loads(out)


def color_for(used, elapsed):
    if used >= 0.9 or used > elapsed + 0.25:
        return STATUS["critical"]
    if used > elapsed:
        return STATUS["warn"]
    return STATUS["ok"]


def fmt_reset(ms):
    t = datetime.datetime.fromtimestamp(ms / 1000)
    left = ms / 1000 - time.time()
    if left < 86400:
        h, m = int(left // 3600), int(left % 3600 // 60)
        return f"reset in {h}h{m:02d}m"
    return t.strftime("%a %H:%M") + f" · {left / 86400:.1f}d"


def bar(d, x, y, w, h, used, elapsed, col):
    d.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=TRACK)
    uw = max(h, round(w * min(used, 1)))
    d.rounded_rectangle([x, y, x + uw, y + h], radius=h // 2, fill=col)
    ex = x + round(w * min(elapsed, 1))  # period marker
    d.rectangle([ex - 1, y - 5, ex + 1, y + h + 5], fill=TEXT)


def render(data, path):
    im = Image.new("RGB", (240, 240), BG)
    d = ImageDraw.Draw(im)
    draw_sprite(d, sprite(), 10, 10, px=3)  # 42x24 mini critter
    d.text((60, 10), "CLAUDE USAGE", font=font(18), fill=TEXT)
    d.text((60, 31), "official limits", font=font(11, False), fill=GREY)

    # official windows first, then derived; max 2 to fit
    cyc = sorted(data.get("cycles", []), key=lambda c: (c.get("source") != "official", c["key"]))[:2]
    y = 54
    for c in cyc:
        used, el = c["used"], c["elapsed"]
        col = color_for(used, el)
        lab = LABELS.get(c["key"], c["key"].upper())
        if c.get("source") != "official":
            lab += " ~"
        d.text((12, y + 8), lab, font=font(13), fill=GREY)
        d.text((228, y - 2), f"{used * 100:.0f}%", font=font(34), fill=col, anchor="ra")
        bar(d, 12, y + 42, 216, 12, used, el, col)
        d.text((12, y + 62), f"{el * 100:.0f}% of period", font=font(13, False), fill=TEXT)
        d.text((228, y + 62), fmt_reset(c["end"]), font=font(12, False), fill=GREY, anchor="ra")
        y += 86

    if not cyc:
        d.text((120, 120), "no data", font=font(20), fill=GREY, anchor="mm")
    off = data.get("official", {})
    ts = off.get("fetchedAt")
    if not ts:  # endpoint rate-limited: fall back to ccpulse's last successful fetch
        try:
            ts = json.load(open(os.path.expanduser("~/.cache/ccpulse/official-usage.json")))["fetchedAt"]
        except Exception:
            ts = time.time() * 1000
    age = (time.time() * 1000 - ts) / 60000
    stamp = "official "  + datetime.datetime.fromtimestamp(ts / 1000).strftime("%H:%M")
    if age > 30:
        stamp += "  (stale)"
    d.text((120, 230), stamp, font=font(11, False), fill=GREY if age <= 30 else STATUS["warn"], anchor="ms")
    im.save(path, quality=90)  # format from extension (device wants .jpg)


if __name__ == "__main__":
    render(load(), sys.argv[1] if len(sys.argv) > 1 else "claude_usage.jpg")
