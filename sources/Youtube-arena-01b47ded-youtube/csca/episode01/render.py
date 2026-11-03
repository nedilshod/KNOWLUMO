#!/usr/bin/env python3
"""CSCA Math #1: animated, narrated educational video. See README for rebuild."""
import bisect, json, math, re, subprocess, sys
from pathlib import Path
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

R=Path(__file__).resolve().parent
FF=imageio_ffmpeg.get_ffmpeg_exe(); W,H=1280,720; FPS=30
NAVY='#091120'; INK='#142239'; FAINT='#9bb0c9'; WHITE='#f3f8ff'; TEAL='#5ff1d1'; BLUE='#79aaff'; GOLD='#ffd17c'; RED='#ff878c'; LINE='#293a50'
SCRIPTS=json.loads((R/'script.json').read_text()); ALIGN=json.loads((R/'alignment.json').read_text())

# Preserve punctuation and split only at sentence boundaries or after at most
# five words. Alignment determines when words become visible; no future words
# are drawn. Keep the final group visible across silence and scene boundaries.
def caption_groups(script):
 tokens=re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?[.,!?;:]*", script)
 groups=[]; cur=[]
 for idx,token in enumerate(tokens):
  cur.append((idx,token))
  if len(cur)>=5 or token.endswith(('.', '?', '!', ';', ':')):
   groups.append(cur); cur=[]
 if cur: groups.append(cur)
 return tokens,groups
CAPTION_DATA=[caption_groups(s) for s in SCRIPTS]
STARTS=[[w['start'] for w in scene] for scene in ALIGN]
def caption_state(i,t):
 active=bisect.bisect_right(STARTS[i],t)-1
 if active<0:
  if i==0: return None
  i-=1; active=len(ALIGN[i])-1
 group=next(g for g in CAPTION_DATA[i][1] if g[0][0]<=active<=g[-1][0])
 return group,active

F='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'; FB='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
@lru_cache(None)
def ft(size,bold=False): return ImageFont.truetype(FB if bold else F,size)
def txt(d,x,y,s,size=28,color=WHITE,b=False): d.text((int(x),int(y)),s,font=ft(size,b),fill=color,stroke_width=0)
def center(d,x,y,s,size=28,color=WHITE,b=False):
 f=ft(size,b); box=d.textbbox((0,0),s,font=f); d.text((int(x-(box[2]-box[0])/2),int(y-(box[3]+box[1])/2)),s,font=f,fill=color)
def ease(x): x=max(0,min(1,x)); return 1-(1-x)**3
def pop(d,x,y,s,t,start,size=30,color=WHITE,b=True):
 if t<start:return
 p=ease((t-start)/.55); txt(d,x,y+(1-p)*18,s,size,color,b)
def card(d,xy,outline=LINE,fill=INK,r=22): d.rounded_rectangle(xy,r,fill=fill,outline=outline,width=2)
def chip(d,x,y,label,color=TEAL,r=34):
 d.ellipse((int(x-r),int(y-r),int(x+r),int(y+r)),fill='#182d3d',outline=color,width=3); center(d,x,y,label,28,color,True)
def at(i, phrase, n=0):
 words=re.findall(r"[a-z]+(?:'[a-z]+)?", SCRIPTS[i].lower()); target=phrase.lower().split()
 hits=[j for j in range(len(words)-len(target)+1) if words[j:j+len(target)]==target]
 if len(hits)<=n: raise ValueError((i,phrase,n))
 return ALIGN[i][hits[n]]['start']
def move(a,b,p): return a+(b-a)*ease(p)
def spring(x):
 x=max(0,min(1,x))
 return 1-((1-x)**2)*math.cos(x*math.pi*2.0)
def pulse(t,start): return max(0,1-(t-start)/1.0) if t>=start else 0
def animated_chip(d,x,y,label,color,t,st,r=34):
 if t<st:return
 p=spring((t-st)/.75)
 chip(d,x,y,label,color,max(3,int(r*p)))
