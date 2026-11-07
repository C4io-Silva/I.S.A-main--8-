"""Audita o redesign de fase (Python padrão, não precisa de pygame)."""
from pathlib import Path
import sys,csv,json,hashlib
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from src.nucleo import constants
from src.mundo.validacao_mapa import validar_csv, validar_regiao
from src.mundo.nivel_dados import SETORES_GERADOS

def main():
    ref=json.loads((ROOT/'docs'/'TERRENO_REFERENCIA.json').read_text(encoding='utf-8'))
    for nome,spec in ref.items():
        path=ROOT/'assets'/'levels'/'setores'/f'{nome}.csv'
        texto=path.read_text(encoding='utf-8-sig')
        sep=';' if texto.splitlines()[0].count(';')>texto.splitlines()[0].count(',') else ','
        grade=[[int(n) for n in r] for r in csv.reader(texto.splitlines(),delimiter=sep) if r]
        assert (len(grade),len(grade[0]))==(spec['altura'],spec['largura']),nome+' dimensoes'
        marcas=sorted([x,y,v] for y,row in enumerate(grade) for x,v in enumerate(row) if v in constants.TILES_MARCADORES)
        assert marcas==spec['marcadores'],nome+' marcadores'
        bits=bytes(int(v in constants.SOLID_TILES) for row in grade for v in row)
        assert hashlib.sha256(bits).hexdigest()==spec['colisoes_sha256'],nome+' solidos'
        g=[[-1 if v in constants.TILES_MARCADORES else v for v in row] for row in grade]
        meta=SETORES_GERADOS[nome]
        erros=validar_csv(grade)+validar_regiao(g,nome,0,len(g[0])-1,meta['entrada_col'],meta['entrada_row'])
        assert not erros,(nome,erros[:5])
        print(f'{nome}: OK — {len(grade[0])}x{len(grade)}, {sum(v==91 for row in grade for v in row)} minérios, rotas e marcadores válidos')
    print('REDESIGN ESTRUTURAL APROVADO: 4 setores')
if __name__=='__main__':main()
