"""
Regressões encontradas na validação da candidata de teste (13/10/2026):

1. Bordas do setor: o redesign tirou as colunas de rocha das bordas da
   floresta, copas e arena. Segurar para a esquerda no spawn levava a
   Areninha para x < 0, sem chão, e dava GAME OVER. Agora main.py tem uma
   parede invisível nas duas bordas (main._limitar_player_ao_setor).
2. Saída da arena: o marcador 35 tinha ido para a coluna 36, DENTRO da área
   de luta. Andar até ela ativava o Gorila e trancava a saída; o jogador que
   entrava na arena não conseguia voltar às copas antes da luta. A saída
   voltou para o lado da chegada, fora da área de luta.

Roda o MESMO código do jogo (atualizar_jogando), com entrada simulada nas
mesmas flags que o teclado liga.

Uso (a partir da raiz do projeto):
    python testes/teste_bordas_e_saidas.py
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


def _pousar(col):
    """Coloca o player em pé no chão mais alto da coluna."""
    g = M.setor_atual.grade
    linha = next(l for l in range(2, len(g))
                 if g[l][col] in constants.SOLID_TILES
                 and g[l - 1][col] not in constants.SOLID_TILES)
    p = M.player
    p.rect.centerx = col * T + T // 2
    p.rect.bottom = linha * T
    p.pos_x, p.pos_y = float(p.rect.x), float(p.rect.y)
    p.vel_y = 0.0
    M.atualizar_camera(instantaneo=True)


def _andar(esquerda, frames):
    M.moving_left, M.moving_right = esquerda, not esquerda
    for _ in range(frames):
        M.atualizar_jogando(16)
    M.moving_left = M.moving_right = False


def teste_bordas_de_todos_os_setores():
    for nome in M.setores:
        M.ativar_setor(nome)
        largura = M.setor_atual.largura_px
        for esquerda, col in ((True, 1), (False, M.setor_atual.world.colunas - 2)):
            M.estado_jogo = "JOGANDO"
            _pousar(col)
            _andar(esquerda, 180)          # 3 s segurando contra a borda
            for _ in range(60):
                M.atualizar_jogando(16)
            p = M.player
            lado = "esquerda" if esquerda else "direita"
            assert M.estado_jogo == "JOGANDO", f"{nome}/{lado}: {M.estado_jogo}"
            assert p.alive and p.rect.left >= 0 and p.rect.right <= largura, \
                f"{nome}/{lado}: saiu do mapa {p.rect}"
            assert p.rect.bottom <= M.setor_atual.altura_px, f"{nome}/{lado}: caiu"
    ok("nenhuma borda lateral deixa a Areninha sair do mapa (4 setores)")


def teste_saida_da_arena_antes_da_luta():
    M.iniciar_jogo()   # partida nova: o teste das bordas ativou o Gorila
    M.estado_jogo = "JOGANDO"
    M.ativar_setor("copas")
    entrada = next(p for p in M.passagens_cenario.itens if p.destino["setor"] == "arena")
    M.player.rect.midbottom = entrada.rect.midbottom
    M.player.pos_x, M.player.pos_y = float(M.player.rect.x), float(M.player.rect.y)
    M.interagir_pressionado = True
    M.atualizar_jogando(16)
    M.interagir_pressionado = False
    for _ in range(240):
        M.atualizar_jogando(16)
        if not M.transicao.ativa:
            break
    assert M.setor_atual.nome == "arena"
    for _ in range(30):
        M.atualizar_jogando(16)
    saida = next(p for p in M.passagens_cenario.itens if p.destino["setor"] == "copas")
    area = M.area_boss["rect"]
    assert saida.rect_interacao.right <= area.left, \
        f"saida da arena dentro da area de luta: {saida.rect_interacao} x {area}"
    # Anda de verdade (tecla segurada) da chegada até a saída.
    esquerda = saida.rect.centerx < M.player.rect.centerx
    M.moving_left, M.moving_right = esquerda, not esquerda
    for _ in range(600):
        M.atualizar_jogando(16)
        if saida.alcancavel_por(M.player.rect):
            break
    M.moving_left = M.moving_right = False
    assert saida.alcancavel_por(M.player.rect), "nao chegou andando na saida da arena"
    assert not M.boss.ativo, "andar ate a saida ativou o Gorila"
    M.interagir_pressionado = True
    M.atualizar_jogando(16)
    M.interagir_pressionado = False
    assert M.transicao.ativa, "E na saida da arena nao iniciou o fade"
    for _ in range(240):
        M.atualizar_jogando(16)
        if not M.transicao.ativa:
            break
    assert M.setor_atual.nome == "copas", M.setor_atual.nome
    ok("arena: da chegada se anda ate a saida e volta as copas sem ativar o Gorila")


if __name__ == "__main__":
    preparar()
    teste_bordas_de_todos_os_setores()
    teste_saida_da_arena_antes_da_luta()
    print("TODOS OS TESTES DE BORDAS E SAIDAS PASSARAM")
