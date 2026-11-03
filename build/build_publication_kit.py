#!/usr/bin/env python3
"""Generate the final English publication copy kit and Instagram covers.

This script does not publish anything. It writes ready-to-copy metadata for
YouTube (long video + Short) and Instagram Reels, plus two cover images derived
from the opening frame of the finished vertical video.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "publication"
SHORTS = ROOT / "output" / "shorts" / "CSCA_Math_01_Sets_Shorts_1080x1920.mp4"
FF = imageio_ffmpeg.get_ffmpeg_exe()
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

HANDLE = "@Knowlumo"

Y_LONG_TITLE = "CSCA Math #01: Sets Made Simple | Intersection, Union & Practice"

Y_LONG_DESCRIPTION = """Learn sets from the ground up: elements, membership, Venn diagrams, intersection, union, the empty set, and a worked practice question. This is CSCA Math Episode 01 — a full visual lesson with English narration and animated examples.

In this lesson you will:
• read set notation and the membership symbols
• see why order and repetition do not change a set
• use a Venn diagram to find shared elements
• calculate intersections and unions without repeating elements
• avoid the “empty set is not {0}” trap
• solve an original multiple-choice question step by step

Chapters (approximate):
00:00 The language of sets
00:29 What is a set?
01:03 Membership
01:34 Two important rules
02:07 The Venn diagram
02:36 Intersection
03:08 Union
03:38 The empty set
04:13 Practice question
04:52 The solution
05:30 Knowlumo outro

This is independent educational material, not an official CSCA past-paper question and not an official CSCA channel. Exam content and university requirements can change; check the latest official syllabus and your intended university’s requirements.

If this helped, subscribe to Knowlumo for future visual lessons. Keep exploring, one idea at a time.

#CSCAMath #SetTheory #MathLessons #Knowlumo"""

Y_LONG_TAGS = "CSCA Math, CSCA mathematics, CSCA exam, China Scholastic Competency Assessment, sets, set theory, elements of a set, membership symbol, Venn diagram, intersection, union, empty set, math lesson, math tutorial, exam prep, undergraduate math, beginner set theory, multiple choice math, Knowlumo"
Y_LONG_HASHTAGS = "#CSCAMath #SetTheory #MathLessons #Knowlumo"
Y_LONG_PINNED = """Welcome to Knowlumo — this is Episode 01 of our CSCA Math series.

Question for you: which felt trickier, intersection or union? Tell me below, and I’ll use your answers to shape future visual lessons.

Independent educational material; not an official CSCA channel."""

Y_SHORT_TITLE = "3 Quick Set Questions: Intersection, Union & Membership | CSCA Math"

Y_SHORT_DESCRIPTION = """A = { 1, 2, 3 } and B = { 2, 3, 4 }.

Can you find A ∩ B, find A ∪ B, and decide whether 4 belongs to the intersection? Each question gives you a short pause, then a quick visual explanation.

For definitions, more examples, Venn diagrams, and a worked practice problem, see the full CSCA Math Episode 01 lesson, “Sets Made Simple,” on Knowlumo.

Independent educational material, not an official CSCA channel or an official CSCA question. Check the latest official syllabus and your university’s requirements.

#CSCAMath #Sets #MathShorts #Intersection #Union #Knowlumo"""

Y_SHORT_TAGS = "CSCA Math, sets, set theory, intersection, union, Venn diagram, math shorts, math quiz, membership, A intersection B, A union B, exam prep, CSCA, Knowlumo, YouTube Shorts"
Y_SHORT_HASHTAGS = "#CSCAMath #Sets #MathShorts #Intersection #Union #Knowlumo"
Y_SHORT_PINNED = """Answers: 1) { 2, 3 }  2) { 1, 2, 3, 4 }  3) No — 4 is in B only.

Full lesson: CSCA Math Episode 01 on Knowlumo. No link is implied here."""

