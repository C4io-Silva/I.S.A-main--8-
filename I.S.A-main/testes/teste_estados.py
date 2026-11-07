"""
Máquina de estados do Jogo (src/jogo): cada tela abre e desenha, os botões
levam ao estado certo, e o que o main antigo fazia nos cantos continua valendo.

Cobre o que os outros testes não pegam: botões de GAME OVER / VITÓRIA / pausa,
TENTAR DE NOVO na arena, F11, QUIT e a cor do feedback do quiz do boss.

Uso (a partir da raiz do projeto):
    python testes/teste_estados.py
"""
import os
import sys
import tempfile
from types import SimpleNamespace

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("ISA_DB", os.path.join(tempfile.mkdtemp(prefix="isa_teste_"), "estatisticas.db"))
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

import pygame  # noqa: E402

from src.jogo.app import Jogo  # noqa: E402
from src.jogo.estados import CLASSES  # noqa: E402
from src.sistemas.joystick import acionar  # noqa: E402


def ok(msg):
    print("ok:", msg)


def tecla(jogo, k, tipo=pygame.KEYDOWN):
    jogo._tratar_evento(pygame.event.Event(tipo, {"key": k, "mod": 0, "unicode": "", "scancode": 0}))


def botao(menu, texto):
    return next(i for i, b in enumerate(menu.botoes) if getattr(b, "texto", None) == texto)


jogo = Jogo()
assert jogo.estado_nome == "INTRO_LOGO"
assert set(jogo.estados) == set(CLASSES), "faltou algum estado"


def teste_toda_tela_abre_e_desenha():
    for nome in ("MENU", "LOGIN", "CONFIGURACOES", "CREDITOS", "MENU"):
        jogo.ir_para(nome)
        for _ in range(3):
            jogo.passo()
    jogo.iniciar_partida()
    assert jogo.estado_nome == "JOGANDO" and jogo.partida.player is not None
    for _ in range(60):
        jogo.passo()
    for nome in ("PAUSADO", "JOGANDO", "GAME_OVER", "VITORIA"):
        jogo.ir_para(nome)
        jogo.passo()
        jogo.passo()
    jogo.abrir_estatisticas()
    jogo.passo()
    assert jogo.estado_nome == "ESTATISTICAS"
    jogo.voltar_menu()
    jogo.passo()
    assert jogo.estado_nome == "MENU" and jogo.partida is None
    ok("os 13 estados abrem e desenham; voltar ao menu descarta a partida")


def teste_pausa_por_teclado():
    jogo.iniciar_partida()
    jogo.partida.entrada.direita = True
    tecla(jogo, pygame.K_ESCAPE)
    assert jogo.estado_nome == "PAUSADO"
    assert not jogo.partida.entrada.direita, "pausar não zerou o movimento"
    tecla(jogo, pygame.K_ESCAPE)
    assert jogo.estado_nome == "JOGANDO"
    ok("ESC pausa (zerando o movimento) e retoma")


def teste_botoes_do_game_over():
    jogo.iniciar_partida()
    antiga = jogo.partida
    jogo.partida.fim_de_jogo()
    estado = jogo.estados["GAME_OVER"]
    assert jogo.estado_nome == "GAME_OVER" and estado.menu is estado.menu_normal
    acionar(estado.menu.botoes, botao(estado.menu, "REINICIAR"))
    assert jogo.estado_nome == "JOGANDO" and jogo.partida is not antiga
    assert jogo.partida.pontuacao == 0
    jogo.partida.fim_de_jogo()
    acionar(estado.menu.botoes, botao(estado.menu, "MENU"))
    assert jogo.estado_nome == "ESTATISTICAS"
    jogo.voltar_menu()
    assert jogo.estado_nome == "MENU"
    ok("GAME OVER: REINICIAR cria partida nova; MENU abre as estatísticas e volta ao menu")


def teste_tentar_de_novo_na_arena():
    jogo.iniciar_partida()
    partida = jogo.partida
    partida.ativar_setor("arena")
    partida.setor_atual.boss.ativar()
    partida.player.alive = False
    partida.fim_de_jogo()
    estado = jogo.estados["GAME_OVER"]
    assert partida.morreu_na_arena and estado.menu is estado.menu_boss
    assert [b.texto for b in estado.menu.botoes] == ["TENTAR DE NOVO", "REINICIAR", "MENU"]
    boss_antigo = partida.setor_atual.boss
    acionar(estado.menu.botoes, botao(estado.menu, "TENTAR DE NOVO"))
    assert jogo.partida is partida, "TENTAR DE NOVO não deveria criar partida nova"
    assert jogo.estado_nome == "JOGANDO" and partida.setor_atual.nome == "arena"
    assert partida.player.alive and not partida.morreu_na_arena
    assert partida.boss is not boss_antigo and not partida.boss.ativo, "o boss não foi trocado"
    ok("TENTAR DE NOVO recomeça só a luta: mesma partida, boss novo, jogador vivo")


