"""
Item de cura (maçã) — veio do fork do boss (src/item_cura/item_cura.py) e
foi movido para src/itens/, junto do minério.

Só é consumido se o jogador estiver ferido: passar por cima com a vida cheia
não gasta a maçã. Marcador no CSV: constants.TILE_ITEM_CURA (96).
"""
import pygame

from src.nucleo import constants
from src.sistemas import sons
from src.nucleo.utils import carregar_imagem


class ItemCura(pygame.sprite.Sprite):
    def __init__(self, nome_arquivo, x, y, tamanho=(40, 40), cura=None):
        super().__init__()
        self.image = carregar_imagem("itens", nome_arquivo, tamanho)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.cura = constants.ITEM_CURA_VIDA if cura is None else cura
        self.coletado = False

    def verificar_coleta(self, player):
        if (
            not self.coletado
            and player
            and player.alive
            and self.rect.colliderect(player.rect)
            and player.player_health < constants.PLAYER_HEALTH
        ):
            self.coletado = True
            player.player_health = min(player.player_health + self.cura,
                                       constants.PLAYER_HEALTH)
            sons.tocar("cura")
            return True
        return False

    def draw(self, surface, camera_x, camera_y):
        if not self.coletado:
            # Flutua de leve para chamar atenção.
            dy = int(3 * ((pygame.time.get_ticks() // 120) % 4 in (1, 2)))
            surface.blit(self.image, self.rect.move(-camera_x, -camera_y - dy))
