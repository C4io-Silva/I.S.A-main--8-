"""
Ambientes dinâmicos — troca de background por ALTURA, dentro da mesma fase.

Ideia central
-------------
O nível continua sendo um só (mesmo CSV, mesmo player, mesma progressão).
O que muda é a ATMOSFERA: conforme o jogador sobe ou desce, o conjunto de
camadas de paralaxe ao fundo é trocado — copas das árvores em cima, floresta
no meio, caverna embaixo — dissolvendo um ambiente no outro.

    y menor  ↑   copas das árvores
                 floresta          (zona central, ambiente principal)
    y maior  ↓   caverna

Em pygame o Y cresce para BAIXO, então a lista de zonas em ordem crescente
já sai naturalmente na ordem copas → floresta → caverna.

Como o crossfade funciona
-------------------------
Cada ambiente sabe se desenhar sozinho numa Surface. Numa fronteira:

    1. o ambiente que SAI é desenhado direto na tela (alpha cheio);
    2. o ambiente que ENTRA é desenhado num buffer reaproveitado;
    3. o buffer recebe set_alpha(t * 255) e é blitado por cima.

Como a camada de fundo de todo ambiente é opaca, o buffer é 100% opaco e o
set_alpha se comporta como uma dissolução linear exata. Nenhuma Surface é
alocada por frame: o buffer nasce uma vez só.

O `t` vem da POSIÇÃO, não de um cronômetro. É isso que dá a reversibilidade
pedida: subir desfaz a mistura na mesma proporção que descer fez. Não depende
de FPS e nunca fica presa no meio se o jogo travar.

Por que existe suavização
-------------------------
No eixo X a posição do jogador é monótona e lenta. No eixo Y não: um pulo
sobe e desce 3 tiles em meio segundo. Ler a altura crua faria o background
piscar a cada pulo. Por isso a referência passa por um filtro passa-baixa —
um pulo é rápido demais para mover o ambiente, uma descida sustentada não é.
Ajuste em constants.SUAVIZACAO_AMBIENTE.

Assets ausentes
---------------
Camadas sem PNG correspondente em assets/images/backgrounds são desenhadas
por geração procedural (somas de senos com frequência inteira, portanto sem
costura no tiling). Quando a arte real chegar, basta soltar o arquivo na
pasta: o carregamento por disco tem prioridade e o procedural some sozinho.
"""

import math

import pygame

from src.nucleo import constants
from src.nucleo.utils import carregar_imagem

# Amostragem das silhuetas procedurais. 6px já sai lisa depois de escalada.
_PASSO = 6

_NEUTRO_MULT = (255, 255, 255)
_NEUTRO_ADD = (0, 0, 0)

# Superfícies de cor sólida para a tonalidade/luz, uma por (tamanho, cor).
# blit com BLEND_RGB_MULT/ADD dá o MESMO resultado pixel a pixel que
# fill(..., BLEND_MULT/ADD), mas usa o caminho SIMD do pygame: medido em
# 960x600, 4,8 ms -> 0,2 ms por camada. Nas copas (tinta + luz) o fill era
# ~60% do tempo do quadro.
_cache_cor = {}


def _aplicar_cor(surface, cor, modo):
    chave = (surface.get_size(), surface.get_bitsize(), cor)
    sup = _cache_cor.get(chave)
    if sup is None:
        if len(_cache_cor) > 16:   # dissolução contínua gera cores novas
            _cache_cor.clear()
        sup = pygame.Surface(surface.get_size(), 0, surface)
        sup.fill(cor)
        _cache_cor[chave] = sup
    surface.blit(sup, (0, 0), special_flags=modo)


# ── Geração procedural (usada só quando o PNG não existe) ─────────────────────
def _perfil(largura, base, harmonicos, afiado=False):
    """
    Linha do horizonte de uma silhueta, como soma de senos.

    As frequências são INTEIRAS em relação à largura, então f(0) == f(L) e a
    imagem repete lado a lado sem emenda. `afiado=True` aplica abs() na onda,
    trocando colinas por picos — é o que dá cara de estalactite.
    """
    pontos = []
    for x in range(0, largura + _PASSO, _PASSO):
        v = 0.0
        for freq, amp, fase in harmonicos:
            v += amp * math.sin(2 * math.pi * freq * x / largura + fase)
        if afiado:
            v = abs(v)
        pontos.append((x, base + v))
    return pontos


