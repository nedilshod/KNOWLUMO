#!/usr/bin/env python3
"""Automated checks for the Episode 01 delivery files."""
from __future__ import annotations

import json
import re
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
FF = imageio_ffmpeg.get_ffmpeg_exe()
FULL = ROOT / "output/episode01/CSCA_Math_01_Sets_Full_With_Outro.mp4"
OUTRO = ROOT / "output/episode01/CSCA_Math_01_Sets_Outro.mp4"
SHORTS = ROOT / "output/shorts/CSCA_Math_01_Sets_Shorts_1080x1920.mp4"
SOURCE = ROOT / "sources/Youtube-arena-01b47ded-youtube/csca/episode01/output/CSCA_Math_01_Sets_Full.mp4"
THUMB = ROOT / "output/episode01/CSCA_Math_01_Sets_Thumbnail_1280x720.png"
TIMELINE = ROOT / "output/shorts/timeline.json"


def probe(path: Path):
    p = subprocess.run([FF, "-hide_banner", "-i", str(path)], capture_output=True, text=True)
    s = p.stderr
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", s)
    assert dur, s
    duration = int(dur[1]) * 3600 + int(dur[2]) * 60 + float(dur[3])
    video_line = next((line for line in s.splitlines() if "Video: h264" in line), None)
    assert video_line, s
    video = re.search(r"(\d{3,5})x(\d{3,5}).*?(\d+) fps", video_line)
    assert video, video_line
    return {"duration": duration, "width": int(video[1]), "height": int(video[2]),
            "fps": int(video[3]), "has_audio": "Audio: aac" in s, "raw": s}


def decode_ok(path: Path):
    p = subprocess.run([FF, "-v", "error", "-i", str(path), "-f", "null", "-"],
                       capture_output=True, text=True)
    return p.returncode == 0 and not p.stderr.strip(), p.stderr


def main():
    checks = []

    full = probe(FULL)
    source = probe(SOURCE)
    outro = probe(OUTRO)
    shorts = probe(SHORTS)
    assert full["has_audio"] and shorts["has_audio"]
    assert full["width"] == 1280 and full["height"] == 720 and full["fps"] == 30
    assert shorts["width"] == 1080 and shorts["height"] == 1920 and shorts["fps"] == 30
    assert 300 < source["duration"] < full["duration"] < 360
    assert abs(full["duration"] - (source["duration"] + outro["duration"])) < 0.2
    assert 40 <= shorts["duration"] <= 180
    assert decode_ok(FULL)[0] and decode_ok(SHORTS)[0]
    checks.append("MP4 streams, durations, FPS, resolution, audio, full decode")

    with Image.open(THUMB) as im:
        assert im.size == (1280, 720)
    for name in ("thumbnail_preview_640x360.png", "thumbnail_preview_320x180.png"):
        p = ROOT / "output/episode01" / name
        assert p.exists(), p
    checks.append("Thumbnail 1280x720 and small-size previews")

    data = json.loads(TIMELINE.read_text(encoding="utf-8"))
    m = data["math"]
    A, B = set(m["A"]), set(m["B"])
    assert A & B == set(m["intersection"])
    assert A | B == set(m["union"])
    assert (4 in (A & B)) == m["four_in_intersection"]
    assert data["cta"]["uses_real_thumbnail"] and not data["cta"]["burned_in_url"]
    assert not data["cta"]["clickable_link_claim"]

    words = data["global_words"]
    groups = data["caption_groups"]
    starts = [w["start"] for w in words]
    for i, w in enumerate(words):
        active_before = sum(1 for s in starts if s <= w["start"] - 0.001) - 1
        assert active_before < i
        active_at = sum(1 for s in starts if s <= w["start"] + 0.001) - 1
        assert active_at >= i
        assert any(g["indices"][0] <= i <= g["indices"][-1] for g in groups)
    assert all(g["segment"] == words[g["indices"][0]]["segment"] for g in groups)
    segs = {s["key"]: s for s in data["segments"]}
    assert segs["a1"]["start"] > segs["q1"]["end"] + 2.0
    assert segs["a2"]["start"] > segs["q2"]["end"] + 2.0
    assert segs["a3"]["start"] > segs["q3"]["end"] + 1.5
    checks.append("Math answers, caption groups, no-future-word checks, thinking pauses, CTA flags")

    for rel in ("output/episode01/VIDEO_01_EN.txt", "output/shorts/SHORTS_01_EN.txt"):
        txt = (ROOT / rel).read_text(encoding="utf-8")
        assert not re.search(r"https?://|www\.", txt), rel
    timeline_txt = TIMELINE.read_text(encoding="utf-8")
    assert not re.search(r"https?://|www\.", timeline_txt)
    checks.append("No invented URL in public metadata or timing file")

    with wave.open(str(ROOT / "output/shorts/audio/shorts_master.wav"), "rb") as w:
        raw = w.readframes(w.getnframes())
        audio = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
        master_duration = w.getnframes() / w.getframerate()
    assert np.max(np.abs(audio)) <= 0.99
    assert master_duration > 50
    checks.append("Shorts master audio within range and long enough")

    assert (ROOT / "Youtube-arena-01b47ded-youtube.zip").exists()
    assert SOURCE.exists()
    checks.append("Original archive and untouched source lesson preserved")

    print("ALL CHECKS PASSED")
    for c in checks:
        print(" -", c)
    print(f"Full lesson: {full['duration']:.2f}s = source {source['duration']:.2f}s + outro {outro['duration']:.2f}s")
    print(f"Shorts: {shorts['duration']:.2f}s, {shorts['width']}x{shorts['height']}, {shorts['fps']} FPS")


if __name__ == "__main__":
    main()
