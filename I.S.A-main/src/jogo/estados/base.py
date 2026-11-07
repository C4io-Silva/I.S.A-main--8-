"""Contrato de um estado (tela) do jogo."""


class Estado:
    """
    Cada tela do jogo — menu, partida, pausa, quiz... — é um Estado. O Jogo
    chama sempre os mesmos métodos, na mesma ordem, a cada frame:

        evento(ev)         para cada evento do pygame
        controle(gamepad)  uma vez, com o controle conectado
        atualizar(dt_ms)   lógica do frame
        desenhar(tela, mouse_pos)

    `entrar` roda ao chegar nesse estado (ir_para) e `sair` ao deixá-lo.
    """

    def __init__(self, jogo):
        self.jogo = jogo

    def entrar(self, **dados):
        pass

    def sair(self):
        pass

    def evento(self, ev):
        pass

    def controle(self, gamepad):
        pass

    def atualizar(self, dt_ms):
        pass

    def desenhar(self, tela, mouse_pos):
        raise NotImplementedError
