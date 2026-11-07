from src.nucleo import constants
from src.sistemas.estatisticas import TelaEstatisticas
from src.jogo.estados.base import Estado


class EstadoEstatisticas(Estado):
    """Desempenho da sessão ATUAL (nunca a última do banco) + relatório PDF."""

    def __init__(self, jogo):
        super().__init__(jogo)
        self.tela = None

    def entrar(self, resultado=None, **dados):
        jogo = self.jogo
        self.tela = TelaEstatisticas(
            jogo.janela.tela,
            constants.SCREEN_WIDTH,
            constants.SCREEN_HEIGHT,
            resultado,
            callback_voltar=jogo.voltar_menu,
            callback_pdf_gerado=jogo.registrar_pdf,
        )

    def evento(self, ev):
        if self.tela:
            self.tela.handle_event(ev)

    def controle(self, gamepad):
        if gamepad.voltou_agora:
            self.jogo.voltar_menu()

    def desenhar(self, tela, mouse_pos):
        if self.tela:
            self.tela.desenhar(mouse_pos)
