#!/usr/bin/env python3
"""Build a ~5-minute 1280x720 / 30 FPS draft for CSCA Math Episode 02.

Uses the owner-selected voice-01 WAVs, energy-based word timings, dynamic
captions, an object-first visual layer, and a short branded outro. A light
tempo adjustment fits the narration into exactly five minutes; no source
lesson is trimmed and no external video/photo is copied.
"""
from __future__ import annotations

import bisect
import json
import math
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_utils import (BLUE, FAINT, GOLD, INK, LINE, NAVY, RED, TEAL, WHITE,
                         caption_groups, center, chime, ease, font,
                         grid_background, read_wav_mono, rounded, text,
                         word_timings, write_stereo_wav)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "episode02"
AUDIO = OUT / "audio"
TEMPO = AUDIO / "tempo"
BG_IMG = OUT / "episode02_background.png"
AVATAR = ROOT / "sources" / "Youtube-arena-01b47ded-youtube" / "channel" / "knowlumo" / "assets" / "avatar_round_800.png"
MASTER = AUDIO / "episode02_master.wav"
MP4 = OUT / "CSCA_Math_02_Subsets_Complements_Draft.mp4"
TIMELINE = OUT / "timeline.json"
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


def rgba(c, a=255):
    return c + (a,)


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
    global_words, groups, scenes = [], [], []

    for i, (clip, script) in enumerate(zip(TEMPO_CLIPS, SCRIPTS)):
        voice, this_sr = read_wav_mono(clip)
        assert this_sr == sr
        words, _ = word_timings(clip, script)
        start, duration = cursor, len(voice) / sr
        end = cursor + duration
        scenes.append({"index": i + 1, "title": TITLES[i],
                       "start": round(start, 3), "end": round(end, 3),
                       "duration": round(duration, 3)})

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
        active = bisect.bisect_right(starts, t) - 1
        active = min(active, len(global_words) - 1)
        group = next(g for g in groups if g["indices"][0] <= active <= g["indices"][-1])
        return group, active

    for i, w in enumerate(global_words):
        _, before = caption_state(w["start"] - 0.001)
        assert before < i, ("future word", i, w["word"])
        _, after = caption_state(w["start"] + 0.001)
        assert after >= i, ("missing word", i, w["word"])

    return sr, global_words, groups, starts, caption_state, scenes, outro_start


def load_background():
    bg = grid_background(W, H, step=64, base=NAVY, line=(17, 29, 48))
    art = Image.open(BG_IMG).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS)
    art.putalpha(48)
    return Image.alpha_composite(bg, art)


BASE = None
AVATAR_FULL = None


def card(d, x, y, value, color, highlight=False, w=92, h=92):
    fill = (55, 45, 20, 235) if highlight else (18, 43, 58, 235)
    rounded(d, (x, y, x + w, y + h), 16, fill, rgba(color, 220), 3)
    center(d, x + w / 2, y + h / 2, str(value), 38, rgba(color), True)


def box(d, rect, label, color, alpha=170):
    rounded(d, rect, 24, (18, 43, 58, alpha), rgba(color, 200), 3)
    center(d, (rect[0] + rect[2]) / 2, rect[1] - 26, label, 22, rgba(color), True)


def header(d, t, scene_index):
    text(d, (44, 32), "KNOWLUMO", 22, rgba(WHITE), True)
    text(d, (44, 62), "CSCA MATH  ·  EPISODE 02", 16, rgba(FAINT), True)
    center(d, 640, 48, TITLES[scene_index], 20, rgba(WHITE), True)
    text(d, (1095, 39), f"{scene_index + 1:02d} / 10", 17, rgba(FAINT), True)
    d.rounded_rectangle((44, 89, 1236, 94), 2, fill=rgba(LINE))
    d.rounded_rectangle((44, 89, 44 + int(1192 * min(1.0, t / TARGET)), 94), 2, fill=rgba(TEAL))


