#!/usr/bin/env python3
"""Create Knowlumo banner and representative centered device crops."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'assets'; PRE=ROOT/'previews'; OUT.mkdir(exist_ok=True); PRE.mkdir(exist_ok=True)
src=Image.open(ROOT/'source/banner-world.png').convert('RGB')
base=ImageOps.fit(src,(2560,1440),Image.Resampling.LANCZOS)
# Ease the teachers further into the mobile-safe zone, while keeping the
# external scenery across the full canvas and not cutting off the TV artwork.
sx=[0,500,1100,1800,2560]; dx=[0,720,1270,1850,2560]
sy=[0,500,1000,1440]; dy=[0,620,1085,1440]
mesh=[]
for j in range(len(sy)-1):
 for i in range(len(sx)-1):
  x0,x1=sx[i:i+2]; y0,y1=sy[j:j+2]
  mesh.append(((dx[i],dy[j],dx[i+1],dy[j+1]),(x0,y0,x0,y1,x1,y1,x1,y0)))
banner=base.transform((2560,1440),Image.Transform.MESH,mesh,resample=Image.Resampling.BICUBIC).convert('RGBA')
# Local tonal vignette, not a frame, ensures the wordmark is legible.
shade=Image.new('RGBA',(2560,1440),(0,0,0,0)); px=shade.load()
for x in range(1260,2000):
 for y in range(545,890):
  fade_x=max(0,min(1,(x-1260)/115,(2000-x)/125))
  fade_y=max(0,min(1,(y-545)/65,(890-y)/65))
  px[x,y]=(2,17,47,int(155*fade_x*fade_y))
banner=Image.alpha_composite(banner,shade); d=ImageDraw.Draw(banner)
F='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'; font=lambda n:ImageFont.truetype(F,n)
# Main text lies in even the tighter 1235×338 centered crop, with margins.
d.text((1310,630),'KNOWLUMO',font=font(78),fill='#ffffff',stroke_width=1,stroke_fill='#091a36')
d.rounded_rectangle((1315,750,1382,757),3,fill='#ffd75e')
d.text((1400,737),'LEARN. EXPLORE. GROW.',font=font(20),fill='#b6f3ff')
banner=banner.convert('RGB'); banner.save(OUT/'banner_2560x1440.jpg',quality=93,subsampling=0,optimize=True)
# Crop rectangles are design guides, not screenshots of YouTube rendering.
banner.crop((507,508,2053,931)).save(PRE/'mobile_1546x423.jpg',quality=93,optimize=True)
banner.crop((663,551,1898,889)).save(PRE/'mobile_conservative_1235x338.jpg',quality=93,optimize=True)
banner.crop((0,508,2560,931)).save(PRE/'desktop_2560x423.jpg',quality=93,optimize=True)
banner.resize((1280,720),Image.Resampling.LANCZOS).save(PRE/'tv_1280x720.jpg',quality=93,optimize=True)
print('Saved channel banner and 3 approximate device previews.')
