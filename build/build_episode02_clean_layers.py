#!/usr/bin/env python3
"""Clean-layer rebuild of CSCA Math Episode 02.

Fixes the visual defects reported by the owner:
- no AI/photo background behind semantic objects;
- opaque panels with correct z-order;
- all objects clipped/checked inside their parent containers;
- translucent shading composited on separate layers, never written as
  half-alpha pixels directly onto the final frame;
- circular avatar mask instead of a black square.

Audio, WAV-driven semantic beats, dynamic captions, duration and 30 FPS timing
are reused from build_episode02_animated.py.
"""
from __future__ import annotations

import bisect
import json
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_utils import (BLUE, FAINT, GOLD, LINE, NAVY, RED, TEAL, WHITE, font)
from build_episode02_animated import (
    ROOT, OUT, AUDIO, TEMPO, AVATAR, MASTER, FF,
    W, H, FPS, TARGET, OUTRO_HOLD, TITLES, BEATS,
    make_tempo_clips, build_audio, p, appeared, clamp, lerp,
)

CLEAN_MP4 = OUT / "CSCA_Math_02_Subsets_Complements_Clean.mp4"
CLEAN_TIMELINE = OUT / "clean_layer_timeline.json"
CLEAN_AUDIT = OUT / "clean_layer_audit.json"

PANEL = (14, 30, 50)
PANEL2 = (18, 43, 58)
FULL = (0, 0, W, H)
MAIN = (80, 180, 1200, 600)
CAPTION_TOP = 608
assert MAIN[3] < CAPTION_TOP

SEEN = set()
AUDIT = []
AVATAR_FULL = None


def mix(a, b, u):
    u = clamp(u)
    return tuple(int(round(a[i] * (1 - u) + b[i] * u)) for i in range(3))


def fc(color, a=1.0, base=PANEL):
    return mix(base, color, a)


def txt(d, xy, s, size, color, bold=True, stroke=0):
    d.text(xy, s, font=font(size, bold), fill=color,
           stroke_width=stroke, stroke_fill=(4, 9, 18))


def ctr(d, cx, cy, s, size, color, bold=True, stroke=0):
    f = font(size, bold)
    box = d.textbbox((0, 0), s, font=f)
    d.text((cx - (box[2] - box[0]) / 2, cy - (box[3] + box[1]) / 2), s,
           font=f, fill=color, stroke_width=stroke, stroke_fill=(4, 9, 18))


def fade_ctr(d, cx, cy, s, size, color, a, base=PANEL, bold=True, stroke=0,
             min_a=0.55):
    if a <= 0.01:
        return
    ctr(d, cx, cy, s, size, fc(color, max(min_a, a), base), bold, stroke)


def rnd(d, rect, r, fill, outline=None, width=1):
    d.rounded_rectangle(rect, r, fill=fill, outline=outline, width=width)


def ensure(rect, parent, label, scene):
    r = tuple(int(round(v)) for v in rect)
    q = tuple(int(round(v)) for v in parent)
    key = (scene, label, r, q)
    if key in SEEN:
        return
    SEEN.add(key)
    ok = (r[0] >= q[0] - 1 and r[1] >= q[1] - 1 and
          r[2] <= q[2] + 1 and r[3] <= q[3] + 1)
    AUDIT.append({"scene": scene, "label": label, "rect": list(r),
                  "parent": list(q), "within_parent": bool(ok)})
    assert ok, f"Layer overflow in scene {scene}: {label} {r} outside {q}"


def panel(d, parent, rect, label, color, a=1.0, scene=0):
    ensure(rect, parent, label or "panel", scene)
    if a < 0.01:
        return
    rnd(d, rect, 24, PANEL, fc(color, a, PANEL), 3)
    if label:
        ctr(d, (rect[0] + rect[2]) / 2, rect[1] + 26, label, 20,
            fc(color, a, PANEL), True)


def card(d, parent, x, y, value, color, a=1.0, scale=1.0, highlight=False,
         w=84, h=84, scene=0, label=None):
    w, h = int(w * scale), int(h * scale)
    rect = (x, y, x + w, y + h)
    ensure(rect, parent, label or f"card {value}", scene)
    if a < 0.01:
        return
    fill = fc((55, 45, 20) if highlight else PANEL2, a, PANEL)
    rnd(d, rect, 16, fill, fc(color, a, PANEL), 3)
    ctr(d, x + w / 2, y + h / 2, str(value), max(16, int(38 * scale)),
        fc(color, a, PANEL), True)


def move_card(d, parent, value, color, u, x0, y0, x1, y1, scene=0, **kw):
    u = clamp(u)
    if "alpha" in kw:
        kw["a"] = kw.pop("alpha")
    card(d, parent, lerp(x0, x1, u), lerp(y0, y1, u), value, color,
         scene=scene, **kw)


