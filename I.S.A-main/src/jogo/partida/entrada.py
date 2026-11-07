"""Teclas e botões de jogo mantidos entre frames."""

from dataclasses import dataclass


@dataclass
class Entrada:
    esquerda: bool = False
    direita: bool = False
    pulo: bool = False
    # Borda, não estado: o loop zera a cada frame, os eventos ligam e a
    # checagem de passagens consome. Sem isso, segurar E entraria na
    # passagem, sairia e entraria de novo a cada frame.
    interagir: bool = False

    def zerar_movimento(self):
        self.esquerda = self.direita = self.pulo = False
