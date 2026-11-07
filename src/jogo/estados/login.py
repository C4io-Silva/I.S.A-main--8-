import pygame

from src.jogo.estados.base import Estado
from src.interface.telas import TelaLogin


class EstadoLogin(Estado):
    """Registro do nome do aluno (vai para o relatório em PDF)."""

    def __init__(self, jogo):
        super().__init__(jogo)
        self.tela = TelaLogin(
            jogo.janela.tela,
            callback_voltar=jogo.voltar_menu,
            callback_entrar=jogo.confirmar_login,
            callback_config=lambda: jogo.ir_para("CONFIGURACOES"),
            callback_admin=lambda: jogo.ir_para("ADMIN_SENHA"),
        )

    def entrar(self, **dados):
        self.tela.resetar()

    def _voltar(self):
        pygame.key.stop_text_input()
        self.jogo.ir_para("MENU")

    def evento(self, ev):
        self.tela.handle_event(ev)
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self._voltar()

    def controle(self, gamepad):
        if gamepad.voltou_agora:
            self._voltar()

    def desenhar(self, tela, mouse_pos):
        self.tela.desenhar(mouse_pos)
