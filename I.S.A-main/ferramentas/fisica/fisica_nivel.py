"""
fisica_nivel.py — núcleo de simulação com a FÍSICA REAL da Areninha.

Usado por:
    ferramentas/validar_fisica_real.py   (validador de mapas)
    ferramentas/medir_fisica.py          (medidas para level design)
    ferramentas/gerar_mapas_tecnicos.py  (imagens de docs/MAPAS_TECNICOS)
    testes/teste_validador_fisica.py     (controle pulo duplo x pulo simples)

Nada aqui reimplementa a física: cada quadro chama `Character.move` e
`Character.jump` de src/character.py, com os obstáculos de `World` montados
a partir do CSV (mesmo `constants.SOLID_TILES`). A única regra copiada é a
parede invisível das bordas laterais (`Partida.limitar_ao_setor`), que
são 6 linhas; `testes/teste_validador_fisica.py` confere que as duas
continuam iguais.

Modelo de busca
---------------
Um NÓ é a Areninha parada em pé no chão (posição x arredondada para QUANT px e
a base do retângulo). De cada nó saem MACRO-AÇÕES — sequências de teclas
quadro a quadro: andar um pouco, cair de uma borda, pular, pular duas vezes
(segundo pulo em 6 momentos diferentes, do quadro 6 ao 40), soltar ou inverter a direção no ar.
A trajetória é simulada até ela pousar de novo (novo nó) ou cair para fora do
mapa. Tudo o que o retângulo dela encosta em QUALQUER quadro (minério, maçã,
área de uma passagem) conta como alcançado, que é exatamente como o jogo
coleta e interage.

A busca é feita em camadas (largura), então o caminho guardado até cada nó é
o de menos macro-ações — usado para desenhar as rotas nos mapas técnicos.
"""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

QUANT = 12          # px: resolução dos nós em x (1/4 de tile)
MAX_QUADROS = 320   # limite de uma macro-ação (5,3 s de jogo)
PENALIDADE_PULO = 30  # custo extra por pulo nas rotas "naturais" (prefere andar quando dá)


