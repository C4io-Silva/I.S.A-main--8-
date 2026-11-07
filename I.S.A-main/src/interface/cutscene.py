"""
Cutscene de abertura do I.S.A.

Exibida logo depois que o jogador digita o nome na TelaLogin e antes da
partida começar. São 6 imagens em sequência (assets/images/cutscenes/
cutscene_1.png ... cutscene_6.png); o jogador avança com o botão PRÓXIMO.

Como funciona:
    - As imagens são carregadas e ESCALADAS UMA VEZ em `iniciar()` (não a cada
      frame) para caber na área acima da barra inferior, mantendo a proporção.
      A largura virtual do jogo varia conforme o monitor, então nada aqui
      assume 800x600: tudo é calculado a partir de (largura, altura).
    - A troca de imagem faz um crossfade curto.
    - Ao avançar além da última imagem (ou pular com ESC) chama `callback_fim`,
      que no main.py inicia a partida.

Entradas aceitas: clique no botão PRÓXIMO, ENTER / ESPAÇO / seta direita,
botão de confirmar do controle. ESC (ou botão voltar do controle) pula tudo.
"""

import math

import pygame

from src.nucleo.utils import ASSETS_PATH, carregar_fonte

# Mesma paleta do resto da interface (ver src/buttons.py).
PRETO = (0, 0, 0)
AMARELO = (241, 187, 52)
AMARELO_ESCURO = (196, 140, 25)
FUNDO = (14, 14, 30)
BARRA = (20, 20, 40)
CINZA = (150, 150, 170)

PASTA = "cutscenes"
ARQUIVOS = [f"cutscene_{i}.png" for i in range(1, 8)]
ROTULO_BOTAO = "PRÓXIMO"

ALTURA_BARRA = 64        # faixa inferior com o botão e os indicadores
MARGEM = 10              # respiro em volta da moldura da imagem
FADE_MS = 380            # duração do crossfade entre imagens
TRAVA_ENTRADA_MS = 350   # ignora entrada logo ao abrir (ENTER do login ainda "quente")


