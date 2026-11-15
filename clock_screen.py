"""Render a 240x240 clock + local weather screen (Open-Meteo, no API key).

Configure with WEATHER_LAT, WEATHER_LON, WEATHER_CITY and WEATHER_TZ (IANA) env vars."""
import datetime, json, math, os, sys, time, urllib.parse, urllib.request
from PIL import Image, ImageDraw, ImageFont

LAT = os.environ.get("WEATHER_LAT", "51.5074")
LON = os.environ.get("WEATHER_LON", "-0.1278")
CITY = os.environ.get("WEATHER_CITY", "London")
TZ = urllib.parse.quote(os.environ.get("WEATHER_TZ", "Europe/London"), safe="")
CACHE = os.path.expanduser("~/.cache/geekmagic-weather.json")
F = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts") + "/"
BG = (18, 18, 20)
TEXT = (240, 236, 228)
GREY = (140, 140, 150)
ORANGE = (217, 119, 87)
SUN = (255, 196, 80)
CLOUD = (200, 205, 215)
RAIN = (110, 170, 240)


def font(sz, bold=True):
    return ImageFont.truetype(F + ("LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"), sz)


def weather():
    """Cached for 15 minutes; on network failure use the stale cache."""
    try:
        c = json.load(open(CACHE))
        if time.time() - c["_at"] < 900:
            return c
    except Exception:
        c = None
    url = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
           "&current=temperature_2m,apparent_temperature,weather_code,is_day"
           "&daily=temperature_2m_max,temperature_2m_min,weather_code&timezone=%s&forecast_days=3"
           % (LAT, LON, TZ))
    try:
        d = json.load(urllib.request.urlopen(url, timeout=10))
        d["_at"] = time.time()
        json.dump(d, open(CACHE, "w"))
        return d
    except Exception:
        return c


def kind(code):
    if code in (0, 1):
        return "clear", "Clear"
    if code == 2:
        return "partly", "Partly cloudy"
    if code == 3:
        return "cloud", "Overcast"
    if code in (45, 48):
        return "fog", "Fog"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow", "Snow"
    if code in (95, 96, 99):
        return "storm", "Thunderstorm"
    if 51 <= code <= 67 or 80 <= code <= 82:
        return "rain", "Rain" if code >= 61 else "Drizzle"
    return "cloud", "Cloudy"


def cloud(d, x, y, s, col=CLOUD):
    d.ellipse([x, y + s * .35, x + s * .55, y + s * .9], fill=col)
    d.ellipse([x + s * .25, y + s * .1, x + s * .8, y + s * .7], fill=col)
    d.ellipse([x + s * .5, y + s * .35, x + s, y + s * .9], fill=col)
    d.rectangle([x + s * .27, y + s * .55, x + s * .78, y + s * .9], fill=col)


def sun(d, cx, cy, r, day=True):
    if not day:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(230, 225, 200))
        d.ellipse([cx - r * .4, cy - r * 1.1, cx + r * 1.4, cy + r * .6], fill=BG)
        return
    for i in range(8):
        a = i * math.pi / 4
        d.line([cx + math.cos(a) * r * 1.3, cy + math.sin(a) * r * 1.3,
                cx + math.cos(a) * r * 1.7, cy + math.sin(a) * r * 1.7], fill=SUN, width=3)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=SUN)


def icon(d, k, x, y, s, day=True):
    if k == "clear":
        sun(d, x + s / 2, y + s / 2, s * .28, day)
    elif k == "partly":
        sun(d, x + s * .62, y + s * .35, s * .2, day)
        cloud(d, x, y + s * .2, s * .8)
    elif k == "fog":
        for i in range(4):
            d.line([x + s * .1, y + s * (.25 + i * .17), x + s * .9, y + s * (.25 + i * .17)], fill=CLOUD, width=4)
    else:
        cloud(d, x, y, s * .95, CLOUD if k != "storm" else (150, 150, 165))
        if k == "rain":
            for i in range(3):
                d.line([x + s * (.25 + i * .22), y + s * .92, x + s * (.18 + i * .22), y + s * 1.08], fill=RAIN, width=3)
        if k == "snow":
            for i in range(3):
                cx, cy = x + s * (.25 + i * .22), y + s
                d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(255, 255, 255))
        if k == "storm":
            p = [(x + s * .5, y + s * .75), (x + s * .38, y + s * 1.0), (x + s * .5, y + s * .98), (x + s * .42, y + s * 1.18)]
            d.line(p, fill=SUN, width=3)


