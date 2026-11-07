import math

import pygame

from src.nucleo.utils import carregar_fonte, texto_contorno

# ── Paleta única (a mesma da TelaLogin) ──────────────────────────────────────
PRETO          = (0, 0, 0)
BRANCO         = (255, 255, 255)
DOURADO        = (247, 181, 20)
DOURADO_HOVER  = (255, 201, 60)
DOURADO_BRILHO = (255, 226, 130)
AZUL_ESCURO    = (22, 28, 90)

# Nomes antigos, caso outro arquivo ainda importe daqui
AMARELO        = DOURADO
AMARELO_ESCURO = (196, 140, 25)
AZUL           = (40, 60, 200)
CLARO          = (255, 245, 220)

PROFUNDIDADE = 5   # altura da sombra azul-escura embaixo do botão
LEVANTAR     = 2   # quanto o botão sobe quando o mouse passa por cima
SUPER_BASE   = 4   # a base do botão é desenhada 4x maior e reduzida (suaviza as bordas)


_cache_base = {}


def _desenhar_base(tela, rect, hover, raio):
    """
    Sombra azul-escura, corpo dourado, faixa de brilho e borda.
    Devolve o rect visual (que sobe um pouco no hover) para o conteúdo
    do botão ser desenhado em cima dele.

    A base é desenhada em alta resolução e reduzida com suavização
    (bordas sem serrilhado); fica em cache por tamanho e hover.
    """
    visual = rect.move(0, -LEVANTAR) if hover else rect

    chave = (rect.width, rect.height, raio, hover)
    img = _cache_base.get(chave)
    if img is None:
        k = SUPER_BASE
        w, h = rect.width, rect.height
        topo = 0 if hover else LEVANTAR     # y do corpo dentro da imagem
        alta = pygame.Surface((w * k, (h + PROFUNDIDADE + LEVANTAR) * k), pygame.SRCALPHA)

        corpo = pygame.Rect(0, topo * k, w * k, h * k)
        sombra = pygame.Rect(0, (LEVANTAR + PROFUNDIDADE) * k, w * k, h * k)
        pygame.draw.rect(alta, AZUL_ESCURO, sombra, border_radius=raio * k)
        pygame.draw.rect(alta, DOURADO_HOVER if hover else DOURADO, corpo,
                         border_radius=raio * k)

        brilho = pygame.Rect(corpo.x + 8 * k, corpo.y + 5 * k,
                             max(1, w - 16) * k, max(3, h // 12) * k)
        pygame.draw.rect(alta, (255, 236, 160) if hover else DOURADO_BRILHO,
                         brilho, border_radius=3 * k)

        pygame.draw.rect(alta, AZUL_ESCURO, corpo, 3 * k, border_radius=raio * k)
        img = pygame.transform.smoothscale(alta, (w, h + PROFUNDIDADE + LEVANTAR))
        if len(_cache_base) > 64:
            _cache_base.clear()
        _cache_base[chave] = img

    tela.blit(img, (rect.x, rect.y - LEVANTAR))
    return visual


class Botao:
    # Proporção entre a altura do botão e o corpo da fonte.
    # 60px de altura (o padrão em 800x600) resulta em fonte 20.
    PROPORCAO_FONTE = 1 / 3

    def __init__(self, texto, x, y, largura, altura, acao=None, tamanho_fonte=None):
        self.texto      = texto
        self.rect       = pygame.Rect(x, y, largura, altura)
        self.cor_normal = DOURADO
        self.cor_hover  = DOURADO_HOVER
        self.acao       = acao
        self.raio       = max(8, altura // 4)

        if tamanho_fonte is None:
            tamanho_fonte = max(12, int(altura * self.PROPORCAO_FONTE))
        self.tamanho_fonte = tamanho_fonte
        self.fonte = self._ajustar_fonte(texto, largura, tamanho_fonte)

        # Texto branco com contorno azul-escuro, gerado UMA vez (não a cada frame)
        self._img_texto = texto_contorno(
            self.fonte, texto, BRANCO, AZUL_ESCURO,
            espessura=max(2, altura // 28), sombra=(0, 2),
        )

    @staticmethod
    def _ajustar_fonte(texto, largura, tamanho):
        """Reduz a fonte até o rótulo caber na largura do botão."""
        largura_util = max(1, largura - 28)  # margem interna (contorno incluso)
        while tamanho > 12:
            fonte = carregar_fonte("upheavtt.ttf", tamanho)
            if fonte.size(texto)[0] <= largura_util:
                return fonte
            tamanho -= 1
        return carregar_fonte("upheavtt.ttf", max(8, tamanho))

    def desenhar(self, tela, mouse_pos=None):
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()

        hover = self.rect.collidepoint(mouse_pos)
        visual = _desenhar_base(tela, self.rect, hover, self.raio)
        tela.blit(self._img_texto, self._img_texto.get_rect(center=visual.center))

    def verificar_click(self, evento):
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if self.rect.collidepoint(evento.pos):
                if self.acao:
                    self.acao()


# ── Botões de ícone (quadrados arredondados, mesmo estilo do Botao) ─────────
SUPER = 4   # os ícones são desenhados 4x maior e reduzidos com suavização


class _BotaoIcone:
    """
    Base de BotaoConfig e BotaoSair. Mantém cx, cy e raio (usados pelo
    main.py e pelo controle) e ganha um rect, para o clique e o foco do
    controle funcionarem igual aos botões de texto.

    O ícone é desenhado em alta resolução e reduzido com smoothscale
    (antialiasing). O resultado fica em cache: só é redesenhado quando muda
    (hover, ou o ângulo da engrenagem).
    """

    def __init__(self, cx, cy, raio=35, acao=None):
        self.cx   = cx
        self.cy   = cy
        self.raio = raio
        self.acao = acao
        self.rect = pygame.Rect(cx - raio, cy - raio, raio * 2, raio * 2)
        self._cache = {}

    def _dentro(self, pos):
        return self.rect.collidepoint(pos)

    def _chave_cache(self, hover):
        return hover

    def _desenhar_alta_resolucao(self, surf, k, hover):
        """Desenha o ícone em `surf` (lado*k), centralizado, tudo multiplicado por k."""
        raise NotImplementedError

    def _icone_suave(self, hover):
        chave = self._chave_cache(hover)
        img = self._cache.get(chave)
        if img is None:
            lado = self.rect.width
            alta = pygame.Surface((lado * SUPER, lado * SUPER), pygame.SRCALPHA)
            self._desenhar_alta_resolucao(alta, SUPER, hover)
            img = pygame.transform.smoothscale(alta, (lado, lado))
            if len(self._cache) > 64:
                self._cache.clear()
            self._cache[chave] = img
        return img

    def desenhar(self, tela, mouse_pos=None):
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()

        hover = self._dentro(mouse_pos)
        visual = _desenhar_base(tela, self.rect, hover, max(8, self.rect.width // 5))
        img = self._icone_suave(hover)
        tela.blit(img, img.get_rect(center=visual.center))

    def verificar_click(self, evento):
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if self._dentro(evento.pos):
                if self.acao:
                    self.acao()


def _engrenagem(surf, cx, cy, r_ext, r_int, dentes, ang, cor, cor_borda, cor_furo, borda):
    """Engrenagem de dentes trapezoidais, com contorno e furo no centro."""
    passo = 2 * math.pi / dentes

    def contorno(re, ri):
        pts = []
        for i in range(dentes):
            a = ang + i * passo
            for raio, desvio in ((ri, -0.40), (re, -0.22), (re, 0.22), (ri, 0.40)):
                t = a + desvio * passo
                pts.append((cx + math.cos(t) * raio, cy + math.sin(t) * raio))
        return pts

    pygame.draw.polygon(surf, cor_borda, contorno(r_ext + borda, r_int + borda))
    pygame.draw.polygon(surf, cor, contorno(r_ext, r_int))

    furo = max(2, int(r_int * 0.42))
    pygame.draw.circle(surf, cor_borda, (cx, cy), furo + borda)
    pygame.draw.circle(surf, cor_furo, (cx, cy), furo)


class BotaoConfig(_BotaoIcone):
    def __init__(self, cx, cy, raio=35, acao=None):
        super().__init__(cx, cy, raio, acao)
        self._angulo = 0.0

    def _chave_cache(self, hover):
        # 8 dentes: a engrenagem se repete a cada 45 graus
        return (hover, int(math.degrees(self._angulo)) % 45)

    def _desenhar_alta_resolucao(self, surf, k, hover):
        c = surf.get_width() // 2
        _engrenagem(
            surf, c, c,
            r_ext=self.raio * 0.62 * k, r_int=self.raio * 0.46 * k,
            dentes=8, ang=self._angulo,
            cor=BRANCO, cor_borda=AZUL_ESCURO,
            cor_furo=DOURADO_HOVER if hover else DOURADO,
            borda=2.2 * k,
        )

    def desenhar(self, tela, mouse_pos=None):
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()
        # Gira devagar enquanto o mouse está em cima
        if self._dentro(mouse_pos):
            self._angulo += 0.03
        else:
            self._angulo = 0.0
        super().desenhar(tela, mouse_pos)


class BotaoSair(_BotaoIcone):
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
        borda = int(1.6 * k) * 2          # sobra do contorno, nos dois lados
        # A seta anda um pouco para a direita no hover
        dx = int(self.raio * 0.08 * k) if hover else 0

        def s(v):
            return int(v * escala)

        # Colchete à esquerda + seta que sai dele para a direita
        porta = [
            ((cx + s(6), cy + s(-30)), (cx + s(-22), cy + s(-30))),
            ((cx + s(-22), cy + s(-30)), (cx + s(-22), cy + s(30))),
            ((cx + s(-22), cy + s(30)), (cx + s(6), cy + s(30))),
        ]
        haste = ((cx + s(-8) + dx, cy), (cx + s(24) + dx, cy))
        ponta = [
            (cx + s(36) + dx, cy),
            (cx + s(20) + dx, cy + s(-16)),
            (cx + s(20) + dx, cy + s(16)),
        ]

        # 1ª passada: contorno azul-escuro (mais grosso); 2ª: ícone branco
        for cor, extra in ((AZUL_ESCURO, borda), (BRANCO, 0)):
            for a, b in porta:
                self._linha(surf, cor, a, b, espessura + extra)
            self._linha(surf, cor, haste[0], haste[1], espessura + extra)
            pygame.draw.polygon(surf, cor, ponta)
            if extra:
                pygame.draw.polygon(surf, cor, ponta, extra)