def chip(d, parent, cx, cy, label, color, a=1.0, size=20, scene=0):
    f = font(size, True)
    w = int(f.getlength(label)) + 40
    h = 44
    rect = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    ensure(rect, parent, f"chip {label}", scene)
    if a < 0.01:
        return
    rnd(d, rect, 22, fc(PANEL2, a, PANEL), fc(color, a, PANEL), 2)
    ctr(d, cx, cy, label, size, fc(color, a, PANEL), True)


def assemble(d, parent, cx, cy, full, a, size=32, color=WHITE, scene=0,
             base=PANEL):
    a = clamp(a)
    n = int(len(full) * a + 0.001)
    if n <= 0:
        return
    part = full[:n]
    f = font(size, True)
    w = f.getlength(part)
    h = size * 1.25
    rect = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    ensure(rect, parent, f"text {part[:12]}", scene)
    ctr(d, cx, cy, part, size, fc(color, a, base), True)


def mark(d, parent, cx, cy, kind, color=RED, a=1.0, r=16, scene=0):
    rect = (cx - r, cy - r, cx + r, cy + r)
    ensure(rect, parent, f"mark {kind}", scene)
    if a < 0.01:
        return
    c = fc(color, a, PANEL)
    if kind == "cross":
        d.line((cx - r, cy - r, cx + r, cy + r), fill=c, width=5)
        d.line((cx + r, cy - r, cx - r, cy + r), fill=c, width=5)
    else:
        d.line((cx - r, cy, cx - r / 3, cy + r / 2), fill=c, width=5)
        d.line((cx - r / 3, cy + r / 2, cx + r, cy - r / 2), fill=c, width=5)


def shade_outside(im, rect, ellipse_bbox, color, a, parent, scene):
    """Composite translucent shading on its own layer, then cut a clean hole."""
    ensure(rect, parent, "shade rect", scene)
    ensure(ellipse_bbox, parent, "shade hole", scene)
    if a <= 0.01:
        return im
    base = im.convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle(rect, 20, fill=color + (int(70 * a),))
    ld.ellipse(ellipse_bbox, fill=(0, 0, 0, 0))
    return Image.alpha_composite(base, layer).convert("RGB")


def make_base(t):
    im = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(im)
    grid = mix(NAVY, LINE, 0.22)
    off = int((t * 18.0) % 64)
    for x in range(-64 + off, W, 64):
        d.line((x, 0, x, H), fill=grid, width=1)
    for y in range(-64 + off, H, 64):
        d.line((0, y, W, y), fill=grid, width=1)

    glow = Image.new("RGB", (W, H), NAVY)
    gd = ImageDraw.Draw(glow)
    gx = int(880 + 48 * math.sin(t * 0.55))
    gy = int(300 + 30 * math.cos(t * 0.42))
    gd.ellipse((gx - 230, gy - 230, gx + 230, gy + 230),
               fill=mix(NAVY, TEAL, 0.10 + 0.025 * math.sin(t * 0.8)))
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    im = Image.blend(im, glow, 0.45)
    d = ImageDraw.Draw(im)
    for j in range(5):
        px = int(140 + j * 250 + 26 * math.sin(t * 0.75 + j * 1.3))
        py = int(160 + (j % 3) * 170 + 20 * math.cos(t * 0.62 + j * 0.9))
        d.ellipse((px - 3, py - 3, px + 3, py + 3),
                  fill=mix(NAVY, TEAL, 0.42))
    return im


def header(d, t, i):
    txt(d, (44, 32), "KNOWLUMO", 22, WHITE, True)
    txt(d, (44, 62), "CSCA MATH  ·  EPISODE 02", 16, FAINT, True)
    ctr(d, 640, 48, TITLES[i], 20, WHITE, True)
    txt(d, (1095, 39), f"{i + 1:02d} / 10", 17, FAINT, True)
    d.rounded_rectangle((44, 89, 1236, 94), 2, fill=mix(NAVY, LINE, 0.7))
    d.rounded_rectangle((44, 89, 44 + int(1192 * min(1.0, t / TARGET)), 94),
                        2, fill=TEAL)


def main_panel(d, scene):
    ensure(MAIN, FULL, "main panel", scene)
    rnd(d, MAIN, 24, PANEL, mix(PANEL, LINE, 0.8), 2)


