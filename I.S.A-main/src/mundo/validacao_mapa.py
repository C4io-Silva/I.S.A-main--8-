"""
Validação do mundo — a rede de segurança que faltava.

Este módulo é usado em DOIS momentos, de propósito:

1. NO GERADOR (`gerar_mundo.py`), antes de gravar o CSV: valida a grade
   pura (lista de listas de int). Se o mapa tem um problema, o gerador
   avisa e não finge que está tudo bem.

2. EM RUNTIME (`main.py`, quando `constants.DEBUG` está ligado): valida os
   rects REAIS — o do player, os dos inimigos já instanciados, os dos
   minérios. É aqui que aparecem os problemas que a grade sozinha não
   enxerga, porque dependem do tamanho real dos sprites (que muda quando
   alguém troca uma arte).

A separação importa: a checagem 1 não precisa de pygame e roda antes de o
jogo existir; a checagem 2 precisa de pygame e roda depois de tudo montado.

Nenhuma das duas altera nada — só devolvem uma lista de strings.
"""

from src.nucleo import constants


# ── Limites de mobilidade derivados da física ────────────────────────────────
# Não são números mágicos: saem de constants.SPEED_JUMP / GRAVITY / PLAYER_SPEED.
# Se alguém mexer no pulo, os limites de "o que é alcançável" acompanham.
#
#   altura de um pulo   = v² / (2g)
#   tempo total no ar   = 2v / g
#   alcance horizontal  = PLAYER_SPEED * tempo_no_ar
def _altura_pulo_tiles():
    v = constants.SPEED_JUMP
    g = constants.GRAVITY
    return (v * v) / (2 * g) / constants.TILE_SIZE


def _alcance_pulo_tiles():
    v = constants.SPEED_JUMP
    g = constants.GRAVITY
    tempo = 2 * v / g
    return constants.PLAYER_SPEED * tempo / constants.TILE_SIZE


# O degrau considera o pulo duplo (constants.MAX_JUMPS), mas com fator de
# segurança 0.75: o segundo pulo só rende a altura cheia se for disparado
# exatamente no ápice do primeiro, e não dá pra exigir isso do jogador.
# O vão usa o alcance de um pulo truncado para baixo, pela mesma razão.
#
# Com os valores atuais (SPEED_JUMP=7.2, GRAVITY=0.36, TILE=48, MAX_JUMPS=2):
#   altura de um pulo = 1.5 tiles  →  DEGRAU_MAX = 2
#   alcance de um pulo = 2.5 tiles →  VAO_MAX    = 2
_MAX_JUMPS = getattr(constants, "MAX_JUMPS", 1)
DEGRAU_MAX = max(1, int(_altura_pulo_tiles() * _MAX_JUMPS * 0.75))
VAO_MAX = max(1, int(_alcance_pulo_tiles()))

IDS_PASSAGEM = (
    constants.TILE_PASSAGEM_CAVERNA,
    constants.TILE_PASSAGEM_COPAS,
    constants.TILE_PASSAGEM_FLORESTA,
)

VAZIO = -1


# ══════════════════════════════════════════════════════════════════════════
# 1. Validação da grade (sem pygame)
# ══════════════════════════════════════════════════════════════════════════
def validar_csv(grade, esperado=None):
    """Consistência estrutural do CSV: retângulo, dimensões, IDs conhecidos."""
    problemas = []
    if not grade:
        return ["CSV vazio"]

    larguras = {len(linha) for linha in grade}
    if len(larguras) > 1:
        problemas.append(f"CSV inconsistente: linhas com larguras diferentes {sorted(larguras)}")

    if esperado is not None and (len(grade), len(grade[0])) != tuple(esperado):
        problemas.append(
            f"CSV {len(grade)}x{len(grade[0])} nao bate com o esperado "
            f"{esperado[0]}x{esperado[1]}"
        )

    # Marcadores (player, mobs, minerios, passagens, chegadas) sao IDs legitimos
    # do CSV desde que o mapa virou data-driven: sao lidos e apagados da grade
    # por utils.extrair_marcadores antes do mundo ser montado.
    conhecidos = (set(constants.TILE_SPRITES) | set(IDS_PASSAGEM)
                  | set(constants.TILES_MARCADORES) | {VAZIO})
    desconhecidos = {v for linha in grade for v in linha if v not in conhecidos}
    for v in sorted(desconhecidos):
        problemas.append(f"bloco desconhecido no CSV: id {v} (sem sprite e sem significado)")

    # IDs que têm sprite mas o arquivo nunca foi desenhado só caem no fallback —
    # não é erro, mas some visualmente com o bloco genérico. Vale o aviso.
    return problemas


