"""
Teste headless do fluxo da partida (sem janela, sem controle).

Cobre o caminho que a revisão técnica pediu para verificar:
spawn -> movimento -> inimigos (culling) -> coleta -> quiz -> passagem/
transição entre SETORES -> estado preservado -> arena do boss, e a base de
combate dos inimigos.

Uso (a partir da raiz do projeto):
    python testes/teste_partida.py
"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
# Banco de estatísticas temporário: os testes nunca gravam no estatisticas.db real.
import tempfile  # noqa: E402
os.environ.setdefault("ISA_DB", os.path.join(tempfile.mkdtemp(prefix="isa_teste_"), "estatisticas.db"))
os.environ["SDL_AUDIODRIVER"] = "dummy"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

import pygame  # noqa: E402

from src.nucleo import constants  # noqa: E402
from compat_main import M  # noqa: E402
from src.entidades.enemies import CLASSES_INIMIGO, Aranha, Enemy  # noqa: E402
from src.sistemas.joystick import GerenciadorJoystick  # noqa: E402

T = constants.TILE_SIZE


def preparar():
    pygame.init()
    M.configurar_janela()
    M.clock = pygame.time.Clock()
    M.gamepad = GerenciadorJoystick()
    M.recriar_ui()
    M.iniciar_jogo()


def rodar(frames):
    for _ in range(frames):
        M.atualizar_jogando(16)
        M.desenhar_jogo((0, 0))


def teleportar(col, linha_ocupada):
    """Põe o player com os pés na base da célula (col, linha)."""
    p = M.player
    p.rect.centerx = col * T + T // 2
    p.rect.bottom = (linha_ocupada + 1) * T
    p.pos_x, p.pos_y = float(p.rect.x), float(p.rect.y)
    p.vel_y = 0.0
    M.atualizar_camera(instantaneo=True)


def ok(msg):
    print("ok:", msg)


def teste_spawn_e_movimento():
    rodar(30)
    assert M.player.on_ground, "player nasceu sem chao"
    x0 = M.player.rect.x
    M.moving_right = True
    rodar(40)
    M.moving_right = False
    assert M.player.rect.x > x0 + 50, "player nasceu preso (nao anda para a direita)"
    assert M.estado_jogo == "JOGANDO"
    ok("spawn com chao e player anda livre")


def teste_culling_inimigos():
    area = M.area_ativa()
    ativos = [e for e in M.enemies if e.precisa_atualizar(area)]
    assert len(ativos) < len(M.enemies), "culling nao filtrou nenhum inimigo"
    longe = next(e for e in M.enemies if not e.precisa_atualizar(area))
    pos = longe.rect.topleft
    rodar(10)
    assert longe.rect.topleft == pos, "inimigo fora da area continuou sendo atualizado"
    dist_spawn = min(abs(e.rect.centerx - M.player.rect.centerx) for e in M.enemies)
    assert dist_spawn > 10 * T, "inimigo nasce em cima do jogador"
    ok(f"culling: {len(ativos)}/{len(M.enemies)} inimigos ativos no spawn")


# Minérios da floresta no início da partida (o redesign mudou de 4 para 24;
# o teste usa a contagem real em vez de um número fixo).
MINERIOS_FLORESTA_INICIO = None


def teste_coleta_abre_quiz():
    global MINERIOS_FLORESTA_INICIO
    item = M.itens[0]
    total = len(M.itens)
    MINERIOS_FLORESTA_INICIO = total
    M.player.rect.center = item.rect.center
    M.player.pos_x, M.player.pos_y = float(M.player.rect.x), float(M.player.rect.y)
    M.atualizar_jogando(16)
    assert M.estado_jogo == "QUIZ", f"coleta nao abriu o quiz ({M.estado_jogo})"
    M.processar_resposta("a")
    assert M.estado_jogo == "QUIZ_FEEDBACK"
    assert len(M.itens) == total - 1, "minerio respondido nao saiu do mapa"
    M.estado_jogo = "JOGANDO"
    ok("minerio -> quiz -> resposta -> minerio removido")


def usar_passagem(setor_destino):
    """Leva o player até a passagem do setor ativo que vai para `setor_destino`,
    aperta interagir e roda a transição até o fim."""
    passagem = next(p for p in M.passagens_cenario.itens
                    if p.destino["setor"] == setor_destino)
    M.player.rect.centerx = passagem.rect.centerx
    M.player.rect.bottom = passagem.rect.bottom
    M.player.pos_x, M.player.pos_y = float(M.player.rect.x), float(M.player.rect.y)
    M.player.vel_y = 0.0
    M.atualizar_camera(instantaneo=True)
    M.interagir_pressionado = True
    M.atualizar_jogando(16)
    M.interagir_pressionado = False
    assert M.transicao.ativa, f"interagir na passagem para {setor_destino} nao iniciou o fade"
    for _ in range(200):
        M.atualizar_jogando(16)
        if not M.transicao.ativa:
            break
    assert not M.transicao.ativa, "transicao nao terminou"
    assert M.setor_atual.nome == setor_destino, M.setor_atual.nome
    rodar(30)
    assert M.player.on_ground and M.player.alive, f"player caiu/morreu ao chegar em {setor_destino}"


def teste_passagem_para_caverna():
    usar_passagem("caverna")
    assert M.ambientes.nome_atual == "caverna", M.ambientes.nome_atual
    assert M.fase_atual == constants.FASE_POR_REGIAO["caverna"]
    assert M.world is M.setores["caverna"].world and M.enemies is M.setores["caverna"].inimigos
    ok("floresta -> passagem -> fade -> setor caverna (mundo, inimigos e fase trocados)")


def teste_estado_persiste_entre_setores():
    minerios_floresta = len(M.setores["floresta"].itens)
    assert minerios_floresta == MINERIOS_FLORESTA_INICIO - 1, \
        "o teste de coleta deveria ter tirado 1 minerio da floresta"
    usar_passagem("floresta")
    assert len(M.itens) == minerios_floresta, "minerio coletado reapareceu ao voltar"
    ok("voltar para a floresta mantem o minerio coletado antes (estado por setor)")


def teste_arena_do_boss():
    M.ativar_setor("copas")
    usar_passagem("arena")
    assert M.area_boss is not None, "setor arena sem area do boss"
    # Mudou na unificação: a arena não é mais vazia — o boss nasce nela.
    # Continua sem inimigo comum e sem minério.
    assert [type(e).__name__ for e in M.enemies] == ["Gorila"], M.enemies
    assert not M.itens, "arena nao deve ter minerio"
    assert M.boss is M.enemies[0] and not M.boss.ativo, "boss deveria esperar o jogador"
    rodar(30)
    assert M.player.on_ground and not M.boss.ativo, "luta comecou antes de entrar na area"
    assert M.area_boss["rect"].colliderect(M.boss.rect), "boss fora da area de luta"
    usar_passagem("copas")
    ok("copas -> arena (boss esperando, chao firme) -> de volta as copas")


def teste_base_de_combate():
    class InimigoTeste(Enemy):
        VIDA_MAX = 3
        INVENCIVEL = False
        derrotas = []

        def ao_derrotar(self):
            InimigoTeste.derrotas.append(self)

    # Mudou na unificação: inimigos comuns morrem com o pisão
    # (constants.INIMIGOS_MORREM_COM_PISAO). O pisão em si é testado em
    # testes/teste_inimigos.py; aqui só a regra de vida.
    comum = M.enemies[0]
    assert comum.INVENCIVEL is (not constants.INIMIGOS_MORREM_COM_PISAO)

    alvo = InimigoTeste(x=M.player.rect.x + 4 * T, y=M.player.rect.y)
    M.enemies.append(alvo)
    assert alvo.receber_dano(1) is False and abs(alvo.proporcao_vida - 2 / 3) < 1e-6
    alvo.iniciar_cooldown("ataque", 10_000)
    assert alvo.em_cooldown("ataque")
    assert alvo.receber_dano(5) is True and alvo.derrotado
    M.atualizar_jogando(16)
    assert alvo not in M.enemies, "inimigo derrotado nao foi removido"
    assert InimigoTeste.derrotas == [alvo]
    ok("vida, dano, cooldown e evento de derrota funcionam")


def teste_registro_e_aranha():
    for _id, (nome, _ancora) in constants.MARCADORES_MOB.items():
        assert nome in CLASSES_INIMIGO, f"marcador aponta para classe nao registrada: {nome}"
    aranha = next(e for setor in M.setores.values() for e in setor.inimigos
                  if isinstance(e, Aranha))
    assert aranha.area_desenho().top <= int(aranha.altura_inicial)
    ok("todo marcador de mob tem classe registrada; culling da aranha inclui o fio")


if __name__ == "__main__":
    preparar()
    teste_spawn_e_movimento()
    teste_culling_inimigos()
    teste_coleta_abre_quiz()
    teste_passagem_para_caverna()
    teste_estado_persiste_entre_setores()
    teste_arena_do_boss()
    teste_base_de_combate()
    teste_registro_e_aranha()
    M.banco_estatisticas.fechar()
    print("TODOS OS TESTES DE PARTIDA PASSARAM")