def draw_scene_clean(im, i, t, b, scene_start, scene_end):
    s = i + 1
    d = ImageDraw.Draw(im)
    main_panel(d, s)

    if i == 0:
        fade_ctr(d, 640, 135, "SETS INSIDE SETS", 50, WHITE,
                 p(t, b, "title", 0.8), base=NAVY, stroke=3)
        pn = p(t, b, "nested", 1.1)
        U = (120, 210, 1160, 560)
        panel(d, MAIN, U, "UNIVERSAL BOX", BLUE, pn, s)
        bx = lerp(140, 200, pn)
        A = (bx, 270, bx + 560, 430)
        panel(d, U, A, "SMALLER SET", TEAL, pn, s)
        for j, v in enumerate([1, 2, 3]):
            pj = p(t, b, "small", 0.45, delay=j * 0.18)
            card(d, A, 260 + j * 140, 330, v, TEAL, pj, 0.72,
                 w=72, h=72, scene=s, label=f"A card {v}")
        for j, v in enumerate([1, 2, 3, 4, 5, 6]):
            pj = p(t, b, "large", 0.45, delay=j * 0.12)
            card(d, U, 170 + j * 170, 460, v, BLUE, pj, 0.66,
                 w=72, h=72, scene=s, label=f"U card {v}")
        if appeared(t, b, "nested"):
            ar = p(t, b, "nested", 1.4)
            x2 = lerp(760, 900, ar)
            d.line((760, 445, x2, 445), fill=fc(GOLD, ar, PANEL), width=4)
            d.polygon([(x2, 445), (x2 - 16, 437), (x2 - 16, 453)],
                      fill=fc(GOLD, ar, PANEL))
        for j, key in enumerate(["goal1", "goal2", "goal3"]):
            chip(d, MAIN, 240 + j * 400, 575,
                 ["SUBSET", "COMPLEMENT", "PRACTICE"][j],
                 GOLD if j == 2 else TEAL, p(t, b, key, 0.6), 18, s)

    elif i == 1:
        pd = p(t, b, "def", 1.0)
        fade_ctr(d, 640, 130, "A  ⊆  B", 56, TEAL, pd, base=NAVY)
        B = (120, 210, 1160, 560)
        panel(d, MAIN, B, "B", BLUE, 1.0, s)
        A = (160, 270, 720, 430)
        panel(d, B, A, "A", TEAL, p(t, b, "a_nums", 0.9), s)
        for j, v in enumerate([1, 2, 3]):
            pj = p(t, b, "a_nums", 0.4, delay=j * 0.18)
            card(d, A, 230 + j * 150, 330, v, TEAL, pj, 0.78,
                 w=80, h=80, scene=s, label=f"A card {v}")
        for j, v in enumerate([1, 2, 3, 4]):
            pj = p(t, b, "b_nums", 0.4, delay=j * 0.15)
            card(d, B, 180 + j * 220, 460, v, BLUE, pj, 0.72,
                 w=80, h=80, scene=s, label=f"B card {v}")
        pm = p(t, b, "move", 1.2)
        for j, v in enumerate([1, 2, 3]):
            move_card(d, B, v, GOLD, pm, 230 + j * 150 + 8, 338,
                      180 + j * 220 + 8, 468, scene=s,
                      alpha=pm, scale=0.72, w=80, h=80,
                      label=f"moving {v}")
        pe = p(t, b, "empty", 0.7)
        E = (900, 250, 1140, 400)
        panel(d, B, E, "∅", FAINT, pe, s)
        if appeared(t, b, "every"):
            mark(d, B, 1020, 425, "check", TEAL,
                 p(t, b, "every", 0.6), 18, s)
            chip(d, B, 1020, 470, "SUBSET OF EVERY SET", TEAL,
                 p(t, b, "every", 0.6), 15, s)

    elif i == 2:
        pp = p(t, b, "proper", 0.9)
        fade_ctr(d, 640, 130, "A  ⊊  B", 56, GOLD, pp, base=NAVY)
        B = (120, 210, 1160, 560)
        panel(d, MAIN, B, "B", BLUE, 1.0, s)
        A = (160, 270, 720, 430)
        panel(d, B, A, "A", TEAL, 1.0, s)
        for j, v in enumerate([1, 2, 3]):
            card(d, A, 230 + j * 150, 330, v, TEAL, 1.0, 0.78,
                 w=80, h=80, scene=s, label=f"A card {v}")
        pf = p(t, b, "four_new", 1.1)
        move_card(d, B, 4, GOLD, pf, 760, 390, 980, 390, scene=s,
                  alpha=pf, scale=0.8, w=80, h=80, highlight=True,
                  label="moving 4")
        peq = p(t, b, "equal", 0.9)
        EQ = (820, 250, 1120, 330)
        panel(d, B, EQ, "A = B", FAINT, peq, s)
        if peq > 0:
            fade_ctr(d, 970, 300, "=", 46, WHITE, peq)
            mark(d, EQ, 970, 300, "cross", RED,
                 p(t, b, "not_proper", 0.6), 24, s)
        L = (180, 460, 520, 540)
        R = (560, 460, 900, 540)
        panel(d, B, L, "⊆  CONTAINED OR EQUAL", TEAL,
              p(t, b, "underline", 0.7), s)
        panel(d, B, R, "⊊  STRICTLY SMALLER", GOLD,
              p(t, b, "strict", 0.7), s)
        chip(d, B, 1040, 500, "EQUALITY EXCLUDED", RED,
             p(t, b, "excludes", 0.6), 16, s)

    elif i == 3:
        ctr(d, 640, 130, "TWO SYMBOLS, TWO MEANINGS", 38, WHITE, True)
        L = (110, 210, 620, 500)
        R = (660, 210, 1170, 500)
        panel(d, MAIN, L, "CONTAINED OR EQUAL", TEAL, 1.0, s)
        panel(d, MAIN, R, "STRICTLY SMALLER", GOLD, 1.0, s)
        fade_ctr(d, 365, 320, "⊆", 100, TEAL,
                 p(t, b, "subseteq", 0.9))
        fade_ctr(d, 915, 320, "⊊", 100, GOLD,
                 p(t, b, "subsetneq", 0.9))
        ctr(d, 365, 435, "⊆", 30, WHITE, True)
        ctr(d, 915, 435, "⊊", 30, WHITE, True)
        STRIP = (520, 515, 760, 585)
        panel(d, MAIN, STRIP, "", FAINT, 1.0, s)
        ppl = p(t, b, "plain", 0.6)
        fade_ctr(d, 600, 550, "⊂ ?", 26, FAINT, ppl)
        mark(d, STRIP, 700, 550, "check", TEAL,
             p(t, b, "check_def", 0.6), 14, s)
        pm = p(t, b, "missing", 0.9)
        move_card(d, R, 1, RED, pm, 700, 430, 1080, 430, scene=s,
                  alpha=pm, scale=0.55, w=50, h=50, label="missing 1")
        fade_ctr(d, 365, 470, "TRUE  →  FALSE", 22, RED,
                 p(t, b, "false", 0.7))

    elif i == 4:
        U = (120, 210, 1160, 560)
        panel(d, MAIN, U, "U = { 1, 2, 3, 4, 5, 6 }", BLUE,
              p(t, b, "u", 0.8), s)
        pun = p(t, b, "u_nums", 1.0)
        xs = [170, 330, 490, 650, 810, 970]
        for j, v in enumerate([1, 2, 3, 4, 5, 6]):
            if v > 3 and appeared(t, b, "comp"):
                continue
            pj = p(t, b, "u_nums", 0.4, delay=j * 0.13)
            card(d, U, xs[j], 280, v, BLUE, pj * pun, 0.72,
                 w=80, h=80, scene=s, label=f"U card {v}")
        A = (160, 390, 700, 540)
        panel(d, U, A, "A = { 1, 2, 3 }", TEAL,
              p(t, b, "a_group", 0.9), s)
        for j, v in enumerate([1, 2, 3]):
            card(d, A, 230 + j * 150, 440, v, TEAL,
                 p(t, b, "a_group", 0.9), 0.66, w=70, h=70,
                 scene=s, label=f"A card {v}")
        REM = (780, 390, 1140, 540)
        panel(d, U, REM, "Aᶜ = { 4, 5, 6 }", GOLD,
              p(t, b, "comp", 1.1), s)
        pc = p(t, b, "comp", 1.1)
        for j, v in enumerate([4, 5, 6]):
            move_card(d, U, v, GOLD, pc, xs[j + 3] + 8, 288,
                      830 + j * 110, 440, scene=s,
                      alpha=pc, scale=0.66, w=70, h=70,
                      highlight=True, label=f"complement {v}")
        ctr(d, 950, 515, "WHAT REMAINS IN U", 18,
            fc(GOLD, p(t, b, "remains", 0.8), PANEL), True)

    elif i == 5:
        ctr(d, 640, 130, "THE COMPLEMENT REGION", 42, WHITE, True)
        U = (180, 210, 1100, 560)
        panel(d, MAIN, U, "U", BLUE, p(t, b, "rect", 1.0), s)
        ELL = (430, 260, 850, 500)
        psh = p(t, b, "shade", 1.1)
        im2 = shade_outside(im, U, ELL, GOLD, psh, MAIN, s)
        if im2 is not im:
            im.paste(im2)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle(U, 20, outline=BLUE, width=4)
        d.ellipse(ELL, outline=TEAL, width=5)
        ctr(d, 640, 240, "U", 22, BLUE, True)
        ctr(d, 640, 380, "A", 46, TEAL, True)
        fade_ctr(d, 990, 300, "Aᶜ", 38, GOLD, psh)
        chip(d, U, 340, 525, "A ∩ Aᶜ = ∅", WHITE,
             p(t, b, "never", 0.7), 17, s)
        chip(d, U, 930, 525, "A ∪ Aᶜ = U", GOLD,
             p(t, b, "whole", 0.7), 17, s)
        pbo = p(t, b, "boundary", 0.6)
        if pbo > 0:
            d.rounded_rectangle(U, 20, outline=fc(BLUE, pbo, PANEL), width=6)

    elif i == 6:
        ctr(d, 640, 130, "ORDER MATTERS", 42, WHITE, True)
        A_ELL = (180, 220, 620, 500)
        B_ELL = (660, 220, 1100, 500)
        ensure(A_ELL, MAIN, "circle A", s)
        ensure(B_ELL, MAIN, "circle B", s)
        pdif = p(t, b, "diff", 0.8)
        d.ellipse(A_ELL, outline=fc(TEAL, pdif, PANEL), width=5)
        d.ellipse(B_ELL, outline=fc(BLUE, pdif, PANEL), width=5)
        ctr(d, 250, 195, "A", 26, TEAL, True)
        ctr(d, 1030, 195, "B", 26, BLUE, True)
        pk = p(t, b, "keep", 1.0)
        pos = [(260, 310, 1, TEAL), (540, 310, 2, FAINT),
               (700, 310, 3, FAINT), (940, 310, 4, BLUE)]
        for j, (x, y, v, col) in enumerate(pos):
            pj = p(t, b, "keep", 0.4, delay=j * 0.14)
            card(d, MAIN, x, y, v, col, pj * pk, 0.66,
                 w=70, h=70, scene=s, label=f"diff card {v}")
        pn = p(t, b, "notin", 0.8)
        mark(d, MAIN, 575, 345, "cross", RED, pn, 16, s)
        mark(d, MAIN, 735, 345, "cross", RED, pn, 16, s)
        LT = (160, 510, 600, 575)
        RT = (680, 510, 1120, 575)
        p1 = p(t, b, "result1", 0.9)
        p2 = p(t, b, "result2", 0.9)
        panel(d, MAIN, LT, "", TEAL, p1, s)
        panel(d, MAIN, RT, "", BLUE, p2, s)
        move_card(d, MAIN, 1, TEAL, p1, 260, 310, 210, 525, scene=s,
                  alpha=p1, scale=0.5, w=50, h=50, highlight=True,
                  label="result 1")
        fade_ctr(d, 300, 530, "A \\ B", 18, TEAL, p1)
        fade_ctr(d, 430, 555, "= { 1 }", 22, TEAL, p1)
        move_card(d, MAIN, 4, BLUE, p2, 940, 310, 730, 525, scene=s,
                  alpha=p2, scale=0.5, w=50, h=50, highlight=True,
                  label="result 4")
        fade_ctr(d, 820, 530, "B \\ A", 18, BLUE, p2)
        fade_ctr(d, 950, 555, "= { 4 }", 22, BLUE, p2)
        fade_ctr(d, 640, 590, "A COMPLEMENT REFERS TO U", 16, GOLD,
                 p(t, b, "u_remind", 0.6))
        po = p(t, b, "order", 0.6)
        if po > 0:
            x2 = 640 - 90 * po
            d.line((640, 495, x2, 495), fill=fc(GOLD, po, PANEL), width=4)
            d.polygon([(x2, 495), (x2 + 18, 487), (x2 + 18, 503)],
                      fill=fc(GOLD, po, PANEL))

    elif i == 7:
        fade_ctr(d, 640, 130, "YOUR TURN: CHOOSE ONE ANSWER", 36, WHITE,
                 p(t, b, "practice", 0.7), base=NAVY, stroke=2)
        pu = p(t, b, "u", 0.9)
        for j, v in enumerate([1, 2, 3, 4, 5, 6]):
            pj = p(t, b, "u", 0.35, delay=j * 0.10)
            card(d, MAIN, 300 + j * 115, 205, v, BLUE, pj * pu, 0.5,
                 w=55, h=55, scene=s, label=f"U card {v}")
        AB = (150, 260, 620, 370)
        BB = (660, 260, 1130, 370)
        panel(d, MAIN, AB, "A = { 1, 2, 3 }", TEAL,
              p(t, b, "a", 0.8), s)
        panel(d, MAIN, BB, "B = { 2, 3, 4 }", BLUE,
              p(t, b, "b", 0.8), s)
        for j, v in enumerate([1, 2, 3]):
            card(d, AB, 220 + j * 120, 320, v, TEAL,
                 p(t, b, "a", 0.8), 0.48, w=50, h=50,
                 scene=s, label=f"A card {v}")
        for j, v in enumerate([2, 3, 4]):
            card(d, BB, 730 + j * 120, 320, v, BLUE,
                 p(t, b, "b", 0.8), 0.48, w=50, h=50,
                 scene=s, label=f"B card {v}")
        fade_ctr(d, 640, 395, "WHICH STATEMENT IS TRUE?", 26, GOLD,
                 p(t, b, "question", 0.6))
        opts = [("opt_a", "A", "A ⊆ B"), ("opt_b", "B", "Aᶜ = { 4, 5, 6 }"),
                ("opt_c", "C", "A \\ B = { 2, 3 }"), ("opt_d", "D", "B ⊆ A")]
        for j, (key, lab, val) in enumerate(opts):
            pj = p(t, b, key, 0.55)
            x, y = 90 + (j % 2) * 570, 420 + (j // 2) * 70
            rect = (x, y, x + 530, y + 60)
            ensure(rect, MAIN, f"option {lab}", s)
            if pj > 0.01:
                rnd(d, rect, 16, fc(PANEL2, pj, PANEL),
                    fc(LINE, pj, PANEL), 2)
                fade_ctr(d, x + 40, y + 30, lab, 24, GOLD, pj)
                fade_ctr(d, x + 290, y + 30, val, 22, WHITE, pj)
        chip(d, MAIN, 640, 570, "PAUSE THE VIDEO TO SOLVE", TEAL,
             p(t, b, "pause", 0.7), 19, s)

    elif i == 8:
        ctr(d, 640, 130, "LET US CHECK EACH OPTION", 36, WHITE, True)
        rows = [
            ("row_a", "A ⊆ B", "FALSE — 1 ∉ B", RED),
            ("row_b", "Aᶜ = { 4, 5, 6 }", "TRUE", TEAL),
            ("row_c", "A \\ B = { 2, 3 }", "FALSE — A \\ B = { 1 }", RED),
            ("row_d", "B ⊆ A", "FALSE — 4 ∉ A", RED),
        ]
        for j, (key, expr, verdict, col) in enumerate(rows):
            pj = p(t, b, key, 0.6)
            y = 205 + j * 72
            rect = (110, y, 1170, y + 60)
            ensure(rect, MAIN, f"row {j+1}", s)
            if pj > 0.01:
                rnd(d, rect, 16, fc(PANEL2, pj, PANEL),
                    fc(col, pj, PANEL), 2)
                fade_ctr(d, 400, y + 30, expr, 24, WHITE, pj)
                if key != "row_b" or appeared(t, b, "true"):
                    fade_ctr(d, 880, y + 30, verdict, 22, col, pj)
                if key == "row_b":
                    if appeared(t, b, "true"):
                        mark(d, rect, 1130, y + 30, "check", TEAL,
                             p(t, b, "true", 0.5), 14, s)
                else:
                    mark(d, rect, 1130, y + 30, "cross", RED, pj, 14, s)
        STRIP = (110, 500, 1170, 585)
        panel(d, MAIN, STRIP, "VISUAL CHECK", FAINT, 1.0, s)
        for j, v in enumerate([4, 5, 6]):
            card(d, STRIP, 170 + j * 90, 525, v, GOLD,
                 p(t, b, "row_b", 0.8), 0.45, w=45, h=45,
                 highlight=True, scene=s, label=f"complement {v}")
        mark(d, STRIP, 500, 548, "cross", RED,
             p(t, b, "not23", 0.6), 12, s)
        mark(d, STRIP, 610, 548, "cross", RED,
             p(t, b, "not23", 0.6), 12, s)
        card(d, STRIP, 950, 525, 1, RED,
             p(t, b, "one", 0.6), 0.45, w=45, h=45,
             scene=s, label="missing 1")
        card(d, STRIP, 1030, 525, 4, RED,
             p(t, b, "four", 0.6), 0.45, w=45, h=45,
             scene=s, label="missing 4")
        ANSW = (470, 510, 810, 575)
        pans = p(t, b, "answer", 0.7)
        ensure(ANSW, MAIN, "answer card", s)
        if pans > 0.01:
            rnd(d, ANSW, 24, fc(GOLD, pans, PANEL), None)
            fade_ctr(d, 640, 542, "ANSWER B", 30, NAVY, pans)

    else:
        fade_ctr(d, 640, 130, "THREE IDEAS TO KEEP", 40, WHITE,
                 p(t, b, "recap", 0.8), base=NAVY)
        cards = [(100, 210, 420, 470), (470, 210, 790, 470),
                 (840, 210, 1160, 470)]
        labels = [("SUBSET", TEAL), ("COMPLEMENT", GOLD),
                  ("DIFFERENCE", BLUE)]
        for j, (rect, (label, col)) in enumerate(zip(cards, labels)):
            key = ["subset", "comp", "diff"][j]
            panel(d, MAIN, rect, label, col,
                  p(t, b, key, 0.7, delay=j * 0.12), s)
        ps = p(t, b, "subset", 0.9)
        U1 = (130, 300, 390, 440)
        A1 = (170, 340, 330, 420)
        panel(d, cards[0], U1, "U", BLUE, ps, s)
        bx = lerp(140, 170, ps)
        panel(d, U1, (bx, 340, bx + 160, 420), "A", TEAL, ps, s)
        pc = p(t, b, "comp", 0.9)
        U2 = (500, 300, 760, 440)
        E2 = (560, 320, 700, 420)
        panel(d, cards[1], U2, "U", BLUE, pc, s)
        im2 = shade_outside(im, U2, E2, GOLD, pc * 0.6, cards[1], s)
        if im2 is not im:
            im.paste(im2)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle(U2, 18, outline=BLUE, width=3)
        d.ellipse(E2, outline=TEAL, width=4)
        pdif = p(t, b, "diff", 0.9)
        for j, v in enumerate([1, 2, 3]):
            card(d, cards[2], 880 + j * 70, 330, v, BLUE, pdif, 0.45,
                 w=45, h=45, highlight=(v == 1), scene=s,
                 label=f"diff {v}")
        mark(d, cards[2], 1020, 352, "cross", RED, pdif, 12, s)
        chip(d, MAIN, 640, 510, "NEXT LESSON", TEAL,
             p(t, b, "next", 0.6), 18, s)
        fade_ctr(d, 640, 555, "INTERVAL NOTATION & INEQUALITIES", 24, GOLD,
                 p(t, b, "intervals", 0.6))
        fade_ctr(d, 640, 585, "KEEP EXPLORING, ONE IDEA AT A TIME", 18, FAINT,
                 p(t, b, "thanks", 0.6))

    return im


def draw_captions(im, t, caption_state, global_words, outro_start):
    if t >= outro_start:
        return
    group, active = caption_state(t)
    if not group:
        return
    visible = [(j, global_words[j]["word"]) for j in group["indices"] if j <= active]
    if not visible:
        return
    d = ImageDraw.Draw(im)
    rnd(d, (80, 608, 1200, 694), 20, (5, 12, 24), mix((5, 12, 24), LINE, 0.5), 2)
    f = font(29, True)
    lines, cur = [], []
    for idx, word in visible:
        trial = " ".join([w for _, w in cur + [(idx, word)]])
        if cur and f.getlength(trial) > 1010:
            lines.append(cur)
            cur = [(idx, word)]
        else:
            cur.append((idx, word))
    if cur:
        lines.append(cur)
    lines = lines[:2]
    line_y = 625 if len(lines) == 2 else 640
    for line in lines:
        widths = [f.getlength(w) for _, w in line]
        total = sum(widths) + 14 * (len(line) - 1)
        x = (W - total) / 2
        for (idx, word), pw in zip(line, widths):
            col = TEAL if idx == active else WHITE
            d.text((x, line_y), word, font=f, fill=col,
                   stroke_width=2, stroke_fill=(3, 8, 16))
            x += pw + 14
        line_y += 41


def draw_outro(im, t, outro_start, b9):
    local = t - outro_start
    fade_in = min(1.0, max(0.0, local / 0.8))
    fade_out = min(1.0, max(0.0, (TARGET - t) / 0.8))
    alpha = min(fade_in, fade_out)
    d = ImageDraw.Draw(im)
    txt(d, (54, 42), "KNOWLUMO", 22, WHITE, True)
    txt(d, (54, 72), "CSCA MATH  ·  EPISODE 02", 16, FAINT, True)
    rnd(d, (1088, 40, 1226, 82), 20, PANEL2, TEAL, 2)
    ctr(d, 1157, 61, "THANK YOU", 16, TEAL, True)

    pulse = 1.0 + 0.018 * math.sin(2 * math.pi * local / 2.4)
    glow = Image.new("RGB", (W, H), NAVY)
    gd = ImageDraw.Draw(glow)
    r = int(175 * pulse)
    gd.ellipse((640 - r, 292 - r, 640 + r, 292 + r),
               fill=mix(NAVY, TEAL, 0.14))
    glow = glow.filter(ImageFilter.GaussianBlur(24))
    im = Image.blend(im, glow, 0.55)
    d = ImageDraw.Draw(im)

    pt = p(t, b9, "thanks", 0.8)
    scale = 0.82 + 0.18 * min(1.0, local / 0.9)
    size = int(290 * scale * pulse)
    av = AVATAR_FULL.resize((size, size), Image.Resampling.LANCZOS).convert("RGB")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    im.paste(av, (640 - size // 2, 292 - size // 2), mask)
    d = ImageDraw.Draw(im)

    ps = p(t, b9, "subscribe", 0.7)
    if ps > 0.05:
        y = 470 + int((1 - ps) * 18)
        rnd(d, (455, y, 825, y + 64), 32, fc(GOLD, ps, NAVY), None)
        ctr(d, 640, y + 32, "SUBSCRIBE", 31, fc(NAVY, ps, NAVY), True)
    pe = p(t, b9, "explore", 0.7)
    fade_ctr(d, 640, 558, "MORE VISUAL LESSONS", 24, WHITE, pe, base=NAVY)
    if alpha < 1.0:
        dark = Image.new("RGB", (W, H), (4, 9, 18))
        im = Image.blend(dark, im, alpha)
    return im


def main():
    global AVATAR_FULL
    make_tempo_clips()
    (sr, global_words, groups, starts, caption_state, scenes,
     scene_beats, scene_word_lists, outro_start) = build_audio()
    AVATAR_FULL = Image.open(AVATAR).convert("RGBA").resize((320, 320), Image.Resampling.LANCZOS)

    scene_starts = [s["start"] for s in scenes]
    answer_reveal = scene_beats[8]["answer"]
    practice_end = scenes[7]["end"]
    solution_start = scenes[8]["start"]
    assert practice_end < answer_reveal < scenes[8]["end"]
    assert MAIN[3] < CAPTION_TOP

    total_frames = int(round(TARGET * FPS))
    cmd = [FF, "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(MASTER),
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-profile:v", "high",
           "-pix_fmt", "yuv420p", "-r", str(FPS), "-video_track_timescale", "15360",
           "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
           "-t", f"{TARGET:.3f}", "-movflags", "+faststart", str(CLEAN_MP4)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for f in range(total_frames):
            t = f / FPS
            im = make_base(t)
            if t < outro_start:
                i = max(0, min(len(scenes) - 1, bisect.bisect_right(scene_starts, t) - 1))
                header(ImageDraw.Draw(im), t, i)
                im = draw_scene_clean(im, i, t, scene_beats[i], scenes[i]["start"], scenes[i]["end"])
                draw_captions(im, t, caption_state, global_words, outro_start)
                frame = im
            else:
                frame = draw_outro(im, t, outro_start, scene_beats[9])
            proc.stdin.write(frame.tobytes())
    finally:
        proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("FFmpeg encoding failed")

    base_tl = json.loads((OUT / "animation_timeline.json").read_text())
    CLEAN_TIMELINE.write_text(json.dumps({
        **base_tl,
        "status": "animated draft",
        "file": CLEAN_MP4.name,
        "clean_layers": {
            "background_source": "procedural grid only",
            "ai_photo_background_in_video": False,
            "opaque_panels": True,
            "clipped_objects": True,
            "translucent_effects_on_separate_layers": True,
            "circular_avatar_mask": True,
            "z_index_order": ["background", "main_panel", "nested_panels",
                              "objects", "labels", "outro", "captions"],
        },
        "answer_reveal_at": round(answer_reveal, 3),
        "practice_question_end": round(practice_end, 3),
        "solution_scene_start": round(solution_start, 3),
        "published": False,
    }, indent=2), encoding="utf-8")

    CLEAN_AUDIT.write_text(json.dumps({
        "status": "passed",
        "file": CLEAN_MP4.name,
        "main_panel": list(MAIN),
        "caption_top": CAPTION_TOP,
        "checked_objects": len(AUDIT),
        "violations": sum(1 for a in AUDIT if not a["within_parent"]),
        "checks": AUDIT,
    }, indent=2), encoding="utf-8")

    dec = subprocess.run([FF, "-v", "error", "-i", str(CLEAN_MP4), "-f", "null", "-"],
                         capture_output=True, text=True)
    if dec.returncode != 0:
        raise RuntimeError(f"Full decode failed: {dec.stderr}")
    print(f"Wrote {CLEAN_MP4}")
    print(f"Duration: {TARGET:.2f}s | {total_frames} frames @ {FPS} FPS")
    print(f"Layer bounds checked: {len(AUDIT)} | violations: 0")
    print("Full decode passed.")


if __name__ == "__main__":
    main()
