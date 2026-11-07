import pygame

from src.nucleo import constants
from src.interface.buttons import Botao, BotaoConfig, BotaoSair
from src.jogo.estados.base import Estado
from src.jogo.intro_personagem import IntroPersonagem
from src.jogo.menu_botoes import MenuBotoes
from src.jogo.visual import veu_topo


class EstadoMenu(Estado):
    def __init__(self, jogo):
        super().__init__(jogo)
        W = constants.SCREEN_WIDTH
        # Com a largura virtual variável, posições fixas deixariam os botões
        # descentralizados: JOGAR centraliza em W; sair e configurações
        # ancoram na borda direita. JOGAR abre a tela de registro do nome
        # (TelaLogin) antes da partida: o nome vai para o PDF.
        self.menu = MenuBotoes(jogo, [
            Botao("JOGAR", W // 2 - 100, 500, 200, 60, lambda: jogo.ir_para("LOGIN")),
            BotaoSair(cx=W - 100, cy=38, raio=30, acao=jogo.encerrar),
            BotaoConfig(cx=W - 38, cy=38, raio=30,
                        acao=lambda: jogo.ir_para("CONFIGURACOES")),
        ])
        self.personagem = IntroPersonagem()

    def evento(self, ev):
        self.menu.clicar(ev)
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.personagem.clicar(ev.pos)

    def controle(self, gamepad):
        self.menu.atualizar_controle(gamepad)

    def atualizar(self, dt_ms):
        self.personagem.atualizar()

    def desenhar(self, tela, mouse_pos):
        jogo = self.jogo
        tela.blit(jogo.fundo, (0, 0))
        tela.blit(veu_topo(), (0, 0))
        logo = jogo.titulo_logo
        tela.blit(logo, logo.get_rect(center=(constants.SCREEN_WIDTH // 2, 110)))
        self.menu.desenhar(tela, mouse_pos)
        self.personagem.desenhar(tela, self.menu.botoes)   # por cima dos botões
