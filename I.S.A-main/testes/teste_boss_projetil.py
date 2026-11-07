"""
Teste unitário do ciclo de arremessos do Gorila (veio do fork do boss).

As duas regras originais continuam as mesmas:
  1. em cada ciclo de arremessos sai EXATAMENTE um minério, numa posição
     sorteada do ciclo (o resto são bananas);
  2. o boss só é derrotado no 8º minério devolvido.

Adaptado à integração: os tipos de minério agora são "cobre"/"zinco" (antes
eram os nomes dos PNGs), o tamanho do ciclo vem de
constants.GORILA_ARREMESSOS_POR_CICLO e o dano usa a API comum dos inimigos
(Enemy.receber_dano(quantidade) via Gorila.levar_minerio()). Na derrota o
boss passa por uma animação antes de ficar `derrotado`.
"""
import os
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from src.nucleo import constants  # noqa: E402
from src.entidades.enemies.boss import Gorila  # noqa: E402

N = constants.GORILA_ARREMESSOS_POR_CICLO


class TesteProjetilBoss(unittest.TestCase):
    def test_um_minerio_em_cada_ciclo_com_posicao_variavel(self):
        gorila = Gorila.__new__(Gorila)
        gorila.lancamentos = 0

        with patch("src.entidades.enemies.boss.random.randrange", side_effect=(2, 0)):
            with patch("src.entidades.enemies.boss.random.choice", side_effect=("cobre", "zinco")):
                primeiro_ciclo = [gorila._proximo_tipo_projetil() for _ in range(N)]
                segundo_ciclo = [gorila._proximo_tipo_projetil() for _ in range(N)]

        esperado_1 = [None] * N
        esperado_1[2] = "cobre"
        esperado_2 = [None] * N
        esperado_2[0] = "zinco"
        self.assertEqual(primeiro_ciclo, esperado_1)
        self.assertEqual(segundo_ciclo, esperado_2)

    def test_boss_so_e_derrotado_no_oitavo_minerio(self):
        gorila = Gorila.__new__(Gorila)
        gorila.vida = Gorila.VIDA_MAX
        gorila.derrotado = False
        gorila.estado = "COMBATE"
        gorila.preparando = gorila.pancada = None
        gorila.projeteis, gorila.ondas = [], []
        gorila.tremor = 0

        self.assertEqual(Gorila.VIDA_MAX, 8)
        with patch("src.entidades.enemies.boss.pygame.time.get_ticks", return_value=1000):
            for _ in range(7):
                gorila.levar_minerio()
                self.assertNotEqual(gorila.estado, "DERROTA")
            gorila.levar_minerio()
        self.assertEqual(gorila.vida, 0)
        self.assertEqual(gorila.estado, "DERROTA")
        # derrotado (remoção da lista) só depois da animação de derrota
        self.assertFalse(gorila.derrotado)
        with patch("src.entidades.enemies.boss.pygame.time.get_ticks",
                   return_value=1000 + Gorila.DURACAO_DERROTA_MS + 1):
            gorila.obstaculos_proximos = lambda r: []
            gorila.rect = __import__("pygame").Rect(0, 0, 10, 10)
            gorila.pos_y, gorila.vel_y, gorila.chao_y = 0.0, 0.0, None
            gorila.update([], None)
        self.assertTrue(gorila.derrotado)


if __name__ == "__main__":
    unittest.main()
