import pygame

from src.nucleo.utils import carregar_imagem


class minerio_cobre(pygame.sprite.Sprite):
    """Minério coletável: tocar nele abre o quiz.

    `liberar()` desfaz a coleta quando o quiz é cancelado (ESC) ou quando não
    há pergunta disponível — antes o minério ficava marcado como coletado e
    sumia sem pergunta nenhuma. Depois de liberado ele ignora o jogador por
    um instante, para não reabrir o quiz no frame seguinte.
    """

    PAUSA_APOS_LIBERAR_MS = 1500

    def __init__(self, nome_arquivo, x, y, tamanho=(40, 40)):
        super().__init__()
        self.image = carregar_imagem("itens", nome_arquivo, tamanho)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.coletado = False
        self._ignorar_ate = 0

    def verificar_coleta(self, player):
        if self.coletado or pygame.time.get_ticks() < self._ignorar_ate:
            return False
        if self.rect.colliderect(player.rect):
            self.coletado = True
            return True
        return False

    def liberar(self):
        self.coletado = False
        self._ignorar_ate = pygame.time.get_ticks() + self.PAUSA_APOS_LIBERAR_MS

    def draw(self, surface, camera_x, camera_y):
        if not self.coletado:
            surface.blit(self.image, self.rect.move(-camera_x, -camera_y))
