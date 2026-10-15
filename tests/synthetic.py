"""Procedural fixtures with explicit ground truth; never substitutes for user photos."""
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

CASES = ['black_white','black_color','black_outline','white_dark','complex_color','gradient_shadow','perspective','folds','similar_color']


def sample(case='black_white'):
    w,h = 360,420
    bg = (238,238,233) if case=='white_dark' else (23,25,28)
    image = Image.new('RGB',(w,h),bg)
    design = Image.new('RGBA',(w,h))
    d = ImageDraw.Draw(design)
    font_path=Path('C:/Windows/Fonts/arialbd.ttf')
    font=ImageFont.truetype(str(font_path),44) if font_path.exists() else ImageFont.load_default(size=44)
    color = (30,32,35) if case=='white_dark' else (35,38,41) if case=='similar_color' else (245,245,242)
    colorful=case in {'black_color','complex_color'}
    for i,text in enumerate(['PRINT','2026']):
        d.text((70,135+i*60),text,font=font,fill=(255,110+40*i,60) if colorful else color,
               stroke_width=5 if case=='black_outline' else 0,stroke_fill=bg)
    if case=='complex_color':
        for x,y,c in [(90,115,'cyan'),(260,130,'magenta'),(110,295,'yellow')]:
            d.ellipse((x-15,y-15,x+15,y+15),fill=c)
        d.line([(60,125),(280,300)], fill='cyan',width=2)
    if case=='gradient_shadow':
        a=np.array(design)
        ys,xs=np.mgrid[:h,:w]
        a[:,:,:3]=np.stack([xs/w*200+45,ys/h*160+60,np.full((h,w),190)],axis=2).astype(np.uint8)
        design=Image.fromarray(a)
        shadow=design.getchannel('A').filter(__import__('PIL.ImageFilter',fromlist=['GaussianBlur']).GaussianBlur(4))
        shadow_img=Image.new('RGBA',(w,h),(60,60,65,0));shadow_img.putalpha(shadow)
        shadow_img.alpha_composite(design)
        design=shadow_img
    truth=design.getchannel('A')
    image=image.convert('RGBA');image.alpha_composite(design)
    if case=='perspective':
        p=np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]])
        q=np.float32([[35,20],[330,45],[350,390],[10,410]])
        matrix=cv2.getPerspectiveTransform(p,q)
        image=Image.fromarray(cv2.warpPerspective(np.array(image),matrix,(w,h),borderValue=(*bg,255)))
        truth=Image.fromarray(cv2.warpPerspective(np.array(truth),matrix,(w,h)))
    if case=='folds':
        yy,xx=np.mgrid[:h,:w].astype(np.float32)
        mx=xx+7*np.sin(yy/16)
        a=cv2.remap(np.array(image),mx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT)
        shade=(.8+.2*np.sin(xx/24))[:,:,None]
        a[:,:,:3]=(a[:,:,:3]*shade).astype(np.uint8)
        image=Image.fromarray(a)
        truth=Image.fromarray(cv2.remap(np.array(truth),mx,yy,cv2.INTER_LINEAR))
    return image,truth


def metrics(mask, truth):
    a=np.array(mask)>127;b=np.array(truth)>127
    tp=int((a&b).sum());fp=int((a&~b).sum());fn=int((~a&b).sum())
    return {'iou':tp/max(1,tp+fp+fn),'precision':tp/max(1,tp+fp),'recall':tp/max(1,tp+fn)}


def generate(destination):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    for case in CASES:
        image,truth=sample(case)
        image.save(destination/(case+'.png'));truth.save(destination/(case+'.mask.png'))


if __name__=='__main__':
    generate('tests/fixtures/synthetic')
