"""FLORESTA v0.9 — 404 x 44. Setor inicial (fase 1): "a floresta viva".

Percurso (colunas) e o que cada trecho oferece:
    0-37    Clareira       relevo suave, placa, 1º pulo numa passarela baixa (minério)
   38-76    Colina         árvore no topo; passarela + galho alto no tronco (minério de desvio)
   77-96    Ravina         vale de 4 degraus com a boca da caverna (30) emoldurada
   97-127   Clareira afundada  bacia com minério no fundo; um tronco caído cruza
                           por cima (atalho que pula o minério, escolha do jogador)
  128-160   Planície       patamar da árvore, 1ª cobra, chegada da caverna (42)
  161-216   Árvore Guardiã colina monumental: face oeste em terraços, platô com a
                           árvore e cobra, passarela alta a leste e uma GRUTA
                           escondida dentro da colina, com porta no paredão leste
  217-300   Baixada        lago raso, campo do tucano, tronco caído, toca entre raízes
  301-373   Árvore-Mãe     vala com ponte, platô com o cipó das copas (31) e uma
                           escalada pela copa da árvore até o cume (minério)

Minérios: 25, cada um num ponto de descoberta (plataforma, fundo de vale,
gruta, copa). Regra seguida: nenhum minério de chão sob um minério de
plataforma (a queda encurtaria o intervalo entre perguntas) e trechos de
caminhada sem interação entre eles. Medido por ferramentas/auditar_ritmo_minerios.py.
"""
from kit import Grade, Compositor, perfil, checar_perfil, ruido, acaso, VAZIO

L, C = 44, 404

GRAMA, GRAMA_FLOR, GRAMA_RAIZ = 1, 12, 13
TERRA, TERRA_FUNDA, TERRA_PEDRA = 2, 20, 22
PONTE, PASSARELA, ESCORA = 60, 64, 67
SPAWN, MINERIO, COBRA, TUCANO = 90, 91, 92, 93
P_CAVERNA, P_COPAS, CH_CAVERNA, CH_COPAS = 30, 31, 42, 43

FLOR, SAMAMB, COGU, ARBUSTO, PLACA, AGUA, FLOR_ROXA = 100, 101, 110, 112, 114, 115, 117
LIANA, FUNGO, RAMOS, RAIZ_ARCO, PEDRA, FOLHAGEM = 118, 119, 120, 121, 122, 123

PERFIL = [
    (0, 30), (23, 29), (27, 30),                                   # clareira (spawn plano; morrinho 23-26)
    (38, 29), (40, 28), (45, 27), (49, 26), (52, 25),              # colina (v0.9: assimétrica,
    (61, 27), (63, 28), (69, 29), (72, 30),                        #  leste mais íngreme)
    (78, 31), (81, 32), (84, 33), (91, 32), (93, 31), (95, 30),    # ravina
    (101, 31), (103, 32), (105, 33), (117, 32), (119, 31),         # clareira afundada
    (121, 30), (124, 29), (133, 28), (144, 29),                    # planície
    (161, 28), (165, 26), (168, 24), (171, 23),                    # Guardiã, face oeste (v0.9: terraços variados)
    (179, 21),                                                     # platô
    (196, 22),                                                     # ombro leste (teto do túnel)
    (200, 26), (207, 27), (210, 28), (213, 29), (216, 30),         # paredão da gruta
    (222, 31), (228, 32), (240, 31), (246, 30),                    # lago
    (250, 29), (254, 28), (258, 27), (265, 28), (269, 29),         # outeiro do mirante
    (273, 30),
    (302, 31), (308, 30), (311, 29),                               # toca
    (324, 28), (326, 27), (332, 26), (338, 25),
    (342, 26), (343, 27), (344, 28), (351, 27), (352, 26),         # vala
    (353, 25), (356, 24), (376, 23), (389, 24),                    # platô; v0.9: pedestal sob a Árvore-Mãe
]
LAGO = (228, 239)
# Gruta dentro da colina da Guardiã: (c0, c1, linha_topo, linha_base) de ar
GRUTA = [(187, 193, 24, 25),        # salão sob a árvore (v0.9: teto 1 tile mais baixo, janela menor)
         (194, 199, 24, 25)]        # túnel curto até a porta no paredão (col 200)

