# CSCA Math — episode 1 pilot

English, 16:9, original introductory lesson on sets. Generated MP4 and cover are in `output/`. `audio/` contains the six selected-voice narration clips. `CURRICULUM.md` contains the proposed roadmap, provenance and limits.

This pilot uses custom Pillow-generated graphics and FFmpeg, inspired by the general research/script/scene/render/review workflow described by OpenMontage. It is **not** an installation of OpenMontage or YouTube Automation Agent and does not publish anything. Graphics currently use a gentle zoom and scene-level narration, not word-synchronized animation or subtitles. The full series will need separate scripts, graphics and audio, editorial review, and a more flexible scene system.

## Rebuild

Requires Python 3.10+, DejaVu Sans fonts in `/usr/share/fonts/truetype/dejavu/` and the included MP3 clips. `imageio-ffmpeg` provides a compatible FFmpeg binary.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r csca/requirements.txt
python csca/render.py
# Generate a future episode thumbnail:
python csca/render.py --cover-only --number 2 --title 'Subsets and Complements'
```

The included voice clips must be regenerated separately if the script changes. Rebuilding leaves generated frames and output in this directory. The cover generator is reusable; the lesson images and timing are specific to episode 1.

## Fact check and narrative

A={1,2,3}, B={2,3,4}: A∩B={2,3}, A∪B={1,2,3,4}. C={1,4}: B∩C={4}. All are original examples. The video asks viewers to pause; there is no extended silent countdown. Check audio, visual timing, typography and current syllabus before publishing.

## Expanded episode 01

The longer, animated revision is in [`episode01/`](episode01/README.md); its rendered MP4 is `episode01/output/CSCA_Math_01_Sets_Full.mp4`. The earlier one-minute pilot remains available for comparison.