def teste_botoes_da_vitoria():
    jogo.iniciar_partida()
    jogo.ir_para("VITORIA")
    menu = jogo.estados["VITORIA"].menu
    assert [b.texto for b in menu.botoes] == ["RELATORIO", "JOGAR DE NOVO", "MENU"]
    antiga = jogo.partida
    acionar(menu.botoes, botao(menu, "JOGAR DE NOVO"))
    assert jogo.estado_nome == "JOGANDO" and jogo.partida is not antiga
    ok("VITÓRIA: JOGAR DE NOVO começa partida nova")


def teste_cor_do_feedback_nao_depende_do_texto():
    """No original a cor vinha de `"ACERTOU" in mensagem`: 'ERROU! O MINERIO TE
    ACERTOU!' (erro no quiz do boss) saía VERDE."""
    jogo.iniciar_partida()
    partida = jogo.partida
    quiz = partida.quiz
    projetil = SimpleNamespace(causar_dano=lambda alvo: None, refletir=lambda: None)
    gorila = SimpleNamespace(projeteis=[projetil])
    pergunta = {"pergunta": "2+2?", "opcao_a": "3", "opcao_b": "4", "resposta": "b",
                "disciplina": "Teste", "dificuldade": "Fácil"}
    quiz.boss = {"boss": gorila, "projetil": projetil, "pergunta": pergunta, "prazo": 10 ** 12}
    quiz.responder("a")                              # errou
    assert "ACERTOU" in quiz.mensagem and quiz.acertou is False, (quiz.mensagem, quiz.acertou)
    jogo.passo()                                     # desenha o feedback sem erro
    assert ("ERROU! O MINERIO TE ACERTOU!", False) in jogo.estados["QUIZ_FEEDBACK"]._cache
    quiz.boss = {"boss": gorila, "projetil": projetil, "pergunta": pergunta, "prazo": 10 ** 12}
    quiz.responder("b")                              # acertou
    assert quiz.acertou is True
    ok("cor do feedback vem de `acertou`, não do texto (erro do boss deixa de ficar verde)")


def teste_feedback_volta_ao_jogo_e_restaura_volume():
    jogo.iniciar_partida()
    partida = jogo.partida
    item = partida.itens[0]
    partida.quiz.abrir_para_minerio(item)
    assert jogo.estado_nome == "QUIZ" and jogo.audio._em_quiz
    partida.quiz.responder("a")
    assert jogo.estado_nome == "QUIZ_FEEDBACK" and not jogo.audio._em_quiz
    for _ in range(100):
        jogo.passo()
        if jogo.estado_nome != "QUIZ_FEEDBACK":
            break
    assert jogo.estado_nome in ("JOGANDO", "GAME_OVER"), jogo.estado_nome
    ok("quiz -> feedback (90 frames) -> jogo, com o volume da música restaurado")


def teste_f11_quit_e_mouse():
    antes = jogo.janela.fullscreen
    tecla(jogo, pygame.K_F11)
    assert jogo.janela.fullscreen != antes
    tecla(jogo, pygame.K_F11)
    assert jogo.janela.fullscreen == antes
    jogo.foco_no_controle = True
    jogo._tratar_evento(pygame.event.Event(pygame.MOUSEMOTION, {"pos": (10, 10), "rel": (1, 1), "buttons": (0, 0, 0)}))
    assert jogo.foco_no_controle is False, "mexer o mouse deve devolver o destaque ao cursor"
    jogo._tratar_evento(pygame.event.Event(pygame.QUIT))
    assert jogo.rodando is False
    jogo.rodando = True
    ok("F11 alterna tela cheia; mouse devolve o foco; QUIT encerra o loop")


for _teste in (teste_toda_tela_abre_e_desenha, teste_pausa_por_teclado, teste_botoes_do_game_over,
               teste_tentar_de_novo_na_arena, teste_botoes_da_vitoria,
               teste_cor_do_feedback_nao_depende_do_texto,
               teste_feedback_volta_ao_jogo_e_restaura_volume, teste_f11_quit_e_mouse):
    _teste()
jogo.banco.fechar()
print("TODOS OS TESTES DE ESTADOS PASSARAM")
