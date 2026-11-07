from src.nucleo import constants
from src.interface.intro_logo import IntroLogo
from src.jogo.estados.base import Estado


class EstadoIntroLogo(Estado):
    """Logo da escola em fade in/out, antes do menu."""

    def __init__(self, jogo):
        super().__init__(jogo)
        self.logo = IntroLogo(constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT,
                              callback_fim=lambda: jogo.ir_para("MENU"))

    def entrar(self, **dados):
        self.logo.iniciar()

    def evento(self, ev):
        self.logo.handle_event(ev)

    def atualizar(self, dt_ms):
        self.logo.atualizar(dt_ms)

    def desenhar(self, tela, mouse_pos):
        self.logo.desenhar(tela)
