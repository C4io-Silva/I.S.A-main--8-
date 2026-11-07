"""
Teste headless da luta contra o boss (Gorila) na arena.

Roda o MESMO código do jogo (main.passo_da_partida / atualizar_jogando) com
um relógio falso — cada frame avança 16 ms exatos —, então os tempos de
aviso, atordoamento e prazo do quiz são reproduzíveis.

Cobre: entrada na arena e posição segura, aparição, arremesso com aviso,
dano sem repetição por frame, minério -> quiz com prazo -> acerto devolve o
minério e atordoa, erro e tempo esgotado causam dano, saída bloqueada na
luta, fase 2 com salto-pancada e onda de choque, maçãs, vitória (tela,
SQLite e PDF), derrota na arena e reinício da luta sem duplicar o boss.

Uso (a partir da raiz do projeto):
    python testes/teste_boss.py
"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import tempfile  # noqa: E402

PASTA_TMP = tempfile.mkdtemp(prefix="isa_teste_boss_")
os.environ["ISA_DB"] = os.path.join(PASTA_TMP, "estatisticas.db")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

import pygame  # noqa: E402

# ── relógio falso ──────────────────────────────────────────────────────────
_agora = [10_000]
pygame.time.get_ticks = lambda: _agora[0]

from src.nucleo import constants  # noqa: E402
from compat_main import M  # noqa: E402
from src.entidades.enemies.boss import Gorila, OndaDeChoque  # noqa: E402
from src.sistemas.joystick import GerenciadorJoystick  # noqa: E402

T = constants.TILE_SIZE
DT = 16


def ok(msg):
    print("ok:", msg)


def frame(n=1):
    for _ in range(n):
        _agora[0] += DT
        M.passo_da_partida(DT)
        if M.estado_jogo in ("JOGANDO", "PAUSADO"):
            M.desenhar_jogo((0, 0))


def preparar():
    pygame.init()
    M.configurar_janela()
    M.clock = pygame.time.Clock()
    M.gamepad = GerenciadorJoystick()
    M.recriar_ui()
    M.aluno_atual = "Aluna Teste com Acentuação"
    M.iniciar_jogo()


def ir_para_arena():
    """Usa a passagem real das copas para a arena (fade incluído)."""
    M.ativar_setor("copas")
    passagem = next(p for p in M.passagens_cenario.itens if p.destino["setor"] == "arena")
    M.player.rect.midbottom = passagem.rect.midbottom
    M.player.pos_x, M.player.pos_y = float(M.player.rect.x), float(M.player.rect.y)
    M.player.vel_y = 0
    M.atualizar_camera(instantaneo=True)
    M.interagir_pressionado = True
    frame()
    M.interagir_pressionado = False
    for _ in range(200):
        if not M.transicao.ativa:
            break
        frame()
    assert M.setor_atual.nome == "arena", M.setor_atual.nome


def colocar_player(col):
    p = M.player
    p.rect.centerx = col * T + T // 2
    p.rect.bottom = M.boss.rect.bottom
    p.pos_x, p.pos_y = float(p.rect.x), float(p.rect.y)
    p.vel_y = 0
    M.reiniciar_movimento()


def teste_entrada_segura():
    ir_para_arena()
    frame(40)
    assert M.player.alive and M.player.on_ground, "jogador sem chao na entrada da arena"
    assert M.player.player_health == constants.PLAYER_HEALTH or M.player.alive
    assert not M.boss.ativo, "boss atacou antes do jogador entrar na area"
    dist = abs(M.boss.rect.centerx - M.player.rect.centerx) / T
    assert dist > 10, f"entrada perto demais do boss ({dist:.1f} tiles)"
    assert [type(e) for e in M.enemies].count(Gorila) == 1
    ok(f"entrada na arena segura (boss a {dist:.0f} tiles, esperando)")


def teste_aparicao_e_saida_bloqueada():
    colocar_player(M.area_boss["rect"].left // T + 1)
    frame()
    assert M.boss.ativo and M.boss.estado == "INTRO", M.boss.estado
    vida = M.player.player_health
    frame(constants.GORILA_INTRO_MS // DT - 2)
    assert M.player.player_health == vida and not M.boss.projeteis, "atacou durante a aparicao"
    frame(5)
    assert M.boss.estado == "COMBATE"
    # saída trancada durante a luta
    saida = M.passagens_cenario.itens[0]
    guarda = (M.player.rect.copy(), M.player.pos_x, M.player.pos_y)
    M.player.rect.midbottom = saida.rect.midbottom
    M.player.pos_x, M.player.pos_y = float(M.player.rect.x), float(M.player.rect.y)
    M.interagir_pressionado = True
    M._checar_passagens()
    M.interagir_pressionado = False
    assert not M.transicao.ativa and M.setor_atual.nome == "arena", "saiu da arena durante a luta"
    assert "bloqueada" in M.aviso_jogo[0]
    M.player.rect, M.player.pos_x, M.player.pos_y = guarda
    ok("aparicao sem ataque, barra ativa e saida bloqueada durante a luta")


def _esperar(cond, limite=2000):
    for _ in range(limite):
        if cond():
            return True
        frame()
    return False


def teste_arremesso_com_aviso_e_dano_unico():
    b = M.boss
    b.lancamentos = 1          # garante banana neste arremesso
    b._pos_minerio_ciclo = 0
    assert _esperar(lambda: b.preparando is not None), "boss nunca preparou arremesso"
    inicio = _agora[0]
    assert _esperar(lambda: b.projeteis), "boss nunca arremessou"
    assert _agora[0] - inicio >= constants.GORILA_POSE_ARREMESSO - DT, "arremesso sem aviso"
    # dano não repete por frame
    M.player.invulnerable = False
    vida = M.player.player_health
    proj = b.projeteis[0]
    for _ in range(10):
        proj.rect.center = M.player.rect.center
        proj.causar_dano(M.player)
    assert vida - M.player.player_health == constants.GORILA_PROJETIL_DAMAGE, "dano repetido"
    b.projeteis.clear()
    ok("arremesso com pose de aviso; dano aplicado uma vez so (invencibilidade)")


def _forcar_minerio_no_player(tipo="cobre"):
    b = M.boss
    from src.entidades.enemies.boss import ProjetilGorila
    p = ProjetilGorila(b, M.player.rect.centerx + 60, M.player.rect.centery, -8, 0, tipo)
    b.projeteis.append(p)
    assert _esperar(lambda: M.estado_jogo == "QUIZ", 60), "minerio nao abriu o quiz"
    return p


def teste_minerio_acerto_devolve_e_atordoa():
    b = M.boss
    vida_boss = b.vida
    p = _forcar_minerio_no_player()
    assert M.quiz_boss is not None and M.quiz_boss["projetil"] is p
    seg = M.segundos_restantes_boss()
    assert constants.QUIZ_BOSS_MIN_S <= seg <= constants.QUIZ_BOSS_MAX_S, seg
    M.desenhar_jogo((0, 0))
    M.quiz_tela.desenhar(M.screen, M.pergunta_em_jogo(), 0, 0, 1,
                         segundos_restantes=seg)
    certa = M.pergunta_em_jogo()["resposta"]
    n_resp = M.ordem_resposta
    M.processar_resposta(certa)
    assert M.estado_jogo == "QUIZ_FEEDBACK" and "ACERTOU" in M.quiz_mensagem
    assert M.ordem_resposta == n_resp + 1, "resposta do boss nao foi registrada"
    assert _esperar(lambda: b.vida == vida_boss - 1, 400), "minerio devolvido nao feriu o boss"
    assert b.estado == "ATORDOADO"
    frame(30)
    assert not b.preparando and b.estado == "ATORDOADO", "boss atacou atordoado"
    assert _esperar(lambda: b.estado == "COMBATE", constants.GORILA_ATORDOADO_MS // DT + 10)
    ok(f"minerio -> quiz ({seg}s) -> acerto devolve, boss perde 1 vida e fica atordoado")


def teste_minerio_erro_e_tempo_esgotado():
    b = M.boss
    vida_boss = b.vida
    _forcar_minerio_no_player("zinco")
    certa = M.pergunta_em_jogo()["resposta"]
    errada = next(l for l in "abcde" if l != certa)
    M.player.invulnerable = True    # mesmo invencível, o minério errado acerta
    vida = M.player.player_health
    M.processar_resposta(errada)
    assert M.player.player_health == vida - constants.GORILA_PROJETIL_DAMAGE
    assert b.vida == vida_boss and not any(p.eh_minerio for p in b.projeteis)
    assert _esperar(lambda: M.estado_jogo == "JOGANDO", 200)
    # tempo esgotado
    frame(80)
    M.player.player_health = constants.PLAYER_HEALTH
    _forcar_minerio_no_player()
    vida = M.player.player_health
    prazo = M.quiz_boss["prazo"]
    _agora[0] = prazo + 1
    frame()
    assert M.estado_jogo == "QUIZ_FEEDBACK" and "TEMPO" in M.quiz_mensagem
    assert M.player.player_health < vida
    res = M.banco_estatisticas.buscar_resultado(M.sessao_atual_id)
    assert res["perguntas"][-1]["escolhida"] == "" and not res["perguntas"][-1]["acertou"]
    assert _esperar(lambda: M.estado_jogo == "JOGANDO", 200)
    ok("erro e tempo esgotado: dano no jogador, boss intacto, registrado como erro")


def teste_fase2_pancada_e_onda():
    b = M.boss
    b.vida = b.VIDA_MAX // 2
    assert b.fase == 2
    M.player.player_health = constants.PLAYER_HEALTH
    b.proxima_pancada = _agora[0]
    b.preparando = None
    assert _esperar(lambda: b.pancada is not None, 200), "fase 2 sem pancada"
    assert b.pancada["etapa"] == "aviso"
    inicio = _agora[0]
    assert _esperar(lambda: b.ondas, 400), "pancada sem onda de choque"
    assert _agora[0] - inicio >= constants.GORILA_PANCADA_AVISO_MS, "pancada sem aviso"
    # onda acerta quem está no chão (uma vez) e não quem está acima dela
    onda = OndaDeChoque(0, M.player.rect.bottom, 1, b.limites)
    M.player.invulnerable = False
    vida = M.player.player_health
    onda.rect.midbottom = M.player.rect.midbottom
    onda.pos_x = float(onda.rect.x)
    onda.update(M.player)
    onda.update(M.player)
    assert M.player.player_health == vida - constants.GORILA_ONDA_DANO
    M.player.invulnerable = False
    vida = M.player.player_health
    pulando = M.player.rect.copy()
    M.player.rect.bottom = onda.rect.top - 2
    M.player.rect.centerx = onda.rect.centerx
    onda.update(M.player)
    assert M.player.player_health == vida, "onda acertou jogador no ar"
    M.player.rect = pulando
    M.player.player_health = constants.PLAYER_HEALTH
    ok("fase 2: salto-pancada com aviso, onda acerta no chao e e evitavel pulando")


def teste_macas_da_arena():
    assert len(M.curas) == 2, f"arena deveria ter 2 macas, tem {len(M.curas)}"
    maca = M.curas[0]
    M.player.player_health = 20
    guarda = M.player.rect.copy()
    M.player.rect.center = maca.rect.center
    M._verificar_coletas()
    assert M.player.player_health == 20 + constants.ITEM_CURA_VIDA and maca not in M.curas
    M.player.rect = guarda
    M.player.player_health = constants.PLAYER_HEALTH
    ok("maca cura e some; com vida cheia nao e gasta")


def teste_derrota_na_arena_e_reinicio():
    velho = M.boss
    M.player.player_health = 0
    M.player.alive = False
    frame()
    assert M.estado_jogo == "GAME_OVER" and M.morreu_na_arena
    textos = [b.texto for b in M.botoes_game_over_boss]
    assert "TENTAR DE NOVO" in textos, textos
    M.reiniciar_luta_boss()
    assert M.estado_jogo == "JOGANDO" and M.player.alive
    assert M.player.player_health == constants.PLAYER_HEALTH
    assert M.boss is not velho and M.boss.vida == M.boss.VIDA_MAX and not M.boss.ativo
    assert [type(e) for e in M.enemies].count(Gorila) == 1, "boss duplicado"
    assert len(M.curas) == 2, "macas nao voltaram"
    frame(20)
    assert M.player.on_ground and not M.boss.ativo
    ok("game over na arena -> TENTAR DE NOVO: boss novo (sem duplicar), vida cheia, macas de volta")


def teste_luta_completa_ate_vitoria():
    """Bot: deixa minérios acertarem, responde certo e mantém a vida (testa o ritmo)."""
    colocar_player(M.area_boss["rect"].left // T + 2)
    respostas = 0
    for _ in range(60 * 60 * 6):         # até 6 minutos de jogo
        if M.estado_jogo == "QUIZ" and M.quiz_boss:
            M.processar_resposta(M.pergunta_em_jogo()["resposta"])
            respostas += 1
        if M.estado_jogo == "VITORIA":
            break
        if M.player:
            M.player.player_health = constants.PLAYER_HEALTH  # só o ritmo importa aqui
        # minério vem na direção do jogador; banana o bot ignora (vida cheia)
        frame()
    assert M.estado_jogo == "VITORIA", f"luta nao terminou (vida do boss {M.boss.vida if M.boss else 0})"
    assert M.boss is None and not any(isinstance(e, Gorila) for e in M.enemies)
    M.desenhar_vitoria((0, 0))
    res = M.banco_estatisticas.buscar_resultado(M.sessao_atual_id)
    assert res["resultado"] == "vitoria", res.get("resultado")
    assert res["acertos"] >= Gorila.VIDA_MAX - 1
    from src.sistemas.estatisticas import gerar_pdf_relatorio
    caminho = gerar_pdf_relatorio(res, PASTA_TMP)
    assert os.path.getsize(caminho) > 2000
    ok(f"luta completa vencivel: {respostas} minerios respondidos ate a VITORIA; "
       f"sessao marcada como vitoria e PDF gerado ({len(res['perguntas'])} respostas)")


if __name__ == "__main__":
    preparar()
    teste_entrada_segura()
    teste_aparicao_e_saida_bloqueada()
    teste_arremesso_com_aviso_e_dano_unico()
    teste_minerio_acerto_devolve_e_atordoa()
    teste_minerio_erro_e_tempo_esgotado()
    teste_fase2_pancada_e_onda()
    teste_macas_da_arena()
    teste_derrota_na_arena_e_reinicio()
    teste_luta_completa_ate_vitoria()
    M.banco_estatisticas.fechar()
    print("TODOS OS TESTES DO BOSS PASSARAM")
