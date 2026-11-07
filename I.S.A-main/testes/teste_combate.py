"""
Teste do combate da Areninha (golpe de asa) contra os inimigos comuns.

Roda o código real da partida (main.atualizar_jogando) com relógio falso:
cada frame avança 16 ms exatos, então antecipação, janela de acerto,
cooldown e atordoamento são medidos de forma reproduzível.

Cobre: acerto e redução de vida, um golpe = um acerto por inimigo,
cooldown e buffer, direção do golpe, atordoamento (sem dano de contato) e
empurrão, derrota/remoção/efeito/contador, golpe andando e no ar sem mudar a
física, aranha (solta o jogador), tucano, Gorila imune com a mecânica dele
intacta, setores sem reaparecimento nem duplicação, minérios e quiz
preservados, e a entrada pelo teclado (evento J) e pelo controle (botão B).

Uso (a partir da raiz do projeto):
    python testes/teste_combate.py
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

_agora = [50_000]
pygame.time.get_ticks = lambda: _agora[0]

from src.nucleo import constants  # noqa: E402
from compat_main import M  # noqa: E402
from src.entidades.enemies import Aranha, Enemy, Gorila, Tucano  # noqa: E402
from src.sistemas.joystick import GerenciadorJoystick  # noqa: E402

T = constants.TILE_SIZE
DT = 16


def ok(msg):
    print("ok:", msg)


def frame(n=1):
    for _ in range(n):
        _agora[0] += DT
        M.atualizar_jogando(DT)


def preparar():
    pygame.init()
    M.configurar_janela()
    M.clock = pygame.time.Clock()
    M.gamepad = GerenciadorJoystick()
    M.recriar_ui()
    M.iniciar_jogo()


def _parado(inimigo):
    """Desliga a IA (patrulha/perseguição) só deste inimigo: o teste mede o combate."""
    inimigo.update = lambda *a, **k: None
    return inimigo


def _setor_com(setor, classe):
    M.ativar_setor(setor)
    return _parado(next(e for e in M.enemies if type(e) is classe))


def _frente_a(alvo, distancia_px=4, olhando=1):
    """Põe a Areninha no chão do alvo, a `distancia_px` dele, olhando para ele."""
    p = M.player
    p.player_health = constants.PLAYER_HEALTH
    p.invulnerable = False
    p.preso = False
    p.vel_y = 0.0
    p.rect.bottom = alvo.rect.bottom
    if olhando > 0:
        p.rect.right = alvo.rect.left - distancia_px
    else:
        p.rect.left = alvo.rect.right + distancia_px
    p.pos_x, p.pos_y = float(p.rect.x), float(p.rect.y)
    p.flip = olhando < 0
    M.reiniciar_movimento()
    M.golpe.reiniciar()
    M.atualizar_camera(instantaneo=True)


def _golpear_e_esperar(n_frames=None):
    M.golpe.pedir()
    frame(n_frames or (constants.GOLPE_INICIO_MS + constants.GOLPE_ATIVO_MS) // DT + 2)


def teste_golpe_fere_uma_vez_e_atordoa():
    cobra = _setor_com("floresta", Enemy)
    assert cobra.vida == constants.VIDA_INIMIGO_COMUM == 2
    _frente_a(cobra)
    x_antes = cobra.rect.centerx
    M.golpe.pedir()
    frame(1)
    assert cobra.vida == 2, "acertou antes da antecipação acabar"
    frame((constants.GOLPE_INICIO_MS + constants.GOLPE_ATIVO_MS) // DT + 2)
    assert cobra.vida == 1, f"golpe deveria tirar 1 de vida (vida {cobra.vida})"
    assert cobra.atordoado_por_golpe and _agora[0] < cobra.barra_vida_ate
    assert cobra.rect.centerx > x_antes, "inimigo deveria ser empurrado para longe"
    assert len(M.efeitos) >= 1, "sem faísca de impacto"
    ok("golpe de asa tira 1 de vida UMA vez, pisca, mostra a barra, atordoa e empurra")


def teste_dois_golpes_sem_andar():
    """Achado na revisão visual: com empurrão maior que o alcance da asa, o
    2º golpe dado no lugar errava. Agora dois golpes seguidos derrubam."""
    cobra = next(e for e in M.enemies if type(e) is Enemy and e.vida == 2 and not e.derrotado)
    _parado(cobra)
    _agora[0] += 2000
    _frente_a(cobra)
    _golpear_e_esperar()
    assert cobra.vida == 1
    _agora[0] = M.golpe.inicio + constants.GOLPE_COOLDOWN_MS
    _golpear_e_esperar()
    assert cobra.derrotado, "2º golpe no lugar não alcançou o inimigo empurrado"
    ok("dois golpes seguidos, sem andar, derrubam o inimigo (empurrão < alcance)")


def teste_atordoado_nao_machuca():
    cobra = next(e for e in M.enemies if type(e) is Enemy and e.vida == 1)
    p = M.player
    p.invulnerable = False
    p.rect.center = cobra.rect.center
    vida = p.player_health
    assert cobra.atordoado_por_golpe
    cobra.check_player_collision(p)
    assert p.player_health == vida, "inimigo atordoado deu dano de contato"
    _agora[0] = cobra.atordoado_golpe_ate + 1
    p.invulnerable = False
    p.vel_y = 0
    p.caindo = False
    p.pes_antes = p.rect.bottom
    cobra.check_player_collision(p)
    assert p.player_health == vida - constants.DAMAGE, "fim do atordoamento: contato volta a machucar"
    vida = p.player_health
    for _ in range(20):
        cobra.check_player_collision(p)
    assert p.player_health == vida, "dano de contato repetido por frame"
    ok("atordoado não machuca; depois volta a machucar, uma vez (invencibilidade do jogador)")


def teste_cooldown_buffer_e_derrota():
    cobra = next(e for e in M.enemies if type(e) is Enemy and e.vida == 1)
    # cooldown/buffer medidos no spawn, longe de inimigos
    M._assentar(M.player, *M.setor_atual.player_spawn)
    _agora[0] += 1000
    M.golpe.reiniciar()
    M.golpe.pedir()
    frame(1)
    inicio = M.golpe.inicio
    for _ in range(5):                 # martelando o botão durante o cooldown
        M.golpe.pedir()
        frame(2)
    assert M.golpe.inicio == inicio, "golpe saiu antes do cooldown"
    # buffer: pede pouco antes de liberar -> sai exatamente quando libera
    _agora[0] = inicio + constants.GOLPE_COOLDOWN_MS - 80
    M.golpe.pedir()
    frame(6)
    assert M.golpe.inicio > inicio, "pedido dentro do buffer foi perdido"
    assert M.golpe.inicio - inicio >= constants.GOLPE_COOLDOWN_MS
    _agora[0] += 2000
    _frente_a(cobra)
    total_antes = M.inimigos_derrotados
    _golpear_e_esperar()
    assert cobra.derrotado and cobra not in M.enemies, "segundo golpe deveria derrotar"
    assert M.inimigos_derrotados == total_antes + 1
    ok("cooldown impede golpe infinito; buffer guarda o toque; 2º golpe derrota e remove")


def teste_direcao():
    cobra = next(e for e in M.enemies if type(e) is Enemy and not e.derrotado)
    _parado(cobra)
    _agora[0] += 2000
    _frente_a(cobra, olhando=1)
    M.player.flip = True              # de costas para a cobra
    vida = cobra.vida
    _golpear_e_esperar()
    assert cobra.vida == vida, "golpe acertou quem estava atrás"
    ok("golpe só acerta à frente da Areninha")


def teste_golpe_andando_e_no_ar_sem_mudar_fisica():
    p = M.player
    M.ativar_setor("floresta")
    sx, sy = M.setor_atual.player_spawn
    for golpeando in (False, True):
        M._assentar(p, sx, sy)
        p.vel_y = 0
        frame(20)
        x0 = p.rect.x
        M.moving_right = True
        M.jump_pressed = True
        alturas = []
        for i in range(30):
            if golpeando and i % 4 == 0:
                M.golpe.pedir()
            frame(1)
            alturas.append(p.rect.y)
        M.moving_right = False
        if not golpeando:
            dx_sem, pico_sem = p.rect.x - x0, min(alturas)
        else:
            dx_com, pico_com = p.rect.x - x0, min(alturas)
    assert dx_com == dx_sem and pico_com == pico_sem, \
        f"golpe mudou a física (dx {dx_sem}->{dx_com}, pico {pico_sem}->{pico_com})"
    ok("golpe andando e no ar: mesma velocidade e mesma altura de pulo")


def teste_tucano_e_aranha():
    tucano = _setor_com("copas", Tucano)
    _agora[0] += 2000
    _frente_a(tucano)
    _golpear_e_esperar()
    _agora[0] += 1000
    _frente_a(tucano)
    _golpear_e_esperar()
    assert tucano.derrotado and tucano not in M.enemies, "tucano não morreu com 2 golpes"

    aranha = _setor_com("caverna", Aranha)
    aranha.update = Aranha.update.__get__(aranha)   # aranha usa a IA real aqui
    p = M.player
    # Areninha logo abaixo do ponto onde a aranha estava, no ar livre
    p.rect.midtop = (aranha.rect.centerx, aranha.rect.bottom + T)
    p.pos_x, p.pos_y = float(p.rect.x), float(p.rect.y)
    p.vel_y = 0.0
    aranha.player_preso = p
    aranha._prender(p)
    aranha._trocar_estado("PRENDENDO")
    aranha.rect.bottom = p.rect.top + aranha.rect.height // 2
    aranha.rect.centerx = p.rect.centerx + 10
    aranha.ancora_x = float(aranha.rect.centerx)
    M.atualizar_camera(instantaneo=True)   # aranha dentro da área ativa
    assert p.preso
    _agora[0] += 2000
    M.golpe.reiniciar()
    M.golpe.direcao = 1
    p.flip = False
    M.golpe.pedir()
    frame((constants.GOLPE_INICIO_MS + constants.GOLPE_ATIVO_MS) // DT + 2)
    assert aranha.vida == 1 and not p.preso, "golpe na aranha deveria soltar o jogador"
    assert aranha.estado == "SUBINDO"
    ok("tucano cai com 2 golpes; golpe na aranha solta a Areninha e a faz recuar")


def teste_gorila_imune_e_mecanica_intacta():
    M.ativar_setor("arena")
    boss = M.boss
    boss.ativar()
    _agora[0] = boss.intro_ate + 50
    p = M.player
    p.rect.bottom = boss.rect.bottom
    p.rect.right = boss.rect.left - 4
    p.pos_x, p.pos_y = float(p.rect.x), float(p.rect.y)
    p.flip = False
    M.golpe.reiniciar()
    vida = boss.vida
    _golpear_e_esperar()
    assert boss.vida == vida and boss.estado != "ATORDOADO", "golpe feriu o Gorila"
    assert "Gorila" in M.aviso_jogo[0]
    # a mecânica própria continua: minério que acerta abre a pergunta
    from src.entidades.enemies.boss import ProjetilGorila
    proj = ProjetilGorila(boss, p.rect.centerx + 50, p.rect.centery, -8, 0, "cobre")
    boss.projeteis.append(proj)
    for _ in range(30):
        frame()
        if M.estado_jogo == "QUIZ":
            break
    assert M.estado_jogo == "QUIZ" and M.quiz_boss is not None
    M.processar_resposta(M.pergunta_em_jogo()["resposta"])
    assert proj.estado == "retornando"
    M.estado_jogo = "JOGANDO"
    ok("Gorila imune ao golpe (aviso na tela); minério -> quiz -> rebote continua igual")


def teste_setores_sem_reaparecer_nem_duplicar():
    def contagem():
        return {n: len(s.inimigos) for n, s in M.setores.items()}
    antes = contagem()
    for destino in ("floresta", "caverna", "copas", "arena", "floresta"):
        M.ativar_setor(destino)
        frame(3)
    assert contagem() == antes, f"inimigos mudaram ao trocar de setor: {antes} -> {contagem()}"
    todos = [e for s in M.setores.values() for e in s.inimigos]
    assert len({id(e) for e in todos}) == len(todos), "inimigo duplicado"
    assert sum(isinstance(e, Gorila) for e in todos) == 1
    assert not any(e.derrotado for e in todos), "derrotado ficou na lista"
    ok(f"derrotados não reaparecem nem duplicam ao trocar de setor ({antes})")


def teste_minerios_e_quiz_preservados():
    M.ativar_setor("floresta")
    item = M.itens[0]
    total = len(M.itens)
    M.player.rect.center = item.rect.center
    M.player.pos_x, M.player.pos_y = float(M.player.rect.x), float(M.player.rect.y)
    M.golpe.pedir()             # golpear em cima do minério não estraga a coleta
    frame()
    assert M.estado_jogo == "QUIZ", M.estado_jogo
    M.processar_resposta(M.pergunta_em_jogo()["resposta"])
    assert len(M.itens) == total - 1
    M.estado_jogo = "JOGANDO"
    ok("golpe não interfere na coleta: minério -> quiz -> resposta -> minério removido")


def teste_teclado_e_controle():
    M.golpe.reiniciar()
    # teclado: o loop chama golpe.pedir() para as teclas de TECLAS_GOLPE
    assert pygame.K_j in M.TECLAS_GOLPE and pygame.K_f in M.TECLAS_GOLPE
    # controle: botões configurados existem e são diferentes de pulo/interagir
    usados = {constants.JOY_BOTAO_PULO, constants.JOY_BOTAO_INTERAGIR, constants.JOY_BOTAO_PAUSA}
    assert constants.JOY_BOTAO_ATAQUE not in usados and constants.JOY_BOTAO_ATAQUE_ALT not in usados
    ok("teclas J/F e botões B/Y mapeados sem conflito (o loop real é testado em "
       "teste_teclado.py e teste_gamepad_falso.py)")


if __name__ == "__main__":
    preparar()
    teste_golpe_fere_uma_vez_e_atordoa()
    teste_atordoado_nao_machuca()
    teste_dois_golpes_sem_andar()
    teste_cooldown_buffer_e_derrota()
    teste_direcao()
    teste_golpe_andando_e_no_ar_sem_mudar_fisica()
    teste_tucano_e_aranha()
    teste_gorila_imune_e_mecanica_intacta()
    teste_setores_sem_reaparecer_nem_duplicar()
    teste_minerios_e_quiz_preservados()
    teste_teclado_e_controle()
    M.banco_estatisticas.fechar()
    print("TODOS OS TESTES DE COMBATE PASSARAM")