IG_CAPTION = """3 set questions. Think you can get all three? 👇

A = { 1, 2, 3 }
B = { 2, 3, 4 }

1) A ∩ B = ?
2) A ∪ B = ?
3) Is 4 in A ∩ B?

Pause on each one — the answers and quick explanations are in the Reel. Intersection means “in both.” Union means “in either set, without repeats.”

Want the definitions, Venn diagrams, and a worked practice question? Full lesson: CSCA Math Episode 01 — Sets Made Simple, on Knowlumo.

Save this for revision and follow @Knowlumo for visual math lessons. Independent; not official CSCA.

#CSCAMath #Sets #SetTheory #Intersection #Union #VennDiagram #MathShorts #MathReels #LearnMath #ExamPrep #Knowlumo"""

IG_HASHTAGS = "#CSCAMath #Sets #SetTheory #Intersection #Union #VennDiagram #MathShorts #MathReels #LearnMath #ExamPrep #Knowlumo"
IG_BIO = "Visual math lessons for curious minds. CSCA Math starts here. Learn. Explore. Grow. Independent; not official CSCA."
IG_FIRST_COMMENT = "Which one made you pause the longest: 1, 2, or 3? 👇"

YT_ABOUT = """Welcome to Knowlumo — where curiosity becomes understanding.

We make visual, step-by-step lessons that turn difficult ideas into clear pictures. Our first series starts with CSCA Mathematics; more subjects may follow as the channel grows.

Every full lesson builds the idea from the ground up, shows worked examples, and gives you time to pause and practise. Short videos bring quick questions you can try on the go.

Learn. Explore. Grow. One idea at a time.

Knowlumo is an independent educational channel, not affiliated with the CSCA organizer or any university. Exam content and university requirements can change; always check the latest official syllabus and your intended university’s requirements.

Handle: @Knowlumo"""

YT_CHANNEL_KEYWORDS = "Knowlumo, visual learning, education, math lessons, mathematics explained, CSCA exam, CSCA mathematics, CSCA math, study in China, animated education, exam preparation, step-by-step learning"

PLAYLIST_FULL = "CSCA Mathematics — Full Lessons"
PLAYLIST_SHORT = "CSCA Math — Quick Quizzes"

LAUNCH_POST = """Knowlumo is here.

Episode 01 is live: Sets Made Simple. We start with the language of sets — elements, Venn diagrams, intersection, union, and a worked practice question.

A three-question quick quiz is also up for Shorts and Reels. Watch, pause, try it, then keep exploring one idea at a time.

Learn. Explore. Grow."""


def block(lines, label, value, note=""):
    suffix = f" — {len(value)} characters" if note == "chars" else ""
    lines.append(f"**{label}**{suffix}")
    lines.append("")
    lines.append("```text")
    lines.extend(value.splitlines())
    lines.append("```")
    lines.append("")


