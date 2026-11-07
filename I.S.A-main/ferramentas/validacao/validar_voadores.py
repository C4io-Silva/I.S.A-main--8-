"""
validar_voadores.py — regras específicas para o inimigo voador (ID 93, tucano).

Aprovadas pela direção criativa (relatório da Caverna v0.4c, §5: V1 e V3–V6). O
tucano não fica apoiado no chão, então a regra de "marcador de chão" do auditor
(superfície a ±1 coluna e até 2 linhas) não vale para ele. No lugar dela, este
validador usa a IA REAL do Tucano e o grafo da física real (pulo duplo):

  V1  patrulha real entre 2 tiles e 2·ALCANCE + 2 tiles: nem preso, nem fugindo da rota
  V3  existe posição em pé ALCANÇÁVEL a ≤ RAIO_DETECCAO do spawn: ele consegue atacar
  V4  o chão alcançável sob a rota fica a ≤ 6 tiles da altitude de cruzeiro (aparece na tela)
  V5  ≥ RAIO_DETECCAO + 1 tile de qualquer chegada e fora da área 3×3 das passagens
  V6  superfície alcançável a ±ceil(RAIO_DETECCAO / tile) colunas e até 8 linhas abaixo
  V2  (só aviso) célula do spawn livre; fração livre da faixa de voo

Reprodutível: o relógio do pygame é simulado (16 ms por quadro) e a fase da senoide
do voo é fixada em zero, então a mesma entrada dá sempre o mesmo resultado.
Esquiva sem dano e "derrotável" continuam em testar_inimigos_reais.py.

uso (na raiz do projeto):
    python ferramentas/validar_voadores.py                 # todos os tucanos dos 4 setores
    python ferramentas/validar_voadores.py caverna 147,18  # tucano hipotético na célula (col, linha)
"""
import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import ferramentas.fisica.fisica_nivel as F
import ferramentas.validacao.validar_fisica_real as V

_relogio = [0]
QUADROS_PATRULHA = 900
_grafos = {}


def _instalar_relogio(pygame):
    pygame.time.get_ticks = lambda: _relogio[0]


def _grafo(setor, d):
    """Grafo de física real a partir de todas as entradas do setor (cache por setor:
    o marcador do tucano não é terreno, então mover o tucano não muda o grafo)."""
    if setor not in _grafos:
        mk = d["marcadores"]
        sim = F.Simulador(d["grade"])
        inicios = []
        starts = ([mk["player"]] if mk.get("player") else []) + [(c, l + 1) for c, l in mk["chegadas"].values()]
        for c, l in starts:
            sim.colocar(c, l); sim.assentar(); inicios.append(sim.estado())
        gr = F.explorar(d["grade"], inicios, [p.rect_interacao for p in d["passagens"]], processos=1)
        _grafos[setor] = (sim, gr)
    return _grafos[setor]


