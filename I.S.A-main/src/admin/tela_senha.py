"""
Tela de senha do ADMIN. Mesmo visual da tela de LOGIN do jogo (painel
azul-escuro com borda dourada, fonte pixel, botão dourado), sobre o fundo
desfocado. Senha certa -> callback_sucesso; errada -> avisa e limpa o campo.
"""

import pygame

from src.admin import SENHA_ADMIN
from src.admin.campos import Campo
from src.interface.buttons import Botao
from src.nucleo.estilo import (
    AMARELO_TITULO,
    BRANCO,
    CONTORNO_TITULO,
    COR_ERRO,
    BotaoVoltar,
    CacheTexto,
    criar_painel,
    criar_veu_topo,
)
from src.nucleo.utils import carregar_fonte, carregar_fonte_typewriter


def desfocar(fundo, fator=10):
    """Fundo desfocado: reduz e amplia com suavização (barato e basta aqui)."""
    w, h = fundo.get_size()
    pequeno = pygame.transform.smoothscale(
        fundo, (max(1, w // fator), max(1, h // fator)))
    grande = pygame.transform.smoothscale(pequeno, (w, h))
    veu = pygame.Surface((w, h), pygame.SRCALPHA)
    veu.fill((10, 20, 80, 70))
    grande.blit(veu, (0, 0))
    return grande


def fonte_pixel(tamanho):
    """Fonte pixel do jogo, com plano B se o arquivo não for achado."""
    try:
        return carregar_fonte("upheavtt.ttf", max(8, tamanho))
    except (FileNotFoundError, pygame.error):
        return pygame.font.SysFont("consolas,couriernew,monospace",
                                   max(8, tamanho), bold=True)


class TelaSenhaAdmin:
    MAX_CARACTERES = 20

    def __init__(self, screen, fundo, callback_voltar=None, callback_sucesso=None):
        self.screen = screen
        self.W, self.H = screen.get_width(), screen.get_height()
        self.callback_voltar = callback_voltar
        self.callback_sucesso = callback_sucesso
        self.mensagem = ""
        self._txt = CacheTexto()

        k = self.H / 600
        sx = sy = lambda v: int(v * k)
        self.sy = sy
        self.fundo = desfocar(fundo)
        self._veu = criar_veu_topo(self.W)

        self.f_cabecalho = fonte_pixel(sy(30))
        self.f_label = fonte_pixel(sy(22))
        self.f_info = fonte_pixel(sy(16))

        pw, ph = sx(460), sy(330)
        self.painel_rect = pygame.Rect((self.W - pw) // 2, (self.H - ph) // 2, pw, ph)
        self._img_painel = criar_painel(pw, ph, raio=sx(24), prof=sy(8))
        p = self.painel_rect

        margem = sx(40)
        self.campo = Campo(
            (p.x + margem, p.y + sy(105), pw - 2 * margem, sy(52)),
            self.MAX_CARACTERES, carregar_fonte_typewriter(sy(22), bold=True),
            mascara=True, margem=sx(16))

        bw, bh = max(180, sx(220)), max(50, sy(60))
        self.btn_entrar = Botao("ENTRAR", p.centerx - bw // 2, p.bottom - bh - sy(35),
                                bw, bh, self.confirmar)
        self.btn_voltar = BotaoVoltar(cx=sx(38), cy=sy(38), raio=max(25, sx(30)),
                                      acao=self.voltar)
        self._botoes = [self.btn_entrar, self.btn_voltar]

    # ── ações ────────────────────────────────────────────────────────────────
    def resetar(self):
        self.campo.definir("")
        self.mensagem = ""
        pygame.key.start_text_input()

    def voltar(self):
        if self.callback_voltar:
            self.callback_voltar()

    def confirmar(self):
        if self.campo.texto == SENHA_ADMIN:
            self.mensagem = ""
            self.campo.definir("")
            if self.callback_sucesso:
                self.callback_sucesso()
        else:
            self.mensagem = "SENHA INCORRETA!" if self.campo.texto else "DIGITE A SENHA!"
            self.campo.definir("")

    # ── eventos ──────────────────────────────────────────────────────────────
    def handle_event(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for botao in self._botoes:
                if botao.rect.collidepoint(ev.pos):
                    botao.verificar_click(ev)
                    return
            if self.campo.rect.collidepoint(ev.pos):
                self.campo.clique(ev.pos)
        elif ev.type == pygame.TEXTINPUT:
            self.campo.inserir(ev.text)
            self.mensagem = ""
        elif ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.confirmar()
            elif ev.key == pygame.K_ESCAPE:
                self.voltar()
            else:
                self.campo.tecla(ev)

    # ── desenho ──────────────────────────────────────────────────────────────
    def desenhar(self, mouse_pos=None):
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()
        tela, sy, p = self.screen, self.sy, self.painel_rect

        tela.blit(self.fundo, (0, 0))
        tela.blit(self._veu, (0, 0))
        tela.blit(self._img_painel, p.topleft)

        cab = self._txt(self.f_cabecalho, "ADMIN", AMARELO_TITULO, CONTORNO_TITULO, 3)
        tela.blit(cab, cab.get_rect(center=(p.centerx, p.y + sy(42))))

        r = self.campo.rect
        label = self._txt(self.f_label, "SENHA:", BRANCO, CONTORNO_TITULO, 2)
        tela.blit(label, (r.x + 4, r.y - label.get_height() - sy(6)))
        self.campo.desenhar(tela, True)

        y = r.bottom + sy(18)
        if self.mensagem:
            linhas, cor = (self.mensagem,), COR_ERRO
        else:
            linhas, cor = ("ADICIONE A SENHA ADMIN", "PARA ENTRAR"), BRANCO
        for linha in linhas:
            surf = self._txt(self.f_info, linha, cor, CONTORNO_TITULO, 2)
            tela.blit(surf, surf.get_rect(midtop=(p.centerx, y)))
            y += surf.get_height() + sy(2)

        for botao in self._botoes:
            botao.desenhar(tela, mouse_pos)
