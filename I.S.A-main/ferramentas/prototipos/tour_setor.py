"""Loop REAL do main.py (runpy) numa janela X11 960x600 + diretor em pygame.event.get.
Entra na caverna pela passagem real da floresta (E), percorre as 4 regiões
(teleporte só para enquadrar), mede FPS real andando e sai pela passagem 32."""
import os, sys, subprocess, runpy, json, time
RAIZ, PREF = sys.argv[1], sys.argv[2]
EVID = os.environ.get("EVID", "/home/claude/cav04/ev/capturas"); os.makedirs(EVID, exist_ok=True)
os.environ.setdefault("DISPLAY", ":99"); os.environ["SDL_AUDIODRIVER"] = "dummy"
import tempfile
os.environ["ISA_DB"] = os.path.join(tempfile.mkdtemp(prefix="isa_tourc_"), "estat.db")
sys.path.insert(0, RAIZ); os.chdir(RAIZ); sys.path.insert(0, "/home/claude/scripts")
import pygame, xdrv
xdrv.EVID = EVID
_get_real = pygame.event.get
LOG = []
def log(*a):
    s = " ".join(str(x) for x in a); LOG.append(s); print("[tour]", s, flush=True)
def K(k, down=True):
    return pygame.event.Event(pygame.KEYDOWN if down else pygame.KEYUP, key=k, mod=0, unicode="", scancode=0)
G = None
FPS = {}
_tempos = []
def shot(nome):
    if os.environ.get("SEM_CAPTURA"): return
    p = xdrv.shot(f"{PREF}_{nome}"); log("captura", os.path.basename(p))

REGIOES = json.loads(os.environ["REGIOES"]) if os.environ.get("REGIOES") else [
    ("1_Fenda_de_Entrada", [(18, "inicio"), (31, "aranha"), (49, "cobra")]),
    ("2_Mina_Abandonada", [(62, "minerios"), (81, "aranha"), (98, "cobra_na_viga")]),
    ("3_Coracao_de_Cristal", [(131, "cristais"), (147, "tucano"), (164, "desvio_pulo_duplo"), (178, "cobra")]),
    ("4_Galeria_de_Retorno", [(205, "minerios"), (229, "aranha_e_saida")]),
]

