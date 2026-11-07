"""
Efeitos sonoros sintetizados (o projeto só tem a trilha de fundo).

Nenhuma das versões recebidas trazia arquivos de efeito. Em vez de deixar o
combate do boss mudo — ou adicionar dependência (numpy) — os efeitos são
gerados uma vez, no início, como ondas simples em 8 bits, no espírito da
trilha "8-bit". Se algum dia existirem arquivos .wav em assets/songs/sfx/
com os mesmos nomes (ex.: "dano.wav"), eles são usados no lugar.

O volume segue o controle "Efeitos" da tela de configurações (antes esse
controle existia mas não afetava nada, porque não havia efeito nenhum).
"""

import array
import math
import random

import pygame

from src.nucleo.utils import ASSETS_PATH

TAXA = 22050
_sons = {}
_volume = 0.7


def _onda(notas, forma="quadrada", volume=0.35, ruido=0.0):
    """notas: lista de (frequência_hz, duração_ms). 0 Hz = pausa."""
    amostras = array.array("h")
    for freq, dur in notas:
        n = int(TAXA * dur / 1000)
        for i in range(n):
            env = 1.0 - i / max(1, n)          # decaimento linear
            if freq <= 0:
                v = 0.0
            elif forma == "quadrada":
                v = 1.0 if (i * freq / TAXA) % 1.0 < 0.5 else -1.0
            elif forma == "triangulo":
                f = (i * freq / TAXA) % 1.0
                v = 4 * abs(f - 0.5) - 1
            else:
                v = math.sin(2 * math.pi * freq * i / TAXA)
            if ruido:
                v = v * (1 - ruido) + random.uniform(-1, 1) * ruido
            amostras.append(int(max(-1, min(1, v * env * volume)) * 32767))
    return amostras


_RECEITAS = {
    "acerto":   lambda: _onda([(660, 70), (880, 70), (1320, 120)]),
    "erro":     lambda: _onda([(330, 110), (0, 30), (220, 280)], forma="quadrada", volume=0.6, ruido=0.1),    "dano":     lambda: _onda([(140, 90)], ruido=0.55, volume=0.5),
    "cura":     lambda: _onda([(523, 60), (659, 60), (784, 90)], forma="seno", volume=0.5),
    "arremesso": lambda: _onda([(330, 40), (250, 50)], forma="triangulo", volume=0.3),
    "rugido":   lambda: _onda([(90, 450)], ruido=0.7, volume=0.55),
    "boss_dano": lambda: _onda([(200, 60), (120, 160)], ruido=0.35, volume=0.55),
    "pancada":  lambda: _onda([(70, 260)], ruido=0.8, volume=0.6),
    "golpe":    lambda: _onda([(900, 25), (600, 45)], ruido=0.6, volume=0.25),
    "golpe_acerto": lambda: _onda([(330, 35), (180, 60)], forma="quadrada", volume=0.35),
    "golpe_imune": lambda: _onda([(1400, 30), (1100, 60)], forma="triangulo", volume=0.3),
    "pisao":    lambda: _onda([(520, 40), (300, 70)], forma="quadrada", volume=0.4),
    "vitoria":  lambda: _onda([(523, 120), (659, 120), (784, 120), (1047, 320)]),
}


def iniciar():
    """Gera (ou carrega) os efeitos. Seguro chamar sem mixer: vira no-op."""
    if not pygame.mixer.get_init():
        return
    freq, tamanho, canais = pygame.mixer.get_init()
    pasta = ASSETS_PATH / "songs" / "sfx"
    for nome, receita in _RECEITAS.items():
        arquivo = pasta / f"{nome}.wav"
        try:
            if arquivo.exists():
                _sons[nome] = pygame.mixer.Sound(str(arquivo))
                continue
            mono = receita()
            if freq != TAXA:  # reamostra de forma simples para o mixer atual
                passo = TAXA / freq
                mono = array.array("h", (mono[int(i * passo)]
                                         for i in range(int(len(mono) / passo))))
            if canais == 2:
                estereo = array.array("h")
                for v in mono:
                    estereo.append(v)
                    estereo.append(v)
                mono = estereo
            _sons[nome] = pygame.mixer.Sound(buffer=mono.tobytes())
        except (pygame.error, ValueError) as e:
            print(f"Aviso: efeito '{nome}' indisponível: {e}")


def definir_volume(valor):
    global _volume
    _volume = max(0.0, min(1.0, float(valor)))


def tocar(nome):
    som = _sons.get(nome)
    if som is None or _volume <= 0:
        return
    som.set_volume(_volume)
    som.play()
