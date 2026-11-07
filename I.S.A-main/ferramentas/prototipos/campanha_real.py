"""
# COPIA DE REFERENCIA dos scripts de teste real usados na integracao (rodam fora do jogo, via Xvfb).
Travessia REAL da caverna no loop do main.py (janela X11 960x600):
floresta -> passagem 30 (E) -> chegada 40 -> ... -> passagem 32 (ida),
depois volta até a chegada 40 (volta) e sai de novo pela passagem 32.

Dentro da caverna NÃO há teleporte: um piloto planeja a rota com a física
real (ferramentas/fisica_nivel.py) a partir do estado EXATO da Areninha e a
executa como teclas (A/D/Espaço/J/E) injetadas no pygame.event.get do jogo,
quadro a quadro. Inimigos ativos, vida real, quizzes respondidos pelo teclado.
Se algo desviar o plano (dano, empurrão, aranha, quiz), o piloto espera ela
pousar e replaneja a partir de onde ela está.
uso: python travessia_real.py RAIZ PREFIXO
"""
import os, sys, runpy, json, time
RAIZ, PREF = sys.argv[1], sys.argv[2]
EVID = os.environ.get("EVID", "/home/claude/final/campanha"); os.makedirs(EVID, exist_ok=True)
os.environ.setdefault("DISPLAY", ":99"); os.environ["SDL_AUDIODRIVER"] = "dummy"
import tempfile
os.environ["ISA_DB"] = os.path.join(tempfile.mkdtemp(prefix="isa_trav_"), "estat.db")
print("ISA_DB", os.environ["ISA_DB"], flush=True)
sys.path.insert(0, RAIZ); os.chdir(RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "ferramentas")); sys.path.insert(0, "/home/claude/scripts")
import pygame, xdrv
xdrv.EVID = EVID
_get_real = pygame.event.get
LOG, EVENTOS, AMOSTRAS = [], [], []
G = None
_tempos = []

def log(*a):
    s = " ".join(str(x) for x in a); LOG.append(s); print("[trav]", s, flush=True)
def K(k, down=True):
    return pygame.event.Event(pygame.KEYDOWN if down else pygame.KEYUP, key=k, mod=0, unicode="", scancode=0)
def shot(nome):
    p = xdrv.shot(f"{PREF}_{nome}"); EVENTOS.append(("captura", os.path.basename(p)))


