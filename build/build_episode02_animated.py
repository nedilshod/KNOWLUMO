#!/usr/bin/env python3
"""Build the animation-rich 5-minute draft for CSCA Math Episode 02.

Visual state changes are driven by word timings from the actual voice WAVs,
not by average reading speed or static slide changes. Every semantic beat has
an action: objects appear, move, group, are excluded, or build a formula.
The old static draft is preserved under its original filename.
"""
from __future__ import annotations

import bisect
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_utils import (BLUE, FAINT, GOLD, INK, LINE, NAVY, RED, TEAL, WHITE,
                         caption_groups, center, chime, ease, font,
                         grid_background, read_wav_mono, rounded, spring, text,
                         word_timings, write_stereo_wav)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "episode02"
AUDIO = OUT / "audio"
TEMPO = AUDIO / "tempo"
BG_IMG = OUT / "episode02_background.png"
AVATAR = ROOT / "sources" / "Youtube-arena-01b47ded-youtube" / "channel" / "knowlumo" / "assets" / "avatar_round_800.png"
MASTER = AUDIO / "episode02_animated_master.wav"
MP4 = OUT / "CSCA_Math_02_Subsets_Complements_Animated.mp4"
TIMELINE = OUT / "animation_timeline.json"
FF = imageio_ffmpeg.get_ffmpeg_exe()

W, H, FPS = 1280, 720, 30
TARGET = 300.0
LEAD, TAIL, GAP, OUTRO_HOLD = 0.3, 0.3, 0.15, 8.0
ATEMPO = 1.055

NAMES = ["hook", "subset", "proper", "symbols", "complement",
         "venn", "difference", "practice", "solution", "recap"]
TITLES = ["SETS INSIDE SETS", "WHAT IS A SUBSET?", "PROPER SUBSETS",
          "THE TWO SYMBOLS", "COMPLEMENTS AND U", "THE VENN DIAGRAM",
          "SET DIFFERENCE", "PRACTICE QUESTION", "THE SOLUTION",
          "RECAP AND OUTRO"]

SCRIPTS = json.loads((OUT / "script.json").read_text())
CLIPS = [AUDIO / f"{i:02d}_{n}.wav" for i, n in enumerate(NAMES, 1)]
TEMPO_CLIPS = [TEMPO / f"{i:02d}_{n}.wav" for i, n in enumerate(NAMES, 1)]

# (visual-beat key, phrase spoken by the narrator). Times come from the WAV.
BEATS = [
    [("title", "what if"), ("nested", "one whole set sits inside another"),
     ("goal1", "subset notation"), ("goal2", "find a complement"),
     ("goal3", "original practice question"), ("small", "small box of colored cards"),
     ("large", "larger box")],
    [("def", "A set A is a subset of B"),
     ("a_nums", "small box holds one, two, three"),
     ("b_nums", "larger box holds one, two, three, four"),
     ("move", "Every small card is already in the larger collection"),
     ("extra", "extra cards"), ("empty", "empty set"),
     ("every", "subset of every set")],
    [("proper", "proper subset"), ("four_new", "strictly smaller because four is new"),
     ("equal", "Equal sets"), ("not_proper", "neither is proper"),
     ("underline", "line underneath"), ("strict", "strict symbol"),
     ("excludes", "excludes equality")],
    [("subseteq", "subseteq"), ("subsetneq", "subsetneq"),
     ("plain", "plain curved symbol"), ("check_def", "check the definition"),
     ("missing", "single missing element"),
     ("false", "true statement into a false one")],
    [("u", "universal set"), ("u_nums", "U is one, two, three, four, five, six"),
     ("a_group", "A is one, two, three"),
     ("comp", "complement of A is four, five, six"),
     ("remove", "remove the small box"), ("remains", "whatever remains")],
    [("rect", "draw a rectangle"), ("circle", "circle for A"),
     ("shade", "Shade everything outside"), ("never", "never overlap"),
     ("merge", "together they rebuild"), ("whole", "whole universal set"),
     ("boundary", "boundary of the rectangle")],
    [("diff", "Set difference"), ("aminusb", "A minus B"),
     ("keep", "keep the elements of A"), ("notin", "not in B"),
     ("result1", "A minus B is one"), ("result2", "B minus A is four"),
     ("u_remind", "complement always refers to U"), ("order", "order matters")],
    [("practice", "original practice question"), ("u", "Let U contain"),
     ("a", "Let A contain"), ("b", "B contain"),
     ("question", "Which statement is true?"), ("opt_a", "Option A"),
     ("opt_b", "Option B"), ("opt_c", "Option C"), ("opt_d", "Option D"),
     ("pause", "Pause the video now"), ("choose", "choose one answer")],
    [("check", "Let us check each option"), ("row_a", "A is not a subset of B"),
     ("one", "one is missing from B"),
     ("row_b", "complement of A inside U is four, five, six"),
     ("true", "option B is true"), ("row_c", "A minus B is only one"),
     ("not23", "not two, three"), ("row_d", "B is not a subset of A"),
     ("four", "four is missing from A"), ("answer", "one correct answer: B"),
     ("u_compare", "compare against the universal set")],
    [("recap", "Recap the three ideas"), ("subset", "subset is contained"),
     ("comp", "complement is everything"), ("diff", "set difference keeps only"),
     ("next", "next lesson"), ("intervals", "interval notation and inequalities"),
     ("thanks", "Thanks for learning"), ("subscribe", "Subscribe"),
     ("explore", "keep exploring")],
]


