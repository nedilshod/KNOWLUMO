#!/usr/bin/env python3
"""Programmatic QA for the animation-rich Episode 02 draft.

Checks: stream metadata, full decode, WAV-driven subtitle/timeline invariants,
answer timing, and real inter-frame motion at 30 FPS (not duplicated frames).
It cannot replace by-eye/by-ear playback review before publication.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "episode02"
MP4 = OUT / "CSCA_Math_02_Subsets_Complements_Animated.mp4"
TIMELINE = OUT / "animation_timeline.json"
METADATA = OUT / "EPISODE_02_EN.txt"
REPORT = OUT / "animation_verification.json"
FF = imageio_ffmpeg.get_ffmpeg_exe()

SW, SH, SAMPLE_FPS = 320, 180, 10
FRAME_BYTES = SW * SH * 3


def probe():
    r = subprocess.run([FF, "-i", str(MP4)], capture_output=True, text=True)
    s = r.stderr
    checks = {
        "h264": "h264" in s.lower(),
        "aac": "aac" in s.lower(),
        "1280x720": "1280x720" in s,
        "30_fps": "30 fps" in s,
        "44100_hz": "44100 Hz" in s,
        "stereo": "stereo" in s.lower(),
    }
    assert all(checks.values()), f"Stream probe failed: {checks}\n{s[-1200:]}"
    return checks


def full_decode():
    r = subprocess.run([FF, "-v", "error", "-i", str(MP4), "-f", "null", "-"],
                       capture_output=True, text=True)
    assert r.returncode == 0, f"Full decode failed: {r.stderr}"
    return True


def timeline_checks():
    tl = json.loads(TIMELINE.read_text())
    assert tl["status"] == "animated draft"
    assert tl["fps"] == 30
    assert tl["target_duration"] == 300.0
    assert tl["resolution"] == [1280, 720]
    assert len(tl["chapters"]) == 10
    assert len(tl["visual_beats"]) == 10
    beats = sum(len(b) for b in tl["visual_beats"])
    assert beats >= 70, f"Too few semantic beats: {beats}"
    assert tl["checks"]["no_future_words"] is True
    assert tl["checks"]["last_group_holds"] is True
    assert tl["checks"]["answer_hidden_until_solution"] is True
    assert tl["checks"]["semantic_beats_from_wav"] is True
    assert tl["answer_reveal_at"] > tl["practice_question_end"]
    assert tl["answer_reveal_at"] > tl["solution_scene_start"]
    assert tl["answer_reveal_at"] < tl["chapters"][8]["end"]
    assert tl["caption_safe_zone"][1] >= 600
    text = METADATA.read_text() + "\n" + TIMELINE.read_text()
    assert not re.search(r"https?://|www\.", text), "Invented URL found"
    return {
        "fps": tl["fps"],
        "duration": tl["target_duration"],
        "resolution": tl["resolution"],
        "chapters": len(tl["chapters"]),
        "semantic_beats": beats,
        "answer_reveal_at": tl["answer_reveal_at"],
        "practice_question_end": tl["practice_question_end"],
        "caption_safe_zone": tl["caption_safe_zone"],
        "no_future_words": True,
        "last_group_holds": True,
        "answer_hidden_until_solution": True,
        "no_invented_url": True,
    }


def motion_checks(tl):
    cmd = [FF, "-v", "error", "-i", str(MP4),
           "-vf", f"fps={SAMPLE_FPS},scale={SW}:{SH}",
           "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    diffs, times = [], []
    duplicates = 0
    prev = None
    frame_index = 0
    try:
        while True:
            buf = proc.stdout.read(FRAME_BYTES)
            if len(buf) < FRAME_BYTES:
                break
            cur = np.frombuffer(buf, dtype=np.uint8).astype(np.int16)
            if prev is not None:
                t = frame_index / SAMPLE_FPS
                diffs.append((t, float(np.abs(cur - prev).mean())))
                times.append(t)
                if np.array_equal(cur, prev):
                    duplicates += 1
            prev = cur
            frame_index += 1
    finally:
        proc.stdout.close()
        proc.wait()
    assert frame_index >= 2900, f"Too few decoded sample frames: {frame_index}"
    assert diffs, "No frame differences decoded"

    all_d = np.array([d for _, d in diffs])
    overall = float(all_d.mean())
    overall_p95 = float(np.percentile(all_d, 95))
    duplicate_ratio = duplicates / len(diffs)
    # A calm dark frame has a low mean; require no duplicates, continuous
    # micro-motion, and clear semantic peaks instead of a noisy slideshow.
    assert duplicate_ratio < 0.01, f"Too many identical frames: {duplicate_ratio:.4f}"
    assert overall > 0.20, f"Overall motion too weak: {overall:.3f}"
    assert overall_p95 > 0.70, f"Overall semantic peaks too weak: {overall_p95:.3f}"

    scene_stats = []
    for i, c in enumerate(tl["chapters"], 1):
        ds = [d for t, d in diffs if c["start"] <= t < c["end"]]
        assert ds, f"No motion samples in scene {i}"
        a = np.array(ds)
        mean = float(a.mean())
        p95 = float(np.percentile(a, 95))
        mx = float(a.max())
        micro_ratio = float((a > 0.08).mean())
        semantic_ratio = float((a > 0.50).mean())
        assert mean > 0.15, f"Scene {i} looks static: mean {mean:.3f}"
        assert p95 > 0.60, f"Scene {i} lacks clear peaks: p95 {p95:.3f}"
        assert mx > 0.80, f"Scene {i} lacks a semantic action: max {mx:.3f}"
        assert micro_ratio > 0.18, f"Scene {i} has too little continuous motion: {micro_ratio:.3f}"
        assert semantic_ratio > 0.10, f"Scene {i} has too few visible state changes: {semantic_ratio:.3f}"
        scene_stats.append({
            "scene": i,
            "title": c["title"],
            "samples": len(ds),
            "mean_frame_diff": round(mean, 3),
            "p95_frame_diff": round(p95, 3),
            "max_frame_diff": round(mx, 3),
            "continuous_motion_ratio": round(micro_ratio, 3),
            "semantic_peak_ratio": round(semantic_ratio, 3),
        })
    return {
        "sample_fps": SAMPLE_FPS,
        "sample_resolution": [SW, SH],
        "decoded_frames": frame_index,
        "compared_pairs": len(diffs),
        "overall_mean_frame_diff": round(overall, 3),
        "overall_p95_frame_diff": round(overall_p95, 3),
        "duplicate_frame_ratio": round(duplicate_ratio, 4),
        "scenes": scene_stats,
    }


def main():
    stream = probe()
    decode = full_decode()
    timeline = timeline_checks()
    tl = json.loads(TIMELINE.read_text())
    motion = motion_checks(tl)
    REPORT.write_text(json.dumps({
        "status": "passed",
        "file": MP4.name,
        "stream": stream,
        "full_decode": decode,
        "timeline": timeline,
        "motion": motion,
        "manual_checks_pending": [
            "by-eye/by-ear playback of subtitle timing and short words",
            "sentence endings and scene transitions in a real player",
            "readability of formulas and captions on a phone",
            "platform UI overlay after upload",
            "real end screen / related video setup after publication",
        ],
        "published": False,
    }, indent=2), encoding="utf-8")
    print("ALL CHECKS PASSED")
    print(f"Decoded sample frames: {motion['decoded_frames']} @ {SAMPLE_FPS} FPS")
    print(f"Overall mean / p95 frame diff: {motion['overall_mean_frame_diff']} / {motion['overall_p95_frame_diff']}")
    print(f"Duplicate frame ratio: {motion['duplicate_frame_ratio']}")
    print(f"Semantic beats: {timeline['semantic_beats']}")
    print(f"Answer reveal: {timeline['answer_reveal_at']:.2f}s")


if __name__ == "__main__":
    main()