# ── pygame mínimo ─────────────────────────────────────────────────────────────
def iniciar_pygame():
    """Janela invisível 1x1: o Character precisa de display para convert_alpha."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    import pygame
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1, 1))
    return pygame


# ── leitura do mapa ───────────────────────────────────────────────────────────
def ler_setor(nome):
    """(grade_terreno, marcadores) de um setor, lidos com as funções do jogo."""
    from src.nucleo import constants
    from src.nucleo.utils import carregar_nivel_csv, extrair_marcadores
    grade = carregar_nivel_csv(os.path.join(constants.PASTA_SETORES,
                                            constants.SETORES[nome]["arquivo"]))
    marcadores = extrair_marcadores(grade)   # apaga os marcadores da grade
    return grade, marcadores


def superficies(grade):
    """Células sólidas com a célula de cima livre: onde dá para ficar em pé."""
    from src.nucleo import constants
    S = constants.SOLID_TILES
    return {(l, c) for l in range(1, len(grade)) for c in range(len(grade[l]))
            if grade[l][c] in S and grade[l - 1][c] not in S}


# ── macro-ações ──────────────────────────────────────────────────────────────
def macros():
    """Lista fixa de macro-ações: (tipo, dir, quadros_de_pulo, troca_em, nova_dir)."""
    ms = []
    for d in (-1, 0, 1):
        for J in ((0,), (0, 6), (0, 12), (0, 18), (0, 24), (0, 32), (0, 40)):
            trocas = [(None, d)]
            for s in (12, 24):
                for d2 in ((0, -d) if d else (-1, 1)):
                    trocas.append((s, d2))
            for s, d2 in trocas:
                ms.append(("pulo", d, J, s, d2))
    for d in (-1, 1):
        ms.append(("anda", d, (), None, d))
        for J in ((), (0,), (8,), (0, 8), (8, 18), (0, 30)):
            for s, d2 in ((None, d), (10, 0), (10, -d)):
                ms.append(("borda", d, J, s, d2))
    return ms


MACROS = macros()


def macro_usa_pulo_duplo(m):
    """Macro com dois pulos (ou queda de borda + dois pulos no ar)."""
    return len(m[2]) >= 2


# ── simulador ────────────────────────────────────────────────────────────────
class Simulador:
    """A Areninha real (Character) num World montado a partir de uma grade."""

    def __init__(self, grade, pulos=2):
        pygame = iniciar_pygame()
        from src.nucleo import constants
        from src.entidades.character import Character
        from src.mundo.world import World
        self.T = constants.TILE_SIZE
        self.speed = constants.PLAYER_SPEED
        ids = {v for linha in grade for v in linha if v >= 0}
        bloco = pygame.Surface((self.T, self.T))
        self.world = World()
        self.world.process_data(grade, {i: bloco for i in ids}, bloco)
        self.grade = grade
        self.largura = self.world.colunas * self.T
        self.altura = self.world.linhas * self.T
        self.p = Character(0, 0, constants.PLAYER_SIZE, constants.PLAYER_SPEED,
                           None, constants.PLAYER_HEALTH)
        self.p.MAX_JUMPS = pulos            # atributo de instância: só este simulador
        self.p.jumps_left = pulos
        self.pulos = pulos

    # cópia exata de Partida.limitar_ao_setor (conferida no teste)
    def limitar(self):
        p = self.p
        if p.rect.left < 0:
            p.rect.left = 0
            p.pos_x = float(p.rect.x)
        elif p.rect.right > self.largura:
            p.rect.right = self.largura
            p.pos_x = float(p.rect.x)

    def passo(self, sinal, pular):
        """Um quadro de jogo: mesma ordem de main._movimento_do_player + atualizar_jogando."""
        if pular:
            self.p.jump()
        self.p.move(sinal * self.speed, self.world.obstaculos_proximos(self.p.rect, margem=1))
        self.limitar()

    def estado(self):
        p = self.p
        return (p.pos_x, p.pos_y, p.rect.x, p.rect.y, p.vel_y, p.jumps_left, p.on_ground)

    def restaurar(self, e):
        p = self.p
        p.pos_x, p.pos_y, p.rect.x, p.rect.y, p.vel_y, p.jumps_left, p.on_ground = e
        p.preso = False

    def colocar(self, col, linha_base):
        """Como main._assentar / _resolver_passagem: centro da coluna, base na linha."""
        p = self.p
        p.rect.centerx = col * self.T + self.T // 2
        p.rect.bottom = linha_base * self.T
        p.pos_x, p.pos_y = float(p.rect.x), float(p.rect.y)
        p.vel_y = 0.0
        p.on_ground = False
        p.jumps_left = p.MAX_JUMPS

    def dentro_de_bloco(self):
        return any(self.p.rect.colliderect(r)
                   for r in self.world.obstaculos_proximos(self.p.rect, margem=1))

    def assentar(self, max_quadros=600):
        """Deixa cair até pousar. Devolve (ok, quadros, queda_px)."""
        y0 = self.p.rect.bottom
        for q in range(max_quadros):
            self.passo(0, False)
            if self.p.on_ground:
                return True, q + 1, self.p.rect.bottom - y0
            if self.p.rect.top > self.altura:
                return False, q + 1, None
        return self.p.on_ground, max_quadros, self.p.rect.bottom - y0

    def simular(self, inicio, m, alvos=(), trajeto=False):
        """
        Executa a macro `m` a partir do estado `inicio`.
        alvos: lista de Rects; devolve os índices tocados em algum quadro.
        Retorno: (estado_final_em_pe | None, tocados:set, pontos:list|None)
        """
        tipo, d, J, s, d2 = m
        self.restaurar(inicio)
        p = self.p
        tocados = set()
        pontos = [p.rect.center] if trajeto else None
        x0 = p.rect.x
        t_ar = None
        self.quadros = 0
        for f in range(MAX_QUADROS):
            self.quadros = f + 1
            if tipo == "pulo":
                ref = f
            else:
                if t_ar is None and not p.on_ground and f > 0:
                    t_ar = f
                ref = None if t_ar is None else f - t_ar
            dd = d if (s is None or ref is None or ref < s) else d2
            pular = ref is not None and ref in J
            self.passo(dd, pular)
            r = p.rect
            if alvos:
                for i, a in enumerate(alvos):
                    if a.colliderect(r):
                        tocados.add(i)
            if trajeto:
                pontos.append(r.center)
            if r.top > self.altura:
                return None, tocados, pontos
            if tipo == "anda":
                if not p.on_ground:
                    return None, tocados, pontos     # coberto pelas macros "borda"
                if abs(r.x - x0) >= QUANT or f >= 6:
                    return self.estado(), tocados, pontos
                continue
            if tipo == "borda" and t_ar is None:
                if f > 40:
                    return None, tocados, pontos     # não havia borda perto
                continue
            if f >= 1 and p.on_ground and (ref is None or ref >= 1):
                return self.estado(), tocados, pontos
        return (self.estado() if p.on_ground else None), tocados, pontos


def chave(e):
    return (int(e[2]) // QUANT, int(e[3]))


# ── busca (opcionalmente em vários processos) ────────────────────────────────
_SIM = None
_ALVOS = None


def _iniciar_trabalhador(grade, pulos, alvos_tuplas):
    global _SIM, _ALVOS
    iniciar_pygame()
    import pygame
    _SIM = Simulador(grade, pulos)
    _ALVOS = [pygame.Rect(*t) for t in alvos_tuplas]


def _expandir(item):
    k, e = item
    saidas = []
    _SIM.restaurar(e)
    r = _SIM.p.rect
    em_pe = {i for i, a in enumerate(_ALVOS) if a.colliderect(r)}
    for mi, m in enumerate(MACROS):
        fim, toc, _ = _SIM.simular(e, m, _ALVOS)
        saidas.append((mi, fim, tuple(sorted(toc)), _SIM.quadros))
    return k, em_pe, saidas


class Grafo:
    """Resultado da busca: nós, arestas, profundidade e o que foi tocado."""

    def __init__(self):
        self.nos = {}          # chave -> estado
        self.pai = {}          # chave -> (chave_pai, indice_macro) | None
        self.prof = {}         # chave -> nº de macro-ações desde a entrada
        self.arestas = {}      # chave -> {chave_destino: [indices de macro]}
        self.toque = {}        # alvo -> (chave_origem, indice_macro | None) do 1º toque
        self.toques_no = {}    # chave -> set(alvos tocados saindo dela ou em pé nela)
        self.chegadas = {}     # chave -> nº de (origem, macro) distintos que pousam ali
        self.custo = {}        # (chave, chave_destino) -> (custo, macro): menor custo (quadros + pulos)
        self.toque_custo = {}  # (chave, alvo) -> (custo, macro|None): macro mais barata que toca o alvo

    def alcancados(self):
        return set(self.toque)


def explorar(grade, entradas, alvos, pulos=2, processos=1, progresso=None):
    """
    BFS a partir de `entradas` (lista de estados em pé).
    alvos: lista de pygame.Rect (minérios, maçãs, áreas de passagem...).
    """
    iniciar_pygame()
    g = Grafo()
    fronteira = []
    for e in entradas:
        k = chave(e)
        if k not in g.nos:
            g.nos[k] = e
            g.pai[k] = None
            g.prof[k] = 0
            fronteira.append(k)
    tuplas = [tuple(a) for a in alvos]
    pool = None
    if processos and processos > 1:
        import multiprocessing as mp
        pool = mp.get_context("spawn").Pool(processos, _iniciar_trabalhador,
                                             (grade, pulos, tuplas))
    else:
        _iniciar_trabalhador(grade, pulos, tuplas)
    try:
        nivel = 0
        while fronteira:
            itens = [(k, g.nos[k]) for k in sorted(fronteira)]
            if pool:
                resultados = pool.map(_expandir, itens, chunksize=max(1, len(itens) // (processos * 4) or 1))
            else:
                resultados = [_expandir(i) for i in itens]
            nova = []
            for k, em_pe, saidas in sorted(resultados, key=lambda r: r[0]):
                toc_no = set(em_pe)
                for a in em_pe:
                    g.toque.setdefault(a, (k, None))
                destinos = g.arestas.setdefault(k, {})
                for a in em_pe:
                    g.toque_custo[(k, a)] = (0, None)
                for mi, fim, toc, quadros in saidas:
                    custo = quadros + PENALIDADE_PULO * len(MACROS[mi][2])
                    toc_no.update(toc)
                    for a in toc:
                        g.toque.setdefault(a, (k, mi))
                        if custo < g.toque_custo.get((k, a), (1e9,))[0]:
                            g.toque_custo[(k, a)] = (custo, mi)
                    if fim is None:
                        continue
                    k2 = chave(fim)
                    destinos.setdefault(k2, []).append(mi)
                    if custo < g.custo.get((k, k2), (1e9,))[0]:
                        g.custo[(k, k2)] = (custo, mi)
                    g.chegadas[k2] = g.chegadas.get(k2, 0) + 1
                    if k2 not in g.nos:
                        g.nos[k2] = fim
                        g.pai[k2] = (k, mi)
                        g.prof[k2] = nivel + 1
                        nova.append(k2)
                g.toques_no[k] = toc_no
            nivel += 1
            fronteira = nova
            if progresso:
                progresso(nivel, len(g.nos))
    finally:
        if pool:
            pool.close()
            pool.join()
    return g


def caminho_ate(g, k):
    """Lista [(chave_origem, macro)] da entrada até o nó k."""
    passos = []
    while g.pai.get(k):
        k0, mi = g.pai[k]
        passos.append((k0, mi))
        k = k0
    return list(reversed(passos))


def rota_natural(g, entradas_chaves, alvo):
    """
    Caminho de menor custo (quadros de jogo + PENALIDADE_PULO por pulo) da
    entrada até tocar `alvo`. Devolve [(chave, macro|None)], ou None.
    """
    import heapq
    dist = {k: 0 for k in entradas_chaves}
    ant = {}
    fila = [(0, k) for k in entradas_chaves]
    heapq.heapify(fila)
    toques = {}
    for (k, a), (c, mi) in g.toque_custo.items():
        if a == alvo:
            toques[k] = (c, mi)
    melhor, fim = None, None
    while fila:
        d, k = heapq.heappop(fila)
        if d > dist.get(k, 1e18):
            continue
        if melhor is not None and d >= melhor:
            break
        if k in toques:
            total = d + toques[k][0]
            if melhor is None or total < melhor:
                melhor, fim = total, k
        for k2 in g.arestas.get(k, {}):
            c, mi = g.custo[(k, k2)]
            if d + c < dist.get(k2, 1e18):
                dist[k2] = d + c
                ant[k2] = (k, mi)
                heapq.heappush(fila, (d + c, k2))
    if fim is None:
        return None
    passos = []
    if toques[fim][1] is not None:
        passos.append((fim, toques[fim][1]))
    k = fim
    while k in ant:
        k0, mi = ant[k]
        passos.append((k0, mi))
        k = k0
    return list(reversed(passos))


def sem_saida(g, alvos_saida):
    """Nós dos quais não se chega a nenhum nó que toque um alvo de `alvos_saida`."""
    bons = {k for k, t in g.toques_no.items() if t & alvos_saida}
    reverso = {}
    for a, dests in g.arestas.items():
        for b in dests:
            reverso.setdefault(b, set()).add(a)
    salvos = set(bons)
    pilha = list(bons)
    while pilha:
        b = pilha.pop()
        for a in reverso.get(b, ()):
            if a not in salvos:
                salvos.add(a)
                pilha.append(a)
    return sorted(k for k in g.nos if k not in salvos)


def componentes(g):
    """Componentes fortemente conexas do grafo (regiões onde se vai e volta)."""
    nos = list(g.nos)
    adj = {k: list(g.arestas.get(k, {})) for k in nos}
    rev = {k: [] for k in nos}
    for a, bs in adj.items():
        for b in bs:
            if b in rev:
                rev[b].append(a)
    ordem, vis = [], set()
    for s in nos:
        if s in vis:
            continue
        pilha = [(s, iter(adj[s]))]
        vis.add(s)
        while pilha:
            v, it = pilha[-1]
            for w in it:
                if w not in vis and w in adj:
                    vis.add(w)
                    pilha.append((w, iter(adj[w])))
                    break
            else:
                ordem.append(v)
                pilha.pop()
    comp, cid = {}, 0
    for s in reversed(ordem):
        if s in comp:
            continue
        pilha = [s]
        comp[s] = cid
        while pilha:
            v = pilha.pop()
            for w in rev[v]:
                if w not in comp:
                    comp[w] = cid
                    pilha.append(w)
        cid += 1
    return comp


def alcancaveis_de(g, inicio):
    vis, pilha = set(inicio), list(inicio)
    while pilha:
        a = pilha.pop()
        for b in g.arestas.get(a, {}):
            if b not in vis:
                vis.add(b)
                pilha.append(b)
    return vis


def superficies_pisadas(g, sim):
    """Células de superfície sob os pés de algum nó."""
    T = sim.T
    pisadas = set()
    for e in g.nos.values():
        sim.restaurar(e)
        r = sim.p.rect
        l = r.bottom // T
        for c in range(r.left // T, (r.right - 1) // T + 1):
            pisadas.add((l, c))
    return pisadas
