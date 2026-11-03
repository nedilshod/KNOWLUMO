#!/usr/bin/env python3
"""Append a branded Knowlumo subscribe outro to the existing Episode 01 MP4.

The original lesson is kept untouched in sources/. This script renders a new
12-second 1280x720 / 30 FPS outro with the selected round avatar centered,
energy-based English captions, a static subscribe graphic, and new narration.
It then concatenates the original and the outro without cutting either one.
"""
from __future__ import annotations

import bisect
import math
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_utils import (BLUE, FAINT, GOLD, INK, LINE, NAVY, TEAL, WHITE,
                         caption_groups, center, chime, font, grid_background,
                         read_wav_mono, rounded, text, word_timings,
                         write_stereo_wav)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sources" / "Youtube-arena-01b47ded-youtube" / "csca" / "episode01" / "output" / "CSCA_Math_01_Sets_Full.mp4"
AVATAR = ROOT / "sources" / "Youtube-arena-01b47ded-youtube" / "channel" / "knowlumo" / "assets" / "avatar_round_800.png"
VOICE = ROOT / "output" / "episode01" / "audio" / "outro_voice.wav"
OUT_DIR = ROOT / "output" / "episode01"
OUTRO_MP4 = OUT_DIR / "CSCA_Math_01_Sets_Outro.mp4"
MASTER_WAV = OUT_DIR / "audio" / "outro_master.wav"
FINAL_MP4 = OUT_DIR / "CSCA_Math_01_Sets_Full_With_Outro.mp4"
CONCAT = ROOT / "build" / "concat_outro.txt"

FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1280, 720, 30
DURATION = 12.0
LEAD = 0.8
OUTRO_TEXT = "Thanks for learning with Knowlumo. Subscribe for more visual lessons, and keep exploring, one idea at a time."