def arrow(d,x1,y1,x2,y2,color,progress):
 p=ease(progress); x=x1+(x2-x1)*p; y=y1+(y2-y1)*p
 d.line((int(x1),int(y1),int(x),int(y)),fill=color,width=4)
 if p>.95:
  ang=math.atan2(y2-y1,x2-x1)
  for delta in (-.55,.55):
   d.line((x2,y2,x2-15*math.cos(ang+delta),y2-15*math.sin(ang+delta)),fill=color,width=4)

def dur(p):
 s=subprocess.run([FF,'-i',str(p)],capture_output=True,text=True).stderr
 m=re.search(r'Duration: (\d+):(\d+):([\d.]+)',s)
 return int(m[1])*3600+int(m[2])*60+float(m[3])
DURS=[dur(R/'audio'/f'{i:02}.mp3') for i in range(1,11)]
TOTAL=sum(x+.35 for x in DURS)
BG=Image.new('RGB',(W,H),NAVY); db=ImageDraw.Draw(BG)
for x in range(0,W,64): db.line((x,0,x,H),fill='#111d30',width=1)
for y in range(0,H,64): db.line((0,y,W,y),fill='#111d30',width=1)
titles=['THE LANGUAGE OF SETS','WHAT IS A SET?','MEMBERSHIP','TWO IMPORTANT RULES','THE VENN DIAGRAM','INTERSECTION','UNION','THE EMPTY SET','PRACTICE QUESTION','THE SOLUTION']

def venn(d,t,mode):
 # Circles are drawn as outlines so their overlap remains clear.
 d.ellipse((255,169,655,569),outline=TEAL,width=5)
 d.ellipse((475,169,875,569),outline=BLUE,width=5)
 txt(d,330,190,'A',31,TEAL,True); txt(d,780,190,'B',31,BLUE,True)
 if mode=='diagram':
  events=[('1',360,365,'put one',TEAL),('4',770,365,'and four',BLUE),('2',535,335,'now look',GOLD),('3',595,397,'now look',GOLD)]
  for label,x,y,phrase,col in events:
   st=at(4,phrase)
   if t>=st:
    p=(t-st)/1.25
    chip(d,move(1000,x,p),move(205,y,p),label,col)
 else:
  for label,x,y,col in [('1',360,365,TEAL),('2',535,335,GOLD),('3',595,397,GOLD),('4',770,365,BLUE)]: chip(d,x,y,label,col)

def common(i,t,elapsed):
 im=BG.copy(); d=ImageDraw.Draw(im)
 d.rounded_rectangle((44,30,166,70),12,fill='#173a3a'); txt(d,60,38,'CSCA',19,TEAL,True)
 txt(d,190,38,'MATH  /  01',19,FAINT,True); txt(d,510,38,titles[i],20,WHITE,True)
 txt(d,1095,39,f'{i+1:02d} / 10',17,FAINT,True)
 d.rounded_rectangle((44,89,1236,94),2,fill=LINE); d.rounded_rectangle((44,89,44+int(1192*(elapsed+t)/TOTAL),94),2,fill=TEAL)
 return im,d

