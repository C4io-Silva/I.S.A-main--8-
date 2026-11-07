"""Kit de autoria dos mapas do I.S.A. (redesign v0.7).

Nada aqui gera mapa "aleatório": cada setor é descrito à mão em seu módulo
(perfil do terreno, plataformas, marcadores). O kit só cuida do trabalho
mecânico e repetitivo:

  * Grade      — matriz de IDs com operações de preenchimento.
  * ruido()    — ruído de valor determinístico (hash), usado só para VARIAR a
                 textura (qual tile de terra, onde nasce uma flor), nunca para
                 decidir geometria.
  * Compositor — posiciona decorações lendo a geometria física: superfícies
                 (apoio no chão), tetos (pendurar), bordas, zonas limpas.
  * gravar_csv — grava respeitando separador / BOM / quebra de linha do
                 arquivo original.

IDs usados são exatamente os definidos em constants.TILE_SPRITES,
constants.SOLID_TILES e src/decoracoes_offline.ARTE.
"""
import math

VAZIO = -1

# ── ruído determinístico ─────────────────────────────────────────────────────
def _hash(x, y, seed):
    h = (x * 374761393 + y * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def ruido(x, y, seed=0, escala=6.0):
    """Ruído de valor suave em [0,1]. `escala` = tamanho das manchas em células."""
    fx, fy = x / escala, y / escala
    x0, y0 = math.floor(fx), math.floor(fy)
    tx, ty = fx - x0, fy - y0
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    a = _hash(x0, y0, seed); b = _hash(x0 + 1, y0, seed)
    c = _hash(x0, y0 + 1, seed); d = _hash(x0 + 1, y0 + 1, seed)
    return (a + (b - a) * tx) + ((c + (d - c) * tx) - (a + (b - a) * tx)) * ty


def acaso(x, y, seed=0):
    """Valor pseudoaleatório por célula em [0,1] (sem suavização)."""
    return _hash(x, y, seed + 9001)


# ── grade ────────────────────────────────────────────────────────────────────
class Grade:
    def __init__(self, linhas, colunas, valor=VAZIO):
        self.linhas, self.colunas = linhas, colunas
        self.g = [[valor] * colunas for _ in range(linhas)]

    def dentro(self, c, r):
        return 0 <= c < self.colunas and 0 <= r < self.linhas

    def get(self, c, r, fora=VAZIO):
        return self.g[r][c] if self.dentro(c, r) else fora

    def set(self, c, r, v):
        if self.dentro(c, r):
            self.g[r][c] = v

    def retangulo(self, c0, c1, r0, r1, v):
        for r in range(max(0, r0), min(self.linhas - 1, r1) + 1):
            for c in range(max(0, c0), min(self.colunas - 1, c1) + 1):
                self.g[r][c] = v


def perfil(pontos, colunas):
    """[(coluna_inicial, linha), ...] -> lista com a linha do topo em cada coluna."""
    pontos = sorted(pontos)
    alt = [None] * colunas
    for i, (c, r) in enumerate(pontos):
        fim = pontos[i + 1][0] if i + 1 < len(pontos) else colunas
        for x in range(c, min(fim, colunas)):
            alt[x] = r
    assert all(a is not None for a in alt), "perfil sem cobertura total"
    return alt


def checar_perfil(alt, degrau_max=2, rotulo=""):
    """Garante degraus andáveis (≤ degrau_max) entre colunas vizinhas."""
    for c in range(1, len(alt)):
        if abs(alt[c] - alt[c - 1]) > degrau_max:
            raise ValueError(f"{rotulo}: degrau de {abs(alt[c]-alt[c-1])} entre col {c-1} e {c}")


# ── leitura / gravação ───────────────────────────────────────────────────────
def ler_formato(caminho):
    raw = open(caminho, "rb").read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    txt = raw.decode("utf-8-sig")
    primeira = txt.splitlines()[0]
    sep = ";" if ";" in primeira else ","
    nl = "\r\n" if "\r\n" in txt else "\n"
    final = txt.endswith(("\n", "\r\n"))
    return {"bom": bom, "sep": sep, "nl": nl, "final": final}


def ler_csv(caminho):
    fmt = ler_formato(caminho)
    txt = open(caminho, encoding="utf-8-sig").read()
    return [[int(v) for v in l.split(fmt["sep"]) if v.strip() != ""]
            for l in txt.splitlines() if l.strip()]


def gravar_csv(caminho, matriz, formato):
    corpo = formato["nl"].join(formato["sep"].join(str(v) for v in row) for row in matriz)
    if formato["final"]:
        corpo += formato["nl"]
    dados = corpo.encode("utf-8")
    if formato["bom"]:
        dados = b"\xef\xbb\xbf" + dados
    open(caminho, "wb").write(dados)


# ── compositor de decorações ─────────────────────────────────────────────────
class Compositor:
    """
    Decorações posicionadas a partir da geometria física.

    terreno : Grade com IDs físicos e marcadores.
    solidos : conjunto de IDs com colisão (constants.SOLID_TILES).
    bloqueados : IDs que não podem receber decoração (marcadores).
    """

    def __init__(self, terreno, solidos, bloqueados):
        self.t = terreno
        self.solidos = solidos
        self.bloqueados = set(bloqueados)
        self.d = Grade(terreno.linhas, terreno.colunas)
        self.reservado = set()   # (c, r) que devem ficar visualmente limpas

    # consultas de geometria
    def solido(self, c, r):
        return self.t.get(c, r, fora=0) in self.solidos

    def livre(self, c, r):
        """Célula onde uma decoração pode existir (sem colisão, sem marcador, vaga)."""
        if not self.t.dentro(c, r):
            return False
        v = self.t.g[r][c]
        return (v not in self.solidos and v not in self.bloqueados
                and self.d.g[r][c] == VAZIO and (c, r) not in self.reservado)

    def apoio(self, c, r):
        """Célula livre com bloco sólido logo abaixo (algo pousado no chão)."""
        return self.livre(c, r) and self.solido(c, r + 1)

    def teto(self, c, r):
        """Célula livre com bloco sólido logo acima (algo pendurado)."""
        return self.livre(c, r) and self.solido(c, r - 1)

    def reservar(self, c0, c1, r0, r1):
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                self.reservado.add((c, r))

    def por(self, c, r, v):
        if self.livre(c, r):
            self.d.g[r][c] = v
            return True
        return False

    # vinhetas
    def grupo_chao(self, c, r, ids):
        """Coloca `ids` lado a lado, todos apoiados no mesmo nível, a partir de c."""
        cels = [(c + i, r) for i in range(len(ids))]
        if not all(self.apoio(x, y) or v == VAZIO for (x, y), v in zip(cels, ids)):
            return False
        for (x, y), v in zip(cels, ids):
            if v != VAZIO:
                self.d.g[y][x] = v
        return True

    def pendurar(self, c, r, ids):
        """Coluna pendurada a partir de (c, r) para baixo; para se encontrar obstáculo."""
        if not self.teto(c, r):
            return 0
        n = 0
        for i, v in enumerate(ids):
            if not self.livre(c, r + i):
                break
            self.d.g[r + i][c] = v
            n += 1
        return n

    def superficies(self, c0=0, c1=None):
        """Trechos contínuos [(c_ini, c_fim, linha_da_celula_livre)] onde se pousa algo."""
        c1 = self.t.colunas - 1 if c1 is None else c1
        por_linha = {}
        for c in range(c0, c1 + 1):
            for r in range(1, self.t.linhas):
                if self.solido(c, r) and not self.solido(c, r - 1):
                    por_linha.setdefault(r - 1, []).append(c)
        trechos = []
        for r, cols in por_linha.items():
            cols.sort()
            ini = ant = cols[0]
            for c in cols[1:] + [None]:
                if c is not None and c == ant + 1:
                    ant = c
                    continue
                trechos.append((ini, ant, r))
                if c is not None:
                    ini = ant = c
        return sorted(trechos)

    def tetos(self, c0=0, c1=None):
        c1 = self.t.colunas - 1 if c1 is None else c1
        out = []
        for c in range(c0, c1 + 1):
            for r in range(1, self.t.linhas):
                if self.solido(c, r - 1) and not self.solido(c, r):
                    out.append((c, r))
        return out
