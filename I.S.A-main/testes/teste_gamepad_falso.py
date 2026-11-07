"""Roda o jogo headless com um CONTROLE FALSO plugado.

Exercita os caminhos que so existem quando gamepad.conectado eh True:
navegacao de menu, confirmacao, eixo analogico no movimento, pausa no Start.
"""
import os
import sys
import threading
import time
import runpy

os.environ["SDL_VIDEODRIVER"] = "dummy"
# Banco de estatísticas temporário: os testes nunca gravam no estatisticas.db real.
import tempfile  # noqa: E402
os.environ.setdefault("ISA_DB", os.path.join(tempfile.mkdtemp(prefix="isa_teste_"), "estatisticas.db"))
os.environ["SDL_AUDIODRIVER"] = "dummy"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

import pygame

estado = {"eixo_x": 0.0, "eixo_y": 0.0, "botoes": set()}


class ControleFalso:
    def __init__(self, indice=0):
        self.indice = indice

    def init(self):
        pass

    def get_name(self):
        return "Controle Falso de Teste"

    def get_numaxes(self):
        return 4

    def get_axis(self, i):
        return estado["eixo_x"] if i == 0 else (estado["eixo_y"] if i == 1 else 0.0)

    def get_numhats(self):
        return 1

    def get_hat(self, i):
        return (0, 0)

    def get_numbuttons(self):
        return 12

    def get_button(self, i):
        return i in estado["botoes"]


pygame.joystick.get_count = lambda: 1
pygame.joystick.Joystick = ControleFalso


def aperta(indice, dur=0.12):
    estado["botoes"].add(indice)
    time.sleep(dur)
    estado["botoes"].discard(indice)
    time.sleep(0.25)


# Estado atual do jogo, lido a cada frame em pygame.display.flip (que a Janela
# chama em apresentar()); o Jogo em execução é capturado no __init__. Permite ao roteiro ESPERAR a partida e responder um
# quiz que apareça — os mapas novos têm minérios logo perto do spawn.
from src.jogo import app as _app  # noqa: E402

estado_jogo = [None]
jogos = []
_init = _app.Jogo.__init__


def _init_espiao(self, *args, **kwargs):
    jogos.append(self)
    _init(self, *args, **kwargs)


_app.Jogo.__init__ = _init_espiao
_flip = pygame.display.flip


def _flip_espiao():
    estado_jogo[0] = getattr(jogos[-1], "estado_nome", None) if jogos else None
    _flip()


pygame.display.flip = _flip_espiao


def esperar_estado(nome, limite=15.0):
    fim = time.time() + limite
    while time.time() < fim:
        if estado_jogo[0] == nome:
            return True
        time.sleep(0.05)
    return False


quizzes_respondidos = [0]


def jogando(segundos):
    """Espera `segundos` de PARTIDA; se um quiz abrir, responde com A
    (direcional + confirmar, o caminho do controle) e segue."""
    fim = time.time() + segundos
    while time.time() < fim:
        if estado_jogo[0] == "QUIZ":
            aperta(0)                  # A = confirma a alternativa destacada
            quizzes_respondidos[0] += 1
            esperar_estado("JOGANDO", 5)
            fim += 2                   # devolve o tempo gasto no quiz
        time.sleep(0.05)


def roteiro():
    time.sleep(6)
    # menu: desce e sobe a selecao, depois confirma no item selecionado
    estado["eixo_y"] = 1.0
    time.sleep(0.6)
    estado["eixo_y"] = 0.0
    time.sleep(0.3)
    estado["eixo_y"] = -1.0
    time.sleep(0.4)
    estado["eixo_y"] = 0.0
    time.sleep(0.3)
    # clica JOGAR com o mouse: abre a tela de registro do nome
    for tipo in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
        pygame.event.post(pygame.event.Event(tipo, {"pos": (400, 530), "button": 1}))
    time.sleep(0.8)
    # digita o nome e confirma com Enter -> cutscene
    for letra in "Teste":
        pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, {"text": letra}))
    pygame.event.post(pygame.event.Event(
        pygame.KEYDOWN, {"key": pygame.K_RETURN, "mod": 0, "unicode": "\r", "scancode": 0}))
    # cutscene: A avança uma imagem, B pula o resto -> a partida comeca
    esperar_estado("CUTSCENE")
    time.sleep(0.6)
    aperta(0)
    aperta(1)
    if not esperar_estado("JOGANDO"):
        falhas.append("a cutscene não terminou com o controle")
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        return
    time.sleep(0.5)
    # movimento analogico parcial (deve andar devagar, nao teleportar)
    estado["eixo_x"] = 0.45
    jogando(1.2)
    estado["eixo_x"] = 1.0
    jogando(1.2)
    aperta(0)          # pulo
    jogando(0.6)
    aperta(1)          # B -> golpe de asa
    jogando(0.5)
    aperta(3)          # Y -> golpe de asa (alternativa)
    jogando(0.5)
    estado["eixo_x"] = -1.0
    jogando(1.0)
    # zona morta: valor abaixo do limiar precisa ser ignorado
    estado["eixo_x"] = 0.1
    jogando(1.0)
    estado["eixo_x"] = 0.0
    jogando(0.3)
    aperta(7)          # Start -> pausa
    if not esperar_estado("PAUSADO", 3):
        falhas.append("Start não pausou")
    estado["eixo_y"] = 1.0   # navega no menu de pausa
    time.sleep(0.5)
    estado["eixo_y"] = 0.0
    time.sleep(0.4)
    aperta(7)          # Start -> retoma
    if not esperar_estado("JOGANDO", 3):
        falhas.append("Start não retomou")
    time.sleep(1.0)
    pygame.event.post(pygame.event.Event(pygame.QUIT))


falhas = []


# Conta os frames de partida de verdade: sem isto o teste "passava" mesmo
# que o jogo nunca saísse do menu (foi o que aconteceu quando JOGAR passou a
# abrir a tela de nome).
from src.entidades import character  # noqa: E402

frames_jogados = [0]
_move_original = character.Character.move


def _move_contado(self, dx, obstacles):
    frames_jogados[0] += 1
    return _move_original(self, dx, obstacles)


character.Character.move = _move_contado

# Conta os golpes de asa que de fato COMEÇARAM (não só pedidos).
from src.sistemas import combate  # noqa: E402

golpes = [0]
_atualizar_golpe = combate.GolpeAsa.atualizar


def _atualizar_contado(self, agora, *a, **k):
    antes = self.inicio
    r = _atualizar_golpe(self, agora, *a, **k)
    if self.inicio != antes:
        golpes[0] += 1
    return r


combate.GolpeAsa.atualizar = _atualizar_contado

threading.Thread(target=roteiro, daemon=True).start()
runpy.run_path(os.path.join(RAIZ, "main.py"), run_name="__main__")
if frames_jogados[0] < 60:
    raise SystemExit(f"FALHOU: a partida nao comecou (frames jogados: {frames_jogados[0]})")
if falhas:
    raise SystemExit("FALHOU: " + "; ".join(falhas))
if golpes[0] < 2:
    raise SystemExit(f"FALHOU: botões B/Y não deram golpe de asa (golpes: {golpes[0]})")
print(f"JOGO RODOU COM CONTROLE FALSO SEM ERRO ({frames_jogados[0]} frames de partida, "
      f"{golpes[0]} golpes de asa, {quizzes_respondidos[0]} quiz(zes) respondido(s) com o controle)")