# pixel-art weather icons (same 'chunky pixel' language as the critter); 12x10 cells
PIX = {
    "clear": ["....s..s....", ".s........s.", "....oooo....", "...oooooo...", "s.oooooooo.s",
              "..oooooooo..", "...oooooo...", "....oooo....", ".s........s.", "....s..s...."],
    "moon": ["....cccc....", "...ccc......", "..ccc.......", "..cc........", "..cc........",
             "..ccc.......", "...cccc..c..", "....cccccc..", "............", "............"],
    "partly": ["......s..s..", ".......ooo..", "...cc.ooooo.", "..cccccoooo.", ".cccccccoo..",
               "cccccccccc..", "cccccccccc..", ".cccccccc...", "............", "............"],
    "cloud": ["............", "....cccc....", "...cccccc...", ".cccccccccc.", "cccccccccccc",
              "cccccccccccc", ".cccccccccc.", "............", "............", "............"],
    "rain": ["....cccc....", "...cccccc...", ".cccccccccc.", "cccccccccccc", ".cccccccccc.",
             "............", "..b...b...b.", ".b...b...b..", "..b...b...b.", ".b...b...b.."],
    "snow": ["....cccc....", "...cccccc...", ".cccccccccc.", "cccccccccccc", ".cccccccccc.",
             "............", ".w...w...w..", "...w...w...w", ".w...w...w..", "...w...w...w"],
    "storm": ["....gggg....", "...gggggg...", ".gggggggggg.", "gggggggggggg", ".ggggyggggg.",
              ".....yy.....", "....yy......", "...yyyy.....", ".....yy.....", "....y......."],
    "fog": ["............", "cccccccccc..", "............", "..cccccccccc", "............",
            "cccccccccc..", "............", "..cccccccccc", "............", "............"],
}
PCOL = {"s": SUN, "o": (255, 170, 70), "c": CLOUD, "b": RAIN, "w": (255, 255, 255),
        "g": (150, 150, 165), "y": SUN}


def pix_icon(d, k, x, y, px=5):
    for r, line in enumerate(PIX[k]):
        for c, ch in enumerate(line):
            if ch != ".":
                d.rectangle([x + c * px, y + r * px, x + c * px + px - 1, y + r * px + px - 1], fill=PCOL[ch])


def temp_color(t):
    if t <= -10:
        return (120, 170, 255)
    if t <= 5:
        return (170, 200, 240)
    if t >= 28:
        return (235, 85, 70)
    return ORANGE


def render(path, now=None, w=None):
    from clawd import sprite, draw_sprite
    im = Image.new("RGB", (240, 240), BG)
    d = ImageDraw.Draw(im)
    now = now or datetime.datetime.now()
    # header — same as the usage screen
    draw_sprite(d, sprite(), 10, 10, px=3)
    d.text((60, 10), "CLAUDE TIME", font=font(18), fill=TEXT)
    d.text((60, 31), now.strftime("%A, %d %b").lower(), font=font(11, False), fill=GREY)

    # time — big, centered, colon in Claude orange
    hh, mm = now.strftime("%H"), now.strftime("%M")
    f = font(64)
    wh, wc, wm = d.textlength(hh, font=f), d.textlength(":", font=f), d.textlength(mm, font=f)
    x0 = 120 - (wh + wc + wm) / 2
    d.text((x0, 50), hh, font=f, fill=TEXT)
    d.text((x0 + wh, 46), ":", font=f, fill=ORANGE)
    d.text((x0 + wh + wc, 50), mm, font=f, fill=TEXT)

    w = w or weather()
    if not w:
        d.text((120, 175), "weather unavailable", font=font(13, False), fill=GREY, anchor="mm")
    else:
        cur, day = w["current"], w["daily"]
        k, label = kind(cur["weather_code"])
        if k == "clear" and not cur.get("is_day", 1):
            k = "moon"
        t = round(cur["temperature_2m"])
        d.text((12, 130), CITY.upper(), font=font(13), fill=GREY)
        d.text((228, 124), f"{t}°", font=font(34), fill=temp_color(t), anchor="ra")
        pix_icon(d, k, 12, 152, px=5)
        d.text((76, 160), label, font=font(14), fill=TEXT)
        d.text((76, 180), f"feels {round(cur['apparent_temperature'])}°  ·  "
               f"{round(day['temperature_2m_max'][0])}°/{round(day['temperature_2m_min'][0])}°",
               font=font(12, False), fill=GREY)
        tk, tl = kind(day["weather_code"][1])
        d.text((12, 210), "tomorrow", font=font(13, False), fill=TEXT)
        d.text((228, 210), f"{tl.lower()}  {round(day['temperature_2m_max'][1])}°/{round(day['temperature_2m_min'][1])}°",
               font=font(12, False), fill=GREY, anchor="ra")
    im.save(path, quality=90)  # format from extension (device wants .jpg)


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "clock.jpg")
