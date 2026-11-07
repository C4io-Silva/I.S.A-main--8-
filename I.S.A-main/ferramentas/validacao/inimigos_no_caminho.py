"""
inimigos_no_caminho.py — quais inimigos ficam no caminho obrigatório?

Remove do grafo de física real (pulo duplo) toda trajetória que passa pela
zona de perigo de um inimigo (faixa de patrulha da cobra/tucano, coluna de
gatilho da aranha) e confere se cada passagem do setor continua alcançável a
partir da primeira entrada. "OBRIGATÓRIO" = não dá para chegar à passagem sem
cruzar aquele inimigo (o dano só se evita com tempo certo ou derrotando-o).

uso (na raiz do projeto): python ferramentas/inimigos_no_caminho.py caverna
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import ferramentas.fisica.fisica_nivel as F
import ferramentas.validacao.validar_fisica_real as V

if __name__ == "__main__":
    pg = F.iniciar_pygame()
    from src.nucleo import constants
    T = constants.TILE_SIZE
    setor = sys.argv[1] if len(sys.argv) > 1 else "caverna"
    d = V.montar_setor(setor)
    g = d["grade"]
    sim = F.Simulador(g)
    if d["marcadores"]["player"]:
        c, l = d["marcadores"]["player"]
        sim.colocar(c, l)
    else:
        c, l = sorted(d["marcadores"]["chegadas"].items())[0][1]
        sim.colocar(c, l + 1)
    sim.assentar()
    raiz = F.chave(sim.estado())       # antes de qualquer simulação mexer no estado
    saidas = [p.rect_interacao for p in d["passagens"]]
    gr = F.explorar(g, [sim.estado()], saidas, processos=1)
    zonas = []
    for dados, e in d["inimigos"]:
        nome = type(e).__name__.replace("Enemy", "Cobra")
        if nome == "Aranha":
            # A descida para no primeiro bloco sólido sob a aranha (na coluna dela ou
            # nas vizinhas que a largura dela toca): abaixo disso ela não alcança.
            altura = int(e.ALCANCE_VERTICAL + e.rect.h)
            c0, c1 = int(e.ancora_x - e.rect.w / 2) // T, int(e.ancora_x + e.rect.w / 2 - 1) // T
            for y in range(int(e.altura_inicial + e.rect.h) // T, len(g)):
                if any(0 <= c < len(g[0]) and g[y][c] in constants.SOLID_TILES for c in range(c0, c1 + 1)):
                    altura = min(altura, y * T - int(e.altura_inicial))
                    break
            z = pg.Rect(int(e.ancora_x - e.TOLERANCIA_X - 17), int(e.altura_inicial),
                        int(2 * e.TOLERANCIA_X + 34), altura)
        elif nome == "Cobra":
            z = pg.Rect(int(e.rect.x - e.ALCANCE), e.rect.y - 4, int(e.rect.w + 2 * e.ALCANCE), e.rect.h + 8)
        else:
            z = pg.Rect(int(e.rect.x - e.ALCANCE), int(e.rect.y - e.AMPLITUDE_VOO),
                        int(e.rect.w + 2 * e.ALCANCE), int(e.rect.h + 2 * e.AMPLITUDE_VOO))
        zonas.append((nome, dados["col"], z))
    # quais arestas atravessam cada zona
    arestas = []
    for k, dests in gr.arestas.items():
        for k2, mis in dests.items():
            arestas.append((k, k2, mis[0]))
    passa = {}
    for k, k2, mi in arestas:
        _, _, pts = sim.simular(gr.nos[k], F.MACROS[mi], trajeto=True)
        hit = set()
        for x, y in pts or []:
            r = pg.Rect(x - 16, y - 22, 33, 45)
            for i, (_, _, z) in enumerate(zonas):
                if z.colliderect(r):
                    hit.add(i)
        passa[(k, k2)] = hit
    def alcanca(bloq, j):
        alvo = {k for k, t in gr.toques_no.items() if j in t}
        vis, pilha = {raiz}, [raiz]
        while pilha:
            a = pilha.pop()
            for b in gr.arestas.get(a, {}):
                if b not in vis and not (passa[(a, b)] & bloq):
                    vis.add(b); pilha.append(b)
        return bool(vis & alvo)
    for j, p in enumerate(d["passagens"]):
        print(f"== passagem para '{p.destino['setor']}' (col {p.coluna}): alcancavel = {alcanca(set(), j)}")
        for i, (nome, col, z) in enumerate(zonas):
            print(f"   {nome} col {col}: " + ("OBRIGATORIO (todo caminho cruza a zona)" if not alcanca({i}, j)
                                             else "evitavel (existe caminho que nao cruza a zona)"))
        print("   todos evitados ao mesmo tempo:", alcanca(set(range(len(zonas))), j))
