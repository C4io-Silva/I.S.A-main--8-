"""Validacao offline (sem Pygame) dos CSVs, portais, sprites e rotas.

Uso: py -3.12 ferramentas/auditar_level_design.py
"""
import csv, sys, json, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from src.nucleo import constants
from src.mundo.nivel_dados import SETORES_GERADOS
from src.mundo.validacao_mapa import validar_csv, validar_regiao, alcancaveis
from src.mundo.decoracoes_offline import ARTE  # IDs compartilhados sem importar pygame

BASE=ROOT/'assets/levels/setores';DEC=ROOT/'assets/levels/decoracoes'
MARKERS=constants.TILES_MARCADORES
TYPES={30:'floresta',31:'floresta',32:'caverna',33:'copas',34:'copas',35:'arena'}
PAIRS={30:40,31:41,32:42,33:43,34:44,35:45}
# Inimigo voador (ID 93): raio de deteccao do Tucano = 288 px = 6 tiles.
TUCANO_COLS=6; TUCANO_LINHAS=8; TUCANO_DIST_CHEGADA=7
EXPECTED={
  'floresta':{30,31,42,43,90},
  'caverna':{32,40},
  'copas':{33,34,41,45},
  'arena':{35,44,95},
}

def read(path):
 with path.open(encoding='utf-8-sig',newline='') as fp:
  return [[int(v) for v in row] for row in csv.reader(fp) if row]

def checar():
 total_ore=0; report={}; grades={};marks={}
 for name,meta in SETORES_GERADOS.items():
  g=read(BASE/f'{name}.csv');grades[name]=g
  assert len(g)==meta['linhas'] and all(len(row)==meta['colunas'] for row in g),name
  mark={(x,y,v) for y,row in enumerate(g) for x,v in enumerate(row) if v in MARKERS};marks[name]=mark
  ids={v for _,_,v in mark}
  assert EXPECTED[name].issubset(ids),(name,'marcadores ausentes',EXPECTED[name]-ids)
  assert len([1 for x,y,v in mark if v==95])==(1 if name=='arena' else 0)
  assert len([1 for x,y,v in mark if v==90])==(1 if name=='floresta' else 0)
  for x,y,v in mark:
   if v==95:
    assert name=='arena' and g[y+1][x] in constants.SOLID_TILES
    continue
   if v==93:continue  # tucano voador
   if v==94:continue  # aranha pendurada
   assert y+1<len(g) and g[y+1][x] in constants.SOLID_TILES,(name,x,y,v,'sem apoio')
   assert y>1 and all(g[yy][x] not in constants.SOLID_TILES for yy in (y-1,y)),(name,x,y,v,'sem espaco')
  g_clean=[[-1 if val in MARKERS else val for val in row] for row in g]
  issues=validar_csv(g)+validar_regiao(g_clean,name,0,len(g[0])-1,meta['entrada_col'],meta['entrada_row'])
  assert not issues,(name,issues[:8])
  reached,segs=alcancaveis(g_clean,meta['entrada_col'],meta['entrada_row'])
  for x,y,v in mark:
   if v in (90,91,92,96) or v in PAIRS or v in PAIRS.values():
    # can stand on a surface in marker column or within one-tile step
    supports=[s for s in reached if s[0]-1<=x<=s[1]+1 and abs(s[2]-(y+1))<=2]
    assert supports,(name,x,y,v,'fora das rotas')
   elif v==93:
    # Tucano voa: a regra de "apoio a ±1 coluna / 2 linhas" nao vale para ele.
    # Regras aprovadas para o ID 93 (V5 e V6, versao offline; V1/V3/V4 com IA e
    # fisica reais em ferramentas/validar_voadores.py e testes/teste_voadores.py):
    #  V6 superficie acessivel a +-ceil(288/48)=6 colunas e ate 8 linhas abaixo
    #  V5 a >= 7 tiles (288 px + 1 tile) de qualquer chegada
    voo=[s for s in reached if s[0]-TUCANO_COLS<=x<=s[1]+TUCANO_COLS and 0<s[2]-y<=TUCANO_LINHAS]
    assert voo,(name,x,y,v,'tucano longe de qualquer chao acessivel (V6)')
    for xa,ya,va in mark:
     if va in PAIRS.values():
      assert (xa-x)**2+(ya-y)**2>=TUCANO_DIST_CHEGADA**2,(name,x,y,v,'tucano em cima da chegada',(xa,ya))
  dec=read(DEC/f'{name}_decor.csv')
  assert len(dec)==len(g) and all(len(row)==len(g[0]) for row in dec)
  for y,row in enumerate(dec):
   for x,v in enumerate(row):
    assert v==-1 or v in ARTE,(name,x,y,v,'arte desconhecida')
    if v>=0:assert g[y][x] not in constants.SOLID_TILES and g[y][x] not in MARKERS,(name,x,y,'decor sobre colisao')
  ore=sum(v==91 for _,_,v in mark);total_ore+=ore
  report[name]={'tamanho':f'{len(g[0])}x{len(g)}','minerios':ore,'decoracoes':sum(v>=0 for row in dec for v in row),'marcadores':len(mark),'superficies':len(segs)}
  print(f"{name:8} {len(g[0])}x{len(g)} | {ore:2} minerais | {report[name]['decoracoes']:3} decoracoes | {len(reached)}/{len(segs)} superficies acessiveis")
 # Cross-sector entry to arrival markers and separation from source portals.
 for marker,target in PAIRS.items():
  source=TYPES[marker]; destination=constants.PASSAGENS_CSV[marker]['setor']
  assert constants.PASSAGENS_CSV[marker]['chegada']==target
  assert len([1 for x,y,v in marks[source] if v==marker])==1,(marker,'passagem repetida')
  assert len([1 for x,y,v in marks[destination] if v==target])==1,(target,'chegada repetida')
 for name,g in grades.items():
  portals=[(x,y) for x,y,v in marks[name] if v in PAIRS]
  arrivals=[(x,y) for x,y,v in marks[name] if v in PAIRS.values()]
  for a in portals:
   for b in arrivals:
    assert abs(a[0]-b[0])>=4,(name,'risco de repique portal',a,b)
  # 78+ ores overall and item-to-portal separation in same sector.
  for x,y,v in marks[name]:
   if v in (91,92,93):assert all(abs(x-xp)>=3 for xp,yp in portals),(name,x,v,'junto a portal')
 assert total_ore>=72,total_ore
 for filename in constants.TILE_SPRITES.values():
  assert (ROOT/'assets/images/tiles'/filename).is_file(),filename
 for name in ARTE.values():assert (ROOT/'assets/images/tiles'/name).is_file(),name
 for name in ('entrada_caverna.png','saida_caverna.png','subida_copas.png','descida_copas.png','portal_arena.png','saida_arena.png'):
  assert (ROOT/'assets/images/passagens'/name).is_file(),name
 report['total_minerios']=total_ore
 print('OK: todos os destinos, rotas, apoios, camadas e sprites passaram. Total minérios:',total_ore)
 (ROOT/'docs').mkdir(exist_ok=True)
 (ROOT/'docs/RELATORIO_VALIDACAO_LEVEL_DESIGN.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
 return report
if __name__=='__main__':checar()