def superficies(grade, c0=None, c1=None):
    """
    Toda célula sólida com espaço vazio logo acima — ou seja, todo lugar em
    que dá pra pisar. Devolve set de (coluna, linha).

    A linha 0 nunca conta: um bloco no topo da grade não tem espaço nenhum
    acima dele, então ninguém pisa ali. Sem esta exclusão, o teto de rocha da
    caverna e cada muro de contenção viravam "plataformas inalcançáveis" no
    relatório — ruído que escondia os problemas de verdade.
    """
    linhas, colunas = len(grade), len(grade[0])
    c0 = 0 if c0 is None else max(0, c0)
    c1 = colunas - 1 if c1 is None else min(colunas - 1, c1)
    achadas = set()
    for c in range(c0, c1 + 1):
        for r in range(1, linhas):
            if (
                grade[r][c] in constants.SOLID_TILES
                and grade[r - 1][c] not in constants.SOLID_TILES
            ):
                achadas.add((c, r))
    return achadas


def trechos_de_superficie(grade, c0=None, c1=None):
    """Agrupa as superfícies em trechos horizontais contínuos (c_ini, c_fim, linha)."""
    por_linha = {}
    for c, r in superficies(grade, c0, c1):
        por_linha.setdefault(r, []).append(c)

    trechos = []
    for r, cols in por_linha.items():
        cols.sort()
        ini = ant = cols[0]
        for c in cols[1:]:
            if c == ant + 1:
                ant = c
            else:
                trechos.append((ini, ant, r))
                ini = ant = c
        trechos.append((ini, ant, r))
    return trechos


def _ligado(a, b):
    """
    `b` é alcançável a partir de `a` num pulo? Vale para os dois sentidos de
    subida/descida: descer é sempre possível (gravidade), subir respeita
    DEGRAU_MAX.
    """
    a0, a1, ar = a
    b0, b1, br = b
    if b0 > a1:
        vao = b0 - a1 - 1
    elif a0 > b1:
        vao = a0 - b1 - 1
    else:
        vao = 0  # sobrepostos horizontalmente (uma plataforma acima da outra)
    if vao > VAO_MAX:
        return False
    subida = ar - br  # positivo = b está ACIMA de a
    return subida <= DEGRAU_MAX


def alcancaveis(grade, col_entrada, linha_entrada=None, c0=None, c1=None):
    """
    BFS a partir do trecho onde o jogador entra na região. Devolve o conjunto
    de trechos (c_ini, c_fim, linha) que ele consegue alcançar andando/pulando.
    """
    trechos = trechos_de_superficie(grade, c0, c1)
    if not trechos:
        return set(), []

    def _origem():
        candidatos = [
            t for t in trechos if t[0] <= col_entrada <= t[1]
        ]
        if not candidatos:
            return None
        if linha_entrada is None:
            return min(candidatos, key=lambda t: t[2])
        # o trecho logo abaixo do ponto de entrada
        abaixo = [t for t in candidatos if t[2] >= linha_entrada]
        return min(abaixo or candidatos, key=lambda t: abs(t[2] - linha_entrada))

    origem = _origem()
    if origem is None:
        return set(), trechos

    vistos = {origem}
    fila = [origem]
    while fila:
        atual = fila.pop()
        for outro in trechos:
            if outro not in vistos and _ligado(atual, outro):
                vistos.add(outro)
                fila.append(outro)
    return vistos, trechos


