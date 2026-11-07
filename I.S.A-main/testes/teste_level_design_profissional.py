"""Auditoria offline do redesign: rotas, portais, apoios, CSVs e arte.

Pode ser executada sem pygame, também no Windows.
"""
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ferramentas.auditoria.auditar_level_design import checar

if __name__=='__main__':
    resultado=checar()
    assert resultado['total_minerios']>=72
    print('TESTE LEVEL DESIGN PROFISSIONAL APROVADO')