def _silhueta_inferior(surface, largura, altura, base, harmonicos, cor, afiado=False):
    """Massa sólida que sobe do rodapé até a linha do perfil."""
    pontos = _perfil(largura, base, harmonicos, afiado)
    pygame.draw.polygon(surface, cor, pontos + [(largura, altura), (0, altura)])


def _silhueta_superior(surface, largura, base, harmonicos, cor, afiado=False):
    """Massa sólida que desce do topo até a linha do perfil."""
    pontos = _perfil(largura, base, harmonicos, afiado)
    pygame.draw.polygon(surface, cor, pontos + [(largura, 0), (0, 0)])


def _pinheiros(surface, largura, altura, base, cor, espacamento, escala):
    """
    Coníferas sobre a linha do terreno. Todas ficam inteiramente dentro da
    imagem (a primeira em espacamento/2), então nenhuma é cortada pela emenda.
    """
    x = espacamento // 2
    i = 0
    while x < largura - espacamento // 2:
        # Alturas variadas mas determinísticas: idêntico em toda máquina.
        h = escala * (0.75 + 0.25 * math.sin(i * 2.399))
        larg = h * 0.45
        pygame.draw.polygon(
            surface,
            cor,
            [
                (x, base - h),
                (x - larg / 2, base + altura * 0.05),
                (x + larg / 2, base + altura * 0.05),
            ],
        )
        x += espacamento
        i += 1


def _folhagem(surface, largura, cor, base, raio, espacamento):
    """Bolhas de copa penduradas no topo, para o ambiente 'copas'."""
    x = espacamento // 2
    i = 0
    while x < largura - espacamento // 2:
        r = raio * (0.7 + 0.3 * math.sin(i * 1.713))
        y = base + raio * 0.4 * math.sin(i * 0.941)
        pygame.draw.circle(surface, cor, (int(x), int(y)), int(r))
        x += espacamento
        i += 1


def _gerar_camada(estilo, indice, largura, altura):
    """
    Uma camada de paralaxe desenhada na mão. `indice` 0 é o fundo (mais claro
    e distante); índices maiores são frontais (mais escuros, mais movimento).
    """
    surf = pygame.Surface((largura, altura), pygame.SRCALPHA)
    fundo = indice == 0

    if estilo == "caverna":
        cor = (58, 48, 66) if fundo else (28, 22, 34)
        # Teto e chão de rocha com picos apontando para dentro. Amplitudes
        # generosas de propósito: com picos tímidos sobrava uma faixa lisa no
        # meio e a caverna virava um retângulo preto.
        _silhueta_superior(
            surf,
            largura,
            altura * (0.20 if fundo else 0.10),
            [(3, altura * 0.26, 0.0), (7, altura * 0.11, 1.9), (13, altura * 0.05, 4.1)],
            cor,
            afiado=True,
        )
        _silhueta_inferior(
            surf,
            largura,
            altura,
            altura * (0.74 if fundo else 0.86),
            [(4, -altura * 0.24, 1.2), (9, -altura * 0.10, 3.3), (15, -altura * 0.04, 0.7)],
            cor,
            afiado=True,
        )

    elif estilo == "copas":
        cor = (46, 82, 44) if fundo else (18, 42, 22)
        _silhueta_superior(
            surf,
            largura,
            altura * (0.46 if fundo else 0.30),
            [(2, altura * 0.12, 0.6), (5, altura * 0.06, 2.4), (11, altura * 0.025, 5.0)],
            cor,
        )
        _folhagem(surf, largura, cor, altura * (0.48 if fundo else 0.32), altura * 0.11, 130)
        # Galhos descendo da copa. Espessos: com 5px viravam gravetos no ar.
        passo = 190 if fundo else 150
        x = passo // 2
        while x < largura - passo // 2:
            pygame.draw.line(
                surf, cor, (x, altura * 0.25), (x, altura * (0.68 if fundo else 0.86)), 11
            )
            x += passo
        # Copa distante no rodapé: sem ela sobrava uma faixa chapada do céu.
        if fundo:
            _silhueta_inferior(
                surf,
                largura,
                altura,
                altura * 0.86,
                [(3, -altura * 0.06, 1.4), (8, -altura * 0.025, 3.7)],
                (74, 108, 72),
            )

    else:  # "floresta" e qualquer estilo desconhecido
        cor = (40, 70, 50) if fundo else (18, 34, 26)
        base = altura * (0.58 if fundo else 0.74)
        _silhueta_inferior(
            surf,
            largura,
            altura,
            base,
            [(2, -altura * 0.07, 0.3), (5, -altura * 0.035, 2.1), (11, -altura * 0.015, 4.4)],
            cor,
        )
        _pinheiros(
            surf,
            largura,
            altura,
            base,
            cor,
            espacamento=150 if fundo else 110,
            escala=altura * (0.20 if fundo else 0.34),
        )

    return surf.convert_alpha()


