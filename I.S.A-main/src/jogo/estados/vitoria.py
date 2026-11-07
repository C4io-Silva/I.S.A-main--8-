from src.nucleo import constants
from src.interface.buttons import Botao
from src.nucleo.estilo import AMARELO_TITULO
from src.jogo.estados.base import Estado
from src.jogo.menu_botoes import MenuBotoes
from src.jogo.visual import overlay, painel_menu, texto_c


class EstadoVitoria(Estado):
    """Boss derrotado: resumo da partida."""

    def __init__(self, jogo):
        super().__init__(jogo)
        xl = constants.SCREEN_WIDTH // 2 - 150
        self.menu = MenuBotoes(jogo, [
            Botao("RELATORIO", xl, 345, 300, 60, jogo.abrir_estatisticas),
            Botao("JOGAR DE NOVO", xl, 420, 300, 60, jogo.iniciar_partida),
            Botao("MENU", xl, 495, 300, 60, jogo.voltar_menu),
        ])

    def entrar(self, **dados):
        self.menu.resetar()

    def evento(self, ev):
        self.menu.clicar(ev)

    def controle(self, gamepad):
        self.menu.atualizar_controle(gamepad)

    def desenhar(self, tela, mouse_pos):
        jogo = self.jogo
        partida = jogo.partida
        W = constants.SCREEN_WIDTH
        fontes = jogo.fontes
        tela.blit(jogo.fundo, (0, 0))
        tela.blit(overlay((10, 20, 80, 175)), (0, 0))
        painel_menu(tela, W // 2, 40, min(620, W - 40), 545)
        titulo = texto_c(fontes.logo, "VITORIA!", AMARELO_TITULO, 4)
        tela.blit(titulo, titulo.get_rect(center=(W // 2, 110)))
        linhas = (
            f"{jogo.aluno}, o Gorila Guardiao foi derrotado!",
            "Os minerios da floresta estao a salvo.",
            f"Acertos: {partida.pontuacao}   |   "
            f"Perguntas respondidas: {partida.ordem_resposta}",
            f"Inimigos derrotados: {partida.inimigos_derrotados}",
        )
        y = 185
        for linha in linhas:
            surf = texto_c(fontes.titulo, linha, constants.WHITE)
            tela.blit(surf, surf.get_rect(center=(W // 2, y)))
            y += 36
        self.menu.desenhar(tela, mouse_pos)
