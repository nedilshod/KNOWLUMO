# CSCA Math 01 — Sets (full animated lesson)

An independent, English-language beginner lesson. It covers elements and membership, order and repetition, a Venn diagram, intersection and union, the empty set, and an original multiple-choice question with a worked solution. The question is practice material, not an official exam question. No upload to YouTube is automated.

## Render

Requires Python 3.10+, Pillow, imageio-ffmpeg, DejaVu Sans fonts at `/usr/share/fonts/truetype/dejavu/`, the ten audio files, script.json, and alignment.json.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r csca/requirements.txt
python csca/episode01/render.py --preview  # stills at 65% of each scene
python csca/episode01/render.py            # output/CSCA_Math_01_Sets_Full.mp4
```

The graphics and text are authored animation in Pillow and FFmpeg; this does not run OpenMontage. Words are force-aligned against the actual recorded narration. Captions reveal only the words whose start times have passed and hold the last spoken word through pauses and scene boundaries. Short groups end at sentence boundaries or after five words. Highlighting and visual cues use the same recorded timestamps; the automatic alignment is approximate and should be manually reviewed before publishing. If the script or narration changes, regenerate alignment.json; changing script alone is not sufficient. This revision renders at 30 frames per second and 1280×720; it also illustrates numbers, letters, and other objects, and animates membership, reordering, and intersection examples. Episode 01 is a custom composition, not a generic template for all future subjects.

## Sources and review

See `../CURRICULUM.md` for syllabus source and limitations. Mathematics checked: A={1,2,3}, B={2,3,4}, intersection={2,3}, union={1,2,3,4}; C={5,6}, D={7,8}, intersection=∅, union={5,6,7,8}; P={1,3,5,7}, Q={3,4,7}, intersection={3,7}, union={1,3,4,5,7}. The distinction ∅ ≠ {0} is correct. The practice question asks viewers to pause, not wait through a long countdown.

## Timing regression tests

```sh
python -m unittest discover -s csca/episode01 -p "test_*.py" -v
```

Tests verify that no future word is shown relative to the alignment timestamps, captions hold through pauses and at scene boundaries, and transcript and alignment match. They do not prove that every automatically generated timestamp matches the spoken audio exactly.