# ── Partículas atmosféricas ───────────────────────────────────────────────────
class Camada:
    """Uma faixa de paralaxe: imagem repetida no eixo X a uma dada velocidade."""

    __slots__ = ("img", "fator", "largura")

    def __init__(self, img, fator):
        self.img = img
        self.fator = fator
        self.largura = img.get_width()

    def desenhar(self, surface, camera_x):
        larg = self.largura
        limite = surface.get_width()
        # Offset sempre em [0, larg): o loop começa uma imagem à esquerda
        # para não abrir buraco na borda.
        x = (int(-camera_x * self.fator) % larg) - larg
        while x < limite:
            surface.blit(self.img, (x, 0))
            x += larg


class Ambiente:
    """Camadas + céu + atmosfera. Sabe se desenhar por inteiro."""

    def __init__(self, nome, cor_ceu, camadas, tint, luz):
        self.nome = nome
        self.cor_ceu = cor_ceu
        self.camadas = camadas
        self.tint = tint            # multiplicativo, (255,255,255) = neutro
        self.luz = luz              # aditivo, (0,0,0) = neutro

    @classmethod
    def criar(cls, nome, config, largura, altura):
        estilo = config.get("estilo", nome)
        cor_ceu = config.get("cor_ceu", (0, 0, 0))
        camadas = []

        for indice, (arquivo, fator) in enumerate(config.get("camadas", [])):
            img = cls._carregar(arquivo, altura)
            if img is None:
                # Sem arte ainda: silhueta procedural com largura confortável
                # (nunca menor que a tela, para poucos blits por frame).
                img = _gerar_camada(estilo, indice, max(1024, largura), altura)
            if indice == 0:
                # A camada do fundo é achatada contra o céu e perde o alpha.
                # Duas economias medidas: o fill() da tela some (esta camada
                # já cobre tudo) e o blit vira cópia crua, não mistura.
                img = cls._achatar(img, cor_ceu, altura)
            camadas.append(Camada(img, fator))

        return cls(
            nome,
            cor_ceu,
            camadas,
            config.get("tint", _NEUTRO_MULT),
            config.get("luz", _NEUTRO_ADD),
        )

    @staticmethod
    def _achatar(img, cor_ceu, altura):
        """Compõe a camada sobre o céu e devolve uma Surface 100% opaca."""
        base = pygame.Surface((img.get_width(), altura))
        base.fill(cor_ceu)
        base.blit(img, (0, 0))
        return base.convert()

    @staticmethod
    def _carregar(arquivo, altura):
        """
        Lê o PNG e escala pela ALTURA preservando a proporção — a largura não
        importa, a camada é repetida no X de qualquer jeito. None se faltar.
        """
        if not arquivo:
            return None
        try:
            img = carregar_imagem("backgrounds", arquivo)
        except (FileNotFoundError, pygame.error):
            return None
        larg = max(1, img.get_width() * altura // max(1, img.get_height()))
        return pygame.transform.scale(img, (larg, altura))

    def desenhar(self, surface, camera_x):
        if not self.camadas:
            surface.fill(self.cor_ceu)
            return
        # Sem fill(): a camada 0 é opaca e cobre a tela inteira (ver _achatar).
        for camada in self.camadas:
            camada.desenhar(surface, camera_x)


class GerenciadorAmbientes:
    """
    Decide qual ambiente vale para cada faixa do mapa e faz a mistura.

    zonas: lista de (limite, nome), onde `limite` é a linha (eixo "y") ou a
    coluna (eixo "x") em que a zona começa. A zona vale dali até o início da
    próxima; a dissolução fica CENTRADA na fronteira, com metade da largura
    de transição de cada lado.
    """

    def __init__(
        self,
        largura,
        altura,
        definicoes=None,
        zonas=None,
        transicao_tiles=None,
        eixo=None,
        suavizacao=None,
        modo_discreto=None,
    ):
        definicoes = definicoes if definicoes is not None else constants.AMBIENTES
        zonas = zonas if zonas is not None else constants.ZONAS_AMBIENTE

        self.largura = largura
        self.altura = altura
        self.eixo = (eixo or getattr(constants, "EIXO_AMBIENTE", "y")).lower()
        self.ambientes = {
            nome: Ambiente.criar(nome, cfg, largura, altura)
            for nome, cfg in definicoes.items()
        }

        # Modo discreto (padrão): o ambiente só troca via forcar(), chamado
        # por main.py dentro do callback de uma Transicao (tela 100% preta).
        # Sem isso, GerenciadorAmbientes cairia de volta no comportamento
        # antigo — reler a POSIÇÃO do player a cada frame e dissolver
        # sozinho — que é exatamente o que a feature de passagens tirou.
        if modo_discreto is None:
            modo_discreto = getattr(constants, "AMBIENTE_MODO_DISCRETO", True)
        self.modo_discreto = modo_discreto

        # Ordena pelo limite e descarta zonas que apontem para ambiente ausente
        self.zonas = sorted([(lim, nome) for lim, nome in zonas if nome in self.ambientes])
        if not self.zonas:
            # Nunca deixa o jogo sem fundo: cai no primeiro ambiente definido.
            self.zonas = [(0, next(iter(self.ambientes)))]

        if transicao_tiles is None:
            transicao_tiles = getattr(constants, "TRANSICAO_TILES", 4)
        self.transicao = max(1, transicao_tiles * constants.TILE_SIZE)

        if suavizacao is None:
            suavizacao = getattr(constants, "SUAVIZACAO_AMBIENTE", 0.05)
        self.suavizacao = min(1.0, max(0.001, suavizacao))

        # Buffer reaproveitado do ambiente que entra durante a dissolução.
        # convert() e não convert_alpha: o ambiente preenche tudo, e set_alpha
        # em Surface opaca é o caminho rápido do pygame. Só é usado no modo
        # contínuo — no discreto não existe dissolução, então nunca é lido.
        self._buffer = pygame.Surface((largura, altura)).convert()

        self._ref = None          # referência suavizada (só modo contínuo)
        self._saindo = self.zonas[0][1]
        self._entrando = None
        self.nome_atual = self.zonas[0][1]
        self.mistura = 0.0        # 0..1, quanto do próximo ambiente está visível

    def forcar(self, nome):
        """
        Troca o ambiente atual IMEDIATAMENTE, sem dissolução — usado só no
        modo discreto, chamado enquanto a tela está 100% preta (ver
        src/transicao.py). Se `nome` não existir em AMBIENTES, não faz nada
        (fica no ambiente anterior) em vez de derrubar o jogo.
        """
        if nome not in self.ambientes:
            return
        self._saindo = nome
        self._entrando = None
        self.mistura = 0.0
        self.nome_atual = nome

    def reiniciar(self, posicao=None):
        """
        Zera o filtro. Chamado ao (re)carregar a fase: sem isso o jogador
        renasce no spawn e o background leva um segundo escorregando de volta,
        porque a referência suavizada ainda estava onde ele morreu.
        """
        self._ref = None if posicao is None else float(posicao)

    def _resolver(self, pos):
        """Devolve (ambiente_saindo, ambiente_entrando_ou_None, t)."""
        meia = self.transicao * 0.5
        tile = constants.TILE_SIZE

        idx = 0
        for i, (limite, _nome) in enumerate(self.zonas):
            if pos >= limite * tile:
                idx = i

        atual = self.zonas[idx][1]

        # Ainda dentro da faixa de entrada desta zona (fronteira anterior)
        if idx > 0:
            limite = self.zonas[idx][0] * tile
            if pos < limite + meia:
                t = (pos - (limite - meia)) / self.transicao
                return self.zonas[idx - 1][1], atual, min(1.0, max(0.0, t))

        # Já entrando na faixa de saída (fronteira seguinte)
        if idx + 1 < len(self.zonas):
            limite = self.zonas[idx + 1][0] * tile
            if pos > limite - meia:
                t = (pos - (limite - meia)) / self.transicao
                return atual, self.zonas[idx + 1][1], min(1.0, max(0.0, t))

        return atual, None, 0.0

    def _atualizar_referencia(self, referencia, camera_x, camera_y):
        if referencia is None:
            # Sem player (menu, tela de morte): usa o centro da tela.
            base = camera_y if self.eixo == "y" else camera_x
            metade = self.altura if self.eixo == "y" else self.largura
            referencia = base + metade * 0.5

        if self._ref is None:
            self._ref = float(referencia)   # primeiro frame: sem deslizar
        else:
            self._ref += (referencia - self._ref) * self.suavizacao
        return self._ref

    def desenhar(self, surface, camera_x, referencia=None, camera_y=0):
        """
        Desenha o fundo do frame.

        No modo discreto (padrão): ignora `referencia` por completo e
        desenha só `self.nome_atual`, sem dissolução — o ambiente muda
        exclusivamente via `forcar()`.

        No modo contínuo (AMBIENTE_MODO_DISCRETO = False): `referencia` é a
        posição do jogador ao longo do eixo configurado — com
        EIXO_AMBIENTE = "y", passe player.rect.centery. Usar o jogador e não
        a câmera importa nas bordas do mapa, onde a câmera trava e a
        transição congelaria pela metade.
        """
        if self.modo_discreto:
            self.ambientes[self.nome_atual].desenhar(surface, camera_x)
            return

        pos = self._atualizar_referencia(referencia, camera_x, camera_y)

        saindo, entrando, t = self._resolver(pos)
        self._saindo, self._entrando, self.mistura = saindo, entrando, t
        self.nome_atual = entrando if (entrando and t >= 0.5) else saindo

        self.ambientes[saindo].desenhar(surface, camera_x)

        if entrando is None or t <= 0.0:
            return
        if t >= 1.0:
            # Dissolução completa: desenha direto, sem pagar o buffer.
            self.ambientes[entrando].desenhar(surface, camera_x)
            return

        self.ambientes[entrando].desenhar(self._buffer, camera_x)
        self._buffer.set_alpha(int(t * 255))
        surface.blit(self._buffer, (0, 0))

    # ── Atmosfera ─────────────────────────────────────────────────────────────
    @staticmethod
    def _misturar(cor_a, cor_b, t):
        return (
            int(cor_a[0] + (cor_b[0] - cor_a[0]) * t),
            int(cor_a[1] + (cor_b[1] - cor_a[1]) * t),
            int(cor_a[2] + (cor_b[2] - cor_a[2]) * t),
        )

    def desenhar_atmosfera(self, surface, camera_x=0, camera_y=0):
        """
        Tonalidade, luz e partículas do ambiente atual.

        Chamada DEPOIS do mundo, dos inimigos e do jogador, mas ANTES da HUD:
        a intenção é escurecer a cena, não a barra de vida. Tinta e luz são
        blits de uma superfície de cor sólida em cache (ver _aplicar_cor).
        """
        a = self.ambientes[self._saindo]
        b = self.ambientes[self._entrando] if self._entrando else a
        t = self.mistura if self._entrando else 0.0

        tint = self._misturar(a.tint, b.tint, t)
        if tint != _NEUTRO_MULT:
            _aplicar_cor(surface, tint, pygame.BLEND_RGB_MULT)

        luz = self._misturar(a.luz, b.luz, t)
        if luz != _NEUTRO_ADD:
            _aplicar_cor(surface, luz, pygame.BLEND_RGB_ADD)