class Cutscene:
    def __init__(self, largura, altura, callback_fim=None):
        self.W = largura
        self.H = altura
        self.callback_fim = callback_fim

        self.imagens = []        # Surfaces já escaladas
        self.indice = 0
        self.anterior = None     # índice da imagem que está saindo (crossfade)
        self.fade = 255.0        # 0..255: opacidade da imagem atual
        self.tempo = 0           # ms desde que a cutscene abriu
        self.ativa = False

        self.moldura = pygame.Rect(0, 0, 0, 0)
        self.botao = pygame.Rect(0, 0, 0, 0)

        self.fonte_botao = carregar_fonte("upheavtt.ttf", 22)
        self.fonte_info = carregar_fonte("upheavtt.ttf", 14)

        self._calcular_layout()

    # ── Layout ────────────────────────────────────────────────────────────
    def _calcular_layout(self):
        area_h = self.H - ALTURA_BARRA
        self.moldura = pygame.Rect(
            MARGEM, MARGEM, self.W - 2 * MARGEM, area_h - 2 * MARGEM
        )
        bw, bh = 190, 44
        self.botao = pygame.Rect(0, 0, bw, bh)
        self.botao.midright = (
            self.W - MARGEM - 8,
            self.H - ALTURA_BARRA // 2,
        )

    def _carregar_imagens(self):
        """Carrega cada PNG uma vez, já no tamanho final (contain, sem distorcer)."""
        self.imagens = []
        caixa_w, caixa_h = self.moldura.size
        for nome in ARQUIVOS:
            caminho = ASSETS_PATH / "images" / PASTA / nome
            try:
                img = pygame.image.load(str(caminho)).convert()
                fator = min(caixa_w / img.get_width(), caixa_h / img.get_height())
                tam = (
                    max(1, int(img.get_width() * fator)),
                    max(1, int(img.get_height() * fator)),
                )
                self.imagens.append(pygame.transform.smoothscale(img, tam))
            except (FileNotFoundError, pygame.error) as e:
                # Imagem faltando não pode travar o jogo: a cena é só pulada.
                print(f"Aviso: cutscene '{nome}' não carregou: {e}")

    # ── Ciclo de vida ─────────────────────────────────────────────────────
    def iniciar(self):
        """Chamada ao entrar no estado CUTSCENE (sempre recarrega do zero)."""
        self._calcular_layout()
        self._carregar_imagens()
        self.indice = 0
        self.anterior = None
        self.fade = 255.0
        self.tempo = 0
        self.ativa = True
        if not self.imagens:
            self._finalizar()

    def _finalizar(self):
        self.ativa = False
        self.imagens = []  # libera memória; recarrega se a cutscene rodar de novo
        if self.callback_fim:
            self.callback_fim()

    def avancar(self):
        if not self.ativa or self.tempo < TRAVA_ENTRADA_MS:
            return
        if self.indice + 1 >= len(self.imagens):
            self._finalizar()
            return
        self.anterior = self.indice
        self.indice += 1
        self.fade = 0.0

    def pular(self):
        if not self.ativa or self.tempo < TRAVA_ENTRADA_MS:
            return
        self._finalizar()

    # ── Eventos ───────────────────────────────────────────────────────────
    def handle_event(self, evento):
        if not self.ativa:
            return
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if self.botao.collidepoint(evento.pos):
                self.avancar()
        elif evento.type == pygame.KEYDOWN:
            if evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                              pygame.K_SPACE, pygame.K_RIGHT):
                self.avancar()
            elif evento.key == pygame.K_ESCAPE:
                self.pular()

    # ── Atualização ───────────────────────────────────────────────────────
    def atualizar(self, dt_ms):
        if not self.ativa:
            return
        self.tempo += dt_ms
        if self.fade < 255.0:
            self.fade = min(255.0, self.fade + 255.0 * dt_ms / FADE_MS)
            if self.fade >= 255.0:
                self.anterior = None

    # ── Desenho ───────────────────────────────────────────────────────────
    def _blit_centralizada(self, tela, img, alpha=255):
        rect = img.get_rect(center=self.moldura.center)
        img.set_alpha(alpha)
        tela.blit(img, rect)
        return rect

    def _desenhar_botao(self, tela, mouse_pos, foco):
        hover = foco or self.botao.collidepoint(mouse_pos)
        pressionado = hover and pygame.mouse.get_pressed()[0] and not foco
        r = self.botao.move(0, 3 if pressionado else 0)

        # Sombra "pixel" sob o botão
        pygame.draw.rect(tela, PRETO, self.botao.move(0, 5), border_radius=12)
        pygame.draw.rect(tela, AMARELO_ESCURO if hover else AMARELO, r, border_radius=12)
        pygame.draw.rect(tela, PRETO, r, 3, border_radius=12)

        # Pulso suave no contorno para chamar atenção para o botão
        pulso = 0.5 + 0.5 * math.sin(self.tempo / 260.0)
        brilho = pygame.Rect(r).inflate(8, 8)
        cor = (255, int(220 + 35 * pulso), int(120 + 100 * pulso))
        pygame.draw.rect(tela, cor, brilho, 2, border_radius=15)

        # Texto + seta (a fonte pixel não tem o glifo ▶, então a seta é desenhada)
        txt = self.fonte_botao.render(ROTULO_BOTAO, True, PRETO)
        seta_w, folga = 14, 12
        total = txt.get_width() + folga + seta_w
        x0 = r.centerx - total // 2
        tela.blit(txt, (x0, r.centery - txt.get_height() // 2))
        ax = x0 + txt.get_width() + folga + int(2 * pulso)
        ay = r.centery
        pygame.draw.polygon(tela, PRETO, [(ax, ay - 9), (ax, ay + 9), (ax + seta_w, ay)])

    def _desenhar_indicadores(self, tela):
        total = len(self.imagens)
        x = self.moldura.left + 6
        cy = self.H - ALTURA_BARRA // 2
        for i in range(total):
            lado = 12 if i == self.indice else 9
            rect = pygame.Rect(0, 0, lado, lado)
            rect.center = (x + 6, cy)
            if i <= self.indice:
                pygame.draw.rect(tela, AMARELO, rect)
            else:
                pygame.draw.rect(tela, (60, 60, 90), rect)
            pygame.draw.rect(tela, PRETO, rect, 2)
            x += 22
        cont = self.fonte_info.render(f"{self.indice + 1}/{total}", True, AMARELO)
        tela.blit(cont, (x + 6, cy - cont.get_height() // 2))
        dica = self.fonte_info.render("ESC = pular", True, CINZA)
        tela.blit(dica, (x + 6 + cont.get_width() + 18, cy - dica.get_height() // 2))

    def desenhar(self, tela, mouse_pos=None, foco_no_controle=False):
        if not self.ativa or not self.imagens:
            return
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()

        tela.fill(FUNDO)

        # Imagem (com crossfade: a anterior fica por baixo, a nova sobe por cima)
        if self.anterior is not None:
            self._blit_centralizada(tela, self.imagens[self.anterior], 255)
        rect_img = self._blit_centralizada(
            tela, self.imagens[self.indice], int(self.fade)
        )

        # Moldura dourada em volta da imagem
        pygame.draw.rect(tela, PRETO, rect_img.inflate(10, 10), 5)
        pygame.draw.rect(tela, AMARELO, rect_img.inflate(6, 6), 3)

        # Barra inferior
        barra = pygame.Rect(0, self.H - ALTURA_BARRA, self.W, ALTURA_BARRA)
        pygame.draw.rect(tela, BARRA, barra)
        pygame.draw.line(tela, AMARELO, barra.topleft, barra.topright, 2)

        self._desenhar_indicadores(tela)
        self._desenhar_botao(tela, mouse_pos, foco_no_controle)