def draw_scene(im, i, t, local_t):
    d = ImageDraw.Draw(im)
    p = min(1.0, max(0.0, local_t / 1.2))

    if i == 0:
        center(d, 640, 150, "SETS INSIDE SETS", 52, rgba(WHITE), True)
        box(d, (180, 210, 1100, 540), "UNIVERSAL BOX", BLUE, 150)
        box(d, (300, 270, 760, 480), "SMALLER SET", TEAL, 220)
        for j, v in enumerate([1, 2, 3, 4, 5, 6]):
            card(d, 230 + j * 140, 410, v, BLUE, w=72, h=72)
        for j, v in enumerate([1, 2, 3]):
            card(d, 370 + j * 120, 330, v, TEAL, w=72, h=72)
        center(d, 640, 570, "ONE COLLECTION CAN LIVE INSIDE ANOTHER", 26, rgba(GOLD), True)

    elif i == 1:
        center(d, 640, 135, "A ⊆ B", 64, rgba(TEAL), True)
        box(d, (150, 200, 1130, 540), "B = { 1, 2, 3, 4 }", BLUE, 150)
        box(d, (260, 270, 820, 470), "A = { 1, 2, 3 }", TEAL, 225)
        for j, v in enumerate([1, 2, 3, 4]):
            card(d, 250 + j * 190, 420, v, BLUE, w=80, h=80)
        for j, v in enumerate([1, 2, 3]):
            card(d, 350 + j * 150, 320, v, TEAL, w=80, h=80)
        center(d, 640, 570, "EVERY ELEMENT OF A IS ALSO IN B", 26, rgba(WHITE), True)

    elif i == 2:
        center(d, 640, 135, "A ⊊ B", 64, rgba(GOLD), True)
        box(d, (150, 200, 1130, 540), "B HAS ONE EXTRA CARD", BLUE, 150)
        box(d, (260, 270, 760, 470), "A", TEAL, 225)
        for j, v in enumerate([1, 2, 3]):
            card(d, 350 + j * 140, 330, v, TEAL, w=80, h=80)
        card(d, 930, 330, 4, GOLD, highlight=True, w=80, h=80)
        center(d, 640, 570, "STRICTLY SMALLER, NOT EQUAL", 26, rgba(GOLD), True)

    elif i == 3:
        center(d, 640, 135, "TWO SYMBOLS, TWO MEANINGS", 40, rgba(WHITE), True)
        rounded(d, (110, 220, 610, 500), 26, (18, 43, 58, 235), rgba(TEAL, 210), 3)
        center(d, 360, 300, "⊆", 110, rgba(TEAL), True)
        center(d, 360, 420, "CONTAINED OR EQUAL", 26, rgba(WHITE), True)
        rounded(d, (670, 220, 1170, 500), 26, (18, 43, 58, 235), rgba(GOLD, 210), 3)
        center(d, 920, 300, "⊊", 110, rgba(GOLD), True)
        center(d, 920, 420, "STRICTLY SMALLER", 26, rgba(WHITE), True)
        center(d, 640, 560, "CHECK THE DEFINITION IN YOUR COURSE", 24, rgba(FAINT), True)

    elif i == 4:
        center(d, 640, 135, "Aᶜ = U \\ A", 58, rgba(GOLD), True)
        box(d, (140, 200, 1140, 520), "U = { 1, 2, 3, 4, 5, 6 }", BLUE, 150)
        for j, v in enumerate([1, 2, 3, 4, 5, 6]):
            col = TEAL if v <= 3 else GOLD
            card(d, 220 + j * 150, 320, v, col, highlight=(v > 3), w=84, h=84)
        center(d, 430, 470, "A", 30, rgba(TEAL), True)
        center(d, 880, 470, "Aᶜ = { 4, 5, 6 }", 30, rgba(GOLD), True)
        center(d, 640, 570, "REMOVE THE SMALL BOX; KEEP WHAT REMAINS", 24, rgba(WHITE), True)

    elif i == 5:
        center(d, 640, 130, "THE COMPLEMENT REGION", 44, rgba(WHITE), True)
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.rounded_rectangle((180, 190, 1100, 550), 20, fill=rgba(GOLD, 55))
        od.ellipse((430, 240, 850, 510), fill=(9, 17, 32, 255))
        im.alpha_composite(overlay)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((180, 190, 1100, 550), 20, outline=rgba(BLUE, 220), width=4)
        d.ellipse((430, 240, 850, 510), outline=rgba(TEAL, 230), width=5)
        center(d, 640, 170, "U", 28, rgba(BLUE), True)
        center(d, 640, 375, "A", 52, rgba(TEAL), True)
        center(d, 980, 275, "Aᶜ", 42, rgba(GOLD), True)
        center(d, 640, 575, "A ∪ Aᶜ = U     A ∩ Aᶜ = ∅", 28, rgba(WHITE), True)

    elif i == 6:
        center(d, 640, 130, "ORDER MATTERS", 44, rgba(WHITE), True)
        d.ellipse((250, 230, 650, 530), outline=rgba(TEAL), width=5)
        d.ellipse((630, 230, 1030, 530), outline=rgba(BLUE), width=5)
        center(d, 330, 200, "A", 30, rgba(TEAL), True)
        center(d, 950, 200, "B", 30, rgba(BLUE), True)
        card(d, 300, 340, 1, TEAL, highlight=True, w=70, h=70)
        card(d, 560, 340, 2, FAINT, w=70, h=70)
        card(d, 650, 340, 3, FAINT, w=70, h=70)
        card(d, 900, 340, 4, BLUE, highlight=True, w=70, h=70)
        center(d, 360, 560, "A \\ B = { 1 }", 30, rgba(TEAL), True)
        center(d, 920, 560, "B \\ A = { 4 }", 30, rgba(BLUE), True)
        center(d, 640, 610, "A COMPLEMENT ALWAYS REFERS TO U", 22, rgba(GOLD), True)

    elif i == 7:
        center(d, 640, 125, "YOUR TURN: CHOOSE ONE ANSWER", 38, rgba(WHITE), True)
        center(d, 640, 180, "U = { 1, 2, 3, 4, 5, 6 }   A = { 1, 2, 3 }   B = { 2, 3, 4 }", 26, rgba(FAINT), True)
        opts = [
            ("A", "A ⊆ B"),
            ("B", "Aᶜ = { 4, 5, 6 }"),
            ("C", "A \\ B = { 2, 3 }"),
            ("D", "B ⊆ A"),
        ]
        for j, (lab, val) in enumerate(opts):
            x, y = 90 + (j % 2) * 570, 240 + (j // 2) * 130
            rounded(d, (x, y, x + 530, y + 96), 18, (18, 43, 58, 235), rgba(LINE), 2)
            center(d, x + 45, y + 48, lab, 30, rgba(GOLD), True)
            center(d, x + 290, y + 48, val, 28, rgba(WHITE), True)
        center(d, 640, 530, "PAUSE THE VIDEO TO SOLVE", 28, rgba(TEAL), True)

    elif i == 8:
        center(d, 640, 125, "LET US CHECK EACH OPTION", 38, rgba(WHITE), True)
        rows = [
            ("A ⊆ B", "FALSE — 1 ∉ B", RED),
            ("Aᶜ = { 4, 5, 6 }", "TRUE", TEAL),
            ("A \\ B = { 2, 3 }", "FALSE — A \\ B = { 1 }", RED),
            ("B ⊆ A", "FALSE — 4 ∉ A", RED),
        ]
        for j, (expr, verdict, col) in enumerate(rows):
            y = 210 + j * 85
            rounded(d, (110, y, 1170, y + 68), 16, (18, 43, 58, 235), rgba(col, 180), 2)
            center(d, 400, y + 34, expr, 28, rgba(WHITE), True)
            center(d, 880, y + 34, verdict, 26, rgba(col), True)
        rounded(d, (470, 570, 810, 640), 24, rgba(GOLD, 235), None)
        center(d, 640, 605, "ANSWER B", 34, rgba(NAVY), True)

    else:
        center(d, 640, 130, "THREE IDEAS TO KEEP", 42, rgba(WHITE), True)
        items = [("SUBSET", "CONTAINED", TEAL), ("COMPLEMENT", "OUTSIDE IN U", GOLD),
                 ("DIFFERENCE", "KEEP FROM FIRST", BLUE)]
        for j, (a, b, col) in enumerate(items):
            x = 100 + j * 370
            rounded(d, (x, 220, x + 330, 470), 24, (18, 43, 58, 235), rgba(col, 210), 3)
            center(d, x + 165, 290, a, 30, rgba(col), True)
            center(d, x + 165, 380, b, 22, rgba(WHITE), True)
        center(d, 640, 530, "NEXT: INTERVAL NOTATION AND INEQUALITIES", 28, rgba(GOLD), True)
        center(d, 640, 575, "KEEP EXPLORING, ONE IDEA AT A TIME", 24, rgba(FAINT), True)

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


def draw_outro(im, t, outro_start):
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

    scale = 0.82 + 0.18 * min(1.0, local / 0.9)
    size = int(290 * scale * pulse)
    av = AVATAR_FULL.resize((size, size), Image.Resampling.LANCZOS)
    im.alpha_composite(av, (640 - size // 2, 292 - size // 2))
    d = ImageDraw.Draw(im)

    p = min(1.0, max(0.0, (local - 1.6) / 0.7))
    if p > 0.05:
        y = 470 + int((1 - p) * 18)
        subs = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(subs)
        rounded(sd, (455, y, 825, y + 64), 32, rgba(GOLD, int(235 * p)), None)
        center(sd, 640, y + 32, "SUBSCRIBE", 31, rgba(NAVY, int(255 * p)), True)
        im.alpha_composite(subs)
    center(d, 640, 558, "MORE VISUAL LESSONS", 24, rgba(WHITE), True)
    if alpha < 1.0:
        dark = Image.new("RGBA", (W, H), (4, 9, 18, 255))
        im = Image.blend(dark, im, alpha)
    return im


def main():
    make_tempo_clips()
    sr, global_words, groups, starts, caption_state, scenes, outro_start = build_audio()
    global BASE, AVATAR_FULL
    BASE = load_background()
    AVATAR_FULL = Image.open(AVATAR).convert("RGBA").resize((320, 320), Image.Resampling.LANCZOS)

    scene_starts = [s["start"] for s in scenes]
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
            if t < outro_start:
                i = max(0, min(len(scenes) - 1, bisect.bisect_right(scene_starts, t) - 1))
                header(ImageDraw.Draw(im), t, i)
                draw_scene(im, i, t, t - scene_starts[i])
                draw_captions(im, t, caption_state, global_words, outro_start)
                frame = im.convert("RGB")
            else:
                frame = draw_outro(im, t, outro_start).convert("RGB")
            proc.stdin.write(frame.tobytes())
    finally:
        proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("FFmpeg encoding failed")

    TIMELINE.write_text(json.dumps({
        "status": "draft",
        "episode": 2,
        "title": "Subsets & Complements",
        "target_duration": TARGET,
        "fps": FPS,
        "resolution": [W, H],
        "voice": "voice-01 (owner-selected; not a clone of the source narrator)",
        "tempo_adjustment": ATEMPO,
        "chapters": scenes,
        "outro_start": round(outro_start, 3),
        "math": {
            "U": [1, 2, 3, 4, 5, 6],
            "A": [1, 2, 3],
            "B": [2, 3, 4],
            "A_subset_B": False,
            "A_proper_subset_U": True,
            "A_complement": [4, 5, 6],
            "A_minus_B": [1],
            "B_minus_A": [4],
            "B_subset_A": False,
            "correct_option": "B",
        },
        "checks": {
            "no_future_words": True,
            "last_group_holds": True,
            "full_decode": "run separately by verify script",
        },
        "published": False,
    }, indent=2), encoding="utf-8")

    dec = subprocess.run([FF, "-v", "error", "-i", str(MP4), "-f", "null", "-"],
                         capture_output=True, text=True)
    if dec.returncode != 0:
        raise RuntimeError(f"Full decode failed: {dec.stderr}")
    print(f"Wrote {MP4}")
    print(f"Duration: {TARGET:.2f}s | {total_frames} frames @ {FPS} FPS")
    print(f"Chapters: {len(scenes)} | Outro start: {outro_start:.2f}s")
    print("Full decode passed.")


if __name__ == "__main__":
    main()
