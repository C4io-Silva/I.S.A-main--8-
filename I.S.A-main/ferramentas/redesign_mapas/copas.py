"""COPAS v0.9 — 171 x 44 (fase 3): verticalidade e natureza.

As árvores da arte (estruturas_cenario.json) ficam onde estão e ditam a
geometria. Cada plataforma se apoia num elemento medido na arte:

  árvores de fundo (col 10/33/53/83/116): tronco de 3 colunas; galho esquerdo
      nas linhas 20-21, direito nas 25-27, esquerdo baixo nas 29-31
  Ancestral (col 37): copa nas linhas 21-28 (cols 28-46), tronco nas 29-36
  Espiral (col 89): copa nas linhas 11-18 (cols 80-98), tronco nas 19-26

Percurso (ziguezague vertical, nada de tronco sólido em escada):
     0-27   deck de chegada sob o pórtico e dois galhos sobre o ramo conector
    28-45   deck baixo da Ancestral (cobra); DESVIO: sobe pela copa até o cume
            e segue pela ROTA ALTA até o galho esquerdo da árvore de fundo B3
    47-66   galho com conector -> deck do ninho (minério dentro do ninho)
    67-82   subida até o galho da B4; DESVIO: galho baixo da B4 (minério)
    85-98   deck da Espiral na bifurcação; DESVIO: cume da copa (minério)
    99-137  ÁRVORE VIGIA (nova, +40 colunas): ponte de galhos, galho esquerdo,
            deck no galho direito, subida pela copa baixa
   139-170  galho com conector -> deck final, lanternas, portal da arena
"""
from kit import Grade, Compositor, ruido, acaso, VAZIO

L, C = 44, 171
COPA, COPA_VAR, GALHO = 14, 15, 62
MINERIO, COBRA, TUCANO = 91, 92, 93
P_FLORESTA, P_ARENA, CH_COPAS, CH_ARENA = 33, 34, 41, 45
FLOR, SAMAMB, CIPO, COPA_D, LANTERNA, ARBUSTO, PLACA, FLOR_ROXA = 100, 101, 105, 107, 109, 112, 114, 117
LIANA, RAMOS, FOLHAGEM = 118, 120, 123

# (c0, c1, linha, tipo, apoio na arte)
PLATAFORMAS = [
    (0, 16, 34, "deck", "tronco de fundo col 10 + pórtico"),
    (17, 21, 32, "galho", "ramo conector A"),
    (23, 27, 30, "galho", "ramo conector A"),
    (28, 45, 29, "deck", "troncos da Ancestral e de fundo col 33"),
    (41, 45, 27, "galho", "toquinho sobre o deck"),
    (32, 38, 25, "deck", "copa da Ancestral"),
    (27, 30, 23, "galho", "copa da Ancestral (cume)"),
    (39, 44, 23, "galho", "copa da Ancestral"),
    (47, 52, 21, "galho", "galho esquerdo da árvore de fundo col 53"),
    (47, 51, 27, "galho", "ramo conector B"),
    (53, 66, 26, "deck", "tronco de fundo col 53 + ninho"),
    (67, 71, 24, "galho", "ramo conector A"),
    (68, 73, 28, "galho", "sob o ninho"),
    (75, 81, 30, "galho", "galho esquerdo baixo da árvore de fundo col 83"),
    (74, 82, 22, "galho", "galho esquerdo da árvore de fundo col 83"),
    (85, 97, 20, "deck", "bifurcação da Espiral"),
    (94, 98, 18, "galho", "toquinho sobre o deck"),
    (86, 91, 16, "deck", "copa da Espiral (cume)"),
    # Árvore Vigia (nova na v0.8, +40 colunas): ponte de galhos e subida
    (99, 110, 22, "galho", "ponte de galhos sobre o ramo conector B"),
    (112, 117, 21, "galho", "galho esquerdo da árvore de fundo col 118 (Vigia)"),
    (119, 125, 23, "deck", "galho direito da Vigia + toquinho"),
    (127, 132, 21, "galho", "ramo conector A (v0.9)"),
    (134, 137, 20, "galho", "ponta do ramo conector A (v0.9)"),
    (139, 144, 19, "galho", "ramo conector B"),
    (146, 170, 17, "deck", "tronco de fundo col 156 + portal ancestral"),
    (150, 155, 15, "galho", "toquinho sobre o deck"),
    # rota baixa (sub-bosque): sob o deck de chegada até as raízes da Ancestral
    (17, 28, 36, "galho", "ramo conector A (por baixo)"),
    (30, 43, 37, "deck", "raízes da Ancestral"),
    # desvio baixo continua do galho da B4 até as raízes da Espiral
    (84, 93, 28, "deck", "raízes da Espiral"),
]

