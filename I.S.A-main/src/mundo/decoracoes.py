"""Camada de decoracao independente das colisoes e dos marcadores.

Os IDs (100..117) sao exclusivamente visuais. Recursos cacheados por arquivo;
renderiza apenas as celulas no enquadramento atual.
"""
from pathlib import Path
import csv
import pygame
from src.nucleo import constants
from src.nucleo.utils import ASSETS_PATH

from src.mundo.decoracoes_offline import ARTE

class DecoracaoSetor:
    def __init__(self, nome, linhas, colunas):
        caminho = ASSETS_PATH / 'levels' / 'decoracoes' / f'{nome}_decor.csv'
        self.grade = [[-1] * colunas for _ in range(linhas)]
        self.sprites = {}
        if not caminho.exists():
            return  # compatibilidade com saves/projetos antigos
        with caminho.open(encoding='utf-8-sig', newline='') as fp:
            grade = [[int(v) for v in row] for row in csv.reader(fp) if row]
        if len(grade) != linhas or any(len(row) != colunas for row in grade):
            raise ValueError(f'Decoracao {nome}: CSV incompativel com setor {linhas}x{colunas}')
        ids = {v for row in grade for v in row if v != -1}
        if ids - ARTE.keys():
            raise ValueError(f'Decoracao {nome}: IDs desconhecidos: {sorted(ids - ARTE.keys())}')
        self.grade = grade
        for tipo in ids:
            caminho_img = ASSETS_PATH / 'images' / 'tiles' / ARTE[tipo]
            img = pygame.image.load(str(caminho_img)).convert_alpha()
            self.sprites[tipo] = pygame.transform.scale(img, (constants.TILE_SIZE, constants.TILE_SIZE))

    def render(self, surface, camera_x, camera_y):
        """Nenhuma Surface criada por frame; culling bidimensional de celulas."""
        T = constants.TILE_SIZE
        left = max(0, int(camera_x) // T)
        right = min(len(self.grade[0]), int((camera_x + constants.SCREEN_WIDTH) // T) + 2)
        top = max(0, int(camera_y) // T)
        bottom = min(len(self.grade), int((camera_y + constants.SCREEN_HEIGHT) // T) + 2)
        for y in range(top, bottom):
            row = self.grade[y]
            for x in range(left, right):
                sprite = self.sprites.get(row[x])
                if sprite is not None:
                    surface.blit(sprite, (x*T - camera_x, y*T - camera_y))