def build_markdown():
    lines = [
        "# Knowlumo — publication copy kit (EN)",
        "",
        f"Working handle on both platforms: `{HANDLE}`. This agent has not checked availability, reserved a handle, created an account, or published any video.",
        "",
        "All text below is English and ready to copy. Do not add dates, subscriber counts, contact details, URLs, or claims of official CSCA affiliation.",
        "",
        "---",
        "",
        "## 1. YouTube — full lesson",
        "",
        "File: `output/episode01/CSCA_Math_01_Sets_Full_With_Outro.mp4`",
        "",
    ]
    block(lines, "Title", Y_LONG_TITLE, "chars")
    block(lines, "Description", Y_LONG_DESCRIPTION, "chars")
    block(lines, "Tags (comma-separated)", Y_LONG_TAGS, "chars")
    block(lines, "Hashtags", Y_LONG_HASHTAGS)
    block(lines, "Pinned comment", Y_LONG_PINNED)
    lines += [
        "Thumbnail: `CSCA_Math_01_Sets_Thumbnail_1280x720.png` or `.jpg`",
        f"Playlist: `{PLAYLIST_FULL}`",
        "Category: Education · Language: English",
        "End screen / subscribe element: configure separately in YouTube Studio. The burned-in SUBSCRIBE card is static artwork, not a clickable YouTube feature.",
        "",
        "---",
        "",
        "## 2. YouTube Shorts",
        "",
        "File: `output/shorts/CSCA_Math_01_Sets_Shorts_1080x1920.mp4`",
        "",
    ]
    block(lines, "Title", Y_SHORT_TITLE, "chars")
    block(lines, "Description", Y_SHORT_DESCRIPTION, "chars")
    block(lines, "Tags (comma-separated)", Y_SHORT_TAGS, "chars")
    block(lines, "Hashtags", Y_SHORT_HASHTAGS)
    block(lines, "Pinned comment", Y_SHORT_PINNED)
    lines += [
        "Optional custom Shorts thumbnail, if your account has the feature: `instagram_reels_cover_1080x1920.png`.",
        "Related Video: after the full lesson is public or unlisted, attach it in YouTube Studio if the feature is available. The card inside the MP4 is not a link.",
        "",
        "---",
        "",
        "## 3. Instagram Reels",
        "",
        "Instagram has no separate title field. The first line of the caption acts as the title/hook.",
        "",
    ]
    block(lines, "Caption", IG_CAPTION, "chars")
    block(lines, "Hashtags", IG_HASHTAGS)
    block(lines, "First comment", IG_FIRST_COMMENT)
    block(lines, "Profile bio", IG_BIO, "chars")
    lines += [
        "Cover: `instagram_reels_cover_1080x1920.png`",
        "Feed-preview cover: `instagram_feed_cover_1080x1080.png`",
        "After the long video has a real public URL, add that real URL to the Instagram bio. Do not invent a link before publication.",
        "",
        "---",
        "",
        "## 4. Channel / account identity",
        "",
        "YouTube channel name: Knowlumo  ",
        f"YouTube handle: {HANDLE}  ",
        f"Instagram username: {HANDLE}  ",
        "Instagram display name: Knowlumo  ",
        "Tagline: Learn. Explore. Grow.  ",
        "",
    ]
    block(lines, "YouTube channel About", YT_ABOUT, "chars")
    block(lines, "YouTube channel keywords", YT_CHANNEL_KEYWORDS, "chars")
    lines += [
        f"Playlist 1: `{PLAYLIST_FULL}`",
        f"Playlist 2: `{PLAYLIST_SHORT}`",
        "",
        "---",
        "",
        "## 5. Launch announcement (use only after both videos are public)",
        "",
    ]
    block(lines, "Community post / caption", LAUNCH_POST)
    lines += [
        "---",
        "",
        "## 6. Backup handles, only if the exact name is rejected",
        "",
        "`@KnowlumoLearn` · `@LearnKnowlumo`",
        "",
        "These are fallbacks, not claims that they are free. Check availability inside YouTube Studio and Instagram.",
        "",
    ]
    return "\n".join(lines) + "\n"


def build_video_metadata():
    return "\n".join([
        "Suggested title:",
        Y_LONG_TITLE,
        "",
        "Suggested description:",
        Y_LONG_DESCRIPTION,
        "",
        "Tags:",
        Y_LONG_TAGS,
        "",
        "Hashtags:",
        Y_LONG_HASHTAGS,
        "",
        "Pinned comment:",
        Y_LONG_PINNED,
        "",
        "Thumbnail: CSCA_Math_01_Sets_Thumbnail_1280x720.png / .jpg",
        f"Playlist: {PLAYLIST_FULL}",
        "Category: Education | Language: English",
        "",
        "The SUBSCRIBE graphic in the outro is static artwork, not a clickable YouTube end screen.",
        "Configure real end screens separately in YouTube Studio after publication.",
        "Independent educational material; not an official CSCA channel.",
        "",
    ])


def build_short_metadata():
    return "\n".join([
        "Suggested title:",
        Y_SHORT_TITLE,
        "",
        "Suggested description:",
        Y_SHORT_DESCRIPTION,
        "",
        "Tags:",
        Y_SHORT_TAGS,
        "",
        "Hashtags:",
        Y_SHORT_HASHTAGS,
        "",
        "Pinned comment:",
        Y_SHORT_PINNED,
        "",
        "No URL is burned into the video. The final card is a stylized graphic.",
        "After the full lesson is public, attach it as a Related Video in YouTube Studio if available.",
        "Independent educational material; not an official CSCA channel.",
        "",
    ])


