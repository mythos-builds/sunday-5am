#!/usr/bin/env python3
"""BCH BLAZE 2026 · Media track entry, « Sunday, 5 AM » (1080x1920, 60 fps): Mom needs $50, the bank is closed,
Bitcoin Cash is not. Made entirely with code: every frame is drawn here and the music and sound effects are synthesized here, on one 120 BPM grid (beat 0.5 s,
bar 2 s, 22 s of score) played at SPEED 0.45, so 54 BPM and 48.9 s.
One idea per screen, motion acts out the word, no voiceover. Palette: night, cream, BCH green, one red.
Claims kept to what bitcoincash.org itself says (« fees under a penny and confirmations in seconds », checked
2026-11-15) and the whitepaper's first line. Logo: bch-logo.svg (the community mark, #0AC18E).
Needs numpy, scipy, Pillow and ffmpeg, plus the four fonts listed in README.md, in fonts/:
  python3 cash.py                   → out/sunday-5am.mp4
  python3 cash.py --fps 30          → quicker render for a check
  python3 cash.py --stills 1,3,5.2  → out/stills.png (frames at those seconds of the video)"""
import json, math, pathlib, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.signal import butter, sosfilt

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
def arg(k, d): return sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
W, H, SR, BEAT, DUR = 1080, 1920, 48000, 0.5, 22.0               # BEAT, DUR in score time
SPEED = float(arg("--speed", 0.45)); FPS = int(arg("--fps", 60))
LEN = round(DUR / SPEED, 3)                                       # video seconds
BG, SURF, LINE, INK, MUTED = (11, 14, 13), (25, 30, 28), (56, 64, 60), (238, 236, 228), (138, 147, 142)
GREEN, DEEP, RED, STEEL = (10, 193, 142), (5, 28, 20), (232, 90, 79), (70, 77, 74)
DISPLAY, SERIF, MONO, MONOB = "BigShouldersDisplay-900.ttf", "InstrumentSerif-400i.ttf", "IBMPlexMono-500.ttf", "IBMPlexMono-700.ttf"
SANS, SANSB = "Inter.ttf@450", "Inter.ttf@700"
BIC = Image.Resampling.BICUBIC

# ── easing ───────────────────────────────────────────────────────────────────
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, t0, d): return clamp((t - t0) / d)
def out_expo(x): return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)
def out_back(x, s=1.9): x -= 1; return 1 + (s + 1) * x ** 3 + s * x ** 2
def in_out(x): return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def drop(x): return (x / .7) ** 2 if x < .7 else 1 - .07 * math.sin(math.pi * (x - .7) / .3)   # falls, one bounce
def mix(a, b, k): return tuple(round(a[i] + (b[i] - a[i]) * k) for i in range(3))
def pulse(t, start, amp=0.022):
    """A small breath on every beat after `start`: the picture moves with the kick."""
    if t < start: return 1.0
    return 1 + amp * math.exp(-((t - start) % BEAT) / 0.07)
def lubdub(t, start):
    if t < start: return 1.0
    dt = (t - start) % BEAT
    return 1 + .11 * math.exp(-dt / .07) + (.07 * math.exp(-(dt - .13) / .07) if dt > .13 else 0)

# ── drawing helpers ──────────────────────────────────────────────────────────
_fonts, _layers = {}, {}
def font(name, size):
    """name = file or file@weight (Inter is variable: its axes are opsz, wght)."""
    if (name, size) not in _fonts:
        file, _, wght = name.partition("@"); f = ImageFont.truetype(str(HERE / "fonts" / file), size)
        if wght: f.set_variation_by_axes([max(14, min(32, size * .75)), int(wght)])
        _fonts[name, size] = f
    return _fonts[name, size]

def fit(txt, name, max_w, size):
    while size > 12 and font(name, size).getlength(txt) > max_w: size -= 4
    return size