MINERIOS = [(19, 32), (39, 29), (28, 23), (49, 21), (58, 26), (70, 24),
            (79, 30), (90, 28), (33, 37), (88, 16), (104, 22), (122, 23), (136, 20),
            (153, 15), (163, 17)]


def construir():
    t = Grade(L, C)
    for c0, c1, r, tipo, _ in PLATAFORMAS:
        for c in range(c0, c1 + 1):
            assert t.g[r][c] == VAZIO, ("sobreposicao", c, r)
            t.set(c, r, GALHO if tipo == "galho" else (COPA_VAR if ruido(c, r, 13, 3.0) > 0.62 else COPA))

    def sobre(c, r, v):
        assert t.g[r][c] in (COPA, COPA_VAR, GALHO), ("sem apoio", c, r)
        t.set(c, r - 1, v)

    sobre(5, 34, CH_COPAS)
    sobre(11, 34, P_FLORESTA)
    sobre(158, 17, CH_ARENA)
    sobre(166, 17, P_ARENA)
    sobre(36, 29, COBRA)
    sobre(64, 26, COBRA)          # v0.9: longe do minério do ninho
    t.set(78, 18, TUCANO)
    for c, r in MINERIOS:
        sobre(c, r, MINERIO)
    return t, decorar(t), estruturas()


def decorar(t):
    from src.nucleo import constants
    comp = Compositor(t, constants.SOLID_TILES, constants.TILES_MARCADORES)
    comp.reservar(4, 6, 32, 33)          # chegada 41
    comp.reservar(9, 13, 31, 33)         # descida para a floresta (sob o pórtico)
    comp.reservar(156, 160, 15, 16)      # chegada 45
    comp.reservar(164, 168, 14, 16)      # portal da arena
    comp.reservar(73, 83, 16, 20)        # faixa de voo do tucano
    for r in range(L):
        for c in range(C):
            if t.g[r][c] == MINERIO:
                comp.reservar(c - 1, c + 1, r, r)

    comp.grupo_chao(7, 33, [PLACA])

    # Lanternas sob o deck final (o caminho para a clareira do Gorila) — antes
    # dos pendurados genéricos, para terem prioridade.
    for c in (148, 153, 161, 169):
        comp.pendurar(c, 18, [LANTERNA])

    # Decks: vegetação densa, em manchas; galhos finos: só folhas nas pontas.
    VINHETAS = [[SAMAMB], [FLOR, SAMAMB], [ARBUSTO], [FOLHAGEM, ARBUSTO], [SAMAMB, VAZIO, FLOR_ROXA],
                [FLOR_ROXA, FLOR], [ARBUSTO, SAMAMB], [COPA_D, FOLHAGEM]]
    for c0, c1, r, tipo, _ in PLATAFORMAS:
        if tipo == "deck":
            c = c0
            while c <= c1:
                if ruido(c, r, 17, 3.5) > 0.38:
                    v = VINHETAS[int(acaso(c, r, 19) * len(VINHETAS)) % len(VINHETAS)]
                    if c + len(v) - 1 <= c1 and comp.grupo_chao(c, r - 1, v):
                        c += len(v) + 1 + int(acaso(c, r, 23) * 3)
                        continue
                c += 1
        else:
            # folhagem brotando na ponta do galho que encosta na copa/tronco
            ponta = c1 if acaso(c0, r, 29) > 0.5 else c0
            comp.grupo_chao(ponta, r - 1, [FOLHAGEM if acaso(c0, r, 31) > 0.5 else SAMAMB])

    # v0.9 — leitura do risco: só nos PONTOS DE SALTO sobre o vazio (a ponta
    # da plataforma encara outra plataforma a até 4 colunas e não há nada
    # sólido nas 12 linhas abaixo do vão), uma liana longa marca a borda de
    # decolagem. Queda = consequência visível, não armadilha.
    def vazio_abaixo(c, r):
        return all(not comp.solido(c, rr) for rr in range(r + 1, min(L, r + 13)))
    for c0, c1, r, tipo, _ in PLATAFORMAS:
        for ponta, passo in ((c0, -1), (c1, 1)):
            vao = [ponta + passo * k for k in range(1, 5)]
            alvo = any(any(comp.solido(x, rr) for rr in range(r - 3, r + 4)) for x in vao[1:])
            if alvo and 0 <= vao[0] < C and vazio_abaixo(vao[0], r - 1):
                comp.pendurar(ponta, r + 1, [LIANA, LIANA])

    # Pendurados: lianas de comprimentos variados, ramos e um ou outro cipó.
    for c0, c1, r, tipo, _ in PLATAFORMAS:
        c = c0 + int(acaso(c0, r, 37) * 2)
        while c <= c1:
            sorte = acaso(c, r, 41)
            if sorte < 0.36:
                if sorte < 0.20:
                    ids = [RAMOS]
                elif sorte < 0.27:
                    ids = [CIPO]
                else:
                    ids = [LIANA] * (1 + int(acaso(c, r, 43) * 3))
                comp.pendurar(c, r + 1, ids)
            c += 2 + int(acaso(c, r, 47) * 3)
    return comp.d


