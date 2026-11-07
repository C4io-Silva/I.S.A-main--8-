"""
gerar_mapas_tecnicos.py — documentação técnica e imagens dos 4 setores,
geradas a partir dos ARQUIVOS REAIS do jogo (CSVs, constants.py e as próprias
classes de entidades), nunca de ilustração.

Gera:
    docs/ISA_MAPA_TECNICO.md                         documentação (Tarefa 1)
    docs/MAPAS_TECNICOS/<setor>_tecnico_completo.png mapa técnico inteiro
    docs/MAPAS_TECNICOS/<setor>_tecnico_trecho_NN_colA-B.png  trechos ampliados
    docs/MAPAS_TECNICOS/<setor>_terreno_real.png     os tiles reais do CSV (sem fundo)
    docs/MAPAS_TECNICOS/visao_geral_setores.png      os 4 setores e as ligações
    docs/MAPAS_TECNICOS/dados_<setor>.json           todos os dados em JSON
    docs/MAPAS_TECNICOS/LEGENDA.md

Rotas, alcance e "exige pulo duplo" vêm da busca com a física real
(ferramentas/validar_fisica_real.py + fisica_nivel.py). Patrulhas vêm de
rodar Enemy/Tucano.update por 30 s de jogo com um relógio simulado.

uso (na raiz do projeto):
    python ferramentas/gerar_mapas_tecnicos.py [--processos N] [--sem-imagens]
Depois de mudar um CSV, rode de novo: a documentação acompanha o mapa.
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import ferramentas.fisica.fisica_nivel as F  # noqa: E402
import ferramentas.validacao.validar_fisica_real as V  # noqa: E402

pygame = F.iniciar_pygame()
from src.nucleo import constants  # noqa: E402
from src.mundo.decoracoes_offline import ARTE as ARTE_DECOR  # noqa: E402

T = constants.TILE_SIZE
DOCS = F.RAIZ / "docs"
PASTA = DOCS / "MAPAS_TECNICOS"

# ── catálogo de tiles ────────────────────────────────────────────────────────
FAMILIA = {
    "grama": {1, 10, 11, 12, 13},
    "terra": {2, 20, 21, 22, 23},
    "areia": {3},
    "pedra/rocha": {4, 24, 25, 26},
    "copa/tronco": {14, 15, 36, 37},
    "templo": {27, 28, 29, 63},
    "ponte/viga/galho": {60, 61, 62},
    "bloco genérico": {0},
}
COR_FAMILIA = {
    "grama": (86, 160, 72), "terra": (128, 88, 56), "areia": (214, 190, 120),
    "pedra/rocha": (92, 98, 128), "copa/tronco": (60, 110, 60), "templo": (120, 108, 128),
    "ponte/viga/galho": (176, 112, 52), "bloco genérico": (190, 60, 50),
}


def familia(tid):
    for nome, ids in FAMILIA.items():
        if tid in ids:
            return nome
    return None


def funcao_tile(tid):
    if tid in constants.TILES_PASSAGEM:
        d = constants.PASSAGENS_CSV[tid]
        return "passagem", f"{d['tipo']} → setor '{d['setor']}', chegada {d['chegada']}"
    if tid in constants.TILES_CHEGADA:
        origem = [k for k, v in constants.PASSAGENS_CSV.items() if v["chegada"] == tid]
        return "chegada", f"onde a Areninha reaparece ao usar a passagem {origem[0] if origem else '?'}"
    nomes = {
        constants.TILE_PLAYER_SPAWN: ("marcador", "spawn da Areninha (só no setor inicial)"),
        constants.TILE_MINERIO: ("marcador", "minério (abre pergunta)"),
        constants.TILE_MOB_COBRA: ("marcador", "cobra (classe Enemy), apoiada no bloco de baixo"),
        constants.TILE_MOB_TUCANO: ("marcador", "tucano, voa na altura da célula"),
        constants.TILE_MOB_ARANHA: ("marcador", "aranha, pendurada no bloco de cima"),
        constants.TILE_AREA_BOSS: ("marcador", "Gorila (só na arena)"),
        constants.TILE_ITEM_CURA: ("marcador", "maçã (+15 de vida)"),
    }
    if tid in nomes:
        return nomes[tid]
    if tid in constants.SOLID_TILES:
        return "sólido", familia(tid) or "sólido"
    if tid in constants.TILE_SPRITES:
        return "visual sem colisão", "desenhado na grade de terreno, atravessável"
    return "desconhecido", "sem sprite: vira o tile de fallback (0)"


# ── coleta de dados ──────────────────────────────────────────────────────────
def relogio_simulado():
    estado = {"t": 10_000}
    real = pygame.time.get_ticks
    pygame.time.get_ticks = lambda: estado["t"]
    return estado, real


def simular_patrulhas(d, sim):
    """Roda a IA real de cada inimigo comum por 30 s sem jogador por perto."""
    from src.mundo import setores as S
    estado, real = relogio_simulado()
    out = []
    try:
        for dados in d["marcadores"]["inimigos"]:
            e = S.criar_inimigo(dados)
            if e is None:
                continue
            nome = type(e).__name__.replace("Enemy", "Cobra")
            r0 = e.rect.copy()
            xs, ys = [e.rect.left], [e.rect.top]
            xr, yb = [e.rect.right], [e.rect.bottom]
            if nome != "Aranha":
                for _ in range(1800):
                    estado["t"] += 16
                    e.update(sim.world.obstaculos_proximos(e.rect), None)
                    xs.append(e.rect.left); xr.append(e.rect.right)
                    ys.append(e.rect.top); yb.append(e.rect.bottom)
            info = {
                "tipo": nome, "marcador_col": dados["col"],
                "marcador_linha": dados["row"] - 1 if dados["ancora"] == "chao" else dados["row"] + 1,
                "rect_inicial_px": [r0.x, r0.y, r0.w, r0.h],
                "patrulha_x_px": [min(xs), max(xr)], "patrulha_y_px": [min(ys), max(yb)],
                "patrulha_colunas": [min(xs) // T, (max(xr) - 1) // T],
                "caiu_do_mapa": max(yb) > sim.altura,
            }
            if nome == "Cobra":
                info.update(alcance_patrulha_px=e.ALCANCE, raio_deteccao_px=round(e.RAIO_DETECCAO),
                            raio_desistencia_px=round(e.RAIO_DESISTENCIA))
            elif nome == "Tucano":
                info.update(alcance_vaivem_px=e.ALCANCE, amplitude_voo_px=e.AMPLITUDE_VOO,
                            raio_rasante_px=round(e.RAIO_DETECCAO))
            else:
                info.update(alcance_vertical_px=e.ALCANCE_VERTICAL,
                            largura_gatilho_px=round(e.TOLERANCIA_X * 2))
            out.append(info)
    finally:
        pygame.time.get_ticks = real
    return out


def segmentos_plataforma(grade, sup, pisadas, so_duplo):
    """Trechos contínuos de superfície numa mesma linha."""
    segs = []
    for l in range(len(grade)):
        c = 0
        while c < len(grade[l]):
            if (l, c) in sup:
                c0 = c
                while c + 1 < len(grade[l]) and (l, c + 1) in sup:
                    c += 1
                celulas = [(l, x) for x in range(c0, c + 1)]
                ids = sorted({grade[l][x] for x in range(c0, c + 1)})
                segs.append({
                    "linha": l, "col_ini": c0, "col_fim": c, "largura_tiles": c - c0 + 1,
                    "ids": ids, "familias": sorted({familia(i) or str(i) for i in ids}),
                    "pisado": any(x in pisadas for x in celulas),
                    "so_com_pulo_duplo": all(x in so_duplo or x not in pisadas for x in celulas)
                    and any(x in so_duplo for x in celulas),
                })
            c += 1
    return segs


def rotas(ctx):
    """Arestas (nó, macro) das rotas: principal = até as passagens/luta; secundária = itens."""
    g = ctx["grafo"]
    n_m, n_c = ctx["n_minerios"], ctx["n_curas"]
    n_alvos = len(ctx["alvos"])
    principal, secundaria = set(), set()

    raizes = [k for k, v in g.pai.items() if v is None]

    def caminho_alvo(a):
        return F.rota_natural(g, raizes, a) or []
    for a in range(n_m + n_c, n_alvos):
        principal.update(caminho_alvo(a))
    for a in range(0, n_m + n_c):
        secundaria.update(p for p in caminho_alvo(a) if p not in principal)
    return principal, secundaria


def coletar(nome, proc, dados):
    rel, ctx = V.analisar_setor(nome, 2, proc, True, dados)
    d = ctx["dados"]
    sim = ctx["sim"]
    dif = ctx["dificuldade"] or {}
    so_duplo_sup = {(l, c) for c, l in dif.get("superficies_so_com_pulo_duplo", [])}
    segs = segmentos_plataforma(d["grade"], ctx["superficies"], ctx["pisadas"], so_duplo_sup)
    patrulhas = simular_patrulhas(d, sim)
    g = ctx["grafo"]
    # passagens: dá para parar em pé dentro da área?
    passagens = []
    for j, p in enumerate(d["passagens"]):
        em_pe = False
        for st in g.nos.values():
            sim.restaurar(st)
            if p.rect_interacao.colliderect(sim.p.rect):
                em_pe = True
                break
        passagens.append({
            "id": p.destino["id_tile"], "tipo": p.tipo, "col": p.coluna, "linha": p.linha,
            "destino_setor": p.destino["setor"], "chegada_no_destino": p.destino["chegada"],
            "sprite": p.estilo.get("sprite"), "estrutura_tiles": [p.estilo["largura"], p.estilo["altura"]],
            "area_interacao_px": [p.rect_interacao.x, p.rect_interacao.y, p.rect_interacao.w,
                                  p.rect_interacao.h],
            "area_interacao_colunas": [p.rect_interacao.left // T, p.rect_interacao.right // T - 1],
            "da_para_parar_em_pe_na_area": em_pe,
            "exige_pulo_duplo": j in dif.get("passagens_so_com_pulo_duplo", []),
            "rotulo": p.rotulo,
        })
    minerios = []
    duplos = set(dif.get("minerios_so_com_pulo_duplo", []))
    for i, (m, r) in enumerate(zip(d["marcadores"]["minerios"], d["minerios"])):
        k = g.toque.get(i)
        minerios.append({
            "indice": i, "col": m["col"], "linha_marcador": m["row"] - 1,
            "rect_px": [r.x, r.y, r.w, r.h], "exige_pulo_duplo": i in duplos,
            "passos_desde_a_entrada": (g.prof.get(k[0], 0) + (1 if k and k[1] is not None else 0)) if k else None,
        })
    curas = [{"indice": i, "col": c["col"], "linha_marcador": c["row"] - 1,
              "exige_pulo_duplo": i in set(dif.get("macas_so_com_pulo_duplo", []))}
             for i, c in enumerate(d["marcadores"]["curas"])]
    chegadas = {str(k): {"col": c, "linha": l} for k, (c, l) in sorted(d["marcadores"]["chegadas"].items())}
    contagem = {}
    for linha in _grade_crua(nome):
        for v in linha:
            contagem[v] = contagem.get(v, 0) + 1
    decor = {}
    for linha in _grade_decor(nome):
        for v in linha:
            if v != -1:
                decor[v] = decor.get(v, 0) + 1
    estruturas = json.loads((F.RAIZ / "assets/levels/estruturas_cenario.json").read_text(encoding="utf-8")).get(nome, [])
    info = {
        "setor": nome, "arquivo": constants.SETORES[nome]["arquivo"],
        "ambiente": constants.SETORES[nome]["ambiente"],
        "colunas": len(d["grade"][0]), "linhas": len(d["grade"]),
        "largura_px": len(d["grade"][0]) * T, "altura_px": len(d["grade"]) * T,
        "spawn": ({"col": d["marcadores"]["player"][0], "linha": d["marcadores"]["player"][1] - 1}
                  if d["marcadores"]["player"] else None),
        "entradas_px": rel.info.get("entradas"),
        "chegadas": chegadas, "passagens": passagens, "minerios": minerios, "macas": curas,
        "inimigos": patrulhas,
        "boss": ({"marcador": list(d["area_boss"]["marcador"]),
                  "area_luta_colunas": [d["area_boss"]["rect"].left // T, d["area_boss"]["rect"].right // T - 1],
                  "area_luta_linhas": [d["area_boss"]["rect"].top // T, d["area_boss"]["rect"].bottom // T],
                  "rect_gorila_px": list(d["boss"])} if d["area_boss"] else None),
        "contagem_ids_csv": {str(k): v for k, v in sorted(contagem.items())},
        "contagem_decoracao": {str(k): v for k, v in sorted(decor.items())},
        "estruturas_cenario": estruturas,
        "plataformas": segs,
        "validacao": {"erros": rel.erros, "avisos": rel.avisos, "info": {
            k: v for k, v in rel.info.items() if k != "entradas"}},
    }
    return info, ctx


def _grade_crua(nome):
    from src.nucleo.utils import carregar_nivel_csv
    return carregar_nivel_csv(os.path.join(constants.PASTA_SETORES, constants.SETORES[nome]["arquivo"]))


def _grade_decor(nome):
    import csv
    p = F.RAIZ / "assets/levels/decoracoes" / f"{nome}_decor.csv"
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", newline="") as f:
        return [[int(v) for v in r] for r in csv.reader(f) if r]


# ── desenho ──────────────────────────────────────────────────────────────────
C = {
    "fundo": (24, 26, 34), "vazio": (236, 238, 242), "grade": (214, 218, 226),
    "grade10": (150, 156, 170), "texto": (20, 22, 28), "texto_claro": (245, 245, 245),
    "nao_solido": (188, 218, 236), "decor": (226, 232, 214),
    "rota1": (18, 140, 60), "rota2": (60, 120, 220), "duplo": (240, 130, 0),
    "precisao": (220, 30, 30), "nunca": (230, 0, 200), "passagem": (130, 40, 170),
    "chegada": (0, 150, 170), "spawn": (0, 170, 60), "minerio": (220, 160, 0),
    "cura": (210, 30, 40), "cobra": (60, 120, 30), "tucano": (20, 60, 160),
    "aranha": (90, 30, 110), "boss": (200, 30, 30),
}


def fonte(tam):
    return pygame.font.Font(None, tam)


def texto(sup, msg, pos, tam=18, cor=None, fundo=None, centro=False):
    s = fonte(tam).render(str(msg), True, cor or C["texto"], fundo)
    r = s.get_rect()
    if centro:
        r.center = pos
    else:
        r.topleft = pos
    sup.blit(s, r)
    return r


MARGEM_E, MARGEM_T = 46, 34


def desenhar_tecnico(info, ctx, S):
    """Mapa técnico em S px por tile, com margens numeradas."""
    d = ctx["dados"]
    grade = d["grade"]
    cru = _grade_crua(info["setor"])
    decor = _grade_decor(info["setor"])
    L, Cn = len(grade), len(grade[0])
    W, H = Cn * S + 2 * MARGEM_E, L * S + 2 * MARGEM_T
    sup = pygame.Surface((W, H))
    sup.fill(C["vazio"])
    ox, oy = MARGEM_E, MARGEM_T

    def px(x, y):
        return ox + x * S / T, oy + y * S / T

    # células
    for l in range(L):
        for c in range(Cn):
            tid = grade[l][c]
            r = pygame.Rect(ox + c * S, oy + l * S, S, S)
            if tid in constants.SOLID_TILES:
                sup.fill(COR_FAMILIA.get(familia(tid), (200, 60, 50)), r)
            elif tid >= 0:
                sup.fill(C["nao_solido"], r)
            elif decor and decor[l][c] != -1:
                sup.fill(C["decor"], r)
    # grade
    for c in range(Cn + 1):
        cor = C["grade10"] if c % 10 == 0 else C["grade"]
        if S >= 12 or c % 10 == 0:
            pygame.draw.line(sup, cor, (ox + c * S, oy), (ox + c * S, oy + L * S), 1)
    for l in range(L + 1):
        cor = C["grade10"] if l % 5 == 0 else C["grade"]
        if S >= 12 or l % 5 == 0:
            pygame.draw.line(sup, cor, (ox, oy + l * S), (ox + Cn * S, oy + l * S), 1)
    for c in range(0, Cn, 10):
        texto(sup, c, (ox + c * S + 2, 8), 20)
        texto(sup, c, (ox + c * S + 2, oy + L * S + 8), 20)
    for l in range(0, L, 5):
        texto(sup, l, (6, oy + l * S + 2), 20)
        texto(sup, l, (ox + Cn * S + 6, oy + l * S + 2), 20)
    # superfícies: pisada / só com pulo duplo / nunca pisada
    so_duplo = {(l, c) for c, l in (ctx["dificuldade"] or {}).get("superficies_so_com_pulo_duplo", [])}
    for (l, c) in ctx["superficies"]:
        r = pygame.Rect(ox + c * S, oy + l * S, S, max(2, S // 6))
        if (l, c) not in ctx["pisadas"]:
            sup.fill(C["nunca"], r)
        elif (l, c) in so_duplo:
            sup.fill(C["duplo"], r)
    # saltos de precisão: plataforma <= 2 tiles que só se alcança com pulo duplo
    for seg in info["plataformas"]:
        if seg["so_com_pulo_duplo"] and seg["largura_tiles"] <= 2:
            cx = ox + (seg["col_ini"] + seg["largura_tiles"] / 2) * S
            cy = oy + seg["linha"] * S - S * 0.9
            pygame.draw.circle(sup, C["precisao"], (int(cx), int(cy)), max(5, int(S * 0.45)), 3)
    # rotas com as trajetórias simuladas
    principal, secundaria = rotas(ctx)
    g, sim = ctx["grafo"], ctx["sim"]
    for conjunto, cor, larg in ((secundaria, C["rota2"], 2), (principal, C["rota1"], 4)):
        for (k, mi) in sorted(conjunto):
            _, _, pts = sim.simular(g.nos[k], F.MACROS[mi], trajeto=True)
            if pts and len(pts) > 1:
                pygame.draw.lines(sup, cor, False, [px(x, y) for x, y in pts], larg)
    # área de luta do Gorila
    if d["area_boss"]:
        a = d["area_boss"]["rect"]
        ra = pygame.Rect(*px(a.x, a.y), a.w * S / T, a.h * S / T)
        pygame.draw.rect(sup, C["boss"], ra, 3)
        texto(sup, "ÁREA DE LUTA (cruzar a borda esquerda ativa o Gorila)", (ra.x + 6, ra.y + 4), 22, C["boss"])
        b = d["boss"]
        rb = pygame.Rect(*px(b.x, b.y), b.w * S / T, b.h * S / T)
        pygame.draw.rect(sup, C["boss"], rb, 0)
        texto(sup, "G", rb.center, 30, C["texto_claro"], centro=True)
    # passagens
    for p in info["passagens"]:
        x, y, w, h = p["area_interacao_px"]
        r = pygame.Rect(*px(x, y), w * S / T, h * S / T)
        pygame.draw.rect(sup, C["passagem"], r, 3)
        rot = f"P{p['id']} -> {p['destino_setor']} (C{p['chegada_no_destino']})"
        texto(sup, rot, (r.x, r.y - 20), 21, C["texto_claro"], C["passagem"])
    # chegadas e spawn
    for id_c, ch in info["chegadas"].items():
        cx, cy = ox + ch["col"] * S + S // 2, oy + ch["linha"] * S + S // 2
        pygame.draw.circle(sup, C["chegada"], (cx, cy), max(6, S // 2 - 2))
        texto(sup, f"C{id_c}", (cx, cy), 18, C["texto_claro"], centro=True)
    if info["spawn"]:
        cx, cy = ox + info["spawn"]["col"] * S + S // 2, oy + info["spawn"]["linha"] * S + S // 2
        pygame.draw.circle(sup, C["spawn"], (cx, cy), max(7, S // 2))
        texto(sup, "S", (cx, cy), 22, C["texto_claro"], centro=True)
    # minérios e maçãs
    for m in info["minerios"]:
        x, y, w, h = m["rect_px"]
        cx, cy = px(x + w / 2, y + h / 2)
        rr = max(6, int(S * 0.42))
        pts = [(cx, cy - rr), (cx + rr, cy), (cx, cy + rr), (cx - rr, cy)]
        pygame.draw.polygon(sup, C["minerio"], pts)
        pygame.draw.polygon(sup, C["duplo"] if m["exige_pulo_duplo"] else C["texto"], pts, 3)
        texto(sup, m["indice"], (cx, cy - rr - 9), 17, C["texto"], centro=True)
    for c in info["macas"]:
        cx, cy = ox + c["col"] * S + S // 2, oy + c["linha_marcador"] * S + S // 2
        pygame.draw.circle(sup, C["cura"], (cx, cy), max(5, S // 3))
    # inimigos com a área real de patrulha
    for e in info["inimigos"]:
        cor = C[e["tipo"].lower()]
        x0, x1 = e["patrulha_x_px"]
        y0, y1 = e["patrulha_y_px"]
        rp = pygame.Rect(*px(x0, y0), (x1 - x0) * S / T, (y1 - y0) * S / T)
        if e["tipo"] == "Aranha":
            ax = ox + e["marcador_col"] * S + S // 2
            topo = oy + (e["marcador_linha"]) * S
            alc = e["alcance_vertical_px"] * S / T
            pygame.draw.line(sup, cor, (ax, topo), (ax, topo + alc + S), 3)
            pygame.draw.circle(sup, cor, (ax, topo + S // 2), max(6, S // 2))
            texto(sup, "A", (ax, topo + S // 2), 20, C["texto_claro"], centro=True)
            msgs = [m for m in info["validacao"]["erros"] + info["validacao"]["avisos"]
                    if f"Aranha (col {e['marcador_col']})" in m
                    or f"Aranha (marcador col {e['marcador_col']})" in m]
            if msgs:
                r = max(8, S // 2)
                cy = topo + S // 2
                pygame.draw.line(sup, C["precisao"], (ax - r, cy - r), (ax + r, cy + r), 4)
                pygame.draw.line(sup, C["precisao"], (ax - r, cy + r), (ax + r, cy - r), 4)
                rot = "nunca ataca" if any("nunca ataca" in m for m in msgs) else "problema"
                if any("sobrepondo" in m for m in msgs):
                    rot += " / encosta em bloco"
                texto(sup, rot, (ax + r + 4, cy - 9), 20, C["texto_claro"], C["precisao"])
        else:
            s2 = pygame.Surface(rp.size, pygame.SRCALPHA)
            s2.fill((*cor, 70))
            sup.blit(s2, rp)
            pygame.draw.rect(sup, cor, rp, 2)
            texto(sup, e["tipo"][0], rp.center, 24, C["texto_claro"], cor, centro=True)
    return sup


def legenda(largura):
    itens = [
        ("bloco", "terreno sólido (cor = família do tile)"), ("ns", "tile sem colisão / decoração"),
        ("rota1", "rota principal: trajetórias reais até passagens/luta"),
        ("rota2", "rotas secundárias: até cada minério/maçã"),
        ("duplo", "superfície que só se alcança com pulo duplo"),
        ("precisao", "salto de precisão: plataforma de até 2 tiles só com pulo duplo"),
        ("nunca", "superfície nunca pisada (inacessível)"),
        ("passagem", "P30-35: área de interação da passagem -> destino (chegada)"),
        ("chegada", "C40-45: chegada"), ("spawn", "S: spawn"),
        ("minerio", "minério (nº; contorno laranja = exige pulo duplo)"),
        ("cura", "maçã"), ("cobra", "C cobra / T tucano: faixa real de patrulha (30 s simulados)"),
        ("aranha", "A aranha: linha = alcance de 240 px do gatilho"),
        ("boss", "G Gorila e área de luta"),
    ]
    colunas = max(1, largura // 520)
    linhas = (len(itens) + colunas - 1) // colunas
    sup = pygame.Surface((largura, 16 + linhas * 30))
    sup.fill((250, 250, 250))
    for i, (k, msg) in enumerate(itens):
        x = 16 + (i // linhas) * 520
        y = 10 + (i % linhas) * 30
        cor = {"bloco": COR_FAMILIA["terra"], "ns": C["nao_solido"]}.get(k, C.get(k))
        pygame.draw.rect(sup, cor, (x, y + 3, 26, 18))
        texto(sup, msg, (x + 34, y + 4), 20)
    return sup


def com_titulo_e_legenda(mapa, titulo):
    leg = legenda(max(mapa.get_width(), 1100))
    W = max(mapa.get_width(), leg.get_width())
    H = 44 + mapa.get_height() + leg.get_height()
    sup = pygame.Surface((W, H))
    sup.fill((250, 250, 250))
    texto(sup, titulo, (12, 10), 30)
    sup.blit(mapa, (0, 44))
    sup.blit(leg, (0, 44 + mapa.get_height()))
    return sup


def desenhar_terreno_real(info):
    """Tiles reais do CSV (16 px = arte nativa), decoração, estruturas e passagens. Sem fundo."""
    from src.nucleo.utils import carregar_tiles
    from src.mundo.passagens import GerenciadorPassagens
    nome = info["setor"]
    tiles, fb = carregar_tiles(constants.TILE_SPRITES, constants.TILE_SIZE, constants.TILE_FALLBACK_ID)
    S = 16
    escala = S / T
    cru = _grade_crua(nome)
    grade, mk = F.ler_setor(nome)
    decor = _grade_decor(nome)
    L, Cn = len(grade), len(grade[0])
    sup = pygame.Surface((Cn * S, L * S))
    sup.fill(constants.AMBIENTES[constants.SETORES[nome]["ambiente"]]["cor_ceu"])
    cache = {}

    def peq(img):
        k = id(img)
        if k not in cache:
            cache[k] = pygame.transform.scale(img, (max(1, int(img.get_width() * escala)),
                                                    max(1, int(img.get_height() * escala))))
        return cache[k]
    for item in info["estruturas_cenario"]:
        img = pygame.image.load(str(F.RAIZ / "assets/images/cenarios" / item["imagem"])).convert_alpha()
        w, h = img.get_width(), img.get_height()     # arte nativa = 16 px por tile
        sup.blit(img, (int(item["coluna"] * S - w // 2), int(item["base"] * S - h)))
    for l in range(L):
        for c in range(Cn):
            tid = grade[l][c]
            if tid >= 0:
                sup.blit(peq(tiles.get(tid, fb)), (c * S, l * S))
    decor_img = {}
    for l in range(len(decor)):
        for c in range(len(decor[l])):
            v = decor[l][c]
            if v != -1:
                if v not in decor_img:
                    decor_img[v] = pygame.transform.scale(pygame.image.load(
                        str(F.RAIZ / "assets/images/tiles" / ARTE_DECOR[v])).convert_alpha(), (S, S))
                sup.blit(decor_img[v], (c * S, l * S))
    for p in GerenciadorPassagens(mk["passagens"], grade).itens:
        sup.blit(peq(p.superficie), (int(p.rect.x * escala), int(p.rect.y * escala)))
    return sup


def visao_geral(infos, imagens):
    escala = 4
    blocos = []
    for nome, info in infos.items():
        g = _grade_crua(nome)
        s = pygame.Surface((len(g[0]) * escala, len(g) * escala))
        s.fill((236, 238, 242))
        for l, linha in enumerate(g):
            for c, v in enumerate(linha):
                if v in constants.SOLID_TILES:
                    s.fill(COR_FAMILIA.get(familia(v), (190, 60, 50)), (c * escala, l * escala, escala, escala))
        for p in info["passagens"]:
            pygame.draw.circle(s, C["passagem"], (p["col"] * escala, p["linha"] * escala), 7)
        for ch in info["chegadas"].values():
            pygame.draw.circle(s, C["chegada"], (ch["col"] * escala, ch["linha"] * escala), 6)
        blocos.append((nome, info, s))
    W = max(b[2].get_width() for b in blocos) + 520
    H = sum(b[2].get_height() + 50 for b in blocos) + 20
    sup = pygame.Surface((W, H))
    sup.fill((250, 250, 250))
    y = 10
    for nome, info, s in blocos:
        texto(sup, f"{nome.upper()} — {info['colunas']}x{info['linhas']} tiles, {len(info['minerios'])} minérios",
              (10, y), 28)
        sup.blit(s, (10, y + 30))
        ty = y + 34
        for p in info["passagens"]:
            texto(sup, f"P{p['id']} col {p['col']} -> {p['destino_setor']} (chega em C{p['chegada_no_destino']})",
                  (s.get_width() + 30, ty), 22, C["passagem"])
            ty += 24
        for id_c, ch in info["chegadas"].items():
            texto(sup, f"C{id_c} col {ch['col']} (chegada)", (s.get_width() + 30, ty), 22, C["chegada"])
            ty += 24
        y += s.get_height() + 50
    return sup


def salvar(sup, nome):
    caminho = PASTA / nome
    pygame.image.save(sup, str(caminho))
    return caminho


def gerar_imagens(infos, ctxs):
    feitos = []
    for nome, info in infos.items():
        ctx = ctxs[nome]
        S = 24
        mapa = desenhar_tecnico(info, ctx, S)
        titulo = (f"{nome.upper()} — {info['arquivo']} — {info['colunas']}x{info['linhas']} tiles "
                  f"(tile = 48 px no jogo, {S} px aqui). Gerado de assets/levels/setores/{info['arquivo']}")
        completo = com_titulo_e_legenda(mapa, titulo)
        if completo.get_width() > 6000:
            f = 6000 / completo.get_width()
            completo = pygame.transform.smoothscale(
                completo, (6000, int(completo.get_height() * f)))
        feitos.append(salvar(completo, f"{nome}_tecnico_completo.png"))
        largura_trecho = 64
        n = 0
        # trechos de 64 colunas espaçados por igual, com pelo menos 4 de sobreposição
        cols = info["colunas"]
        n_tr = max(1, -(-(cols - 4) // (largura_trecho - 4)))
        inicios = ([0] if n_tr == 1 else
                   [round(i * (cols - largura_trecho) / (n_tr - 1)) for i in range(n_tr)])
        for c0 in inicios:
            c1 = min(info["colunas"], c0 + largura_trecho)
            recorte = mapa.subsurface(pygame.Rect(
                MARGEM_E + c0 * S - (MARGEM_E if c0 == 0 else 0), 0,
                (c1 - c0) * S + (MARGEM_E if c0 == 0 else 0) + (MARGEM_E if c1 == info["colunas"] else 0),
                mapa.get_height())).copy()
            if info["colunas"] <= largura_trecho:
                break
            n += 1
            img = com_titulo_e_legenda(recorte, f"{nome.upper()} — trecho {n}: colunas {c0} a {c1 - 1}")
            feitos.append(salvar(img, f"{nome}_tecnico_trecho_{n:02d}_col{c0:03d}-{c1 - 1:03d}.png"))
            if c1 >= info["colunas"]:
                break
        real = desenhar_terreno_real(info)
        feitos.append(salvar(real, f"{nome}_terreno_real.png"))
    feitos.append(salvar(visao_geral(infos, None), "visao_geral_setores.png"))
    return feitos


# ── markdown ─────────────────────────────────────────────────────────────────
def gerar_md(infos, catalogo):
    linhas = []
    w = linhas.append
    w("# I.S.A. — Mapa técnico dos quatro setores")
    w("")
    w("> **Gerado automaticamente** por `ferramentas/gerar_mapas_tecnicos.py` a partir dos arquivos reais "
      "(`assets/levels/setores/*.csv`, `assets/levels/decoracoes/*_decor.csv`, "
      "`assets/levels/estruturas_cenario.json`, `constants.py`, `src/nivel_dados.py`) e das classes do jogo. "
      "Não edite à mão: mude o CSV e rode a ferramenta de novo. Imagens em `docs/MAPAS_TECNICOS/`, "
      "dados completos em `docs/MAPAS_TECNICOS/dados_<setor>.json`.")
    w("")
    w("## 1. Convenções do CSV")
    w("")
    w(f"- 1 célula = 1 tile = **{T} px** no jogo (`TILE_SIZE = 16 × SCALE`, `SCALE = {constants.SCALE}`). "
      "Linha 0 é o topo; coluna 0 é a esquerda. `-1` = vazio.")
    w("- O terreno e os marcadores ficam no **mesmo CSV**. Os marcadores são lidos e apagados da grade ao carregar "
      "(`utils.extrair_marcadores`), então não têm sprite nem colisão.")
    w("- **A célula do marcador é a célula que a entidade ocupa.** Minério, maçã, cobra, chegada e spawn ficam "
      "apoiados no bloco de **baixo**; a aranha fica pendurada no bloco de **cima**; o tucano voa na altura da célula.")
    w("- Colisão: só os IDs de `constants.SOLID_TILES` são sólidos (blocos inteiros 48×48; não existe plataforma "
      "atravessável por baixo nem rampa). Qualquer outro ID com sprite é desenhado mas atravessável.")
    w("- Um ID sem sprite em `TILE_SPRITES` vira o tile de fallback (ID 0, tijolo) — se o ID estiver em "
      "`SOLID_TILES` ele colide, senão é só visual.")
    w("- A decoração (IDs 100–117) fica num CSV **separado** (`assets/levels/decoracoes/<setor>_decor.csv`) "
      "do mesmo tamanho do terreno; nunca colide. As estruturas grandes (árvores, arcos, colunas) ficam em "
      "`assets/levels/estruturas_cenario.json` (coluna central + linha da base), atrás dos tiles, sem colisão.")
    w("- Todos os setores têm parede invisível nas bordas esquerda e direita (`Partida.limitar_ao_setor`). "
      "Não há limite no topo; cair abaixo da última linha = GAME OVER.")
    w("")
    w("## 2. Catálogo de IDs (verificado no código e nos CSVs)")
    w("")
    w("| ID | Função | Detalhe | Sprite | Floresta | Caverna | Copas | Arena |")
    w("|---|---|---|---|---|---|---|---|")
    for item in catalogo:
        w(f"| {item['id']} | {item['funcao']} | {item['detalhe']} | {item['sprite'] or '—'} | "
          + " | ".join(str(item['contagem'].get(s, 0) or '') for s in ("floresta", "caverna", "copas", "arena"))
          + " |")
    w("")
    w("Decoração (CSV separado, sem colisão): "
      + ", ".join(f"{k} = `{v}`" for k, v in sorted(ARTE_DECOR.items())) + ".")
    w("")
    w("## 3. Setores")
    for nome, info in infos.items():
        w("")
        w(f"### {nome.capitalize()} — `{info['arquivo']}`")
        w("")
        val = info["validacao"]["info"]
        w(f"- Tamanho: **{info['colunas']} × {info['linhas']} tiles** ({info['largura_px']} × {info['altura_px']} px). "
          f"Ambiente: `{info['ambiente']}`.")
        if info["spawn"]:
            w(f"- **Spawn da Areninha (90):** coluna {info['spawn']['col']}, linha {info['spawn']['linha']}.")
        for id_c, ch in info["chegadas"].items():
            orig = [k for k, v in constants.PASSAGENS_CSV.items() if str(v["chegada"]) == id_c]
            w(f"- **Chegada {id_c}:** coluna {ch['col']}, linha {ch['linha']} "
              f"(destino da passagem {orig[0] if orig else '?'}).")
        w(f"- Física real: {val.get('nos_em_pe')} posições em pé alcançáveis; superfícies pisadas "
          f"{val.get('superficies_pisadas')}/{val.get('superficies')}; "
          f"{val.get('minerios_so_com_pulo_duplo', 0)} minério(s) e {val.get('superficies_so_com_pulo_duplo', 0)} "
          f"célula(s) de superfície só com pulo duplo; pontos sem saída: {val.get('pontos_sem_saida')}.")
        w("")
        w("**Passagens**")
        w("")
        w("| ID | Tipo | Coluna, linha | Leva a | Chegada | Área de interação (colunas) | Para em pé na área? | Sprite |")
        w("|---|---|---|---|---|---|---|---|")
        for p in info["passagens"]:
            w(f"| {p['id']} | {p['tipo']} | {p['col']}, {p['linha']} | {p['destino_setor']} | {p['chegada_no_destino']} "
              f"| {p['area_interacao_colunas'][0]}–{p['area_interacao_colunas'][1]} | "
              f"{'sim' if p['da_para_parar_em_pe_na_area'] else 'NÃO'} | `{p['sprite']}` |")
        w("")
        if info["inimigos"]:
            w("**Inimigos (patrulha real: 30 s de IA simulados sem o jogador)**")
            w("")
            w("| Tipo | Marcador (col, linha) | Faixa percorrida (colunas) | Faixa vertical (px) | Observação |")
            w("|---|---|---|---|---|")
            for e in info["inimigos"]:
                if e["tipo"] == "Cobra":
                    obs = (f"vira na borda da plataforma ou a {e['alcance_patrulha_px']:.0f} px da origem; "
                           f"persegue a {e['raio_deteccao_px']} px, desiste a {e['raio_desistencia_px']} px")
                elif e["tipo"] == "Tucano":
                    obs = (f"vaivém de ±{e['alcance_vaivem_px']:.0f} px, sobe/desce {e['amplitude_voo_px']:.0f} px; "
                           f"rasante a {e['raio_rasante_px']} px")
                else:
                    obs = (f"não se move na horizontal; desce até {e['alcance_vertical_px']:.0f} px "
                           f"quando a Areninha passa embaixo (faixa de {e['largura_gatilho_px']} px)")
                if e["caiu_do_mapa"]:
                    obs += " — **caiu do mapa na simulação**"
                w(f"| {e['tipo']} | {e['marcador_col']}, {e['marcador_linha']} | "
                  f"{e['patrulha_colunas'][0]}–{e['patrulha_colunas'][1]} | "
                  f"{e['patrulha_y_px'][0]}–{e['patrulha_y_px'][1]} | {obs} |")
            w("")
        if info["boss"]:
            b = info["boss"]
            w(f"**Gorila:** marcador 95 em coluna {b['marcador'][0]}, linha {b['marcador'][1]}; área de luta "
              f"colunas {b['area_luta_colunas'][0]}–{b['area_luta_colunas'][1]}, linhas "
              f"{b['area_luta_linhas'][0]}–{b['area_luta_linhas'][1]} (de `src/nivel_dados.AREA_BOSS`, não do CSV). "
              f"A luta começa quando `player.rect.left >= coluna {b['area_luta_colunas'][0]} × 48`.")
            w("")
        if info["macas"]:
            w("**Maçãs (96):** " + "; ".join(
                f"col {c['col']}, linha {c['linha_marcador']}{' (pulo duplo)' if c['exige_pulo_duplo'] else ''}"
                for c in info["macas"]) + ".")
            w("")
        if info["minerios"]:
            w(f"**Minérios (91): {len(info['minerios'])}** — `*` = só com pulo duplo; passos = nº de "
              "movimentos (andar/pular/cair) desde a primeira entrada.")
            w("")
            w("| # | Col | Linha | Passos | # | Col | Linha | Passos | # | Col | Linha | Passos |")
            w("|---|---|---|---|---|---|---|---|---|---|---|---|")
            ms = info["minerios"]
            for i in range(0, len(ms), 3):
                cel = []
                for m in ms[i:i + 3]:
                    cel += [f"{m['indice']}{'*' if m['exige_pulo_duplo'] else ''}", str(m["col"]),
                            str(m["linha_marcador"]), str(m["passos_desde_a_entrada"])]
                cel += [""] * (12 - len(cel))
                w("| " + " | ".join(cel) + " |")
            w("")
        segs = info["plataformas"]
        larg = {}
        for s in segs:
            larg[s["largura_tiles"]] = larg.get(s["largura_tiles"], 0) + 1
        fam = {}
        for s in segs:
            for f in s["familias"]:
                fam[f] = fam.get(f, 0) + 1
        estreitas = [s for s in segs if s["largura_tiles"] <= 2]
        w(f"**Plataformas (trechos contínuos de superfície):** {len(segs)} trechos; "
          f"{len(estreitas)} com 1–2 tiles de largura; "
          f"{sum(1 for s in segs if s['so_com_pulo_duplo'])} só com pulo duplo; "
          f"{sum(1 for s in segs if not s['pisado'])} nunca pisados. Por família: "
          + ", ".join(f"{k} {v}" for k, v in sorted(fam.items())) + ". Lista completa em `dados_"
          + nome + ".json`.")
        w("")
        if info["estruturas_cenario"]:
            w("**Estruturas de cenário (sem colisão):** " + "; ".join(
                f"`{e['imagem']}` col {e['coluna']} base {e['base']}" for e in info["estruturas_cenario"]) + ".")
            w("")
        if info["contagem_decoracao"]:
            w("**Decoração:** " + ", ".join(f"{k}×{v}" for k, v in info["contagem_decoracao"].items()) + ".")
            w("")
        erros, avisos = info["validacao"]["erros"], info["validacao"]["avisos"]
        if erros or avisos:
            w("**Validador de física real:**")
            w("")
            for e in erros:
                w(f"- ERRO: {e}")
            for a in avisos:
                w(f"- AVISO: {a}")
            w("")
    w("## 4. Limitações do código que o mapa precisa respeitar")
    w("")
    for item in LIMITACOES:
        w(f"- {item}")
    w("")
    return "\n".join(linhas) + "\n"


LIMITACOES = [
    "**Passagens e chegadas são fixas no código:** os IDs 30–35 e 40–45 e para onde cada um leva estão em "
    "`constants.PASSAGENS_CSV`. Cada ID deve aparecer **uma única vez** em todos os CSVs. Uma passagem nova exige "
    "um par novo de IDs nessa tabela e um estilo em `src/passagens.ESTILOS`.",
    "**A área de interação de uma passagem é 3×3 tiles** centrada no marcador (`passagens.ALCANCE_TILES = 1`). "
    "O sprite ocupa 3×2 tiles com o marcador no meio da linha de baixo; partes que caem sobre bloco sólido são apagadas.",
    "**Interação por tecla (E/Enter/X):** funciona também no ar. Se a chegada cair dentro da área de outra "
    "passagem, um toque em E leva de volta (teleporte em sequência).",
    "**Arena:** a área de luta vem de `src/nivel_dados.AREA_BOSS` (colunas c0–c1, linhas), não do CSV. A luta "
    "começa quando a borda esquerda da Areninha passa de `c0`; daí a saída tranca até a vitória. A saída (35) "
    "precisa ficar **antes** de `c0`. Se a arena mudar de tamanho, `AREA_BOSS` precisa mudar junto.",
    "**Spawn:** um único 90, só na floresta (`constants.SETOR_INICIAL`). `src/nivel_dados.PLAYER_SPAWN` é só "
    "o valor de reserva; vale o marcador do CSV.",
    "**`src/nivel_dados.SETORES_GERADOS`** guarda tamanho e entrada de cada setor e é usado por "
    "`ferramentas/validar_redesign.py`. Um CSV com outro tamanho exige atualizar esse dicionário.",
    "**Referência congelada:** `docs/TERRENO_REFERENCIA.json` guarda dimensões, marcadores e o hash das colisões "
    "da versão aprovada. `validar_redesign.py` e `validar_terreno.py` **reprovam qualquer mudança de geometria "
    "ou de marcador de propósito**; depois de aprovado o redesign, regenere com "
    "`ferramentas/atualizar_referencia_terreno.py`.",
    "**Decoração:** `<setor>_decor.csv` precisa ter exatamente o mesmo tamanho do terreno, senão o setor não "
    "carrega (`DecoracaoSetor` lança erro). IDs aceitos: 100–117.",
    "**Inimigos:** cobra precisa de chão embaixo e vira nas bordas (sensor de 6 px à frente); tucano nunca "
    "pousa e inverte ao bater em bloco; aranha precisa de bloco sólido em cima, não pode encostar em bloco "
    "vizinho (a largura dela é 51 px > 48 px) e só ataca se houver onde a Areninha passar até 240 px abaixo. "
    "Inimigos só são atualizados a até 6 tiles fora da tela (`MARGEM_ATIVACAO_TILES`).",
    "**Gerador:** `gerar_mundo.py` não sobrescreve CSVs editados à mão (`_gerado.json` guarda o hash do que ele "
    "gerou); não use `--sobrescrever` nos mapas do redesign.",
    "**Validação geométrica antiga:** `src/validacao_mapa.py` usa `DEGRAU_MAX = 2` e `VAO_MAX = 2` (aproximação). "
    "Os limites medidos com a física real estão em `docs/ISA_FISICA_LEVEL_DESIGN.md` e são maiores no vão.",
]


def catalogo_ids(infos):
    contagens = {n: {int(k): v for k, v in i["contagem_ids_csv"].items()} for n, i in infos.items()}
    ids = sorted(set(constants.TILE_SPRITES) | constants.SOLID_TILES | set(constants.TILES_MARCADORES)
                 | {k for c in contagens.values() for k in c if k >= 0})
    cat = []
    for tid in ids:
        f, det = funcao_tile(tid)
        sprite = constants.TILE_SPRITES.get(tid)
        if sprite and not (F.RAIZ / "assets/images/tiles" / sprite).exists():
            sprite += " (ARQUIVO AUSENTE)"
        cat.append({"id": tid, "funcao": f, "detalhe": det, "sprite": f"`{sprite}`" if sprite else None,
                    "contagem": {n: c.get(tid, 0) for n, c in contagens.items()}})
    return cat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--processos", type=int, default=0)
    ap.add_argument("--sem-imagens", action="store_true")
    a = ap.parse_args()
    proc = a.processos or os.cpu_count() or 1
    PASTA.mkdir(parents=True, exist_ok=True)
    dados = {n: V.montar_setor(n) for n in constants.SETORES}
    infos, ctxs = {}, {}
    for nome in constants.SETORES:
        print(f"analisando {nome}...", flush=True)
        infos[nome], ctxs[nome] = coletar(nome, proc, dados[nome])
        (PASTA / f"dados_{nome}.json").write_text(
            json.dumps(infos[nome], indent=1, ensure_ascii=False), encoding="utf-8")
    catalogo = catalogo_ids(infos)
    (DOCS / "ISA_MAPA_TECNICO.md").write_text(gerar_md(infos, catalogo), encoding="utf-8")
    print("docs/ISA_MAPA_TECNICO.md gravado", flush=True)
    if not a.sem_imagens:
        for p in gerar_imagens(infos, ctxs):
            print("  imagem:", p.relative_to(F.RAIZ))
        (PASTA / "LEGENDA.md").write_text(LEGENDA_MD, encoding="utf-8")


LEGENDA_MD = """# Mapas técnicos — como ler

