import pygame

from src.nucleo import constants
from src.jogo.estados.base import Estado
from src.interface.telas import TelaConfiguracoes


class EstadoConfiguracoes(Estado):
    def __init__(self, jogo):
        super().__init__(jogo)
        self.tela = TelaConfiguracoes(
            jogo.janela.tela,
            constants.SCREEN_WIDTH,
            constants.SCREEN_HEIGHT,
            callback_voltar=jogo.voltar_menu,
            callback_creditos=lambda: jogo.ir_para("CREDITOS"),
            callback_toggle_fullscreen=jogo.janela.alternar_fullscreen,
            callback_volume_musica=jogo.audio.definir_volume_musica,
            callback_volume_efeitos=jogo.audio.definir_volume_efeitos,
        )

    def evento(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.jogo.ir_para("MENU")
        self.tela.handle_event(ev)

    def controle(self, gamepad):
        # Campos de texto e sliders continuam no mouse/teclado: o controle
        # só oferece a saída.
        if gamepad.voltou_agora:
            self.jogo.ir_para("MENU")

    def desenhar(self, tela, mouse_pos):
        self.tela.desenhar(mouse_pos)
