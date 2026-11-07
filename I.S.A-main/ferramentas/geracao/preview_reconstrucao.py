"""Preview de composicao via Pillow. NAO e captura do runtime Pygame.
Combina as mesmas imagens e coordenadas de tiles usadas pelo jogo, com camera
estatistica; usa para revisar arte antes do teste de partida manual.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import sys,json,csv
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R));from src.nucleo import constants
T=constants.TILE_SIZE; W,H=800,600
A=R/'assets/images';L=R/'assets/levels';data=json.loads((L/'estruturas_cenario.json').read_text())

def pic(p,size=None):
 img=Image.open(p).convert('RGBA')
 return img.resize(size,Image.Resampling.NEAREST) if size else img

def overlay_tiled(screen,img,camera_x,factor):
 width=img.width; offset=-int(camera_x*factor)%width
 for x in range(offset-width,W+width,width):screen.alpha_composite(img,(x,0))

def stage(name,center_col):
 with (L/'setores'/f'{name}.csv').open() as f:g=[[int(v) for v in row] for row in csv.reader(f)]
 with (L/'decoracoes'/f'{name}_decor.csv').open() as f:decor=[[int(v) for v in row] for row in csv.reader(f)]
 ground=min((y for y in range(14,44) if g[y][center_col] in constants.SOLID_TILES and g[y-1][center_col] not in constants.SOLID_TILES),default=26)
 cx=max(0,min(center_col*T-W//2,len(g[0])*T-W));cy=max(0,min(ground*T-H*2//3,44*T-H))
 cfg=constants.AMBIENTES[name]
 b=pic(A/'backgrounds'/cfg['camadas'][0][0]);screen=Image.new('RGBA',(W,H),cfg['cor_ceu']+(255,))
 overlay_tiled(screen,b,cx,cfg['camadas'][0][1])
 for filename,fac in cfg['camadas'][1:]:overlay_tiled(screen,pic(A/'backgrounds'/filename),cx,fac)
 for item in data[name]:
  img=pic(A/'cenarios'/item['imagem']);img=img.resize((img.width*constants.SCALE,img.height*constants.SCALE),Image.Resampling.NEAREST)
  px=item['coluna']*T-img.width//2-cx;py=item['base']*T-img.height-cy
  if px < W and py < H and px+img.width>0 and py+img.height>0:screen.alpha_composite(img,(px,py))
 from src.mundo.decoracoes_offline import ARTE
 dc={k:pic(A/'tiles'/v,(T,T)) for k,v in ARTE.items()}
 tile={k:pic(A/'tiles'/v,(T,T)) for k,v in constants.TILE_SPRITES.items()}
 fallback=tile[constants.TILE_FALLBACK_ID]
 xmin=max(0,cx//T-1); xmax=min(len(g[0]),(cx+W)//T+3);ymin=max(0,cy//T-1);ymax=min(44,(cy+H)//T+3)
 for y in range(ymin,ymax):
  for x in range(xmin,xmax):
   px=x*T-cx;py=y*T-cy
   d=dc.get(decor[y][x]);
   if d:screen.alpha_composite(d,(px,py))
   v=g[y][x]
   if v in constants.SOLID_TILES:screen.alpha_composite(tile.get(v,fallback),(px,py))
 for y in range(ymin,ymax):
  for x in range(xmin,xmax):
   v=g[y][x]
   if v in constants.TILES_PASSAGEM:
    file={'CAVE_ENTRY':'entrada_caverna.png','CAVE_EXIT':'saida_caverna.png',
          'CANOPY_ENTRY':'subida_copas.png','CANOPY_EXIT':'descida_copas.png',
          'ARENA_ENTRY':'portal_arena.png','ARENA_EXIT':'saida_arena.png'}[constants.PASSAGENS_CSV[v]['tipo']]
    img=pic(A/'passagens'/file)
    # Same exclusion of solid cells applied by src/passagens.py
    mask=Image.new('RGBA',img.size);mask.alpha_composite(img)
    for dl in range(2):
     for dcx in range(3):
      xx=x-1+dcx;yy=y-1+dl
      if 0<=yy<44 and 0<=xx<len(g[0]) and g[yy][xx] in constants.SOLID_TILES:
       mask.paste((0,0,0,0),(dcx*T,dl*T,(dcx+1)*T,(dl+1)*T))
    px=(x-1)*T-cx;py=(y-1)*T-cy
    screen.alpha_composite(mask,(px,py))
   if v==91:
    # only for test map screenshot -- cyan diamond where collectable exists
    px=x*T-cx+T//2;py=y*T-cy+T//2
    d=ImageDraw.Draw(screen)
    d.polygon([(px,py-9),(px+6,py),(px,py+8),(px-6,py)],fill=(244,190,73,240))
  
 d=ImageDraw.Draw(screen);d.rectangle((0,0,W,30),fill=(12,19,25,235));d.text((12,7),f'{name.upper()}  |  composicao offline  |  col {center_col}',fill=(240,245,239,255))
 return screen.convert('RGB')

names=[('floresta',89),('caverna',113),('copas',82),('arena',21)]
res=Image.new('RGB',(W*2,H*2))
for i,(name,col) in enumerate(names):
 im=stage(name,col);res.paste(im,((i%2)*W,(i//2)*H));im.save(R/'docs'/f'PREVIEW_OFFLINE_{name}.png')
res.save(R/'docs/PREVIEWS_OFFLINE_QUATRO_SETORES.png')
print('previews offline geradas (nao sao screenshots do jogo)')
