"""
auditar_ritmo_minerios.py — ritmo das perguntas: quanto se anda entre minérios.

Tocar num minério abre o quiz na hora (Partida.verificar_coletas). Se dois
minérios estão perto demais NO PERCURSO, o jogador sai de uma pergunta e cai
em outra sem tempo de explorar. Distância em células engana: um minério 3
colunas ao lado pode estar 6 tiles acima (subida longa) e outro, 10 colunas à
frente, a 3 s de caminhada reta.

Por isso a medida aqui é TEMPO DE PERCURSO com a física real: o grafo de
posições em pé de ferramentas/validar_fisica_real.py (cada aresta = uma
macro-ação simulada com Character.move, custo em quadros a 60 FPS, sem a
penalidade artificial por pulo das rotas "naturais"). Para cada par de
minérios, o menor número de quadros saindo do ponto em que se toca um até
tocar o outro.

Medidas por setor
  ordem    minérios ordenados pelo tempo desde a entrada principal (spawn ou
           primeira chegada) — a ordem em que um jogador os encontra
  intervalo tempo do minério anterior (ou da entrada) até o seguinte
  vizinho  menor tempo até QUALQUER outro minério, nos dois sentidos
  janela   quantos minérios o jogador encontra nos PRÓXIMOS 15 s de percurso
           (tempo acumulado ao longo da ordem; os que ficaram para trás não contam)

Critérios (metas de design desta auditoria, não regras do motor)
  ERRO   vizinho < 2,0 s  — pergunta colada na outra
  AVISO  vizinho < 3,5 s, ou mais de 4 minérios numa janela de 15 s
  AVISO  minério a menos de 3 tiles do nascimento de um inimigo
  AVISO  decoração na célula do minério ou ao lado (leitura do item)

uso:  python ferramentas/auditar_ritmo_minerios.py [setores...] [--processos N] [--json saida.json]
Sai com código 1 se houver ERRO.
"""
import argparse
import heapq
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import ferramentas.fisica.fisica_nivel as F  # noqa: E402
import ferramentas.validacao.validar_fisica_real as V  # noqa: E402

FPS = 60
ERRO_S, AVISO_S = 2.0, 3.5
JANELA_S, JANELA_MAX = 15.0, 4
DIST_INIMIGO_TILES = 3


def _quadros(custo, mi):
    """Custo do grafo sem a penalidade de pulo: quadros reais de jogo."""
    if mi is None:
        return 0
    return custo - F.PENALIDADE_PULO * len(F.MACROS[mi][2])


def _dijkstra(g, fontes):
    dist = dict(fontes)
    fila = [(d, k) for k, d in fontes.items()]
    heapq.heapify(fila)
    while fila:
        d, k = heapq.heappop(fila)
        if d > dist.get(k, 1e18):
            continue
        for k2 in g.arestas.get(k, {}):
            c, mi = g.custo[(k, k2)]
            nd = d + _quadros(c, mi)
            if nd < dist.get(k2, 1e18):
                dist[k2] = nd
                heapq.heappush(fila, (nd, k2))
    return dist


