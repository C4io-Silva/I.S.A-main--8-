"""
validar_fisica_real.py — valida os mapas com a FÍSICA REAL da Areninha.

Diferente de ferramentas/auditar_level_design.py e src/validacao_mapa.py
(aproximações geométricas: "degrau <= 2", "vão <= 2"), aqui cada salto é
simulado quadro a quadro com o Character.move do jogo, considerando o pulo
duplo (ver ferramentas/fisica_nivel.py). Os retângulos de minérios, maçãs,
inimigos, Gorila e passagens são criados com as MESMAS funções do jogo
(src/setores.py, src/passagens.py).

uso (na raiz do projeto):
    python ferramentas/validar_fisica_real.py                 # 4 setores
    python ferramentas/validar_fisica_real.py copas arena     # só alguns
    python ferramentas/validar_fisica_real.py --pulos 1       # controle: pulo simples
    python ferramentas/validar_fisica_real.py --dificuldade   # + o que exige pulo duplo
    python ferramentas/validar_fisica_real.py --json saida.json --processos 4

Sai com código 1 se houver algum ERRO. AVISOs não reprovam.

O que é verificado, por setor
-----------------------------
ENTRADAS (spawn do jogador e cada marcador de chegada 40-45)
  ERRO  nasce dentro de bloco sólido / cai para fora do mapa
  ERRO  chega já dentro da área de uma passagem (teleporte em sequência)
  ERRO  chega dentro da área de luta do Gorila (a luta começaria sozinha)
  AVISO cai mais de 3 tiles ao chegar; chega encostando num minério;
        inimigo nasce a menos de 4 tiles da chegada
PASSAGENS (30-35)
  ERRO  destino/chegada inexistente ou repetida; setor sem caminho de volta;
        setor inalcançável a partir da floresta; saída da arena dentro da
        área de luta; passagem inalcançável a partir de alguma entrada
  AVISO passagem a menos de 4 colunas da chegada do mesmo setor
ALCANCE (física real, pulo duplo)
  ERRO  minério ou maçã inalcançável a partir de alguma entrada
  ERRO  ponto onde se pode ficar em pé e do qual nenhuma passagem é alcançável
        (o jogador ficaria preso; só sairia morrendo)
  ERRO  a borda da área de luta do Gorila é inalcançável
  AVISO superfície (bloco com espaço em cima) onde nunca se pisa
  AVISO sem caminho de volta de uma passagem até uma entrada (ERRO com --exigir-volta);
        trechos de mão única (desce e não sobe mais)
COLISÃO DE ENTIDADES
  ERRO  minério, maçã, inimigo ou Gorila nascendo dentro de bloco sólido;
        cobra sem chão embaixo; aranha sem teto em cima
  AVISO voo de vaivém do tucano atravessando blocos; aranha que nunca ataca
        (nenhum lugar de pé até 240 px abaixo dela)
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import ferramentas.fisica.fisica_nivel as F  # noqa: E402

DIST_INIMIGO_SEGURA_TILES = 4
QUEDA_AVISO_TILES = 3


class Relatorio:
    def __init__(self, setor):
        self.setor = setor
        self.erros = []
        self.avisos = []
        self.info = {}

    def erro(self, msg):
        self.erros.append(msg)

    def aviso(self, msg):
        self.avisos.append(msg)


def _cel(rect, T):
    return [rect.centerx // T, (rect.bottom - 1) // T]


def montar_setor(nome):
    """Lê o CSV e cria as entidades com as funções do jogo (sem iniciar a partida)."""
    pygame = F.iniciar_pygame()
    from src.nucleo import constants
    from src.mundo import setores as S
    from src.mundo.passagens import GerenciadorPassagens
    grade, mk = F.ler_setor(nome)
    T = constants.TILE_SIZE
    d = {
        "nome": nome, "grade": grade, "marcadores": mk, "T": T,
        "minerios": [S.criar_minerio(m).rect.copy() for m in mk["minerios"]],
        "curas": [S.criar_cura(c).rect.copy() for c in mk["curas"]],
        "passagens": GerenciadorPassagens(mk["passagens"], grade).itens,
        "inimigos": [],
        "area_boss": S.montar_area_boss(nome, mk["area_boss"]),
        "boss": None,
    }
    for dados in mk["inimigos"]:
        e = S.criar_inimigo(dados)
        if e is not None:
            d["inimigos"].append((dados, e))
    if d["area_boss"]:
        from src.entidades.enemies import CLASSE_BOSS
        col, linha = d["area_boss"]["marcador"]
        molde = CLASSE_BOSS(x=0, y=0)
        d["boss"] = pygame.Rect(col * T + (T - molde.rect.width) // 2,
                                (linha + 1) * T - molde.rect.height,
                                molde.rect.width, molde.rect.height)
    return d


def verificar_ligacoes(setores_dados):
    """Consistência das passagens entre TODOS os setores do jogo."""
    from src.nucleo import constants
    erros, avisos = [], []
    chegadas_por_setor = {n: dict(d["marcadores"]["chegadas"]) for n, d in setores_dados.items()}
    usados = {}
    for n, d in setores_dados.items():
        for p in d["passagens"]:
            dest, cheg = p.destino["setor"], p.destino["chegada"]
            usados.setdefault(p.destino["id_tile"], []).append(n)
            if dest not in chegadas_por_setor:
                erros.append(f"{n}: passagem {p.destino['id_tile']} (col {p.coluna}, linha {p.linha}) "
                             f"leva ao setor '{dest}', que nao foi carregado")
            elif cheg not in chegadas_por_setor[dest]:
                erros.append(f"{n}: passagem {p.destino['id_tile']} leva a chegada {cheg} em '{dest}', "
                             f"mas '{dest}.csv' nao tem esse marcador")
    for id_tile, onde in usados.items():
        if len(onde) > 1:
            erros.append(f"passagem {id_tile} aparece {len(onde)} vezes ({', '.join(onde)})")
    for id_tile in constants.PASSAGENS_CSV:
        if id_tile not in usados and set(setores_dados) == set(constants.SETORES):
            erros.append(f"passagem {id_tile} ({constants.PASSAGENS_CSV[id_tile]['tipo']}) "
                         f"nao existe em nenhum CSV")
    # grafo de setores
    if set(setores_dados) == set(constants.SETORES):
        viz = {n: {p.destino["setor"] for p in d["passagens"]} for n, d in setores_dados.items()}
        def fecho(inicio, arestas):
            vis, pilha = {inicio}, [inicio]
            while pilha:
                a = pilha.pop()
                for b in arestas.get(a, ()):
                    if b not in vis:
                        vis.add(b)
                        pilha.append(b)
            return vis
        alc = fecho(constants.SETOR_INICIAL, viz)
        for n in setores_dados:
            if n not in alc:
                erros.append(f"setor '{n}' nao e alcancavel a partir de '{constants.SETOR_INICIAL}'")
            elif constants.SETOR_INICIAL not in fecho(n, viz):
                erros.append(f"setor '{n}' nao tem caminho de volta para '{constants.SETOR_INICIAL}'")
    return erros, avisos


def analisar_setor(nome, pulos=2, processos=1, dificuldade=False, dados=None, log=print,
                   exigir_volta=False):
    """Valida um setor. Devolve (Relatorio, contexto) — o contexto serve aos mapas técnicos."""
    pygame = F.iniciar_pygame()
    from src.nucleo import constants
    d = dados or montar_setor(nome)
    T = d["T"]
    grade = d["grade"]
    rel = Relatorio(nome)
    sim = F.Simulador(grade, pulos)
    S = constants.SOLID_TILES
    area = d["area_boss"]["rect"] if d["area_boss"] else None

    def bloco_em(rect):
        return [(r.x // T, r.y // T) for r in sim.world.obstaculos_proximos(rect, margem=1)
                if r.colliderect(rect)]

    # ── colisão das entidades ────────────────────────────────────────────────
    for i, r in enumerate(d["minerios"]):
        if bloco_em(r):
            rel.erro(f"minerio #{i} em {_cel(r, T)} nasce dentro de bloco solido {bloco_em(r)}")
    for i, r in enumerate(d["curas"]):
        if bloco_em(r):
            rel.erro(f"maca #{i} em {_cel(r, T)} nasce dentro de bloco solido")
    for dados_e, e in d["inimigos"]:
        r = e.rect
        nome_e = type(e).__name__.replace("Enemy", "Cobra")
        cel = [dados_e["col"], dados_e["row"]]
        if bloco_em(r):
            extra = (" — a descida e abortada no 1o quadro (Aranha._colidiu_vertical), ela nunca ataca"
                     if nome_e == "Aranha" else "")
            rel.erro(f"{nome_e} (marcador col {cel[0]}) nasce sobrepondo bloco solido "
                     f"{bloco_em(r)}{extra}")
        if nome_e == "Cobra":
            sensor = pygame.Rect(r.left, r.bottom, r.width, 2)
            if not bloco_em(sensor):
                rel.erro(f"Cobra (col {cel[0]}) sem chao embaixo: cairia ao nascer")
        elif nome_e == "Aranha":
            l_teto = dados_e["row"]
            if not (0 <= l_teto < len(grade)) or grade[l_teto][dados_e["col"]] not in S:
                rel.erro(f"Aranha (col {cel[0]}) sem bloco de teto acima do marcador")
            # descida: o retângulo dela (51 px) cobre 3 colunas; um bloco numa coluna
            # vizinha para a descida antes do chão sob o fio (Aranha._colidiu_vertical)
            c0, c1 = r.left // T, (r.right - 1) // T
            col_fio = int(e.ancora_x) // T
            primeiro = next(((l, [c for c in range(c0, c1 + 1) if grade[l][c] in S])
                             for l in range(r.bottom // T + (1 if r.bottom % T == 0 else 0), len(grade))
                             if any(grade[l][c] in S for c in range(c0, c1 + 1))), None)
            chao_fio = next((l for l in range(r.bottom // T, len(grade)) if grade[l][col_fio] in S), None)
            if primeiro and chao_fio is not None and primeiro[0] < chao_fio:
                livre = primeiro[0] * T - r.bottom
                rel.aviso(f"Aranha (col {cel[0]}): a descida para a {livre} px, no bloco "
                          f"{[(c, primeiro[0]) for c in primeiro[1]]} (coluna vizinha), "
                          f"antes do chao sob o fio (linha {chao_fio})")
        elif nome_e == "Tucano":
            faixa = pygame.Rect(int(r.x - e.ALCANCE), int(r.y - e.AMPLITUDE_VOO),
                                int(r.width + 2 * e.ALCANCE), int(r.height + 2 * e.AMPLITUDE_VOO))
            n_blocos = sum(1 for linha in sim.world._solidos for b in linha
                           if b is not None and b.colliderect(faixa))
            if n_blocos:
                rel.aviso(f"Tucano (col {cel[0]}): o vaivem ({faixa.width // T}x{faixa.height // T} tiles) "
                          f"cruza {n_blocos} bloco(s) solido(s) — ele inverte ao bater")
    if d["boss"] is not None and bloco_em(d["boss"]):
        rel.erro(f"Gorila nasce dentro de bloco solido {bloco_em(d['boss'])}")

    # ── passagens ────────────────────────────────────────────────────────────
    zonas = [p.rect_interacao for p in d["passagens"]]
    if area is not None:
        for p in d["passagens"]:
            if p.rect_interacao.colliderect(area) or p.rect_interacao.right > area.left:
                rel.erro(f"saida da arena (col {p.coluna}) dentro/depois da borda da area de luta "
                         f"(colunas {area.left // T}-{area.right // T - 1}): andar ate ela ativa o Gorila")

    # ── entradas ─────────────────────────────────────────────────────────────
    entradas = {}
    pontos = []
    if d["marcadores"]["player"] is not None:
        pontos.append(("spawn", d["marcadores"]["player"][0], d["marcadores"]["player"][1]))
    for id_c, (col, linha) in sorted(d["marcadores"]["chegadas"].items()):
        pontos.append((f"chegada {id_c}", col, linha + 1))
    for rotulo, col, linha_base in pontos:
        sim.colocar(col, linha_base)
        if sim.dentro_de_bloco():
            rel.erro(f"{rotulo} (col {col}): a Areninha aparece dentro de bloco solido")
        ok, quadros, queda = sim.assentar()
        if not ok:
            rel.erro(f"{rotulo} (col {col}): nao ha chao embaixo, cai para fora do mapa")
            continue
        r = sim.p.rect.copy()
        if queda is not None and queda > QUEDA_AVISO_TILES * T:
            rel.aviso(f"{rotulo} (col {col}): cai {queda / T:.1f} tiles ao aparecer")
        for p in d["passagens"]:
            if p.rect_interacao.colliderect(r):
                rel.erro(f"{rotulo} (col {col}): ja chega dentro da area da passagem para "
                         f"'{p.destino['setor']}' (col {p.coluna}) — teleporte em sequencia")
            elif abs(p.coluna - col) < 4 and abs(p.linha - (linha_base - 1)) <= 2:
                rel.aviso(f"{rotulo} (col {col}): passagem para '{p.destino['setor']}' a "
                          f"{abs(p.coluna - col)} coluna(s) (regra do auditor: >= 4)")
        if area is not None and r.left >= area.left:
            rel.erro(f"{rotulo} (col {col}): chega dentro da area de luta — o Gorila ativa na hora")
        for i, m in enumerate(d["minerios"]):
            if m.colliderect(r):
                rel.aviso(f"{rotulo} (col {col}): chega encostando no minerio #{i} (abre pergunta na hora)")
        for dados_e, e in d["inimigos"]:
            dist = abs(e.rect.centerx - r.centerx) / T
            if dist < DIST_INIMIGO_SEGURA_TILES and abs(e.rect.centery - r.centery) < 4 * T:
                rel.aviso(f"{rotulo} (col {col}): {type(e).__name__.replace('Enemy', 'Cobra')} "
                          f"nasce a {dist:.1f} tiles")
        entradas[rotulo] = sim.estado()

    # ── alcance com a física real ────────────────────────────────────────────
    alvos = list(d["minerios"]) + list(d["curas"]) + zonas
    n_m, n_c = len(d["minerios"]), len(d["curas"])
    idx_pass = set(range(n_m + n_c, len(alvos)))
    if area is not None:
        alvos.append(pygame.Rect(area.left, 0, T, sim.altura))   # borda da luta
    rel.info["entradas"] = {k: [v[2], v[3]] for k, v in entradas.items()}
    grafo = None
    alcance_por_entrada = {}
    t0 = time.time()
    if entradas:
        primeira = next(iter(entradas.values()))
        grafo = F.explorar(grade, [primeira], alvos, pulos=pulos, processos=processos)
        for rotulo, e in entradas.items():
            k = F.chave(e)
            if k not in grafo.nos:
                extra = F.explorar(grade, [e], alvos, pulos=pulos, processos=processos)
                alcance_por_entrada[rotulo] = (set(extra.nos), extra.alcancados())
                continue
            vis, pilha = {k}, [k]
            while pilha:
                a = pilha.pop()
                for b in grafo.arestas.get(a, {}):
                    if b not in vis:
                        vis.add(b)
                        pilha.append(b)
            toc = set()
            for a in vis:
                toc |= grafo.toques_no.get(a, set())
            alcance_por_entrada[rotulo] = (vis, toc)
    rel.info["segundos_busca"] = round(time.time() - t0, 1)
    rel.info["nos_em_pe"] = len(grafo.nos) if grafo else 0

    for rotulo, (vis, toc) in alcance_por_entrada.items():
        for i, m in enumerate(d["minerios"]):
            if i not in toc:
                rel.erro(f"minerio #{i} em {_cel(m, T)} inalcancavel a partir de '{rotulo}'")
        for i, c in enumerate(d["curas"]):
            if n_m + i not in toc:
                rel.erro(f"maca #{i} em {_cel(c, T)} inalcancavel a partir de '{rotulo}'")
        for j, p in enumerate(d["passagens"]):
            if n_m + n_c + j not in toc:
                rel.erro(f"passagem para '{p.destino['setor']}' (col {p.coluna}) inalcancavel "
                         f"a partir de '{rotulo}'")
        if area is not None and len(alvos) - 1 not in toc:
            rel.erro(f"a area de luta do Gorila e inalcancavel a partir de '{rotulo}'")

    presos = []
    if grafo is not None and zonas:
        presos = F.sem_saida(grafo, idx_pass)
        if presos:
            h = sim.p.rect.height
            amostra = [[(k[0] * F.QUANT + sim.p.rect.width // 2) // T, (k[1] + h) // T] for k in presos[:12]]
            rel.erro(f"{len(presos)} ponto(s) em pe sem caminho para nenhuma passagem "
                     f"(jogador preso). Ex. (col, linha da base): {amostra}")
    # volta: de cada passagem dá para voltar até cada entrada? e trechos de mão única
    if grafo is not None and zonas:
        h, w = sim.p.rect.height, sim.p.rect.width

        def cel(k):
            return [(k[0] * F.QUANT + w // 2) // T, (k[1] + h) // T]
        for j, p in enumerate(d["passagens"]):
            origem = [k for k, t in grafo.toques_no.items() if (n_m + n_c + j) in t]
            if not origem:
                continue
            vis = F.alcancaveis_de(grafo, origem)
            for rotulo, e in entradas.items():
                cx, cy = e[2] + w // 2, e[3] + h // 2
                area_ent = pygame.Rect(cx - T * 3 // 2, cy - T * 3 // 2, 3 * T, 3 * T)
                volta = any(area_ent.collidepoint(st[2] + w // 2, st[3] + h // 2)
                            for k, st in grafo.nos.items() if k in vis)
                if not volta:
                    msg = (f"sem caminho de volta: da passagem para '{p.destino['setor']}' "
                           f"(col {p.coluna}) nao se chega de novo a '{rotulo}'")
                    (rel.erro if exigir_volta else rel.aviso)(msg)
        comp = F.componentes(grafo)
        tam = {}
        for k, c_ in comp.items():
            tam[c_] = tam.get(c_, 0) + 1
        maos = {}
        for a, dests in grafo.arestas.items():
            for b in dests:
                if comp[a] != comp[b] and tam[comp[a]] >= 3 and tam[comp[b]] >= 3:
                    maos.setdefault((comp[a], comp[b]), (cel(a), cel(b)))
        for (ca, cb), (de, para) in sorted(maos.items(), key=lambda kv: kv[1][0]):
            rel.aviso(f"trecho de mao unica: de (col {de[0]}, linha {de[1]}) se desce para "
                      f"(col {para[0]}, linha {para[1]}) e nao se sobe de volta")
        rel.info["regioes_ida_e_volta"] = len([c_ for c_, t in tam.items() if t >= 3])
    # aranha: algum lugar onde a Areninha passa fica dentro do gatilho dela?
    if grafo is not None:
        h = sim.p.rect.height
        for dados_e, e in d["inimigos"]:
            if type(e).__name__ != "Aranha":
                continue
            melhor = None
            for st in grafo.nos.values():
                cx = st[2] + sim.p.rect.width / 2
                if abs(cx - e.ancora_x) > e.TOLERANCIA_X:
                    continue
                dy = st[3] - e.rect.bottom          # topo da Areninha - base da aranha
                if dy >= 0 and (melhor is None or dy < melhor):
                    melhor = dy
            if melhor is None or melhor > e.ALCANCE_VERTICAL + 140:
                rel.aviso(f"Aranha (col {dados_e['col']}) nunca ataca: nao ha onde ficar em pe "
                          f"ate {e.ALCANCE_VERTICAL:.0f} px abaixo dela "
                          f"({'nenhum chao embaixo' if melhor is None else f'chao mais perto a {melhor:.0f} px'})")
            elif melhor > e.ALCANCE_VERTICAL:
                rel.aviso(f"Aranha (col {dados_e['col']}) so ataca se a Areninha pular embaixo dela "
                          f"(chao a {melhor:.0f} px; gatilho {e.ALCANCE_VERTICAL:.0f} px)")
    sup = F.superficies(grade)
    pisadas = F.superficies_pisadas(grafo, sim) if grafo else set()
    nunca = sorted(sup - pisadas)
    if nunca:
        rel.aviso(f"{len(nunca)} celula(s) de superficie nunca pisada(s). "
                  f"Ex. (col, linha): {[[c, l] for l, c in nunca[:15]]}")
    rel.info.update({
        "minerios": n_m, "macas": n_c, "passagens": len(d["passagens"]),
        "superficies": len(sup), "superficies_pisadas": len(sup & pisadas),
        "pontos_sem_saida": len(presos), "pulos": pulos,
    })

    # ── dificuldade: o que só se alcança com o pulo duplo ────────────────────
    dif = None
    if dificuldade and pulos >= 2 and entradas:
        g1 = F.explorar(grade, list(entradas.values()), alvos, pulos=1, processos=processos)
        sim1 = F.Simulador(grade, 1)
        pis1 = F.superficies_pisadas(g1, sim1)
        toc1 = g1.alcancados()
        dif = {
            "minerios_so_com_pulo_duplo": [i for i in range(n_m) if i not in toc1],
            "macas_so_com_pulo_duplo": [i for i in range(n_c) if n_m + i not in toc1],
            "passagens_so_com_pulo_duplo": [j for j in range(len(zonas)) if n_m + n_c + j not in toc1],
            "superficies_so_com_pulo_duplo": sorted([c, l] for l, c in (pisadas - pis1)),
            "grafo_pulo_simples": g1,
        }
        rel.info["minerios_so_com_pulo_duplo"] = len(dif["minerios_so_com_pulo_duplo"])
        rel.info["superficies_so_com_pulo_duplo"] = len(dif["superficies_so_com_pulo_duplo"])
        rel.info["macas_so_com_pulo_duplo"] = len(dif["macas_so_com_pulo_duplo"])
        rel.info["indices_minerios_so_com_pulo_duplo"] = dif["minerios_so_com_pulo_duplo"]
    contexto = {"dados": d, "grafo": grafo, "sim": sim, "alvos": alvos, "entradas": entradas,
                "n_minerios": n_m, "n_curas": n_c, "dificuldade": dif, "presos": presos,
                "superficies": sup, "pisadas": pisadas}
    return rel, contexto


def main(argv=None):
    from src.nucleo import constants
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("setores", nargs="*", default=list(constants.SETORES))
    ap.add_argument("--pulos", type=int, default=2)
    ap.add_argument("--processos", type=int, default=0, help="0 = todos os núcleos")
    ap.add_argument("--dificuldade", action="store_true")
    ap.add_argument("--exigir-volta", action="store_true",
                    help="falta de caminho de volta (passagem -> entrada) vira ERRO")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    import os
    proc = a.processos or os.cpu_count() or 1
    F.iniciar_pygame()
    dados = {n: montar_setor(n) for n in constants.SETORES}
    total_erros = 0
    saida = {"pulos": a.pulos, "setores": {}}
    erros_lig, avisos_lig = verificar_ligacoes(dados)
    print("== LIGACOES ENTRE SETORES ==")
    for e in erros_lig:
        print("  ERRO ", e)
    for w in avisos_lig:
        print("  AVISO", w)
    if not erros_lig:
        print("  OK: todas as passagens tem destino e chegada; todos os setores tem ida e volta")
    total_erros += len(erros_lig)
    saida["ligacoes"] = {"erros": erros_lig, "avisos": avisos_lig}
    for nome in a.setores:
        rel, _ = analisar_setor(nome, a.pulos, proc, a.dificuldade, dados[nome],
                                exigir_volta=a.exigir_volta)
        i = rel.info
        print(f"\n== {nome.upper()} (pulo {'duplo' if a.pulos >= 2 else 'simples'}) ==")
        print(f"  {i['minerios']} minerios, {i['macas']} macas, {i['passagens']} passagens, "
              f"{i['nos_em_pe']} posicoes em pe, superficies pisadas "
              f"{i['superficies_pisadas']}/{i['superficies']}, {i['segundos_busca']} s")
        if "minerios_so_com_pulo_duplo" in i:
            print(f"  exigem pulo duplo: {i['minerios_so_com_pulo_duplo']} minerio(s), "
                  f"{i['macas_so_com_pulo_duplo']} maca(s), "
                  f"{i['superficies_so_com_pulo_duplo']} celula(s) de superficie")
        for e in rel.erros:
            print("  ERRO ", e)
        for w in rel.avisos:
            print("  AVISO", w)
        if not rel.erros:
            print("  OK")
        total_erros += len(rel.erros)
        saida["setores"][nome] = {"erros": rel.erros, "avisos": rel.avisos, "info": rel.info}
    if a.json:
        Path(a.json).write_text(json.dumps(saida, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n{'REPROVADO' if total_erros else 'APROVADO'}: {total_erros} erro(s)")
    return 1 if total_erros else 0


if __name__ == "__main__":
    raise SystemExit(main())