def diretor():
    from src.nucleo import constants
    T = constants.TILE_SIZE; S = constants.SOLID_TILES
    def esperar(n):
        for _ in range(n): yield []
    def esperar_estado(est, lim=900):
        for _ in range(lim):
            if G["estado_jogo"] == est: return
            yield []
        raise AssertionError(f"estado {est} nao atingido ({G['estado_jogo']})")
    def resolver_quiz():
        for _ in range(400):
            if G["estado_jogo"] == "QUIZ":
                letra = G["pergunta_em_jogo"]().get("resposta", "a").strip().lower()
                yield [K(getattr(pygame, f"K_{letra}")), K(getattr(pygame, f"K_{letra}"), False)]
                continue
            if G["estado_jogo"] == "JOGANDO": return
            yield []
    def chao(col, ini=10):
        g = G["setor_atual"].grade
        for l in range(max(1, ini), len(g)):
            if g[l][col] in S and g[l-1][col] not in S: return l
    def teleportar(col, ini=10):
        p = G["player"]; l = chao(col, ini)
        p.rect.centerx = col * T + T // 2; p.rect.bottom = l * T
        p.pos_x, p.pos_y = float(p.rect.x), float(p.rect.y); p.vel_y = 0
        G["atualizar_camera"](instantaneo=True)
    def usar(destino):
        yield from resolver_quiz()
        pas = next(p for p in G["passagens_cenario"].itens if p.destino["setor"] == destino)
        p = G["player"]; p.rect.midbottom = pas.rect.midbottom
        p.pos_x, p.pos_y = float(p.rect.x), float(p.rect.y); p.vel_y = 0
        G["atualizar_camera"](instantaneo=True)
        yield from esperar(25); yield from resolver_quiz()
        shot(f"portal_{G['setor_atual'].nome}_para_{destino}")
        yield [K(pygame.K_e), K(pygame.K_e, False)]
        yield from esperar(1)
        ativo = G["transicao"].ativa
        for _ in range(240):
            if not G["transicao"].ativa: break
            yield []
        yield from esperar(45)
        log(f"passagem -> {destino}: fade={'sim' if ativo else 'NAO'} setor={G['setor_atual'].nome} "
            f"no_chao={G['player'].on_ground} vivo={G['player'].alive} pos_col={G['player'].rect.centerx // T}")
    # menu -> login -> cutscene -> jogo
    yield from esperar(30)
    yield [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(480, 530)),
           pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(480, 530))]
    yield from esperar_estado("LOGIN"); yield from esperar(5)
    for ch in "caverna": yield [pygame.event.Event(pygame.TEXTINPUT, text=ch)]
    yield [K(pygame.K_RETURN), K(pygame.K_RETURN, False)]
    yield from esperar_estado("CUTSCENE"); yield from esperar(10)
    yield [K(pygame.K_ESCAPE), K(pygame.K_ESCAPE, False)]
    yield from esperar_estado("JOGANDO"); yield from esperar(40)
    log("janela", xdrv.janela())
    SETOR = os.environ.get("SETOR", "caverna")
    ROTA = {"floresta": [], "caverna": ["caverna"], "copas": ["copas"], "arena": ["copas", "arena"]}[SETOR]
    VOLTA = {"floresta": [], "caverna": ["floresta"], "copas": ["floresta"], "arena": ["copas", "floresta"]}[SETOR]
    if SETOR == "floresta":
        shot("floresta_spawn")
    for dest in ROTA:
        yield from usar(dest)
        shot(f"{dest}_chegada")
    for regiao, pontos in REGIOES:
        for ponto in pontos:
            col, rot = ponto[0], ponto[1]; ini = ponto[2] if len(ponto) > 2 else 10
            G["player"].player_health = 80
            if rot.startswith("aviso"):
                # chega andando de 4 tiles antes da aranha e fotografa o aviso
                lado = -1 if rot.endswith("direita") else 1
                teleportar(col - 4 * lado, ini); yield from esperar(30); yield from resolver_quiz()
                ar = min((e for e in G["enemies"] if type(e).__name__ == "Aranha"), key=lambda e: abs(e.ancora_x - col * T))
                tecla = pygame.K_d if lado > 0 else pygame.K_a
                yield [K(tecla)]
                t0 = 0
                while ar.estado != "AVISO" and t0 < 240:
                    t0 += 1; yield []
                yield [K(tecla, False)]
                yield from esperar(6); shot(f"{regiao}_col{col}_{rot}_1_aviso")
                log(f"{regiao}: aviso estado {ar.estado}")
                t0 = 0
                while ar.estado not in ("DESCENDO",) and t0 < 60:
                    t0 += 1; yield []
                yield from esperar(5); shot(f"{regiao}_col{col}_{rot}_2_descida")
                t0 = 0
                while ar.estado != "SUBINDO" and t0 < 120:
                    t0 += 1; yield []
                yield from esperar(20); shot(f"{regiao}_col{col}_{rot}_3_subindo")
                log(f"{regiao}: depois do aviso, preso={G['player'].preso} vida={G['player'].player_health}")
                continue
            teleportar(col, ini)
            yield from esperar(50); yield from resolver_quiz(); yield from esperar(8)
            if rot.startswith("aranha"):
                ar = min((e for e in G["enemies"] if type(e).__name__ == "Aranha"),
                         key=lambda e: abs(e.ancora_x - col * T))
                t0 = 0
                while ar.estado not in ("DESCENDO", "PRENDENDO") and t0 < 240:
                    t0 += 1; yield []
                yield from esperar(6)
                log(f"{regiao}: aranha col {int(ar.ancora_x)//T} estado {ar.estado} (Areninha presa={G['player'].preso})")
            if rot == "tucano":
                tu = next(e for e in G["enemies"] if type(e).__name__ == "Tucano")
                t0 = 0
                while tu.estado != "MERGULHO" and t0 < 300:
                    t0 += 1; yield []
                yield from esperar(10)
                log(f"{regiao}: tucano estado {tu.estado}")
            shot(f"{regiao}_col{col}_{rot}")
        # FPS: anda 3 s para a direita no meio da região
        meio = pontos[0][0]
        if os.environ.get("SEM_FPS"): continue
        teleportar(meio); yield from esperar(20)
        _tempos.clear()
        yield [K(pygame.K_d)]
        for _ in range(int(os.environ.get("QUADROS_FPS", "180"))): yield []
        yield [K(pygame.K_d, False)]
        ts = sorted(_tempos[5:])
        if ts:
            med = sum(ts) / len(ts)
            FPS[regiao] = {"fps_medio": round(1000 / med, 1), "fps_min": round(1000 / ts[-1], 1),
                           "fps_p5": round(1000 / ts[int(len(ts) * 0.95)], 1), "quadros_lentos_33ms": sum(t > 33.4 for t in ts),
                           "ms_medio": round(med, 2), "ms_max": round(ts[-1], 2), "quadros": len(ts)}
            log(f"{regiao}: FPS medio {FPS[regiao]['fps_medio']} p5 {FPS[regiao]['fps_p5']} min {FPS[regiao]['fps_min']} lentos {FPS[regiao]['quadros_lentos_33ms']}")
        yield from resolver_quiz()
    for dest in VOLTA:
        yield from usar(dest)
        shot(f"{dest}_chegada_na_volta")
    if SETOR == "floresta" and os.environ.get("TESTAR_PASSAGENS"):
        for ida, volta in (("caverna", "floresta"), ("copas", "floresta")):
            yield from usar(ida); shot(f"{ida}_chegada"); yield from usar(volta); shot(f"floresta_chegada_vindo_de_{ida}")
    json.dump({"log": LOG, "fps": FPS}, open(os.path.join(EVID, f"{PREF}_log.json"), "w"), indent=1, ensure_ascii=False)
    log("FIM")
    while True: yield [pygame.event.Event(pygame.QUIT)]

_dir = None; _ult = [None]
def get_patch(*a, **k):
    global G, _dir
    agora = time.perf_counter()
    if _ult[0] is not None: _tempos.append((agora - _ult[0]) * 1000)
    G = sys._getframe(1).f_globals
    if _dir is None: _dir = diretor()
    reais = _get_real(*a, **k)
    try:
        extras = next(_dir)
    except Exception as e:
        import traceback; traceback.print_exc(); log("ERRO NO DIRETOR:", repr(e))
        json.dump({"log": LOG, "fps": FPS}, open(os.path.join(EVID, f"{PREF}_log.json"), "w"), indent=1, ensure_ascii=False)
        extras = [pygame.event.Event(pygame.QUIT)]
    _ult[0] = time.perf_counter()   # não conta o tempo das capturas
    return reais + extras
pygame.event.get = get_patch
runpy.run_path(os.path.join(RAIZ, "main.py"), run_name="__main__")
