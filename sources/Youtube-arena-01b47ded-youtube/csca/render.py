#!/usr/bin/env python3
"""Render the CSCA sets pilot from its six English narration clips.
Requires Pillow, imageio-ffmpeg and the included audio. Outputs remain local.
"""
import argparse, math, re, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent
FF = imageio_ffmpeg.get_ffmpeg_exe()
W,H=1280,720
BG='#0a1020'; PANEL='#111c30'; WHITE='#f4f8ff'; MUTED='#9bacc3'; TEAL='#61ead4'; GOLD='#ffce67'; BLUE='#71a9ff'
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def font(n,b=False): return ImageFont.truetype(BOLD if b else FONT,n)
def text(d,xy,s,size=32,color=WHITE,b=False): d.text(xy,s,font=font(size,b),fill=color)
def base(section):
 im=Image.new('RGB',(W,H),BG); d=ImageDraw.Draw(im)
 for x in range(0,W,80): d.line((x,0,x,H),fill='#101b2e',width=1)
 for y in range(0,H,80): d.line((0,y,W,y),fill='#101b2e',width=1)
 d.rounded_rectangle((48,38,172,78),12,fill='#183437'); text(d,(66,46),'CSCA',20,TEAL,True)
 text(d,(195,46),'MATH  /  EPISODE 01',20,MUTED,True)
 text(d,(1020,46),section.upper(),18,MUTED,True)
 d.line((48,98,1232,98), fill='#25344b',width=2)
 d.line((48,667,1232,667), fill='#25344b',width=2)
 text(d,(50,680),'CSCA MATH  •  LEARN STEP BY STEP',15,MUTED,True)
 return im,d
def card(d,box): d.rounded_rectangle(box,24,fill=PANEL,outline='#293c56',width=2)
def slide(i):
 im,d=base(['START HERE','THE IDEA','INTERSECTION','UNION','YOUR TURN','THE ANSWER'][i-1])
 if i==1:
  text(d,(65,157),'01',100,TEAL,True); text(d,(65,300),'Sets, made simple.',66,WHITE,True)
  text(d,(68,403),'The language of collections',30,MUTED)
  card(d,(765,175,1170,538)); text(d,(820,223),'A =',48,TEAL,True); text(d,(820,307),'{ 1, 2, 3 }',48,WHITE,True)
  text(d,(820,420),'3 DISTINCT ELEMENTS',20,MUTED,True)
 elif i==2:
  text(d,(65,142),'What is a set?',53,WHITE,True); text(d,(67,215),'A collection of distinct elements.',28,MUTED)
  card(d,(65,287,1215,590)); text(d,(108,318),'A = { 1, 2, 3 }',55,TEAL,True)
  text(d,(110,417),'2 ∈ A',42,WHITE,True); text(d,(355,428),'2 belongs to A',26,MUTED)
  text(d,(110,493),'4 ∉ A',42,WHITE,True); text(d,(355,504),'4 does not belong to A',26,MUTED)
 elif i in (3,4):
  inter=i==3
  text(d,(65,139),'Intersection' if inter else 'Union',53,WHITE,True)
  text(d,(67,211),'Elements in BOTH sets' if inter else 'Elements in EITHER set',29,MUTED)
  card(d,(66,282,640,587)); text(d,(106,317),'A = { 1, 2, 3 }',39,TEAL,True); text(d,(106,390),'B = { 2, 3, 4 }',39,BLUE,True)
  text(d,(106,495),'BOTH' if inter else 'COMBINE  •  NO REPEATS',21,GOLD,True)
  card(d,(680,282,1215,587)); text(d,(719,326),'A ∩ B' if inter else 'A ∪ B',42,GOLD,True)
  text(d,(718,410),'= { 2, 3 }' if inter else '= { 1, 2, 3, 4 }',38,WHITE,True)
 elif i==5:
  text(d,(65,139),'Your turn',53,WHITE,True); text(d,(67,211),'Pause and find the intersection.',29,MUTED)
  card(d,(65,282,1215,590)); text(d,(110,316),'B = { 2, 3, 4 }',42,BLUE,True); text(d,(110,385),'C = { 1, 4 }',42,TEAL,True)
  text(d,(110,484),'B ∩ C = ?',49,GOLD,True); text(d,(830,505),'THINK: IN BOTH',22,MUTED,True)
 else:
  text(d,(65,140),'The answer',53,WHITE,True); text(d,(67,212),'Four is the only element in both sets.',27,MUTED)
  card(d,(65,282,1215,480)); text(d,(108,315),'B ∩ C = { 4 }',53,TEAL,True)
  text(d,(105,405),'BOTH → INTERSECTION',22,MUTED,True); text(d,(630,405),'EITHER → UNION',22,MUTED,True)
  text(d,(68,540),'NEXT  /  Subsets & complements',26,GOLD,True)
 return im

