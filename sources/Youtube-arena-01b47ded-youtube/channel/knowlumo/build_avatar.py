#!/usr/bin/env python3
"""Crop chosen badge to a round transparent PNG; retain a square YouTube upload."""
from pathlib import Path
from PIL import Image, ImageDraw
R=Path(__file__).resolve().parent
im=Image.open(R/'source/avatar-selected.png').convert('RGBA')
w,h=im.size
# Image has a centered badge with about 7% near-black margin on each side.
# Crop into the badge's outer rim, preserving its logo and lettering.
side=min(w,h); margin=round(side*.063)
left=(w-side)//2+margin; top=(h-side)//2+margin
badge=im.crop((left,top,left+side-2*margin,top+side-2*margin))
large=badge.resize((1600,1600),Image.Resampling.LANCZOS)
mask=Image.new('L',(1600,1600),0); ImageDraw.Draw(mask).ellipse((1,1,1598,1598),fill=255)
large.putalpha(mask)
large.resize((800,800),Image.Resampling.LANCZOS).save(R/'assets/avatar_round_800.png',optimize=True)
# YouTube ultimately displays a circle. Opaque square upload is the safest fallback.
upload=Image.new('RGBA',(800,800),'#030914'); upload.alpha_composite(large.resize((800,800),Image.Resampling.LANCZOS))
upload.convert('RGB').save(R/'assets/avatar_square_for_youtube_800.png',optimize=True)
large.resize((196,196),Image.Resampling.LANCZOS).save(R/'assets/avatar_small_preview.png',optimize=True)
