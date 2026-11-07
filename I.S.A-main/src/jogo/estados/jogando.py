import pygame

from src.nucleo import constants
from src.jogo.estados.base import Estado
from src.jogo.partida.render import desenhar_partida

TECLAS_ESQUERDA = (pygame.K_a, pygame.K_LEFT)
TECLAS_DIREITA = (pygame.K_d, pygame.K_RIGHT)
TECLAS_PULO = (pygame.K_w, pygame.K_UP, pygame.K_SPACE)
# Interagir com o cenário (entrar numa passagem): fica junto do pulo/ESC para
# quem joga só de teclado não precisar tirar a mão do WASD.
TECLAS_INTERAGIR = (pygame.K_e, pygame.K_RETURN)
TECLAS_GOLPE = (pygame.K_j, pygame.K_f)


class EstadoJogando(Estado):
    def evento(self, ev):
        jogo = self.jogo
        partida = jogo.partida
        entrada = partida.entrada
        if ev.type == pygame.KEYDOWN:
            if ev.key in TECLAS_ESQUERDA:
                entrada.esquerda = True
            if ev.key in TECLAS_DIREITA:
                entrada.direita = True
            if ev.key in TECLAS_PULO:
                entrada.pulo = True
            if ev.key in TECLAS_INTERAGIR:
                entrada.interagir = True
            if ev.key in TECLAS_GOLPE:
                partida.golpe.pedir()
            if ev.key == pygame.K_ESCAPE and not jogo.transicao.ativa:
                jogo.ir_para("PAUSADO")
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            # Ataque só na partida; menus e quiz mantêm o clique normal. Usa o
            # mesmo buffer/cooldown do teclado e do controle.
            if not jogo.transicao.ativa:
                partida.golpe.pedir()
        elif (ev.type == pygame.JOYBUTTONDOWN
              and ev.button == constants.JOY_BOTAO_INTERAGIR):
            entrada.interagir = True
        elif ev.type == pygame.KEYUP:
            if ev.key in TECLAS_ESQUERDA:
                entrada.esquerda = False
            if ev.key in TECLAS_DIREITA:
                entrada.direita = False

    def controle(self, gamepad):
        jogo = self.jogo
        partida = jogo.partida
        if (gamepad.acabou_de_apertar(constants.JOY_BOTAO_ATAQUE)
                or gamepad.acabou_de_apertar(constants.JOY_BOTAO_ATAQUE_ALT)):
            partida.golpe.pedir()
        if gamepad.pulou_agora:
            partida.entrada.pulo = True
        if gamepad.pausou_agora and not jogo.transicao.ativa:
            jogo.ir_para("PAUSADO")

    def atualizar(self, dt_ms):
        partida = self.jogo.partida
        if partida and partida.player:
            partida.atualizar_jogando(dt_ms)

    def desenhar(self, tela, mouse_pos):
        desenhar_partida(self.jogo, self.jogo.partida, tela)