def diretor():
    from src.nucleo import constants
    import ferramentas.fisica.fisica_nivel as F
    import ferramentas.validacao.validar_fisica_real as V
    T = constants.TILE_SIZE
    estado = {"dir": 0, "quadro": 0, "replans": 0, "golpes": 0}

    def esperar(n):
        for _ in range(n):
            yield []
    def esperar_estado(est, lim=900):
        for _ in range(lim):
            if G["estado_jogo"] == est: return
            yield []
        raise AssertionError(f"estado {est} nao atingido ({G['estado_jogo']})")

    def responder_quiz():
        perg = G["pergunta_em_jogo"]()
        letra = perg.get("resposta", "a").strip().lower()
        EVENTOS.append(("quiz", estado["quadro"], letra, G["player"].rect.centerx // T))
        return [K(getattr(pygame, f"K_{letra}")), K(getattr(pygame, f"K_{letra}"), False)]

    def tick(eventos):
        """Um quadro do jogo: amostra o estado e devolve eventos (resolve quiz/feedback)."""
        p = G["player"]
        estado["quadro"] += 1
        if estado["quadro"] % 6 == 0:
            AMOSTRAS.append((estado["quadro"], p.rect.centerx, p.rect.bottom, p.player_health,
                             G["estado_jogo"], bool(getattr(p, "preso", False))))
        return eventos

    def direcao(d):
        evs = []
        if d != estado["dir"]:
            if estado["dir"] == 1: evs.append(K(pygame.K_d, False))
            if estado["dir"] == -1: evs.append(K(pygame.K_a, False))
            if d == 1: evs.append(K(pygame.K_d))
            if d == -1: evs.append(K(pygame.K_a))
            estado["dir"] = d
        return evs

    def reflexo_golpe():
        """Aperta J se uma cobra/tucano estiver ao alcance da asa, à frente."""
        p = G["player"]
        alc = constants.GOLPE_ALCANCE
        for e in G["enemies"]:
            n = type(e).__name__
            if n not in ("Enemy", "Tucano") or e.derrotado or getattr(e, "atordoado_por_golpe", False):
                continue
            frente = -1 if p.flip else 1
            dx = (e.rect.left - p.rect.right) if frente > 0 else (p.rect.left - e.rect.right)
            if -10 <= dx <= alc * 0.9 and e.rect.bottom > p.rect.top - 20 and e.rect.top < p.rect.bottom + 20:
                estado["golpes"] += 1
                return [K(pygame.K_j), K(pygame.K_j, False)]
        return []

    def interrompido():
        return G["estado_jogo"] != "JOGANDO" or getattr(G["player"], "preso", False)

    def estabilizar():
        """Solta as teclas, resolve quiz, espera pousar e sair de prisão."""
        yield tick(direcao(0))
        for _ in range(900):
            est = G["estado_jogo"]
            if est == "QUIZ":
                yield tick(responder_quiz()); continue
            if est == "GAME_OVER":
                return False
            p = G["player"]
            if est == "JOGANDO" and not getattr(p, "preso", False) and p.on_ground and abs(p.vel_y) < 1:
                # dois quadros no chão seguidos (on_ground pisca a cada quadro)
                yield tick([])
                if G["player"].on_ground or abs(G["player"].vel_y) < 0.5:
                    return True
                continue
            yield tick([])
        return G["estado_jogo"] == "JOGANDO"

    def estado_sim():
        p = G["player"]
        return (p.pos_x, p.pos_y, p.rect.x, p.rect.y, 0.0, p.MAX_JUMPS, True)

    CTX = {}
    def preparar(nome):
        d = V.montar_setor(nome)
        CTX.update(nome=nome, d=d, grade=d["grade"], sim=F.Simulador(d["grade"]))
        log(f"setor {nome}: planejador preparado")

    def planejar(alvo):
        t0 = time.time()
        e0 = estado_sim()
        g = F.explorar(CTX['grade'], [e0], [alvo], processos=1)
        rota = F.rota_natural(g, [F.chave(e0)], 0)
        estado["replans"] += 1
        log(f"plano #{estado['replans']} de col {G['player'].rect.centerx // T}: "
            f"{len(rota) if rota else 'SEM ROTA'} movimentos ({time.time() - t0:.1f} s)")
        if not rota:
            return None
        # alvos: a sequência de nós (chave) e a macro planejada para cada passo
        passos = []
        for i, (k, mi) in enumerate(rota):
            prox = rota[i + 1][0] if i + 1 < len(rota) else None
            passos.append((k, mi, prox))
        return passos, g

    def quadros_da_macro(m, e_ini):
        """Reproduz a mesma sequência de entradas de Simulador.simular (para a execução real)."""
        sim = CTX["sim"]
        sim.restaurar(e_ini)
        fim, _, _ = sim.simular(e_ini, m)
        n = sim.quadros
        tipo, dd, J, s, d2 = m
        seq = []
        sim.restaurar(e_ini)
        p = sim.p
        t_ar = None
        for f in range(n):
            if tipo == "pulo":
                ref = f
            else:
                if t_ar is None and not p.on_ground and f > 0:
                    t_ar = f
                ref = None if t_ar is None else f - t_ar
            di = dd if (s is None or ref is None or ref < s) else d2
            pul = ref is not None and ref in J
            seq.append((di, pul))
            sim.passo(di, pul)
        return seq, fim

    def escolher_macro(e_atual, k_dest, mi_plan):
        """A macro planejada, se do estado ATUAL ela chega no nó planejado; senão outra que chegue."""
        sim = CTX["sim"]
        ordem = [mi_plan] + [i for i in range(len(F.MACROS)) if i != mi_plan]
        for mi in ordem:
            fim, _, _ = sim.simular(e_atual, F.MACROS[mi])
            if k_dest is None or (fim is not None and F.chave(fim) == k_dest):
                return mi
        return None

    def executar(seq):
        """Executa a sequência (dir, pulo) como teclas. False se algo interrompeu."""
        for di, pul in seq:
            if interrompido():
                return False
            evs = direcao(di)
            if pul:
                evs += [K(pygame.K_SPACE), K(pygame.K_SPACE, False)]
            evs += reflexo_golpe()
            yield tick(evs)
        return True

    def pousada_exata():
        p = G["player"]
        return p.on_ground and p.vel_y == 0 and G["estado_jogo"] == "JOGANDO" and not getattr(p, "preso", False)

    def ir_ate(alvo, nome, chegou):
        hp0 = G["player"].player_health
        q0 = estado["quadro"]
        g = None
        falhas = 0
        while not chegou():
            ok = yield from estabilizar()
            if not ok:
                log(f"{nome}: GAME OVER em col {G['player'].rect.centerx // T}"); return False
            if chegou(): break
            for _ in range(4):
                if pousada_exata(): break
                yield tick([])
            if not pousada_exata():
                continue
            e_at = estado_sim()
            k = F.chave(e_at)
            if g is None or k not in g.nos:
                plano = planejar(alvo)
                if plano is None: return False
                _, g = plano
            rota = F.rota_natural(g, [k], 0)
            if not rota:
                g = None; falhas += 1
                if falhas > 15: log(f"{nome}: sem rota"); return False
                continue
            k0, mi = rota[0]
            prox = rota[1][0] if len(rota) > 1 else None
            mi2 = escolher_macro(e_at, prox, mi)
            if mi2 is None:
                falhas += 1
                if falhas > 15: log(f"{nome}: macro nao reproduz"); return False
                g = None
                continue
            seq, _ = quadros_da_macro(F.MACROS[mi2], e_at)
            yield from executar(seq)
        yield tick(direcao(0))
        log(f"{nome}: chegou em {estado['quadro'] - q0} quadros ({(estado['quadro'] - q0) / 60:.1f} s de jogo), "
            f"vida {hp0} -> {G['player'].player_health}, exploracoes {estado['replans']}")
        return True

    # ── menu -> login -> cutscene -> floresta ────────────────────────────
    yield from esperar(30)
    yield [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(480, 530)),
           pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(480, 530))]
    yield from esperar_estado("LOGIN"); yield from esperar(5)
    for ch in "travessia": yield [pygame.event.Event(pygame.TEXTINPUT, text=ch)]
    yield [K(pygame.K_RETURN), K(pygame.K_RETURN, False)]
    yield from esperar_estado("CUTSCENE"); yield from esperar(10)
    yield [K(pygame.K_ESCAPE), K(pygame.K_ESCAPE, False)]
    yield from esperar_estado("JOGANDO"); yield from esperar(40)
    log("janela", xdrv.janela(), "vida inicial", G["player"].player_health)
    COLETA = {}
    def coletar(nome):
        """Coleta TODOS os minérios restantes do setor atual, sem teleporte."""
        setor = G["setor_atual"]
        total0 = len(setor.itens)
        hp0 = G["player"].player_health
        g = None; alvos_g = []; falhas = 0; q0 = estado["quadro"]
        inalcancaveis = set()
        while True:
            restantes = [it for it in setor.itens if id(it) not in inalcancaveis]
            if not restantes:
                break
            ok = yield from estabilizar()
            if not ok:
                log(f"{nome}: GAME OVER em col {G['player'].rect.centerx // T}"); return False
            for _ in range(4):
                if pousada_exata(): break
                yield tick([])
            if not pousada_exata():
                continue
            e_at = estado_sim(); k = F.chave(e_at)
            ids = {id(it) for it in restantes}
            if g is None or k not in g.nos or not any(id(it) in ids for it in alvos_g):
                alvos_g = list(restantes)
                t0 = time.time()
                g = F.explorar(CTX["grade"], [e_at], [it.rect for it in alvos_g], processos=1)
                estado["replans"] += 1
                log(f"plano-coleta #{estado['replans']} de col {G['player'].rect.centerx // T}: {len(alvos_g)} minerio(s) restantes ({time.time() - t0:.1f} s)")
            melhor = None
            for j, it in enumerate(alvos_g):
                if id(it) not in ids: continue
                rota = F.rota_natural(g, [k], j)
                if rota is not None and (melhor is None or len(rota) < len(melhor[1])):
                    melhor = (j, rota)
            if melhor is None:
                falhas += 1
                if falhas > 3:
                    for it in restantes: inalcancaveis.add(id(it))
                    log(f"{nome}: {len(restantes)} minerio(s) sem rota: {[(it.rect.centerx // T, it.rect.centery // T) for it in restantes]}")
                    break
                g = None; continue
            j, rota = melhor
            if not rota:
                # O nó "toca" o minério, mas os nós agrupam posições de 12 px: a posição real
                # pode ficar uns pixels antes. Anda até ele (e pula, se precisar).
                it = alvos_g[j]; p = G["player"]
                cut = COLETA.setdefault("_cutucadas", {}); cut[id(it)] = cut.get(id(it), 0) + 1
                if cut[id(it)] > 6:
                    inalcancaveis.add(id(it)); log(f"{nome}: minerio em {(it.rect.centerx // T, it.rect.centery // T)} nao coletado"); continue
                d = 1 if it.rect.centerx > p.rect.centerx else -1
                for f in range(14):
                    if it not in setor.itens or interrompido(): break
                    evs = direcao(d)
                    if f == 7 and cut[id(it)] > 2: evs += [K(pygame.K_SPACE), K(pygame.K_SPACE, False)]
                    yield tick(evs)
                yield tick(direcao(0))
                g = None if cut[id(it)] > 1 else g
                continue
            k0, mi = rota[0]
            prox = rota[1][0] if len(rota) > 1 else None
            mi2 = escolher_macro(e_at, prox, mi)
            if mi2 is None:
                falhas += 1; g = None
                if falhas > 30: log(f"{nome}: macro nao reproduz"); return False
                continue
            seq, _ = quadros_da_macro(F.MACROS[mi2], e_at)
            yield from executar(seq)
        yield tick(direcao(0))
        yield from estabilizar()
        COLETA.pop("_cutucadas", None)
        COLETA[setor.nome] = {"no_inicio": total0, "coletados": total0 - len(setor.itens),
                              "restantes": len(setor.itens), "quadros": estado["quadro"] - q0}
        log(f"{nome}: coletou {total0 - len(setor.itens)}/{total0} minerios em {(estado['quadro'] - q0) / 60:.0f} s de jogo, "
            f"vida {hp0} -> {G['player'].player_health}")
        return len(setor.itens) == 0

    def clicar(pos):
        return [pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0)),
                pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos),
                pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos)]

    LUTA = {"capturas": [], "bananas_esquivadas": 0, "ondas_puladas": 0, "minerios_devolvidos": 0,
            "dano_banana_ou_onda": 0, "vida_boss": [], "pdf": None, "resultado_db": None}

    def lutar_boss(nome):
        """Luta REAL contra o Gorila: só teclas (A/D/Espaço) e respostas do quiz.
        Desvia das bananas (sai do ponto de queda marcado no chão), deixa o minério acertar,
        responde certo, pula as ondas de choque. Fotografa cada fase."""
        T_ = T
        fotos = set()
        def foto(chave, txt):
            if chave not in fotos:
                fotos.add(chave); shot(f"boss_{len(fotos):02d}_{txt}"); LUTA["capturas"].append(txt)
        esquivando = {"ate": 0, "dir": 0}
        vida_boss_ant = None
        trava = {"x": None, "n": 0}
        def destravar(dirx):
            """Pula sozinha quando anda e não sai do lugar (degrau)."""
            p = G["player"]
            if dirx and trava["x"] == p.rect.x:
                trava["n"] += 1
            else:
                trava["n"] = 0
            trava["x"] = p.rect.x
            if trava["n"] >= 3:
                trava["n"] = 0
                return [K(pygame.K_SPACE), K(pygame.K_SPACE, False)]
            return []
        for f in range(60 * 600):
            est = G["estado_jogo"]
            if est == "VITORIA":
                yield tick(direcao(0)); yield from esperar(40); foto("vitoria", "tela_vitoria")
                return True
            if est == "GAME_OVER":
                foto("gameover", "game_over"); return False
            if est == "QUIZ":
                foto(f"quiz{LUTA['minerios_devolvidos']}", f"quiz_do_boss_{LUTA['minerios_devolvidos'] + 1}")
                yield tick(responder_quiz()); LUTA["minerios_devolvidos"] += 1; continue
            if est != "JOGANDO":
                yield tick([]); continue
            b = G.get("boss"); p = G["player"]
            if b is None:
                yield tick(direcao(0)); continue
            if vida_boss_ant != b.vida:
                LUTA["vida_boss"].append((estado["quadro"], b.vida)); vida_boss_ant = b.vida
            evs = []
            if not b.ativo:
                evs += direcao(1) + destravar(1)
                if estado["quadro"] % 30 == 0: foto("entrada", "entrando_na_area_de_luta")
                yield tick(evs); continue
            if b.estado == "INTRO": foto("intro", "aparicao_do_gorila")
            if b.estado == "ATORDOADO": foto(f"atord{LUTA['minerios_devolvidos']}", f"gorila_atordoado_{LUTA['minerios_devolvidos']}")
            if b.estado == "DERROTA": foto("derrota", "derrota_do_gorila")
            if b.preparando:
                foto("pose_minerio" if b.preparando[0] else "pose_banana",
                     "pose_arremesso_minerio" if b.preparando[0] else "pose_arremesso_banana")
            if b.fase == 2: foto("fase2", "fase_2")
            if b.pancada and b.pancada["etapa"] == "aviso": foto("pancada", "aviso_salto_pancada")
            if b.ondas: foto("ondas", "ondas_de_choque")
            # ── decisão ──
            dirx = 0; pular = False
            agora_q = estado["quadro"]
            for pr in b.projeteis:
                if (not pr.eh_minerio and pr.estado == "voando" and pr.alvo_x is not None
                        and abs(pr.alvo_x - p.rect.centerx) < 90 and agora_q >= esquivando["ate"]):
                    lado = -1 if pr.alvo_x >= p.rect.centerx else 1
                    area = G["area_boss"]["rect"]
                    if lado < 0 and p.rect.left - 3 * T_ < area.left: lado = 1
                    if lado > 0 and b.rect.left - p.rect.right < 3 * T_: lado = -1
                    esquivando.update(ate=agora_q + 40, dir=lado); LUTA["bananas_esquivadas"] += 1
            if agora_q < esquivando["ate"]:
                dirx = esquivando["dir"]
            else:
                # volta para uma posição de espera: 6 tiles à esquerda do Gorila
                alvo = b.rect.left - 6 * T_
                if p.rect.centerx < alvo - T_: dirx = 1
                elif p.rect.centerx > alvo + T_: dirx = -1
            for o in b.ondas:
                dx = o.rect.centerx - p.rect.centerx
                if abs(dx) < 110 and dx * o.direcao < 0 and p.on_ground:
                    pular = True
            evs += direcao(dirx) + destravar(dirx)
            if pular:
                evs += [K(pygame.K_SPACE), K(pygame.K_SPACE, False)]; LUTA["ondas_puladas"] += 1
            yield tick(evs)
        return False

    def depois_da_vitoria():
        """RELATÓRIO -> gera PDF -> volta ao menu."""
        bv = G["botoes_vitoria"][0]
        yield clicar(bv.rect.center); yield from esperar(40)
        log(f"tela apos RELATORIO: {G['estado_jogo']}")
        shot("pos_01_relatorio")
        te = G.get("tela_estatisticas")
        if te is not None:
            yield clicar(te.btn_pdf_rect.center); yield from esperar(40)
            LUTA["pdf"] = G.get("pdf_estatisticas_atual")
            log(f"PDF: {LUTA['pdf']} existe={bool(LUTA['pdf']) and os.path.exists(LUTA['pdf'])}")
            shot("pos_02_pdf_gerado")
            if LUTA["pdf"] and os.path.exists(LUTA["pdf"]):
                import shutil; shutil.copy(LUTA["pdf"], os.path.join(EVID, f"{PREF}_relatorio.pdf"))
        try:
            import sqlite3
            con = sqlite3.connect(os.environ["ISA_DB"])
            tabs = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
            LUTA["resultado_db"] = {t: con.execute(f"select count(*) from {t}").fetchone()[0] for t in tabs}
            for t in tabs:
                cols = [r[1] for r in con.execute(f"pragma table_info({t})")]
                if "resultado" in cols:
                    LUTA["resultado_db"]["ultimo_resultado"] = con.execute(f"select resultado from {t} order by rowid desc limit 1").fetchone()
            con.close()
        except Exception as e:  # noqa
            LUTA["resultado_db"] = repr(e)
        log(f"SQLite: {LUTA['resultado_db']}")
        yield [K(pygame.K_ESCAPE), K(pygame.K_ESCAPE, False)]; yield from esperar(40)
        log(f"depois do ESC: {G['estado_jogo']}"); shot("pos_03_menu")

    ROTEIRO = [x for x in os.environ.get("ROTEIRO", "ir:copas,ir:caverna").split(",") if x]
    for destino_ini in [x for x in os.environ.get("INICIO", "").split(">") if x]:
        # começa no portal que leva ao setor testado (teleporte só FORA do setor testado)
        pas = next(p for p in G["passagens_cenario"].itens if p.destino["setor"] == destino_ini)
        p = G["player"]; p.rect.midbottom = pas.rect.midbottom
        p.pos_x, p.pos_y = float(p.rect.x), float(p.rect.y); p.vel_y = 0
        G["atualizar_camera"](instantaneo=True)
        yield from esperar(30)
        yield [K(pygame.K_e), K(pygame.K_e, False)]
        for _ in range(300):
            if G["setor_atual"].nome == destino_ini and not G["transicao"].ativa: break
            yield []
        yield from esperar(30)
        log(f"inicio no setor {G['setor_atual'].nome}, col {G['player'].rect.centerx // T}")
    trechos = []
    preparar(G["setor_atual"].nome)
    shot(f"00_{G['setor_atual'].nome}_inicio")
    for n, passo in enumerate(ROTEIRO, 1):
        acao, _, arg = passo.partition(":")
        nome = f"{n:02d}_{G['setor_atual'].nome}_{passo.replace(':', '_')}"
        hp0 = G["player"].player_health; q0 = estado["quadro"]; golpes0 = estado["golpes"]
        _tempos.clear()
        if acao == "ir":
            pas = next(p for p in CTX["d"]["passagens"] if p.destino["setor"] == arg)
            zona = pas.rect_interacao
            alvo = pygame.Rect(zona.x, pas.linha * T + T // 2, zona.w, T // 2)
            ok = yield from ir_ate(alvo, nome, lambda: pas.alcancavel_por(G["player"].rect) and G["player"].on_ground)
        elif acao == "chegada":
            c, l = CTX["d"]["marcadores"]["chegadas"][int(arg)]
            alvo = pygame.Rect((c - 1) * T, l * T + T // 2, 3 * T, T // 2)
            ok = yield from ir_ate(alvo, nome, lambda: alvo.colliderect(G["player"].rect) and G["player"].on_ground)
        elif acao == "entrar":
            antes = G["setor_atual"].nome
            yield tick(direcao(0)); yield from esperar(5)
            yield [K(pygame.K_e), K(pygame.K_e, False)]
            for _ in range(300):
                if G["setor_atual"].nome != antes and not G["transicao"].ativa: break
                yield []
            yield from esperar(30)
            ok = G["setor_atual"].nome != antes
            log(f"{nome}: {antes} -> {G['setor_atual'].nome}, col {G['player'].rect.centerx // T}, vida {G['player'].player_health}")
            if ok: preparar(G["setor_atual"].nome)
        elif acao == "coletar":
            ok = yield from coletar(nome)
        elif acao == "boss":
            ok = yield from lutar_boss(nome)
        else:
            raise ValueError(passo)
        shot(nome)
        trechos.append({"passo": passo, "setor": CTX["nome"], "ok": ok, "vida_inicio": hp0,
                        "vida_fim": G["player"].player_health if G.get("player") else None, "quadros": estado["quadro"] - q0,
                        "golpes_dados": estado["golpes"] - golpes0, "fps": None, "_t": list(_tempos)})
        if acao == "boss" and ok:
            yield from depois_da_vitoria()
        if not ok:
            log(f"PAROU em {nome}"); break

    def fps(ts):
        ts = sorted(ts[5:]) if len(ts) > 10 else ts
        if not ts: return None
        med = sum(ts) / len(ts)
        return {"fps_medio": round(1000 / med, 1), "fps_p5": round(1000 / ts[int(len(ts) * 0.95)], 1),
                "quadros": len(ts)}
    for t in trechos:
        t["fps"] = fps(t.pop("_t"))
    res = {"roteiro": ROTEIRO, "completo": len(trechos) == len(ROTEIRO) and all(t["ok"] for t in trechos),
           "trechos": trechos, "replanejamentos": estado["replans"], "golpes": estado["golpes"],
           "vida_final": G["player"].player_health if G.get("player") else None, "pontos": G.get("pontuacao"),
           "quizzes": [e for e in EVENTOS if e[0] == "quiz"], "luta": LUTA, "coleta": COLETA}
    log("RESULTADO", json.dumps({k: v for k, v in res.items() if k != "quizzes"}, ensure_ascii=False))
    json.dump({"resultado": res, "log": LOG, "eventos": EVENTOS, "amostras": AMOSTRAS},
              open(os.path.join(EVID, f"{PREF}_log.json"), "w"), indent=1, ensure_ascii=False)
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
        json.dump({"log": LOG, "eventos": EVENTOS, "amostras": AMOSTRAS},
                  open(os.path.join(EVID, f"{PREF}_log.json"), "w"), indent=1, ensure_ascii=False)
        extras = [pygame.event.Event(pygame.QUIT)]
    _ult[0] = time.perf_counter()   # tempo de planejamento/captura não entra no FPS
    return reais + extras
pygame.event.get = get_patch
runpy.run_path(os.path.join(RAIZ, "main.py"), run_name="__main__")