def validar_regiao(grade, nome, c0, c1, col_entrada, linha_entrada=None):
    """
    Duas checagens, não uma:

    1. ALCANÇÁVEL — toda plataforma da região precisa ser atingível a partir
       da entrada. Uma que não é vira conteúdo morto (era exatamente o caso
       da fenda das raízes no mapa v3: desenhada e depois soterrada).

    2. SEM ARMADILHA — de toda plataforma alcançável o jogador precisa
       conseguir VOLTAR à entrada. Descer é sempre possível (gravidade), então
       sem esta segunda checagem um poço fundo passaria como "alcançável" e
       deixaria o jogador preso lá embaixo até o game over.
    """
    vistos, trechos = alcancaveis(grade, col_entrada, linha_entrada, c0, c1)
    if not trechos:
        return [f"{nome}: regiao sem nenhuma superficie pisavel"]
    if not vistos:
        return [f"{nome}: sem chao na coluna de entrada {col_entrada}"]

    problemas = []
    for t in trechos:
        if t not in vistos:
            problemas.append(
                f"area inacessivel — {nome}: trecho col {t[0]}-{t[1]} linha {t[2]} "
                f"nao alcancavel a partir da entrada (col {col_entrada})"
            )

    # Volta: BFS no grafo invertido a partir da mesma origem.
    origem = next(iter(sorted(vistos, key=lambda t: (abs(t[2] - (linha_entrada or t[2])), t[0]))))
    if linha_entrada is not None:
        candidatos = [t for t in vistos if t[0] <= col_entrada <= t[1]]
        if candidatos:
            origem = min(candidatos, key=lambda t: abs(t[2] - linha_entrada))

    voltam = {origem}
    fila = [origem]
    while fila:
        atual = fila.pop()
        for outro in trechos:
            if outro not in voltam and _ligado(outro, atual):
                voltam.add(outro)
                fila.append(outro)

    for t in vistos:
        if t not in voltam:
            problemas.append(
                f"armadilha — {nome}: trecho col {t[0]}-{t[1]} linha {t[2]} tem ida "
                f"mas nao tem volta para a entrada (jogador fica preso)"
            )
    return problemas


def componentes_de_terreno(grade, c0=None, c1=None):
    """
    Agrupa os tiles sólidos em componentes conexos (vizinhança de 4).

    Um mapa bem construído tende a UM componente grande por região: o terreno.
    Cada componente extra é literalmente um pedaço de matéria flutuando sem
    encostar em nada — o "bloco no meio do nada". Devolve a lista de
    componentes, do maior para o menor, cada um como lista de (linha, coluna).
    """
    linhas, colunas = len(grade), len(grade[0])
    c0 = 0 if c0 is None else max(0, c0)
    c1 = colunas - 1 if c1 is None else min(colunas - 1, c1)

    visto = [[False] * colunas for _ in range(linhas)]
    componentes = []
    for r in range(linhas):
        for c in range(c0, c1 + 1):
            if grade[r][c] not in constants.SOLID_TILES or visto[r][c]:
                continue
            pilha, celulas = [(r, c)], []
            visto[r][c] = True
            while pilha:
                y, x = pilha.pop()
                celulas.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if (
                        0 <= ny < linhas and c0 <= nx <= c1
                        and not visto[ny][nx]
                        and grade[ny][nx] in constants.SOLID_TILES
                    ):
                        visto[ny][nx] = True
                        pilha.append((ny, nx))
            componentes.append(celulas)
    componentes.sort(key=len, reverse=True)
    return componentes


