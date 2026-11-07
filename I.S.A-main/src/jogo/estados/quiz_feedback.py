from src.nucleo import constants
from src.nucleo.estilo import COR_ACERTO, COR_ERRO, CONTORNO_TITULO
from src.jogo.estados.base import Estado
from src.jogo.visual import overlay, painel_menu
from src.nucleo.utils import carregar_fonte, texto_contorno


class EstadoQuizFeedback(Estado):
    """Acerto/erro depois de responder: fundo preto, painel e texto estilizados."""

    def __init__(self, jogo):
        super().__init__(jogo)
        self._cache = {}    # (mensagem, acertou) -> (texto, subtexto): o contorno é caro

    def _textos(self, mensagem, acertou):
        chave = (mensagem, acertou)
        if chave not in self._cache:
            cor = COR_ACERTO if acertou else COR_ERRO
            msg = texto_contorno(carregar_fonte("upheavtt.ttf", 32), mensagem, cor,
                                 CONTORNO_TITULO, espessura=3, sombra=(0, 2))
            sub = texto_contorno(carregar_fonte("upheavtt.ttf", 16), "Voltando ao jogo...",
                                 (200, 210, 255), CONTORNO_TITULO, espessura=2, sombra=(0, 2))
            self._cache[chave] = (msg, sub)
        return self._cache[chave]

    def atualizar(self, dt_ms):
        self.jogo.partida.quiz.atualizar_feedback()

    def desenhar(self, tela, mouse_pos):
        quiz = self.jogo.partida.quiz
        W, H = constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT
        # Sem limpar a tela: o véu escuro se acumula sobre o quadro anterior,
        # e em poucos frames o fundo fica preto (como sempre foi nesta tela).
        tela.blit(overlay((0, 0, 0, 220)), (0, 0))
        msg, sub = self._textos(quiz.mensagem, quiz.acertou)
        largura = min(W - 40, max(480, msg.get_width() + 80))
        painel_menu(tela, W // 2, H // 2 - 70, largura, 170)
        tela.blit(msg, msg.get_rect(center=(W // 2, H // 2 - 15)))
        tela.blit(sub, sub.get_rect(center=(W // 2, H // 2 + 45)))
