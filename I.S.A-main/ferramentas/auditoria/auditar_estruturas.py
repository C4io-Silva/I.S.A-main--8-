"""
auditar_estruturas.py — confere cada estrutura de cenário (assets/levels/estruturas_cenario.json)
contra o terreno real do setor, com a mesma escala e o mesmo posicionamento do jogo
(src/estruturas_cenario.py: centro na coluna, base na linha, sprite × SCALE, atrás dos tiles).

Para cada estrutura:
  arquivo   imagem existe e carrega
  apoio     % dos "pés" da arte (colunas de pixels cuja parte opaca desce até os 15 % de baixo
            da imagem) que tocam ou entram em bloco sólido — abaixo de 50 % = parece FLUTUAR
  topo      (só suportes de viga) o topo encosta em bloco sólido? senão é poste solto
  visível   % dos pixels opacos que NÃO ficam escondidos atrás de blocos sólidos
  caminho   % dos pixels opacos dentro da área onde a Areninha anda (posições em pé do grafo
            de física real) — estrutura alta e estreita no caminho pode parecer obstáculo
  cobre     marcadores (portal, chegada, minério, inimigo) atrás da arte (fica atrás, mas pode
            confundir a leitura)

Não altera nada. uso (na raiz): python ferramentas/auditar_estruturas.py caverna [--json saida.json]
"""
import os, sys, json
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import ferramentas.fisica.fisica_nivel as F
import ferramentas.validacao.validar_fisica_real as V


