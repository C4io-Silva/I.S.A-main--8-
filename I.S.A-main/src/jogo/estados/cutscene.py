from src.nucleo import constants
from src.interface.cutscene import Cutscene
from src.jogo.estados.base import Estado


class EstadoCutscene(Estado):
    """Abertura em imagens: ao terminar (ou ser pulada), começa a partida."""

    def __init__(self, jogo):
        super().__init__(jogo)
        self.cutscene = Cutscene(constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT,
                                 callback_fim=jogo.iniciar_partida)

    def entrar(self, **dados):
        self.jogo.audio.parar_musica(400)
        self.cutscene.iniciar()

    def evento(self, ev):
        self.cutscene.handle_event(ev)

    def controle(self, gamepad):
        if gamepad.confirmou_agora:
            self.cutscene.avancar()
        elif gamepad.voltou_agora or gamepad.pausou_agora:
            self.cutscene.pular()

    def atualizar(self, dt_ms):
        self.cutscene.atualizar(dt_ms)

    def desenhar(self, tela, mouse_pos):
        self.cutscene.desenhar(tela, mouse_pos, self.jogo.foco_no_controle)
