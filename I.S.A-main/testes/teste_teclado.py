"""
Roda o jogo de verdade (o while do main.py) com teclado/mouse simulados.

Verifica o caminho MENU -> JOGAR -> nome -> cutscene (ESC pula) -> partida
-> ESC pausa -> ESC retoma, e dois bugs encontrados na auditoria:
  * ESC não pausava pelo teclado (o teste estava dentro do ramo do joystick);
  * o botão "interagir" do controle (JOYBUTTONDOWN) lia `event.key` e
    derrubava o jogo com AttributeError.

Os estados são lidos a cada frame interceptando pygame.display.flip (que a
Janela chama em apresentar()); o Jogo em execução é capturado no __init__.

Uso (a partir da raiz do projeto):
    python testes/teste_teclado.py
"""
import os
import runpy
import sys
import tempfile
import threading
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("ISA_DB", os.path.join(tempfile.mkdtemp(prefix="isa_teste_"), "estatisticas.db"))
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

import pygame  # noqa: E402

from src.jogo import app as _app  # noqa: E402

estados = []
jogos = []                       # o Jogo criado por main.py (capturado no __init__)
_init = _app.Jogo.__init__


def _init_espiao(self, *args, **kwargs):
    jogos.append(self)
    _init(self, *args, **kwargs)


_app.Jogo.__init__ = _init_espiao
_flip = pygame.display.flip


def _flip_espiao():
    estado = getattr(jogos[-1], "estado_nome", None) if jogos else None
    if estado is not None and (not estados or estados[-1] != estado):
        estados.append(estado)
    _flip()


pygame.display.flip = _flip_espiao


def tecla(k, unicode=""):
    for tipo in (pygame.KEYDOWN, pygame.KEYUP):
        pygame.event.post(pygame.event.Event(tipo, {"key": k, "mod": 0, "unicode": unicode,
                                                    "scancode": 0}))
    time.sleep(0.4)


def esperar(estado, limite=15.0):
    fim = time.time() + limite
    while time.time() < fim:
        if estados and estados[-1] == estado:
            return True
        time.sleep(0.05)
    return False


falhas = []


def roteiro():
    try:
        if not esperar("MENU", 30):
            falhas.append("não chegou ao MENU")
            return
        time.sleep(1.0)
        for tipo in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(tipo, {"pos": (400, 530), "button": 1}))
        if not esperar("LOGIN"):
            falhas.append("JOGAR não abriu a tela de nome")
            return
        for letra in "Ana":
            pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, {"text": letra}))
        time.sleep(0.2)
        tecla(pygame.K_RETURN, "\r")
        if not esperar("CUTSCENE"):
            falhas.append("cutscene não abriu")
            return
        time.sleep(0.6)
        tecla(pygame.K_ESCAPE)                       # pula a cutscene
        if not esperar("JOGANDO", 30):
            falhas.append("partida não começou depois da cutscene")
            return
        time.sleep(1.0)
        # botão interagir do controle: antes derrubava o jogo
        pygame.event.post(pygame.event.Event(pygame.JOYBUTTONDOWN,
                                             {"button": 2, "joy": 0, "instance_id": 0}))
        time.sleep(0.4)
        tecla(pygame.K_d)
        # golpe de asa pelo teclado (J): o golpe precisa ter começado
        golpe = jogos[-1].partida.golpe
        antes = golpe.inicio
        tecla(pygame.K_j)
        if golpe.inicio == antes:
            falhas.append("tecla J não deu o golpe de asa")
        time.sleep(0.5)
        antes = golpe.inicio
        tecla(pygame.K_f)
        if golpe.inicio == antes:
            falhas.append("tecla F não deu o golpe de asa")
        # Clique esquerdo no mundo deve acionar o mesmo golpe de asa.
        time.sleep(0.5)
        antes = golpe.inicio
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                             {"button": 1, "pos": (400, 300)}))
        time.sleep(0.15)
        if golpe.inicio == antes:
            falhas.append("clique esquerdo não acionou o golpe de asa")
        tecla(pygame.K_ESCAPE)                       # pausa
        if not esperar("PAUSADO", 3):
            falhas.append("ESC não pausou o jogo")
        tecla(pygame.K_ESCAPE)                       # retoma
        if not esperar("JOGANDO", 3):
            falhas.append("ESC não retomou o jogo")
    finally:
        pygame.event.post(pygame.event.Event(pygame.QUIT))


threading.Thread(target=roteiro, daemon=True).start()
try:
    runpy.run_path(os.path.join(RAIZ, "main.py"), run_name="__main__")
except SystemExit:
    pass
print("estados:", " -> ".join(str(e) for e in estados))
if falhas:
    raise SystemExit("FALHOU: " + "; ".join(falhas))
print("ok: MENU -> nome -> cutscene -> partida -> golpe (J/F) -> ESC pausa/retoma; "
      "botão do controle não derruba")