def auditar(setor, grafo=True):
    pg = F.iniciar_pygame()
    from src.nucleo import constants
    from src.nucleo.utils import ASSETS_PATH
    T, SC, SOL = constants.TILE_SIZE, constants.SCALE, constants.SOLID_TILES
    d = V.montar_setor(setor); g = d["grade"]; H, W = len(g), len(g[0])
    sol = lambda x, y: 0 <= y < H * T and 0 <= x < W * T and g[int(y) // T][int(x) // T] in SOL
    caminho = set()
    if grafo:
        mk = d["marcadores"]; sim = F.Simulador(g); ini = []
        starts = ([mk["player"]] if mk.get("player") else []) + [(c, l + 1) for c, l in mk["chegadas"].values()]
        for c, l in starts:
            sim.colocar(c, l); sim.assentar(); ini.append(sim.estado())
        gr = F.explorar(g, ini, [p.rect_interacao for p in d["passagens"]], processos=1)
        for e in gr.nos.values():                      # células ocupadas pela Areninha em pé
            for cx in range(int(e[2]) // T, (int(e[2]) + 32) // T + 1):
                for cy in range(int(e[3]) // T, (int(e[3]) + 44) // T + 1):
                    caminho.add((cx, cy))
    marcadores = []
    for p in d["passagens"]:
        marcadores.append(("portal", p.rect_interacao))
    for c, l in d["marcadores"]["chegadas"].values():
        marcadores.append(("chegada", pg.Rect(c * T, l * T, T, T)))
    for r in d["minerios"]:
        marcadores.append(("minerio", r))
    for dados, e in d["inimigos"]:
        marcadores.append((type(e).__name__.replace("Enemy", "Cobra"), e.rect))
    est = json.loads((ASSETS_PATH / "levels" / "estruturas_cenario.json").read_text(encoding="utf-8")).get(setor, [])
    cache, out = {}, []
    for i, it in enumerate(est):
        r = {"i": i, "imagem": it["imagem"], "coluna": it["coluna"], "base": it["base"], "problemas": []}
        arq = ASSETS_PATH / "images" / "cenarios" / it["imagem"]
        if not arq.is_file():
            r["problemas"].append("ARQUIVO AUSENTE"); out.append(r); continue
        if it["imagem"] not in cache:
            img = pg.image.load(str(arq)).convert_alpha()
            img = pg.transform.scale(img, (img.get_width() * SC, img.get_height() * SC))
            cache[it["imagem"]] = pg.mask.from_surface(img)
        m = cache[it["imagem"]]; w, h = m.get_size()
        x0 = int(it["coluna"] * T - w // 2); y0 = int(it["base"] * T - h)
        r["tiles"] = f"{w / T:.1f}x{h / T:.1f}"
        r["rect_tiles"] = [round(x0 / T, 1), round(y0 / T, 1), round((x0 + w) / T, 1), round((y0 + h) / T, 1)]
        tot = m.count(); escondido = 0; no_caminho = 0
        for py in range(0, h, 2):
            for px in range(0, w, 2):
                if m.get_at((px, py)):
                    X, Y = x0 + px, y0 + py
                    if sol(X, Y): escondido += 1
                    elif (X // T, Y // T) in caminho: no_caminho += 1
        amostra = max(1, sum(1 for py in range(0, h, 2) for px in range(0, w, 2) if m.get_at((px, py))))
        r["visivel_%"] = round(100 * (1 - escondido / amostra))
        r["no_caminho_%"] = round(100 * no_caminho / amostra) if caminho else None
        # pé da arte: a linha opaca mais baixa de cada coluna de pixels
        pes, apoiados = 0, 0
        for px in range(0, w, 2):
            ys = [py for py in range(h - 1, -1, -1) if m.get_at((px, py))]
            if not ys or ys[0] < 0.85 * h: continue   # só "pés" (base da arte), não o vão de um arco
            pes += 1
            X, Y = x0 + px, y0 + ys[0]
            if sol(X, Y) or sol(X, Y + 3): apoiados += 1
        r["apoio_%"] = round(100 * apoiados / max(1, pes))
        if r["apoio_%"] < 50: r["problemas"].append(f"PARECE FLUTUAR (só {r['apoio_%']}% do pé toca o chão)")
        if "support" in it["imagem"] or "suporte" in it["imagem"]:
            tops, ok = 0, 0
            for px in range(0, w, 2):
                ys = [py for py in range(h) if m.get_at((px, py))]
                if not ys: continue
                tops += 1
                if sol(x0 + px, y0 + ys[0] - 6): ok += 1
            r["topo_apoiado_%"] = round(100 * ok / max(1, tops))
            if r["topo_apoiado_%"] < 50: r["problemas"].append(f"SUPORTE SEM VIGA/ROCHA EM CIMA (topo {r['topo_apoiado_%']}%)")
        if r["visivel_%"] < 30: r["problemas"].append(f"QUASE TODA ESCONDIDA ({r['visivel_%']}% visível)")
        if caminho and r["no_caminho_%"] >= 25 and w <= 3.5 * T:
            r["problemas"].append(f"POSTE NO CAMINHO ({r['no_caminho_%']}% da arte onde a Areninha anda): pode parecer obstáculo")
        rr = pg.Rect(x0, y0, w, h)
        r["cobre"] = sorted({nome for nome, mr in marcadores if rr.colliderect(mr)
                              and m.overlap(pg.mask.Mask((mr.w, mr.h), fill=True), (mr.x - x0, mr.y - y0))})
        out.append(r)
    return out


if __name__ == "__main__":
    args = []
    for i, a in enumerate(sys.argv[1:], 1):
        if a.startswith("--") or (i > 1 and sys.argv[i - 1] == "--json"):
            continue
        args.append(a)
    setores = args or ["floresta", "caverna", "copas", "arena"]
    todos = {}
    for s in setores:
        res = auditar(s, grafo="--sem-grafo" not in sys.argv)
        todos[s] = res
        print(f"== {s.upper()}: {len(res)} estrutura(s)")
        for r in res:
            print(f"  [{r['i']:2d}] {r['imagem']:34s} col {r['coluna']!s:>5} base {r['base']:>4} "
                  f"({r.get('tiles', '?')} tiles) apoio {r.get('apoio_%', '-'):>3}% vis {r.get('visivel_%', '-'):>3}% "
                  f"caminho {r.get('no_caminho_%', '-')}%" + (f" topo {r['topo_apoiado_%']}%" if "topo_apoiado_%" in r else "")
                  + (f" | atrás: {','.join(r['cobre'])}" if r.get("cobre") else ""))
            for p in r["problemas"]:
                print("        ->", p)
    if "--json" in sys.argv:
        json.dump(todos, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1, ensure_ascii=False)
