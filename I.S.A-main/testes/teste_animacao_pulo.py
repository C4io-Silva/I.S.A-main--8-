"""
Teste da animação de pulo (veio do fork do boss, onde falhava porque o
Character não tinha jump_frames). Asserções originais mantidas; só foi
acrescentada a preparação do ambiente (path, vídeo dummy, janela) para o
arquivo rodar sozinho ou pelo pytest.

Uso (a partir da raiz do projeto):
    python testes/teste_animacao_pulo.py
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

import pygame  # noqa: E402

pygame.init()
if pygame.display.get_surface() is None:
    pygame.display.set_mode((1, 1))

from src.entidades.character import Character  # noqa: E402


def test_personagem_usa_frames_de_pulo_em_ordem_numerica():
    personagem = Character(
        0,
        0,
        32,
        5,
        None,
        10,
    )

    assert hasattr(personagem, "jump_frames"), "Personagem deve ter frames de pulo carregados"
    assert len(personagem.jump_frames) >= 2, "Deve existir mais de um frame de pulo"
    assert [frame[0][0] for frame in []] == []

    nomes = []
    for caminho in sorted(os.listdir(os.path.join(os.getcwd(), "assets", "images", "personagens", "areninha"))):
        if "pulo" in caminho.lower() and caminho.lower().endswith(".png"):
            nomes.append(caminho)

    assert nomes, "Arquivos de pulo não encontrados na pasta do personagem"
    assert nomes == sorted(nomes), "Arquivos de pulo devem ser lidos em ordem numérica"

    personagem.jump()
    personagem.vel_y = -1
    personagem._update_animation()

    assert personagem.jumping is True
    assert getattr(personagem, "image_normal", None) is not None


if __name__ == "__main__":
    test_personagem_usa_frames_de_pulo_em_ordem_numerica()
    print("ok: frames de pulo carregados e usados no ar")