def avaliar(setor, col, linha, d=None):
    """Avalia um tucano cujo MARCADOR está na célula (col, linha)."""
    pygame = F.iniciar_pygame(); _instalar_relogio(pygame)
    from src.nucleo import constants
    from src.mundo import setores as S
    from src.entidades.enemies.enemy import Tucano
    T = constants.TILE_SIZE
    d = d or V.montar_setor(setor)
    g, mk = d["grade"], d["marcadores"]
    sim, gr = _grafo(setor, d)
    solido = lambda c, l: 0 <= l < len(g) and 0 <= c < len(g[0]) and g[l][c] in constants.SOLID_TILES
    _relogio[0] = 10_000
    e = S.criar_inimigo({"col": col, "row": linha + 1, "classe": "Tucano", "altura": 0, "ancora": "chao"})
    e.fase_voo = _relogio[0]                       # fase fixa
    cx0, cy0 = e.rect.center
    r = {"setor": setor, "col": col, "linha": linha}
    # V1 — IA real, sem jogador
    xs = []; batidas = 0; dir_ant = e.direcao
    for _ in range(QUADROS_PATRULHA):
        _relogio[0] += 16
        obs = sim.world.obstaculos_proximos(e.rect.inflate(96, 96), margem=1)
        antes = e.rect.copy()
        e.update(obs, None)
        if e.direcao != dir_ant:
            if any(o.colliderect(antes.move(dir_ant * 6, 0)) for o in obs):
                batidas += 1
            dir_ant = e.direcao
        xs.append(e.rect.centerx)
    larg = max(xs) - min(xs)
    r.update(V1_patrulha_px=larg, V1_viradas_por_bloco=batidas,
             V1=2 * T <= larg <= 2 * Tucano.ALCANCE + 2 * T)
    # V2 (aviso)
    amp = Tucano.AMPLITUDE_VOO
    cels = [(c, l) for c in range((min(xs) - 40) // T, (max(xs) + 40) // T + 1)
            for l in range(int(cy0 - amp - 20) // T, int(cy0 + amp + 20) // T + 1)]
    livre = sum(not solido(c, l) for c, l in cels) / max(1, len(cels))
    r.update(V2_faixa_livre=round(livre, 2), V2_aviso=solido(col, linha) or livre < 0.5)
    # V3
    pes = [(s[2] + 16, s[3] + 45) for s in gr.nos.values()]          # (centro x, base) de cada posição em pé
    R = Tucano.RAIO_DETECCAO
    dist = min(math.hypot(x - cx0, (y - 22) - cy0) for x, y in pes)
    r.update(V3_dist_min_px=int(dist), V3=dist <= R)
    # V4
    sup = {(int(y) // T, int(x) // T) for x, y in pes}               # (linha do bloco pisado, col)
    linha_voo = cy0 // T
    abaixo = [l - linha_voo for (l, c) in sup if min(xs) // T <= c <= max(xs) // T and l > linha_voo]
    r.update(V4_tiles_ate_chao=(min(abaixo) - 1) if abaixo else None,
             V4=bool(abaixo) and min(abaixo) - 1 <= 6)
    # V5
    dch = min((math.hypot((c - col) * T, (l - linha) * T) for c, l in mk["chegadas"].values()), default=1e9)
    perto_passagem = any(p.rect_interacao.inflate(T, T).collidepoint(cx0, cy0) for p in d["passagens"])
    r.update(V5_dist_chegada_px=int(dch) if dch < 1e9 else None, V5=dch >= R + T and not perto_passagem)
    # V6 — regra do auditor para o ID 93, com superfícies da física real
    k = math.ceil(R / T)
    r["V6"] = any(abs(c - col) <= k and 0 < l - linha <= 8 for (l, c) in sup)
    r["falhas"] = [f"V{i}" for i in (1, 3, 4, 5, 6) if not r[f"V{i}"]]
    r["APROVADO"] = not r["falhas"]
    return r


def tucanos_do_setor(setor):
    d = V.montar_setor(setor)
    from src.entidades.enemies.enemy import Tucano
    out = []
    for dados, e in d["inimigos"]:
        if isinstance(e, Tucano):
            out.append(avaliar(setor, dados["col"], dados["row"] - 1, d))
    return out


def linha_txt(r):
    return (f"{r['setor']:8s} tucano ({r['col']},{r['linha']}): "
            f"{'APROVADO' if r['APROVADO'] else 'REPROVADO ' + ','.join(r['falhas'])} | "
            f"patrulha {r['V1_patrulha_px']} px ({r['V1_viradas_por_bloco']} batidas) | "
            f"posição alcançável a {r['V3_dist_min_px']} px | chão a {r['V4_tiles_ate_chao']} tiles | "
            f"chegada a {r['V5_dist_chegada_px']} px" + (" | AVISO faixa de voo apertada" if r["V2_aviso"] else ""))


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 2 and "," in args[1]:
        c, l = map(int, args[1].split(","))
        print(linha_txt(avaliar(args[0], c, l)))
    else:
        erros = 0
        for s in args or ["floresta", "caverna", "copas", "arena"]:
            for r in tucanos_do_setor(s):
                print(linha_txt(r)); erros += not r["APROVADO"]
        print(f"{'APROVADO' if not erros else 'REPROVADO'}: {erros} tucano(s) com erro")
        sys.exit(1 if erros else 0)
