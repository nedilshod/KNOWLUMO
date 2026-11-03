#!/usr/bin/env python3
"""Build the reusable Episode 01 thumbnail template for the Knowlumo CSCA Math series.

The background is an AI-generated, text-free illustration. All words and the
brand mark are composited here with Pillow so the typography stays exact and
readable. Change EPISODE / SUBJECT / TOPIC / SUBTITLE / TAGS for later episodes.
"""
from pathlib import Path
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "episode01"
BG = ROOT / "build" / "thumbnail_background.png"
AVATAR = ROOT / "sources" / "Youtube-arena-01b47ded-youtube" / "channel" / "knowlumo" / "assets" / "avatar_round_800.png"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

W, H = 1280, 720
NAVY = (9, 17, 32)
INK = (17, 32, 53)
WHITE = (243, 248, 255)
TEAL = (95, 241, 209)
BLUE = (121, 170, 255)
GOLD = (255, 209, 124)
FAINT = (155, 176, 201)
LINE = (41, 58, 80)

EPISODE = "01"
PART = "01"
SUBJECT = "CSCA MATH"
TOPIC = "SETS"
SUBTITLE = "MADE SIMPLE"
TAGS = "INTERSECTION  •  UNION  •  VENN DIAGRAMS"


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size)


def text(d, xy, s, size, color=WHITE, bold=True, stroke=0, anchor=None):
    d.text(xy, s, font=font(size, bold), fill=color,
           stroke_width=stroke, stroke_fill=(4, 9, 18), anchor=anchor)


def center(d, cx, cy, s, size, color=WHITE, bold=True):
    f = font(size, bold)
    box = d.textbbox((0, 0), s, font=f)
    d.text((cx - (box[2] - box[0]) / 2, cy - (box[3] + box[1]) / 2), s,
           font=f, fill=color)


def rounded(d, box, r, fill, outline=None, width=1):
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)


def draw_cap(d, cx, cy, w, h, color, width=8):
    """Draw a clear vector intersection symbol ∩ (arch, opening downward)."""
    pts = []
    for i in range(25):
        x = -w / 2 + w * i / 24
        u = 2 * x / w
        y = h / 2 - h * math.sqrt(max(0.0, 1 - u * u))
        pts.append((cx + x, cy + y))
    d.line(pts, fill=color, width=width, joint="curve")
    leg = h * 0.20
    d.line((cx - w / 2, cy + h / 2, cx - w / 2, cy + h / 2 + leg), fill=color, width=width)
    d.line((cx + w / 2, cy + h / 2, cx + w / 2, cy + h / 2 + leg), fill=color, width=width)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bg = Image.open(BG).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS)

    # Darken the left half with a horizontal gradient so the large type stays
    # legible at small preview sizes without hiding the Venn illustration.
    grad = np.zeros((H, W, 4), dtype=np.uint8)
    alpha = np.clip((1 - np.linspace(0, 1, W)) * 215, 0, 215).astype(np.uint8)
    grad[..., 0], grad[..., 1], grad[..., 2] = NAVY
    grad[..., 3] = np.tile(alpha, (H, 1))
    bg = Image.alpha_composite(bg, Image.fromarray(grad, "RGBA"))

    # A subtle glow behind the centered brand mark area.
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((770, 110, 1260, 600), fill=(95, 241, 209, 18))
    glow = glow.filter(ImageFilter.GaussianBlur(80))
    bg = Image.alpha_composite(bg, glow)

    d = ImageDraw.Draw(bg)

    # Brand lockup: selected round avatar + wordmark.
    ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rd.ellipse((48, 38, 166, 156), outline=TEAL + (190,), width=4)
    ring = ring.filter(ImageFilter.GaussianBlur(7))
    bg = Image.alpha_composite(bg, ring)
    av = Image.open(AVATAR).convert("RGBA").resize((104, 104), Image.Resampling.LANCZOS)
    bg.alpha_composite(av, (55, 45))
    d = ImageDraw.Draw(bg)
    text(d, (178, 50), "KNOWLUMO", 34, WHITE, True, 2)
    text(d, (180, 94), "VISUAL LEARNING", 16, TEAL, True)

    # Subject / series chip.
    rounded(d, (872, 44, 1224, 102), 28, (18, 43, 58, 235), TEAL + (210,), 2)
    center(d, 1048, 73, f"{SUBJECT}  ·  EPISODE {EPISODE}", 19, WHITE, True)

    # Main typography.
    text(d, (58, 188), TOPIC, 150, WHITE, True, 5)
    text(d, (62, 356), SUBTITLE, 72, TEAL, True, 4)
    d.rounded_rectangle((62, 462, 596, 469), 3, fill=TEAL)
    text(d, (62, 492), TAGS, 23, GOLD, True, 2)

    # Part marker and a compact set notation hint over the Venn artwork.
    rounded(d, (60, 608, 222, 666), 26, GOLD, None)
    center(d, 141, 637, f"PART {PART}", 21, NAVY, True)
    rounded(d, (912, 566, 1206, 638), 24, (7, 18, 34, 220), GOLD + (180,), 2)
    center(d, 980, 602, "A", 40, GOLD, True)
    draw_cap(d, 1059, 598, 62, 36, GOLD, 8)
    center(d, 1138, 602, "B", 40, GOLD, True)

    final = bg.convert("RGB")
    png = OUT / "CSCA_Math_01_Sets_Thumbnail_1280x720.png"
    jpg = OUT / "CSCA_Math_01_Sets_Thumbnail_1280x720.jpg"
    final.save(png, optimize=True)
    final.save(jpg, quality=92, subsampling=0, optimize=True)
    final.resize((640, 360), Image.Resampling.LANCZOS).save(OUT / "thumbnail_preview_640x360.png")
    final.resize((320, 180), Image.Resampling.LANCZOS).save(OUT / "thumbnail_preview_320x180.png")
    print(f"Wrote {png}")
    print(f"Wrote {jpg}")


if __name__ == "__main__":
    main()