def cover(number,title,out):
 im=Image.new('RGB',(W,H),BG); d=ImageDraw.Draw(im)
 for x in range(0,W,80): d.line((x,0,x,H),fill='#101b2e',width=1)
 for y in range(0,H,80): d.line((0,y,W,y),fill='#101b2e',width=1)
 d.rounded_rectangle((60,55,280,110),14,fill='#183437'); text(d,(84,65),'CSCA MATH',23,TEAL,True)
 text(d,(65,168),'EPISODE',30,MUTED,True); text(d,(60,213),f'{number:02d}',150,TEAL,True)
 # Wrap title into at most three lines; scale to fit the thumbnail's right hand panel.
 words=title.upper().split(); size=64
 while size>=28:
  f=font(size,True); lines=[]; line=''
  for word in words:
   trial=(line+' '+word).strip()
   if line and d.textlength(trial,font=f)>690: lines.append(line); line=word
   else: line=trial
  if line: lines.append(line)
  if len(lines)<=3 and all(d.textlength(line,font=f)<=690 for line in lines): break
  size-=2
 for j,line in enumerate(lines): text(d,(490,235+j*(size+18)),line,size,WHITE,True)
 d.line((65,595,1210,595),fill='#2a3c54',width=2); text(d,(65,620),'LEARN STEP BY STEP',24,GOLD,True)
 im.save(out,quality=94)
def duration(p):
 r=subprocess.run([FF,'-i',str(p)],capture_output=True,text=True).stderr
 m=re.search(r'Duration: (\d+):(\d+):([\d.]+)',r)
 if not m: raise RuntimeError(f'Cannot read duration: {p}')
 return int(m[1])*3600+int(m[2])*60+float(m[3])
def run(*args): subprocess.run(args,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
def main():
 parser=argparse.ArgumentParser(); parser.add_argument('--cover-only',action='store_true'); parser.add_argument('--number',type=int,default=1); parser.add_argument('--title',default='Sets Made Simple'); args=parser.parse_args()
 out=ROOT/'output'; out.mkdir(exist_ok=True); frames=ROOT/'frames'; frames.mkdir(exist_ok=True)
 cover(args.number,args.title,out/f'thumbnail-{args.number:02}.jpg')
 if args.cover_only:return
 segments=[]
 for i in range(1,7):
  p=ROOT/'audio'/f'{i:02}.mp3'; t=duration(p)+0.35
  image=frames/f'{i:02}.png'; slide(i).save(image)
  seg=out/f'segment-{i:02}.mp4'; segments.append(seg)
  # Very slow push in; each complete scene stays visible for the matching narration clip.
  filt="zoompan=z='min(zoom+0.00008,1.035)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1280x720:fps=24,format=yuv420p"
  run(FF,'-y','-loop','1','-framerate','24','-i',str(image),'-i',str(p),'-vf',filt,'-af','apad','-t',f'{t:.3f}','-c:v','libx264','-preset','veryfast','-crf','23','-c:a','aac','-b:a','128k','-ar','44100','-ac','2',str(seg))
 concat=out/'concat.txt'; concat.write_text(''.join(f"file '{p.name}'\n" for p in segments))
 run(FF,'-y','-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(out/'CSCA_Math_01_Sets_Pilot.mp4'))
 for p in segments: p.unlink()
 concat.unlink()
 print('Wrote',out/'CSCA_Math_01_Sets_Pilot.mp4')
if __name__=='__main__': main()
