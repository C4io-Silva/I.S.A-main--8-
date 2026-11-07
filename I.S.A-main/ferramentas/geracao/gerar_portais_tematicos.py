"""Arte 48x32px: portal de 3x2 tiles, escalado para 144x96 sem antialias."""
from PIL import Image, ImageDraw
from pathlib import Path
p=Path(__file__).resolve().parents[2]/'assets/images/passagens'
p.mkdir(exist_ok=True,parents=True)

def draw_portal(kind, reverse=False):
 im=Image.new('RGBA',(48,32));d=ImageDraw.Draw(im)
 if kind=='cave':
  material=(74,68,80);bright=(121,111,130);dark=(33,31,44);glow=(63,138,162)
 elif kind=='canopy':
  material=(93,64,40);bright=(151,113,61);dark=(23,63,43);glow=(99,184,112)
 else:
  material=(81,73,91);bright=(162,136,101);dark=(59,42,65);glow=(226,183,85)
 # Tiny, strong silhouette. Columns + lintel keep center visually open.
 d.rectangle((12,9,35,31), fill=material)
 d.rectangle((15,10,32,29), fill=dark)
 d.ellipse((13,2,34,17), fill=material)
 d.ellipse((16,6,31,20), fill=dark)
 d.rectangle((16,13,31,30), fill=dark)
 # Interior tint reads as receding light, no costly frame particles.
 for y in range(12,30):
  alpha=int(95+(y-12)*5) if reverse else int(165-(y-12)*5)
  d.line((19,y,29,y),fill=(*glow,alpha))
 d.rectangle((10,27,37,31),fill=material)
 for x in (11,12,35,36):
  d.line((x,14,x,28),fill=bright,width=1)
 for x in (15,19,23,27,31):
  d.point((x,7),fill=bright)
 if kind=='cave':
  for x in (6,42):
   d.polygon([(x-3,29),(x,19),(x+3,29)],fill=(63,132,166,255))
   d.polygon([(x,22),(x+3,29),(x,29)],fill=(141,209,214,255))
 elif kind=='canopy':
  for x in (9,37):
   d.line((x,9,x-2,29),fill=(52,113,49,255),width=2)
   d.ellipse((x-7,12,x+1,17),fill=(81,149,70,255))
  d.ellipse((7,4,17,11),fill=(60,112,57,255))
  d.ellipse((29,1,41,10),fill=(54,128,65,255))
 else:
  for x in (11,36):
   d.rectangle((x-2,18,x+2,20),fill=(207,155,81,255))
   d.polygon([(x-1,18),(x,11),(x+2,18)],fill=(255,195,93,255))
  d.rectangle((20,3,27,6),fill=(211,174,110,255))
 return im.resize((144,96),Image.Resampling.NEAREST)

for name,kind,reverse in (
  ('entrada_caverna.png','cave',False),('saida_caverna.png','cave',True),
  ('subida_copas.png','canopy',False),('descida_copas.png','canopy',True),
  ('portal_arena.png','arena',False),('saida_arena.png','arena',True)):
 draw_portal(kind,reverse).save(p/name)
print('6 sprites de portais gerados em 144x96')
