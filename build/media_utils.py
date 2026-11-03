#!/usr/bin/env python3
"""Shared audio alignment and drawing helpers for Knowlumo video builds.

Word timings are estimated from each generated WAV's actual energy envelope:
word boundaries are placed near low-energy valleys inside the detected speech
span, rather than at a fixed average reading rate. This is not an ASR forced
alignment and should still be reviewed by eye/ear before publication.
"""
from __future__ import annotations

import math
import re
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

NAVY = (9, 17, 32)
INK = (17, 32, 53)
WHITE = (243, 248, 255)
TEAL = (95, 241, 209)
BLUE = (121, 170, 255)
GOLD = (255, 209, 124)
RED = (255, 135, 140)
FAINT = (155, 176, 201)
LINE = (41, 58, 80)


def font(size: int, bold: bool = False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size)


def text(d, xy, s, size, color=WHITE, bold=True, stroke=0, stroke_fill=(4, 9, 18), anchor=None):
    d.text(xy, s, font=font(size, bold), fill=color, stroke_width=stroke,
           stroke_fill=stroke_fill, anchor=anchor)


def center(d, cx, cy, s, size, color=WHITE, bold=True, stroke=0):
    f = font(size, bold)
    box = d.textbbox((0, 0), s, font=f)
    d.text((cx - (box[2] - box[0]) / 2, cy - (box[3] + box[1]) / 2), s,
           font=f, fill=color, stroke_width=stroke, stroke_fill=(4, 9, 18))


def rounded(d, box, r, fill, outline=None, width=1):
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)


def chip(d, cx, cy, label, color, r=44, size=38, fill=(16, 32, 51)):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill, outline=color, width=4)
    center(d, cx, cy, label, size, color, True)


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def spring(x):
    x = max(0.0, min(1.0, x))
    return 1 - ((1 - x) ** 2) * math.cos(x * math.pi * 2.0)


def draw_cap(d, cx, cy, w, h, color, width=9):
    """Vector intersection symbol ∩: arch with short downward legs."""
    pts = []
    for i in range(29):
        x = -w / 2 + w * i / 28
        u = 2 * x / w
        y = h / 2 - h * math.sqrt(max(0.0, 1 - u * u))
        pts.append((cx + x, cy + y))
    d.line(pts, fill=color, width=width, joint="curve")
    leg = h * 0.22
    d.line((cx - w / 2, cy + h / 2, cx - w / 2, cy + h / 2 + leg), fill=color, width=width)
    d.line((cx + w / 2, cy + h / 2, cx + w / 2, cy + h / 2 + leg), fill=color, width=width)


def draw_cup(d, cx, cy, w, h, color, width=9):
    """Vector union symbol ∪: bowl with short upward legs."""
    pts = []
    for i in range(29):
        x = -w / 2 + w * i / 28
        u = 2 * x / w
        y = -h / 2 + h * math.sqrt(max(0.0, 1 - u * u))
        pts.append((cx + x, cy + y))
    d.line(pts, fill=color, width=width, joint="curve")
    leg = h * 0.22
    d.line((cx - w / 2, cy - h / 2, cx - w / 2, cy - h / 2 - leg), fill=color, width=width)
    d.line((cx + w / 2, cy - h / 2, cx + w / 2, cy - h / 2 - leg), fill=color, width=width)


