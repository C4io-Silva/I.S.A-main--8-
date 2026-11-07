import pygame

from src.nucleo.utils import carregar_imagem


class IntroLogo:
    """Logo em tela preta: fade in, pausa e fade out (4 s no total)."""

    def __init__(self, largura, altura, callback_fim,
                 arquivo="salvador_arena_widescreen_branco_preto.png",
                 duracao=4000, fade_in=1000, fade_out=1000, escala=0.6):
        self.largura, self.altura = largura, altura
        self.callback_fim = callback_fim
        self.duracao, self.fade_in, self.fade_out = duracao, fade_in, fade_out
        self.t = 0
        self.terminou = False
        self.imagem = None
        try:
            img = carregar_imagem("intro", arquivo).convert_alpha()
            # cabe na tela sem distorcer; "escala" deixa uma margem em volta
            f = min(largura / img.get_width(), altura / img.get_height()) * escala
            self.imagem = pygame.transform.smoothscale(
                img, (int(img.get_width() * f), int(img.get_height() * f)))
        except Exception as e:  # noqa: BLE001
            print(f"Aviso: logo de abertura não carregou: {e}")
        self.veu = pygame.Surface((largura, altura))
        self.veu.fill((0, 0, 0))

    def iniciar(self):
        self.t = 0
        self.terminou = False

    def pular(self):
        self._finalizar()

    def _finalizar(self):
        if not self.terminou:
            self.terminou = True
            self.callback_fim()

    def handle_event(self, event):
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self._finalizar()

    def atualizar(self, dt_ms):
        self.t += dt_ms
        if self.imagem is None or self.t >= self.duracao:
            self._finalizar()

    def desenhar(self, screen):
        screen.fill((0, 0, 0))
        if self.imagem:
            screen.blit(self.imagem, self.imagem.get_rect(
                center=(self.largura // 2, self.altura // 2)))
        if self.t < self.fade_in:
            opacidade = self.t / self.fade_in
        elif self.t > self.duracao - self.fade_out:
            opacidade = (self.duracao - self.t) / self.fade_out
        else:
            opacidade = 1.0
        opacidade = max(0.0, min(1.0, opacidade))
        self.veu.set_alpha(int(255 * (1 - opacidade)))
        screen.blit(self.veu, (0, 0))