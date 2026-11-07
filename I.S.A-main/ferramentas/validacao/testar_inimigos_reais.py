"""
testar_inimigos_reais.py — testa a IA REAL de cada inimigo de um setor (código do jogo: Partida.atualizar_jogando,
Enemy/Tucano/Aranha.update, golpe de asa, check_player_collision), com relógio
simulado de 16 ms por quadro. Minérios são retirados do setor durante o teste
para nenhuma pergunta abrir no meio (o CSV não muda).
Para cada cobra, tucano e aranha: patrulha (30 s), ativação do ataque com a
Areninha parada perto, derrota com o golpe de asa (J) e esquiva sem dano
(andar, pular, pulo duplo e, para a aranha, "isca": entrar no gatilho, recuar e
passar enquanto ela sobe).

uso (na raiz do projeto):
    python ferramentas/testar_inimigos_reais.py caverna [saida.json]
"""
import os, sys, json, tempfile
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["ISA_DB"] = os.path.join(tempfile.mkdtemp(prefix="isa_inim_"), "e.db")
from pathlib import Path
RAIZ = str(Path(__file__).resolve().parents[2])
SETOR = sys.argv[1] if len(sys.argv) > 1 else "caverna"
SAIDA = sys.argv[2] if len(sys.argv) > 2 else None
sys.path.insert(0, RAIZ); os.chdir(RAIZ)
import pygame
_t = [10_000]
pygame.time.get_ticks = lambda: _t[0]
from src.nucleo import constants
sys.path.insert(0, os.path.join(os.getcwd(), "testes")); from compat_main import M  # fachada: API antiga sobre src/jogo
from src.sistemas.joystick import GerenciadorJoystick
from src.entidades.enemies import Aranha, Tucano, Enemy
T = constants.TILE_SIZE
S = constants.SOLID_TILES

pygame.init(); M.configurar_janela(); M.clock = pygame.time.Clock()
M.gamepad = GerenciadorJoystick(); M.recriar_ui()


def novo():
    M.iniciar_jogo()
    M.ativar_setor(SETOR)
    M.itens[:] = []
    M.estado_jogo = "JOGANDO"
    M.player.player_health = 1000
    M.player.invulnerable = False


def chao(col, linha_ini):
    g = M.setor_atual.grade
    for l in range(max(1, linha_ini), len(g)):
        if g[l][col] in S and g[l - 1][col] not in S:
            return l
    return None


def por(col, linha_base):
    p = M.player
    p.rect.centerx = col * T + T // 2
    p.rect.bottom = linha_base * T
    p.pos_x, p.pos_y = float(p.rect.x), float(p.rect.y)
    p.vel_y = 0
    p.jumps_left = p.MAX_JUMPS
    M.atualizar_camera(instantaneo=True)


def quadros(n, d=0, pular=(), golpear=lambda i: False, parar=lambda: False):
    """Roda n quadros do jogo com entrada simulada. Devolve nº de quadros rodados."""
    for i in range(n):
        _t[0] += 16
        M.moving_left, M.moving_right = d < 0, d > 0
        if i in pular:
            M.jump_pressed = True
        if golpear(i):
            M.golpe.pedir()
        M.estado_jogo = "JOGANDO"
        M.atualizar_jogando(16)
        if parar():
            M.moving_left = M.moving_right = False
            return i + 1
    M.moving_left = M.moving_right = False
    return n


def mesmo_piso(col, linha_sup, lado, max_tiles=7):
    """Coluna mais distante (até max_tiles) andando pelo mesmo piso, sem subir/descer."""
    g = M.setor_atual.grade
    c = col
    for _ in range(max_tiles):
        n = c + lado
        if not (0 <= n < len(g[0])) or g[linha_sup][n] not in S or g[linha_sup - 1][n] in S:
            break
        c = n
    return c


