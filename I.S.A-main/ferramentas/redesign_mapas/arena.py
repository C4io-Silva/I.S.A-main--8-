"""ARENA — 41 x 44. Clareira-santuário do Gorila.

A geometria da luta NÃO muda: piso na linha 24, plataformas 63 nas mesmas
células (validadas por gerar_mundo.validar_area_boss e teste_boss), marcadores
nas mesmas células. Muda:
  * o preenchimento do piso: as faixas diagonais de templo (tTTTT repetido a
    cada 5 colunas) viram blocos com variação orgânica;
  * a decoração: as colunas de runas quebradas e soltas no ar (113 em pilhas
    com buracos) viram dois obeliscos apoiados no chão; estandartes e
    lanternas passam a pendurar das plataformas; tochas no chão e sobre as
    plataformas altas. O centro da luta fica limpo.
"""
import os
from kit import Grade, Compositor, ler_csv, ruido, acaso, VAZIO

TEMPLO, TEMPLO_VAR, LAJE = 27, 28, 29
TOCHA, BANDEIRA, LANTERNA, RUNAS = 104, 108, 109, 113


def construir():
    # Geometria lida do próprio arena.csv do jogo (não é alterada aqui; só o
    # preenchimento do piso é refeito), então rodar de novo dá o mesmo resultado.
    base = ler_csv(os.path.join(os.environ["ISA_JOGO"], "assets", "levels", "setores", "arena.csv"))
    L, C = len(base), len(base[0])
    t = Grade(L, C)
    for r in range(L):
        for c in range(C):
            v = base[r][c]
            if v in (TEMPLO, TEMPLO_VAR):
                v = TEMPLO_VAR if ruido(c, r, 81, 3.2) > 0.64 else TEMPLO
            t.g[r][c] = v
    return t, decorar(t), None   # estruturas da arena mantidas


def decorar(t):
    from src.nucleo import constants
    comp = Compositor(t, constants.SOLID_TILES, constants.TILES_MARCADORES)
    comp.reservar(0, 2, 22, 23)            # saída
    comp.reservar(4, 6, 23, 23)            # chegada
    comp.reservar(16, 32, 12, 23)          # palco da luta: limpo

    # v0.8 — moldura da luta: dois obeliscos de runas iguais marcam as bordas
    # do palco (cols 14 e 34), cada um com uma tocha do lado de fora. O centro
    # (16-32) fica limpo: o jogador lê o Gorila e os projéteis sem ruído.
    for c in (14, 34):
        for i in range(3):
            comp.por(c, 23 - i, RUNAS)
    # v0.9: braseiro no topo de cada obelisco (as tochas de chão ficavam na
    # frente dos estandartes de pedra); tochas nas pontas das plataformas altas.
    for c, r in ((14, 20), (34, 20), (3, 20), (38, 20)):
        comp.por(c, r, TOCHA)
    # Estandartes e lanternas pendurados das plataformas altas (linha 21).
    comp.pendurar(4, 22, [BANDEIRA])
    comp.pendurar(37, 22, [BANDEIRA])
    comp.pendurar(7, 22, [LANTERNA])
    comp.pendurar(34, 22, [LANTERNA])
    return comp.d