def text(txt, name, size, fill, upto=None):
    """A text layer cropped to the full line's box; upto = draw only the first n characters (typing),
    in the same box, so the line never jumps while it types."""
    key = (txt, name, size, fill, upto)
    if key not in _layers:
        f = font(name, size); l, t, r, b = f.getbbox(txt)
        im = Image.new("RGBA", (r - l + 8, b - t + 8), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((4 - l, 4 - t), txt if upto is None else txt[:upto], font=f, fill=fill)
        _layers[key] = im
    return _layers[key]

def put(fr, im, cx, cy, scale=1.0, alpha=1.0, rot=0.0):
    if alpha <= 0.01 or scale <= 0.01: return
    if abs(scale - 1) > 1e-3: im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), BIC)
    if rot: im = im.rotate(rot, BIC, expand=True)
    if alpha < 0.999:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    fr.paste(im, (round(cx - im.width / 2), round(cy - im.height / 2)), im)

def tint(im, col):
    key = ("tint", id(im), col)
    if key not in _layers:
        out = Image.new("RGBA", im.size, col + (255,)); out.putalpha(im.getchannel("A")); _layers[key] = out
    return _layers[key]

def notif(lines, w=960, h=410):
    """A phone notification from Mom; lines = the message, one or two lines."""
    key = ("notif", lines)
    if key not in _layers:
        im = Image.new("RGBA", (w + 18, h + 18), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle([18, 18, w + 17, h + 17], 48, fill=(0, 0, 0, 150))
        d.rounded_rectangle([0, 0, w - 1, h - 1], 48, fill=SURF + (255,), outline=LINE + (255,), width=2)
        d.rounded_rectangle([44, 40, 108, 104], 17, fill=GREEN + (255,))
        d.rounded_rectangle([58, 55, 94, 83], 10, fill=DEEP + (255,)); d.polygon([(63, 79), (61, 93), (75, 82)], fill=DEEP + (255,))
        d.text((132, 72), "MESSAGES", font=font(MONOB, 28), fill=MUTED, anchor="lm")
        d.text((w - 48, 72), "now", font=font(MONO, 28), fill=MUTED, anchor="rm")
        d.text((48, 172), "Mom", font=font(SANSB, 64), fill=INK, anchor="lm")
        for i, ln in enumerate(lines): d.text((48, 262 + i * 78), ln, font=font(SANS, 62), fill=INK, anchor="lm")
        _layers[key] = im
    return _layers[key]

def heart(size, col):
    key = ("heart", size, col)
    if key not in _layers:
        im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); s = size / 36
        pts = [(size / 2 + s * 16 * math.sin(a) ** 3,
                size * .45 - s * (13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)))
               for a in np.linspace(0, 2 * math.pi, 240)]
        ImageDraw.Draw(im).polygon(pts, fill=col + (255,)); _layers[key] = im
    return _layers[key]

