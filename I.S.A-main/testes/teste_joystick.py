"""Teste de fumaca do modulo de joystick (sem controle fisico)."""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import pygame
from src.nucleo import constants
from src.sistemas.joystick import (
    GerenciadorJoystick,
    acionar,
    centro_do_botao,
    navegar,
    ordem_de_navegacao,
)

pygame.init()
pygame.display.set_mode((800, 600))
from src.interface.buttons import Botao, BotaoConfig, BotaoSair

g = GerenciadorJoystick()
assert not g.conectado, "nao deveria achar controle no sandbox"
g.atualizar()
assert g.eixo_x == 0.0 and not g.pulou_agora and g.scroll == 0
print("ok: sem controle, tudo neutro e sem crash")

# eventos de conexao/remocao nao podem estourar
for tipo in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
    g.processar_evento(pygame.event.Event(tipo, {"device_index": 0}))
print("ok: eventos de conexao tratados")

# --- pulso com repeticao ---
class Falso(GerenciadorJoystick):
    def __init__(self):
        self.joystick = object()
        self.nome = "falso"
        self._botoes = {}
        self._botoes_antes = {}
        self.eixo_x = self.eixo_y = 0.0
        self.nav_x = self.nav_y = 0
        self._dir_x_antes = self._dir_y_antes = 0
        self._t_repete_x = self._t_repete_y = 0

f = Falso()
p1 = f._pulso(1.0, 0, 0, 1000)
assert p1[0] == 1, p1
p2 = f._pulso(1.0, p1[1], p1[2], 1050)
assert p2[0] == 0, "segurar nao deve repetir antes do atraso"
p3 = f._pulso(1.0, p2[1], p2[2], 1000 + constants.JOY_REPETICAO_ATRASO + 1)
assert p3[0] == 1, "deveria repetir depois do atraso"
assert f._pulso(0.1, 1, 0, 2000)[0] == 0, "zona morta / limiar falhou"
print("ok: pulso de navegacao com atraso e repeticao")

# --- navegacao entre botoes de tipos diferentes ---
chamados = []
botoes = [
    Botao("JOGAR", 300, 500, 200, 60, lambda: chamados.append("jogar")),
    BotaoSair(cx=700, cy=38, raio=30, acao=lambda: chamados.append("sair")),
    BotaoConfig(cx=762, cy=38, raio=30, acao=lambda: chamados.append("config")),
    Botao("LOGIN", 300, 400, 200, 60, lambda: chamados.append("login")),
]
assert centro_do_botao(botoes[1]) == (700, 38), "centro de botao circular"
ordem = ordem_de_navegacao(botoes)
assert ordem == [1, 2, 3, 0], f"ordem visual errada: {ordem}"
i = 1
i = navegar(botoes, i, 1)
assert i == 2
i = navegar(botoes, i, 1)
assert i == 3
i = navegar(botoes, i, 1)
assert i == 0
i = navegar(botoes, i, 1)
assert i == 1, "deveria circular de volta ao primeiro"
i = navegar(botoes, i, -1)
assert i == 0, "navegacao reversa"
assert acionar(botoes, 3) and chamados == ["login"]
print("ok: navegacao visual, ciclo e acionamento")

print("TODOS OS TESTES PASSARAM")
