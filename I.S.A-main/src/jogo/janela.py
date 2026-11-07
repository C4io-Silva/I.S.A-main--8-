"""
Janela real + superfície virtual.

O jogo inteiro é desenhado numa superfície virtual de altura fixa (600) e, no
fim de cada frame, ela é esticada para caber na janela real.

A ALTURA é travada em 600: é ela que define o zoom do mundo e o tamanho de
toda a interface. A LARGURA acompanha o formato do monitor, para que não
sobrem barras pretas nas laterais em telas widescreen (16:9 -> 1067x600;
4:3 -> 800x600).
"""

import pygame

from src.nucleo import constants

ALTURA = 600
LARGURA_MIN = 800        # nunca mais estreito que 4:3
ASPECTO_MAX = 2.0        # trava ultrawide, senão a UI fica perdida no meio

_EVENTOS_COM_POS = (
    pygame.MOUSEBUTTONDOWN,
    pygame.MOUSEBUTTONUP,
    pygame.MOUSEMOTION,
)


class Janela:
    def __init__(self):
        self.largura = LARGURA_MIN
        self.altura = ALTURA
        self.real = None        # superfície da janela/monitor: só recebe o blit final
        self.tela = None        # superfície virtual: TUDO é desenhado aqui
        self.fullscreen = False
        self._escala = 1.0
        self._offset_x = 0
        self._offset_y = 0
        self._tamanho_destino = (LARGURA_MIN, ALTURA)
        self._alvo = None       # recorte da janela que recebe a imagem escalada
        self._escala_direta = True

        constants.SCREEN_WIDTH = self.largura
        constants.SCREEN_HEIGHT = self.altura

    # ── criação ──────────────────────────────────────────────────────────────
    def _largura_para_monitor(self):
        info = pygame.display.Info()
        if info.current_h <= 0:
            return LARGURA_MIN
        aspecto = info.current_w / info.current_h
        aspecto = max(LARGURA_MIN / ALTURA, min(aspecto, ASPECTO_MAX))
        largura = int(round(ALTURA * aspecto / 2)) * 2  # número par
        return max(LARGURA_MIN, largura)

    def abrir(self, fullscreen=False):
        """Cria ou recria a janela real. A superfície virtual é preservada."""
        self.fullscreen = fullscreen

        if self.tela is None:
            # A largura virtual é decidida uma única vez, na primeira chamada,
            # para que alternar F11 não mude o enquadramento do jogo.
            self.largura = self._largura_para_monitor()
            constants.SCREEN_WIDTH = self.largura
            constants.SCREEN_HEIGHT = self.altura

        if fullscreen:
            self.real = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.real = pygame.display.set_mode((self.largura, self.altura))

        if self.tela is None:
            self.tela = pygame.Surface((self.largura, self.altura)).convert()
        self._recalcular_escala()

    def alternar_fullscreen(self):
        """Alterna janela/tela cheia. Nada além da janela real precisa mudar."""
        self.abrir(not self.fullscreen)

    def _recalcular_escala(self):
        jw, jh = self.real.get_size()
        # min() preserva a proporção; com a largura casando com o monitor,
        # na prática não sobra barra nenhuma em tela cheia.
        self._escala = min(jw / self.largura, jh / self.altura)
        destino = (int(self.largura * self._escala), int(self.altura * self._escala))
        self._tamanho_destino = destino
        self._offset_x = (jw - destino[0]) // 2
        self._offset_y = (jh - destino[1]) // 2
        self._alvo = None
        if destino != (jw, jh):
            self.real.fill((0, 0, 0))
            recorte = pygame.Rect(self._offset_x, self._offset_y, *destino)
            self._alvo = self.real.subsurface(recorte)
        self._escala_direta = True

    # ── apresentação ─────────────────────────────────────────────────────────
    def apresentar(self):
        """Escala a superfície virtual para a janela e atualiza o vídeo."""
        if self._alvo is None:
            self.real.blit(self.tela, (0, 0))
        else:
            if self._offset_x or self._offset_y:
                self.real.fill((0, 0, 0))  # barras do letterbox
            self._escalar_para_alvo()
        pygame.display.flip()

    def _escalar_para_alvo(self):
        # Escala direto no recorte da janela, sem alocar uma Surface nova por frame.
        if self._escala_direta:
            try:
                pygame.transform.scale(self.tela, self._tamanho_destino, self._alvo)
                return
            except (ValueError, pygame.error):
                self._escala_direta = False   # formato incompatível: cai no caminho lento
        self._alvo.blit(pygame.transform.scale(self.tela, self._tamanho_destino), (0, 0))

    # ── coordenadas ──────────────────────────────────────────────────────────
    def pos_virtual(self, pos):
        """Converte coordenada da janela real para coordenada da virtual."""
        x = (pos[0] - self._offset_x) / self._escala
        y = (pos[1] - self._offset_y) / self._escala
        return (int(x), int(y))

    def mouse_virtual(self):
        return self.pos_virtual(pygame.mouse.get_pos())

    def converter_evento(self, evento):
        """
        Reescreve as coordenadas de eventos de mouse para o espaço virtual.
        Sem isso, um clique em tela cheia chegaria aos botões com a coordenada
        do monitor (ex: 1600, 900) em vez da coordenada do jogo.
        """
        if evento.type not in _EVENTOS_COM_POS:
            return evento
        dados = dict(evento.__dict__)
        dados["pos"] = self.pos_virtual(dados["pos"])
        if "rel" in dados:
            rx, ry = dados["rel"]
            dados["rel"] = (int(rx / self._escala), int(ry / self._escala))
        return pygame.event.Event(evento.type, dados)
