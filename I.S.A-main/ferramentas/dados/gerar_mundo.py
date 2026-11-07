"""
Gerador do mundo do I.S.A — versão 5 (passada de level design).

Uma execução grava, sempre juntos:

    assets/levels/setores/*.csv     — um CSV por setor (floresta, caverna,
                                      copas, arena)
    src/nivel_dados.py              — spawn inicial, entrada de cada setor
                                      e limites da arena do boss

O QUE MUDOU DA v4 PARA A v5
---------------------------
A v4 consertou os bugs, mas o mapa continuava LENDO como uma matriz de
blocos: 22 componentes de terreno desconexos, plataformas retangulares
flutuando no vazio sem encostar em nada. A v5 ataca isso na raiz — trocando
as primitivas de desenho.

A regra que organiza tudo agora: **nenhuma peça flutua**. Toda plataforma
nasce presa em alguma coisa.

  - a floresta é UM perfil de terreno contínuo, com subidas e descidas
    interpoladas entre pontos-chave. Não há "plataforma da floresta":
    há relevo;
  - a caverna é rocha maciça ESCAVADA. Corredores, câmaras e passagens
    estreitas são buracos na pedra, e cada prateleira sai de uma parede;
  - as copas são árvores: tronco que nasce no chão, galhos presos no tronco.

O validador agora cobra isso (`validar_terreno_conectado`): se sobrar
qualquer ilha, o CSV não é gravado.

A LEITURA DO NÍVEL
------------------
    FLORESTA BAIXA (spawn)  →  clareira  →  DESCIDA NATURAL  →  ravina
       →  BOCA DA CAVERNA  →  [caverna: entrada, corredor, câmara,
          caminho alto alternativo, sala escondida, profundezas]
    volta pela ravina  →  FLORESTA CENTRAL  →  FLORESTA ALTA
       →  A GRANDE ÁRVORE  →  copa  →  [copas: a árvore-mãe]

A floresta ocupa ~57% das colunas — é o ambiente principal, como pedido.
As copas ficam no fim da subida, não no meio do caminho.

Uso:
    python gerar_mundo.py
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.nucleo import constants  # noqa: E402
from src.mundo import validacao_mapa as val  # noqa: E402

VAZIO = -1
ROCHA = 0    # tile_brick — rocha da caverna
GRAMA = 1
TERRA = 2

PASS_CAVERNA = constants.TILE_PASSAGEM_CAVERNA
PASS_COPAS = constants.TILE_PASSAGEM_COPAS
PASS_FLORESTA = constants.TILE_PASSAGEM_FLORESTA        # saida da caverna
PASS_FLOR_COPAS = constants.TILE_PASSAGEM_FLORESTA_COPAS  # saida das copas

ROWS = 44          # 44 x 48px = 2112px ≈ 3,5 telas de altura
TILE = constants.TILE_SIZE


class Grade:
    """
    Primitivas de construção. Todas produzem peças ANCORADAS: `terreno`
    preenche até o fim da grade, `escavar` abre buraco em rocha existente,
    `saliencia`/`galho` nascem grudados numa parede ou tronco.

    Não existe primitiva que solte um retângulo no ar — de propósito.
    """

    def __init__(self, cols):
        self.cols = cols
        self.g = [[VAZIO] * cols for _ in range(ROWS)]

    # ── básicas ─────────────────────────────────────────────────────────
    def preencher(self, r0, r1, c0, c1, material=ROCHA):
        for r in range(max(0, r0), min(ROWS, r1 + 1)):
            for c in range(max(0, c0), min(self.cols, c1 + 1)):
                self.g[r][c] = material

    def escavar(self, r0, r1, c0, c1):
        self.preencher(r0, r1, c0, c1, VAZIO)

    def marcar(self, r, c, tile_id):
        self.g[r][c] = tile_id

    def solido(self, r, c):
        if not (0 <= r < ROWS and 0 <= c < self.cols):
            return True
        return self.g[r][c] in constants.SOLID_TILES

    def superficie(self, c):
        for r in range(1, ROWS):
            if self.solido(r, c) and not self.solido(r - 1, c):
                return r
        return None

    # ── relevo ──────────────────────────────────────────────────────────
    def terreno(self, pontos, material=GRAMA, miolo=TERRA):
        """
        Constrói relevo contínuo a partir de pontos-chave (coluna, linha).
        Entre dois pontos a altura é interpolada, o que produz rampas em
        degraus de 1 linha — a forma que o terreno de um platformer tem.

        Preenche até o fim da grade, então o resultado é sempre UMA massa
        conectada: é isto que elimina o "bloco solto" por construção.
        """
        for (ca, ra), (cb, rb) in zip(pontos, pontos[1:]):
            largura = max(1, cb - ca)
            for c in range(ca, cb + 1):
                r = round(ra + (rb - ra) * (c - ca) / largura)
                for y in range(r, ROWS):
                    self.g[y][c] = material if y == r else miolo

    def teto(self, pontos, material=ROCHA):
        """
        O espelho de `terreno`: preenche da linha 0 PARA BAIXO até a linha
        interpolada. É o que dá pé-direito variável a uma caverna — teto
        baixo vira corredor apertado, teto alto vira câmara. Sem isso a
        caverna é um retângulo vazio de altura constante.
        """
        for (ca, ra), (cb, rb) in zip(pontos, pontos[1:]):
            largura = max(1, cb - ca)
            for c in range(ca, cb + 1):
                r = round(ra + (rb - ra) * (c - ca) / largura)
                for y in range(0, r + 1):
                    self.g[y][c] = material

    def saliencia(self, c0, c1, linha, material=ROCHA):
        """
        Prateleira de uma linha. Só é legítima se ENCOSTAR em terreno já
        existente numa das pontas (ou logo abaixo) — senão é exatamente o
        bloco flutuante que estamos combatendo, e o assert avisa na hora.
        """
        encosta = (
            self.solido(linha, c0 - 1)
            or self.solido(linha, c1 + 1)
            or any(self.solido(linha + 1, c) for c in range(c0, c1 + 1))
        )
        assert encosta, f"saliencia solta em linha {linha}, col {c0}-{c1}"
        for c in range(c0, c1 + 1):
            self.g[linha][c] = material

    def escada_de_parede(self, c_parede, lado, linha_base, linha_topo,
                         comprido=10, passo=2, minimo=3, material=ROCHA):
        """
        Escada presa numa parede, com os degraus ENCURTANDO conforme sobem.

        O encurtamento não é estético, é o que torna a escada subível. Numa
        escada de um apoio só, se um degrau for mais comprido que o de baixo
        ele cobre o de baixo inteiro: quem está lá embaixo fica num vão de
        uma linha, sem nenhuma coluna livre de onde saltar. A primeira versão
        alternava comprido/curto e por isso METADE dos degraus era impossível
        de subir — o validador geométrico aprovava (havia sobreposição e a
        subida era de 2 linhas), mas a física não deixava.
        Cada degrau agora deixa uma ponta descoberta, que é de onde se pula.

        `lado` = -1 quando a parede está à direita (degraus crescem para a
        esquerda), +1 quando está à esquerda.
        """
        linha, comp = linha_base, comprido
        while linha > linha_topo:
            if lado < 0:
                c0, c1 = c_parede - comp, c_parede - 1
            else:
                c0, c1 = c_parede + 1, c_parede + comp
            self.saliencia(c0, c1, linha, material=material)
            linha -= 2
            comp = max(minimo, comp - passo)

    # ── vegetação ───────────────────────────────────────────────────────
    def tronco(self, col, largura, linha_topo, linha_base, material=TERRA):
        """Tronco que nasce no chão e sobe. Ancorado pela base."""
        self.preencher(linha_topo, linha_base, col, col + largura - 1, material)

    def escada_entre(self, col_a, col_b, linha_base, linha_topo, largura=8,
                     material=GRAMA):
        """
        Degraus alternando entre DOIS apoios verticais — na floresta, um cipó
        e o tronco de uma árvore.

        Dois apoios resolvem o que um só não resolve: o degrau que sai de A
        e o que sai de B se sobrepõem no meio (dá para pular de um para o
        outro) mas cada um deixa a sua ponta livre do lado oposto (dá de onde
        pular). O jogador sobe em ziguezague entre os dois, que é como se
        sobe numa árvore de verdade.

        A distância entre os apoios importa: com `largura` 8, `col_b - col_a`
        precisa ficar entre largura+4 e 2*largura para haver ao mesmo tempo
        sobreposição e ponta livre. 14 é o valor usado no mapa.
        """
        linha, no_a = linha_base, True
        while linha >= linha_topo:
            if no_a:
                c0, c1 = col_a + 1, col_a + largura
            else:
                c0, c1 = col_b - largura, col_b - 1
            self.saliencia(c0, c1, linha, material=material)
            linha -= 2
            no_a = not no_a


# ════════════════════════════════════════════════════════════════════════
g = Grade(820)  # folga; a grade e cortada em COLS no fim

inimigos = []
minerios = []


def por_inimigo(col, row, classe, altura=0, regiao="", ancora="chao"):
    inimigos.append({"col": col, "row": row, "classe": classe,
                     "altura": altura, "regiao": regiao, "ancora": ancora})


def por_minerio(col, row, regiao=""):
    minerios.append({"col": col, "row": row, "regiao": regiao})


# Itens de cura (maçã, marcador 96): (col, linha do bloco de apoio, região).
curas = []


def por_cura(col, row, regiao=""):
    curas.append({"col": col, "row": row, "regiao": regiao})


# ── Encontros ────────────────────────────────────────────────────────────
# Antes os inimigos eram uma lista chapada: `por_inimigo` chamado N vezes em
# sequência, sem nenhuma noção de agrupamento. O resultado era o que a spec
# chama de "inimigos espalhados aleatoriamente" (§6, §12).
#
# Um ENCONTRO é uma situação de combate com nome e lugar: quem está nela,
# quanto espaço tem, o que se ganha. Declarar por encontro permite validar
# o que uma lista chapada não deixa: espaçamento entre inimigos, distância
# de onde o jogador nasce/chega, e se o combate tem recompensa por perto.
ENCONTROS = []

# Colunas mínimas entre dois inimigos do MESMO encontro. Colados, viram uma
# parede de dano sem espaço para revidar; longe demais, deixam de ser um
# encontro e viram dois.
DIST_MIN_MOBS = 4
# Distância mínima de qualquer ponto onde o jogador aparece. Sem isso, chegar
# numa região já é tomar dano antes do primeiro frame de controle.
DIST_MIN_CHEGADA = 10

# A âncora é consequência da classe, não escolha de quem posiciona: aranha
# pendura no teto, o resto se apoia no chão.
ANCORA_POR_CLASSE = {"Aranha": "teto"}


def encontro(nome, regiao, mobs=(), minerios=()):
    """Declara um encontro: inimigos e recompensas que fazem sentido juntos."""
    registro = {"nome": nome, "regiao": regiao,
                "mobs": list(mobs), "minerios": list(minerios)}
    ENCONTROS.append(registro)
    for mob in mobs:
        # (col, row, classe) ou (col, row, classe, altura). A altura é quantos
        # tiles o bicho flutua acima do apoio: é o que põe o tucano NO AR em
        # vez de andando no chão como uma cobra.
        col, row, classe = mob[0], mob[1], mob[2]
        altura = mob[3] if len(mob) > 3 else 0
        por_inimigo(col, row, classe, altura, regiao,
                    ancora=ANCORA_POR_CLASSE.get(classe, "chao"))
    for col, row in minerios:
        por_minerio(col, row, regiao)
    return registro


def validar_encontros(pontos_de_chegada):
    """Regras de posicionamento que a geometria sozinha não pega."""
    problemas = []
    for enc in ENCONTROS:
        cols = sorted(mob[0] for mob in enc["mobs"])
        for a, b in zip(cols, cols[1:]):
            if b - a < DIST_MIN_MOBS:
                problemas.append(
                    f"encontro '{enc['nome']}': inimigos colados nas colunas "
                    f"{a} e {b} (minimo {DIST_MIN_MOBS} de distancia)"
                )
        for mob in enc["mobs"]:
            col, row, classe = mob[0], mob[1], mob[2]
            for nome_pt, (pc, pr) in pontos_de_chegada.items():
                if abs(col - pc) < DIST_MIN_CHEGADA and abs(row - pr) <= 3:
                    problemas.append(
                        f"encontro '{enc['nome']}': {classe}@col{col} a menos de "
                        f"{DIST_MIN_CHEGADA} colunas de '{nome_pt}'"
                    )
    return problemas


# ════════════════════════════════════════════════════════════════════════
# REGIÃO 1 — FLORESTA  (o ambiente principal)
#
# Um único perfil de relevo, lido da esquerda para a direita como uma
# jornada: começa baixo e seguro, cava até a ravina onde está a boca da
# caverna, volta a subir em patamares e termina no pé da grande árvore.
# ════════════════════════════════════════════════════════════════════════
FLOR_C0 = 0

# O relevo lido como uma jornada. Os dois pontos coladinhos (140→141 e
# 185→186) são penhascos verticais de propósito: é a ravina. Uma parede
# vertical dá onde prender as saliências da subida e onde escavar a boca
# da caverna — coisa que uma encosta diagonal não oferece.
PERFIL_FLORESTA = [
    (0, 26), (30, 26),      # FLORESTA BAIXA — plana e segura, é onde se nasce
    (44, 28), (60, 28),     # depressão rasa: primeiro desnível, primeiro minério
    (78, 25), (140, 25),    # clareira longa — área aberta, até a beira da ravina
    (141, 35), (185, 35),   # A RAVINA — queda de 10 linhas e o fundo
    (186, 25), (214, 25),   # do outro lado, de volta ao nível da clareira
    (236, 22), (262, 22),   # FLORESTA CENTRAL
    (282, 19), (308, 19),   # patamar intermediário
    (326, 17), (346, 17),   # FLORESTA ALTA
    (352, 15), (372, 15),   # clareira no pé da grande árvore
]
g.terreno(PERFIL_FLORESTA)

LINHA_SPAWN = 26
COL_SPAWN = 8
RAVINA_PISO = 35

# ── A boca da caverna ───────────────────────────────────────────────────
# Escavada DENTRO do penhasco oeste, no ponto mais fundo do relevo: um vão
# de 2 linhas com teto de rocha por cima e o próprio piso da ravina embaixo.
# Não é um poço no chão — é uma entrada que o relevo mostra ao jogador.
g.escavar(RAVINA_PISO - 2, RAVINA_PISO - 1, 126, 140)
COL_BOCA_CAVERNA = 131
g.marcar(RAVINA_PISO - 1, COL_BOCA_CAVERNA, PASS_CAVERNA)

# ── Travessia da ravina ─────────────────────────────────────────────────
# Saliências de rocha presas nos DOIS penhascos. Sem as do lado oeste a
# ravina viraria via de mão única: dava para descer e seguir para leste,
# mas nunca para voltar ao começo do mapa.
g.saliencia(141, 152, RAVINA_PISO - 1, material=TERRA)   # 1º degrau, no piso
g.escada_de_parede(140, lado=+1, linha_base=32, linha_topo=24,
                   comprido=10, passo=2, material=TERRA)
g.escada_de_parede(186, lado=-1, linha_base=33, linha_topo=25,
                   comprido=10, passo=2, material=TERRA)

# ── A grande árvore: o caminho para as copas ────────────────────────────
# Tronco cheio que fecha a floresta a leste (a árvore É o limite da região)
# e galhos só do lado esquerdo, alternando comprido/curto, para escalar.
# Tronco cheio, que fecha a floresta a leste (a árvore É o limite da região),
# mais um CIPÓ 14 colunas à esquerda. Os galhos alternam entre os dois: é a
# subida em ziguezague que o enunciado pede, e não uma escada de blocos.
COL_TRONCO = 373
g.preencher(0, ROWS - 1, COL_TRONCO, COL_TRONCO, TERRA)
# Galhos afunilando para cima, como numa árvore de verdade. O afunilamento é
# o que torna a subida possível: a ponta descoberta de cada galho tem céu
# aberto acima dela, porque todos os galhos seguintes param mais para dentro.
g.escada_de_parede(COL_TRONCO, lado=-1, linha_base=13, linha_topo=3,
                   comprido=12, passo=1, minimo=6, material=GRAMA)
LINHA_COPA_FLORESTA = 3
g.saliencia(COL_TRONCO - 7, COL_TRONCO, LINHA_COPA_FLORESTA, material=GRAMA)
COL_PASS_COPAS = COL_TRONCO - 3
g.marcar(LINHA_COPA_FLORESTA - 1, COL_PASS_COPAS, PASS_COPAS)

FLOR_C1 = COL_TRONCO

# ── Pontos de interesse da floresta ─────────────────────────────────────
# Poucos minérios, cada um pedindo um desvio: o fundo da depressão, o fundo
# da ravina, o patamar alto e um galho lá no topo da árvore.
por_minerio(50, 28, "floresta")
por_minerio(158, RAVINA_PISO, "floresta")
por_minerio(295, 19, "floresta")
por_minerio(COL_TRONCO - 10, 9, "floresta")   # ponta livre do galho

# Inimigos só em áreas abertas, com chão de sobra para recuar, e longe do
# spawn: o primeiro está a 78 tiles do início.
por_inimigo(86, 25, "Enemy", 0, "floresta")
por_inimigo(165, RAVINA_PISO, "Enemy", 0, "floresta")
por_inimigo(248, 22, "Enemy", 0, "floresta")
por_inimigo(336, 17, "Enemy", 0, "floresta")
# Aranha pendurada no teto da boca da caverna — guardando a entrada.
por_inimigo(135, RAVINA_PISO - 3, "Aranha", 0, "floresta", ancora="teto")

# ════════════════════════════════════════════════════════════════════════
# REGIÃO 2 — CAVERNA  (rocha maciça escavada)
#
# Nada aqui é "colocado": tudo é buraco. Entrada → corredor descendente →
# câmara principal → (caminho alto alternativo → sala escondida) → passagem
# estreita → profundezas.
# ════════════════════════════════════════════════════════════════════════
CAV_C0 = FLOR_C1 + 1
CAV_LARG = 250
CAV_C1 = CAV_C0 + CAV_LARG

# Rocha maciça, depois o vazio inteiro, e só então piso e teto desenhados
# como PERFIS. É a mesma ideia do relevo da floresta aplicada por dentro:
# o piso é uma linha contínua que desce em degraus de 1 (dá pra subir e
# descer andando), e o teto é outra linha que sobe e desce sozinha.
# A distância entre as duas é o pé-direito — e é ela que faz um trecho ser
# corredor apertado, câmara aberta ou passagem espremida.
g.preencher(0, ROWS - 1, CAV_C0, CAV_C1, ROCHA)
g.escavar(0, ROWS - 1, CAV_C0 + 1, CAV_C1 - 1)

LINHA_CAV_ENTRADA = 16
# A caverna lida como uma jornada com INÍCIO, MEIO e FIM (§5 da spec). Cada
# par de pontos é um trecho com uma função clara, e o pé-direito (distância
# entre piso e teto) é o que dá o caráter de cada um: 4-5 linhas viram
# corredor apertado, 11-14 viram câmara onde dá para lutar.
#
#   entrada → corredor descendente → CÂMARA PRINCIPAL → passagem espremida
#   → GALERIA DOS VEIOS → ARENA → corredor fundo → CÂMARA PROFUNDA (saída)
PISO_CAVERNA = [
    (CAV_C0 + 1, LINHA_CAV_ENTRADA), (CAV_C0 + 30, LINHA_CAV_ENTRADA),  # entrada
    (CAV_C0 + 52, 20), (CAV_C0 + 70, 20),        # corredor → primeiro patamar
    (CAV_C0 + 92, 26), (CAV_C0 + 122, 26),       # CÂMARA PRINCIPAL
    (CAV_C0 + 136, 31), (CAV_C0 + 146, 31),      # passagem estreita
    (CAV_C0 + 158, 34), (CAV_C0 + 178, 34),      # GALERIA DOS VEIOS
    (CAV_C0 + 186, 30), (CAV_C0 + 208, 30),      # ARENA DE COMBATE
    (CAV_C0 + 220, 36), (CAV_C0 + 234, 36),      # corredor fundo
    (CAV_C0 + 244, 40), (CAV_C1 - 1, 40),        # CÂMARA PROFUNDA
]
TETO_CAVERNA = [
    (CAV_C0 + 1, 11), (CAV_C0 + 30, 11),         # entrada de teto baixo
    (CAV_C0 + 44, 15), (CAV_C0 + 60, 15),        # corredor apertado (5 linhas)
    (CAV_C0 + 74, 12), (CAV_C0 + 84, 12),
    (CAV_C0 + 92, 12), (CAV_C0 + 122, 12),       # câmara: 14 linhas de pé-direito
    (CAV_C0 + 132, 27), (CAV_C0 + 146, 27),      # passagem espremida (3-4 linhas)
    (CAV_C0 + 154, 28), (CAV_C0 + 178, 28),      # galeria: 5 linhas, baixa e longa
    (CAV_C0 + 188, 18), (CAV_C0 + 208, 18),      # arena: 11 linhas, espaço de luta
    (CAV_C0 + 218, 30), (CAV_C0 + 234, 30),      # corredor fundo, apertado de novo
    (CAV_C0 + 242, 22), (CAV_C1 - 1, 22),        # câmara profunda, a mais alta
]
g.terreno(PISO_CAVERNA, material=ROCHA, miolo=ROCHA)
g.teto(TETO_CAVERNA)

COL_PASS_FLOR_CAV = CAV_C0 + 14
g.marcar(LINHA_CAV_ENTRADA - 1, COL_PASS_FLOR_CAV, PASS_FLORESTA)

# ── Estruturas dentro da câmara principal ───────────────────────────────
# Colunas de rocha que vão do piso ao teto (presas nas duas pontas) e uma
# parede pendurada com vão embaixo: é o que transforma um salão vazio num
# espaço com corredores, cantos e obstáculos.
g.preencher(13, 25, CAV_C0 + 100, CAV_C0 + 101, ROCHA)   # coluna do piso ao teto
# Parede pendurada no teto com um vão de 2 linhas embaixo: dá para passar
# agachado por baixo dela. É o obstáculo que faz a câmara ter "dentro".
g.preencher(13, 23, CAV_C0 + 112, CAV_C0 + 113, ROCHA)
# Monte de rocha no piso: primeiro degrau do caminho alto, e o que obriga a
# subir em vez de so andar reto. Fica 3 colunas AFASTADO da parede pendurada
# de proposito — encostado nela, o jogador nao tinha de onde saltar: por
# baixo da parede so ha 2 linhas de pé-direito, e subir ali significa bater
# a cabeça nela. Com a folga, ele pula do piso livre e cai no topo do monte.
g.preencher(24, 25, CAV_C0 + 117, CAV_C0 + 122, ROCHA)

# ── Caminho alto alternativo ────────────────────────────────────────────
# A escada se prende na FACE LESTE da parede pendurada (CAV_C0+113), que é
# a única superfície vertical de verdade da câmara. Não se usa a parede da
# câmara porque é por ela que o piso segue para as profundezas — uma parede
# só pode ter um trabalho.
g.escada_de_parede(CAV_C0 + 113, lado=+1, linha_base=22, linha_topo=12,
                   comprido=8, passo=1, minimo=4)

# ── Sala escondida, escavada acima do teto da câmara ────────────────────
# Fica literalmente dentro da rocha do teto. Quem sobe a escada e continua
# achando o vão estreito encontra a maior concentração de minério do mapa.
SALA_C0, SALA_C1 = CAV_C0 + 96, CAV_C0 + 118
g.escavar(6, 9, SALA_C0, SALA_C1)                  # a sala (piso na linha 10)
g.escavar(10, 13, CAV_C0 + 115, CAV_C0 + 119)      # a fresta que atravessa o teto
g.saliencia(CAV_C0 + 112, CAV_C0 + 116, 12)        # degrau dentro da fresta

# ── GALERIA DOS VEIOS ───────────────────────────────────────────────────
# Corredor longo e baixo com prateleiras presas no piso, alternando os dois
# lados. O minério fica EM CIMA delas, não flutuando: é o §8 ("o minério deve
# parecer fazer parte da estrutura da caverna").
# O pilar vem PRIMEIRO de propósito: é ele que ancora a prateleira alta.
# Invertida, a ordem dispara o assert de `saliencia` — que é justamente o
# guarda-corpo contra bloco flutuante.
# O pilar vem PRIMEIRO de propósito: é ele que ancora a prateleira alta.
# E as duas sobem de 2 em 2 linhas, com folga horizontal entre elas: o pulo
# do jogo vale 1,5 tile de altura e 2,5 de alcance, então degrau de 3 linhas
# é enfeite inalcançável, não level design.
g.preencher(31, 33, CAV_C0 + 172, CAV_C0 + 172, ROCHA)
g.saliencia(CAV_C0 + 160, CAV_C0 + 165, 33)   # piso 34 -> sobe 1
g.saliencia(CAV_C0 + 168, CAV_C0 + 173, 31)   # da anterior -> sobe 2

# ── ARENA DE COMBATE ────────────────────────────────────────────────────
# Espaço aberto com dois pilares do piso ao teto: dá cobertura, obriga a
# circular e impede que a luta vire "andar reto batendo".
g.preencher(19, 29, CAV_C0 + 196, CAV_C0 + 196, ROCHA)
g.preencher(19, 29, CAV_C0 + 205, CAV_C0 + 205, ROCHA)
# Escadinha entre os dois pilares: 30 -> 28 -> 26 -> 24, sempre de 2 em 2 e
# sempre deixando ponta livre do lado oposto, que é de onde se salta.
g.saliencia(CAV_C0 + 197, CAV_C0 + 200, 28)
g.saliencia(CAV_C0 + 202, CAV_C0 + 204, 26)
g.saliencia(CAV_C0 + 197, CAV_C0 + 201, 24)              # plataforma central

# ── NICHO ESCONDIDO DA ARENA ────────────────────────────────────────────
# Escavado DENTRO da rocha do teto da arena. Quem só atravessa a arena não vê;
# quem sobe a escadinha e continua subindo pela chaminé acha a maior
# concentração de minério da segunda metade da caverna.
NICHO_C0, NICHO_C1 = CAV_C0 + 197, CAV_C0 + 207
g.escavar(13, 16, NICHO_C0, NICHO_C1)                    # a sala (piso: linha 17)
g.escavar(17, 23, CAV_C0 + 199, CAV_C0 + 203)            # chaminé de acesso
# Degraus da chaminé: largo, estreito, largo — o estreito deixa as colunas
# 199-200 livres, senão o degrau de cima cobre o de baixo e ninguém sobe.
g.saliencia(CAV_C0 + 199, CAV_C0 + 204, 22)
g.saliencia(CAV_C0 + 201, CAV_C0 + 204, 20)
g.saliencia(CAV_C0 + 199, CAV_C0 + 201, 18)

# ── Pontos de interesse da caverna ──────────────────────────────────────
# Concentração bem maior que na floresta, puxada para o fundo e para a sala
# escondida: quem explora mais fundo é quem leva mais.
# A caverna lida de ponta a ponta, alternando exploração, combate e
# recompensa (§7: pergunta -> exploração -> combate -> pergunta -> minérios
# -> área secreta). Cada minério é uma pergunta, então a distribuição dos
# minérios É a distribuição das perguntas.
encontro("entrada", "caverna",
         minerios=[(CAV_C0 + 24, LINHA_CAV_ENTRADA)])
encontro("corredor descendente", "caverna",
         mobs=[(CAV_C0 + 62, 20, "Enemy")],
         minerios=[(CAV_C0 + 64, 20)])
encontro("camara principal", "caverna",
         mobs=[(CAV_C0 + 104, 26, "Enemy"), (CAV_C0 + 110, 26, "Enemy"),
               (CAV_C0 + 92, 12, "Aranha")],
         minerios=[(CAV_C0 + 96, 26), (CAV_C0 + 107, 26)])
encontro("sala escondida", "caverna",
         minerios=[(SALA_C0 + 4, 10), (SALA_C0 + 9, 10), (SALA_C0 + 15, 10)])
# Galeria: o minério fica EM CIMA das prateleiras, e a aranha desce bem no
# vão entre elas — obriga a escolher entre subir e recuar.
encontro("galeria dos veios", "caverna",
         mobs=[(CAV_C0 + 166, 28, "Aranha"), (CAV_C0 + 178, 34, "Enemy")],
         minerios=[(CAV_C0 + 162, 33), (CAV_C0 + 171, 31)])
# Arena: dois inimigos separados VERTICALMENTE, um no chão e um guardando a
# plataforma. É o encontro mais difícil da região.
encontro("arena", "caverna",
         mobs=[(CAV_C0 + 190, 30, "Enemy"), (CAV_C0 + 202, 30, "Enemy"),
               (CAV_C0 + 195, 18, "Aranha")],
         minerios=[(CAV_C0 + 198, 24)])
encontro("nicho secreto", "caverna",
         minerios=[(CAV_C0 + 197, 17), (CAV_C0 + 206, 17)])
encontro("camara profunda", "caverna",
         mobs=[(CAV_C0 + 244, 40, "Enemy"), (CAV_C0 + 249, 22, "Aranha")],
         minerios=[(CAV_C0 + 246, 40), (CAV_C0 + 248, 40)])

# ════════════════════════════════════════════════════════════════════════
# REGIÃO 3 — COPAS  (a recompensa da subida)
#
# Uma árvore-mãe: tronco do chão ao topo, galhos dos DOIS lados para o
# jogador circular, e uma copa larga no alto. Pequena e vertical de
# propósito — é área especial, não mais um corredor.
# ════════════════════════════════════════════════════════════════════════
COP_C0 = CAV_C1 + 1
COP_LARG = 130
COP_C1 = COP_C0 + COP_LARG
g.preencher(0, ROWS - 1, COP_C0, COP_C0, TERRA)   # tronco-parede da esquerda

LINHA_COPAS_CHAO = 30
g.terreno([(COP_C0 + 1, LINHA_COPAS_CHAO), (COP_C1 - 1, LINHA_COPAS_CHAO)],
          material=GRAMA, miolo=TERRA)
COL_PASS_FLOR_COP = COP_C0 + 7
g.marcar(LINHA_COPAS_CHAO - 1, COL_PASS_FLOR_COP, PASS_FLOR_COPAS)

# As copas deixaram de ser uma árvore só com 56 colunas de clareira em volta.
# Agora são uma região com a mesma estrutura da caverna — início, meio e fim —
# só que lida de baixo para cima (§9, §11).
#
#   clareira da chegada → PRIMEIRA ÁRVORE (cipó + tronco, ziguezague)
#   → PONTE DE GALHOS suspensa → ÁRVORE-MÃE → COPA (saída, o ponto mais alto)
#
# A verticalidade é o assunto: quase toda recompensa exige subir, e os
# tucanos ocupam o ar entre as plataformas em vez de ficarem enfileirados.

# ── PRIMEIRA ÁRVORE: cipó + tronco, subida em ziguezague ────────────────
# Mesma técnica da grande árvore da floresta: dois apoios verticais com
# galhos alternados. Um apoio só não funciona — o galho de cima cobre o de
# baixo e não sobra de onde saltar (ver docstring de escada_entre).
LINHA_PONTE = 12   # declarada antes: o tronco da 1a arvore para nela
COL_CIPO_COPAS = COP_C0 + 24
COL_TRONCO_1 = COP_C0 + 38
g.tronco(COL_CIPO_COPAS, 1, 14, LINHA_COPAS_CHAO - 1)  # topo na altura do ultimo degrau
g.tronco(COL_TRONCO_1, 2, LINHA_PONTE, LINHA_COPAS_CHAO - 1)
g.escada_entre(COL_CIPO_COPAS, COL_TRONCO_1, linha_base=28, linha_topo=14,
               largura=8, material=GRAMA)

# ── PONTE DE GALHOS ─────────────────────────────────────────────────────
# Travessia suspensa entre as duas árvores, com um vão no meio que obriga a
# pular. Cada trecho encosta num apoio: nada solto no ar.
# O apoio do meio nasce PRIMEIRO: é nele que o segundo trecho da ponte se
# prende. Na ordem inversa, o assert de `saliencia` acusa galho solto — que
# é exatamente o "bloco no vazio" que o §16 proíbe.
g.tronco(COL_TRONCO_1 + 22, 1, 10, LINHA_COPAS_CHAO - 1)  # apoio do meio, sobe ate o ninho
# Trecho 1 encosta no topo do tronco; vao de 2 colunas (o limite do pulo);
# trecho 2 encosta no apoio do meio. O vao e o que torna a ponte travessia e
# nao corredor.
g.saliencia(COL_TRONCO_1 + 2, COL_TRONCO_1 + 10, LINHA_PONTE, material=GRAMA)
g.saliencia(COL_TRONCO_1 + 13, COL_TRONCO_1 + 22, LINHA_PONTE, material=GRAMA)

# ── ÁRVORE-MÃE: o tronco é a parede leste da região ─────────────────────
COL_TRONCO_COPAS = COP_C1
g.preencher(0, ROWS - 1, COL_TRONCO_COPAS, COL_TRONCO_COPAS, TERRA)
g.escada_de_parede(COL_TRONCO_COPAS, lado=-1, linha_base=28, linha_topo=6,
                   comprido=20, passo=1, minimo=9, material=GRAMA)
LINHA_COPA = 6
g.saliencia(COL_TRONCO_COPAS - 9, COL_TRONCO_COPAS, LINHA_COPA, material=GRAMA)

# ── NINHO ESCONDIDO ─────────────────────────────────────────────────────
# Plataforma isolada acima da ponte, presa no apoio do meio. Só se chega
# saltando do galho mais alto da primeira árvore: é a área secreta das copas,
# equivalente à sala escondida da caverna.
g.saliencia(COL_TRONCO_1 + 16, COL_TRONCO_1 + 22, 10, material=GRAMA)

# ── Encontros das copas ─────────────────────────────────────────────────
# Tucano aproveita o ar aberto: os três primeiros ocupam alturas diferentes
# da mesma clareira, em vez de enfileirados na mesma linha (§12).
# Os tucanos ficam sobre o CHAO ABERTO, com alturas diferentes — e o que
# aproveita a verticalidade (§12) sem enfileirar todo mundo na mesma linha.
# Minerio, ao contrario, fica em cima de galho: subir e o preco da recompensa.
encontro("clareira da chegada", "copas",
         mobs=[(COP_C0 + 16, LINHA_COPAS_CHAO, "Tucano", 6)],
         minerios=[(COP_C0 + 18, LINHA_COPAS_CHAO)])
encontro("primeira arvore", "copas",
         minerios=[(COP_C0 + 26, 24), (COP_C0 + 26, 16)])  # em cima dos galhos
encontro("ponte de galhos", "copas",
         mobs=[(COL_TRONCO_1 + 6, LINHA_COPAS_CHAO, "Tucano", 8),
               (COL_TRONCO_1 + 13, LINHA_COPAS_CHAO, "Tucano", 12)],
         minerios=[(COL_TRONCO_1 + 5, LINHA_PONTE)])
encontro("ninho escondido", "copas",
         minerios=[(COL_TRONCO_1 + 18, 10), (COL_TRONCO_1 + 21, 10)])
encontro("arvore-mae", "copas",
         mobs=[(COL_TRONCO_COPAS - 24, LINHA_COPAS_CHAO, "Tucano", 6)],
         minerios=[(COL_TRONCO_COPAS - 20, 28), (COL_TRONCO_COPAS - 14, 16)])
# A copa virou a antessala da arena: o jogador chega nela voltando da arena
# (chegada 45), então fica sem inimigo — regra DIST_MIN_CHEGADA.
encontro("copa", "copas",
         minerios=[(COL_TRONCO_COPAS - 7, LINHA_COPA)])
COL_PASS_ARENA = COL_TRONCO_COPAS - 2
g.marcar(LINHA_COPA - 1, COL_PASS_ARENA, constants.TILE_PASSAGEM_ARENA)

# ════════════════════════════════════════════════════════════════════════
# SETOR 4 — ARENA DO BOSS (clareira no alto da copa)
#
# Setor próprio: entra-se pela passagem no alto da copa da árvore-mãe (34) e
# sai-se pela passagem 35, de volta para a copa. Não há inimigo comum nem
# minério (validar_area_boss cobra isso): o Gorila nasce no marcador
# TILE_AREA_BOSS (95), e a luta começa quando o jogador cruza a borda
# esquerda de AREA_BOSS — a saída fica antes dessa borda, fora da luta.
#
# Geometria pensada para o combate (ver src/enemies/boss.py):
#   - chão contínuo de 30 colunas: espaço para correr dos arremessos;
#   - DUAS plataformas baixas (2 tiles acima do chão, alcançáveis com o
#     pulo duplo) nas laterais: mudar de altura é a outra forma de fugir das
#     bananas, e elas não protegem da onda de choque (que corre no chão,
#     mas o jogador em cima da plataforma está acima dela);
#   - teto de galhos alto (linha 8) só para fechar o cenário.
# ════════════════════════════════════════════════════════════════════════
ARENA_C0 = COP_C1 + 1                    # parede oeste
ARENA_LARG = 40
ARENA_C1 = ARENA_C0 + ARENA_LARG         # parede leste
LINHA_ARENA = 24                         # chão da arena
ARENA_MIN_LARGURA = 24                   # colunas livres mínimas
ARENA_MIN_ALTURA = 8                     # linhas livres acima do chão

g.preencher(0, ROWS - 1, ARENA_C0, ARENA_C0, TERRA)
g.terreno([(ARENA_C0 + 1, LINHA_ARENA), (ARENA_C1 - 1, LINHA_ARENA)],
          material=GRAMA, miolo=TERRA)
g.preencher(0, ROWS - 1, ARENA_C1, ARENA_C1, TERRA)
COL_CHEGADA_ARENA = ARENA_C0 + 3
COL_PASS_SAIDA_ARENA = ARENA_C0 + 7
g.marcar(LINHA_ARENA - 1, COL_PASS_SAIDA_ARENA, constants.TILE_PASSAGEM_SAIDA_ARENA)
# Teto de galhos (fecha o céu da clareira; bem acima do alcance do pulo).
g.preencher(0, 7, ARENA_C0, ARENA_C1, TERRA)
g.preencher(8, 8, ARENA_C0, ARENA_C1, GRAMA)
# Plataformas laterais de combate: (coluna inicial, coluna final), na linha
# PLATAFORMA_ARENA_LINHA. Declaradas aqui para validar_area_boss saber que
# são intencionais.
PLATAFORMA_ARENA_LINHA = LINHA_ARENA - 2
PLATAFORMAS_ARENA = [(ARENA_C0 + 12, ARENA_C0 + 15), (ARENA_C1 - 5, ARENA_C1 - 2)]
for _c0, _c1 in PLATAFORMAS_ARENA:
    g.preencher(PLATAFORMA_ARENA_LINHA, PLATAFORMA_ARENA_LINHA, _c0, _c1, GRAMA)
    # Uma maçã em cada plataforma: subir nela é arriscado, mas cura.
    por_cura((_c0 + _c1) // 2, PLATAFORMA_ARENA_LINHA, "arena")
# Antessala: uma maçã na copa, antes de entrar na arena.
por_cura(COL_TRONCO_COPAS - 4, LINHA_COPA, "copas")

AREA_BOSS = {
    "c0": COL_PASS_SAIDA_ARENA + 3,       # a saída fica fora da área de luta
    "c1": ARENA_C1 - 1,
    "linha_topo": LINHA_ARENA - 12,
    "linha_chao": LINHA_ARENA,
    "setor": "arena",
}
AREA_BOSS["marcador"] = ((AREA_BOSS["c0"] + AREA_BOSS["c1"]) // 2, LINHA_ARENA - 1)

COLS = ARENA_C1 + 1
g.g = [linha[:COLS] for linha in g.g]
g.cols = COLS

PLAYER_SPAWN = (COL_SPAWN, LINHA_SPAWN)

SPAWNS = {
    "floresta_da_caverna": ((COL_BOCA_CAVERNA + 8) * TILE, (RAVINA_PISO - 1) * TILE),
    "floresta_do_cipo": ((COL_PASS_COPAS - 4) * TILE, (LINHA_COPA_FLORESTA - 1) * TILE),
    "caverna_entrada": ((CAV_C0 + 6) * TILE, (LINHA_CAV_ENTRADA - 1) * TILE),
    "copas_entrada": ((COP_C0 + 3) * TILE, (LINHA_COPAS_CHAO - 1) * TILE),
    "arena_entrada": (COL_CHEGADA_ARENA * TILE, (LINHA_ARENA - 1) * TILE),
    "copas_da_arena": ((COL_PASS_ARENA - 4) * TILE, (LINHA_COPA - 1) * TILE),
}

# Celula (coluna, linha) de cada ponto de chegada — os mesmos pontos que
# SPAWNS guardava em pixels. Daqui saem os marcadores 40..43 no CSV.
CELULA_CHEGADA = {
    "floresta_da_caverna": (COL_BOCA_CAVERNA + 8, RAVINA_PISO - 1),
    "floresta_do_cipo": (COL_PASS_COPAS - 4, LINHA_COPA_FLORESTA - 1),
    "caverna_entrada": (CAV_C0 + 6, LINHA_CAV_ENTRADA - 1),
    "copas_entrada": (COP_C0 + 3, LINHA_COPAS_CHAO - 1),
    "arena_entrada": (COL_CHEGADA_ARENA, LINHA_ARENA - 1),
    "copas_da_arena": (COL_PASS_ARENA - 4, LINHA_COPA - 1),
}

CHEGADAS = {
    "caverna_entrada": constants.TILE_CHEGADA_CAVERNA,
    "copas_entrada": constants.TILE_CHEGADA_COPAS,
    "floresta_da_caverna": constants.TILE_CHEGADA_FLOR_CAVERNA,
    "floresta_do_cipo": constants.TILE_CHEGADA_FLOR_COPAS,
    "arena_entrada": constants.TILE_CHEGADA_ARENA,
    "copas_da_arena": constants.TILE_CHEGADA_COPAS_ARENA,
}

PASSAGENS = {
    (RAVINA_PISO - 1, COL_BOCA_CAVERNA): {"ambiente": "caverna", "spawn": "caverna_entrada"},
    (LINHA_COPA_FLORESTA - 1, COL_PASS_COPAS): {"ambiente": "copas", "spawn": "copas_entrada"},
    (LINHA_CAV_ENTRADA - 1, COL_PASS_FLOR_CAV): {"ambiente": "floresta", "spawn": "floresta_da_caverna"},
    (LINHA_COPAS_CHAO - 1, COL_PASS_FLOR_COP): {"ambiente": "floresta", "spawn": "floresta_do_cipo"},
    (LINHA_COPA - 1, COL_PASS_ARENA): {"ambiente": "copas", "spawn": "arena_entrada"},
    (LINHA_ARENA - 1, COL_PASS_SAIDA_ARENA): {"ambiente": "copas", "spawn": "copas_da_arena"},
}

REGIOES = {
    "floresta": {"c0": FLOR_C0, "c1": FLOR_C1,
                 "entrada_col": COL_SPAWN, "entrada_row": LINHA_SPAWN},
    "caverna": {"c0": CAV_C0, "c1": CAV_C1,
                "entrada_col": CAV_C0 + 6, "entrada_row": LINHA_CAV_ENTRADA},
    "copas": {"c0": COP_C0, "c1": COP_C1,
              "entrada_col": COP_C0 + 3, "entrada_row": LINHA_COPAS_CHAO},
    "arena": {"c0": ARENA_C0, "c1": ARENA_C1,
              "entrada_col": COL_CHEGADA_ARENA, "entrada_row": LINHA_ARENA},
}


# ════════════════════════════════════════════════════════════════════════
# CARIMBO DOS MARCADORES NA GRADE
#
# Esta e a metade "escrita" do mapa data-driven. Ate aqui o gerador so sabia
# montar terreno; player, mobs, minerios e destinos saiam em listas Python
# para src/nivel_dados.py. Agora eles tambem viram CELULAS DO CSV, e e o CSV
# que o jogo le (utils.extrair_marcadores).
#
# Conversao — inversa exata da que o leitor faz. A celula do marcador e a
# celula que a entidade OCUPA, entao:
#     chao  -> linha_marcador = row - 1 - altura   (row = bloco de apoio)
#     teto  -> linha_marcador = row + 1 + altura   (row = bloco do teto)
# O jogo le SO os marcadores; as listas `inimigos`/`minerios` daqui servem
# para a validacao do gerador.
# ════════════════════════════════════════════════════════════════════════
def _celula_do_marcador(row, altura, ancora):
    return (row + 1 + altura) if ancora == "teto" else (row - 1 - altura)


CONFLITOS_MARCADORES = []


def carimbar_marcadores():
    """Escreve os marcadores na grade. Devolve quantos foram gravados."""
    gravados = 0

    def _por(linha, col, tile_id, oque):
        nonlocal gravados
        if not (0 <= linha < ROWS and 0 <= col < COLS):
            print(f"  AVISO: {oque} fora da grade ({linha},{col}) — nao carimbado")
            return
        atual = g.g[linha][col]
        if atual in constants.TILES_MARCADORES:
            CONFLITOS_MARCADORES.append(
                f"marcador sobreposto: {oque} em ({linha},{col}) apagaria o "
                f"marcador {atual} que ja estava ali")
            return
        if atual in constants.SOLID_TILES:
            print(f"  AVISO: {oque} cairia dentro de bloco solido em "
                  f"({linha},{col}) — nao carimbado")
            return
        g.g[linha][col] = tile_id
        gravados += 1

    lin_player = _celula_do_marcador(LINHA_SPAWN, 0, "chao")
    _por(lin_player, COL_SPAWN, constants.TILE_PLAYER_SPAWN, "spawn do player")

    for m in minerios:
        _por(_celula_do_marcador(m["row"], 0, "chao"), m["col"],
             constants.TILE_MINERIO, "minerio")

    id_por_classe = {c: t for t, (c, _) in constants.MARCADORES_MOB.items()}
    for e in inimigos:
        tile_id = id_por_classe.get(e["classe"])
        if tile_id is None:
            print(f"  AVISO: classe {e['classe']} sem marcador — nao carimbada")
            continue
        _por(_celula_do_marcador(e["row"], e.get("altura", 0), e.get("ancora", "chao")),
             e["col"], tile_id, f"mob {e['classe']}")

    col_boss, lin_boss = AREA_BOSS["marcador"]
    _por(lin_boss, col_boss, constants.TILE_AREA_BOSS, "area do boss")

    for c in curas:
        _por(_celula_do_marcador(c["row"], 0, "chao"), c["col"],
             constants.TILE_ITEM_CURA, "item de cura")

    # Chegadas: mesma celula que o dict SPAWNS apontava, agora como marcador.
    for nome, tile_id in CHEGADAS.items():
        col, linha = CELULA_CHEGADA[nome]
        _por(linha, col, tile_id, f"chegada {nome}")

    return gravados


# ════════════════════════════════════════════════════════════════════════
# SETORES — cada região vira um CSV próprio
#
# O mundo continua sendo CONSTRUÍDO numa grade só (as primitivas usam
# colunas absolutas e a validação de geometria roda nela), mas é GRAVADO
# fatiado: uma faixa de colunas por setor. As regiões já eram separadas por
# paredes cheias e só se ligavam por passagens, então o corte não muda nada
# no que o jogador vê.
# ════════════════════════════════════════════════════════════════════════
def faixas_dos_setores():
    """nome do setor -> (coluna inicial, coluna final) na grade de construção."""
    faixas = {nome: (r["c0"], r["c1"]) for nome, r in REGIOES.items()}
    assert set(faixas) == set(constants.SETORES), "REGIOES e constants.SETORES divergem"
    return faixas


def fatiar_setores():
    """nome -> grade (lista de linhas) só com as colunas daquele setor."""
    return {nome: [linha[c0:c1 + 1] for linha in g.g]
            for nome, (c0, c1) in faixas_dos_setores().items()}


def validar_ligacoes(grades):
    """
    Cada passagem precisa apontar para uma chegada que EXISTE no setor de
    destino — senão o jogador aperta E e nada acontece. Cada setor também
    precisa ser um retângulo e só um setor pode ter o spawn do player.
    """
    problemas = []
    ids = {nome: {v for linha in gr for v in linha} for nome, gr in grades.items()}
    for nome, conteudo in ids.items():
        if len({len(linha) for linha in grades[nome]}) != 1:
            problemas.append(f"setor {nome}: linhas de larguras diferentes")
        for tile_id in conteudo & constants.TILES_PASSAGEM:
            destino = constants.PASSAGENS_CSV[tile_id]
            if destino["chegada"] not in ids.get(destino["setor"], set()):
                problemas.append(
                    f"setor {nome}: passagem {tile_id} leva a '{destino['setor']}', "
                    f"que nao tem a chegada {destino['chegada']}"
                )
    com_spawn = [n for n, c in ids.items() if constants.TILE_PLAYER_SPAWN in c]
    if com_spawn != [constants.SETOR_INICIAL]:
        problemas.append(f"spawn do player deveria estar so em "
                         f"'{constants.SETOR_INICIAL}', esta em {com_spawn}")
    return problemas


def validar_area_boss():
    """
    A arena precisa existir de verdade: chão contínuo, espaço livre acima,
    largura mínima, vazia de inimigos/minérios e alcançável (e com volta) a
    partir da entrada das copas.
    """
    a = AREA_BOSS
    problemas = []
    largura = a["c1"] - a["c0"] + 1
    if largura < ARENA_MIN_LARGURA:
        problemas.append(f"area do boss estreita: {largura} colunas "
                         f"(minimo {ARENA_MIN_LARGURA})")
    for c in range(a["c0"], a["c1"] + 1):
        if g.g[a["linha_chao"]][c] not in constants.SOLID_TILES:
            problemas.append(f"area do boss: buraco no chao na coluna {c}")
        for r in range(a["linha_chao"] - ARENA_MIN_ALTURA, a["linha_chao"]):
            plataforma = r == PLATAFORMA_ARENA_LINHA and any(
                p0 <= c <= p1 for p0, p1 in PLATAFORMAS_ARENA)
            if g.g[r][c] in constants.SOLID_TILES and not plataforma:
                problemas.append(f"area do boss: bloco solido em ({r},{c})")
    # Espaço livre para o boss no centro: nada sólido sobre ele.
    col_boss, lin_boss = a["marcador"]
    for r in range(lin_boss - 4, lin_boss + 1):
        for c in range(col_boss - 2, col_boss + 3):
            if g.g[r][c] in constants.SOLID_TILES:
                problemas.append(f"area do boss: bloco solido em ({r},{c}) sobre o boss")
    for e in inimigos:
        if a["c0"] <= e["col"] <= a["c1"]:
            problemas.append(f"area do boss: {e['classe']} na coluna {e['col']} "
                             f"(a arena deve ficar vazia)")
    for m in minerios:
        if a["c0"] <= m["col"] <= a["c1"]:
            problemas.append(f"area do boss: minerio na coluna {m['col']}")
    r = REGIOES[a["setor"]]
    vistos, _ = val.alcancaveis(g.g, r["entrada_col"], r["entrada_row"],
                                r["c0"], r["c1"])
    if not any(t[2] == a["linha_chao"] and t[0] <= a["c0"] and t[1] >= a["c1"]
               for t in vistos):
        problemas.append("area do boss inalcancavel a partir da entrada da arena")
    return problemas


def validar():
    problemas = list(CONFLITOS_MARCADORES)

    larguras = {len(linha) for linha in g.g}
    if len(larguras) > 1:
        problemas.append(f"CSV inconsistente: larguras {sorted(larguras)}")

    conhecidos = (set(constants.TILE_SPRITES) | set(constants.TILES_MARCADORES)
                  | {VAZIO})
    for v in sorted({v for linha in g.g for v in linha} - conhecidos):
        problemas.append(f"bloco desconhecido: id {v}")

    for nome, r in REGIOES.items():
        # As plataformas de combate da arena são ilhas de propósito.
        ilhas = len(PLATAFORMAS_ARENA) if nome == "arena" else 0
        problemas += val.validar_terreno_conectado(g.g, nome, r["c0"], r["c1"],
                                                   max_ilhas=ilhas)
        problemas += val.validar_regiao(
            g.g, nome, r["c0"], r["c1"], r["entrada_col"], r["entrada_row"]
        )

    for e in inimigos:
        problemas += val.validar_celula_entidade(
            g.g, f"{e['classe']}({e['regiao']})", e["col"], e["row"],
            e["altura"], e["ancora"]
        )
    for m in minerios:
        problemas += val.validar_celula_entidade(
            g.g, f"minerio({m['regiao']})", m["col"], m["row"], 0
        )
    for c in curas:
        problemas += val.validar_celula_entidade(
            g.g, f"cura({c['regiao']})", c["col"], c["row"], 0
        )
    problemas += val.validar_celula_entidade(
        g.g, "player", PLAYER_SPAWN[0], PLAYER_SPAWN[1], 0
    )
    problemas += val.validar_ritmo(g.g, inimigos, minerios, PLAYER_SPAWN)
    problemas += validar_area_boss()

    for nome, (px, py) in SPAWNS.items():
        col, linha = px // TILE, py // TILE
        if not (0 <= col < COLS and 0 <= linha < ROWS):
            problemas.append(f"coordenada invalida — spawn '{nome}' fora do mapa")
            continue
        if g.g[linha][col] in constants.SOLID_TILES:
            problemas.append(f"dentro de bloco — spawn '{nome}' (col {col}, linha {linha})")
        if linha + 1 < ROWS and g.g[linha + 1][col] not in constants.SOLID_TILES:
            problemas.append(f"spawn '{nome}' nao tem chao logo abaixo (col {col})")
        for (pr, pc) in PASSAGENS:
            if abs(pc - col) <= 1 and abs(pr - linha) <= 1:
                problemas.append(
                    f"spawn sobreposto — '{nome}' cola no tile de passagem ({pr},{pc})"
                )

    for (pr, pc) in PASSAGENS:
        if g.g[pr][pc] in constants.SOLID_TILES:
            problemas.append(f"passagem ({pr},{pc}) marcada num tile solido")
        if g.g[pr + 1][pc] not in constants.SOLID_TILES:
            problemas.append(f"passagem ({pr},{pc}) sem chao embaixo — inalcancavel")

    return problemas


# ════════════════════════════════════════════════════════════════════════
# GRAVAÇÃO PROTEGIDA DOS CSVs
#
# Os CSVs de setor são o FORMATO DE EDIÇÃO do mapa: o professor/aluno pode
# abri-los no Excel, LibreOffice ou num editor e mudar blocos à mão. Antes,
# rodar este gerador sobrescrevia tudo em silêncio — foi assim que a edição
# manual em caverna.csv deixou de "valer" (e o teste_mapa a acusava como
# erro). Agora:
#
#   * assets/levels/setores/_gerado.json guarda a impressão digital da GRADE
#     (não do texto: salvar no Excel sem mudar nada não conta como edição)
#     que este gerador gravou da última vez;
#   * se o CSV em disco ainda é aquela grade (ou não existe), ele é
#     atualizado normalmente;
#   * se foi editado à mão, ele NÃO é tocado: a versão nova do gerador vai
#     para assets/levels/gerados/<setor>.csv, e o terminal avisa;
#   * --sobrescrever força a troca, guardando antes uma cópia em
#     assets/levels/backup/.
#
# Formato gravado: separador ";" e UTF-8 com BOM — abre direto no Excel em
# português. O jogo lê também vírgula (ver src/dados_csv.py).
# ════════════════════════════════════════════════════════════════════════
def impressao_digital(grade):
    import hashlib
    texto = "\n".join(",".join(str(v) for v in linha) for linha in grade)
    return hashlib.sha256(texto.encode("ascii")).hexdigest()


def _ler_grade_existente(caminho):
    from src.nucleo.utils import carregar_nivel_csv
    try:
        return carregar_nivel_csv(str(caminho))
    except Exception:  # noqa: BLE001 - arquivo ilegível conta como "editado"
        return None


def escrever_csv_grade(caminho, grade):
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f, delimiter=";").writerows(grade)


def gravar_setores(raiz, grades, sobrescrever=False):
    import datetime
    import json
    import shutil

    pasta = raiz / "assets" / "levels" / constants.PASTA_SETORES
    pasta.mkdir(parents=True, exist_ok=True)
    manifesto_path = pasta / "_gerado.json"
    try:
        manifesto = json.loads(manifesto_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        manifesto = {}

    protegidos = []
    for nome, grade in grades.items():
        arquivo = constants.SETORES[nome]["arquivo"]
        destino = pasta / arquivo
        nova = impressao_digital(grade)
        if destino.exists():
            atual_grade = _ler_grade_existente(destino)
            atual = impressao_digital(atual_grade) if atual_grade else None
            if atual == nova:
                manifesto[arquivo] = nova
                print(f"Sem mudancas  {destino.name}")
                continue
            editado = atual != manifesto.get(arquivo)
            if editado and not sobrescrever:
                pasta_ger = raiz / "assets" / "levels" / "gerados"
                pasta_ger.mkdir(parents=True, exist_ok=True)
                escrever_csv_grade(pasta_ger / arquivo, grade)
                protegidos.append(arquivo)
                print(f"PROTEGIDO     {destino.name}: foi editado a mao e NAO foi "
                      f"sobrescrito. Versao do gerador em levels/gerados/{arquivo}")
                continue
            if editado:
                pasta_bkp = raiz / "assets" / "levels" / "backup"
                pasta_bkp.mkdir(parents=True, exist_ok=True)
                carimbo = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                copia = pasta_bkp / f"{destino.stem}_{carimbo}.csv"
                shutil.copy2(destino, copia)
                print(f"Backup        {destino.name} -> {copia}")
        escrever_csv_grade(destino, grade)
        manifesto[arquivo] = nova
        print(f"Gravado       {destino}  ({len(grade)} x {len(grade[0])})")

    manifesto_path.write_text(json.dumps(manifesto, indent=2, sort_keys=True),
                              encoding="utf-8")
    if protegidos:
        print("\nArquivos editados a mao preservados: " + ", ".join(protegidos))
        print("Use  python gerar_mundo.py --sobrescrever  para trocar pela versao "
              "do gerador (com backup).")
    return protegidos


if __name__ == "__main__":
    # Marcadores ANTES da validacao, de proposito: assim a validacao ve a
    # grade exatamente como ela vai para o disco, e um marcador carimbado
    # em cima de bloco solido aparece no relatorio em vez de virar bug.
    n_marcadores = carimbar_marcadores()
    problemas = validar()
    # Regras de ENCONTRO (espacamento, distancia de onde o jogador chega).
    # A geometria sozinha nao pega isso: dois inimigos colados formam um
    # mapa geometricamente valido e injogavel.
    problemas += validar_encontros(CELULA_CHEGADA)
    solidas = sum(1 for linha in g.g for v in linha if v in constants.SOLID_TILES)
    comps = val.componentes_de_terreno(g.g)
    print(f"Mapa: {COLS} colunas x {ROWS} linhas   "
          f"({100 * solidas / (ROWS * COLS):.0f}% solido)")
    print(f"Largura por regiao: floresta {FLOR_C1 - FLOR_C0 + 1} "
          f"({100 * (FLOR_C1 - FLOR_C0 + 1) / COLS:.0f}%), "
          f"caverna {CAV_C1 - CAV_C0 + 1}, copas {COP_C1 - COP_C0 + 1}")
    print(f"Componentes de terreno: {len(comps)}  (maior: {len(comps[0])} tiles)")
    print(f"Inimigos: {len(inimigos)}   Minerios: {len(minerios)}   "
          f"Passagens: {len(PASSAGENS)}")
    print(f"Marcadores carimbados no CSV: {n_marcadores}")
    print(f"Area do boss: colunas {AREA_BOSS['c0']}-{AREA_BOSS['c1']}, "
          f"chao na linha {AREA_BOSS['linha_chao']}")
    print(f"Encontros: {len(ENCONTROS)}   "
          f"(mobs por encontro: "
          f"{[len(e['mobs']) for e in ENCONTROS]})")

    grades = fatiar_setores()
    problemas += validar_ligacoes(grades)
    print("Setores: " + ", ".join(f"{n} {len(gr[0])} col" for n, gr in grades.items()))

    if not val.relatorio(problemas, "VALIDACAO DO MAPA GERADO"):
        raise SystemExit("Mapa NAO gravado — corrija os problemas acima.")

    raiz = Path(__file__).resolve().parents[2]
    faixas = faixas_dos_setores()
    gravar_setores(raiz, grades, sobrescrever="--sobrescrever" in sys.argv)

    def _local(nome, col):
        return col - faixas[nome][0]

    ab = dict(AREA_BOSS)
    off = faixas["arena"][0]
    ab["c0"] -= off
    ab["c1"] -= off
    ab["marcador"] = (ab["marcador"][0] - off, ab["marcador"][1])

    destino_py = raiz / "src" / "nivel_dados.py"
    with open(destino_py, "w", encoding="utf-8") as f:
        f.write('"""\n')
        f.write("ARQUIVO GERADO por gerar_mundo.py — nao editar a mao.\n\n")
        f.write("Rode `python gerar_mundo.py` para regerar este arquivo junto com os\n")
        f.write("CSVs de assets/levels/setores/. Tudo aqui esta em coordenadas LOCAIS\n")
        f.write("de cada setor (coluna 0 = primeira coluna do CSV do setor).\n\n")
        f.write("A posicao de player, inimigos, minerios, passagens e chegadas NAO\n")
        f.write("mora aqui: vem dos marcadores dos proprios CSVs (ver MAPA-CSV.md).\n")
        f.write('"""\n\n')
        f.write(f"PLAYER_SPAWN = {PLAYER_SPAWN!r}  # (coluna, linha da superficie) no setor inicial\n\n")
        f.write("# Ponto de entrada de cada setor, usado pela validacao de alcance.\n")
        f.write("SETORES_GERADOS = {\n")
        for nome, r in REGIOES.items():
            info = {"colunas": faixas[nome][1] - faixas[nome][0] + 1, "linhas": ROWS,
                    "entrada_col": _local(nome, r["entrada_col"]),
                    "entrada_row": r["entrada_row"]}
            f.write(f"    {nome!r}: {info!r},\n")
        f.write("}\n\n")
        f.write("# Arena do boss (coordenadas do setor 'arena').\n")
        f.write(f"AREA_BOSS = {ab!r}\n")
    print(f"Gravado {destino_py}")

    antigo = raiz / "assets" / "levels" / "level1_mapa.csv"
    if antigo.exists():
        antigo.unlink()
        print(f"Removido {antigo} (substituido pelos CSVs de setor)")