"""Testa a tela de pergunta com selecao por controle (sem abrir o loop)."""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
# Banco de estatísticas temporário: os testes nunca gravam no estatisticas.db real.
import tempfile  # noqa: E402
os.environ.setdefault("ISA_DB", os.path.join(tempfile.mkdtemp(prefix="isa_teste_"), "estatisticas.db"))
os.environ["SDL_AUDIODRIVER"] = "dummy"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

import pygame

from src.jogo.app import Jogo

jogo = Jogo()
quiz_tela = jogo.tela_quiz
tela = jogo.janela.tela

pergunta = {
    "pergunta": "Pergunta bem longa " * 25,
    "opcao_a": "Alternativa A com texto suficiente para quebrar linha " * 3,
    "opcao_b": "Alternativa B com texto suficiente para quebrar linha " * 3,
    "opcao_c": "Alternativa C com texto suficiente para quebrar linha " * 3,
    "opcao_d": "Alternativa D com texto suficiente para quebrar linha " * 3,
    "resposta": "c",
}

# --- desenho com foco no controle ---
jogo.foco_no_controle = True
quiz_tela.selecao = 0
quiz_tela.desenhar(tela, pergunta, 0, 0, 4, foco_no_controle=True)
assert len(quiz_tela.alt_rects) == 4, quiz_tela.alt_rects
assert [l for l, _ in quiz_tela.alt_rects] == ["a", "b", "c", "d"]
assert quiz_tela.max_scroll > 0, "conteudo longo deveria permitir scroll"
print("ok: alternativas registradas e scroll disponivel")

# --- selecao fora da faixa eh corrigida (pergunta com menos opcoes) ---
quiz_tela.selecao = 4
quiz_tela.desenhar(tela, pergunta, 0, 0, 4, foco_no_controle=True)
assert quiz_tela.selecao == 3, f"clamp falhou: {quiz_tela.selecao}"
print("ok: selecao limitada ao numero real de alternativas")

# --- navegacao circular + autoscroll para o item selecionado ---
quiz_tela.selecao = 0
vistos = []
for _ in range(6):
    quiz_tela.desenhar(tela, pergunta, 0, 0, 4, foco_no_controle=True)
    vistos.append(quiz_tela.selecao)
    quiz_tela.navegar(1)
    assert 0 <= quiz_tela.scroll <= quiz_tela.max_scroll
assert vistos == [0, 1, 2, 3, 0, 1], vistos
print("ok: navegacao circula e o scroll acompanha sem sair dos limites")

# --- responder pelo indice selecionado usa a letra certa ---
jogo.iniciar_partida()
partida = jogo.partida
partida.perguntas.fila = [pergunta]
partida.perguntas.indice = 0
partida.pontuacao = 0
partida.player = None
quiz_tela.selecao = 2  # alternativa C = gabarito
quiz_tela.desenhar(tela, pergunta, 0, 0, 1, foco_no_controle=True)
partida.quiz.responder(quiz_tela.letra_selecionada())
assert partida.pontuacao == 1, "resposta pelo controle nao pontuou"
assert jogo.estado_nome == "QUIZ_FEEDBACK"
print("ok: confirmar no controle responde a alternativa destacada")

print("TODOS OS TESTES DE QUIZ PASSARAM")
