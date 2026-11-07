"""
Campo de texto do painel ADMIN: uma linha (com rolagem lateral), várias
linhas (quebra automática) ou senha (bolinhas). Tem cursor, que anda com as
setas/Home/End/clique, e funciona com o TEXTINPUT do pygame (acentos e
cedilha saem certos).

O visual é o mesmo do campo da tela de login: miolo creme, borda azul-escura
e borda dourada quando está selecionado.
"""

import pygame

from src.nucleo.estilo import AZUL_ESCURO, CLARO, DOURADO

TXT_ESCURO = (35, 40, 60)
TXT_PLACEHOLDER = (150, 145, 135)

_imagens = {}


def imagem_campo(largura, altura, ativo, prof=4):
    """Fundo do campo, desenhado grande e reduzido (borda sem serrilhado)."""
    chave = (largura, altura, ativo, prof)
    img = _imagens.get(chave)
    if img is None:
        k = 4
        raio = max(8, min(altura // 4, 14))
        alta = pygame.Surface((largura * k, (altura + prof) * k), pygame.SRCALPHA)
        pygame.draw.rect(alta, (10, 14, 55), (0, prof * k, largura * k, altura * k),
                         border_radius=raio * k)
        corpo = pygame.Rect(0, 0, largura * k, altura * k)
        pygame.draw.rect(alta, CLARO, corpo, border_radius=raio * k)
        pygame.draw.rect(alta, DOURADO if ativo else AZUL_ESCURO, corpo,
                         (4 if ativo else 3) * k, border_radius=raio * k)
        img = pygame.transform.smoothscale(alta, (largura, altura + prof))
        if len(_imagens) > 80:
            _imagens.clear()
        _imagens[chave] = img
    return img


def quebrar(texto, fonte, largura):
    """
    Quebra `texto` em linhas que cabem em `largura` pixels. Devolve uma lista
    de (inicio, fim): a linha é texto[inicio:fim], e as linhas juntas cobrem o
    texto inteiro sem perder nenhum caractere (o espaço onde a linha quebrou
    fica no fim dela). Palavra maior que a linha é quebrada no meio.
    """
    n = len(texto)
    if n == 0:
        return [(0, 0)]
    linhas = []
    ini = 0
    while ini < n:
        fim = ini
        espaco = -1
        while fim < n and fonte.size(texto[ini:fim + 1])[0] <= largura:
            if texto[fim] == " ":
                espaco = fim
            fim += 1
        if fim >= n:                      # o resto cabe inteiro
            linhas.append((ini, n))
            break
        if fim == ini:                    # nem um caractere cabe: avança 1
            fim = ini + 1
        elif espaco > ini:                # quebra depois do último espaço
            fim = espaco + 1
        linhas.append((ini, fim))
        ini = fim
    return linhas


def cortar(texto, fonte, largura):
    """Corta `texto` com reticências para caber em `largura`."""
    if fonte.size(texto)[0] <= largura:
        return texto
    while texto and fonte.size(texto + "...")[0] > largura:
        texto = texto[:-1]
    return texto.rstrip() + "..."


class Campo:
    def __init__(self, rect, max_caracteres, fonte, multilinha=False,
                 placeholder="", mascara=False, margem=12):
        self.rect = pygame.Rect(rect)
        self.max = max_caracteres
        self.fonte = fonte
        self.multilinha = multilinha
        self.placeholder = placeholder
        self.mascara = mascara
        self.margem = margem
        self.texto = ""
        self.cursor = 0
        self._rolagem = 0              # px (uma linha) ou nº da 1ª linha visível (várias)
        self._cache_linhas = None      # (texto, largura, linhas)

    # ── geometria ────────────────────────────────────────────────────────────
    @property
    def area(self):
        r = self.rect
        return pygame.Rect(r.x + self.margem, r.y + 4, r.width - 2 * self.margem,
                           r.height - 8)

    @property
    def _altura_linha(self):
        return self.fonte.get_linesize()

    @property
    def _passo_mascara(self):
        return max(10, self._altura_linha // 2 + 6)

    def _linhas(self):
        largura = self.area.width
        c = self._cache_linhas
        if c is None or c[0] != self.texto or c[1] != largura:
            c = (self.texto, largura, quebrar(self.texto, self.fonte, largura))
            self._cache_linhas = c
        return c[2]

    def _linha_do_cursor(self, linhas):
        for i, (ini, fim) in enumerate(linhas):
            if ini <= self.cursor < fim:
                return i
        return len(linhas) - 1

    @staticmethod
    def _fim_util(texto, ini, fim, ultima):
        """Fim da linha sem o espaço da quebra (o cursor não fica 'depois' dele)."""
        if not ultima and fim > ini and texto[fim - 1] == " ":
            return fim - 1
        return fim

    # ── edição ───────────────────────────────────────────────────────────────
    def definir(self, texto):
        self.texto = (texto or "")[: self.max]
        self.cursor = len(self.texto)
        self._rolagem = 0

    def inserir(self, texto):
        """Insere no cursor. Quebra de linha e tab viram espaço; respeita o máximo."""
        texto = "".join(" " if c in "\r\n\t" else c for c in texto)
        texto = "".join(c for c in texto if c.isprintable())
        texto = texto[: max(0, self.max - len(self.texto))]
        if not texto:
            return
        self.texto = self.texto[: self.cursor] + texto + self.texto[self.cursor:]
        self.cursor += len(texto)

    def colar(self):
        """Cola da área de transferência (se o sistema permitir; senão ignora)."""
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            bruto = pygame.scrap.get(pygame.SCRAP_TEXT)
            if isinstance(bruto, bytes):
                bruto = bruto.decode("utf-8", "ignore")
            self.inserir((bruto or "").replace("\x00", ""))
        except Exception:  # noqa: BLE001 - colar é só um conforto
            pass

    def tecla(self, ev):
        """Teclas de edição. Devolve True se a tecla foi usada."""
        k = ev.key
        if k == pygame.K_BACKSPACE:
            if self.cursor > 0:
                self.texto = self.texto[: self.cursor - 1] + self.texto[self.cursor:]
                self.cursor -= 1
        elif k == pygame.K_DELETE:
            self.texto = self.texto[: self.cursor] + self.texto[self.cursor + 1:]
        elif k == pygame.K_LEFT:
            self.cursor = max(0, self.cursor - 1)
        elif k == pygame.K_RIGHT:
            self.cursor = min(len(self.texto), self.cursor + 1)
        elif k in (pygame.K_HOME, pygame.K_END):
            inicio = k == pygame.K_HOME
            if self.multilinha:
                ini, fim = self._linhas()[self._linha_do_cursor(self._linhas())]
                self.cursor = ini if inicio else self._fim_util(
                    self.texto, ini, fim, fim >= len(self.texto))
            else:
                self.cursor = 0 if inicio else len(self.texto)
        elif k in (pygame.K_UP, pygame.K_DOWN) and self.multilinha:
            self._mover_vertical(-1 if k == pygame.K_UP else 1)
        else:
            return False
        return True

    def _mover_vertical(self, delta):
        linhas = self._linhas()
        i = self._linha_do_cursor(linhas)
        j = i + delta
        if not 0 <= j < len(linhas):
            return
        x = self.fonte.size(self.texto[linhas[i][0]:self.cursor])[0]
        ini, fim = linhas[j]
        fim = self._fim_util(self.texto, ini, fim, j == len(linhas) - 1)
        self.cursor = ini + self._indice_por_x(self.texto[ini:fim], x)

    # ── mouse ────────────────────────────────────────────────────────────────
    def _indice_por_x(self, trecho, x):
        """Posição do cursor (0..len) mais próxima do pixel x dentro de `trecho`."""
        if self.mascara:
            return max(0, min(len(trecho), int(round(x / self._passo_mascara))))
        anterior = 0
        for j in range(1, len(trecho) + 1):
            w = self.fonte.size(trecho[:j])[0]
            if w >= x:
                return j if (w - x) < (x - anterior) else j - 1
            anterior = w
        return len(trecho)

    def clique(self, pos):
        a = self.area
        if self.multilinha:
            linhas = self._linhas()
            i = self._rolagem + max(0, (pos[1] - a.y) // self._altura_linha)
            i = min(i, len(linhas) - 1)
            ini, fim = linhas[i]
            fim = self._fim_util(self.texto, ini, fim, i == len(linhas) - 1)
            self.cursor = ini + self._indice_por_x(self.texto[ini:fim], pos[0] - a.x)
        else:
            self.cursor = self._indice_por_x(self.texto, pos[0] - a.x + self._rolagem)

    # ── desenho ──────────────────────────────────────────────────────────────
    def _x_cursor(self):
        if self.mascara:
            return self.cursor * self._passo_mascara
        return self.fonte.size(self.texto[: self.cursor])[0]

    def desenhar(self, tela, ativo):
        r = self.rect
        tela.blit(imagem_campo(r.width, r.height, bool(ativo)), r.topleft)
        a = self.area
        piscar = ativo and (pygame.time.get_ticks() // 500) % 2 == 0
        tela.set_clip(a)
        if self.multilinha:
            self._desenhar_varias(tela, a, ativo, piscar)
        else:
            self._desenhar_uma(tela, a, ativo, piscar)
        tela.set_clip(None)

    def _desenhar_uma(self, tela, a, ativo, piscar):
        cx = self._x_cursor()
        # Rolagem lateral: o cursor sempre fica à vista.
        if cx - self._rolagem > a.width - 3:
            self._rolagem = cx - a.width + 3
        if cx < self._rolagem:
            self._rolagem = cx
        total = (len(self.texto) * self._passo_mascara if self.mascara
                 else self.fonte.size(self.texto)[0])
        self._rolagem = max(0, min(self._rolagem, max(0, total - a.width + 3)))
        meio = a.centery

        if self.mascara:
            raio = max(3, self._altura_linha // 5)
            for i in range(len(self.texto)):
                x = a.x + i * self._passo_mascara + self._passo_mascara // 2 - self._rolagem
                pygame.draw.circle(tela, TXT_ESCURO, (x, meio), raio)
        elif self.texto:
            img = self.fonte.render(self.texto, True, TXT_ESCURO)
            tela.blit(img, (a.x - self._rolagem, meio - img.get_height() // 2))
        elif self.placeholder and not ativo:
            img = self.fonte.render(self.placeholder, True, TXT_PLACEHOLDER)
            tela.blit(img, (a.x, meio - img.get_height() // 2))

        if piscar:
            x = a.x + cx - self._rolagem + (2 if not self.mascara else 0)
            pygame.draw.rect(tela, TXT_ESCURO,
                             (x, meio - self._altura_linha // 2 + 1, 2,
                              self._altura_linha - 2))

    def _desenhar_varias(self, tela, a, ativo, piscar):
        h = self._altura_linha
        visiveis = max(1, a.height // h)
        linhas = self._linhas()
        atual = self._linha_do_cursor(linhas)
        if atual < self._rolagem:
            self._rolagem = atual
        elif atual >= self._rolagem + visiveis:
            self._rolagem = atual - visiveis + 1
        self._rolagem = max(0, min(self._rolagem, max(0, len(linhas) - visiveis)))

        if not self.texto and self.placeholder and not ativo:
            img = self.fonte.render(self.placeholder, True, TXT_PLACEHOLDER)
            tela.blit(img, (a.x, a.y))
        for k in range(visiveis):
            i = self._rolagem + k
            if i >= len(linhas):
                break
            ini, fim = linhas[i]
            trecho = self.texto[ini:fim].rstrip(" ")
            if trecho:
                tela.blit(self.fonte.render(trecho, True, TXT_ESCURO),
                          (a.x, a.y + k * h))
        if piscar:
            ini, _ = linhas[atual]
            x = a.x + self.fonte.size(self.texto[ini:self.cursor])[0] + 1
            y = a.y + (atual - self._rolagem) * h
            pygame.draw.rect(tela, TXT_ESCURO, (x, y + 1, 2, h - 2))
