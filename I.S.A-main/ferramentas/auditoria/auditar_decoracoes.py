"""
auditar_decoracoes.py — procura enfeites da camada de decoração (assets/levels/decoracoes/*_decor.csv,
IDs 100..123, 1 tile cada, sem colisão) que ficam SOLTOS no ar.

Cada ID tem um tipo de apoio, deduzido do desenho (borda opaca do sprite) e do que ele representa:
  chao      precisa de bloco embaixo (flor, samambaia, cristal, cogumelo, arbusto, placa, ...)
  pendurado precisa de bloco em cima (cipó, liana, lanterna, estalactite, ramos)
  parede    precisa de bloco ao lado, em cima ou embaixo (tocha, runas, bandeira)
  qualquer  precisa encostar em algo (copa, folhagem densa, tronco, corda)
"Bloco" é qualquer tile desenhado do terreno (sólido ou só visual), menos marcadores.
Correntes contam: um cipó pendurado em outro cipó que encosta no teto está apoiado.

Também lista enfeites na MESMA célula de minério, portal, chegada ou inimigo (não deveria haver).
Não altera nada. uso (na raiz): python ferramentas/auditar_decoracoes.py [setor ...] [--json saida.json]
"""
import csv, json, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RAIZ))
from src.nucleo import constants  # noqa: E402
from src.mundo.decoracoes_offline import ARTE  # noqa: E402

CHAO = {100, 101, 102, 103, 110, 112, 114, 115, 117, 119, 121, 122}
PENDURADO = {105, 109, 111, 118, 120}
PAREDE = {104, 108, 113}
QUALQUER = {106, 107, 116, 123}
assert CHAO | PENDURADO | PAREDE | QUALQUER == set(ARTE), sorted(set(ARTE) - (CHAO | PENDURADO | PAREDE | QUALQUER))

MARC = set(getattr(constants, "TILES_MARCADORES", set())) | {90, 91, 92, 93, 94, 95, 96}
NOMES_MARC = {91: "minerio", 92: "cobra", 93: "tucano", 94: "aranha", 95: "gorila", 96: "maca", 90: "spawn"}


def ler(p):
    with open(p, encoding="utf-8-sig", newline="") as f:
        return [[int(v) for v in r] for r in csv.reader(f) if r]


def auditar(setor):
    g = ler(RAIZ / "assets" / "levels" / "setores" / f"{setor}.csv")
    d = ler(RAIZ / "assets" / "levels" / "decoracoes" / f"{setor}_decor.csv")
    H, W = len(g), len(g[0])
    bloco = lambda x, y: 0 <= y < H and 0 <= x < W and g[y][x] >= 0 and g[y][x] not in MARC
    deco = lambda x, y: 0 <= y < H and 0 <= x < W and d[y][x] >= 0
    celulas = [(x, y) for y in range(H) for x in range(W) if d[y][x] >= 0]
    apoiado = set()
    viz = {"chao": [(0, 1)], "pendurado": [(0, -1)], "parede": [(-1, 0), (1, 0), (0, -1), (0, 1)],
           "qualquer": [(-1, 0), (1, 0), (0, -1), (0, 1)]}

    def tipo(v):
        return "chao" if v in CHAO else "pendurado" if v in PENDURADO else "parede" if v in PAREDE else "qualquer"
    mudou = True
    while mudou:
        mudou = False
        for x, y in celulas:
            if (x, y) in apoiado:
                continue
            for dx, dy in viz[tipo(d[y][x])]:
                if bloco(x + dx, y + dy) or (x + dx, y + dy) in apoiado:
                    apoiado.add((x, y)); mudou = True; break
    soltos = []
    for x, y in celulas:
        if (x, y) not in apoiado:
            v = d[y][x]
            # o que há em volta, para ajudar a decidir a correção
            abaixo = next((yy for yy in range(y + 1, H) if bloco(x, yy)), None)
            acima = next((yy for yy in range(y - 1, -1, -1) if bloco(x, yy)), None)
            soltos.append({"col": x, "linha": y, "id": v, "arte": ARTE[v], "tipo": tipo(v),
                           "chao_mais_proximo_abaixo": abaixo, "bloco_mais_proximo_acima": acima})
    sobre_marcador = [{"col": x, "linha": y, "id": d[y][x], "marcador": NOMES_MARC.get(g[y][x], g[y][x])}
                      for x, y in celulas if g[y][x] in MARC]
    return {"total": len(celulas), "soltos": soltos, "sobre_marcador": sobre_marcador}


if __name__ == "__main__":
    args = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[i - 1] != "--json"]
    setores = args or ["floresta", "caverna", "copas", "arena"]
    todos = {}
    for s in setores:
        r = todos[s] = auditar(s)
        print(f"== {s.upper()}: {r['total']} enfeite(s), {len(r['soltos'])} solto(s), {len(r['sobre_marcador'])} sobre marcador")
        for e in r["soltos"]:
            print(f"   SOLTO ({e['col']},{e['linha']}) id {e['id']} {e['arte']:28s} [{e['tipo']}]"
                  f" chão abaixo: linha {e['chao_mais_proximo_abaixo']} | bloco acima: linha {e['bloco_mais_proximo_acima']}")
        for e in r["sobre_marcador"]:
            print(f"   SOBRE MARCADOR ({e['col']},{e['linha']}) id {e['id']} -> {e['marcador']}")
    if "--json" in sys.argv:
        json.dump(todos, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1, ensure_ascii=False)