PLATAFORMAS = [  # (c0, c1, linha, tile, colunas de escora até o chão)
    (28, 33, 28, PASSARELA, (28, 33)),          # 1º pulo
    (50, 55, 23, PASSARELA, (50,)),             # passarela da colina
    (57, 61, 21, PASSARELA, ()),                # galho alto, no tronco da árvore
    (102, 118, 29, PASSARELA, (110,)),          # tronco caído sobre a clareira (encostas livres)
    (196, 204, 19, PASSARELA, (196, 199)),      # rota alta da Guardiã (ponta em balanço)
    (201, 203, 24, PASSARELA, (203,)),          # degrau de raiz ao lado da porta da gruta
    (259, 263, 25, PASSARELA, ()),              # mirante no topo do outeiro
    (292, 300, 28, PASSARELA, (292, 300)),      # tronco caído na baixada
    (344, 350, 25, PONTE, ()),                  # ponte sobre a vala
    (390, 394, 22, PASSARELA, (390, 394)),      # escalada da Árvore-Mãe
    (396, 400, 20, PASSARELA, (400,)),
    (390, 394, 18, PASSARELA, ()),
    (384, 388, 16, PASSARELA, ()),
    (378, 382, 14, PASSARELA, ()),              # cume, dentro da copa
]
ESCORAS_ENTRE = [(390, 19, 21)]                 # liga a passarela 18 à de baixo

# O tronco de arvore_antiga fica na coluna do JSON (medido na arte).
ARVORES = [("arvore_antiga.png", 19), ("arvore_antiga_alt.png", 56),
           ("arvore_antiga.png", 97), ("arvore_antiga_alt.png", 139),
           ("arvore_antiga_alt.png", 175), ("arvore_antiga.png", 225),
           ("arvore_antiga_alt.png", 282), ("arvore_antiga.png", 315),
           ("arvore_antiga_alt.png", 328), ("arvore_antiga.png", 359)]

MINERIOS_CHAO = [15, 46, 70, 82, 94, 108, 119, 130, 146, 157, 170, 183, 214, 227,
                 240, 250, 274, 286, 312, 326, 339, 349, 363]   # v0.9: 5 ajustes de ritmo
MINERIOS_PLAT = [(31, 28), (59, 21), (203, 19), (298, 28), (261, 25), (391, 22), (379, 14)]
MINERIOS_GRUTA = [(190, 26), (313, 34)]
# Toca sob a baixada: desce do fundo da depressão (272-277) e corre sob o chão.
TOCA = [(306, 306, 31, 31), (307, 307, 31, 32), (308, 315, 32, 33)]


def construir():
    alt = perfil(PERFIL, C)
    checar_perfil(alt, 4, "floresta")   # 4 só no paredão da gruta (col 200): o degrau de raiz 201-203 liga
    t = Grade(L, C)
    troncos = [col for _, col in ARVORES] + [190, 383]   # tronco medido na arte: na própria coluna

    for c in range(C):
        topo = alt[c]
        perto_tronco = any(abs(c - tc) <= 3 for tc in troncos)
        no_lago = LAGO[0] <= c <= LAGO[1]
        for r in range(topo, L):
            prof = r - topo
            if prof == 0:
                if no_lago:
                    v = TERRA
                elif perto_tronco:
                    v = GRAMA_RAIZ
                elif ruido(c, 0, 11, 5.0) > 0.68:
                    v = GRAMA_FLOR
                else:
                    v = GRAMA
            elif prof <= 2:
                v = TERRA
            else:
                v = TERRA_FUNDA if ruido(c, r, 3, 6.0) + prof * 0.035 > 0.82 else TERRA
                if prof >= 3 and ruido(c, r, 7, 2.6) > 0.80:
                    v = TERRA_PEDRA
            t.set(c, r, v)

    for c0, c1, r0, r1 in GRUTA + TOCA:
        t.retangulo(c0, c1, r0, r1, VAZIO)
    # piso da gruta com raízes (grama com raiz não cabe: não há céu); terra escura
    for c in range(187, 200):
        t.set(c, 26, TERRA_FUNDA if acaso(c, 26, 3) > 0.5 else TERRA)

    for c0, c1, r, tile, escoras in PLATAFORMAS:
        for c in range(c0, c1 + 1):
            assert t.get(c, r) == VAZIO, ("plataforma sobre terreno", c, r)
            t.set(c, r, tile)
        for c in escoras:
            for rr in range(r + 1, alt[c]):
                t.set(c, rr, ESCORA)
    for c, r0, r1 in ESCORAS_ENTRE:
        for rr in range(r0, r1 + 1):
            t.set(c, rr, ESCORA)

    def chao(c, v):
        t.set(c, alt[c] - 1, v)

    chao(8, SPAWN)
    chao(87, P_CAVERNA)
    chao(150, CH_CAVERNA)
    chao(367, CH_COPAS)
    chao(374, P_COPAS)
    for c in (136, 189, 317):
        chao(c, COBRA)
    t.set(288, 25, TUCANO)
    for c in MINERIOS_CHAO:
        chao(c, MINERIO)
    for c, r in MINERIOS_PLAT + MINERIOS_GRUTA:
        assert t.get(c, r) != VAZIO, ("minerio sem apoio", c, r)
        t.set(c, r - 1, MINERIO)

    return t, decorar(t, alt, troncos), estruturas_floresta(alt)


