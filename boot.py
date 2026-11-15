"""Boot animation: critter drops in, a spark spins up, 'CLAUDE' types out."""
import math, sys
from PIL import ImageFont
from clawd import frame, draw_sprite, sprite, spark, save_gif, LEGS_A, LEGS_C, ORANGE, CREAM, ACCENT

FONT = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 30)
SX, SY = 50, 100
WORD = "CLAUDE"


def frames():
    out = []
    # 1) drop in from the top with a small bounce (12 frames)
    for i in range(12):
        im, d = frame()
        t = i / 11
        y = -80 + (SY + 80) * min(1, t * 1.25)
        if t > 0.8:
            y -= math.sin((t - 0.8) / 0.2 * math.pi) * 12
        draw_sprite(d, sprite("open", LEGS_C if t < 0.8 else LEGS_A), SX, round(y))
        out.append(im)
    # 2) spark grows and spins above, critter blinks (14 frames)
    for i in range(14):
        im, d = frame()
        draw_sprite(d, sprite("closed" if i in (6, 7) else "open"), SX, SY)
        spark(d, 120, 55, 6 + i * 2, i / 14 * math.pi, ORANGE)
        out.append(im)
    # 3) word types out under the critter (len(WORD)*2 frames), then hold
    for i in range(len(WORD) * 2 + 10):
        im, d = frame()
        draw_sprite(d, sprite("open"), SX, SY)
        spark(d, 120, 55, 32, math.pi + i / 10, ORANGE)
        shown = WORD[: min(len(WORD), i // 2 + 1)]
        d.text((120, 200), shown, font=FONT, fill=CREAM, anchor="mm")
        if i < len(WORD) * 2 and i % 2 == 0:
            w = d.textlength(shown, font=FONT)
            d.rectangle([120 + w / 2 + 3, 188, 120 + w / 2 + 6, 212], fill=ACCENT)
        out.append(im)
    return out


if __name__ == "__main__":
    save_gif(frames(), 90, sys.argv[1] if len(sys.argv) > 1 else "out/boot.gif")
