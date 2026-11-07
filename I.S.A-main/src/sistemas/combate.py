"""
Combate da Areninha contra os inimigos comuns — o único sistema de combate
do jogo (o Gorila tem a mecânica própria das perguntas, em
src/enemies/boss.py, e é imune a isto).

Duas formas de ferir um inimigo, as duas passando por
Enemy.receber_golpe() (vida, piscar, barrinha, atordoamento, empurrão):

  * GOLPE DE ASA (tecla J/F, botão B/Y do controle): rajada curta na frente
    da Areninha. Funciona parada, andando e no ar. Tem antecipação curta
    (GOLPE_INICIO_MS), janela de acerto (GOLPE_ATIVO_MS) e cooldown
    (GOLPE_COOLDOWN_MS). Cada golpe acerta cada inimigo NO MÁXIMO UMA VEZ.
    Apertar um pouco antes do fim do cooldown guarda o pedido
    (GOLPE_BUFFER_MS), para o controle não "engolir" toques.
  * PISÃO: cair em cima do inimigo (Enemy.check_player_collision).

Equilíbrio (constants.py): inimigos comuns têm 2 de vida; o golpe tira 1, o
pisão tira 2. Derrotar inimigo não dá pontos — a pontuação continua sendo
dos acertos no quiz; o jogo conta os derrotados só para a tela de vitória.

Este módulo também desenha os efeitos de combate (arco do golpe, faíscas
de impacto, "puf" da derrota), para que só exista UMA lista de efeitos.
"""

import math
import random

import pygame

from src.nucleo import constants
from src.sistemas import sons

DURACAO_PUF_MS = 350
DURACAO_FAISCA_MS = 220


