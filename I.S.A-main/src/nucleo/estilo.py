"""
Peças visuais compartilhadas pelas telas, no estilo do menu inicial:
fundo com véu azul no topo, painéis azul-escuros com borda dourada, texto
branco/dourado com contorno azul e botões dourados (classe Botao, em
src/buttons.py).

Tudo aqui é desenhado em alta resolução e reduzido com smoothscale (bordas
sem serrilhado, igual aos botões) e fica em cache: nada é redesenhado a
cada frame.
"""
import pygame

from src.interface.buttons import _BotaoIcone
from src.nucleo.utils import texto_contorno

# ── Paleta (a mesma do menu inicial e de src/buttons.py) ─────────────────────
BRANCO = (255, 255, 255)
DOURADO = (247, 181, 20)
DOURADO_HOVER = (255, 201, 60)
DOURADO_BRILHO = (255, 226, 130)
AZUL_ESCURO = (22, 28, 90)
AZUL_FUNDO = (10, 14, 55)
AZUL_LINHA = (60, 75, 170)
CLARO = (255, 245, 220)
AMARELO_TITULO = (255, 220, 40)
CONTORNO_TITULO = (20, 30, 110)
COR_ERRO = (255, 120, 100)
COR_ACERTO = (120, 230, 130)


# ── Botão de voltar (seta), no estilo de BotaoSair e BotaoConfig ─────────────
class BotaoVoltar(_BotaoIcone):
    """Seta para a esquerda: corpo dourado, ícone branco com contorno azul."""

    @staticmethod
    def _linha(surf, cor, a, b, largura):
        """Linha com pontas arredondadas (evita falhas nos cantos)."""
        pygame.draw.line(surf, cor, a, b, largura)
        pygame.draw.circle(surf, cor, a, largura // 2)
        pygame.draw.circle(surf, cor, b, largura // 2)

    def _desenhar_alta_resolucao(self, surf, k, hover):
        cx = cy = surf.get_width() // 2
        escala = self.raio / 52 * k
        espessura = int(max(4, self.raio * 0.18) * k)
        borda = int(1.6 * k) * 2
        # A seta anda um pouco para a esquerda no hover
        dx = -int(self.raio * 0.08 * k) if hover else 0

        def s(v):
            return int(v * escala)

        haste = ((cx + s(26) + dx, cy), (cx + s(-12) + dx, cy))
        ponta = [
            (cx + s(-30) + dx, cy),
            (cx + s(-8) + dx, cy + s(-22)),
            (cx + s(-8) + dx, cy + s(22)),
        ]

        for cor, extra in ((AZUL_ESCURO, borda), (BRANCO, 0)):
            self._linha(surf, cor, haste[0], haste[1], espessura + extra)
            pygame.draw.polygon(surf, cor, ponta)
            if extra:
                pygame.draw.polygon(surf, cor, ponta, extra)


# ── Painel, véu, separador ───────────────────────────────────────────────────
def criar_painel(w, h, raio=24, prof=8, alpha=228):
    """
    Painel azul-escuro semitransparente com borda dourada, filete interno e
    sombra embaixo. A imagem devolvida tem altura h + prof (a sombra); o
    painel em si ocupa os h primeiros pixels.
    """
    k = 3
    alta = pygame.Surface((w * k, (h + prof) * k), pygame.SRCALPHA)

    pygame.draw.rect(alta, (6, 8, 36, 150),
                     (0, prof * k, w * k, h * k), border_radius=raio * k)
    corpo = pygame.Rect(0, 0, w * k, h * k)
    pygame.draw.rect(alta, (*AZUL_ESCURO, alpha), corpo, border_radius=raio * k)
    pygame.draw.rect(alta, DOURADO, corpo, 4 * k, border_radius=raio * k)
    interno = corpo.inflate(-16 * k, -16 * k)
    pygame.draw.rect(alta, (*AZUL_LINHA, 255), interno, 2 * k,
                     border_radius=max(1, raio - 8) * k)
    return pygame.transform.smoothscale(alta, (w, h + prof))


def criar_veu_topo(largura, altura=230, alpha_max=150):
    """Degradê azul-escuro no topo da tela (o mesmo do menu inicial)."""
    surf = pygame.Surface((largura, altura), pygame.SRCALPHA)
    for y in range(altura):
        a = int(alpha_max * (1 - y / altura) ** 2)
        pygame.draw.line(surf, (10, 20, 80, a), (0, y), (largura, y))
    return surf


def desenhar_separador(tela, x1, x2, y):
    """Linha fina azul com um losango dourado no meio."""
    pygame.draw.line(tela, AZUL_LINHA, (x1, y), (x2, y), 3)
    cx = (x1 + x2) // 2
    pygame.draw.polygon(tela, DOURADO,
                        [(cx - 6, y), (cx, y - 6), (cx + 6, y), (cx, y + 6)])


class CacheTexto:
    """Texto com contorno (como o dos botões), renderizado uma vez só."""

    def __init__(self, limite=256):
        self._d = {}
        self.limite = limite

    def limpar(self):
        self._d.clear()

    def __call__(self, fonte, conteudo, cor=BRANCO, cor_contorno=CONTORNO_TITULO,
                 espessura=2):
        chave = (id(fonte), conteudo, cor, cor_contorno, espessura)
        surf = self._d.get(chave)
        if surf is None:
            if len(self._d) >= self.limite:
                self._d.clear()
            surf = texto_contorno(fonte, conteudo, cor, cor_contorno,
                                  espessura=espessura, sombra=(0, 2))
            self._d[chave] = surf
        return surf


# ── Slider ───────────────────────────────────────────────────────────────────
class SliderMenu:
    """
    Slider no estilo do menu: trilho azul com preenchimento dourado e botão
    redondo dourado. Mesma interface do ControleDeslizante antigo
    (`valor`, `atualizar(evento)`, `desenhar(tela)`), mais `reposicionar`.
    """

    def __init__(self, x, y_centro, larg, valor=0.5, altura=14, botao=26):
        self.valor = valor
        self.arrastando = False
        self.reposicionar(x, y_centro, larg, altura, botao)

    def reposicionar(self, x, y_centro, larg, altura=14, botao=26):
        self.retangulo = pygame.Rect(x, y_centro - altura // 2, larg, altura)
        self.botao = botao
        self.controle_ret = pygame.Rect(0, 0, botao, botao)
        self._trilhos = {}
        self._botoes = {}
        self._sincronizar()

    def _sincronizar(self):
        self.controle_ret.center = (
            self.retangulo.x + int(self.valor * self.retangulo.w),
            self.retangulo.centery,
        )

    def _definir_por_x(self, x):
        x = max(self.retangulo.x, min(x, self.retangulo.right))
        self.valor = (x - self.retangulo.x) / self.retangulo.w
        self._sincronizar()

    def atualizar(self, evento):
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if self.controle_ret.collidepoint(evento.pos):
                self.arrastando = True
            # Também dá para clicar direto no trilho (área de clique maior)
            elif self.retangulo.inflate(0, 16).collidepoint(evento.pos):
                self._definir_por_x(evento.pos[0])
                self.arrastando = True
        elif evento.type == pygame.MOUSEBUTTONUP:
            self.arrastando = False
        elif evento.type == pygame.MOUSEMOTION and self.arrastando:
            self._definir_por_x(evento.pos[0])

    def _img_trilho(self, preenchido):
        img = self._trilhos.get(preenchido)
        if img is None:
            k = 4
            w, h = self.retangulo.size
            alta = pygame.Surface((w * k, h * k), pygame.SRCALPHA)
            pygame.draw.rect(alta, AZUL_ESCURO, (0, 0, w * k, h * k),
                             border_radius=h * k // 2)
            pygame.draw.rect(alta, (45, 58, 150), (2 * k, 2 * k, (w - 4) * k, (h - 4) * k),
                             border_radius=(h - 4) * k // 2)
            f = max(0, min(w - 4, preenchido - 2))
            if f > 0:
                pygame.draw.rect(alta, DOURADO, (2 * k, 2 * k, f * k, (h - 4) * k),
                                 border_radius=(h - 4) * k // 2)
            img = pygame.transform.smoothscale(alta, (w, h))
            if len(self._trilhos) > 300:
                self._trilhos.clear()
            self._trilhos[preenchido] = img
        return img

    def _img_botao(self, destaque):
        img = self._botoes.get(destaque)
        if img is None:
            k = 4
            d = self.botao
            alta = pygame.Surface((d * k, d * k), pygame.SRCALPHA)
            c = d * k // 2
            pygame.draw.circle(alta, AZUL_ESCURO, (c, c), c)
            pygame.draw.circle(alta, DOURADO_HOVER if destaque else DOURADO,
                               (c, c), c - 3 * k)
            pygame.draw.circle(alta, (255, 236, 160), (c - c // 4, c - c // 4),
                               max(2, c // 4))
            img = pygame.transform.smoothscale(alta, (d, d))
            self._botoes[destaque] = img
        return img

    def desenhar(self, tela, mouse_pos=None):
        self._sincronizar()
        r = self.retangulo
        tela.blit(self._img_trilho(self.controle_ret.centerx - r.x), r.topleft)
        sobre = mouse_pos is not None and self.controle_ret.collidepoint(mouse_pos)
        img = self._img_botao(self.arrastando or sobre)
        tela.blit(img, img.get_rect(center=self.controle_ret.center))
