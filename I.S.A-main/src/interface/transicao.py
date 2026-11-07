"""
Fade Out -> (callback no ponto mais escuro) -> Fade In.

Este objeto não sabe nada sobre regiões, spawn ou ambiente — só anima um
véu preto de 0 a 255 (opaco) e de volta a 0, e chama uma função exatamente
uma vez, no instante em que a tela está 100% preta. Quem decide o que essa
função faz é main.py: reposicionar o player, trocar o ambiente ativo,
reajustar a câmera. Essa separação é proposital — o mesmo `Transicao`
poderia futuramente esconder outra coisa (trocar de fase, por exemplo) sem
precisar mudar uma linha aqui.

Enquanto `ativa` for True, main.py NÃO deve processar movimento do player
nem update() dos inimigos (ver o game loop) — é isso que impede o
"Player não deve continuar se movimentando" e "inimigos não devem causar
comportamentos inesperados" pedidos na especificação da feature.
"""

import pygame


class Transicao:
    DURACAO_FADE_MS = 450  # tempo de CADA metade (escurecer OU clarear)

    def __init__(self):
        self.ativa = False
        self.alpha = 0.0
        self._escurecendo = False
        self._callback = None
        self._callback_executado = False
        self._overlay = None  # Surface preta, alocada uma vez (ver desenhar)

    def iniciar(self, callback):
        """
        Começa um Fade Out. `callback` roda uma única vez, no instante em
        que a tela fica completamente preta (ver `atualizar`). Chamar de
        novo enquanto já está ativa não faz nada — evita reentrância se o
        player, por algum motivo, ainda estiver sobrepondo o tile de
        passagem quando a transição já tiver começado.
        """
        if self.ativa:
            return
        self.ativa = True
        self._escurecendo = True
        self.alpha = 0.0
        self._callback = callback
        self._callback_executado = False

    def atualizar(self, dt_ms):
        if not self.ativa:
            return
        passo = 255.0 * dt_ms / self.DURACAO_FADE_MS
        if self._escurecendo:
            self.alpha = min(255.0, self.alpha + passo)
            if self.alpha >= 255.0:
                # Tela 100% preta: momento seguro pra reposicionar o player e
                # trocar o ambiente sem o jogador ver nada acontecer.
                if not self._callback_executado:
                    if self._callback:
                        self._callback()
                    self._callback_executado = True
                self._escurecendo = False
        else:
            self.alpha = max(0.0, self.alpha - passo)
            if self.alpha <= 0.0:
                self.ativa = False

    def desenhar(self, surface):
        if self.alpha <= 0.0:
            return
        if self._overlay is None or self._overlay.get_size() != surface.get_size():
            self._overlay = pygame.Surface(surface.get_size())
            self._overlay.fill((0, 0, 0))
        self._overlay.set_alpha(int(self.alpha))
        surface.blit(self._overlay, (0, 0))
