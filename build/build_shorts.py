#!/usr/bin/env python3
"""Build the vertical Knowlumo CSCA Math Sets quick-quiz Short/Reel.

Audio: eight separately generated English narration clips, joined at exact
sample boundaries. Captions: word timings estimated from each clip's actual
waveform energy envelope; future words are never drawn and the last spoken
group holds through the thinking pauses. Visuals: 1080x1920, 30 FPS, Pillow
animation, with the final card showing the real Episode 01 thumbnail.
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
from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_utils import (BLUE, FAINT, GOLD, INK, LINE, NAVY, RED, TEAL, WHITE,
                         caption_groups, center, chime, chip, draw_cap,
                         draw_cup, ease, font, grid_background, read_wav_mono,
                         rounded, spring, text, word_timings,
                         write_stereo_wav)

ROOT = Path(__file__).resolve().parents[1]
AUDIO_DIR = ROOT / "output" / "shorts" / "audio"
OUT_DIR = ROOT / "output" / "shorts"
THUMB = ROOT / "output" / "episode01" / "CSCA_Math_01_Sets_Thumbnail_1280x720.png"
AVATAR = ROOT / "sources" / "Youtube-arena-01b47ded-youtube" / "channel" / "knowlumo" / "assets" / "avatar_round_800.png"
MASTER_WAV = AUDIO_DIR / "shorts_master.wav"
FINAL_MP4 = OUT_DIR / "CSCA_Math_01_Sets_Shorts_1080x1920.mp4"
TIMELINE_JSON = OUT_DIR / "timeline.json"

FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1080, 1920, 30
LEAD, TAIL = 0.6, 0.7

SEGMENTS = [
    {"key": "hook", "clip": "01_hook.wav", "visual": "hook", "pause": 0.5, "chime": False,
     "text": "Two sets. Two quick questions. Set A is one, two, three. Set B is two, three, four."},
    {"key": "q1", "clip": "02_q1.wav", "visual": "q1", "pause": 2.2, "chime": False,
     "text": "Question one. What is A intersection B?"},
    {"key": "a1", "clip": "03_a1.wav", "visual": "a1", "pause": 0.6, "chime": True,
     "text": "The answer is two, three. Intersection means elements in both sets."},
    {"key": "q2", "clip": "04_q2.wav", "visual": "q2", "pause": 2.2, "chime": False,
     "text": "Question two. What is A union B?"},
    {"key": "a2", "clip": "05_a2.wav", "visual": "a2", "pause": 0.6, "chime": True,
     "text": "The answer is one, two, three, four. Union includes each element once."},
    {"key": "q3", "clip": "06_q3.wav", "visual": "q3", "pause": 1.8, "chime": False,
     "text": "Last check. Is four in A intersection B?"},
    {"key": "a3", "clip": "07_a3.wav", "visual": "a3", "pause": 0.6, "chime": True,
     "text": "No. Four is only in B, not in both sets."},
    {"key": "cta", "clip": "08_cta.wav", "visual": "cta", "pause": 2.0, "chime": True,
     "text": "Want the full lesson and more practice? Watch CSCA Math Episode One, Sets Made Simple, on Knowlumo."},
]

# Mathematical answers used on screen.
A = {1, 2, 3}
B = {2, 3, 4}
assert A & B == {2, 3}
assert A | B == {1, 2, 3, 4}
assert 4 not in (A & B)


def build_audio_and_timeline():
    pieces, sr = [], None
    pieces.append(np.zeros(int(LEAD * 44100), dtype=np.float32))
    cursor = LEAD
    chime_events = []

    for seg in SEGMENTS:
        path = AUDIO_DIR / seg["clip"]
        voice, this_sr = read_wav_mono(path)
        sr = sr or this_sr
        assert this_sr == sr
        words, _ = word_timings(path, seg["text"])
        duration = len(voice) / sr
        seg["start"] = cursor
        seg["end"] = cursor + duration
        seg["duration"] = duration
        seg["words"] = words
        if seg["chime"]:
            chime_events.append(cursor + 0.03)
        pieces.append(voice)
        pieces.append(np.zeros(int(round(seg["pause"] * sr)), dtype=np.float32))
        cursor += duration + seg["pause"]
    pieces.append(np.zeros(int(TAIL * sr), dtype=np.float32))
    cursor += TAIL
    master = np.concatenate(pieces).astype(np.float32)
    for event in chime_events:
        c = chime(sr, duration=0.45, base=620.0, volume=0.055)
        i = int(round(event * sr))
        master[i:i + len(c)] += c
    # Short fades prevent clicks at the boundaries.
    fade = int(0.12 * sr)
    master[:fade] *= np.linspace(0, 1, fade, dtype=np.float32)
    master[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
    write_stereo_wav(MASTER_WAV, master, sr)
    total = len(master) / sr

    global_words, groups = [], []
    for seg in SEGMENTS:
        base = len(global_words)
        for w in seg["words"]:
            global_words.append({
                "word": w["word"],
                "start": seg["start"] + w["start"],
                "end": seg["start"] + w["end"],
                "segment": seg["key"],
            })
        for g in caption_groups(seg["words"], max_words=7):
            groups.append({
                "indices": [base + i for i in g["indices"]],
                "start": seg["start"] + g["start"],
                "end": seg["start"] + g["end"],
                "segment": seg["key"],
            })
    groups.sort(key=lambda g: g["start"])
    starts = [w["start"] for w in global_words]

    def caption_state(t):
        if not starts or t < starts[0]:
            return None, -1
        active = bisect.bisect_right(starts, t) - 1
        active = min(active, len(global_words) - 1)
        group = next(g for g in groups if g["indices"][0] <= active <= g["indices"][-1])
        return group, active

    # Regression checks: no future word is visible; the last group holds.
    for i, w in enumerate(global_words):
        g, active = caption_state(w["start"] - 0.001)
        if g is not None:
            assert active < i, (i, active, w["word"])
        g2, active2 = caption_state(w["start"] + 0.001)
        assert active2 >= i, (i, active2, w["word"])
    last_g, last_active = caption_state(total + 1)
    assert last_active == len(global_words) - 1

    timeline = {
        "total_duration": total,
        "fps": FPS,
        "resolution": [W, H],
        "voice": "voice-01 (closest female educational voice selected by the owner; not a clone of the original narrator)",
        "caption_alignment": "energy-envelope estimate per generated WAV; approximate, not ASR forced alignment",
        "segments": [{k: v for k, v in s.items() if k not in ("words",)} | {"local_words": s["words"]}
                     for s in SEGMENTS],
        "global_words": global_words,
        "caption_groups": groups,
        "math": {"A": [1, 2, 3], "B": [2, 3, 4], "intersection": [2, 3],
                 "union": [1, 2, 3, 4], "four_in_intersection": False},
        "cta": {"uses_real_thumbnail": True, "burned_in_url": False,
                "clickable_link_claim": False},
    }
    TIMELINE_JSON.write_text(json.dumps(timeline, indent=2, ensure_ascii=False), encoding="utf-8")
    return total, global_words, groups, starts, caption_state


def make_venn_layers():
    A_BOX = (115, 530, 635, 1050)
    B_BOX = (445, 530, 965, 1050)

    fill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fill)
    fd.ellipse(A_BOX, fill=TEAL + (26,))
    fd.ellipse(B_BOX, fill=BLUE + (26,))

    strong = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(strong)
    sd.ellipse(A_BOX, fill=TEAL + (50,))
    sd.ellipse(B_BOX, fill=BLUE + (50,))

    mask_a = Image.new("L", (W, H), 0)
    mask_b = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask_a).ellipse(A_BOX, fill=255)
    ImageDraw.Draw(mask_b).ellipse(B_BOX, fill=255)
    overlap = ImageChops.multiply(mask_a, mask_b)
    overlap_alpha = overlap.point(lambda v: int(v * 0.30))
    gold = Image.new("RGBA", (W, H), GOLD + (0,))
    gold.putalpha(overlap_alpha)

    outline = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(outline)
    od.ellipse(A_BOX, outline=TEAL + (235,), width=7)
    od.ellipse(B_BOX, outline=BLUE + (235,), width=7)
    center(od, 205, 590, "A", 44, TEAL, True)
    center(od, 875, 590, "B", 44, BLUE, True)
    return fill, strong, gold, outline


def pop_chip(d, x, y, label, color, t, start, r=50, size=44, delay=0.0):
    p = spring((t - start - delay) / 0.65)
    if p <= 0:
        return
    chip(d, x, y, label, color, r=max(4, int(r * p)), size=size)


def draw_number_set(d, t, mode):
    specs = [
        ("1", 270, 790, TEAL),
        ("2", 485, 725, GOLD),
        ("3", 580, 855, GOLD),
        ("4", 810, 790, BLUE),
    ]
    for i, (label, x, y, color) in enumerate(specs):
        if mode == "hook":
            pop_chip(d, x, y, label, color, t, 0.25, delay=i * 0.22)
            continue
        highlight = False
        dim = False
        if mode == "a1":
            highlight = label in ("2", "3")
            dim = not highlight
        elif mode == "a2":
            highlight = True
        elif mode in ("q3", "a3"):
            highlight = label == "4"
            dim = label != "4"
        col = color if not dim else FAINT
        r = 58 if highlight and mode in ("a1", "q3", "a3") else 50
        chip(d, x, y, label, col, r=r, size=46,
             fill=(16, 32, 51) if not highlight else (42, 38, 27))


def draw_venn(im, t, mode, layers):
    fill, strong, gold, outline = layers
    im.alpha_composite(strong if mode in ("q2", "a2") else fill)
    if mode in ("q1", "a1", "q3", "a3"):
        # Pulse the shared lens while the question/answer is on screen.
        pulse = 0.75 + 0.25 * math.sin(t * 3.0)
        lens = gold.copy()
        lens.putalpha(gold.getchannel("A").point(lambda a: int(a * pulse)))
        im.alpha_composite(lens)
    im.alpha_composite(outline)
    d = ImageDraw.Draw(im)
    draw_number_set(d, t, mode)
    if mode == "a3":
        # A clear cross over the overlap: four is not shared by both sets.
        d.line((455, 700, 625, 880), fill=RED, width=12)
        d.line((625, 700, 455, 880), fill=RED, width=12)
    return d


def draw_formula(d, kind, y):
    center(d, 220, y, "A", 78, TEAL, True)
    if kind == "intersection":
        draw_cap(d, 390, y, 92, 58, GOLD, 12)
    else:
        draw_cup(d, 390, y, 92, 58, GOLD, 12)
    center(d, 560, y, "B", 78, BLUE, True)
    center(d, 810, y, "=  ?", 74, GOLD, True)


def draw_think(d, pause_t):
    center(d, 540, 1150, "TAKE A MOMENT", 34, GOLD, True)
    for i in range(3):
        phase = (pause_t * 2.2 - i * 0.35) % 1.0
        r = 9 + 7 * math.sin(math.pi * phase)
        alpha = int(90 + 150 * math.sin(math.pi * phase))
        x = 470 + i * 70
        d.ellipse((x - r, 1230 - r, x + r, 1230 + r), fill=TEAL + (alpha,))


def draw_brand_bar(im, t, total, avatar_small):
    im.alpha_composite(avatar_small, (60, 242))
    d = ImageDraw.Draw(im)
    text(d, (140, 248), "KNOWLUMO", 28, WHITE, True)
    text(d, (140, 286), "CSCA MATH  ·  SETS QUIZ", 18, FAINT, True)
    d.rounded_rectangle((60, 330, 1020, 338), 4, fill=LINE)
    p = max(0.0, min(1.0, t / total))
    d.rounded_rectangle((60, 330, 60 + int(960 * p), 338), 4, fill=TEAL)
    return d


def draw_captions(im, t, words, groups, starts, caption_state):
    group, active = caption_state(t)
    if group is None:
        return
    visible_indices = [i for i in group["indices"] if i <= active]
    if not visible_indices:
        return
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    rounded(d, (60, 1360, 1020, 1600), 28, (5, 12, 24, 225), LINE + (190,), 2)
    f = font(42, True)
    lines, cur = [], []
    for i in visible_indices:
        trial = " ".join([words[j]["word"] for j in cur + [i]])
        if cur and f.getlength(trial) > 900:
            lines.append(cur)
            cur = [i]
        else:
            cur.append(i)
    if cur:
        lines.append(cur)
    lines = lines[:3]
    line_y = 1395 if len(lines) >= 3 else (1410 if len(lines) == 2 else 1460)
    for indices in lines:
        parts = [words[i]["word"] for i in indices]
        widths = [f.getlength(p) for p in parts]
        total_w = sum(widths) + 18 * (len(parts) - 1)
        x = (W - total_w) / 2
        for idx, part, pw in zip(indices, parts, widths):
            color = TEAL if idx == active else WHITE
            d.text((x, line_y), part, font=f, fill=color,
                   stroke_width=3, stroke_fill=(3, 8, 16))
            x += pw + 18
        line_y += 62
    im.alpha_composite(overlay)


def draw_hook(d, seg_t):
    center(d, 540, 400, "TWO SETS  ·  TWO QUICK QUESTIONS", 38, GOLD, True)
    p1 = ease(seg_t / 0.6)
    p2 = ease((seg_t - 0.25) / 0.6)
    x1 = -1000 + 1000 * p1
    x2 = 1000 - 1000 * p2
    rounded(d, (x1 + 80, 500, x1 + 1000, 740), 30, (15, 30, 48), TEAL + (180,), 3)
    center(d, x1 + 540, 585, "A  =  { 1, 2, 3 }", 62, TEAL, True)
    text(d, (x1 + 120, 665), "SET A", 22, FAINT, True)
    rounded(d, (x2 + 80, 800, x2 + 1000, 1040), 30, (15, 30, 48), BLUE + (180,), 3)
    center(d, x2 + 540, 885, "B  =  { 2, 3, 4 }", 62, BLUE, True)
    text(d, (x2 + 120, 965), "SET B", 22, FAINT, True)
    center(d, 540, 1160, "CAN YOU GET THEM ALL?", 42, WHITE, True)


def draw_question(d, kind, pause, pause_t):
    header = {"q1": "QUESTION 1", "q2": "QUESTION 2", "q3": "LAST CHECK"}[kind]
    center(d, 540, 390, header, 42, TEAL, True)
    if kind in ("q1", "q2"):
        draw_formula(d, "intersection" if kind == "q1" else "union", 490)
    else:
        center(d, 540, 490, "4  ∈  A  ∩  B  ?", 62, GOLD, True)
    if pause:
        draw_think(d, pause_t)
    else:
        hint = {"q1": "WHICH ELEMENTS ARE SHARED?",
                "q2": "WHICH ELEMENTS APPEAR AT LEAST ONCE?",
                "q3": "IS FOUR IN THE OVERLAP?"}[kind]
        center(d, 540, 1150, hint, 30, FAINT, True)


def draw_answer(d, kind, seg_t):
    header = "ANSWER"
    center(d, 540, 390, header, 42, TEAL, True)
    if kind == "a1":
        center(d, 540, 490, "{ 2, 3 }", 96, GOLD, True)
        center(d, 540, 1140, "INTERSECTION  =  BOTH SETS", 32, WHITE, True)
        for i, label in enumerate(("2", "3")):
            pop_chip(d, 455 + i * 170, 1230, label, GOLD, seg_t, 0.15, delay=i * 0.18, r=44, size=40)
    elif kind == "a2":
        center(d, 540, 490, "{ 1, 2, 3, 4 }", 82, GOLD, True)
        center(d, 540, 1140, "UNION  =  EVERY ELEMENT ONCE", 32, WHITE, True)
        for i, label in enumerate(("1", "2", "3", "4")):
            pop_chip(d, 225 + i * 210, 1230, label, [TEAL, BLUE, GOLD, TEAL][i],
                     seg_t, 0.15, delay=i * 0.16, r=44, size=40)
    else:
        center(d, 540, 485, "NO", 120, RED, True)
        center(d, 540, 1140, "4  ∈  B     ·     4  ∉  A", 42, WHITE, True)
        center(d, 540, 1230, "NOT IN BOTH SETS", 34, GOLD, True)


def draw_cta(im, seg_t, thumb, avatar_small):
    d = ImageDraw.Draw(im)
    center(d, 540, 385, "WANT THE FULL LESSON?", 44, GOLD, True)
    p = ease(seg_t / 0.8)
    y = 440 + int((1 - p) * 90)
    rounded(d, (70, y, 1010, y + 790), 34, (13, 27, 45), TEAL + (150,), 3)
    im.alpha_composite(thumb, (100, y + 40))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((100, y + 40, 980, y + 535), 24, outline=GOLD + (190,), width=3)
    center(d, 540, y + 590, "CSCA MATH  ·  EPISODE 01", 34, WHITE, True)
    center(d, 540, y + 642, "SETS MADE SIMPLE", 46, GOLD, True)
    im.alpha_composite(avatar_small, (100, y + 690))
    d = ImageDraw.Draw(im)
    text(d, (165, y + 698), "Knowlumo", 30, TEAL, True)
    center(d, 540, y + 755, "FULL LESSON ON KNOWLUMO", 26, FAINT, True)


def render_frame(t, total, words, groups, starts, caption_state, assets):
    base, venn_layers, thumb, avatar_small = assets
    im = base.copy().convert("RGBA")
    d = draw_brand_bar(im, t, total, avatar_small)

    if t < LEAD:
        center(d, 540, 760, "SETS", 130, WHITE, True, 5)
        center(d, 540, 900, "QUICK QUIZ", 58, TEAL, True)
        center(d, 540, 1010, "THREE QUESTIONS", 32, GOLD, True)
    else:
        seg = None
        for s in SEGMENTS:
            if t < s["end"] + s["pause"]:
                seg = s
                break
        if seg is None:
            seg = SEGMENTS[-1]
        seg_t = t - seg["start"]
        in_pause = t >= seg["end"]
        pause_t = max(0.0, t - seg["end"])
        visual = seg["visual"]

        if visual == "hook":
            draw_hook(d, seg_t)
        elif visual in ("q1", "q2", "q3"):
            d = draw_venn(im, t, visual, venn_layers)
            draw_question(d, visual, in_pause, pause_t)
        elif visual in ("a1", "a2", "a3"):
            d = draw_venn(im, t, visual, venn_layers)
            draw_answer(d, visual, seg_t)
        elif visual == "cta":
            draw_cta(im, seg_t, thumb, avatar_small)

    draw_captions(im, t, words, groups, starts, caption_state)
    alpha = min(1.0, t / 0.35, (total - t) / 0.5)
    if alpha < 1.0:
        im = Image.blend(Image.new("RGBA", (W, H), (4, 9, 18, 255)), im, max(0.0, alpha))
    return im.convert("RGB")


def build_assets():
    base = grid_background(W, H, step=72, base=NAVY, line=(17, 29, 48))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for y in range(H):
        a = int(30 * (y / H))
        ld.line((0, y, W, y), fill=INK + (a,))
    base = Image.alpha_composite(base, layer)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((140, 420, 940, 1220), fill=BLUE + (22,))
    glow = glow.filter(ImageFilter.GaussianBlur(140))
    base = Image.alpha_composite(base, glow)

    thumb = Image.open(THUMB).convert("RGBA").resize((880, 495), Image.Resampling.LANCZOS)
    mask = Image.new("L", (880, 495), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 880, 495), 24, fill=255)
    thumb.putalpha(mask)
    avatar_small = Image.open(AVATAR).convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
    return base, make_venn_layers(), thumb, avatar_small


def encode(total, words, groups, starts, caption_state):
    assets = build_assets()
    cmd = [FF, "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(MASTER_WAV),
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-profile:v", "high",
           "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
           "-movflags", "+faststart", "-shortest", str(FINAL_MP4)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    frames = int(math.ceil(total * FPS))
    try:
        for i in range(frames):
            t = i / FPS
            frame = render_frame(t, total, words, groups, starts, caption_state, assets)
            proc.stdin.write(frame.tobytes())
    finally:
        proc.stdin.close()
    code = proc.wait()
    if code != 0:
        raise RuntimeError(f"ffmpeg Shorts encode failed: {code}")
    # Full decode verification.
    dec = subprocess.run([FF, "-v", "error", "-i", str(FINAL_MP4), "-f", "null", "-"],
                         capture_output=True, text=True)
    if dec.returncode != 0 or dec.stderr.strip():
        raise RuntimeError(f"Shorts decode verification failed: {dec.stderr}")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total, words, groups, starts, caption_state = build_audio_and_timeline()
    encode(total, words, groups, starts, caption_state)
    print(f"Duration: {total:.2f}s")
    print(f"Frames:   {int(math.ceil(total * FPS))} @ {FPS} FPS")
    print(f"Wrote {FINAL_MP4}")
    print(f"Wrote {TIMELINE_JSON}")


if __name__ == "__main__":
    main()