def build_covers():
    vertical = OUT / "instagram_reels_cover_1080x1920.png"
    subprocess.run([FF, "-y", "-loglevel", "error", "-ss", "0.3", "-i", str(SHORTS),
                    "-frames:v", "1", str(vertical)], check=True)
    im = Image.open(vertical).convert("RGB")
    assert im.size == (1080, 1920)
    square = im.crop((0, 420, 1080, 1500))
    d = ImageDraw.Draw(square)
    d.rounded_rectangle((40, 28, 1040, 104), 22, fill=(13, 27, 45), outline=(95, 241, 209), width=2)
    d.text((70, 45), "KNOWLUMO", font=ImageFont.truetype(FONT_BOLD, 30), fill=(243, 248, 255))
    d.text((70, 78), "CSCA MATH  ·  SETS QUIZ", font=ImageFont.truetype(FONT, 18), fill=(155, 176, 201))
    square.save(OUT / "instagram_feed_cover_1080x1080.png")


def verify():
    public_strings = {
        "youtube_long_title": Y_LONG_TITLE,
        "youtube_long_description": Y_LONG_DESCRIPTION,
        "youtube_long_tags": Y_LONG_TAGS,
        "youtube_long_pinned": Y_LONG_PINNED,
        "youtube_short_title": Y_SHORT_TITLE,
        "youtube_short_description": Y_SHORT_DESCRIPTION,
        "youtube_short_tags": Y_SHORT_TAGS,
        "youtube_short_pinned": Y_SHORT_PINNED,
        "instagram_caption": IG_CAPTION,
        "instagram_bio": IG_BIO,
        "youtube_about": YT_ABOUT,
        "launch_post": LAUNCH_POST,
    }
    assert len(Y_LONG_TITLE) <= 100
    assert len(Y_SHORT_TITLE) <= 100
    assert len(Y_LONG_DESCRIPTION) <= 5000
    assert len(Y_SHORT_DESCRIPTION) <= 5000
    assert len(Y_LONG_TAGS) <= 500
    assert len(Y_SHORT_TAGS) <= 500
    assert len(IG_CAPTION) <= 2200
    assert len(IG_BIO) <= 150
    assert len(IG_HASHTAGS.split()) <= 30
    assert len(Y_SHORT_HASHTAGS.split()) <= 15
    assert len(Y_LONG_HASHTAGS.split()) <= 15
    for name, value in public_strings.items():
        assert not re.search(r"https?://|www\.", value), name
        assert not re.search(r"\b20\d{2}\b", value), name
        assert "subscribers" not in value.lower(), name
    assert "not an official CSCA channel" in Y_LONG_DESCRIPTION
    assert "not an official CSCA channel" in Y_SHORT_DESCRIPTION
    assert "not official CSCA" in IG_CAPTION
    return {k: len(v) for k, v in public_strings.items()}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lengths = verify()
    (OUT / "COPY_PASTE_EN.md").write_text(build_markdown(), encoding="utf-8")
    (ROOT / "output/episode01/VIDEO_01_EN.txt").write_text(build_video_metadata(), encoding="utf-8")
    (ROOT / "output/shorts/SHORTS_01_EN.txt").write_text(build_short_metadata(), encoding="utf-8")
    build_covers()
    (OUT / "verification.json").write_text(json.dumps({
        "status": "passed",
        "handle": HANDLE,
        "handle_availability_checked": False,
        "accounts_created_or_reserved_by_agent": False,
        "videos_published_by_agent": False,
        "character_counts": lengths,
        "constraints": {
            "youtube_title_max": 100,
            "youtube_description_max": 5000,
            "youtube_tags_max": 500,
            "instagram_caption_max": 2200,
            "instagram_bio_max": 150,
            "instagram_hashtags_max": 30,
        },
    }, indent=2), encoding="utf-8")
    print("Publication kit generated and verified.")
    print(f"Handle: {HANDLE} (not checked or reserved by this agent)")
    print(f"Long title: {len(Y_LONG_TITLE)} chars | Short title: {len(Y_SHORT_TITLE)} chars")
    print(f"Instagram caption: {len(IG_CAPTION)} chars | bio: {len(IG_BIO)} chars")


if __name__ == "__main__":
    main()
