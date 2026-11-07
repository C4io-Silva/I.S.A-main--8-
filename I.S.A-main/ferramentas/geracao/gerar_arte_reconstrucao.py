"""Gera elementos modulares de cenario em pixel art nativa (assets/images/cenarios/).
Ferramenta de construcao: precisa de Pillow; o jogo so precisa dos PNGs prontos.
Imagens transparentes, desenho deterministico, dimensoes multiplas de 16px.
"""
from pathlib import Path
from PIL import Image, ImageDraw
import random, math

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'assets/images/cenarios';OUT.mkdir(parents=True,exist_ok=True)

def el(draw,xy,fill): draw.ellipse(tuple(map(int,xy)),fill=fill)
def poly(draw,coords,fill): draw.polygon([(int(x),int(y)) for x,y in coords],fill=fill)

def tree(kind, seed):
    rnd=random.Random(seed)
    if kind=='floresta': W,H=160,288;main=(73,48,30);highlight=(109,78,45);leaf=(22,64,46);leaf2=(32,89,59);leaf3=(53,118,76)
    else: W,H=192,528;main=(79,54,35);highlight=(132,90,49);leaf=(30,86,53);leaf2=(47,118,67);leaf3=(74,151,84)
    im=Image.new('RGBA',(W,H));d=ImageDraw.Draw(im)
    cx=W//2;tw=16 if kind=='floresta' else 30
    # Roots taper into the floor while trunks are irregular, not rectangular poles.
    poly(d,[(cx-tw//2,40),(cx+tw//2,40),(cx+tw*0.63,H-36),(cx+tw*1.2,H-2),(cx+tw//4,H-27),(cx-3,H-5),(cx-tw*1.5,H-3),(cx-tw*.57,H-33)],main)
    d.polygon([(cx+3,60),(cx+9,75),(cx+6,H-37),(cx+2,H-20),(cx-1,H-54)],fill=highlight)
    for xx in range(11,H-22,19):
        x=cx+rnd.randint(-4,9)
        d.line((x,xx,x-2,xx+8), fill=(45,37,30,255),width=2)
    # Major branching elbows lead out to support the traversable canopy routes.
    joints=[(H*.34,-1),(H*.53,1),(H*.66,-1)] if kind=='copas' else [(H*.35,-1),(H*.58,1)]
    for y,dirn in joints:
        endx=cx+dirn*(W*.40)
        poly(d,[(cx-6,y+9),(cx+6,y+3),(endx,y-31),(endx,y-21),(cx+5,y+19)],main)
        d.line((cx,y+7,endx,y-27),fill=highlight,width=2)
        # offshoot stems, small foliage groups
        for k in range(6):
            ox=endx+dirn*rnd.randrange(-12,16);oy=y-28+rnd.randrange(-12,13)
            el(d,(ox-11,oy-6,ox+10,oy+5),leaf2)
            el(d,(ox-7,oy-10,ox+6,oy+1),leaf3)
    # Crown is built as overlapping organic leaf clusters, with negative space.
    canopy_y=38 if kind=='floresta' else 67
    for k in range(90 if kind=='copas' else 60):
        xx=cx + rnd.gauss(0,W*.23)
        yy=canopy_y+rnd.gauss(0,21 if kind=='floresta' else 33)
        if xx<4 or xx>W-4 or yy<3 or yy>H*.29:continue
        rad=rnd.randrange(7,18) if kind=='floresta' else rnd.randrange(9,22)
        el(d,(xx-rad,yy-rad*.72,xx+rad,yy+rad*.7), leaf if k%4==0 else (leaf2 if k%3 else leaf3))
    # Highlights deliberately sparse, to avoid noisy auto-generated texture.
    for k in range(26 if kind=='floresta' else 45):
        x=rnd.randrange(11,W-10);y=rnd.randrange(8,int(H*.24))
        if im.getpixel((x,y))[3]:
            d.rectangle((x,y,x+2,y+1),fill=(108,167,99,215))
    return im

def cave_arch(seed):
    rnd=random.Random(seed);W,H=160,256
    im=Image.new('RGBA',(W,H));d=ImageDraw.Draw(im)
    # Natural boulder frames on either side, empty center so the player remains readable.
    for side in (-1,1):
        x=0 if side==-1 else W-1
        dx=1 if side==-1 else -1
        poly(d,[(x,H),(x,H-155),(x+dx*13,H-185),(x+dx*28,H-157),(x+dx*24,H-90),(x+dx*18,H)],(47,47,63,250))
        d.line((x+dx*10,H-145,x+dx*15,H-60),fill=(91,88,98,220),width=3)
        for k in range(6):
            by=H-rnd.randrange(50,170)
            xx=x+dx*rnd.randrange(5,22)
            d.line((xx,by,xx+dx*3,by+18),fill=(112,101,118,155),width=2)
    poly(d,[(0,H-174),(15,H-204),(45,H-207),(55,H-198),(92,H-211),(136,H-198),(159,H-178),(159,H-230),(0,H-240)],(36,34,51,255))
    for x in (22,48,103,144):
        height=rnd.randint(12,35)
        poly(d,[(x-6,H-200),(x+7,H-200),(x,H-200+height)],(71,69,91,240))
    for x in (26,122):
        y=H-rnd.randrange(35,85)
        c=(60,151,185,220) if x==26 else (151,91,186,220)
        poly(d,[(x-7,y),(x-3,y-16),(x+4,y),(x,y-22),(x+9,y)],c)
    return im

def roots_bridge():
    W,H=192,64
    im=Image.new('RGBA',(W,H));d=ImageDraw.Draw(im)
    for j in range(4):
        y=21+j*7
        d.line((2,y,55,y-7,111,y+5,190,y-5),fill=(73+j*6,55+j*5,36,235),width=5 if j==0 else 3)
    for x in range(7,190,21):
        d.line((x,29,x+3,48),fill=(34,79,46,210),width=2)
    return im

def arena_column(seed):
    W,H=80,288;im=Image.new('RGBA',(W,H));d=ImageDraw.Draw(im)
    d.rectangle((19,27,61,H-12),fill=(60,57,73,210))
    d.rectangle((25,27,31,H-13),fill=(91,82,98,190))
    d.rectangle((12,19,68,39),fill=(104,89,104,250))
    d.rectangle((12,H-28,68,H-9),fill=(98,88,103,240))
    for y in range(52,H-38,21):
        d.line((20,y,60,y),fill=(36,34,50,220),width=2)
    # Banners from the ruin, keep middle open.
    if seed%2:
        poly(d,[(34,49),(60,49),(60,124),(47,137),(34,124)],(110,49,63,230))
        d.line((40,62,53,65),fill=(215,158,86,255),width=3)
    return im

for name,img in {'arvore_antiga.png':tree('floresta',17), 'arvore_antiga_alt.png':tree('floresta',31),
                 'arvore_copas.png':tree('copas',25), 'arvore_copas_alt.png':tree('copas',99),
                 'arco_rochoso.png':cave_arch(13),'arco_rochoso_alt.png':cave_arch(30),
                 'ponte_raizes.png':roots_bridge(),
                 'coluna_santuario.png':arena_column(1),'coluna_santuario_alt.png':arena_column(2)}.items():
    img.save(OUT/name)

# Parallax backgrounds: two coherent, repeatable pixel-art layers per biome.
def bg(nome,stage):
    W,H=480,300; rnd=random.Random(sum(map(ord,nome))*100+stage)
    far=(stage==0)
    if nome=='floresta':
        im=Image.new('RGBA',(W,H),(22,50,46,255) if far else (0,0,0,0));d=ImageDraw.Draw(im)
        if far:
            for y in range(H):
                t=y/H; d.line((0,y,W,y),fill=(int(31-13*t),int(69-18*t),int(66-15*t),255))
        for x in range(-10,W+40,35 if far else 58):
            w=rnd.randrange(8,20) if far else rnd.randrange(12,25)
            top=rnd.randrange(-80,15);bot=H
            tint=(27,71,57,170) if far else (12,39,33,170)
            d.rectangle((x,top,x+w,bot),fill=tint)
            for h in (rnd.randrange(40,95),rnd.randrange(90,140)):
                y=H-h
                d.polygon([(x+w//2,y),(x-22,y+21),(x+w+22,y+25)],fill=tint)
            for i in range(6):
                px=x+rnd.randrange(-26,36);py=rnd.randrange(3,80)
                el(d,(px-21,py-9,px+23,py+12), (24,64,47,230) if far else (9,46,34,200))
        return im
    if nome=='copas':
        im=Image.new('RGBA',(W,H),(118,201,214,255) if far else (0,0,0,0));d=ImageDraw.Draw(im)
        if far:
            for y in range(H):
                t=y/H;d.line((0,y,W,y),fill=(int(103+70*t),int(184+38*t),int(214+7*t),255))
            for x in [36,155,256,370,453]:
                y=45+rnd.randrange(-15,20)
                for dx,dy,r in [(-20,0,16),(0,-9,22),(26,3,16)]: el(d,(x+dx-r,y+dy-r//2,x+dx+r,y+dy+r//2),(231,247,230,220))
            for x in range(-10,W+30,28):
                height=rnd.randint(35,90)
                el(d,(x-24,H-height,x+28,H+20),(66,133,110,175))
        else:
            for x in range(0,W+60,87):
                d.rectangle((x+15,154,x+26,H),fill=(52,104,69,110))
                for j in range(11):
                    xx=x+rnd.randint(-30,48); yy=rnd.randint(132,193)
                    el(d,(xx-17,yy-14,xx+17,yy+9),(36,106,65,115))
        return im
    if nome=='caverna':
        im=Image.new('RGBA',(W,H),(17,16,28,255) if far else (0,0,0,0));d=ImageDraw.Draw(im)
        if far:
            for y in range(H):
                t=y/H;d.line((0,y,W,y),fill=(int(24-8*t),int(23-7*t),int(35+6*t),255))
            for x in range(-20,W+30,65):
                d.polygon([(x,0),(x+42,0),(x+29,rnd.randrange(45,120))],fill=(35,34,50,255))
                d.polygon([(x,H),(x+45,H),(x+19,H-rnd.randrange(30,86))],fill=(31,30,49,255))
        else:
            for x in range(-30,W+40,73):
                d.polygon([(x,0),(x+47,0),(x+32,rnd.randrange(16,64))],fill=(13,12,22,190))
            for x in range(12,W,105):
                yy=H-rnd.randint(36,78)
                for dx,c in [(0,(50,128,171,165)),(9,(108,76,164,145))]:
                    d.polygon([(x+dx-7,yy),(x+dx,yy-21),(x+dx+5,yy)],fill=c)
        return im
    if nome=='arena':
        im=Image.new('RGBA',(W,H),(32,30,44,255));d=ImageDraw.Draw(im)
        for y in range(H):
            d.line((0,y,W,y),fill=(int(31+y*.016),int(29+y*.014),int(44+y*.014),255))
        for x in range(-40,W+100,112):
            d.rectangle((x,41,x+17,H),fill=(62,55,69,255))
            d.rectangle((x+2,43,x+6,H),fill=(83,73,87,255))
            d.rectangle((x-7,35,x+24,47),fill=(100,87,100,255))
            d.arc((x+28,57,x+117,185),180,360,fill=(66,59,75,255),width=8)
        for y in range(190,H,30):
            d.line((0,y,W,y),fill=(60,53,66,200),width=2)
        return im

paths={('floresta',0):'pro_floresta_fundo.png',('floresta',1):'pro_floresta_frente.png',
       ('copas',0):'pro_copas_fundo.png',('copas',1):'pro_copas_frente.png',
       ('caverna',0):'caverna_fundo.png',('caverna',1):'caverna_frente.png',('arena',0):'pro_arena_fundo.png'}
for (name,stage),filename in paths.items():
    bg(name,stage).resize((960,600),Image.Resampling.NEAREST).save(ROOT/'assets/images/backgrounds'/filename)
print('gerados',len(list(OUT.glob('*.png'))),'sprites e',len(paths),'fundos')
