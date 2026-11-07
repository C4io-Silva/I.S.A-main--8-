from src.nucleo import constants
from src.interface.creditos import TelaCreditos
from src.jogo.estados.base import Estado


class EstadoCreditos(Estado):
    def __init__(self, jogo):
        super().__init__(jogo)
        self.tela = TelaCreditos(jogo.janela.tela, constants.SCREEN_WIDTH,
                                 constants.SCREEN_HEIGHT,
                                 callback_voltar=jogo.voltar_menu)

    def evento(self, ev):
        self.tela.handle_event(ev)

    def controle(self, gamepad):
        if gamepad.voltou_agora:
            self.jogo.ir_para("MENU")

    def desenhar(self, tela, mouse_pos):
        tela.blit(self.jogo.fundo, (0, 0))
        self.tela.update()
        self.tela.desenhar(mouse_pos)