def decorar(t, alt, troncos):
    from src.nucleo import constants
    comp = Compositor(t, constants.SOLID_TILES, constants.TILES_MARCADORES | {ESCORA})

    # ── zonas limpas ─────────────────────────────────────────────────────────
    comp.reservar(85, 89, 30, 32)          # vão da boca da caverna
    comp.reservar(372, 376, 21, 23)        # cipó das copas
    comp.reservar(365, 369, 22, 23)        # chegada 43
    comp.reservar(148, 152, 27, 28)        # chegada 42
    comp.reservar(6, 10, 27, 29)           # spawn
    comp.reservar(198, 201, 24, 25)        # porta da gruta: leitura da abertura
    for r in range(L):
        for c in range(C):
            if t.g[r][c] == MINERIO:
                comp.reservar(c - 1, c + 1, r, r)

    # ── peças narrativas ─────────────────────────────────────────────────────
    comp.grupo_chao(12, alt[12] - 1, [PLACA])
    comp.grupo_chao(76, alt[76] - 1, [PLACA])                     # aviso da ravina
    comp.grupo_chao(205, 25, [PLACA])                             # "há algo no paredão"
    comp.grupo_chao(370, alt[370] - 1, [PLACA])
    comp.grupo_chao(84, 32, [PEDRA, FUNGO])                       # boca da caverna
    comp.grupo_chao(89, 32, [FUNGO, PEDRA])
    comp.grupo_chao(81, 31, [SAMAMB, COGU])
    comp.grupo_chao(91, 31, [COGU])
    comp.grupo_chao(93, 30, [PEDRA])
    # lago: lâmina d'água inteira, juncos nas margens
    for c in range(LAGO[0] + 1, LAGO[1]):
        comp.por(c, 31, AGUA)
    comp.grupo_chao(LAGO[0], 31, [SAMAMB])
    comp.grupo_chao(LAGO[1], 31, [SAMAMB])
    # clareira afundada: fundo úmido com samambaias e cogumelos, nada sob o tronco no meio
    comp.grupo_chao(105, 32, [SAMAMB, COGU])
    comp.grupo_chao(113, 32, [FUNGO, VAZIO, SAMAMB])
    # toca entre raízes na baixada
    comp.grupo_chao(302, 30, [RAIZ_ARCO, COGU])
    comp.grupo_chao(304, 30, [FUNGO])
    for c, v in ((309, FUNGO), (311, RAIZ_ARCO), (315, COGU)):
        comp.por(c, 33, v)
    for c in (310, 315):
        comp.pendurar(c, 32, [LIANA])

    # Gruta da Guardiã: raízes penduradas do teto, fungos luminosos no chão.
    for c in (188, 192, 195):
        comp.pendurar(c, 24, [LIANA] if c != 192 else [RAMOS])
    for c, v in ((187, FUNGO), (188, RAIZ_ARCO), (192, COGU), (193, FUNGO), (196, RAIZ_ARCO)):
        comp.por(c, 25, v)

    # Pé das árvores: raízes rasteiras, sombra.
    for i, tc in enumerate(troncos):
        r = alt[tc] - 1
        if tc in (190, 383):
            comp.grupo_chao(tc - 6, r, [SAMAMB, RAIZ_ARCO])
            comp.grupo_chao(tc + 4, r, [RAIZ_ARCO, COGU, FUNGO])
            continue
        comp.grupo_chao(tc - 2, r, [RAIZ_ARCO])
        comp.grupo_chao(tc + 2, r, [RAIZ_ARCO])
        if i % 3 == 0:
            comp.grupo_chao(tc + 3, r, [COGU])
        elif i % 3 == 1:
            comp.grupo_chao(tc - 4, r, [SAMAMB, COGU])
        else:
            comp.grupo_chao(tc + 3, r, [SAMAMB])

    # Pendurados sob passarelas: lianas em comprimentos variados.
    for i, (c0, c1, r, tile, escoras) in enumerate(PLATAFORMAS):
        if r <= 18 or c1 - c0 < 4:
            continue
        a = c0 + 1 + int(acaso(c0, r, 5) * (c1 - c0 - 2))
        if a in escoras:
            a += 1
        comp.pendurar(a, r + 1, [LIANA] * (1 + i % 2))
        b = a + 3
        if b < c1 and b not in escoras:
            comp.pendurar(b, r + 1, [RAMOS])

    # Outeiro do mirante: rochas agrupadas nas encostas, flores no topo.
    comp.grupo_chao(250, alt[250] - 1, [PEDRA, SAMAMB])
    comp.grupo_chao(255, alt[255] - 1, [PEDRA, PEDRA])
    comp.grupo_chao(265, alt[265] - 1, [PEDRA])
    comp.grupo_chao(258, 26, [FLOR_ROXA])
    comp.grupo_chao(264, 26, [FLOR, PEDRA])
    # Barrancos: pedras onde o terreno quebra.
    for c in (343, 351, 101, 119):
        comp.grupo_chao(c, alt[c] - 1, [PEDRA])

    # Vegetação por zona: densidades diferentes, manchas com vazios entre elas.
    ZONAS = [  # (c0, c1, limiar, vinhetas) — limiar menor = mais denso
        (0, 37, 0.15, "clareira"), (38, 76, 0.20, "colina"),
        (95, 160, 0.16, "planicie"), (161, 216, 0.22, "guardia"),
        (217, 330, 0.11, "baixada"), (331, 403, 0.13, "final"),
    ]
    VINHETAS = {
        "clareira": [[FLOR], [FLOR, VAZIO, FLOR_ROXA], [SAMAMB, FLOR], [ARBUSTO], [FLOR_ROXA, FLOR, FLOR]],
        "colina": [[SAMAMB], [ARBUSTO, SAMAMB], [FLOR], [ARBUSTO], [PEDRA, SAMAMB]],
        "planicie": [[ARBUSTO, ARBUSTO], [FLOR], [SAMAMB, FLOR, VAZIO, FLOR_ROXA], [FOLHAGEM, ARBUSTO], [SAMAMB]],
        "guardia": [[SAMAMB], [COGU], [ARBUSTO], [PEDRA, SAMAMB], [FLOR_ROXA]],
        "baixada": [[FOLHAGEM, ARBUSTO], [SAMAMB, SAMAMB], [FLOR_ROXA], [ARBUSTO, VAZIO, FLOR],
                    [FOLHAGEM, FOLHAGEM, ARBUSTO], [SAMAMB, COGU], [FLOR, FLOR_ROXA, FLOR]],
        "final": [[FLOR_ROXA], [SAMAMB, FLOR_ROXA], [ARBUSTO, FOLHAGEM], [FUNGO], [FLOR, VAZIO, SAMAMB],
                  [FLOR_ROXA, FLOR, FLOR_ROXA]],
    }
    for z0, z1, limiar, nome in ZONAS:
        c = z0
        while c <= z1:
            r = alt[c] - 1
            if ruido(c, 0, 21, 9.0) * 0.6 > limiar:
                opcoes = VINHETAS[nome]
                vinheta = opcoes[int(acaso(c, r, 31) * len(opcoes)) % len(opcoes)]
                fim = c + len(vinheta) - 1
                if fim <= z1 and all(alt[x] == alt[c] for x in range(c, fim + 1)):
                    if comp.grupo_chao(c, r, vinheta):
                        c = fim + 2 + int(acaso(c, 7, 41) * 4)
                        continue
            c += 1
    return comp.d


def estruturas_floresta(alt):
    out = []
    for img, col in ARVORES:
        tc = col
        assert len({alt[x] for x in range(tc - 2, tc + 3)}) == 1, ("arvore em desnivel", img, col)
        out.append({"imagem": img, "coluna": col, "base": alt[tc] + 1})
    out.append({"imagem": "isa_v06_arvore_guardia_visivel.png", "coluna": 190, "base": alt[190] + 1})
    out.append({"imagem": "isa_v06_arvore_mae_visivel.png", "coluna": 383, "base": alt[383]})
    return out
