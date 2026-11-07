"""
testar_correcoes_mapa.py — testa correções CANDIDATAS de um mapa em memória.

O CSV NÃO é alterado: as mudanças são aplicadas só na leitura, e o validador de
física real roda em cima delas (ida, volta, mão única, minérios, inimigos).
Serve para sugerir à direção criativa a menor mudança que resolve um problema.

uso (na raiz do projeto):
    python ferramentas/testar_correcoes_mapa.py caverna "NOME=linha,coluna,id;linha,coluna,id" ...
exemplo:
    python ferramentas/testar_correcoes_mapa.py caverna "abrir_degrau=31,101,-1"
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import ferramentas.fisica.fisica_nivel as F
import ferramentas.validacao.validar_fisica_real as V
import os
SETOR = "caverna"


def instalar(mods):
    from src.nucleo import constants
    from src.nucleo.utils import carregar_nivel_csv, extrair_marcadores
    def ler_mod(nome):
        g = carregar_nivel_csv(os.path.join(constants.PASTA_SETORES, constants.SETORES[nome]["arquivo"]))
        if nome == SETOR:
            for l, c, v in mods: g[l][c] = v
        return g, extrair_marcadores(g)
    F.ler_setor = ler_mod
if __name__ == "__main__":
    pg = F.iniciar_pygame()
    from src.nucleo import constants
    SETOR = sys.argv[1]
    for arg in sys.argv[2:]:
        nome, _, txt = arg.partition("=")
        mods = [tuple(int(x) for x in m.split(",")) for m in txt.split(";") if m]
        instalar(mods)
        d = V.montar_setor(SETOR)
        rel, ctx = V.analisar_setor(SETOR, 2, 1, True, d, exigir_volta=True)
        i = rel.info
        print(f"## {nome} {mods}")
        print(f"   {len(rel.erros)} erro(s), {len(rel.avisos)} aviso(s); superficies {i['superficies_pisadas']}/{i['superficies']}; "
              f"so com pulo duplo: {i.get('minerios_so_com_pulo_duplo')} minerio(s)")
        for e in rel.erros[:8]: print("     ERRO ", e[:170])
        for a in rel.avisos[:8]: print("     AVISO", a[:170])