def probe_duration(path: Path) -> float:
    p = subprocess.run([FF, "-hide_banner", "-i", str(path)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", p.stderr)
    if not m:
        raise RuntimeError(f"Could not read duration: {path}")
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def build_audio():
    voice, sr = read_wav_mono(VOICE)
    words, clip_dur = word_timings(VOICE, OUTRO_TEXT)
    n = int(round(DURATION * sr))
    master = np.zeros(n, dtype=np.float32)
    offset = int(round(LEAD * sr))
    master[offset:offset + len(voice)] += voice
    # Soft reveal chime before the voice starts.
    c = chime(sr, duration=0.55, base=523.25, volume=0.055)
    cstart = int(round(0.30 * sr))
    master[cstart:cstart + len(c)] += c
    # Gentle audio fade-out; never a hard cut.
    fade = int(round(0.8 * sr))
    if fade > 0:
        master[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
    write_stereo_wav(MASTER_WAV, master, sr)

    global_words = [{"word": w["word"], "start": LEAD + w["start"], "end": LEAD + w["end"]}
                    for w in words]
    groups = caption_groups(global_words, max_words=5)
    starts = [w["start"] for w in global_words]
    return sr, global_words, groups, starts


def wrap_words(d, words, max_width, size, bold=True):
    f = font(size, bold)
    lines, cur = [], []
    for w in words:
        trial = " ".join(cur + [w])
        if cur and f.getlength(trial) > max_width:
            lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    return lines


def draw_captions(im, t, words, groups, starts):
    if not words or t < starts[0]:
        return
    active = bisect.bisect_right(starts, t) - 1
    if active < 0:
        return
    group = next(g for g in groups if g["indices"][0] <= active <= g["indices"][-1])
    visible = [words[i]["word"] for i in group["indices"] if i <= active]
    current_idx = active
    if not visible:
        return

    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    rounded(d, (80, 608, 1200, 694), 20, (5, 12, 24, 218), LINE + (180,), 2)
    f = font(29, True)
    lines, cur, cur_indices = [], [], []
    for i in group["indices"]:
        if i > current_idx:
            break
        trial = " ".join([words[j]["word"] for j in cur_indices + [i]])
        if cur and f.getlength(trial) > 1010:
            lines.append(list(cur_indices))
            cur_indices = [i]
        else:
            cur_indices.append(i)
    if cur_indices:
        lines.append(list(cur_indices))
    lines = lines[:2]

    line_y = 625 if len(lines) == 2 else 640
    for indices in lines:
        parts = [words[i]["word"] for i in indices]
        widths = [f.getlength(p) for p in parts]
        total = sum(widths) + 14 * (len(parts) - 1)
        x = (W - total) / 2
        for idx, part, pw in zip(indices, parts, widths):
            color = TEAL if idx == current_idx else WHITE
            d.text((x, line_y), part, font=f, fill=color,
                   stroke_width=2, stroke_fill=(3, 8, 16))
            x += pw + 14
        line_y += 41
    im.alpha_composite(overlay)


def render_frame(t, alpha, words, groups, starts, base_bg, avatar_full, particles):
    im = base_bg.copy().convert("RGBA")
    d = ImageDraw.Draw(im)

    # Small series label, kept away from the centered avatar.
    text(d, (54, 42), "KNOWLUMO", 22, WHITE, True)
    text(d, (54, 72), "CSCA MATH  ·  EPISODE 01", 16, FAINT, True)
    rounded(d, (1088, 40, 1226, 82), 20, (18, 43, 58, 220), TEAL + (180,), 2)
    center(d, 1157, 61, "THANK YOU", 16, TEAL, True)

    # Pulsing halo and centered round avatar.
    pulse = 1.0 + 0.018 * math.sin(2 * math.pi * t / 2.4)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    r = int(175 * pulse)
    gd.ellipse((640 - r, 292 - r, 640 + r, 292 + r), outline=TEAL + (95,), width=12)
    glow = glow.filter(ImageFilter.GaussianBlur(22))
    im = Image.alpha_composite(im, glow)
    d = ImageDraw.Draw(im)

    scale = 0.82 + 0.18 * min(1.0, t / 0.9)
    size = int(290 * scale * pulse)
    av = avatar_full.resize((size, size), Image.Resampling.LANCZOS)
    im.alpha_composite(av, (640 - size // 2, 292 - size // 2))
    d = ImageDraw.Draw(im)

    # Static subscribe graphic; it is artwork, not a YouTube end-screen element.
    p = min(1.0, max(0.0, (t - 1.6) / 0.7))
    if p > 0.05:
        y = 470 + int((1 - p) * 18)
        subs = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(subs)
        rounded(sd, (455, y, 825, y + 64), 32, GOLD + (int(235 * p),), None)
        center(sd, 640, y + 32, "SUBSCRIBE", 31, NAVY + (int(255 * p),), True)
        im.alpha_composite(subs)
        d = ImageDraw.Draw(im)

    center(d, 640, 558, "MORE VISUAL LESSONS", 24, WHITE, True)

    # Slow floating particles add motion without distracting from the logo.
    for i, (x0, y0, r0, speed, phase) in enumerate(particles):
        x = x0 + 18 * math.sin(t * 0.35 + phase)
        y = (y0 - t * speed) % H
        rr = 2 + (i % 3)
        c = TEAL if i % 2 == 0 else GOLD
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=c + (90,))

    draw_captions(im, t, words, groups, starts)

    # Global fade in / fade out.
    if alpha < 1.0:
        im = Image.blend(Image.new("RGBA", (W, H), (4, 9, 18, 255)), im, alpha)
    return im.convert("RGB")


def encode_outro(words, groups, starts):
    base_bg = grid_background(W, H, step=64, base=NAVY, line=(17, 29, 48))
    # Vertical colour lift toward the lower half.
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for y in range(H):
        a = int(38 * (y / H))
        ld.line((0, y, W, y), fill=INK + (a,))
    base_bg = Image.alpha_composite(base_bg, layer)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((420, 60, 860, 500), fill=BLUE + (34,))
    glow = glow.filter(ImageFilter.GaussianBlur(90))
    base_bg = Image.alpha_composite(base_bg, glow)

    avatar_full = Image.open(AVATAR).convert("RGBA").resize((320, 320), Image.Resampling.LANCZOS)
    rng = np.random.default_rng(7)
    particles = [(float(rng.uniform(40, W - 40)), float(rng.uniform(0, H)), 0,
                  float(rng.uniform(9, 22)), float(rng.uniform(0, 6.28))) for _ in range(26)]

    cmd = [FF, "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(MASTER_WAV),
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-profile:v", "high",
           "-pix_fmt", "yuv420p", "-r", str(FPS), "-video_track_timescale", "15360",
           "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
           "-movflags", "+faststart", "-shortest", str(OUTRO_MP4)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    frames = int(round(DURATION * FPS))
    try:
        for i in range(frames):
            t = i / FPS
            alpha = min(1.0, t / 0.7, (DURATION - t) / 0.8)
            alpha = max(0.0, alpha)
            frame = render_frame(t, alpha, words, groups, starts, base_bg, avatar_full, particles)
            proc.stdin.write(frame.tobytes())
    finally:
        proc.stdin.close()
    code = proc.wait()
    if code != 0:
        raise RuntimeError(f"ffmpeg outro encode failed: {code}")


def concat_copy():
    CONCAT.write_text(
        f"file '{SOURCE.resolve().as_posix()}'\nfile '{OUTRO_MP4.resolve().as_posix()}'\n",
        encoding="utf-8")
    cmd = [FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
           "-i", str(CONCAT), "-c", "copy", "-movflags", "+faststart", str(FINAL_MP4)]
    return subprocess.run(cmd, capture_output=True, text=True)


def concat_reencode():
    cmd = [FF, "-y", "-loglevel", "error", "-i", str(SOURCE), "-i", str(OUTRO_MP4),
           "-filter_complex", "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]",
           "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "20", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-video_track_timescale", "15360", "-c:a", "aac", "-b:a", "128k",
           "-ar", "44100", "-ac", "2", "-movflags", "+faststart", str(FINAL_MP4)]
    return subprocess.run(cmd, capture_output=True, text=True)


def verify_final():
    info = subprocess.run([FF, "-hide_banner", "-i", str(FINAL_MP4)], capture_output=True, text=True).stderr
    assert "Video: h264" in info, info
    assert "30 fps" in info, info
    assert "Audio: aac" in info, info
    decode = subprocess.run([FF, "-v", "error", "-i", str(FINAL_MP4), "-f", "null", "-"],
                            capture_output=True, text=True)
    return decode.returncode == 0 and not decode.stderr.strip(), decode.stderr


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sr, words, groups, starts = build_audio()
    encode_outro(words, groups, starts)
    res = concat_copy()
    if res.returncode != 0:
        print("Stream-copy concat failed; re-encoding for A/V continuity.", res.stderr)
        res = concat_reencode()
        if res.returncode != 0:
            raise RuntimeError(res.stderr)
    ok, err = verify_final()
    if not ok:
        print("Stream-copy output did not fully decode; re-encoding for A/V continuity.", err)
        res = concat_reencode()
        if res.returncode != 0:
            raise RuntimeError(res.stderr)
        ok, err = verify_final()
        if not ok:
            raise RuntimeError(f"Final MP4 failed verification: {err}")
    print(f"Original: {probe_duration(SOURCE):.2f}s")
    print(f"Outro:    {probe_duration(OUTRO_MP4):.2f}s")
    print(f"Final:    {probe_duration(FINAL_MP4):.2f}s")
    print(f"Wrote {FINAL_MP4}")


if __name__ == "__main__":
    main()