def inimigo_por_col(tipo, col):
    for e in M.enemies:
        if isinstance(e, tipo) and (type(e) is tipo) and abs(e.rect.centerx // T - col) <= 1:
            return e
    return None


def dano():
    return 1000 - M.player.player_health


res = []
novo()
marc = [(d["classe"], d["col"], d["row"]) for d in
        __import__("utils").extrair_marcadores(
            __import__("utils").carregar_nivel_csv(os.path.join(
                constants.PASTA_SETORES, constants.SETORES[SETOR]["arquivo"])))["inimigos"]]
for classe, col, row in marc:
    tipo = {"Enemy": Enemy, "Tucano": Tucano, "Aranha": Aranha}[classe]
    nome = {"Enemy": "Cobra", "Tucano": "Tucano", "Aranha": "Aranha"}[classe]
    r = {"tipo": nome, "marcador_col": col}

    # ── 1. patrulha 30 s, Areninha fora do alcance de detecção mas dentro da área ativa
    novo()
    e = inimigo_por_col(tipo, col)
    r["rect_inicial"] = [e.rect.x, e.rect.y, e.rect.w, e.rect.h]
    if nome != "Aranha":
        lado = -1 if col > 20 else 1
        dist = int((e.RAIO_DETECCAO + e.ALCANCE) / T) + 3
        cpl = max(1, min(M.setor_atual.world.colunas - 2, col + lado * dist))
        lb = chao(cpl, 10)
        por(cpl, lb)
        xs, ys = [], []
        for _ in range(1800):
            quadros(1)
            xs.append(e.rect.x); ys.append(e.rect.y)
            por(cpl, lb)   # segura a Areninha parada no lugar
        r["patrulha_px"] = [min(xs), max(xs) + e.rect.w]
        r["patrulha_colunas"] = [min(xs) // T, (max(xs) + e.rect.w - 1) // T]
        r["amplitude_px"] = max(xs) - min(xs)
        r["altura_px"] = [min(ys), max(ys)]
        r["parado"] = (max(xs) - min(xs)) < T
        r["perseguiu_sem_querer"] = e.estado not in ("PATRULHA", "CRUZEIRO")
        r["areninha_em"] = [cpl, lb]
        r["caiu_do_mapa"] = max(ys) > M.setor_atual.altura_px
    # ── 2. ativação do ataque: Areninha parada perto
    novo()
    e = inimigo_por_col(tipo, col)
    if nome == "Aranha":
        lb = chao(int(e.ancora_x) // T, int(e.altura_inicial) // T + 1)
        r["chao_abaixo_linha"] = lb
        r["distancia_chao_px"] = None if lb is None else lb * T - (e.rect.bottom)
        if lb is not None:
            por(int(e.ancora_x) // T, lb)
            estados = set(); maxd = 0
            n = quadros(300, parar=lambda: M.player.preso)
            for _ in range(120):
                quadros(1); estados.add(e.estado); maxd = max(maxd, e.pos_y - e.altura_inicial)
            r["ataque"] = {"prendeu": M.player.preso or dano() > 0, "quadros_ate_prender": n,
                           "dano": dano(), "desceu_px": round(maxd)}
    else:
        lb = (e.rect.bottom // T) if nome == "Cobra" else chao(col, int(e.rect.bottom // T))
        opc = [(abs(mesmo_piso(col, lb, l, 3) - col), mesmo_piso(col, lb, l, 3)) for l in (-1, 1)]
        cpl = max(opc)[1]
        r["piso_linha"] = lb
        por(cpl, lb)
        n = quadros(600, parar=lambda: dano() > 0)
        r["ataque"] = {"estado": e.estado, "acertou": dano() > 0, "quadros_ate_dano": n,
                       "dano": dano(), "areninha_em": cpl}
    # ── 3. derrotar com o golpe de asa (J), sem tomar dano
    novo()
    e = inimigo_por_col(tipo, col)
    if nome == "Aranha":
        lb = chao(int(e.ancora_x) // T, int(e.altura_inicial) // T + 1)
        if lb is not None:
            # espera fora do gatilho, a 2 tiles; entra, recua 1 tile e golpeia quando ela desce
            ax = int(e.ancora_x) // T
            por(ax - 2, chao(ax - 2, lb - 3) or lb)
            M.player.flip = False
            quadros(10, d=1)                       # entra no gatilho
            quadros(12, d=-1)                      # sai antes de ser preso
            M.player.flip = False
            n = quadros(400, golpear=lambda i: i % 22 == 0, parar=lambda: e.derrotado)
            r["derrota"] = {"derrotado": e.derrotado, "quadros": n, "dano": dano(),
                            "preso": bool(M.player.preso)}
    else:
        lb = (e.rect.bottom // T) if nome == "Cobra" else chao(col, int(e.rect.bottom // T))
        opc = sorted(((abs(mesmo_piso(col, lb, l) - col), l) for l in (-1, 1)), reverse=True)
        dist, lado = opc[0]
        cpl = mesmo_piso(col, lb, lado)
        r["espaco_de_aproximacao_tiles"] = {"esquerda": col - mesmo_piso(col, lb, -1),
                                             "direita": mesmo_piso(col, lb, 1) - col}
        por(cpl, lb)
        d = 1 if lado < 0 else -1
        alc = constants.GOLPE_ALCANCE

        def perto():
            dx = (e.rect.left - M.player.rect.right) if d > 0 else (M.player.rect.left - e.rect.right)
            return dx <= alc * 0.8
        hits = {"n": 0}
        n = 0
        for i in range(700):
            if e.derrotado:
                break
            if perto():
                quadros(1, d=0, golpear=lambda k: True)
            else:
                quadros(1, d=d)
            n += 1
        r["derrota"] = {"derrotado": e.derrotado, "quadros": n, "dano": dano()}
    # ── 4. esquiva: atravessar o inimigo andando e pulando, sem derrotar
    novo()
    e = inimigo_por_col(tipo, col)
    base_col = int(e.ancora_x) // T if nome == "Aranha" else col
    lb0 = chao(base_col, (int(e.altura_inicial) // T + 1) if nome == "Aranha" else int(e.rect.bottom // T) - 3)
    melhor = None
    if lb0:
        estrategias = ("andar", "pular_perto", "pulo_duplo_perto") + (("isca",) if nome == "Aranha" else ())
        for estrategia in estrategias:
            for ini in (base_col - 6, base_col + 6):
                if not (0 < ini < M.setor_atual.world.colunas - 1):
                    continue
                lbi = chao(ini, lb0 - 3)
                if lbi is None or abs(lbi - lb0) > 2:
                    continue
                novo(); e = inimigo_por_col(tipo, col)
                por(ini, lbi)
                d = 1 if ini < base_col else -1
                alvo_x = (base_col + 4 * d) * T

                def passou():
                    return (M.player.rect.centerx - alvo_x) * d > 0
                if estrategia == "andar":
                    pul = ()
                else:
                    # pula quando estiver a ~2,5 tiles do inimigo
                    dist0 = abs(ini - base_col) * T - int(2.5 * T)
                    q = max(0, int(dist0 / constants.PLAYER_SPEED))
                    pul = (q, q + 14) if estrategia == "pulo_duplo_perto" else (q,)
                if estrategia == "isca":
                    # anda até o gatilho; quando ela começa a descer, recua; quando ela
                    # bate no chão e começa a subir, atravessa correndo
                    n = 0
                    fase = "ir"
                    for _ in range(900):
                        n += 1
                        if fase == "ir":
                            quadros(1, d=d)
                            if e.estado == "DESCENDO":
                                fase = "recuar"
                        elif fase == "recuar":
                            quadros(1, d=-d)
                            if e.estado in ("SUBINDO", "ESPERA") and not M.player.preso:
                                fase = "passar"
                        else:
                            quadros(1, d=d)
                            if passou():
                                break
                else:
                    n = quadros(600, d=d, pular=pul, parar=passou)
                ok = passou() and dano() == 0
                tent = {"estrategia": estrategia, "de_col": ini, "passou": passou(),
                        "dano": dano(), "preso": bool(M.player.preso), "quadros": n}
                if ok and melhor is None:
                    melhor = tent
                r.setdefault("esquiva_tentativas", []).append(tent)
    r["esquiva_sem_dano"] = melhor
    res.append(r)
    at = r.get("ataque") or {}
    dr = r.get("derrota") or {}
    es = r.get("esquiva_sem_dano")
    print(f"{nome} (col {col}): patrulha {r.get('patrulha_colunas', '-')}"
          f" | ataque: {'acerta' if at.get('acertou') or at.get('prendeu') else 'NAO ataca'}"
          f"{' (desce %s px)' % at.get('desceu_px') if 'desceu_px' in at else ''}"
          f" | golpe J: {'derrota' if dr.get('derrotado') else 'nao derrota'}"
          f"{' com %s de dano' % dr.get('dano') if dr.get('derrotado') and dr.get('dano') else ''}"
          f" | esquiva sem dano: {es['estrategia'] if es else 'NAO encontrada'}", flush=True)

if SAIDA:
    json.dump(res, open(SAIDA, "w"), indent=1, ensure_ascii=False)