def render(i,t,elapsed):
 im,d=common(i,t,elapsed)
 if i==0:
  pop(d,76,140,'Math is a language.',t,0,52,WHITE)
  pop(d,78,219,'Learn to read it, one symbol at a time.',t,at(i,'you could'),26,FAINT,False)
  card(d,(70,310,590,510)); card(d,(690,310,1210,510))
  pop(d,110,350,'A = { 1, 2, 3 }',t,0.5,42,TEAL); pop(d,730,350,'B = { 2, 3, 4 }',t,1.2,42,BLUE)
  pop(d,110,435,'WHAT DO THEY SHARE?',t,at(i,'which numbers'),23,GOLD)
  pop(d,730,435,'SETS  •  SYMBOLS  •  PRACTICE',t,at(i,'you will learn'),20,FAINT)
 elif i==1:
  pop(d,70,130,'A collection of distinct objects',t,0,38,WHITE)
  example_start=at(i,'let a be')
  if t<example_start:
   # Examples appear when they are named, rather than leaving the panel empty.
   examples=[('NUMBERS',['1','2','3'],TEAL,at(i,'contain numbers')),
             ('LETTERS',['A','B','C'],BLUE,at(i,'letters')),
             ('OTHER OBJECTS',['●','▲','■'],GOLD,at(i,'other objects'))]
   for j,(label,items,col,start) in enumerate(examples):
    if t>=start:
     x=70+j*390
     card(d,(x,230,x+360,500),outline=col)
     pop(d,x+24,255,label,t,start,20,col)
     for k,item in enumerate(items):
      animated_chip(d,x+75+k*105,390,item,col,t,start+k*.18,32)
   if t<at(i,'contain numbers'):
    card(d,(190,230,1090,500)); pop(d,250,270,'ONE SET',t,at(i,'a set is'),23,TEAL)
    for j,item in enumerate(['1','2','3']):
     animated_chip(d,400+j*180,390,item,[TEAL,BLUE,GOLD][j],t,at(i,'distinct objects')+j*.2,42)
    pop(d,250,455,'The objects inside are called elements.',t,at(i,'those objects'),23,FAINT,False)
  else:
   card(d,(70,225,1210,525))
   pop(d,125,270,'A  =  { 1, 2, 3 }',t,example_start,59,TEAL)
   if t>=at(i,'we use curly'):
    d.rounded_rectangle((115,255,780,361),16,outline=GOLD,width=2); pop(d,850,290,'CURLY BRACKETS',t,at(i,'we use curly'),20,GOLD)
   pop(d,130,408,'A = name of the set',t,at(i,'notice that'),27,WHITE,False)
   pop(d,650,408,'1, 2, 3 = elements',t,at(i,'the numbers inside'),27,WHITE,False)
 elif i==2:
  pop(d,70,132,'Is it inside the set?',t,0,43)
  card(d,(70,217,1210,540)); txt(d,110,255,'A = { 1, 2, 3 }',42,TEAL,True)
  pop(d,112,350,'2 ∈ A',t,at(i,'so two'),46,WHITE); pop(d,430,365,'2 belongs to A',t,at(i,'so two'),27,TEAL,False)
  pop(d,112,440,'4 ∉ A',t,at(i,'four does'),46,WHITE); pop(d,430,455,'4 does not belong to A',t,at(i,'four does'),27,RED,False)
  # The element travels into the set; the non-member stays outside.
  d.ellipse((995,245,1185,435),outline=TEAL,width=3); txt(d,1073,260,'A',21,TEAL,True)
  inside=at(i,'so two'); outside=at(i,'four does')
  if t>=inside:
   progress=(t-inside)/1.4
   chip(d,move(915,1090,progress),move(340,348,progress),'2',TEAL,25)
  if t>=outside:
   animated_chip(d,970,475,'4',RED,t,outside,25)
   if t>=outside+.45:
    pop(d,1020,463,'OUTSIDE',t,outside+.45,18,RED)
 elif i==3:
  pop(d,70,130,'Two rules to remember',t,0,42)
  card(d,(70,210,1210,345)); txt(d,100,232,'01  ORDER DOES NOT MATTER',21,TEAL,True)
  pop(d,100,270,'{ 1, 2, 3 }  =  { 3, 1, 2 }',t,at(i,'the set one'),37,WHITE)
  card(d,(70,375,1210,540)); pop(d,100,398,'02  REPEATS DO NOT COUNT TWICE',t,at(i,'second repetition'),21,GOLD)
  pop(d,100,443,'{ 1, 2, 2, 3 }  =  { 1, 2, 3 }',t,at(i,'the set one',1),35,WHITE)
  # Show the permutation as moving numbers, then mark the duplicate.
  order=at(i,'the same as')
  if order<=t<at(i,'second repetition'):
   p=(t-order)/1.8
   for a,b,num,col in [(870,970,'1',TEAL),(970,1070,'2',BLUE),(1070,870,'3',GOLD)]:
    chip(d,move(a,b,p),302-32*math.sin(math.pi*min(1,max(0,p))),num,col,23)
  repetition=at(i,'count each')
  if t>=repetition:
   # Strike only the repeated second 2 in the left-hand set.
   x=100+d.textlength('{ 1, 2, ',font=ft(35,True))
   progress=ease((t-repetition)/.6)
   d.line((x-3,482,x-3+31*progress,482-37*progress),fill=RED,width=4)
   pop(d,720,457,'COUNT ONCE',t,repetition,20,RED)
 elif i==4:
  venn(d,t,'diagram'); txt(d,900,175,'A',24,TEAL,True); txt(d,935,175,'= { 1, 2, 3 }',23,WHITE,True)
  pop(d,900,225,'B',t,at(i,'let b'),24,BLUE); pop(d,935,225,'= { 2, 3, 4 }',t,at(i,'let b'),23,WHITE)
  pop(d,904,350,'OVERLAP',t,at(i,'they are in both'),23,GOLD); pop(d,904,385,'= IN BOTH',t,at(i,'they are in both'),21,FAINT)
 elif i==5:
  pop(d,70,128,'Intersection = BOTH',t,0,43,WHITE)
  card(d,(70,210,575,545)); txt(d,100,235,'A = { 1, 2, 3 }',30,TEAL,True); txt(d,100,285,'B = { 2, 3, 4 }',30,BLUE,True)
  for y,num,phrase,result,col in [(350,'1','one is not','NOT IN B',RED),(415,'2','two is in b','KEEP',TEAL),(480,'3','three is also','KEEP',TEAL)]:
   st=at(i,phrase)
   if st<=t<st+2.1:
    d.rounded_rectangle((90,y-8,545,y+45),10,outline=col,width=3)
   pop(d,105,y,num,t,st,33,col); pop(d,180,y+3,result,t,st,25,col)
  card(d,(625,210,1210,545)); txt(d,665,245,'A ∩ B',48,GOLD,True)
  reveal=at(i,'the intersection is',1)
  for num,phrase,y,dest in [('2','two is in b',415,800),('3','three is also',480,885)]:
   st=at(i,phrase)
   if st<=t<reveal:
    p=(t-st-.3)/1.0
    if p>0: chip(d,move(550,dest,p),move(y,375,p),num,TEAL,26)
  pop(d,665,345,'= { 2, 3 }',t,reveal,43,WHITE)
  pop(d,665,445,'IN A  AND  IN B',t,at(i,'a good test'),24,FAINT)
 elif i==6:
  pop(d,70,128,'Union = EITHER (or both)',t,0,40,WHITE)
  card(d,(70,210,1210,545)); txt(d,110,240,'A = { 1, 2, 3 }',32,TEAL,True); txt(d,110,293,'B = { 2, 3, 4 }',32,BLUE,True)
  txt(d,110,378,'A ∪ B  =',42,GOLD,True)
  starts=[at(i,'start with'),at(i,'start with'),at(i,'start with'),at(i,'four is new')]
  for j,(num,st) in enumerate(zip(['1','2','3','4'],starts)):
   if t>=st:
    progress=(t-st-j*.14)/1.1
    if progress>=0: chip(d,move(300+j*45,450+j*85,progress),move(270 if j<3 else 320,410,progress),num,TEAL if j<3 else BLUE)
  pop(d,110,475,'NO REPEATS',t,at(i,'already included'),22,FAINT)
 elif i==7:
  pop(d,70,130,'When nothing is shared',t,0,42)
  card(d,(70,210,1210,540)); txt(d,110,245,'C = { 5, 6 }',34,TEAL,True); txt(d,670,245,'D = { 7, 8 }',34,BLUE,True)
  pop(d,110,325,'C ∩ D = ∅ = { }',t,at(i,'their intersection'),40,GOLD)
  pop(d,110,405,'∅  ≠  { 0 }',t,at(i,'do not write zero'),40,WHITE)
  pop(d,700,422,'empty       one element',t,at(i,'the set containing zero'),19,FAINT,False)
  pop(d,110,475,'C ∪ D = { 5, 6, 7, 8 }',t,at(i,'their union'),30,TEAL)
 elif i==8:
  pop(d,70,124,'Your turn: choose one answer',t,0,38)
  pop(d,72,185,'P = { 1, 3, 5, 7 }',t,at(i,'let p'),32,TEAL)
  pop(d,650,185,'Q = { 3, 4, 7 }',t,at(i,'let q'),32,BLUE)
  pop(d,72,240,'P ∩ Q = ?',t,at(i,'which answer'),35,GOLD)
  for j,(lab,val) in enumerate([('A','{ 1, 5 }'),('B','{ 3, 7 }'),('C','{ 1, 3, 4, 5, 7 }'),('D','{ 4 }')]):
   st=at(i,'option '+lab.lower()); x=70+(j%2)*575; y=310+(j//2)*106
   if t>=st: card(d,(x,y,x+535,y+80)); pop(d,x+24,y+20,lab,t,st,27,GOLD); pop(d,x+70,y+20,val,t,st,27,WHITE)
  pop(d,78,535,'PAUSE THE VIDEO TO SOLVE',t,at(i,'pause the video'),20,TEAL)
 elif i==9:
  pop(d,70,123,'Let’s check each element of P',t,0,38)
  card(d,(70,200,600,550)); txt(d,100,218,'P = { 1, 3, 5, 7 }',29,TEAL,True); txt(d,100,264,'Q = { 3, 4, 7 }',29,BLUE,True)
  for j,(num,phrase,label,col) in enumerate([('1','one is in p','NOT IN Q',RED),('3','three is in both','IN BOTH',TEAL),('5','five is not','NOT IN Q',RED),('7','seven is in both','IN BOTH',TEAL)]):
   st=at(i,phrase); pop(d,105,325+j*47,num,t,st,27,col); pop(d,180,325+j*47,label,t,st,22,col)
  card(d,(650,200,1210,550)); pop(d,687,245,'P ∩ Q = { 3, 7 }',t,at(i,'so p intersect'),35,WHITE)
  pop(d,687,330,'ANSWER  B',t,at(i,'option b'),32,TEAL)
  pop(d,687,413,'BOTH = INTERSECTION',t,at(i,'intersection means both'),21,GOLD)
  pop(d,687,460,'EITHER = UNION',t,at(i,'union means either'),21,BLUE)
 # At a pause, bisect keeps the most recently started word active. Future
 # words affect centering only: their glyphs are never drawn before their start.
 state=caption_state(i,t)
 if state:
  group,active=state; f=ft(28,True)
  widths=[d.textlength(w,font=f) for _,w in group]; total=sum(widths)+14*(len(group)-1); x=(W-total)/2
  d.rounded_rectangle((max(25,int(x-25)),607,min(1255,int(x+total+25)),668),15,fill='#17263a')
  for (index,w),width in zip(group,widths):
   if index<=active: txt(d,x,620,w,28,TEAL if index==active else WHITE,True)
   x+=width+14
 txt(d,45,688,'CSCA MATH  •  SETS',15,FAINT,True)
 txt(d,1040,688,'EPISODE 01',15,FAINT,True)
 return im

def main():
 out=R/'output';out.mkdir(exist_ok=True)
 if len(sys.argv)>1 and sys.argv[1]=='--preview':
  for i in range(10):
   render(i,DURS[i]*.65,sum(DURS[:i])+.35*i).save(out/f'preview-{i+1:02}.png')
  return
 parts=[]; elapsed=0
 for i,seconds in enumerate(DURS):
  seconds+=.35; frames=math.ceil(seconds*FPS); segment=out/f'part-{i+1:02}.mp4'; parts.append(segment)
  cmd=[FF,'-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate',str(FPS),'-i','-','-i',str(R/'audio'/f'{i+1:02}.mp3'),'-af','apad','-t',f'{seconds:.3f}','-c:v','libx264','-preset','veryfast','-crf','22','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-ar','44100','-ac','2',str(segment)]
  print(f'Rendering {i+1}/10 ({seconds:.1f}s)',flush=True)
  proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
  try:
   for f in range(frames): proc.stdin.write(render(i,f/FPS,elapsed).tobytes())
  finally: proc.stdin.close()
  if proc.wait()!=0: raise RuntimeError(f'FFmpeg failed at scene {i+1}')
  elapsed+=seconds
 (out/'concat.txt').write_text(''.join(f"file '{p.name}'\n" for p in parts))
 result=out/'CSCA_Math_01_Sets_Full.mp4'
 subprocess.run([FF,'-loglevel','error','-y','-f','concat','-safe','0','-i',str(out/'concat.txt'),'-c','copy','-movflags','+faststart',str(result)],check=True)
 for p in parts:p.unlink()
 (out/'concat.txt').unlink()
 print('Wrote',result,flush=True)
if __name__=='__main__': main()