def auditar(nome, processos=1):
    from src.nucleo import constants
    rel, ctx = V.analisar_setor(nome, processos=processos, log=lambda *a: None)
    g, d = ctx["grafo"], ctx["dados"]
    T = d["T"]
    minerios = d["minerios"]
    n = len(minerios)
    out = {"setor": nome, "minerios": n, "erros": [], "avisos": [], "lista": []}
    if n == 0 or g is None:
        return out

    # Onde o jogador "está" ao pegar cada minério: posições em pé a até 1,5 tile
    # na horizontal e 2 na vertical do minério. Usar todo nó cuja macro-ação
    # passa pelo minério seria errado: uma caminhada longa que termina nele
    # começaria longe e faria minérios distantes parecerem colados.
    perto = {i: {} for i in range(n)}
    for k, e in g.nos.items():
        cx, base = e[2] + 15, e[3] + 45     # rect 30x45 da Areninha (x, y)
        for i, m in enumerate(minerios):
            if abs(cx - m.centerx) <= 1.5 * T and abs(base - m.bottom) <= 2 * T:
                # o resto do caminho até o minério, andando na velocidade real
                perto[i][k] = abs(cx - m.centerx) / constants.PLAYER_SPEED
    for (k, a), (c, mi) in g.toque_custo.items():   # pego só no pulo, sem chão perto
        if a < n and not perto[a]:
            q = _quadros(c, mi)
            if q < 60:
                perto[a][k] = min(q, perto[a].get(k, 1e18))
    toques = perto

    def tempo_de(fontes):
        dist = _dijkstra(g, fontes)
        return [min((dist[k] + q for k, q in toques[j].items() if k in dist), default=None)
                for j in range(n)]

    entrada = next(iter(ctx["entradas"].values()))
    desde_entrada = tempo_de({F.chave(entrada): 0})
    matriz = [tempo_de(dict(toques[i])) for i in range(n)]

    cel = [(m.centerx // T, m.bottom // T - 1) for m in minerios]
    ordem = sorted(range(n), key=lambda i: (desde_entrada[i] is None, desde_entrada[i] or 0))
    grade_dec = None
    try:
        from src.mundo.decoracoes import DecoracaoSetor  # noqa: F401
        import csv
        caminho = Path(constants.__file__).resolve().parents[2] / "assets/levels/decoracoes" / f"{nome}_decor.csv"
        with caminho.open(encoding="utf-8-sig", newline="") as fp:
            grade_dec = [[int(v) for v in row] for row in csv.reader(fp) if row]
    except (OSError, ValueError):
        pass

    # tempo acumulado de cada minério ao longo do percurso (ordem de encontro)
    acum, t_acc, ant = {}, 0, None
    for i in ordem:
        passo = desde_entrada[i] if ant is None else matriz[ant][i]
        t_acc += passo if passo is not None else 0
        acum[i] = t_acc
        ant = i

    anterior = None
    for pos, i in enumerate(ordem):
        if anterior is None:
            intervalo = desde_entrada[i]
        else:
            intervalo = matriz[anterior][i]
        vizinhos = [min(x for x in (matriz[i][j], matriz[j][i]) if x is not None)
                    for j in range(n) if j != i and (matriz[i][j] is not None or matriz[j][i] is not None)]
        viz = min(vizinhos) if vizinhos else None
        janela = sum(1 for j in ordem if acum[i] <= acum[j] < acum[i] + JANELA_S * FPS)
        c, r = cel[i]
        item = {"ordem": pos + 1, "col": c, "linha": r,
                "intervalo_s": None if intervalo is None else round(intervalo / FPS, 1),
                "vizinho_s": None if viz is None else round(viz / FPS, 1), "janela15s": janela}
        out["lista"].append(item)
        rotulo = f"minerio col {c} linha {r}"
        if viz is not None and viz < ERRO_S * FPS:
            out["erros"].append(f"{rotulo}: outro minerio a {viz / FPS:.1f} s de percurso (min {ERRO_S} s)")
        elif viz is not None and viz < AVISO_S * FPS:
            out["avisos"].append(f"{rotulo}: outro minerio a {viz / FPS:.1f} s de percurso (meta {AVISO_S} s)")
        if janela > JANELA_MAX:
            out["avisos"].append(f"{rotulo}: {janela} minerios em {JANELA_S:.0f} s de percurso (meta <= {JANELA_MAX})")
        for dados_e, e in d["inimigos"]:
            if abs(dados_e["col"] - c) < DIST_INIMIGO_TILES and abs(e.rect.bottom // T - 1 - r) <= 2:
                out["avisos"].append(f"{rotulo}: {type(e).__name__.replace('Enemy', 'Cobra')} "
                                     f"nasce a {abs(dados_e['col'] - c)} coluna(s)")
        if grade_dec is not None:
            vizinhas = [(c + dx, r) for dx in (-1, 0, 1)]
            if any(0 <= x < len(grade_dec[0]) and grade_dec[y][x] != -1 for x, y in vizinhas):
                out["avisos"].append(f"{rotulo}: decoracao na celula ou ao lado (leitura do item)")
        anterior = i

    ints = [x["intervalo_s"] for x in out["lista"][1:] if x["intervalo_s"] is not None]
    vzs = [x["vizinho_s"] for x in out["lista"] if x["vizinho_s"] is not None]
    if ints:
        out["intervalo_mediano_s"] = round(statistics.median(ints), 1)
        out["intervalo_min_s"] = min(ints)
        out["intervalo_max_s"] = max(ints)
    if vzs:
        out["vizinho_min_s"] = min(vzs)
        out["vizinho_mediano_s"] = round(statistics.median(vzs), 1)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("setores", nargs="*")
    ap.add_argument("--processos", type=int, default=1)
    ap.add_argument("--json")
    ap.add_argument("--lista", action="store_true", help="imprime cada minerio na ordem do percurso")
    a = ap.parse_args(argv)
    F.iniciar_pygame()
    from src.nucleo import constants
    nomes = a.setores or [n for n in constants.SETORES if n != "arena"]
    total_erros = 0
    resultados = []
    for nome in nomes:
        r = auditar(nome, a.processos)
        resultados.append(r)
        print(f"\n== {nome.upper()} — {r['minerios']} minerios ==")
        if r["minerios"]:
            print(f"  intervalo no percurso: mediana {r.get('intervalo_mediano_s')} s, "
                  f"min {r.get('intervalo_min_s')} s, max {r.get('intervalo_max_s')} s")
            print(f"  vizinho mais proximo: min {r.get('vizinho_min_s')} s, mediana {r.get('vizinho_mediano_s')} s")
        if a.lista:
            for x in r["lista"]:
                print(f"   #{x['ordem']:2d} col {x['col']:3d} lin {x['linha']:2d} | intervalo {x['intervalo_s']} s"
                      f" | vizinho {x['vizinho_s']} s | janela15s {x['janela15s']}")
        for e in r["erros"]:
            print("  ERRO ", e)
        for w in r["avisos"]:
            print("  AVISO", w)
        if not r["erros"] and not r["avisos"]:
            print("  OK")
        total_erros += len(r["erros"])
    if a.json:
        Path(a.json).write_text(json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{'APROVADO' if not total_erros else 'REPROVADO'}: {total_erros} erro(s)")
    return 1 if total_erros else 0


if __name__ == "__main__":
    sys.exit(main())
