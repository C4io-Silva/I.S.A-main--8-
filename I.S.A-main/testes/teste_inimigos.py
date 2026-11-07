"""
Teste do pisão: pular na cabeça derrota cobra, tucano e aranha; encostar de
lado machuca o jogador; o boss não morre com pisão.

Roda o código real da partida (main.atualizar_jogando). Os inimigos testados
ficam parados (update desligado só neles) para o teste medir a COLISÃO, não
a IA de perseguição.

Uso (a partir da raiz do projeto):
    python testes/teste_inimigos.py
"""
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("ISA_DB", os.path.join(tempfile.mkdtemp(prefix="isa_teste_"), "estatisticas.db"))
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

import pygame  # noqa: E402

from src.nucleo import constants  # noqa: E402
from compat_main import M  # noqa: E402
from src.entidades.enemies import Aranha, Enemy, Gorila, Tucano  # noqa: E402
from src.sistemas.joystick import GerenciadorJoystick  # noqa: E402

T = constants.TILE_SIZE


def ok(msg):
    print("ok:", msg)


def preparar():
    pygame.init()
    M.configurar_janela()
    M.clock = pygame.time.Clock()
    M.gamepad = GerenciadorJoystick()
    M.recriar_ui()
    M.iniciar_jogo()


def _parar(inimigo):
    inimigo.update = lambda *a, **k: None


def _primeiro(setor, classe):
    M.ativar_setor(setor)
    alvo = next(e for e in M.enemies if type(e) is classe)
    _parar(alvo)
    return alvo


def _cair_em_cima(alvo, altura_tiles=3, vel_inicial=0.0):
    p = M.player
    p.player_health = constants.PLAYER_HEALTH
    p.invulnerable = False
    p.preso = False
    p.rect.centerx = alvo.rect.centerx
    p.rect.bottom = alvo.rect.top - int(altura_tiles * T)
    p.pos_x, p.pos_y = float(p.rect.x), float(p.rect.y)
    p.vel_y = vel_inicial
    M.reiniciar_movimento()
    M.atualizar_camera(instantaneo=True)
    for _ in range(180):
        M.atualizar_jogando(16)
        if alvo.derrotado or p.player_health < constants.PLAYER_HEALTH:
            break


def _vao_aberto(altura_tiles):
    """(coluna, linha_do_chao) do primeiro trecho do setor ativo com pelo menos
    `altura_tiles` células livres em cima de um bloco sólido."""
    g = M.setor_atual.grade
    for c in range(2, len(g[0]) - 2):
        for l in range(altura_tiles, len(g)):
            if g[l][c] in constants.SOLID_TILES and all(
                    g[l - k][c] not in constants.SOLID_TILES for k in range(1, altura_tiles + 1)):
                return c, l
    raise AssertionError("setor sem vão aberto para o teste")


def teste_pisao_mata(setor, classe, nome, descer_tiles=0, **kw):
    alvo = _primeiro(setor, classe)
    if descer_tiles:
        # A aranha vive colada no teto: o pisão acontece quando ela desceu
        # pelo fio (para pegar o jogador) e ele pula por cima dela.
        # Antes o teste descia a aranha `descer_tiles` a partir de onde ela
        # nasce, o que só funciona se o mapa tiver esse espaço embaixo dela
        # (na caverna v0.4 as aranhas ficam a ~3 tiles do chão e ela ia parar
        # dentro do piso). Agora a cena é montada num vão aberto do próprio
        # setor: a aranha fica `descer_tiles` acima do chão e a Areninha cai
        # de cima dela. A mecânica testada (pisão mata a aranha) é a mesma.
        col, chao = _vao_aberto(descer_tiles + 4)
        alvo.rect.centerx = col * T + T // 2
        alvo.rect.bottom = (chao - descer_tiles) * T
        alvo.pos_x, alvo.pos_y = float(alvo.rect.x), float(alvo.rect.y)
        if hasattr(alvo, "ancora_x"):
            alvo.ancora_x = float(alvo.rect.centerx)
    _cair_em_cima(alvo, **kw)
    assert alvo.derrotado and alvo not in M.enemies, f"{nome} não morreu com o pisão"
    assert M.player.player_health == constants.PLAYER_HEALTH, f"pisão em {nome} tirou vida"
    assert M.player.vel_y < 0, "jogador deveria quicar"
    assert M.efeitos, "sem efeito de derrota"
    ok(f"pisão derrota {nome} sem dano no jogador (quica)")


def teste_lateral_machuca():
    alvo = _primeiro("floresta", Enemy)
    p = M.player
    p.player_health = constants.PLAYER_HEALTH
    p.invulnerable = False
    p.rect.bottom = alvo.rect.bottom
    p.rect.right = alvo.rect.left - 2
    p.pos_x, p.pos_y = float(p.rect.x), float(p.rect.y)
    p.vel_y = 0
    M.moving_right = True
    for _ in range(40):
        M.atualizar_jogando(16)
        if p.player_health < constants.PLAYER_HEALTH:
            break
    M.moving_right = False
    assert p.player_health == constants.PLAYER_HEALTH - constants.DAMAGE, p.player_health
    assert not alvo.derrotado, "contato lateral não pode matar o inimigo"
    vida = p.player_health
    for _ in range(10):        # encostado: dano não repete por frame
        alvo.check_player_collision(p)
    assert p.player_health == vida
    ok("contato lateral machuca o jogador uma vez e não mata o inimigo")


def teste_boss_imune_a_pisao():
    M.ativar_setor("arena")
    boss = M.boss
    _parar(boss)
    boss.ativo = True
    boss.estado = "COMBATE"
    _cair_em_cima(boss, altura_tiles=2)
    assert not boss.derrotado and boss.vida == boss.VIDA_MAX, "boss não deve morrer com pisão"
    ok("boss só quica no pisão (vence-se pelas perguntas)")


def teste_morto_continua_morto_e_reiniciar_restaura():
    vivos_antes = len(M.setores["floresta"].inimigos)
    M.ativar_setor("caverna")
    M.ativar_setor("floresta")
    assert len(M.enemies) == vivos_antes, "inimigo morto voltou ao trocar de setor"
    total = sum(len(s.inimigos) for s in M.setores.values())
    M.iniciar_jogo()
    assert sum(len(s.inimigos) for s in M.setores.values()) > total, "REINICIAR não restaurou"
    ok("derrotado continua derrotado ao trocar de setor; nova partida restaura")


if __name__ == "__main__":
    preparar()
    teste_lateral_machuca()
    teste_pisao_mata("floresta", Enemy, "cobra")
    teste_pisao_mata("floresta", Enemy, "cobra (queda rápida)", altura_tiles=6,
                     vel_inicial=constants.VEL_TERMINAL)
    teste_pisao_mata("copas", Tucano, "tucano")
    teste_pisao_mata("caverna", Aranha, "aranha (descida no fio)", descer_tiles=4,
                     altura_tiles=1.5)
    teste_morto_continua_morto_e_reiniciar_restaura()
    teste_boss_imune_a_pisao()
    M.banco_estatisticas.fechar()
    print("TODOS OS TESTES DE INIMIGOS PASSARAM")