class GolpeAsa:
    """Estado do golpe de asa da Areninha (um por partida)."""

    def __init__(self):
        self.reiniciar()

    def reiniciar(self):
        self.inicio = -10 ** 9       # ms do último golpe iniciado
        self.pedido_ate = 0          # ms até quando um pedido fica guardado
        self.direcao = 1
        self.atingidos = set()

    # ── entrada ───────────────────────────────────────────────────────────
    def pedir(self, agora=None):
        """Tecla/botão de ataque apertado (borda, não estado)."""
        agora = pygame.time.get_ticks() if agora is None else agora
        self.pedido_ate = agora + constants.GOLPE_BUFFER_MS

    # ── consultas ─────────────────────────────────────────────────────────
    def pronto(self, agora):
        return agora - self.inicio >= constants.GOLPE_COOLDOWN_MS

    def em_antecipacao(self, agora):
        return 0 <= agora - self.inicio < constants.GOLPE_INICIO_MS

    def ativo(self, agora):
        t = agora - self.inicio
        return constants.GOLPE_INICIO_MS <= t < constants.GOLPE_INICIO_MS + constants.GOLPE_ATIVO_MS

    def em_andamento(self, agora):
        return 0 <= agora - self.inicio < constants.GOLPE_INICIO_MS + constants.GOLPE_ATIVO_MS

    def hitbox(self, player, direcao=None):
        """Retângulo de acerto: à frente do corpo, um pouco mais alto que ele."""
        d = self.direcao if direcao is None else direcao
        alt = player.rect.height + 2 * constants.GOLPE_ALTURA_EXTRA
        r = pygame.Rect(0, 0, constants.GOLPE_ALCANCE, alt)
        r.centery = player.rect.centery
        if d > 0:
            r.left = player.rect.centerx
        else:
            r.right = player.rect.centerx
        return r

    # ── frame ─────────────────────────────────────────────────────────────
    def atualizar(self, agora, player, inimigos, efeitos):
        """
        Inicia o golpe pedido (se o cooldown deixar) e aplica o acerto
        durante a janela ativa. Devolve a lista de (inimigo, resultado) deste
        frame — "atingido", "derrotado" ou "imune".
        """
        if player is None or not player.alive:
            return []
        if agora < self.pedido_ate and self.pronto(agora):
            self.pedido_ate = 0
            self.inicio = agora
            self.direcao = -1 if getattr(player, "flip", False) else 1
            self.atingidos = set()
            player.pose_golpe_ate = agora + constants.GOLPE_INICIO_MS + constants.GOLPE_ATIVO_MS
            player.pose_golpe_inicio = agora
            sons.tocar("golpe")
        if not self.ativo(agora):
            return []
        area = self.hitbox(player)
        resultados = []
        for inimigo in inimigos:
            if id(inimigo) in self.atingidos or inimigo.derrotado:
                continue
            if not area.colliderect(inimigo.rect):
                continue
            self.atingidos.add(id(inimigo))
            resultado = inimigo.receber_golpe(constants.DANO_GOLPE, player.rect.centerx)
            ponto = area.clip(inimigo.rect).center
            efeitos.faisca(ponto, imune=resultado == "imune")
            sons.tocar("golpe_imune" if resultado == "imune" else "golpe_acerto")
            resultados.append((inimigo, resultado))
        return resultados

    # ── desenho ───────────────────────────────────────────────────────────
    def desenhar(self, surface, camera_x, camera_y, player, agora=None):
        """Arco de vento com penas na frente da Areninha durante o golpe."""
        agora = pygame.time.get_ticks() if agora is None else agora
        if player is None or not self.em_andamento(agora):
            return
        t = (agora - self.inicio) / (constants.GOLPE_INICIO_MS + constants.GOLPE_ATIVO_MS)
        area = self.hitbox(player).move(-camera_x, -camera_y)
        cx = area.left if self.direcao > 0 else area.right
        cy = area.centery
        raio = int(constants.GOLPE_ALCANCE * (0.55 + 0.45 * min(1.0, t * 1.6)))
        # varredura de cima para baixo, como uma asa batendo
        a0 = -1.2 + 2.0 * max(0.0, t - 0.15)
        alpha = int(230 * (1 - t))
        camada = pygame.Surface((raio * 2 + 8, raio * 2 + 8), pygame.SRCALPHA)
        centro = (raio + 4, raio + 4)
        pontos = []
        for i in range(9):
            ang = a0 + i * 0.16
            pontos.append((centro[0] + math.cos(ang) * raio, centro[1] + math.sin(ang) * raio))
        if len(pontos) >= 2:
            pygame.draw.lines(camada, (255, 255, 255, alpha), False, pontos, 5)
            internos = [(centro[0] + (x - centro[0]) * 0.72, centro[1] + (y - centro[1]) * 0.72)
                        for x, y in pontos]
            pygame.draw.lines(camada, (200, 230, 255, alpha // 2), False, internos, 3)
            for x, y in pontos[1::3]:   # penas soltas
                pygame.draw.ellipse(camada, (255, 250, 220, alpha), (x - 4, y - 2, 8, 4))
        if self.direcao < 0:
            camada = pygame.transform.flip(camada, True, False)
            surface.blit(camada, (cx - camada.get_width() + centro[0], cy - centro[1]))
        else:
            surface.blit(camada, (cx - centro[0], cy - centro[1]))


class EfeitosCombate:
    """Faíscas de impacto e "puf" de derrota (uma lista só para o jogo todo)."""

    def __init__(self):
        self.itens = []   # (tipo, x, y, inicio_ms, tamanho, extra)

    def limpar(self):
        self.itens.clear()

    def __len__(self):
        return len(self.itens)

    def __bool__(self):
        return bool(self.itens)

    def faisca(self, ponto, imune=False):
        angulos = [random.uniform(0, 2 * math.pi) for _ in range(7)]
        self.itens.append(("faisca", ponto[0], ponto[1], pygame.time.get_ticks(),
                           18, (imune, angulos)))

    def puf(self, rect):
        self.itens.append(("puf", rect.centerx, rect.centery, pygame.time.get_ticks(),
                           max(rect.width, rect.height), None))

    def desenhar(self, surface, camera_x, camera_y, agora=None):
        agora = pygame.time.get_ticks() if agora is None else agora
        vivos = []
        for tipo, x, y, inicio, tam, extra in self.itens:
            dur = DURACAO_PUF_MS if tipo == "puf" else DURACAO_FAISCA_MS
            t = (agora - inicio) / dur
            if t >= 1:
                continue
            vivos.append((tipo, x, y, inicio, tam, extra))
            c = (int(x - camera_x), int(y - camera_y))
            if tipo == "puf":
                raio = int(tam * (0.4 + 0.6 * t))
                cor = (255, 255, 255) if t < 0.5 else (200, 200, 200)
                pygame.draw.circle(surface, cor, c, raio, max(1, int(4 * (1 - t))))
                for i in range(6):
                    ang = i * 1.047 + t
                    p = (c[0] + int(raio * 1.1 * math.cos(ang)), c[1] + int(raio * 1.1 * math.sin(ang)))
                    pygame.draw.circle(surface, cor, p, max(1, int(3 * (1 - t))))
            else:
                imune, angulos = extra
                cor = (170, 170, 190) if imune else (255, 230, 120)
                comp = tam * (0.4 + t)
                for ang in angulos:
                    p0 = (c[0] + math.cos(ang) * comp * 0.3, c[1] + math.sin(ang) * comp * 0.3)
                    p1 = (c[0] + math.cos(ang) * comp, c[1] + math.sin(ang) * comp)
                    pygame.draw.line(surface, cor, p0, p1, max(1, int(3 * (1 - t))))
        self.itens = vivos
