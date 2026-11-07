"""
Peças de desenho compartilhadas entre as telas: véus, painéis, textos com
cache, barra de vida e tela de carregamento.

Tudo aqui recebe a superfície onde desenhar; nenhuma função conhece o Jogo.
"""

from dataclasses import dataclass

import pygame

from src.nucleo import constants
from src.nucleo.estilo import CONTORNO_TITULO, CacheTexto, criar_painel
from src.nucleo.utils import carregar_fonte

ARQUIVO_FONTE = "upheavtt.ttf"


@dataclass(frozen=True)
class Fontes:
    """Fontes que vivem o jogo todo (o cache de texto é indexado por elas)."""
    ui: pygame.font.Font
    titulo: pygame.font.Font
    logo: pygame.font.Font

    @classmethod
    def carregar(cls):
        return cls(
            ui=carregar_fonte(ARQUIVO_FONTE, 28),
            titulo=carregar_fonte(ARQUIVO_FONTE, 18),
            logo=carregar_fonte(ARQUIVO_FONTE, 64),
        )


def tamanho_fonte(tamanho):
    """Tamanho mínimo legível (a tela de quiz recebe isto por injeção)."""
    return max(8, int(tamanho))


# ── caches ───────────────────────────────────────────────────────────────────
_overlays = {}
_veus_topo = {}
_textos = {}
_paineis = {}
_texto_estilo = CacheTexto()


def overlay(cor_rgba):
    """Véu translúcido do tamanho da tela, criado uma vez por cor."""
    chave = (cor_rgba, constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT)
    surf = _overlays.get(chave)
    if surf is None:
        surf = pygame.Surface(chave[1:], pygame.SRCALPHA)
        surf.fill(cor_rgba)
        _overlays[chave] = surf
    return surf


def veu_topo(altura=230, alpha_max=150):
    """Degradê azul-escuro no topo da tela, para o título destacar."""
    chave = (constants.SCREEN_WIDTH, altura, alpha_max)
    surf = _veus_topo.get(chave)
    if surf is None:
        surf = pygame.Surface((constants.SCREEN_WIDTH, altura), pygame.SRCALPHA)
        for y in range(altura):
            a = int(alpha_max * (1 - y / altura) ** 2)
            pygame.draw.line(surf, (10, 20, 80, a), (0, y), (constants.SCREEN_WIDTH, y))
        _veus_topo[chave] = surf
    return surf


def texto(fonte, conteudo, cor):
    """
    font.render com cache. HUD e avisos redesenham o MESMO texto a cada
    frame; renderizar fonte é das operações mais caras do pygame.
    """
    chave = (fonte, conteudo, cor)
    surf = _textos.get(chave)
    if surf is None:
        if len(_textos) > 256:
            _textos.clear()
        surf = fonte.render(conteudo, True, cor)
        _textos[chave] = surf
    return surf


def texto_c(fonte, conteudo, cor=constants.WHITE, espessura=2):
    """Texto com contorno azul (como o dos botões), renderizado uma vez só."""
    return _texto_estilo(fonte, conteudo, cor, CONTORNO_TITULO, espessura)


def painel_menu(tela, centro_x, topo, largura, altura):
    """Painel azul-escuro com borda dourada, centralizado em `centro_x`."""
    chave = (largura, altura)
    img = _paineis.get(chave)
    if img is None:
        img = criar_painel(largura, altura)
        _paineis[chave] = img
    tela.blit(img, (centro_x - largura // 2, topo))


def desenhar_barra_vida(surface, x, y, largura, altura, proporcao,
                        cor_cheia=constants.GREEN, cor_vazia=constants.RED):
    """Barra de vida genérica (jogador e boss)."""
    proporcao = max(0.0, min(1.0, proporcao))
    pygame.draw.rect(surface, cor_vazia, (x, y, largura, altura), border_radius=4)
    pygame.draw.rect(surface, cor_cheia, (x, y, int(largura * proporcao), altura),
                     border_radius=4)
    pygame.draw.rect(surface, constants.WHITE, (x, y, largura, altura), 2,
                     border_radius=4)


def tela_carregamento(janela, progresso=0, mensagem="Carregando..."):
    """Barra de progresso exibida durante cargas longas."""
    tela = janela.tela
    W = constants.SCREEN_WIDTH
    H = constants.SCREEN_HEIGHT
    tela.fill((20, 20, 40))
    try:
        fonte_titulo = carregar_fonte(ARQUIVO_FONTE, 48)
        titulo = fonte_titulo.render("I.S.A", True, (241, 187, 52))
        tela.blit(titulo, titulo.get_rect(center=(W // 2, H // 2 - 80)))
        fonte_msg = carregar_fonte(ARQUIVO_FONTE, 20)
        msg = fonte_msg.render(mensagem, True, (200, 200, 200))
        tela.blit(msg, msg.get_rect(center=(W // 2, H // 2 - 20)))
    except Exception as e:  # noqa: BLE001
        print(f"Erro ao desenhar tela de carregamento: {e}")
    barra_w, barra_h = 400, 20
    barra_x = (W - barra_w) // 2
    barra_y = H // 2 + 20
    pygame.draw.rect(tela, (60, 60, 80), (barra_x, barra_y, barra_w, barra_h),
                     border_radius=10)
    pygame.draw.rect(tela, (76, 175, 80),
                     (barra_x, barra_y, int(barra_w * progresso), barra_h),
                     border_radius=10)
    pygame.draw.rect(tela, (241, 187, 52), (barra_x, barra_y, barra_w, barra_h), 2,
                     border_radius=10)
    janela.apresentar()
