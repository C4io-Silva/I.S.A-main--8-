"""Confere novos CSVs/sprites sem depender de pygame. Uso: python ferramentas/validar_terreno.py"""
from pathlib import Path
import sys, json, hashlib, csv, struct
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from src.nucleo import constants

def checar():
    base=json.loads((ROOT/'docs'/'TERRENO_REFERENCIA.json').read_text(encoding='utf-8'))
    n=0
    for name, ref in base.items():
        csv_path=ROOT/'assets'/'levels'/'setores'/f'{name}.csv'
        with csv_path.open(encoding='utf-8-sig',newline='') as f:
            text=f.read()
        d=';' if text.splitlines()[0].count(';')>=text.splitlines()[0].count(',') else ','
        grade=[[int(v) for v in row if v.strip()] for row in csv.reader(text.splitlines(),delimiter=d) if row]
        assert len(grade)==ref['altura'] and all(len(row)==ref['largura'] for row in grade),name+': dimensoes diferentes'
        marcas=sorted([x,y,v] for y,row in enumerate(grade) for x,v in enumerate(row) if v in constants.TILES_MARCADORES)
        assert marcas==ref['marcadores'],name+': marcador mudou'
        bits=bytes(int(v in constants.SOLID_TILES) for row in grade for v in row)
        assert hashlib.sha256(bits).hexdigest()==ref['colisoes_sha256'],name+': geometria do terreno mudou'
        conhecidos=set(constants.TILE_SPRITES)|set(constants.TILES_MARCADORES)|{-1}
        invalidos={v for row in grade for v in row if v not in conhecidos}
        assert not invalidos,name+f': IDs desconhecidos {invalidos}'
        decor_path=ROOT/'assets'/'levels'/'decoracoes'/f'{name}_decor.csv'
        with decor_path.open(encoding='utf-8-sig', newline='') as df:
            decor=sum(int(v)>=100 for row in csv.reader(df) for v in row)
        print(f'{name}: OK {ref["largura"]}x{ref["altura"]}, {decor} decoracoes visuais, marcadores e colisoes atuais validados')
        n+=1
    for tile_id,filename in constants.TILE_SPRITES.items():
        path=ROOT/'assets'/'images'/'tiles'/filename
        assert path.exists(),f'Sprite ausente: {tile_id} {filename}'
        assert path.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n',f'PNG invalido: {filename}'
        w,h=struct.unpack('>II',path.read_bytes()[16:24]);assert w>0 and h>0
    print(f'OK: {n} mapas; {len(constants.TILE_SPRITES)} sprites registrados e presentes')

if __name__=='__main__':
    checar()
