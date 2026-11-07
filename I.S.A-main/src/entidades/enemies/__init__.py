"""
Registro dos tipos de inimigo.

O CSV marca inimigos por ID (constants.MARCADORES_MOB -> nome da classe) e o
main instancia pelo nome usando CLASSES_INIMIGO. Para adicionar um inimigo
novo:

  1. crie a classe herdando de Enemy (src/enemies/enemy.py ou arquivo novo);
  2. registre-a aqui;
  3. dê a ela um ID de marcador em constants.MARCADORES_MOB.
"""

from src.entidades.enemies.boss import Gorila
from src.entidades.enemies.enemy import Aranha, Enemy, Tucano

CLASSES_INIMIGO = {
    "Enemy": Enemy,
    "Tucano": Tucano,
    "Aranha": Aranha,
}

# O boss NÃO é um marcador de mob: nasce do marcador da arena
# (constants.TILE_AREA_BOSS) — ver src/setores.py.
CLASSE_BOSS = Gorila

__all__ = ["Enemy", "Tucano", "Aranha", "Gorila", "CLASSES_INIMIGO", "CLASSE_BOSS"]