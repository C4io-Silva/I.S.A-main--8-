"""A Areninha que corre até o canto do menu inicial e conversa por balão de fala."""

import pygame

from src.nucleo import constants
from src.nucleo.utils import carregar_fonte, carregar_imagem

FRAMES_CORRIDA = ("S4.png", "S5.png")
SPRITE_PARADO = "S7.png"
SPRITE_FALLBACK = "Areninha4 2.png"
ALTURA_SPRITE = 220

FALAS = (
    "Bem-vindo ao I.S.A!",
    "Ajude a personagem a coletar os minerios",
    "e responder as perguntas.",
    "Clique em qualquer lugar para continuar.",
)

COR_TEXTO = (22, 28, 90)
COR_FUNDO = (255, 252, 235)
COR_RABINHO = (255, 252, 225)
COR_INSTRUCAO = (120, 100, 40)
COR_CONTADOR = (214, 150, 0)


def recortar_transparencia(sprite):
    """Remove a margem transparente ao redor do personagem, devolvendo só o conteúdo visível."""
    mask = pygame.mask.from_surface(sprite)
    rects = mask.get_bounding_rects()
    if not rects:
        return sprite
    r = rects[0]
    for rr in rects[1:]:
        r = r.union(rr)
    return sprite.subsurface(r).copy()


def escalar_mantendo_proporcao(sprite, altura_alvo):
    """Recorta a margem transparente e escala todos os frames para a mesma altura."""
    sprite = recortar_transparencia(sprite)
    razao = sprite.get_width() / sprite.get_height()
    return pygame.transform.scale(sprite, (int(altura_alvo * razao), altura_alvo))


class IntroPersonagem:
    VELOCIDADE = 3
    ATRASO_FRAME = 12     # frames de jogo por frame de animação

    def __init__(self):
        self.frames = []
        self.indice_frame = 0
        self.contador = 0
        self.indice_fala = -1       # -1 = nenhuma fala ainda
        self.finalizada = False     # chegou ao destino
        self.imagem = None
        self.rect = None
        self.x = -140
        self._textos = {}           # cache dos textos renderizados do balão
        self._carregar()

    def _carregar(self):
        for nome in FRAMES_CORRIDA:
            try:
                sprite = carregar_imagem("personagens", nome)
                self.frames.append(escalar_mantendo_proporcao(sprite, ALTURA_SPRITE))
            except Exception as e:  # noqa: BLE001
                print(f"Erro ao carregar frame de intro '{nome}': {e}")
        if not self.frames:
            try:
                fallback = carregar_imagem("personagens", SPRITE_FALLBACK)
                self.frames = [pygame.transform.scale(fallback, (220, 220))]
            except Exception as e:  # noqa: BLE001
                print(f"Erro ao carregar frame de fallback de intro: {e}")

        self.imagem = self.frames[0] if self.frames else None
        y = constants.SCREEN_HEIGHT - 250
        self.rect = (self.imagem.get_rect(topleft=(self.x, y))
                     if self.imagem else None)

    # ── lógica ───────────────────────────────────────────────────────────────
    def atualizar(self):
        """Avança a animação de corrida. Chamar só enquanto o menu está aberto."""
        destino_x = 50
        if self.x < destino_x:
            self.x += self.VELOCIDADE
            if self.rect:
                self.rect.x = self.x
            self.contador += 1
            if self.contador >= self.ATRASO_FRAME:
                self.contador = 0
                if self.frames:
                    self.indice_frame = (self.indice_frame + 1) % len(self.frames)
                    self.imagem = self.frames[self.indice_frame]
        elif not self.finalizada:
            self.finalizada = True
            self.indice_fala = 0
            try:
                parado = carregar_imagem("personagens", SPRITE_PARADO)
                self.imagem = escalar_mantendo_proporcao(parado, ALTURA_SPRITE)
            except Exception as e:  # noqa: BLE001
                print(f"Erro ao carregar sprite parado da intro '{SPRITE_PARADO}': {e}")

    def clicar(self, pos):
        """Clicar na personagem passa para a próxima fala."""
        if not self.finalizada or not self.rect:
            return
        if self.rect.collidepoint(pos):
            self.indice_fala = (self.indice_fala + 1) % len(FALAS)

    # ── desenho ──────────────────────────────────────────────────────────────
    def _texto(self, chave, fonte, conteudo, cor):
        """Renderiza uma vez só: o balão redesenha o mesmo texto a cada frame."""
        surf = self._textos.get(chave)
        if surf is None:
            surf = fonte.render(conteudo, True, cor)
            self._textos[chave] = surf
        return surf

    def desenhar(self, tela, botoes):
        """`botoes` são os do menu: o balão desvia deles para não os cobrir."""
        if not (self.imagem and self.rect):
            return
        tela.blit(self.imagem, self.rect)
        if not (self.finalizada and 0 <= self.indice_fala < len(FALAS)):
            return

        W = constants.SCREEN_WIDTH
        fonte = carregar_fonte("upheavtt.ttf", 18)
        fonte_menor = carregar_fonte("upheavtt.ttf", 13)
        surf_txt = self._texto(("fala", self.indice_fala), fonte,
                               FALAS[self.indice_fala], COR_TEXTO)
        pad = 12
        bal_w = surf_txt.get_width() + pad * 2
        bal_h = surf_txt.get_height() + pad * 2 + 22
        bal_x = self.rect.right + 14
        bal_y = self.rect.top

        # Não sai da tela pela direita
        if bal_x + bal_w > W - 10:
            bal_x = self.rect.left - bal_w - 14

        # Nunca sobrepõe os botões do menu
        balao = pygame.Rect(bal_x, bal_y, bal_w, bal_h)
        for botao in botoes:
            rect_botao = getattr(botao, "rect", None)
            if rect_botao and balao.colliderect(rect_botao):
                bal_y = rect_botao.top - bal_h - 10
                balao.topleft = (bal_x, bal_y)

        # Sombra, fundo e borda do balão
        pygame.draw.rect(tela, COR_TEXTO, (bal_x, bal_y + 4, bal_w, bal_h), border_radius=12)
        pygame.draw.rect(tela, COR_FUNDO, (bal_x, bal_y, bal_w, bal_h), border_radius=12)
        pygame.draw.rect(tela, COR_TEXTO, (bal_x, bal_y, bal_w, bal_h), 3, border_radius=12)

        # Rabinho do balão (triângulo apontando para o personagem)
        cx = bal_x
        cy = bal_y + bal_h // 2
        pygame.draw.polygon(tela, COR_RABINHO, [(cx, cy - 8), (cx, cy + 8), (cx - 12, cy)])
        pygame.draw.lines(tela, COR_TEXTO, False,
                          [(cx, cy - 8), (cx - 12, cy), (cx, cy + 8)], 3)

        tela.blit(surf_txt, (bal_x + pad, bal_y + pad))
        instrucao = self._texto("instrucao", fonte_menor, "[ clique em mim! ]", COR_INSTRUCAO)
        tela.blit(instrucao, (bal_x + pad, bal_y + bal_h - instrucao.get_height() - 4))

        # Contador de falas (ex: 1/4)
        contador = self._texto(("contador", self.indice_fala),
                               carregar_fonte("upheavtt.ttf", 18),
                               f"{self.indice_fala + 1}/{len(FALAS)}", COR_CONTADOR)
        tela.blit(contador, (bal_x + bal_w - contador.get_width() - 6,
                             bal_y + bal_h - contador.get_height() - 4))
