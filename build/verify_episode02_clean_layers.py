#!/usr/bin/env python3
"""QA wrapper for the clean-layer Episode 02 rebuild.

Reuses stream/full-decode/motion/subtitle checks from
verify_episode02_animation.py, then adds explicit layer-order checks.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_episode02_animation as v

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "episode02"

v.MP4 = OUT / "CSCA_Math_02_Subsets_Complements_Clean.mp4"
v.TIMELINE = OUT / "clean_layer_timeline.json"
v.METADATA = OUT / "EPISODE_02_EN.txt"
v.REPORT = OUT / "clean_layer_verification.json"


def layering_checks():
    tl = json.loads(v.TIMELINE.read_text())
    cl = tl.get("clean_layers", {})
    expected_order = ["background", "main_panel", "nested_panels",
                      "objects", "labels", "outro", "captions"]
    assert cl.get("background_source") == "procedural grid only"
    assert cl.get("ai_photo_background_in_video") is False
    assert cl.get("opaque_panels") is True
    assert cl.get("clipped_objects") is True
    assert cl.get("translucent_effects_on_separate_layers") is True
    assert cl.get("circular_avatar_mask") is True
    assert cl.get("z_index_order") == expected_order

    audit = json.loads((OUT / "clean_layer_audit.json").read_text())
    assert audit["status"] == "passed"
    assert audit["violations"] == 0
    assert audit["checked_objects"] > 100
    assert all(c["within_parent"] for c in audit["checks"])

    src = Path(ROOT / "build" / "build_episode02_clean_layers.py").read_text()
    assert "episode02_background.png" not in src
    assert "load_background" not in src
    assert "BG_IMG" not in src
    assert "shade_outside" in src
    assert "mask" in src
    assert "mix(" in src
    assert "ensure(" in src

    return {
        "procedural_background_only": True,
        "no_ai_photo_background": True,
        "opaque_panels": True,
        "objects_inside_parents": True,
        "translucent_shading_on_separate_layers": True,
        "circular_avatar_mask": True,
        "z_index_order": expected_order,
        "checked_object_bounds": audit["checked_objects"],
        "bounds_violations": audit["violations"],
    }


def main():
    v.main()
    layering = layering_checks()
    report = json.loads(v.REPORT.read_text())
    report["layering"] = layering
    report["status"] = "passed"
    v.REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("CLEAN LAYER CHECKS PASSED")
    print(f"Checked object bounds: {layering['checked_object_bounds']}")
    print(f"Bounds violations: {layering['bounds_violations']}")


if __name__ == "__main__":
    main()
