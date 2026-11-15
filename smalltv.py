#!/usr/bin/env python3
"""ccpulse-tv: drive a GeekMagic SmallTV-PRO from your server.

  smalltv.py info              device model, firmware, free flash
  smalltv.py setup             render + upload animations and boot screen, configure the album
  smalltv.py usage             render the Claude usage screen and push it      (cron: every 10 min)
  smalltv.py clock             render the clock + weather screen and push it   (cron: every minute)
  smalltv.py ls                list images on the device
  smalltv.py upload FILE...    upload files to the album
  smalltv.py rm NAME...        delete images from the device
  smalltv.py cron              print crontab lines for this checkout

Settings come from env vars or ./config.env (see config.example.env).
"""
import json, os, sys, tempfile, urllib.parse, urllib.request, uuid

HERE = os.path.dirname(os.path.abspath(__file__))


def load_config():
    p = os.path.join(HERE, "config.env")
    if os.path.exists(p):
        for line in open(p):
            line = line.split("#", 1)[0].strip()
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


load_config()
sys.path.insert(0, HERE)
HOST = os.environ.get("SMALLTV_HOST", "")
INTERVAL = os.environ.get("SMALLTV_INTERVAL", "20")  # seconds per album item
GIF_LOOP = os.environ.get("SMALLTV_GIF_LOOP", "3")   # times each GIF plays


def base():
    if not HOST:
        sys.exit("Set SMALLTV_HOST (env or config.env) to your device's IP.")
    return f"http://{HOST}"


def get(path, timeout=10):
    with urllib.request.urlopen(base() + path, timeout=timeout) as r:
        return r.read().decode(errors="replace")


def upload(path, name=None):
    """POST /doUpload?dir=/image/ (multipart field 'file'). Same name overwrites."""
    name = name or os.path.basename(path)
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\n"
            f"Content-Type: application/octet-stream\r\n\r\n").encode() + open(path, "rb").read() + \
        f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(base() + "/doUpload?dir=/image/", data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        if r.status != 200:
            raise RuntimeError(f"upload {name}: HTTP {r.status}")


def ls():
    import re
    return re.findall(r"href='/image//([^']+)'", get("/filelist?dir=/image/"))


def rm(name):
    # firmware answers "Failed" even when the delete succeeded, so check the listing instead
    get("/delete?file=" + urllib.parse.quote("/image//" + name, safe=""))
    return name not in ls()


def cmd_info():
    print(get("/v.json"), get("/space.json"), get("/.sys/app.json"), sep="\n")


def cmd_setup():
    import boot, clawd
    out = os.path.join(HERE, "out")
    os.makedirs(out, exist_ok=True)
    for name, fn in clawd.ANIMS.items():
        frames, ms = fn()
        clawd.save_gif(frames, ms, os.path.join(out, name + ".gif"))
    clawd.save_gif(boot.frames(), 90, os.path.join(out, "boot.gif"))
    for f in sorted(os.listdir(out)):
        if f.endswith(".gif"):
            upload(os.path.join(out, f))
            print("uploaded", f)
    cmd_usage()
    cmd_clock()
    get(f"/set?i_i={INTERVAL}&gif_loop={GIF_LOOP}&autoplay=1")
    get("/set?theme=3")  # 4.Picture = start-up app (applies after reboot)
    print("album: autoplay every", INTERVAL, "s; start-up app set to Picture (reboot or pick it on the device)")


def _push(render, name):
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, name)
        render(p)
        upload(p)


def cmd_usage():
    import usage_screen
    _push(lambda p: usage_screen.render(usage_screen.load(), p), "claude_usage.jpg")


def cmd_clock():
    import clock_screen
    _push(clock_screen.render, "clock.jpg")


def cmd_cron():
    py = sys.executable
    me = os.path.join(HERE, "smalltv.py")
    log = os.path.join(HERE, "push.log")
    print(f"*/10 * * * * {py} {me} usage >> {log} 2>&1")
    print(f"* * * * * {py} {me} clock >> {log} 2>&1")


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return
    c, rest = argv[0], argv[1:]
    if c == "info":
        cmd_info()
    elif c == "setup":
        cmd_setup()
    elif c == "usage":
        cmd_usage()
    elif c == "clock":
        cmd_clock()
    elif c == "ls":
        print("\n".join(ls()))
    elif c == "upload":
        for f in rest:
            upload(f)
            print("uploaded", f)
    elif c == "rm":
        for n in rest:
            print(n, "deleted" if rm(n) else "NOT deleted")
    elif c == "cron":
        cmd_cron()
    else:
        sys.exit(f"unknown command {c!r}; see --help")


if __name__ == "__main__":
    main(sys.argv[1:])