def estruturas():
    """Arte mantida no lugar. Conectores e toquinhos ligam os galhos novos."""
    return [
        {"imagem": "arvore_copas.png", "coluna": 10, "base": 44},
        {"imagem": "arvore_copas_alt.png", "coluna": 33, "base": 44},
        {"imagem": "arvore_copas.png", "coluna": 53, "base": 44},
        {"imagem": "arvore_copas_alt.png", "coluna": 83, "base": 44},
        {"imagem": "arvore_copas_alt.png", "coluna": 118, "base": 44},   # Vigia (nova)
        {"imagem": "arvore_copas.png", "coluna": 156, "base": 44},
        {"imagem": "isa_copas_portico_subida.png", "coluna": 9, "base": 37},
        {"imagem": "isa_copas_arvore_ancestral.png", "coluna": 37, "base": 39},
        {"imagem": "isa_copas_ninho_raizes.png", "coluna": 60, "base": 27},
        {"imagem": "isa_copas_arvore_espiral.png", "coluna": 89, "base": 30},
        {"imagem": "isa_copas_portal_ancestral.png", "coluna": 165, "base": 19},
        {"imagem": "isa_final_ramo_conector_copas_A.png", "coluna": 20, "base": 35},
        {"imagem": "isa_final_ramo_conector_copas_B.png", "coluna": 47.5, "base": 31},
        {"imagem": "isa_final_ramo_conector_copas_A.png", "coluna": 70, "base": 27},
        {"imagem": "isa_final_ramo_conector_copas_B.png", "coluna": 104.5, "base": 27},
        {"imagem": "isa_final_ramo_conector_copas_B.png", "coluna": 141.5, "base": 24},
        {"imagem": "isa_final_ramo_conector_copas_A.png", "coluna": 131.5, "base": 25},  # v0.9: apoio dos galhos 127-137
        {"imagem": "isa_v05_tronco_copas_16px.png", "coluna": 43.5, "base": 29},
        {"imagem": "isa_v05_tronco_copas_16px.png", "coluna": 96.5, "base": 20},
        {"imagem": "isa_v05_tronco_copas_16px.png", "coluna": 152.5, "base": 17},
        {"imagem": "isa_v05_tronco_copas_16px.png", "coluna": 122.5, "base": 25},
    ]