def coin(r, label, fill, ink, ring=None, name=DISPLAY):
    key = ("coin", r, label, fill, ink, ring, name)
    if key not in _layers:
        im = Image.new("RGBA", (2 * r + 4, 2 * r + 4), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.ellipse([2, 2, 2 * r + 1, 2 * r + 1], fill=fill + (255,), outline=(ring or fill) + (255,), width=max(3, r // 20))
        if label: put(im, text(label, name, fit(label, name, int(1.25 * r), int(r * .95)), ink), r + 2, r + 2)
        _layers[key] = im
    return _layers[key]

def stamp(txt, col, size=210):
    key = ("stamp", txt, col, size)
    if key not in _layers:
        f = font(DISPLAY, size); l, t, r, b = f.getbbox(txt)
        im = Image.new("RGBA", (r - l + 110, b - t + 90), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rectangle([0, 0, r - l + 109, b - t + 89], fill=BG + (240,), outline=col + (255,), width=12)
        d.text((55 - l, 45 - t), txt, font=f, fill=col); _layers[key] = im
    return _layers[key]

def logo(px):
    """The Bitcoin Cash mark: bch-logo.png, rasterized from bch-logo.svg at 600 px (README: how)."""
    key = ("logo", px)
    if key not in _layers: _layers[key] = Image.open(HERE / "bch-logo.png").convert("RGBA").resize((px, px), Image.Resampling.LANCZOS)
    return _layers[key]

WIN = (W // 2, 1000, 860, 540)                                    # the bank's window: centre x, y, width, height
def window(fr, inside, label=None, label_col=MUTED):
    cx, cy, w, h = WIN; d = ImageDraw.Draw(fr); x0, y0 = cx - w // 2, cy - h // 2
    d.rectangle([x0 - 18, y0 - 18, x0 + w + 18, y0 + h + 18], fill=LINE)
    d.rectangle([x0, y0, x0 + w, y0 + h], fill=inside)
    if label: put(fr, text(label, MONOB, 40, label_col), cx, cy)

def shutter(fr, cover):
    """A rolling steel shutter over the window, `cover` = 0 (up) … 1 (down)."""
    cx, cy, w, h = WIN; x0, y0 = cx - w // 2, cy - h // 2; hh = int(h * clamp(cover))
    if hh <= 0: return
    d = ImageDraw.Draw(fr); d.rectangle([x0, y0, x0 + w, y0 + hh], fill=STEEL)
    for y in range(y0 + hh - 34, y0, -34): d.line([x0, y, x0 + w, y], fill=(46, 52, 49), width=5)
    d.rectangle([x0, y0 + hh - 24, x0 + w, y0 + hh], fill=(104, 112, 107))

def title(fr, txt, t, t0, col=INK, y=470, size=None):
    size = size or fit(txt, DISPLAY, 940, 200)
    put(fr, text(txt, DISPLAY, size, col), W / 2, y, scale=1.12 - .12 * out_expo(prog(t, t0, .22)), alpha=prog(t, t0, .05))

def line(fr, txt, t, t0, col=INK, y=1450, size=140, name=SERIF):
    q = out_expo(prog(t, t0, .4))
    put(fr, text(txt, name, fit(txt, name, 960, size), col), W / 2, y + 40 * (1 - q), alpha=q)

# ── scenes (one idea per screen, a bar each = 4.4 s at 54 BPM) ───────────────
YOU, MOM, CTRL = (190, 1000), (890, 1000), (540, 560)
def bez(u):
    return ((1 - u) ** 2 * YOU[0] + 2 * (1 - u) * u * CTRL[0] + u ** 2 * MOM[0],
            (1 - u) ** 2 * YOU[1] + 2 * (1 - u) * u * CTRL[1] + u ** 2 * MOM[1])
NOS = ["BANK.", "BORDERS.", "PERMISSION.", "WAITING."]
QUOTE = [("“A purely", INK), ("peer-to-peer", INK), ("version of", INK), ("electronic cash”", GREEN)]

def s_message(fr, t, t0, msg, clock, buzz=(), drop_at=.25):
    lt = t - t0
    put(fr, text(clock, DISPLAY, fit(clock, DISPLAY, 900, 130), MUTED), W / 2, 470, alpha=prog(lt, -.2, .15))
    sh = 0
    for b0 in buzz:                                               # the phone buzzes
        if b0 <= lt < b0 + .3: sh = int(18 * math.sin((lt - b0) * 140) * (1 - (lt - b0) / .3))
    y = 250 + (900 - 250) * out_back(prog(lt, drop_at, .35), 1.3)
    put(fr, notif(msg), W / 2 + sh, y, alpha=prog(lt, drop_at, .08))

def frame(t):
    fr = Image.new("RGB", (W, H), GREEN if t >= 18 else BG); d = ImageDraw.Draw(fr)
    if t < 2:                                                    # SUN 5:12 AM — Mom needs $50
        s_message(fr, t, 0, ("can you send $50?", "it's urgent"), "SUNDAY, 5:12 AM", buzz=(0.0, .75), drop_at=-.12)
        put(fr, text("MOM · 8,000 KM AWAY", MONOB, 44, MUTED), W / 2, 1250, alpha=out_expo(prog(t, 1.35, .3)))
    elif t < 4:                                                  # YOUR BANK — the shutter slams: CLOSED.
        title(fr, "YOUR BANK", t, 2, MUTED, size=170)
        window(fr, SURF, "INTERNATIONAL TRANSFERS")
        shutter(fr, drop(prog(t, 2.5, .24)))
        if t >= 2.74:
            put(fr, stamp("CLOSED.", RED), W / 2, WIN[1], scale=1.4 - .4 * out_back(prog(t, 2.74, .2)), alpha=prog(t, 2.74, .05), rot=-4)
        line(fr, "back on Monday.", t, 3.2)
    elif t < 6:                                                  # BITCOIN CASH — the shutter rises: OPEN.
        title(fr, "BITCOIN CASH", t, 4, GREEN, size=170)
        window(fr, GREEN)
        put(fr, text("OPEN.", DISPLAY, 300, DEEP), W / 2, WIN[1], scale=pulse(t, 4, .03) * (.85 + .15 * out_back(prog(t, 4.1, .3))))
        shutter(fr, 1 - out_expo(prog(t, 4.0, .45)))
        line(fr, "every day. all day.", t, 5.0)
    elif t < 8:                                                  # SENT → ARRIVED. in seconds.
        for k in range(0, 40, 2): d.line([bez(k / 40), bez((k + 1) / 40)], fill=LINE, width=6)
        arrived = t >= 6.85
        for (x, y), name, lit in ((YOU, "YOU", False), (MOM, "MOM", arrived)):
            d.ellipse([x - 82, y - 82, x + 82, y + 82], fill=GREEN if lit else BG, outline=GREEN if lit else INK, width=6)
            put(fr, text(name, MONOB, 40, INK), x, y + 140)
        if arrived:
            p = prog(t, 6.85, .7); rr = 82 + 190 * out_expo(p)
            if p < 1: d.ellipse([MOM[0] - rr, MOM[1] - rr, MOM[0] + rr, MOM[1] + rr], outline=mix(BG, GREEN, 1 - p), width=7)
        if t < 6.25: put(fr, coin(64, "$50", GREEN, DEEP), *YOU, scale=out_back(prog(t, 6.0, .25)))
        elif not arrived:
            for j in range(7, 0, -1):                              # the trail
                put(fr, coin(34, None, GREEN, DEEP), *bez(in_out(prog(t - j * .022, 6.25, .6))), alpha=.1 * (8 - j))
            put(fr, coin(64, "$50", GREEN, DEEP), *bez(in_out(prog(t, 6.25, .6))))
        else: put(fr, coin(64, "$50", DEEP, GREEN), *MOM, scale=1 + .25 * (1 - out_back(prog(t, 6.85, .3))))
        if not arrived: title(fr, "SENT.", t, 6.25, INK, size=230)
        else: title(fr, "ARRIVED.", t, 6.85, GREEN, size=230)
        line(fr, "in seconds.", t, 7.1)
    elif t < 10:                                                 # THE FEE? — a cent, sliced: less than a cent.
        title(fr, "THE FEE?", t, 8, INK, size=200)
        c = coin(230, "1¢", SURF, INK, ring=INK); n, cx, cy = 10, W // 2, 1000; sw = c.width / n; keep = 5
        if t < 8.5: put(fr, c, cx, cy, scale=pulse(t, 8, .03) * (.8 + .2 * out_back(prog(t, 8.0, .3))))
        else:
            for i in range(n):
                strip = c.crop((round(i * sw), 0, round((i + 1) * sw), c.height)); x = cx - c.width / 2 + (i + .5) * sw
                if i == keep:                                       # the tenth of a cent that stays
                    k = out_expo(prog(t, 9.0, .45))
                    put(fr, tint(strip, GREEN) if t >= 9.0 else strip, x + (cx - x) * k, cy, scale=1 + .3 * k)
                else:
                    t0 = 8.62 + .035 * abs(i - keep); dt = max(0.0, t - t0)
                    put(fr, strip, x + (i - keep) * 40 * dt, cy + 2400 * dt * dt, rot=(i - keep) * 14 * dt, alpha=1 - prog(t, t0 + .25, .35))
            for i in range(1, n):                                  # the cuts flash
                ct = 8.5 + .012 * i
                if ct <= t < ct + .1:
                    x = cx - c.width / 2 + i * sw; d.line([x, cy - 270, x, cy + 270], fill=INK, width=4)
        line(fr, "less than a cent.", t, 9.0, GREEN)
    elif t < 12:                                                 # Mom: got it!! — the heart beats
        s_message(fr, t, 10, ("got it!! thank you", "you saved me"), "SUNDAY, 5:13 AM")
        put(fr, heart(240, RED), W / 2, 1380, scale=lubdub(t, 10.75) * out_back(prog(t, 10.6, .3)), alpha=prog(t, 10.6, .06))
    elif t < 14:                                                 # NO BANK. NO BORDERS. NO PERMISSION. NO WAITING.
        k = min(3, int((t - 12) / BEAT)); t0 = 12 + k * BEAT; s = 1.14 - .14 * out_expo(prog(t, t0, .18))
        put(fr, text("NO", DISPLAY, 260, GREEN), W / 2, 720, scale=s)
        lay = text(NOS[k], DISPLAY, fit(NOS[k], DISPLAY, 920, 330), INK); put(fr, lay, W / 2, 1010, scale=s)
        p = out_expo(prog(t, t0 + .2, .14))
        if p > 0:
            x0 = W / 2 - lay.width / 2 + 6; d.rectangle([x0, 1000, x0 + (lay.width - 12) * p, 1022], fill=RED)
    elif t < 16:                                                 # the whitepaper's first line, typed
        n = int(clamp((t - 14.05) * 34, 0, 99)); y = 690
        for txt, col in QUOTE:
            put(fr, text(txt, SERIF, 138, col, upto=max(0, min(len(txt), n))), W / 2, y); n -= len(txt); y += 160
        put(fr, text("— the Bitcoin whitepaper, 2008", MONO, 40, MUTED), W / 2, 1360, alpha=out_expo(prog(t, 15.5, .3)))
    elif t < 18:                                                 # THAT WAS THE PROMISE. — it still works.
        title(fr, "THAT WAS", t, 16, INK, y=720, size=220)
        if t >= 16.5: title(fr, "THE PROMISE.", t, 16.5, INK, y=940, size=fit("THE PROMISE.", DISPLAY, 940, 240))
        line(fr, "it still works.", t, 17.0, GREEN, y=1260, size=180)
    else:                                                        # the mark, on green
        p = out_expo(prog(t, 18, .35)); s = 1.25 - .25 * p
        put(fr, coin(158, None, DEEP, DEEP), W / 2, 690, scale=s * pulse(t, 18.5, .015))
        put(fr, logo(300), W / 2, 690, scale=s * pulse(t, 18.5, .015))
        put(fr, text("BITCOIN CASH", DISPLAY, fit("BITCOIN CASH", DISPLAY, 900, 260), DEEP), W / 2, 1000, scale=s)
        n = int(clamp((t - 19.0) * 22, 0, 99))
        if n: put(fr, text("bitcoincash.org", MONOB, 64, DEEP, upto=n), W / 2, 1180)
        q = out_expo(prog(t, 19.9, .4)); put(fr, text("peer-to-peer electronic cash", SERIF, 80, DEEP), W / 2, 1300, alpha=q)
    return fr

# ── music + sound effects (all synthesized here, original, no license needed) ─
def audio(path):
    n = int((LEN + 1.5) * SR); mix_ = np.zeros((2, n), np.float32); rng = np.random.default_rng(11)
    tt = lambda d: np.arange(int(d * SR)) / SR
    lp = lambda s, fc: sosfilt(butter(2, fc, "low", fs=SR, output="sos"), s)
    hp = lambda s, fc: sosfilt(butter(2, fc, "high", fs=SR, output="sos"), s)
    def add(s, t, g=1.0, pan=0.0):                               # t = score time, placed at SPEED
        i = int(t / SPEED * SR); j = min(n, i + len(s))
        if i < n: mix_[0, i:j] += g * (1 - max(0, pan)) * s[:j - i]; mix_[1, i:j] += g * (1 + min(0, pan)) * s[:j - i]
    def kick(f0=130, f1=46, d=0.4):
        x = tt(d); ph = 2 * np.pi * np.cumsum(f1 + (f0 - f1) * np.exp(-x * 32)) / SR
        return np.sin(ph) * np.exp(-x * 8) + 0.2 * hp(rng.standard_normal(len(x)), 2000) * np.exp(-x * 250)
    def hat(d=0.06): x = tt(d); return hp(rng.standard_normal(len(x)), 7000) * np.exp(-x * 70)
    def clap():
        x = tt(0.25); env = sum(np.exp(-np.clip(x - o, 0, None) * 60) * (x >= o) for o in (0, .011, .022))
        return lp(hp(rng.standard_normal(len(x)), 900), 5000) * env * 0.6
    def saw(f, d): x = tt(d); return 2 * ((x * f) % 1) - 1
    def stab(fs, d=0.32):
        x = tt(d); s = sum(saw(f * c, d) for f in fs for c in (0.996, 1.004))
        return lp(s, 2600) * np.exp(-x * 9) / (2 * len(fs))
    def bass(f, d):
        x = tt(d); return (np.sin(2 * np.pi * f * x) + 0.25 * lp(saw(f, d), 400)) * np.minimum(1, x * 80) * np.exp(-x * 1.2 * SPEED)
    def pad(fs, d=4.5 / SPEED, cut=1800):
        x = tt(d); s = sum(saw(f * c, d) for f in fs for c in (0.995, 1.0, 1.005))
        return lp(s, cut) * np.minimum(1, x / 0.08) * np.exp(-x * 0.9 * SPEED) / (3 * len(fs))
    def tone(f, d, k=30, sq=False):
        x = tt(d); s = np.sign(np.sin(2 * np.pi * f * x)) if sq else np.sin(2 * np.pi * f * x)
        return s * np.exp(-x * k)
    def impact(big=1.0):
        x = tt(1.4); return (kick(95, 34, 1.4) * 1.1 + 0.5 * lp(rng.standard_normal(len(x)), 1400) * np.exp(-x * 9)
                             + 0.6 * np.sin(2 * np.pi * 38 * x) * np.exp(-x * 2.2)) * big
    def whoosh(d=0.6):
        x = tt(d); return lp(hp(rng.standard_normal(len(x)), 300), 3000) * np.sin(np.pi * x / d) ** 2
    def riser(d):
        x = tt(d); f = 180 * (1600 / 180) ** (x / d)
        return (0.6 * hp(rng.standard_normal(len(x)), 1500) + 0.4 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * (x / d) ** 2
    def click(): x = tt(0.012); return hp(rng.standard_normal(len(x)), 2500) * np.exp(-x * 400)
    def buzz(d=0.3):                                              # a phone vibrating on a table
        x = tt(d); s = np.sign(np.sin(2 * np.pi * 168 * x)) * (0.65 + 0.35 * np.sin(2 * np.pi * 24 * x))
        return lp(s, 700) * np.minimum(1, x / .01) * np.minimum(1, (d - x) / .03)
    def metal(d=1.3):                                             # the steel shutter ringing
        x = tt(d); return sum(a * np.sin(2 * np.pi * f * x) * np.exp(-x * k)
                              for f, a, k in ((311, .5, 5), (743, .35, 7), (1187, .25, 9), (1789, .2, 12), (2511, .12, 15)))
    def rattle(d):                                                # slats rolling
        x = tt(d); return hp(rng.standard_normal(len(x)), 1200) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 38 * x))) * 0.5
    def slice_(d=0.2):
        x = tt(d); return (hp(rng.standard_normal(len(x)), 3500) * np.sqrt(x / d) * np.exp(-x * 22)
                           + 0.3 * np.sin(2 * np.pi * np.cumsum(2600 + 5200 * x / d) / SR) * np.exp(-x * 28))
    def ding(f=1318.5): return tone(f, 0.9, 6) + 0.6 * tone(f * 1.5, 0.9, 8)

    C, G, Am, F = (130.81, 164.81, 196.0), (196.0, 246.94, 293.66), (220.0, 261.63, 329.63), (174.61, 220.0, 261.63)
    roots = {C: 65.41, G: 49.0, Am: 55.0, F: 43.65}
    prog_ = [Am, F, C, G, Am, F, C, G, Am, C, C]                  # one chord a bar (2 s of score)
    for bi, ch in enumerate(prog_):
        t = bi * 2.0
        if t < 14 or t >= 18: add(pad(ch, cut=1200 if t < 4 else 1800), t, 0.30 if t < 4 else 0.22)
        if 14 <= t < 16: add(pad(ch, d=4.4 / SPEED, cut=1400), t, 0.34)              # the quote: pad only
        if 2 <= t < 14: add(bass(roots[ch], 1.9 / SPEED), t, 0.42 if t >= 4 else 0.3)
    for b in range(int(DUR / BEAT)):
        t = b * BEAT; bb = b % 4
        if t < 2: add(click(), t, 0.28); add(tone(2400, .02, 200), t, 0.07)          # a clock ticks
        if 4 <= t < 10 or 12 <= t < 14 or 16 <= t < 18: add(kick(), t, 0.95)
        if 10 <= t < 12 and bb == 0: add(kick(110, 44, .35), t, 0.5)
        if 4 <= t < 10 or 12 <= t < 14:
            add(hat(), t + 0.25, 0.15, 0.3); add(hat(0.03), t, 0.06, -0.3)
        if (6 <= t < 10) and bb in (1, 3): add(clap(), t, 0.42)
        if 6 <= t < 10 and bb in (1, 3): add(stab(prog_[int(t // 2)]), t + 0.25, 0.28, 0.2)
    add(buzz(), 0.0, 0.32); add(buzz(), 0.75, 0.3)                                    # Mom's message
    add(rattle(0.24 / SPEED), 2.5, 0.18); add(impact(1.1), 2.74, 0.9); add(metal(), 2.74, 0.22)   # CLOSED.
    add(riser(1.0 / SPEED), 3.0, 0.22)
    add(impact(), 4.0, 0.9); add(rattle(0.45 / SPEED), 4.0, 0.14); add(whoosh(0.45 / SPEED), 4.0, 0.25)  # OPEN.
    add(whoosh(0.6 / SPEED), 6.2, 0.35); add(ding(), 6.85, 0.24)                     # sent → arrived
    add(slice_(), 8.5, 0.5)
    for i in range(9): add(tone(1900 + 140 * i, .14, 30), 8.62 + .035 * i, 0.05, (-.5, .5)[i % 2])
    add(ding(1567.98), 9.0, 0.16)                                                      # less than a cent
    add(tone(880, .07, 30), 10.25, 0.2); add(tone(1318.5, .09, 25), 10.31, 0.2)        # the reply pops in
    for k in range(5):                                                                 # lub-dub
        t = 10.75 + k * BEAT
        if t < 12: add(kick(80, 36, .3), t, 0.55); add(kick(80, 36, .25), t + .13, 0.32)
    for k in range(4):                                                                 # NO …, one per beat
        t = 12 + k * BEAT; add(clap(), t, 0.5); add(impact(0.5), t, 0.35)
        add(hp(rng.standard_normal(int(.09 * SR)), 2500) * np.exp(-np.arange(int(.09 * SR)) / SR * 30), t + 0.2, 0.12)
    for c in range(sum(len(s) for s, _ in QUOTE)): add(click(), 14.05 + c / 34, 0.2 * rng.uniform(.6, 1))
    add(tone(659.25, 1.2, 3), 15.5, 0.06)
    add(riser(2.0 / SPEED), 16.0, 0.28)
    for k in range(2): add(clap(), 17.0 + k * 0.5, 0.35)
    for k in range(4): add(clap(), 17.5 + k * 0.125, 0.25 + 0.08 * k)
    add(impact(1.2), 18.0, 1.0); add(pad((130.81, 196.0, 261.63, 293.66, 329.63), d=4.6 / SPEED), 18.0, 0.5)
    add(ding(1046.5), 18.0, 0.18)
    for c in range(len("bitcoincash.org")): add(click(), 19 + c / 22, 0.2 * rng.uniform(.6, 1))
    mix_ /= np.abs(mix_).max() / 0.9; mix_ = np.tanh(1.8 * mix_) / np.tanh(1.8)     # loud and flat
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix_.T * 32767).astype("<i2").tobytes())

if __name__ == "__main__":
    if "--stills" in sys.argv:
        ts = [float(x) for x in arg("--stills", "").split(",")]
        cols = 4; tw, th = 270, 480; sheet = Image.new("RGB", (cols * tw, -(-len(ts) // cols) * th), "black")
        for i, t in enumerate(ts):
            im = frame(t * SPEED).resize((tw, th), BIC); ImageDraw.Draw(im).text((6, 4), f"{t:.2f}s", font=font(MONOB, 20), fill=(255, 0, 255))
            sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
        sheet.save(OUT / "stills.png"); print("stills →", OUT / "stills.png"); sys.exit()
    wav = OUT / "music.wav"; audio(wav); print("audio →", wav)
    meas = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(wav), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                           "-f", "null", "-"], capture_output=True, text=True).stderr          # pass 1: measure
    m = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
    AF = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,alimiter=limit=0.79:level=false")       # pass 2, in the encode
    mp4 = OUT / "sunday-5am.mp4"
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                            "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                            "-af", AF, "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                            "-shortest", "-t", str(LEN), "-movflags", "+faststart", str(mp4)], stdin=subprocess.PIPE)
    for i in range(round(LEN * FPS)):
        enc.stdin.write(frame(i * SPEED / FPS).tobytes())          # score time of this video frame
    enc.stdin.close(); enc.wait(); print("video →", mp4, "exit", enc.returncode)
