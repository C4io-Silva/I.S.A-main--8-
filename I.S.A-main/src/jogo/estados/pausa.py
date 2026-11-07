import pygame

from src.nucleo import constants
from src.interface.buttons import Botao
from src.nucleo.estilo import AMARELO_TITULO
from src.jogo.estados.base import Estado
from src.jogo.menu_botoes import MenuBotoes
from src.jogo.partida.render import desenhar_partida
from src.jogo.visual import overlay, painel_menu, texto_c


class EstadoPausa(Estado):
    def __init__(self, jogo):
        super().__init__(jogo)
        x = constants.SCREEN_WIDTH // 2 - 100
        # "MENU" encerra a partida no meio: abre as estatísticas da sessão
        # antes de voltar ao menu.
        self.menu = MenuBotoes(jogo, [
            Botao("RETOMAR", x, 220, 200, 60, lambda: jogo.ir_para("JOGANDO")),
            Botao("MENU", x, 310, 200, 60, jogo.abrir_estatisticas),
        ])

    def entrar(self, **dados):
        self.jogo.partida.entrada.zerar_movimento()
        self.menu.resetar()

    def evento(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.jogo.ir_para("JOGANDO")
        self.menu.clicar(ev)

    def controle(self, gamepad):
        if gamepad.pausou_agora or gamepad.voltou_agora:
            self.jogo.ir_para("JOGANDO")
        else:
            self.menu.atualizar_controle(gamepad)

    def desenhar(self, tela, mouse_pos):
        desenhar_partida(
            self.jogo, self.jogo.partida, tela,
            sobreposicao=lambda t: self._desenhar_menu(t, mouse_pos),
            tremor_ativo=False, mostrar_aviso_passagem=False)

    def _desenhar_menu(self, tela, mouse_pos):
        W = constants.SCREEN_WIDTH
        tela.blit(overlay((10, 20, 80, 170)), (0, 0))
        painel_menu(tela, W // 2, 110, 380, 300)
        titulo = texto_c(self.jogo.fontes.ui, "PAUSADO", AMARELO_TITULO, 3)
        tela.blit(titulo, titulo.get_rect(center=(W // 2, 160)))
        self.menu.desenhar(tela, mouse_pos)