Gerados por `ferramentas/gerar_mapas_tecnicos.py` a partir dos CSVs reais. Não são ilustração.

- `<setor>_tecnico_completo.png`: o setor inteiro. Margens numeradas: colunas de 10 em 10 (topo e base),
  linhas de 5 em 5 (laterais). Tile do jogo = 48 px; aqui 24 px (reduzido se a imagem passaria de 6000 px).
- `<setor>_tecnico_trecho_NN_colA-B.png`: o mesmo mapa em trechos de 64 colunas (4 de sobreposição), em 24 px por tile.
- `<setor>_terreno_real.png`: os sprites reais dos tiles, da decoração, das estruturas e das passagens,
  em 16 px por tile (arte nativa), sobre a cor de céu do ambiente. **Os backgrounds não entram** (não fazem parte do CSV).
- `visao_geral_setores.png`: os 4 setores lado a lado com as ligações entre passagens (P) e chegadas (C).
- `dados_<setor>.json`: tudo em números (posições, patrulhas, plataformas, validação).

Cores do mapa técnico:

| Cor | Significado |
|---|---|
| verde/marrom/cinza/roxo... | bloco sólido; a cor é a família do tile (grama, terra, rocha, copa/tronco, templo, ponte/viga/galho) |
| azul-claro | tile sem colisão (água, decoração na grade de terreno) |
| bege | célula com decoração da camada `_decor.csv` (sem colisão) |
| linha verde grossa | rota principal: trajetórias reais da Areninha da entrada até cada passagem (e até a área do Gorila) |
| linha azul fina | rotas secundárias: trajetórias até cada minério/maçã |
| faixa laranja no topo do bloco | superfície que só se alcança com pulo duplo |
| círculo vermelho | salto de precisão: plataforma de 1–2 tiles alcançável só com pulo duplo |
| faixa magenta | superfície onde nunca se consegue pisar |
| retângulo roxo P | área de interação 3×3 da passagem; rótulo = destino e chegada |
| círculo azul C | marcador de chegada |
| círculo verde S | spawn |
| losango dourado | minério (número = índice); contorno laranja = exige pulo duplo |
| círculo vermelho pequeno | maçã |
| caixa C / T | cobra / tucano: faixa REAL percorrida em 30 s de IA simulada |
| linha A | aranha: fio até o alcance do gatilho (240 px) |
| G e retângulo vermelho | Gorila e área de luta |

As trajetórias são a primeira rota encontrada pela busca em largura (menor número de movimentos), não a única.
"""

if __name__ == "__main__":
    main()
