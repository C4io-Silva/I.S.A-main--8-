from src.nucleo import constants
from src.interface.buttons import Botao
from src.nucleo.estilo import AMARELO_TITULO
from src.jogo.estados.base import Estado
from src.jogo.menu_botoes import MenuBotoes
from src.jogo.visual import overlay, painel_menu, texto_c


class EstadoGameOver(Estado):
    def __init__(self, jogo):
        super().__init__(jogo)
        W = constants.SCREEN_WIDTH
        x = W // 2 - 100
        self.menu_normal = MenuBotoes(jogo, [
            Botao("REINICIAR", x, 280, 200, 60, jogo.iniciar_partida),
            Botao("MENU", x, 360, 200, 60, jogo.abrir_estatisticas),
        ])
        # Morreu lutando contra o boss: dá para recomeçar SÓ a luta, sem
        # refazer o mapa (minérios, perguntas e pontuação ficam como estavam).
        xl = W // 2 - 150
        self.menu_boss = MenuBotoes(jogo, [
            Botao("TENTAR DE NOVO", xl, 270, 300, 60, self._tentar_luta_de_novo),
            Botao("REINICIAR", xl, 345, 300, 60, jogo.iniciar_partida),
            Botao("MENU", xl, 420, 300, 60, jogo.abrir_estatisticas),
        ])

    def _tentar_luta_de_novo(self):
        self.jogo.partida.reiniciar_luta_boss()

    @property
    def na_arena(self):
        return self.jogo.partida is not None and self.jogo.partida.morreu_na_arena

    @property
    def menu(self):
        return self.menu_boss if self.na_arena else self.menu_normal

    def entrar(self, **dados):
        self.menu_normal.resetar()
        self.menu_boss.resetar()

    def evento(self, ev):
        self.menu.clicar(ev)

    def controle(self, gamepad):
        self.menu.atualizar_controle(gamepad)

    def desenhar(self, tela, mouse_pos):
        jogo = self.jogo
        W = constants.SCREEN_WIDTH
        fontes = jogo.fontes
        tela.blit(jogo.fundo, (0, 0))
        tela.blit(overlay((10, 20, 80, 170)), (0, 0))
        menu = self.menu
        topo = 100
        painel_menu(tela, W // 2, topo, 460, menu.botoes[-1].rect.bottom + 40 - topo)
        titulo = texto_c(fontes.ui, "GAME OVER", constants.RED, 3)
        tela.blit(titulo, titulo.get_rect(center=(W // 2, 150)))
        pontos = texto_c(fontes.ui, f"Pontuacao Final: {jogo.partida.pontuacao}",
                         AMARELO_TITULO, 3)
        tela.blit(pontos, pontos.get_rect(center=(W // 2, 200)))
        if self.na_arena:
            dica = texto_c(fontes.titulo, "O Gorila venceu desta vez...", constants.WHITE)
            tela.blit(dica, dica.get_rect(center=(W // 2, 238)))
        menu.desenhar(tela, mouse_pos)
