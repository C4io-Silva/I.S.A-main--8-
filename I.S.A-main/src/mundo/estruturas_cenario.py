"""Grandes marcos nao colidiveis, atras dos tiles e do jogador.
Arquitetura visual sem interferir em fisica, portais, minerios ou inimigos.
Imagens geradas em tamanho nativo; expandidas por SCALE com nearest neighbor.
"""
import json
import pygame
from src.nucleo import constants
from src.nucleo.utils import ASSETS_PATH

class EstruturasCenario:
    def __init__(self,nome):
        path=ASSETS_PATH/'levels'/'estruturas_cenario.json'
        self.itens=[]
        if not path.exists():return
        data=json.loads(path.read_text(encoding='utf-8'))
        cache={}
        for item in data.get(nome,[]):
            nome_arq=item['imagem']
            if nome_arq not in cache:
                img=pygame.image.load(str(ASSETS_PATH/'images'/'cenarios'/nome_arq)).convert_alpha()
                cache[nome_arq]=pygame.transform.scale(img,(img.get_width()*constants.SCALE,img.get_height()*constants.SCALE))
            sprite=cache[nome_arq];w,h=sprite.get_size();t=constants.TILE_SIZE
            x=int(item['coluna']*t-w//2);y=int(item['base']*t-h)
            self.itens.append((pygame.Rect(x,y,w,h),sprite))

    def render(self,surface,camera_x,camera_y):
        viewport=pygame.Rect(camera_x,camera_y,constants.SCREEN_WIDTH,constants.SCREEN_HEIGHT)
        for rect,sprite in self.itens:
            if rect.colliderect(viewport):surface.blit(sprite,(rect.x-camera_x,rect.y-camera_y))