def validar_terreno_conectado(grade, nome, c0, c1, max_ilhas=0):
    """
    Cobra que o terreno da região seja UMA massa contínua.

    Plataforma, galho, prateleira ou pilar precisam encostar em alguma coisa —
    parede, chão, tronco. É o que separa "um caminho que alguém construiu" de
    "uma matriz de blocos espalhados".
    """
    componentes = componentes_de_terreno(grade, c0, c1)
    if len(componentes) <= 1 + max_ilhas:
        return []
    problemas = []
    for celulas in componentes[1 + max_ilhas:]:
        linhas_c = [r for r, _ in celulas]
        cols_c = [c for _, c in celulas]
        problemas.append(
            f"bloco isolado — {nome}: {len(celulas)} tiles soltos em "
            f"col {min(cols_c)}-{max(cols_c)}, linha {min(linhas_c)}-{max(linhas_c)}, "
            f"sem encostar no terreno"
        )
    return problemas


def espaco_de_combate(grade, col, linha):
    """
    Quantos tiles contínuos de piso existem sob os pés de quem está em
    (col, linha) — ou seja, quanto chão o jogador tem para manobrar ali.
    """
    colunas = len(grade[0])
    if not (0 <= col < colunas) or grade[linha][col] not in constants.SOLID_TILES:
        return 0
    largura = 1
    c = col - 1
    while c >= 0 and grade[linha][c] in constants.SOLID_TILES and (
        linha == 0 or grade[linha - 1][c] not in constants.SOLID_TILES
    ):
        largura += 1
        c -= 1
    c = col + 1
    while c < colunas and grade[linha][c] in constants.SOLID_TILES and (
        linha == 0 or grade[linha - 1][c] not in constants.SOLID_TILES
    ):
        largura += 1
        c += 1
    return largura


def validar_ritmo(grade, inimigos, minerios, spawn_player,
                  min_combate=7, min_dist_spawn=25):
    """
    Checagens de LEVEL DESIGN, não de estrutura. O mapa pode estar
    geometricamente perfeito e ainda ser injusto:

    - inimigo de chão numa saliência estreita demais para o jogador reagir;
    - inimigo perto demais do spawn, atacando antes de o jogador entender
      onde está;
    - minério empilhado em cima de outro.
    """
    problemas = []
    col_spawn = spawn_player[0]

    for e in inimigos:
        if e.get("ancora") == "teto" or e.get("altura", 0) > 0:
            # Aranha vive no fio, tucano vive no ar: o piso sob eles não é o
            # palco do combate, então a métrica de espaço não se aplica.
            continue
        largura = espaco_de_combate(grade, e["col"], e["row"])
        if largura < min_combate:
            problemas.append(
                f"espaco de combate — {e['classe']}@col{e['col']}: apoio de apenas "
                f"{largura} tiles (minimo {min_combate}); o jogador nao tem como recuar"
            )
        distancia = abs(e["col"] - col_spawn)
        if distancia < min_dist_spawn:
            problemas.append(
                f"perto do spawn — {e['classe']}@col{e['col']}: a {distancia} tiles "
                f"do spawn do player (minimo {min_dist_spawn})"
            )

    vistos = {}
    for m in minerios:
        chave = (m["col"], m["row"])
        if chave in vistos:
            problemas.append(f"minerios sobrepostos na col {m['col']}, linha {m['row']}")
        vistos[chave] = True
    return problemas


