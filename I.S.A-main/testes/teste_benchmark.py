"""
Mede o custo por frame da partida (update + desenho), sem janela.

O player corre para os dois lados e pula, com o mapa real carregado. Serve
para comparar antes/depois de mexer em colisão, render ou inimigos.

Uso (a partir da raiz do projeto):
    python testes/benchmark_jogo.py            # 600 frames
    python testes/benchmark_jogo.py 2000 perfil  # + as 12 funções mais caras

Observação: com o driver de vídeo "dummy" o blit é mais barato que numa
janela real; os números servem para COMPARAR versões, não como FPS final.
"""
import cProfile
import io
import os
import pstats
import sys
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"
# Banco de estatísticas temporário: os testes nunca gravam no estatisticas.db real.
import tempfile  # noqa: E402
os.environ.setdefault("ISA_DB", os.path.join(tempfile.mkdtemp(prefix="isa_teste_"), "estatisticas.db"))
os.environ["SDL_AUDIODRIVER"] = "dummy"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

import pygame  # noqa: E402

from compat_main import M  # noqa: E402
from src.sistemas.joystick import GerenciadorJoystick  # noqa: E402


def frame(i):
    M.moving_right = (i // 120) % 2 == 0
    M.moving_left = not M.moving_right
    if i % 45 == 0:
        M.jump_pressed = True
    M.atualizar_jogando(16)
    M.desenhar_jogo((0, 0))
    # Mantém a partida rodando mesmo se o roteiro levar dano ou abrir quiz.
    M.player.alive, M.player.player_health, M.estado_jogo = True, 100, "JOGANDO"


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 600
    perfil = "perfil" in sys.argv
    pygame.init()
    M.configurar_janela()
    M.gamepad = GerenciadorJoystick()
    M.recriar_ui()
    M.iniciar_jogo()
    print(f"obstaculos: {M.world.total_obstaculos}  inimigos: {len(M.enemies)}  "
          f"minerios: {len(M.itens)}")
    for i in range(60):
        frame(i)

    prof = cProfile.Profile() if perfil else None
    if prof:
        prof.enable()
    inicio = time.perf_counter()
    for i in range(n):
        frame(i)
    ms = (time.perf_counter() - inicio) / n * 1000
    if prof:
        prof.disable()
        saida = io.StringIO()
        pstats.Stats(prof, stream=saida).sort_stats("tottime").print_stats(12)
        print(saida.getvalue())
    print(f"{ms:.2f} ms por frame ({n} frames)")
    M.banco_estatisticas.fechar()


if __name__ == "__main__":
    main()