def grid_background(w, h, step=64, base=NAVY, line=(17, 29, 48), glow=None):
    im = Image.new("RGBA", (w, h), base + (255,))
    d = ImageDraw.Draw(im)
    for x in range(0, w, step):
        d.line((x, 0, x, h), fill=line + (120,), width=1)
    for y in range(0, h, step):
        d.line((0, y, w, y), fill=line + (120,), width=1)
    if glow:
        gx, gy, radius, color, alpha = glow
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.ellipse((gx - radius, gy - radius, gx + radius, gy + radius), fill=color + (alpha,))
        from PIL import ImageFilter
        layer = layer.filter(ImageFilter.GaussianBlur(radius // 3))
        im = Image.alpha_composite(im, layer)
    return im


def read_wav_mono(path: Path):
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        channels = w.getnchannels()
        width = w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width != 2:
        raise ValueError(f"Expected 16-bit PCM WAV: {path}")
    data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    return data, sr


def tokenize(text_value: str):
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?[.,!?;:]*", text_value)


def word_timings(path: Path, spoken_text: str):
    """Estimate word starts/ends from the recorded waveform envelope."""
    samples, sr = read_wav_mono(path)
    duration = len(samples) / sr
    tokens = tokenize(spoken_text)
    if not tokens:
        return [], duration

    hop = int(sr * 0.010)
    win = int(sr * 0.020)
    if len(samples) < win:
        half = duration / max(1, len(tokens))
        return [{"word": t, "start": i * half, "end": (i + 1) * half}
                for i, t in enumerate(tokens)], duration
    count = 1 + (len(samples) - win) // hop
    env = np.empty(count, dtype=np.float32)
    for i in range(count):
        seg = samples[i * hop:i * hop + win]
        env[i] = float(np.sqrt(np.mean(seg * seg)))
    # Light smoothing keeps valleys meaningful without smearing short words.
    kernel = np.ones(3, dtype=np.float32) / 3
    smooth = np.convolve(env, kernel, mode="same")

    peak = float(np.max(smooth))
    floor = float(np.percentile(smooth, 12))
    threshold = max(peak * 0.055, floor * 2.2, 0.0025)
    voiced_mask = (smooth > threshold).astype(np.uint8)

    # Bridge tiny dropouts inside words, but keep genuine sentence pauses.
    padded = np.pad(voiced_mask, (1, 1))
    edges = np.diff(padded)
    false_starts = np.flatnonzero(edges == -1)
    false_ends = np.flatnonzero(edges == 1)
    for a, b in zip(false_starts, false_ends):
        if b - a <= 8:  # <= 80 ms
            voiced_mask[a:b] = 1

    active = np.flatnonzero(voiced_mask)
    if len(active) == 0:
        speech_start, speech_end = 0.0, duration
        voiced_time = np.cumsum(np.ones_like(smooth, dtype=np.float32)) * 0.010
    else:
        speech_start = max(0.0, active[0] * 0.010 - 0.020)
        speech_end = min(duration, (active[-1] + 1) * 0.010 + 0.020)
        voiced_time = np.cumsum(voiced_mask.astype(np.float32)) * 0.010
    if speech_end - speech_start < 0.25:
        speech_start, speech_end = 0.0, duration
        voiced_time = np.cumsum(np.ones_like(smooth, dtype=np.float32)) * 0.010

    letters = [len(re.sub(r"[^A-Za-z]", "", t)) for t in tokens]
    # Sub-linear length weighting keeps short closing words from being pushed
    # into trailing silence by long words such as "intersection".
    weights = np.array([0.9 + math.sqrt(n) + (0.45 if re.search(r"[.!?;:,]$", t) else 0.0)
                        for n, t in zip(letters, tokens)], dtype=np.float32)
    cumulative = np.cumsum(weights) / float(np.sum(weights))

    # Distribute boundaries over cumulative VOICED time. Long internal pauses
    # therefore never receive a word, which prevents captions from appearing
    # before the narrator resumes speaking.
    total_voiced = float(voiced_time[-1]) if len(voiced_time) else max(0.1, speech_end - speech_start)
    expected_frames = np.searchsorted(voiced_time, cumulative[:-1] * total_voiced, side="left")
    expected = np.clip(expected_frames.astype(np.float32) * 0.010,
                       speech_start, max(speech_start, speech_end - 0.10))

    # Small local valley adjustment, constrained to the voiced neighbourhood.
    search = 6  # +/- 60 ms
    starts = [speech_start]
    for expected_t in expected:
        idx = int(expected_t / 0.010)
        lo, hi = max(0, idx - search), min(len(smooth), idx + search + 1)
        scores = smooth[lo:hi] + 0.0030 * np.abs(np.arange(lo, hi) - idx)
        best = lo + int(np.argmin(scores))
        candidate = best * 0.010
        if voiced_mask[min(best, len(voiced_mask) - 1)] == 0:
            candidate = float(expected_t)
        starts.append(max(candidate, starts[-1] + 0.085))
    starts = [min(max(s, speech_start), max(speech_start, speech_end - 0.10)) for s in starts]
    starts[0] = speech_start
    ends = list(starts[1:]) + [speech_end]
    return [{"word": t, "start": float(s), "end": float(e)}
            for t, s, e in zip(tokens, starts, ends)], duration


def caption_groups(words, max_words=5):
    """Split a clip into short caption groups at punctuation or word limits."""
    groups, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        if len(cur) >= max_words or re.search(r"[.!?;:]$", w["word"]):
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    out = []
    for g in groups:
        out.append({
            "indices": g,
            "start": words[g[0]]["start"],
            "end": words[g[-1]]["end"],
        })
    return out


def chime(sr, duration=0.42, base=660.0, volume=0.075):
    t = np.arange(int(sr * duration), dtype=np.float32) / sr
    env = np.exp(-5.5 * t) * np.minimum(1.0, t * 80.0)
    tone = np.sin(2 * np.pi * base * t) + 0.5 * np.sin(2 * np.pi * base * 1.5 * t)
    return (tone * env * volume).astype(np.float32)


def write_stereo_wav(path: Path, mono: np.ndarray, sr: int):
    mono = np.clip(mono, -0.98, 0.98)
    stereo = np.repeat(mono[:, None], 2, axis=1)
    pcm = (stereo * 32767).astype("<i2")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