def validar_celula_entidade(grade, rotulo, col, linha, altura_tiles=0, ancora="chao"):
    """
    A entidade declarada em (col, linha) tem apoio de verdade ali e espaço
    livre para ocupar?

    ancora="chao" : `linha` é o tile SÓLIDO em que ela pisa; `altura_tiles` é
                    quantos tiles ACIMA dele ela flutua (0 = pousada). Exige
                    espaço vazio acima.
    ancora="teto" : `linha` é o tile SÓLIDO de onde ela se pendura;
                    `altura_tiles` é quantos tiles ABAIXO dele ela fica.
                    Exige espaço vazio abaixo. É o caso da Aranha, que vive
                    presa no fio e nunca pisa em nada.
    """
    problemas = []
    linhas, colunas = len(grade), len(grade[0])

    if not (0 <= col < colunas) or not (0 <= linha < linhas):
        return [f"coordenada invalida — {rotulo}: (col {col}, linha {linha}) fora do mapa"]

    if grade[linha][col] not in constants.SOLID_TILES:
        problemas.append(
            f"{rotulo}@col{col}: a linha {linha} declarada como apoio nao e um bloco solido"
        )

    if ancora == "teto":
        # Ocupa de linha+1+altura para baixo; exige 2 tiles de folga
        faixa = range(linha + 1, min(linhas, linha + altura_tiles + 3))
    else:
        # Ocupa de linha-1-altura para cima; exige 2 tiles de folga
        faixa = range(max(0, linha - altura_tiles - 2), linha)

    for r in faixa:
        if grade[r][col] in constants.SOLID_TILES:
            problemas.append(f"{rotulo}@col{col}: embutido em bloco na linha {r}")
            break
    return problemas


# ══════════════════════════════════════════════════════════════════════════
# 2. Validação em runtime (com os rects reais)
# ══════════════════════════════════════════════════════════════════════════
def validar_entidades(grade, obstaculos, entidades, passagens=None):
    """
    Valida os rects REAIS já montados.

    grade       : lista de listas de int (o CSV carregado)
    obstaculos  : lista de pygame.Rect (world.obstacles)
    entidades   : lista de (rotulo, rect) — player, inimigos, minérios
    passagens   : dict {(linha, coluna): destino} — para detectar spawn em cima
                  de passagem (que causaria transição em loop)
    """
    import pygame  # só aqui: a validação de grade não depende de pygame

    problemas = []
    T = constants.TILE_SIZE
    limite = pygame.Rect(0, 0, len(grade[0]) * T, len(grade) * T)

    for rotulo, rect in entidades:
        if not limite.contains(rect):
            problemas.append(
                f"fora do mapa — {rotulo}: rect {tuple(rect)} sai dos limites "
                f"({limite.width}x{limite.height})"
            )
        dentro = [o for o in obstaculos if rect.colliderect(o)]
        if dentro:
            problemas.append(
                f"dentro de bloco — {rotulo}: rect {tuple(rect)} sobrepoe "
                f"{len(dentro)} bloco(s) solido(s)"
            )

    for i in range(len(entidades)):
        rot_a, rect_a = entidades[i]
        for j in range(i + 1, len(entidades)):
            rot_b, rect_b = entidades[j]
            if rect_a.colliderect(rect_b):
                problemas.append(f"spawn sobreposto — {rot_a} sobre {rot_b}")

    if passagens:
        for rotulo, rect in entidades:
            for (linha, col) in passagens:
                cel = pygame.Rect(col * T, linha * T, T, T)
                if rect.colliderect(cel):
                    problemas.append(
                        f"spawn sobreposto — {rotulo} nasce em cima da passagem "
                        f"(linha {linha}, col {col}): transicao dispararia em loop"
                    )
    return problemas


def relatorio(problemas, titulo="VALIDACAO DO MUNDO"):
    """Formata o resultado para o terminal. Devolve True se está tudo certo."""
    print(f"\n── {titulo} " + "─" * max(0, 60 - len(titulo)))
    print(f"   pulo: {_altura_pulo_tiles():.2f} tiles de altura, "
          f"{_alcance_pulo_tiles():.2f} tiles de alcance  "
          f"→ DEGRAU_MAX={DEGRAU_MAX}, VAO_MAX={VAO_MAX}")
    if not problemas:
        print("   OK — nenhum problema encontrado")
        return True
    print(f"   {len(problemas)} PROBLEMA(S):")
    for p in problemas:
        print(f"   - {p}")
    return False