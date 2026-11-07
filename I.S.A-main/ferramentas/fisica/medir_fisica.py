"""
medir_fisica.py — mede a física REAL da Areninha para o level design.

Monta mapas de teste mínimos (chão, plataforma-alvo, teto...) e roda o
Character.move do jogo quadro a quadro (via ferramentas/fisica_nivel.py).
Nada é calculado por fórmula: todo número sai de uma simulação.

uso (na raiz do projeto):
    python ferramentas/medir_fisica.py              # imprime e grava o JSON
    python ferramentas/medir_fisica.py --rapido     # envelope de saltos menor

Saída: docs/ISA_FISICA_MEDIDAS.json (lido por docs/ISA_FISICA_LEVEL_DESIGN.md).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import ferramentas.fisica.fisica_nivel as F  # noqa: E402

pygame = F.iniciar_pygame()
from src.nucleo import constants  # noqa: E402

T = constants.TILE_SIZE
SOLIDO = 24          # pro_rocha.png: qualquer ID de SOLID_TILES serve
VAZIO = -1
RAPIDO = "--rapido" in sys.argv


def grade_vazia(linhas, colunas):
    return [[VAZIO] * colunas for _ in range(linhas)]


def preencher(g, l0, l1, c0, c1, v=SOLIDO):
    for l in range(l0, l1 + 1):
        for c in range(c0, c1 + 1):
            if 0 <= l < len(g) and 0 <= c < len(g[0]):
                g[l][c] = v


def chao_largo(linhas=30, colunas=60, linha_chao=25):
    g = grade_vazia(linhas, colunas)
    preencher(g, linha_chao, linhas - 1, 0, colunas - 1)
    return g


# ── 1. básico ─────────────────────────────────────────────────────────────────
def medir_basico():
    g = chao_largo()
    sim = F.Simulador(g)
    sim.colocar(10, 25)
    sim.assentar()
    p = sim.p
    e0 = sim.estado()
    x0 = p.rect.x
    for _ in range(60):
        sim.passo(1, False)
    vel = (p.rect.x - x0) / 60
    return {
        "hitbox_px": [p.rect.width, p.rect.height],
        "hitbox_tiles": [round(p.rect.width / T, 3), round(p.rect.height / T, 3)],
        "tile_px": T,
        "velocidade_px_por_quadro": vel,
        "velocidade_px_por_s": vel * constants.FPS,
        "velocidade_tiles_por_s": round(vel * constants.FPS / T, 3),
        "quadros_por_tile_andando": round(T / vel, 2),
        "gravidade_px_q2": constants.GRAVITY,
        "impulso_pulo_px_q": constants.SPEED_JUMP,
        "queda_maxima_px_q": constants.VEL_TERMINAL,
        "pulos_no_ar": constants.MAX_JUMPS,
        "fps": constants.FPS,
    }, e0


def trajetoria(sim, e0, entrada):
    """entrada(f) -> (dir, pular). Devolve lista de (x, base) até pousar."""
    sim.restaurar(e0)
    p = sim.p
    pts = []
    for f in range(400):
        d, pular = entrada(f)
        sim.passo(d, pular)
        pts.append((p.rect.x, p.rect.bottom))
        if f >= 1 and p.on_ground:
            break
    return pts


# ── 2. pulo simples / duplo ───────────────────────────────────────────────────
def medir_pulos(e0):
    g = chao_largo(linhas=40, colunas=80, linha_chao=35)
    sim = F.Simulador(g)
    sim.colocar(10, 35)
    sim.assentar()
    e0 = sim.estado()
    base = sim.p.rect.bottom
    x0 = sim.p.rect.x

    def resumo(pts):
        topo = min(b for _, b in pts)
        q_topo = [b for _, b in pts].index(topo) + 1
        return {"altura_px": base - topo, "altura_tiles": round((base - topo) / T, 3),
                "quadros_ate_topo": q_topo, "quadros_no_ar": len(pts),
                "distancia_px": pts[-1][0] - x0,
                "distancia_tiles": round((pts[-1][0] - x0) / T, 3)}

    simples = resumo(trajetoria(sim, e0, lambda f: (1, f == 0)))
    simples_parado = resumo(trajetoria(sim, e0, lambda f: (0, f == 0)))
    melhor_alt, melhor_dist = None, None
    tabela = []
    for k in range(1, 46):
        r = resumo(trajetoria(sim, e0, lambda f, k=k: (1, f in (0, k))))
        r["segundo_pulo_no_quadro"] = k
        tabela.append(r)
        if melhor_alt is None or r["altura_px"] > melhor_alt["altura_px"]:
            melhor_alt = r
        if melhor_dist is None or r["distancia_px"] > melhor_dist["distancia_px"]:
            melhor_dist = r
    # cair de uma borda: quantos pulos sobram?
    g2 = chao_largo(linhas=40, colunas=80, linha_chao=35)
    preencher(g2, 35, 39, 13, 79, VAZIO)     # o chão acaba na coluna 12
    sim2 = F.Simulador(g2)
    sim2.colocar(11, 35)
    sim2.assentar()
    p = sim2.p
    for f in range(60):
        sim2.passo(1, False)
        if not p.on_ground and f > 1:
            break
    pulos_apos_cair = p.jumps_left
    return {
        "simples_andando": simples,
        "simples_parado": simples_parado,
        "duplo_mais_alto": melhor_alt,
        "duplo_mais_longe": melhor_dist,
        "duplo_por_momento_do_2o_pulo": [
            {k: r[k] for k in ("segundo_pulo_no_quadro", "altura_px", "distancia_px")}
            for r in tabela],
        "pulos_disponiveis_apos_cair_de_borda": pulos_apos_cair,
    }


# ── 3. envelope: vão x desnível ──────────────────────────────────────────────
def alcanca_plataforma(vao, desnivel, largura_alvo=3, pulos=2, teto=None):
    """
    Plataforma de saída (até a coluna 9) e plataforma-alvo depois de `vao`
    colunas vazias, `desnivel` tiles mais alta (+) ou mais baixa (-).
    O fundo é vazio: errar o salto = cair para fora (como num poço).
    Devolve (alcançou, nº de pousos distintos no alvo).
    """
    linhas = 40
    base = 22                     # linha do topo da plataforma de saída
    colunas = 10 + vao + largura_alvo + 6
    g = grade_vazia(linhas, colunas)
    preencher(g, base, base + 1, 0, 9)
    topo_alvo = base - desnivel
    c0 = 10 + vao
    preencher(g, topo_alvo, topo_alvo + 1, c0, c0 + largura_alvo - 1)
    if teto is not None:
        preencher(g, base - teto - 1, base - teto - 1, 0, colunas - 1)
    sim = F.Simulador(g, pulos)
    entradas = []
    for col in (7, 8, 9):
        sim.colocar(col, base)
        if sim.assentar()[0]:
            entradas.append(sim.estado())
    alvo = pygame.Rect(c0 * T, topo_alvo * T - 2, largura_alvo * T, 2)
    grafo = F.explorar(g, entradas, [alvo], pulos=pulos)
    w = sim.p.rect.width
    x_ini, x_fim = c0 * T, (c0 + largura_alvo) * T
    pousos = sum(1 for k, e in grafo.nos.items()
                 if e[3] + sim.p.rect.height == topo_alvo * T
                 and e[2] + w > x_ini and e[2] < x_fim)
    return pousos > 0, pousos


def montar_salto(vao, desnivel, largura_alvo=3):
    linhas = 40
    base = 22
    colunas = 10 + vao + largura_alvo + 6
    g = grade_vazia(linhas, colunas)
    preencher(g, base, base + 1, 0, 9)
    topo_alvo = base - desnivel
    c0 = 10 + vao
    preencher(g, topo_alvo, topo_alvo + 1, c0, c0 + largura_alvo - 1)
    return g, base, topo_alvo, c0


def alcanca_exaustivo(vao, desnivel, pulos=2, largura_alvo=3):
    """
    Limite FÍSICO, sem depender das macro-ações do validador: parte da borda
    (pés com 1 px de apoio, e também 16 px para dentro) segurando para a
    direita, testa o 2º pulo em TODOS os quadros de 1 a 50 e também
    "cair da borda e pular no ar" com o 1º pulo em 0..14 quadros.
    """
    g, base, topo_alvo, c0 = montar_salto(vao, desnivel, largura_alvo)
    sim = F.Simulador(g, pulos)
    w = sim.p.rect.width
    x_borda = 10 * T
    planos = [(0, None)] + ([(0, k) for k in range(1, 51)] if pulos >= 2 else [])
    planos_borda = []
    for k1 in range(0, 15, 2):
        planos_borda.append((k1, None))
        if pulos >= 2:
            planos_borda += [(k1, k1 + k) for k in range(4, 51, 2)]
    # Soltar a direção no ar (para não passar do alvo em quedas longas) só é
    # tentado se segurar o tempo todo não bastou.
    soltas = [None] + (list(range(6, 61, 6)) if desnivel < 0 else [])
    for solta in soltas:
        if solta is not None:
            planos_s = [pl for pl in planos if pl[1] is None or pl[1] % 3 == 0]
            planos_b = [pl for pl in planos_borda if pl[1] is None or pl[1] % 6 == 0]
        else:
            planos_s, planos_b = planos, planos_borda
        if _tentar(sim, base, topo_alvo, c0, largura_alvo, x_borda, planos_s, planos_b, solta):
            return True
    return False


def _tentar(sim, base, topo_alvo, c0, largura_alvo, x_borda, planos, planos_borda, solta):
    p = sim.p
    for recuo in (1, 16):
        sim.colocar(9, base)
        sim.assentar()
        p.rect.left = x_borda - recuo
        p.pos_x = float(p.rect.x)
        e0 = sim.estado()
        for modo, lista in (("pulo", planos), ("borda", planos_borda)):
            for a, b in lista:
                sim.restaurar(e0)
                t_ar = None
                for f in range(300):
                    if modo == "pulo":
                        pular = f == a or (b is not None and f == b)
                    else:
                        if t_ar is None and not p.on_ground and f > 0:
                            t_ar = f
                        ref = None if t_ar is None else f - t_ar
                        pular = ref is not None and (ref == a or (b is not None and ref == b))
                    direcao = 1 if (solta is None or f < solta) else 0
                    sim.passo(direcao, pular)
                    if p.rect.top > sim.altura:
                        break
                    if f >= 1 and p.on_ground and (modo == "pulo" or t_ar is not None):
                        if (p.rect.bottom == topo_alvo * T and p.rect.right > c0 * T
                                and p.rect.left < (c0 + largura_alvo) * T):
                            return True
                        if modo == "pulo" or f > 2:
                            break
    return False


def medir_envelope_exaustivo():
    desniveis = list(range(4, -9, -1)) if not RAPIDO else [3, 2, 1, 0, -2, -5]
    resultado = {}
    for pulos in (1, 2):
        linha = {}
        for dy in desniveis:
            maior, falhas = -1, 0
            for vao in range(0, 14):
                if alcanca_exaustivo(vao, dy, pulos):
                    maior, falhas = vao, 0
                else:
                    falhas += 1
                    if falhas >= 2:
                        break
            linha[dy] = maior
        resultado[f"pulos_{pulos}"] = linha
        print(f"  envelope exaustivo ({pulos}) pronto", flush=True)
    return resultado


def medir_envelope():
    desniveis = list(range(4, -9, -1)) if not RAPIDO else [3, 2, 1, 0, -2, -5]
    resultado = {}
    for pulos in (1, 2):
        linha = {}
        for dy in desniveis:
            maior = -1
            falhas = 0
            for vao in range(0, 14):
                ok, _ = alcanca_plataforma(vao, dy, pulos=pulos)
                if ok:
                    maior = vao
                    falhas = 0
                else:
                    falhas += 1
                    if falhas >= 2:
                        break
            linha[dy] = maior
        resultado[f"pulos_{pulos}"] = linha
        print(f"  envelope ({pulos} pulo{'s' if pulos > 1 else ''}) pronto", flush=True)
    return resultado


# ── 4. área de pouso ─────────────────────────────────────────────────────────
def medir_pouso():
    res = {}
    for largura in (1, 2, 3):
        ok, n = alcanca_plataforma(3, 0, largura_alvo=largura)
        ok1, n1 = alcanca_plataforma(3, 0, largura_alvo=largura, pulos=1)
        res[largura] = {"vao3_mesmo_nivel_duplo": [ok, n], "vao3_mesmo_nivel_simples": [ok1, n1]}
    ok, n = alcanca_plataforma(2, 2, largura_alvo=1)
    res["1_tile_2_acima_vao2"] = [ok, n]
    return res


# ── 5. teto, túneis e degraus ────────────────────────────────────────────────
def medir_teto():
    res = {}
    # túnel de altura h (h células livres entre chão e teto): dá para andar?
    for h in (1, 2, 3):
        g = grade_vazia(20, 30)
        preencher(g, 15, 19, 0, 29)              # chão: topo na linha 15
        preencher(g, 0, 14 - h, 5, 24)           # teto: deixa h linhas livres
        sim = F.Simulador(g)
        sim.colocar(2, 15)
        sim.assentar()
        x0 = sim.p.rect.x
        for _ in range(240):
            sim.passo(1, False)
        res[f"tunel_{h}_andar"] = sim.p.rect.x - x0 > 10 * T   # 240 quadros = 15 tiles livres
    # degrau máximo dentro de um túnel de altura h (sem teto = céu aberto)
    for h in (2, 3, 4, None):
        maior = 0
        for degrau in range(1, 7):
            if h is not None and degrau >= h:
                break
            g = grade_vazia(30, 30)
            preencher(g, 22, 29, 0, 29)
            preencher(g, 22 - degrau, 21, 12, 29)   # degrau a partir da coluna 12
            if h is not None:
                preencher(g, 0, 21 - h, 0, 29)
            sim = F.Simulador(g)
            sim.colocar(9, 22)
            sim.assentar()
            alvo = pygame.Rect(14 * T, (22 - degrau) * T - 2, 3 * T, 2)
            gr = F.explorar(g, [sim.estado()], [alvo])
            if gr.alcancados():
                maior = degrau
        res[f"degrau_max_teto_{h if h else 'aberto'}"] = maior
    # altura de pulo com teto baixo: bate a cabeça e perde o impulso
    for h in (2, 3):
        g = grade_vazia(30, 30)
        preencher(g, 22, 29, 0, 29)
        preencher(g, 0, 21 - h, 0, 29)
        sim = F.Simulador(g)
        sim.colocar(10, 22)
        sim.assentar()
        e0 = sim.estado()
        pts = trajetoria(sim, e0, lambda f: (0, f in (0, 10)))
        res[f"pulo_duplo_com_{h}_tiles_livres_altura_px"] = 22 * T - min(b for _, b in pts)
    # vão de 1 tile no chão: anda por cima ou cai?
    g = chao_largo(linhas=30, colunas=40, linha_chao=22)
    preencher(g, 22, 29, 15, 15, VAZIO)
    sim = F.Simulador(g)
    sim.colocar(10, 22)
    sim.assentar()
    for _ in range(120):
        sim.passo(1, False)
    res["buraco_1_tile_andando_cai"] = sim.p.rect.top > sim.altura or sim.p.rect.bottom > 22 * T
    return res


# ── 6. paredes, empurrão e queda ─────────────────────────────────────────────
def medir_paredes():
    res = {}
    # escalada de parede: segurando contra ela e pulando, sobe mais que o pulo duplo?
    g = chao_largo(linhas=30, colunas=30, linha_chao=22)
    preencher(g, 0, 21, 15, 29)
    sim = F.Simulador(g)
    sim.colocar(13, 22)
    sim.assentar()
    e0 = sim.estado()
    pts = trajetoria(sim, e0, lambda f: (1, f in (0, 10)))
    res["pulo_duplo_contra_parede_altura_px"] = 22 * T - min(b for _, b in pts)
    res["sem_escalada_de_parede"] = res["pulo_duplo_contra_parede_altura_px"] <= 3 * T
    # Empurrão de dano contra uma parede, com a COBRA REAL (Enemy) encostando
    # pelo lado direito: Enemy.check_player_collision aplica KNOCKBACK_X em pos_x.
    from src.entidades.enemies.enemy import Enemy
    res["empurrao_contra_parede"] = {}
    for altura in (1, 3, 8):
        g = chao_largo(linhas=30, colunas=30, linha_chao=22)
        preencher(g, 22 - altura, 21, 0, 9)      # parede nas colunas 0-9
        sim = F.Simulador(g)
        sim.colocar(10, 22)
        sim.assentar()
        p = sim.p
        for _ in range(30):
            sim.passo(-1, False)                  # encosta na parede
        antes = p.rect.copy()
        cobra = Enemy(x=p.rect.right - 4, y=p.rect.bottom - Enemy(0, 0).rect.height)
        p.invulnerable = False
        bateu = cobra.check_player_collision(p)
        trajeto = []
        for _ in range(30):
            sim.passo(0, False)
            trajeto.append(p.rect.bottom)
        res["empurrao_contra_parede"][f"parede_{altura}_tiles"] = {
            "contato_aplicado": bool(bateu),
            "antes_x_base": [antes.x, antes.bottom],
            "depois_x_base": [p.rect.x, p.rect.bottom],
            "subiu_px": antes.bottom - min(trajeto),
            "terminou_em_cima_da_parede": p.rect.bottom <= (22 - altura) * T and p.rect.left < 10 * T,
        }
    # queda: quadros para cair N tiles, velocidade terminal
    g = chao_largo(linhas=60, colunas=10, linha_chao=55)
    sim = F.Simulador(g)
    sim.colocar(5, 5)
    p = sim.p
    marcos = {}
    y0 = p.rect.bottom
    for q in range(1, 300):
        sim.passo(0, False)
        caiu = (p.rect.bottom - y0) / T
        for n in (1, 3, 5, 10, 20, 40):
            if n not in marcos and caiu >= n:
                marcos[n] = q
        if p.on_ground:
            break
    res["quadros_para_cair_n_tiles"] = marcos
    res["quadros_ate_velocidade_terminal"] = int(constants.VEL_TERMINAL / constants.GRAVITY + 0.999)
    return res


# ── 7. quique no inimigo (pisão) ─────────────────────────────────────────────
def medir_quique():
    g = chao_largo(linhas=40, colunas=30, linha_chao=35)
    sim = F.Simulador(g)
    sim.colocar(10, 35)
    sim.assentar()
    p = sim.p
    base = p.rect.bottom
    # o que Enemy.pisar faz: vel_y = -QUIQUE_Y e devolve os pulos
    p.vel_y = -constants.QUIQUE_Y
    p.jumps_left = p.MAX_JUMPS
    p.on_ground = False
    e0 = sim.estado()
    so = trajetoria(sim, e0, lambda f: (0, False))
    com = None
    for k in range(1, 30):
        pts = trajetoria(sim, e0, lambda f, k=k: (0, f in (k, k + 12)))
        h = base - min(b for _, b in pts)
        if com is None or h > com:
            com = h
    return {"quique_sozinho_altura_px": base - min(b for _, b in so),
            "quique_mais_pulo_duplo_altura_px": com}


def main():
    saida = {}
    print("medindo básico e pulos...", flush=True)
    basico, e0 = medir_basico()
    saida["basico"] = basico
    saida["pulos"] = medir_pulos(e0)
    print("medindo envelope de saltos (vão x desnível)...", flush=True)
    saida["envelope_vao_max_tiles"] = medir_envelope()
    print("medindo envelope físico exaustivo (todos os momentos do 2º pulo)...", flush=True)
    saida["envelope_fisico_exaustivo"] = medir_envelope_exaustivo()
    print("medindo pouso, teto, paredes e quique...", flush=True)
    saida["pouso"] = medir_pouso()
    saida["teto"] = medir_teto()
    saida["paredes_e_queda"] = medir_paredes()
    saida["quique"] = medir_quique()
    saida["camera"] = {
        "tela_virtual_min_px": [800, 600],
        "tiles_visiveis_800x600": [round(800 / T, 2), round(600 / T, 2)],
        "tiles_visiveis_16x9_1066x600": [round(1066 / T, 2), round(600 / T, 2)],
        "avanco_camera_x_tiles": constants.CAM_AVANCO_X / T,
        "zona_morta_y_tiles": constants.CAM_ZONA_MORTA_Y / T,
    }
    destino = F.RAIZ / "docs" / "ISA_FISICA_MEDIDAS.json"
    destino.write_text(json.dumps(saida, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in saida.items() if k != "pulos"}, indent=1, ensure_ascii=False))
    p = saida["pulos"]
    for k in ("simples_parado", "simples_andando", "duplo_mais_alto", "duplo_mais_longe"):
        print(k, {c: p[k][c] for c in p[k] if c != "segundo_pulo_no_quadro"},
              p[k].get("segundo_pulo_no_quadro", ""))
    print("pulos após cair de borda:", p["pulos_disponiveis_apos_cair_de_borda"])
    print("gravado em", destino)


if __name__ == "__main__":
    main()