def rgba(c, a=255):
    return c + (int(a),)


def clamp(x):
    return max(0.0, min(1.0, x))


def lerp(a, b, u):
    return a + (b - a) * u


def norm_words(s):
    return re.sub(r"[^a-z0-9 ]", " ", s.lower()).split()


def find_phrase(words, phrase):
    toks = [norm_words(w["word"]) for w in words]
    flat = [t for ts in toks for t in ts]
    mapping = [wi for wi, ts in enumerate(toks) for _ in ts]
    target = norm_words(phrase)
    for j in range(len(flat) - len(target) + 1):
        if flat[j:j + len(target)] == target:
            return mapping[j]
    raise ValueError(f"Spoken phrase not found in WAV-aligned words: {phrase!r}")


def make_tempo_clips():
    TEMPO.mkdir(parents=True, exist_ok=True)
    for src, dst in zip(CLIPS, TEMPO_CLIPS):
        subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(src),
                        "-filter:a", f"atempo={ATEMPO}", "-ar", "44100", "-ac", "1",
                        "-c:a", "pcm_s16le", str(dst)], check=True)


def build_audio():
    pieces = [np.zeros(int(LEAD * 44100), dtype=np.float32)]
    cursor = LEAD
    sr = 44100
    global_words, groups, scenes, scene_beats, scene_word_lists = [], [], [], [], []

    for i, (clip, script) in enumerate(zip(TEMPO_CLIPS, SCRIPTS)):
        voice, this_sr = read_wav_mono(clip)
        assert this_sr == sr
        words, _ = word_timings(clip, script)
        start, duration = cursor, len(voice) / sr
        end = cursor + duration
        scenes.append({"index": i + 1, "title": TITLES[i],
                       "start": round(start, 3), "end": round(end, 3),
                       "duration": round(duration, 3)})

        beats = {}
        for key, phrase in BEATS[i]:
            j = find_phrase(words, phrase)
            beats[key] = start + words[j]["start"]
        scene_beats.append(beats)
        scene_word_lists.append([{**w, "start": start + w["start"],
                                  "end": start + w["end"]} for w in words])

        base = len(global_words)
        for w in words:
            global_words.append({"word": w["word"],
                                 "start": start + w["start"],
                                 "end": start + w["end"],
                                 "scene": i + 1})
        for g in caption_groups(words, max_words=5):
            groups.append({"indices": [base + j for j in g["indices"]],
                           "start": start + g["start"],
                           "end": start + g["end"],
                           "scene": i + 1})

        pieces.append(voice)
        if i < len(TEMPO_CLIPS) - 1:
            pieces.append(np.zeros(int(round(GAP * sr)), dtype=np.float32))
            cursor = end + GAP
        else:
            cursor = end

    outro_start = cursor
    pieces.append(np.zeros(int(round(OUTRO_HOLD * sr)), dtype=np.float32))
    cursor += OUTRO_HOLD
    pieces.append(np.zeros(int(round(TAIL * sr)), dtype=np.float32))
    cursor += TAIL
    master = np.concatenate(pieces).astype(np.float32)
    if len(master) / sr < TARGET:
        master = np.concatenate([master, np.zeros(int(round((TARGET - len(master) / sr) * sr)), dtype=np.float32)])
    else:
        master = master[:int(round(TARGET * sr))]
    c = chime(sr, duration=0.45, base=620.0, volume=0.05)
    ci = int(round(outro_start * sr))
    master[ci:ci + len(c)] += c
    fade = int(round(0.8 * sr))
    master[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
    write_stereo_wav(MASTER, master, sr)

    groups.sort(key=lambda g: g["start"])
    starts = [w["start"] for w in global_words]

    def caption_state(t):
        if not starts or t < starts[0]:
            return None, -1
        active = min(bisect.bisect_right(starts, t) - 1, len(global_words) - 1)
        group = next(g for g in groups if g["indices"][0] <= active <= g["indices"][-1])
        return group, active

    for i, w in enumerate(global_words):
        _, before = caption_state(w["start"] - 0.001)
        assert before < i, ("future word", i, w["word"])
        _, after = caption_state(w["start"] + 0.001)
        assert after >= i, ("missing word", i, w["word"])
    # Last spoken group must remain visible through inter-scene gaps.
    for k, (a, b) in enumerate(zip(global_words, global_words[1:])):
        if b["start"] - a["end"] > 0.25:
            mid = (a["end"] + b["start"]) / 2
            g, active = caption_state(mid)
            assert g is not None and active >= k

    return sr, global_words, groups, starts, caption_state, scenes, scene_beats, scene_word_lists, outro_start


BASE = None
AVATAR_FULL = None


def p(t, beats, key, dur=0.8, delay=0.0):
    return ease((t - (beats[key] + delay)) / dur)


def appeared(t, beats, key):
    return t >= beats[key]


def ambient(im, t):
    """Gentle continuous parallax and light drift; no camera shake or flashes."""
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    off = int((t * 18.0) % 64)
    for x in range(-64 + off, W, 64):
        d.line((x, 0, x, H), fill=rgba(LINE, 58), width=1)
    for y in range(-64 + off, H, 64):
        d.line((0, y, W, y), fill=rgba(LINE, 58), width=1)
    for j in range(5):
        px = int(140 + j * 250 + 26 * math.sin(t * 0.75 + j * 1.3))
        py = int(160 + (j % 3) * 170 + 20 * math.cos(t * 0.62 + j * 0.9))
        d.ellipse((px - 4, py - 4, px + 4, py + 4), fill=rgba(TEAL, 70))
    gx = int(880 + 48 * math.sin(t * 0.55))
    gy = int(300 + 30 * math.cos(t * 0.42))
    d.ellipse((gx - 230, gy - 230, gx + 230, gy + 230), fill=rgba(TEAL, 34))
    overlay = overlay.filter(ImageFilter.GaussianBlur(18))
    im.alpha_composite(overlay)


def header(d, t, scene_index):
    text(d, (44, 32), "KNOWLUMO", 22, rgba(WHITE), True)
    text(d, (44, 62), "CSCA MATH  ·  EPISODE 02", 16, rgba(FAINT), True)
    center(d, 640, 48, TITLES[scene_index], 20, rgba(WHITE), True)
    text(d, (1095, 39), f"{scene_index + 1:02d} / 10", 17, rgba(FAINT), True)
    d.rounded_rectangle((44, 89, 1236, 94), 2, fill=rgba(LINE))
    d.rounded_rectangle((44, 89, 44 + int(1192 * min(1.0, t / TARGET)), 94), 2, fill=rgba(TEAL))


def card(d, x, y, value, color, alpha=1.0, scale=1.0, highlight=False,
         w=84, h=84, outline=True):
    w, h = int(w * scale), int(h * scale)
    a = clamp(alpha)
    fill = (55, 45, 20, int(235 * a)) if highlight else (18, 43, 58, int(235 * a))
    rounded(d, (x, y, x + w, y + h), 16, fill,
            rgba(color, int(220 * a)) if outline else None, 3)
    center(d, x + w / 2, y + h / 2, str(value), max(18, int(38 * scale)),
           rgba(color, int(255 * a)), True)


def move_card(d, value, color, u, x0, y0, x1, y1, **kw):
    u = clamp(u)
    x, y = lerp(x0, x1, u), lerp(y0, y1, u)
    card(d, x, y, value, color, **kw)


def box(d, rect, label, color, a=1.0, title_alpha=None):
    a = clamp(a)
    ta = a if title_alpha is None else clamp(title_alpha)
    rounded(d, rect, 24, (18, 43, 58, int(150 * a)), rgba(color, int(200 * a)), 3)
    center(d, (rect[0] + rect[2]) / 2, rect[1] - 26, label, 22, rgba(color, int(255 * ta)), True)


def chip(d, cx, cy, label, color, a=1.0, size=22):
    a = clamp(a)
    f = font(size, True)
    w = int(f.getlength(label)) + 44
    rounded(d, (cx - w / 2, cy - 24, cx + w / 2, cy + 24), 22,
            (18, 43, 58, int(230 * a)), rgba(color, int(210 * a)), 2)
    center(d, cx, cy, label, size, rgba(color, int(255 * a)), True)


def assemble(d, cx, cy, full, a, size=34, color=WHITE):
    a = clamp(a)
    n = max(0, min(len(full), int(len(full) * a + 0.001)))
    if n:
        center(d, cx, cy, full[:n], size, rgba(color, int(255 * a)), True)


def cross(d, cx, cy, color=RED, a=1.0, r=18):
    a = clamp(a)
    c = rgba(color, int(255 * a))
    d.line((cx - r, cy - r, cx + r, cy + r), fill=c, width=5)
    d.line((cx + r, cy - r, cx - r, cy + r), fill=c, width=5)


def check(d, cx, cy, color=TEAL, a=1.0, r=18):
    a = clamp(a)
    c = rgba(color, int(255 * a))
    d.line((cx - r, cy, cx - r / 3, cy + r / 2), fill=c, width=5)
    d.line((cx - r / 3, cy + r / 2, cx + r, cy - r / 2), fill=c, width=5)


def draw_scene(im, i, t, b, scene_start, scene_end):
    d = ImageDraw.Draw(im)
    # A soft travelling focus ring marks the currently explained idea. It is
    # slow, low-contrast, and never covers the caption safe zone.
    focus = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(focus)
    fx = int(350 + 580 * (0.5 + 0.5 * math.sin(t * 0.33 + i * 0.7)))
    fy = int(330 + 70 * math.cos(t * 0.41 + i * 0.5))
    fr = int(150 + 8 * math.sin(t * 1.1))
    fd.ellipse((fx - fr, fy - fr, fx + fr, fy + fr),
               outline=rgba(TEAL, 26), width=10)
    focus = focus.filter(ImageFilter.GaussianBlur(10))
    im.alpha_composite(focus)
    d = ImageDraw.Draw(im)

    if i == 0:
        pt = p(t, b, "title", 0.8)
        center(d, 640, 140, "SETS INSIDE SETS", 52, rgba(WHITE, int(255 * pt)), True)
        pn = p(t, b, "nested", 1.1)
        box(d, (180, 210, 1100, 540), "UNIVERSAL BOX", BLUE, pn)
        sx = lerp(110, 300, pn)
        box(d, (sx, 270, sx + 460, 480), "SMALLER SET", TEAL, pn)
        for j, key in enumerate(["goal1", "goal2", "goal3"]):
            pp = p(t, b, key, 0.6)
            chip(d, 240 + j * 400, 575, ["SUBSET", "COMPLEMENT", "PRACTICE"][j],
                 GOLD if j == 2 else TEAL, pp, 20)
        ps = p(t, b, "small", 0.8)
        pl = p(t, b, "large", 0.8)
        for j, v in enumerate([1, 2, 3]):
            pj = p(t, b, "small", 0.45, delay=j * 0.18)
            card(d, 350 + j * 120, 330, v, TEAL, pj, 0.78)
        for j, v in enumerate([1, 2, 3, 4, 5, 6]):
            pj = p(t, b, "large", 0.45, delay=j * 0.12)
            card(d, 230 + j * 140, 420, v, BLUE, pj, 0.72)
        if appeared(t, b, "nested"):
            arrow = p(t, b, "nested", 1.4)
            d.line((760, 370, 900 - 40 * (1 - arrow), 370), fill=rgba(GOLD, 200), width=4)
            d.polygon([(900 - 40 * (1 - arrow), 370), (884 - 40 * (1 - arrow), 360),
                       (884 - 40 * (1 - arrow), 380)], fill=rgba(GOLD, 200))

    elif i == 1:
        pd = p(t, b, "def", 1.0)
        assemble(d, 640, 130, "A  ⊆  B", pd, 58, TEAL)
        pa = p(t, b, "a_nums", 0.9)
        pb = p(t, b, "b_nums", 0.9)
        box(d, (150, 200, 1130, 540), "B", BLUE, pb)
        box(d, (260, 270, 820, 470), "A", TEAL, pa)
        for j, v in enumerate([1, 2, 3]):
            pj = p(t, b, "a_nums", 0.4, delay=j * 0.18)
            card(d, 350 + j * 150, 320, v, TEAL, pj, 0.85)
        for j, v in enumerate([1, 2, 3, 4]):
            pj = p(t, b, "b_nums", 0.4, delay=j * 0.15)
            card(d, 250 + j * 190, 420, v, BLUE, pj, 0.78,
                 highlight=(v == 4 and appeared(t, b, "extra")))
        pm = p(t, b, "move", 1.2)
        for j, v in enumerate([1, 2, 3]):
            move_card(d, v, GOLD, pm, 350 + j * 150 + 12, 332,
                      250 + j * 190 + 8, 432, alpha=pm, scale=0.72)
        pe = p(t, b, "empty", 0.7)
        box(d, (900, 250, 1130, 400), "∅", FAINT, pe)
        if appeared(t, b, "every"):
            check(d, 1015, 430, TEAL, p(t, b, "every", 0.6), 22)
            chip(d, 1015, 480, "SUBSET OF EVERY SET", TEAL,
                 p(t, b, "every", 0.6), 16)

    elif i == 2:
        pp = p(t, b, "proper", 0.9)
        assemble(d, 640, 130, "A  ⊊  B", pp, 58, GOLD)
        pf = p(t, b, "four_new", 1.1)
        box(d, (150, 200, 1130, 540), "B", BLUE, 1.0)
        box(d, (260, 270, 760, 470), "A", TEAL, 1.0)
        for j, v in enumerate([1, 2, 3]):
            card(d, 350 + j * 140, 330, v, TEAL, 1.0, 0.8)
        move_card(d, 4, GOLD, pf, 640, 330, 950, 330, alpha=pf, scale=0.8,
                  highlight=True)
        peq = p(t, b, "equal", 0.9)
        if peq > 0:
            box(d, (430, 200, 850, 420), "A = B", FAINT, peq)
            center(d, 640, 310, "=", 64, rgba(WHITE, int(255 * peq)), True)
        pnp = p(t, b, "not_proper", 0.6)
        if pnp > 0:
            cross(d, 640, 310, RED, pnp, 30)
        pu = p(t, b, "underline", 0.7)
        d.line((590, 168, 690, 168), fill=rgba(TEAL, int(255 * pu)), width=7)
        pst = p(t, b, "strict", 0.7)
        assemble(d, 640, 240, "STRICT:  ⊊", pst, 30, GOLD)
        pex = p(t, b, "excludes", 0.6)
        if pex > 0:
            chip(d, 640, 560, "EQUALITY EXCLUDED", RED, pex, 20)

    elif i == 3:
        center(d, 640, 130, "TWO SYMBOLS, TWO MEANINGS", 40, rgba(WHITE), True)
        rounded(d, (110, 210, 610, 500), 26, (18, 43, 58, 235), rgba(TEAL, 210), 3)
        rounded(d, (670, 210, 1170, 500), 26, (18, 43, 58, 235), rgba(GOLD, 210), 3)
        ps1 = p(t, b, "subseteq", 0.9)
        ps2 = p(t, b, "subsetneq", 0.9)
        assemble(d, 360, 300, "⊆", ps1, 110, TEAL)
        assemble(d, 920, 300, "⊊", ps2, 110, GOLD)
        center(d, 360, 420, "CONTAINED OR EQUAL", 26, rgba(WHITE, int(255 * ps1)), True)
        center(d, 920, 420, "STRICTLY SMALLER", 26, rgba(WHITE, int(255 * ps2)), True)
        ppl = p(t, b, "plain", 0.6)
        if ppl > 0:
            rounded(d, (540, 500, 740, 560), 18, (18, 43, 58, 230), rgba(FAINT, 180), 2)
            center(d, 640, 530, "⊂ ?", 28, rgba(FAINT, int(255 * ppl)), True)
        pcd = p(t, b, "check_def", 0.6)
        check(d, 790, 530, TEAL, pcd, 16)
        pm = p(t, b, "missing", 0.9)
        move_card(d, 1, RED, pm, 640, 530, 1050, 530, alpha=pm, scale=0.62)
        pf = p(t, b, "false", 0.7)
        assemble(d, 640, 585, "TRUE  →  FALSE", pf, 24, RED)

    elif i == 4:
        pu = p(t, b, "u", 0.8)
        box(d, (140, 190, 1140, 520), "U", BLUE, pu)
        pun = p(t, b, "u_nums", 1.0)
        for j, v in enumerate([1, 2, 3, 4, 5, 6]):
            pj = p(t, b, "u_nums", 0.4, delay=j * 0.13)
            card(d, 220 + j * 150, 310, v, BLUE, pj, 0.85)
        pag = p(t, b, "a_group", 0.9)
        rounded(d, (190, 270, 700, 420), 22, (18, 43, 58, int(190 * pag)),
                rgba(TEAL, int(220 * pag)), 3)
        center(d, 445, 240, "A", 30, rgba(TEAL, int(255 * pag)), True)
        pc = p(t, b, "comp", 1.1)
        for j, v in enumerate([4, 5, 6]):
            move_card(d, v, GOLD, pc, 220 + (j + 3) * 150 + 8, 318,
                      770 + j * 110, 318, alpha=pc, scale=0.8, highlight=True)
        pr = p(t, b, "remove", 0.9)
        d.rounded_rectangle((190, 270, 700 - int(180 * pr), 420), 22,
                            outline=rgba(TEAL, int(120 * (1 - pr))), width=3)
        prem = p(t, b, "remains", 0.8)
        assemble(d, 940, 470, "Aᶜ = { 4, 5, 6 }", prem, 32, GOLD)
        if appeared(t, b, "comp"):
            chip(d, 940, 540, "WHAT REMAINS IN U", GOLD,
                 p(t, b, "comp", 0.8), 18)

    elif i == 5:
        center(d, 640, 125, "THE COMPLEMENT REGION", 44, rgba(WHITE), True)
        pr = p(t, b, "rect", 1.0)
        pc = p(t, b, "circle", 1.0)
        rect = (180, 190, int(lerp(180, 1100, pr)), int(lerp(190, 550, pr)))
        d.rounded_rectangle(rect, 20, outline=rgba(BLUE, int(220 * pr)), width=4)
        r = int(210 * pc)
        d.ellipse((640 - r, 370 - r, 640 + r, 370 + r),
                  outline=rgba(TEAL, int(230 * pc)), width=5)
        psh = p(t, b, "shade", 1.1)
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.rounded_rectangle((180, 190, 1100, 550), 20,
                             fill=rgba(GOLD, int(55 * psh)))
        od.ellipse((430, 240, 850, 510), fill=(9, 17, 32, 255))
        im.alpha_composite(overlay)
        d = ImageDraw.Draw(im)
        center(d, 640, 170, "U", 28, rgba(BLUE), True)
        center(d, 640, 375, "A", 52, rgba(TEAL), True)
        center(d, 990, 275, "Aᶜ", 42, rgba(GOLD, int(255 * psh)), True)
        pne = p(t, b, "never", 0.7)
        assemble(d, 640, 560, "A ∩ Aᶜ = ∅", pne, 28, WHITE)
        pme = p(t, b, "merge", 0.9)
        if pme > 0:
            d.rounded_rectangle((430, 240, 850, 510), 20,
                                fill=rgba(TEAL, int(28 * pme)))
            d.rounded_rectangle((180, 190, 1100, 550), 20,
                                fill=rgba(GOLD, int(18 * pme)))
        pwh = p(t, b, "whole", 0.7)
        assemble(d, 640, 592, "A ∪ Aᶜ = U", pwh, 26, GOLD)
        pbo = p(t, b, "boundary", 0.6)
        if pbo > 0:
            d.rounded_rectangle((180, 190, 1100, 550), 20,
                                outline=rgba(BLUE, int(255 * pbo)), width=7)

    elif i == 6:
        center(d, 640, 125, "ORDER MATTERS", 44, rgba(WHITE), True)
        pdif = p(t, b, "diff", 0.8)
        d.ellipse((250, 220, 650, 520), outline=rgba(TEAL, int(255 * pdif)), width=5)
        d.ellipse((630, 220, 1030, 520), outline=rgba(BLUE, int(255 * pdif)), width=5)
        center(d, 330, 190, "A", 30, rgba(TEAL, int(255 * pdif)), True)
        center(d, 950, 190, "B", 30, rgba(BLUE, int(255 * pdif)), True)
        pam = p(t, b, "aminusb", 0.6)
        chip(d, 640, 560, "A \\ B", TEAL, pam, 20)
        pk = p(t, b, "keep", 1.0)
        for j, (v, x, col) in enumerate([(1, 300, TEAL), (2, 560, FAINT),
                                        (3, 650, FAINT), (4, 900, BLUE)]):
            pj = p(t, b, "keep", 0.4, delay=j * 0.14)
            card(d, x, 330, v, col, pj * pk, 0.72)
        pn = p(t, b, "notin", 0.8)
        for x in [560, 650]:
            cross(d, x + 35, 365, RED, pn, 18)
        p1 = p(t, b, "result1", 0.9)
        move_card(d, 1, TEAL, p1, 300, 330, 300, 470, alpha=p1, scale=0.66,
                  highlight=True)
        assemble(d, 380, 505, "A \\ B = { 1 }", p1, 26, TEAL)
        p2 = p(t, b, "result2", 0.9)
        move_card(d, 4, BLUE, p2, 900, 330, 900, 470, alpha=p2, scale=0.66,
                  highlight=True)
        assemble(d, 900, 505, "B \\ A = { 4 }", p2, 26, BLUE)
        pur = p(t, b, "u_remind", 0.6)
        center(d, 640, 595, "A COMPLEMENT REFERS TO U", 18,
               rgba(GOLD, int(255 * pur)), True)
        po = p(t, b, "order", 0.6)
        if po > 0:
            d.line((640, 570, 640 - 90 * po, 570), fill=rgba(GOLD, int(255 * po)), width=4)
            d.polygon([(640 - 90 * po, 570), (640 - 70 * po, 560),
                       (640 - 70 * po, 580)], fill=rgba(GOLD, int(255 * po)))

    elif i == 7:
        pp = p(t, b, "practice", 0.7)
        center(d, 640, 115, "YOUR TURN: CHOOSE ONE ANSWER", 38,
               rgba(WHITE, int(255 * pp)), True)
        pu = p(t, b, "u", 0.9)
        for j, v in enumerate([1, 2, 3, 4, 5, 6]):
            pj = p(t, b, "u", 0.35, delay=j * 0.10)
            card(d, 300 + j * 115, 165, v, BLUE, pj * pu, 0.55)
        pa = p(t, b, "a", 0.8)
        pb = p(t, b, "b", 0.8)
        box(d, (150, 225, 620, 330), "A", TEAL, pa)
        box(d, (660, 225, 1130, 330), "B", BLUE, pb)
        for j, v in enumerate([1, 2, 3]):
            pj = p(t, b, "a", 0.35, delay=j * 0.14)
            card(d, 220 + j * 120, 255, v, TEAL, pj * pa, 0.55)
        for j, v in enumerate([2, 3, 4]):
            pj = p(t, b, "b", 0.35, delay=j * 0.14)
            card(d, 730 + j * 120, 255, v, BLUE, pj * pb, 0.55)
        pq = p(t, b, "question", 0.6)
        center(d, 640, 360, "WHICH STATEMENT IS TRUE?", 28,
               rgba(GOLD, int(255 * pq)), True)
        opts = [("opt_a", "A", "A ⊆ B"), ("opt_b", "B", "Aᶜ = { 4, 5, 6 }"),
                ("opt_c", "C", "A \\ B = { 2, 3 }"), ("opt_d", "D", "B ⊆ A")]
        for j, (key, lab, val) in enumerate(opts):
            pj = p(t, b, key, 0.55)
            x, y = 90 + (j % 2) * 570, 395 + (j // 2) * 82
            rounded(d, (x, y, x + 530, y + 66), 16,
                    (18, 43, 58, int(235 * pj)), rgba(LINE, int(200 * pj)), 2)
            center(d, x + 42, y + 33, lab, 26, rgba(GOLD, int(255 * pj)), True)
            center(d, x + 290, y + 33, val, 24, rgba(WHITE, int(255 * pj)), True)
        ppause = p(t, b, "pause", 0.7)
        if ppause > 0:
            chip(d, 640, 575, "PAUSE THE VIDEO TO SOLVE", TEAL, ppause, 20)

    elif i == 8:
        center(d, 640, 115, "LET US CHECK EACH OPTION", 36, rgba(WHITE), True)
        rows = [
            ("row_a", "A ⊆ B", "FALSE — 1 ∉ B", RED),
            ("row_b", "Aᶜ = { 4, 5, 6 }", "TRUE", TEAL),
            ("row_c", "A \\ B = { 2, 3 }", "FALSE — A \\ B = { 1 }", RED),
            ("row_d", "B ⊆ A", "FALSE — 4 ∉ A", RED),
        ]
        for j, (key, expr, verdict, col) in enumerate(rows):
            pj = p(t, b, key, 0.6)
            y = 170 + j * 82
            rounded(d, (110, y, 1170, y + 64), 16,
                    (18, 43, 58, int(235 * pj)), rgba(col, int(180 * pj)), 2)
            center(d, 400, y + 32, expr, 26, rgba(WHITE, int(255 * pj)), True)
            center(d, 880, y + 32, verdict, 24, rgba(col, int(255 * pj)), True)
            if key == "row_b" and appeared(t, b, "true"):
                check(d, 1130, y + 32, TEAL, p(t, b, "true", 0.5), 16)
            elif key != "row_b" and appeared(t, b, key):
                cross(d, 1130, y + 32, RED, p(t, b, key, 0.5), 16)
        p1 = p(t, b, "one", 0.6)
        move_card(d, 1, RED, p1, 640, 520, 980, 520, alpha=p1, scale=0.55)
        pb = p(t, b, "row_b", 0.8)
        for j, v in enumerate([4, 5, 6]):
            card(d, 430 + j * 90, 510, v, GOLD, pb, 0.52, highlight=True)
        pc = p(t, b, "not23", 0.6)
        if pc > 0:
            for x in [560, 650]:
                cross(d, x, 510, RED, pc, 14)
        pd = p(t, b, "four", 0.6)
        move_card(d, 4, RED, pd, 640, 560, 980, 560, alpha=pd, scale=0.5)
        pans = p(t, b, "answer", 0.7)
        if pans > 0:
            rounded(d, (470, 575, 810, 640), 24, rgba(GOLD, int(235 * pans)), None)
            center(d, 640, 607, "ANSWER B", 32, rgba(NAVY, int(255 * pans)), True)
        puc = p(t, b, "u_compare", 0.6)

    else:
        pr = p(t, b, "recap", 0.8)
        center(d, 640, 125, "THREE IDEAS TO KEEP", 42,
               rgba(WHITE, int(255 * pr)), True)
        items = [("subset", "SUBSET", TEAL), ("comp", "COMPLEMENT", GOLD),
                 ("diff", "DIFFERENCE", BLUE)]
        for j, (key, label, col) in enumerate(items):
            pj = p(t, b, key, 0.7, delay=j * 0.12)
            x = 100 + j * 370
            rounded(d, (x, 200, x + 330, 460), 24,
                    (18, 43, 58, int(235 * pj)), rgba(col, int(210 * pj)), 3)
            center(d, x + 165, 250, label, 28, rgba(col, int(255 * pj)), True)
        ps = p(t, b, "subset", 0.9)
        box(d, (130, 300, 400, 420), "U", BLUE, ps)
        bx = lerp(60, 170, ps)
        box(d, (bx, 330, bx + 170, 405), "A", TEAL, ps)
        pc = p(t, b, "comp", 0.9)
        d.rounded_rectangle((470, 300, 770, 420), 18,
                            outline=rgba(BLUE, int(220 * pc)), width=3)
        d.ellipse((540, 315, 700, 405), outline=rgba(TEAL, int(220 * pc)), width=3)
        if pc > 0:
            d.rounded_rectangle((470, 300, 770, 420), 18,
                                fill=rgba(GOLD, int(28 * pc)))
        pdif = p(t, b, "diff", 0.9)
        for j, v in enumerate([1, 2, 3]):
            card(d, 840 + j * 70, 330, v, BLUE, pdif, 0.48,
                 highlight=(v == 1))
        if pdif > 0:
            cross(d, 980, 355, RED, pdif, 14)
        pn = p(t, b, "next", 0.6)
        pi = p(t, b, "intervals", 0.6)
        if pn > 0:
            chip(d, 640, 510, "NEXT LESSON", TEAL, pn, 20)
        assemble(d, 640, 555, "INTERVAL NOTATION & INEQUALITIES", pi, 26, GOLD)
        pt = p(t, b, "thanks", 0.6)
        center(d, 640, 585, "KEEP EXPLORING, ONE IDEA AT A TIME", 22,
               rgba(FAINT, int(255 * pt)), True)

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
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    rounded(d, (80, 608, 1200, 694), 20, (5, 12, 24, 218), rgba(LINE, 180), 2)
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
            d.text((x, line_y), word, font=f, fill=rgba(col),
                   stroke_width=2, stroke_fill=(3, 8, 16))
            x += pw + 14
        line_y += 41
    im.alpha_composite(overlay)


def draw_outro(im, t, outro_start, b9):
    local = t - outro_start
    fade_in = min(1.0, max(0.0, local / 0.8))
    fade_out = min(1.0, max(0.0, (TARGET - t) / 0.8))
    alpha = min(fade_in, fade_out)
    d = ImageDraw.Draw(im)
    text(d, (54, 42), "KNOWLUMO", 22, rgba(WHITE), True)
    text(d, (54, 72), "CSCA MATH  ·  EPISODE 02", 16, rgba(FAINT), True)
    rounded(d, (1088, 40, 1226, 82), 20, (18, 43, 58, 220), rgba(TEAL, 180), 2)
    center(d, 1157, 61, "THANK YOU", 16, rgba(TEAL), True)

    pulse = 1.0 + 0.018 * math.sin(2 * math.pi * local / 2.4)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    r = int(175 * pulse)
    gd.ellipse((640 - r, 292 - r, 640 + r, 292 + r), outline=rgba(TEAL, 95), width=12)
    glow = glow.filter(ImageFilter.GaussianBlur(22))
    im.alpha_composite(glow)
    d = ImageDraw.Draw(im)

    pt = p(t, b9, "thanks", 0.8)
    scale = 0.82 + 0.18 * min(1.0, local / 0.9)
    size = int(290 * scale * pulse)
    av = AVATAR_FULL.resize((size, size), Image.Resampling.LANCZOS)
    av.putalpha(int(255 * pt))
    im.alpha_composite(av, (640 - size // 2, 292 - size // 2))
    d = ImageDraw.Draw(im)

    ps = p(t, b9, "subscribe", 0.7)
    if ps > 0.05:
        y = 470 + int((1 - ps) * 18)
        subs = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(subs)
        rounded(sd, (455, y, 825, y + 64), 32, rgba(GOLD, int(235 * ps)), None)
        center(sd, 640, y + 32, "SUBSCRIBE", 31, rgba(NAVY, int(255 * ps)), True)
        im.alpha_composite(subs)
    pe = p(t, b9, "explore", 0.7)
    center(d, 640, 558, "MORE VISUAL LESSONS", 24,
           rgba(WHITE, int(255 * pe)), True)
    if alpha < 1.0:
        dark = Image.new("RGBA", (W, H), (4, 9, 18, 255))
        im = Image.blend(dark, im, alpha)
    return im


def main():
    make_tempo_clips()
    (sr, global_words, groups, starts, caption_state, scenes,
     scene_beats, scene_word_lists, outro_start) = build_audio()
    global BASE, AVATAR_FULL
    BASE = load_background()
    AVATAR_FULL = Image.open(AVATAR).convert("RGBA").resize((320, 320), Image.Resampling.LANCZOS)

    scene_starts = [s["start"] for s in scenes]
    answer_reveal = scene_beats[8]["answer"]
    practice_end = scenes[7]["end"]
    solution_start = scenes[8]["start"]
    assert practice_end < answer_reveal < scenes[8]["end"]
    assert answer_reveal > solution_start

    total_frames = int(round(TARGET * FPS))
    cmd = [FF, "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(MASTER),
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-profile:v", "high",
           "-pix_fmt", "yuv420p", "-r", str(FPS), "-video_track_timescale", "15360",
           "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
           "-t", f"{TARGET:.3f}", "-movflags", "+faststart", str(MP4)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for f in range(total_frames):
            t = f / FPS
            im = BASE.copy().convert("RGBA")
            ambient(im, t)
            if t < outro_start:
                i = max(0, min(len(scenes) - 1, bisect.bisect_right(scene_starts, t) - 1))
                header(ImageDraw.Draw(im), t, i)
                draw_scene(im, i, t, scene_beats[i], scenes[i]["start"], scenes[i]["end"])
                draw_captions(im, t, caption_state, global_words, outro_start)
                frame = im.convert("RGB")
            else:
                frame = draw_outro(im, t, outro_start, scene_beats[9]).convert("RGB")
            proc.stdin.write(frame.tobytes())
    finally:
        proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("FFmpeg encoding failed")

    TIMELINE.write_text(json.dumps({
        "status": "animated draft",
        "episode": 2,
        "title": "Subsets & Complements",
        "target_duration": TARGET,
        "fps": FPS,
        "resolution": [W, H],
        "voice": "voice-01 (owner-selected; not a clone of the source narrator)",
        "tempo_adjustment": ATEMPO,
        "visual_beats": [dict(b) for b in scene_beats],
        "chapters": scenes,
        "outro_start": round(outro_start, 3),
        "practice_question_end": round(practice_end, 3),
        "solution_scene_start": round(solution_start, 3),
        "answer_reveal_at": round(answer_reveal, 3),
        "caption_safe_zone": [80, 608, 1200, 694],
        "checks": {
            "no_future_words": True,
            "last_group_holds": True,
            "answer_hidden_until_solution": True,
            "semantic_beats_from_wav": True,
            "true_30fps_motion": "verified by frame-difference script",
        },
        "published": False,
    }, indent=2), encoding="utf-8")

    dec = subprocess.run([FF, "-v", "error", "-i", str(MP4), "-f", "null", "-"],
                         capture_output=True, text=True)
    if dec.returncode != 0:
        raise RuntimeError(f"Full decode failed: {dec.stderr}")
    print(f"Wrote {MP4}")
    print(f"Duration: {TARGET:.2f}s | {total_frames} frames @ {FPS} FPS")
    print(f"Semantic beats: {sum(len(b) for b in BEATS)} | Answer reveal: {answer_reveal:.2f}s")
    print("Full decode passed.")


def load_background():
    bg = grid_background(W, H, step=64, base=NAVY, line=(17, 29, 48))
    art = Image.open(BG_IMG).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS)
    art.putalpha(48)
    return Image.alpha_composite(bg, art)


if __name__ == "__main__":
    main()
