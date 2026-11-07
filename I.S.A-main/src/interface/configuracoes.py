import pygame

PRETO          = (0,   0,   0)
BRANCO         = (255, 255, 255)
AMARELO        = (241, 187, 52)
AMARELO_ESCURO = (196, 140, 25)


class BotaoSimples:
    """Botão comum para ações como Créditos, Voltar etc."""
    def __init__(self, texto, x, y, largura, altura, acao=None):
        self.texto  = texto
        self.rect   = pygame.Rect(x, y, largura, altura)
        self.acao   = acao

    def desenhar(self, tela, fonte, mouse_pos):
        cor = AMARELO_ESCURO if self.rect.collidepoint(mouse_pos) else AMARELO
        pygame.draw.rect(tela, cor,   self.rect, border_radius=12)
        pygame.draw.rect(tela, PRETO, self.rect, 3, border_radius=12)
        label = fonte.render(self.texto, True, PRETO)
        tela.blit(label, label.get_rect(center=self.rect.center))

    def handle_event(self, evento):
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if self.rect.collidepoint(evento.pos) and self.acao:
                self.acao()
