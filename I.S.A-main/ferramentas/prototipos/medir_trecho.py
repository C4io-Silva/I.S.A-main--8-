"""
PROTÓTIPO — mede o dano num trecho curto, com IA e física reais (relógio simulado).
A Areninha caminha de col_ini até col_fim (pula sozinha quando trava num degrau, como uma
criança), repetindo com N defasagens diferentes dos inimigos (espera k·passo quadros antes
de sair). Mods de terreno opcionais em memória (o CSV não muda).

uso (na raiz):  python ferramentas/prototipos/medir_trecho.py caverna 92 108 [--linha-ref 28]
                [--mods "30,100,-1;..."] [--n 12] [--passo 17]
"""
import os, sys, tempfile, argparse
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["ISA_DB"] = os.path.join(tempfile.mkdtemp(prefix="isa_trecho_"), "e.db")
from pathlib import Path
RAIZ = str(Path(__file__).resolve().parents[2]); sys.path.insert(0, RAIZ); os.chdir(RAIZ)
ap = argparse.ArgumentParser()
ap.add_argument("setor"); ap.add_argument("ini", type=int); ap.add_argument("fim", type=int)
ap.add_argument("--linha-ref", type=int, default=10); ap.add_argument("--mods", default="")
ap.add_argument("--n", type=int, default=12); ap.add_argument("--passo", type=int, default=17)
a = ap.parse_args()
import pygame
_t = [10_000]; pygame.time.get_ticks = lambda: _t[0]
from src.nucleo import constants
from src.nucleo import utils
if a.mods:
    _orig = utils.carregar_nivel_csv
    mods = [tuple(int(x) for x in m.split(",")) for m in a.mods.split(";") if m]
    def _mod(caminho, *k, **kw):
        g = _orig(caminho, *k, **kw)
        if os.path.basename(str(caminho)).startswith(a.setor):
            for l, c, v in mods: g[l][c] = v
        return g
    utils.carregar_nivel_csv = _mod
sys.path.insert(0, os.path.join(os.getcwd(), "testes")); from compat_main import M  # fachada: API antiga sobre src/jogo
if a.mods:
    import src.mundo.setores as _S; _S.carregar_nivel_csv = utils.carregar_nivel_csv
from src.sistemas.joystick import GerenciadorJoystick
T = constants.TILE_SIZE; S = constants.SOLID_TILES
pygame.init(); M.configurar_janela(); M.clock = pygame.time.Clock(); M.gamepad = GerenciadorJoystick(); M.recriar_ui()

def passo(d):
    _t[0] += 16; M.moving_left, M.moving_right = d < 0, d > 0; M.estado_jogo = "JOGANDO"; M.atualizar_jogando(16)

def rodar(espera):
    M.iniciar_jogo(); M.ativar_setor(a.setor); M.itens[:] = []; M.estado_jogo = "JOGANDO"
    p = M.player; p.player_health = 1000; p.invulnerable = False
    g = M.setor_atual.grade
    for l in range(a.linha_ref, len(g)):
        if g[l][a.ini] in S and g[l - 1][a.ini] not in S:
            break
    p.rect.centerx = a.ini * T + T // 2; p.rect.bottom = l * T; p.pos_x, p.pos_y = float(p.rect.x), float(p.rect.y); p.vel_y = 0
    M.atualizar_camera(instantaneo=True)
    for _ in range(espera): passo(0)
    d = 1 if a.fim > a.ini else -1; golpes = 0; vida = p.player_health; parado = 0; x_ant = p.rect.x
    for i in range(1500):
        if d and p.rect.x == x_ant:
            parado += 1
            if parado >= 3: M.jump_pressed = True; parado = 0
        else:
            parado = 0
        x_ant = p.rect.x
        passo(d)
        if p.player_health < vida: golpes += 1
        vida = p.player_health
        if (p.rect.centerx // T - a.fim) * d >= 0:
            return golpes, i, True
    return golpes, 1500, False

res = [rodar(k * a.passo) for k in range(a.n)]
com = sum(1 for g, _, _ in res if g); tot = sum(g for g, _, _ in res); ok = sum(1 for *_, c in res if c)
print(f"{a.setor} {a.ini}->{a.fim} mods=[{a.mods or '-'}] | chegou {ok}/{a.n} | levou dano em {com}/{a.n} | golpes {tot} | por tentativa {[g for g, _, _ in res]}")
