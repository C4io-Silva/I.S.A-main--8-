"""Renderiza cada setor em 3 visões: 1) só a camada física, 2) só a camada
decorativa (+ estruturas), 3) as duas combinadas com o background original.

uso (na raiz do projeto):
    python ferramentas/redesign_mapas/renderizar_camadas.py . all saida_renders 0.5 --grid

Usa as classes do próprio jogo (Setor, World, GerenciadorAmbientes, passagens)
e a ordem de partida/render.desenhar_cena: fundo -> estruturas -> decoração -> tiles ->
passagens -> entidades -> atmosfera. Na visão física, tiles desenhados SEM
colisão (ex.: escora 67) aparecem com contorno magenta.
"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
_CWD0 = os.getcwd(); GAME = os.path.abspath(sys.argv[1]); sys.path.insert(0, GAME); os.chdir(GAME)
import pygame
pygame.init(); pygame.display.set_mode((800, 600))
from src.nucleo import constants
from src.nucleo.utils import carregar_tiles
from src.mundo.setores import Setor
from src.mundo.ambientes import GerenciadorAmbientes

alvo, saida = sys.argv[2], sys.argv[3]
saida = saida if os.path.isabs(saida) else os.path.join(_CWD0, saida)
escala = float(sys.argv[4]) if len(sys.argv) > 4 and not sys.argv[4].startswith('--') else 0.5
grid = '--grid' in sys.argv
T = constants.TILE_SIZE
tiles, fb = carregar_tiles(constants.TILE_SPRITES, T, constants.TILE_FALLBACK_ID)
os.makedirs(saida, exist_ok=True)

def entidades(setor, surf):
    for e in setor.inimigos:
        e.draw(surf, 0, 0)
    for i in setor.itens: i.draw(surf, 0, 0)
    for c in setor.curas: c.draw(surf, 0, 0)
    if setor.player_spawn:
        c, l = setor.player_spawn
        pygame.draw.rect(surf, (255, 230, 0), (c*T+9, l*T-45, 30, 45), 3)
    for cid, (c, l) in setor.chegadas.items():
        pygame.draw.rect(surf, (0, 255, 255), (c*T+9, l*T+3, 30, 45), 3)

def grade(surf, setor):
    f = pygame.font.SysFont(None, 18)
    for c in range(0, setor.world.colunas, 5):
        pygame.draw.line(surf, (255,255,255,90) if c % 10 else (255,80,80,160), (c*T, 0), (c*T, surf.get_height()), 1)
        if c % 10 == 0: surf.blit(f.render(str(c), True, (255,255,255)), (c*T+2, 2))
    for l in range(0, setor.world.linhas, 5):
        pygame.draw.line(surf, (255,255,255,90), (0, l*T), (surf.get_width(), l*T), 1)
        surf.blit(f.render(str(l), True, (255,255,255)), (2, l*T+2))

def fundo(setor, W, H):
    surf = pygame.Surface((W, H))
    amb = GerenciadorAmbientes(800, 600); amb.forcar(setor.ambiente)
    tela = pygame.Surface((800, 600))
    for cy in range(0, H, 600):
        for cx in range(0, W, 800):
            amb.desenhar(tela, cx, None, cy)
            surf.blit(tela, (cx, cy))
    return surf, amb

def atmosfera(amb, surf):
    a = amb.ambientes[amb.nome_atual]
    if a.tint != (255,255,255):
        s = pygame.Surface(surf.get_size()); s.fill(a.tint); surf.blit(s, (0,0), special_flags=pygame.BLEND_RGB_MULT)
    if a.luz != (0,0,0):
        s = pygame.Surface(surf.get_size()); s.fill(a.luz); surf.blit(s, (0,0), special_flags=pygame.BLEND_RGB_ADD)

def salvar(surf, nome):
    w, h = surf.get_size()
    out = pygame.transform.smoothscale(surf, (int(w*escala), int(h*escala))) if escala != 1 else surf
    pygame.image.save(out, os.path.join(saida, nome))

nomes = list(constants.SETORES) if alvo == 'all' else alvo.split(',')
for nome in nomes:
    setor = Setor(nome, constants.SETORES[nome], tiles, fb)
    W, H = setor.largura_px, setor.altura_px
    # 1. fisica
    s1 = pygame.Surface((W, H)); s1.fill((40, 44, 52))
    for y in range(setor.world.linhas):
        for x in range(setor.world.colunas):
            img = setor.world._sprites[y][x]
            if img is not None:
                s1.blit(img, (x*T, y*T))
                if setor.world._solidos[y][x] is None:  # visual nao-solido na camada fisica
                    pygame.draw.rect(s1, (255, 0, 255), (x*T, y*T, T, T), 2)
    setor.passagens.desenhar(s1, 0, 0); entidades(setor, s1)
    if grid: grade(s1, setor)
    salvar(s1, f"{nome}_1_fisica.png")
    # 2. decorativa
    s2 = pygame.Surface((W, H), pygame.SRCALPHA); s2.fill((40, 44, 52, 255))
    for rect, spr in setor.estruturas.itens: s2.blit(spr, rect.topleft)
    for y, row in enumerate(setor.decoracoes.grade):
        for x, v in enumerate(row):
            spr = setor.decoracoes.sprites.get(v)
            if spr: s2.blit(spr, (x*T, y*T))
    if grid: grade(s2, setor)
    salvar(s2, f"{nome}_2_decor.png")
    # 3. combinada, ordem real do jogo
    s3, amb = fundo(setor, W, H)
    for rect, spr in setor.estruturas.itens: s3.blit(spr, rect.topleft)
    for y, row in enumerate(setor.decoracoes.grade):
        for x, v in enumerate(row):
            spr = setor.decoracoes.sprites.get(v)
            if spr: s3.blit(spr, (x*T, y*T))
    for y in range(setor.world.linhas):
        for x in range(setor.world.colunas):
            img = setor.world._sprites[y][x]
            if img is not None: s3.blit(img, (x*T, y*T))
    setor.passagens.desenhar(s3, 0, 0); entidades(setor, s3); atmosfera(amb, s3)
    if grid: grade(s3, setor)
    salvar(s3, f"{nome}_3_combinada.png")
    print("ok", nome, W, H)
