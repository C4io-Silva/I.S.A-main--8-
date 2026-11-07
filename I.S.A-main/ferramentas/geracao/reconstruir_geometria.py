"""Intervencao conservadora nos mapas I.S.A. (versao-base preservada).
Executar uma vez a partir do checkout da base; não usar o gerador historico.
Mantem todos os marcadores, reposicionando apenas terreno e apoios opcionais.
"""
import csv, json, hashlib, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from src.nucleo import constants
B=ROOT/'assets/levels/setores';D=ROOT/'assets/levels/decoracoes'
SOL=constants.SOLID_TILES; MARK=constants.TILES_MARCADORES

def read(n):
 with (B/f'{n}.csv').open(encoding='utf-8-sig',newline='') as fp:
  return [[int(v) for v in row] for row in csv.reader(fp)]
def save(n,g):
 with (B/f'{n}.csv').open('w',encoding='utf-8',newline='') as fp:
  csv.writer(fp).writerows(g)
def surface(g,x):
 return min((y for y in range(1,len(g)) if g[y][x] in SOL and g[y-1][x] not in SOL),default=32)
def near_marker(g,x,within=3):
 return any(g[y][xx] in MARK for xx in range(max(0,x-within),min(len(g[0]),x+within+1)) for y in range(len(g)))

# Copas: conserva a sequencia altimetrica e os apoios dos 18 minerios, mas
# substitui massas de terra retangulares por passarelas de galhos/troncos.
g=read('copas');w=len(g[0]); original=[row[:] for row in g]
# Cada superficie existente e mantida, incluindo degraus secundarios que
# sustentam o percurso; a massa macica abaixo e reduzida a galhos suspensos.
for y in range(44):
 for x in range(w):
  if g[y][x] in SOL:g[y][x]=-1
# Primeiro preserve todas as plataformas ORIGINAIS; nao dependa so do topo mais alto.
for x in range(w):
 for top in range(1,44):
  if original[top][x] not in SOL or original[top-1][x] in SOL:continue
  g[top][x]=14 if (x//7)%3==0 else 62
  for y in (top+1,top+2):
   if y<44 and original[y][x] in SOL:g[y][x]=36 if (x+y)%5 else 37
# Troncos reais conectam as passarelas a arvores gigantes e ao solo;
# somente cinco zonas retém pilares estruturais, não torres por todo lado.
trunks=[(8,12),(30,34),(51,54),(81,85),(115,120)]
for a,b in trunks:
 for x in range(a,b+1):
  t=surface(original,x)
  for y in range(t+1,44):
   if original[y][x] in SOL and g[y][x]==-1:g[y][x]=36 if (x+y)%5 else 37
# Restaurar marcadores sem mover destinos ou minérios, e seus apoios locais.
for y,row in enumerate(original):
 for x,v in enumerate(row):
  if v in MARK:g[y][x]=v
for y,row in enumerate(original):
 for x,v in enumerate(row):
  if v in MARK and v not in (93,94) and y+1<44 and g[y+1][x] not in SOL:
   g[y+1][x]=62
save('copas',g)

# Floresta: reforca caminhos de raizes e pequenos marcos, sem criar degraus
# desconectados, preservar zonas de spawn e portais.
g=read('floresta');original=[row[:] for row in g]
for center in (39,113,211,261,300):
 for x in range(center-3,center+4):
  if near_marker(original,x,3):continue
  t=surface(g,x)
  if 15<t<36 and g[t-1][x]==-1:
   g[t-1][x]=12  # colina curta enraizada: o solo original sustenta o topo
# Plataformas opcionais adicionais só serão incluídas depois de um teste de
# colisão/salto mais rigoroso; não introduzir bolsões desconectados.
save('floresta',g)

# Caverna: diferencia rocha em veios horizontais e antigos apoios de mineracao,
# deixando a geologia e a silhueta das galerias intactas nas areas com marcadores.
g=read('caverna');original=[row[:] for row in g]
for y,row in enumerate(g):
 for x,v in enumerate(row):
  if v==24 and y>21:
   if (x//11+y//5)%9==0:g[y][x]=25
   elif (x*13+y*7)%157==0 and not near_marker(original,x,1):g[y][x]=26
# reforcos de galerias historicas, alicerces ancorados em solo existente
for a,b in ((52,57),(125,130),(205,210)):
 t=min(surface(original,x) for x in range(a,b+1))-2
 if any(near_marker(original,x,2) for x in range(a,b+1)):continue
 for x in range(a,b+1):
  if g[t][x]==-1:g[t][x]=61
 for x in (a,b):
  for yy in (t+1,t+2):
   if g[yy][x]==-1:g[yy][x]=61
save('caverna',g)

# Arena: piso da luta intocado, mantem o espaco das bananas e choque do Gorila.
# A nova arquitetura monumental e desenhada exclusivamente no fundo.

# Referencia do estado atual. Nao e prova de jogabilidade, apenas detector
# de alteracoes acidentais em relacao A ESTA REVISAO APROVAVEL.
ref={}
for n in ('floresta','caverna','copas','arena'):
 g=read(n)
 ms=sorted([x,y,v] for y,row in enumerate(g) for x,v in enumerate(row) if v in MARK)
 bits=bytes(int(v in SOL) for row in g for v in row)
 ref[n]={'altura':len(g),'largura':len(g[0]),'marcadores':ms,'colisoes_sha256':hashlib.sha256(bits).hexdigest()}
(ROOT/'docs/TERRENO_REFERENCIA.json').write_text(json.dumps(ref,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Geometria alterada: floresta, caverna e copas. Referencia atualizada.')
