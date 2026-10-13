"""Render the original, illustrative ADI walkthrough (Pillow + system ffmpeg)."""
from pathlib import Path
import math
import subprocess
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]
FONT=Path('/usr/share/fonts/truetype/dejavu')
def font(size,bold=False):return ImageFont.truetype(str(FONT/('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')),size)
def render(t):
    im=Image.new('RGB',(1280,720),'#191b22');d=ImageDraw.Draw(im)
    def text(x,y,s,size=18,color='#eeeef3',bold=False):d.text((x,y),s,font=font(size,bold),fill=color)
    def box(rect,color,r=12):d.rounded_rectangle(rect,r,fill=color)
    phase=min(int(t//6),2)
    text(48,30,'A / AGENTIC DOCUMENT INTELLIGENCE',16,'#ffa16b',True)
    text(960,32,'ILLUSTRATIVE EXAMPLE',12,'#969bac')
    box((40,95,530,626),'#fff5e9',16)
    text(75,128,'PROJECT BRIEF.PDF  /  PAGE 2',13,'#9d7454',True)
    text(75,196,'The launch plan.',28,'#49372a',True)
    text(75,252,'A small pilot. A clear starting point.',17,'#8a715d')
    highlight='#ffdcc0' if phase==2 else '#eee0d0'
    box((73,315,490,407),highlight,8)
    text(88,334,'The project launches on',20,'#6c5039')
    text(88,367,'12 November.',20,'#6c5039',True)
    for y,w in [(451,350),(479,315),(507,366)]:box((78,y,78+w,y+6),'#e4d5c2',3)
    text(78,564,'The pilot includes three teams.',16,'#937355')
    box((564,95,1240,626),'#22252e',16)
    text(605,131,['01  /  BRING YOUR SOURCES','02  /  ASK YOUR DOCUMENTS','03  /  FOLLOW THE EVIDENCE'][phase],13,'#ff9b65',True)
    if phase==0:
        text(605,196,'Start with what you know.',29,bold=True)
        box((610,270,1192,477),'#2c2f38',12)
        text(807,300,'↑',46,'#ffa16b')
        text(726,370,'Project brief.pdf',21,bold=True)
        progress=min(t/4,1)
        box((675,426,1135,434),'#49424a',4)
        box((675,426,675+max(8,int(460*progress)),434),'#ef4b05',4)
        text(720,513,'PDF → passages → search index',17,'#bec0cb')
    elif phase==1:
        text(605,196,'Ask a focused question.',29,bold=True)
        box((604,280,1200,377),'#30343f',12)
        question='When does the project launch?'
        text(632,315,question[:min(len(question),int((t-6)*14))],22)
        box((946,404,1199,459),'#ef4b05',9)
        text(971,421,'Ask your documents →',16,'white',True)
        text(608,510,'Search relevant passages in your PDFs.',17,'#bec0cb')
    else:
        text(605,193,'An answer, with a source.',29,bold=True)
        text(607,264,'The project launches on',25)
        text(607,302,'12 November. [S1]',25,'#ffa16b',True)
        box((606,371,1196,420),'#293b35',8)
        text(628,386,'✓  Supported by the example passage',16,'#b2e5c5')
        box((606,443,1196,506),'#30343f',8)
        text(627,465,'[S1]  Project brief.pdf · page 2  ↗',17,'#ffa16b')
        text(609,553,'Review the original page before relying on an answer.',14,'#bec0cb')
    for i,label in enumerate(['UPLOAD','ASK','INSPECT']):
        x=400+i*180;box((x,663,x+130,695),'#ef4b05' if i==phase else '#30343f',16);text(x+22,671,label,12,'white' if i==phase else '#9ca2b0',True)
    return im
if __name__=='__main__':
    out=ROOT/'frontend/public/adi-walkthrough.mp4'
    p=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pixel_format','rgb24','-video_size','1280x720','-framerate','20','-i','-','-an','-c:v','libx264','-preset','fast','-crf','25','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],stdin=subprocess.PIPE)
    for frame in range(400):p.stdin.write(render(frame/20).tobytes())
    p.stdin.close()
    if p.wait():raise SystemExit('Video encoding failed')
    print(f'{out}: {out.stat().st_size} bytes')
