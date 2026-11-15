#!/usr/bin/env python3
"""Render assets/logo-{light,dark}.png from assets/mark.svg with headless Chrome
(same recipe as the ccpulse logo: Inter 800 wordmark, transparent background, 2x)."""
import os, shutil, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MARK = open(os.path.join(HERE, "mark.svg")).read()
CHROME = next(c for c in ("google-chrome", "chromium", "chromium-browser") if shutil.which(c))
FONTS = '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;800&display=block" rel="stylesheet">'


def wordmark(theme):
    fg = "#f0efec" if theme == "dark" else "#0b0b0b"
    sub = "#a9b1bc" if theme == "dark" else "#52514e"
    mark = MARK.replace('width="128" height="128"', 'width="120" height="120"')
    return f"""<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>
    body{{margin:0;width:820px;height:190px;display:flex;align-items:center;justify-content:center;
         background:transparent;font-family:Inter,sans-serif;color:{fg}}}
    .wm{{font-size:84px;font-weight:800;letter-spacing:-0.045em;line-height:1;display:flex;align-items:center}}
    .grad{{background:linear-gradient(90deg,#3f8ef0,#6fb8ff);-webkit-background-clip:text;color:transparent}}
    .tv{{font-size:40px;letter-spacing:0;margin-left:14px;padding:6px 14px 8px;border-radius:14px;
         background:#ff8a5c;color:#1a0f0a;line-height:1;transform:translateY(4px)}}
    .sub{{color:{sub};font-size:22px;font-weight:500;margin-top:12px;letter-spacing:-0.01em}}
    </style></head><body><div style="display:flex;align-items:center;gap:26px">
    <div style="width:120px;height:120px">{mark}</div>
    <div><div class="wm">cc<span class="grad">pulse</span><span class="tv">TV</span></div>
    <div class="sub">Claude Code usage, live on a mini TV</div></div></div></body></html>"""


def main():
    tmp = tempfile.mkdtemp()
    for theme in ("light", "dark"):
        html = os.path.join(tmp, f"{theme}.html")
        open(html, "w").write(wordmark(theme))
        out = os.path.join(HERE, f"logo-{theme}.png")
        subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                        "--default-background-color=00000000", "--force-device-scale-factor=2",
                        "--virtual-time-budget=8000", "--window-size=820,190", f"--screenshot={out}",
                        f"file://{html}"], check=True, capture_output=True)
        print("wrote", os.path.relpath(out, os.path.dirname(HERE)))


if __name__ == "__main__":
    main()
