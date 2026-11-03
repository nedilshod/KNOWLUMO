# Knowlumo CSCA Math thumbnail template

- Canvas: 1280 × 720, 16:9.
- Background: `build/thumbnail_background.png`, a text-free generated illustration with a subtle grid and glowing Venn circles.
- Brand: the selected round Knowlumo avatar, composited at top left.
- Palette: deep navy `#091120`, teal `#5ff1d1`, blue `#79aaff`, gold `#ffd17c`, off-white `#f3f8ff`.
- Layout: large topic typography on the left, Venn artwork on the right, compact subject/series chip at top right, part marker at bottom left.

To reuse the style for a later episode, edit these variables in `build/build_thumbnail.py` and rerun it:

```text
EPISODE, PART, SUBJECT, TOPIC, SUBTITLE, TAGS
```

The script writes both PNG and JPG plus 640 × 360 and 320 × 180 readability previews. Keep the left side clear for large type and replace the generated background only if the new illustration remains text-free and high-contrast.
